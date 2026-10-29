## 请求进入 vLLM 后，谁决定下一步计算

vLLM 的实例内部同时管理多条请求。API 进程负责协议、输入预处理和流式输出；EngineCore 中的 Scheduler 决定每轮处理哪些请求、各处理多少 token；KVCacheManager 管理缓存块；GPU Worker 中的 ModelRunner 准备张量、调用模型并执行采样。一个模型副本可以跨多个 GPU，不能把一个 HTTP 请求等同于一个 GPU Pod。

```text
HTTP 请求 → 模板渲染与 tokenization → EngineCore 的等待队列
  → Scheduler：本轮 token 预算、序列数限制、KV 空间检查
  → KVCacheManager：查可复用块，为新增 token 分配块
  → Executor / GPU Worker / ModelRunner：前向计算、采样
  → 更新已计算 token 数与请求状态 → 流式返回
  → 完成或取消：解除请求对缓存块的引用
```

外层路由器选择模型副本，实例内 Scheduler 组织计算批次，Kubernetes 调度器决定 Pod 放在哪个节点。这三个调度决策的对象和时间尺度不同。

## Continuous Batching 与 Chunked Prefill

静态批处理等待整个批次完成再接收下一批。Continuous Batching 在迭代边界移除完成请求、加入新请求，提高不同输出长度混合时的执行效率。它仍受 KV 容量、每轮 token 预算和最大并发序列数限制。

Chunked Prefill 把长输入的预填充拆成若干轮，允许同一轮包含已有请求的 decode 和新请求的部分 prefill。以简化预算为例：一轮最多计算 512 个 token，64 条 decode 请求各需一个 token，剩余 448 个预算可用于长输入。下一轮重新决策。真实实现还会受到块对齐、投机 token、编码器预算和不同调度配置影响。

预算过大，长 prefill 可能拉长 decode 的迭代时间；过小，则可能增加长输入的排队和调度开销。调优时同时测 TTFT、ITL/TPOT、吞吐以及满足 SLO 的请求比例，不能只看总 token/s。

## APC 的索引和生命周期

Automatic Prefix Caching 复用已计算的相同前缀。普通全注意力模型的 KV 依赖前面的 token，因此块的身份需要包含前缀依赖：

```text
H0 = hash(初始状态, tokens[0:b], 额外标识)
H1 = hash(H0, tokens[b:2b], 额外标识)
H2 = hash(H1, tokens[2b:3b], 额外标识)
```

额外标识可包含 LoRA、多模态输入和租户 cache salt。独立引擎天然处在各自模型上下文中；做外部共享时还需要明确模型版本、tokenizer、位置编码、KV dtype、布局等兼容条件。文字相同而 chat template 不同，最终 token 序列也可能不同。

vLLM 的块池记录物理块 ID、内容 hash、引用计数和空闲队列指针。请求通过块表引用物理块。查到可复用块后先增加引用并从空闲队列移除，再分配新块，防止刚命中的缓存被覆盖。

请求完成会解除引用；引用计数归零的块可进入空闲队列，内容仍可能保留。只有后续分配覆盖该块时，才移除缓存索引。因此“请求结束”与“缓存立即消失”不是同一件事。普通 APC 以完整块为复用粒度，末尾不足一块的公共部分不能直接按完整块命中。

## 一个块级例子

设块大小为 4 个 token，缓存中已有前缀 `ABCD | EFGH | IJKL`。新请求为 `ABCD | EFGH | IJXY | Z`：前两块共 8 个 token 可复用，第三块发生变化，后续链式 hash 也随之变化。这里的字母代表 token ID，不代表字符。

缓存命中减少重复 prefill，但生成新 token 时仍要执行模型，并读取需要的历史 KV。已有前缀全部命中也不意味着请求零耗时：还有路由、等待、输入处理、末尾状态计算及后续生成。

## 显存与延迟的定量检查

对使用常规 KV 的全注意力 decoder，单序列未考虑并行分片时：

\[
M_{KV}=2L H_{KV} d_h T s
\]

其中 2 对应 K 与 V，L 为层数，H_KV 为 KV 头数，d_h 为头维度，T 为已缓存 token 数，s 为每个元素的字节数。示例 L=32、H_KV=8、d_h=128、FP16：每 token 为 128 KiB，8192 token 共 1 GiB。批内总量应按实际共享物理块计算；GQA 看 KV 头数，TP 下也不能无条件把总量除以 TP，因为部分配置会复制 KV 头。MLA、滑动窗口和混合注意力需要使用对应结构重新计算。

显存预算还包括权重、激活峰值、CUDA Graph、通信和工作区。KV 容量不足可能导致请求等待或抢占重算；不能把老版本 swap 行为概括成所有 V1 实现的默认策略。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：一条请求进入 vLLM 后如何执行？</div>
<div class="qa-a"><p>输入先经过模板和分词进入 EngineCore。Scheduler 在每轮预算内选择请求，KVCacheManager 查前缀并分配新增空间，再把本轮 token 交给 Worker 执行。执行结果回来后更新状态、采样并流式输出。完成和取消都要回收请求占用，已经形成的缓存块可以保留供后续请求复用。</p><p>继续追问时，分别展开等待队列、token 预算、块表和取消清理。不要把 API 层、实例级批处理与跨副本路由混在一起。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：PagedAttention、FlashAttention、Prefix Caching 有什么关系？</div>
<div class="qa-a"><p>PagedAttention 通过块表支持不连续的 KV 物理存放；FlashAttention 通过分块和算子融合降低 attention 的中间数据访存；Prefix Caching 识别已经算过的前缀并复用 KV。它们分别处理存储寻址、算子执行和跨请求重复计算，可以组合使用。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：GPU 利用率高，但 TTFT 很差，应如何定位？</div>
<div class="qa-a"><p>先把 TTFT 拆成入口等待、实例排队、预处理、实际 prefill 和首个结果返回。检查输入长度分布、未命中 token 数、等待请求和 KV 压力，再看迭代耗时与 GPU kernel 时间线。高 GPU 利用率只说明采样窗口中 GPU 忙，无法证明排队合理或计算都对业务有用。可能需要限流、调整 token 预算、改善缓存命中或增加副本，具体取决于耗时分解。</p></div>
</div>

来源：[vLLM 进程架构](https://github.com/vllm-project/vllm/blob/cf3f6405b849f2b672d93af0c4cf4e5e6dc6bd1b/docs/design/arch_overview.md)、[APC 设计与块生命周期](https://github.com/vllm-project/vllm/blob/cf3f6405b849f2b672d93af0c4cf4e5e6dc6bd1b/docs/design/prefix_caching.md)。核对日期：2026-10-29；数值例子为公式推算。

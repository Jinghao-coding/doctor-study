## KV Cache 的作用

自回归生成时，模型每生成一个新 token 都需要关注历史上下文。如果每一步都重新计算全部历史 token 的 Key 和 Value，计算代价会非常高；KV Cache 的作用就是把历史 K/V 缓存下来，每步只计算新增 token 的 K/V。

```text
KV Cache 大小 = 2 × num_layers × num_kv_heads × head_dim × seq_len × dtype_bytes
```

公式中的 `2` 分别代表 Key 和 Value。KV Cache 随序列长度、batch size 和 KV head 数量线性增长，是长上下文和高并发推理的核心显存压力来源。

## 显存为什么紧张

| 显存类别 | 特点 | 对推理的影响 |
|---|---|---|
| 模型权重 | 加载后固定，可通过 TP/PP 切分 | 决定基础显存门槛 |
| KV Cache | 每个请求独立，随上下文增长 | 决定并发数和最大上下文 |
| 临时激活 | Prefill 时较明显，Decode 时较小 | 影响峰值显存 |
| Runtime Buffer | 框架和 kernel 需要的工作区 | 影响可用余量 |

## Attention 变体

| 机制 | KV Head 数 | KV Cache | 质量与场景 |
|---|---|---|---|
| MHA | 等于 Query Head 数 | 最大 | 质量好，但推理显存压力大 |
| GQA | 多个 Query Head 共享一组 K/V | 缩小数倍 | 当前主流，质量和效率平衡 |
| MQA | 所有 Query Head 共享一组 K/V | 最小 | 显存最省，但质量可能受影响 |
| MLA | 压缩到 latent 表示 | 很小 | DeepSeek 系列代表的前沿方案 |

## PagedAttention

PagedAttention 借鉴操作系统虚拟内存的分页思想，把 KV Cache 切成固定大小的 block，并用 block table 维护逻辑 token 到物理 block 的映射。

| 问题 | 传统连续分配 | PagedAttention |
|---|---|---|
| 短请求浪费 | 按最大长度预留，浪费大 | 按需分配 block |
| 显存碎片 | 连续空间难复用 | 非连续 block 可组合 |
| 前缀共享 | 复用困难 | 支持引用计数和 copy-on-write |
| 并发能力 | 受预分配限制 | 更接近真实显存上限 |

## PagedAttention 为什么颠覆传统推理调度

传统推理调度常被 KV Cache 的连续显存分配限制住：每个请求要么预留最大长度，要么在生成过程中频繁扩容；请求结束后释放的空间也未必能被新请求连续复用。PagedAttention 把 KV Cache 管成固定大小的物理 block，请求看到的是逻辑 token 序列，底层可以映射到不连续 block。

这带来三个调度变化：

| 变化 | 传统方式 | PagedAttention 后 |
|---|---|---|
| 接纳新请求 | 需要判断是否有足够连续 KV 空间 | 只要有足够空闲 block 就可接纳 |
| 释放请求 | 释放一大段连续 cache，容易形成洞 | 释放一组 block，直接回到 block pool |
| 前缀复用 | 很难共享不同请求的公共 prompt | block 可以引用计数，支持 prefix cache 和 copy-on-write |
| 调度粒度 | 多按请求级别粗粒度调度 | 可以按 token/block 预算做细粒度调度 |

因此 vLLM 这类推理引擎可以把调度器从“静态 batch + 固定显存”推进到“iteration-level scheduling + block-level KV 管理”。这也是 Continuous Batching 能稳定工作的基础：每一轮 decode 后，完成的请求释放 block，新请求只要拿到 block 就能进入 running set。

面试口径：**PagedAttention 不是一个 attention kernel，而是 KV Cache 的虚拟内存系统。它解决的是显存碎片和动态请求接纳问题，从而支撑 continuous batching。**

## FlashAttention

FlashAttention 解决的是 attention 计算中的中间矩阵读写问题，而不是 KV Cache 管理问题。它通过分块计算和 online softmax 避免把完整 attention score 矩阵写回 HBM，从而降低显存读写并提升速度。

| 技术 | 解决的问题 | 主要阶段 |
|---|---|---|
| KV Cache | 避免重复计算历史 K/V | Decode |
| PagedAttention | 降低 KV Cache 碎片和浪费 | Serving 调度 |
| FlashAttention | 降低 attention 中间读写 | Prefill 和长上下文 |
| GQA/MQA | 从模型结构上减少 KV Cache | Decode 和长上下文 |

## 易错点

PagedAttention 和 FlashAttention 不是同一类技术。PagedAttention 管 KV Cache 的存储和分配，FlashAttention 优化 attention kernel 的计算和访存，两者可以同时使用。

## 高频追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: PagedAttention 和操作系统分页有什么相似点？</div>
<div class="qa-a"><p>相似点是都把“逻辑连续”映射到“物理不连续”。OS 里进程看到连续虚拟地址，页表映射到物理页；PagedAttention 里请求看到连续 token/KV 序列，block table 映射到 GPU KV block。这样可以按需分配、释放和复用 block，降低内部/外部碎片。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: PagedAttention 会不会降低 attention 计算效率？</div>
<div class="qa-a"><p>它增加了 block table 查询和非连续 block 访问的管理复杂度，但换来更高的显存利用率和更大的可运行 batch。在服务场景中，吞吐瓶颈往往来自 KV Cache 容量和调度空洞，而不是单次 attention 的极限 kernel 性能，所以整体收益通常更大。</p></div>
</div>

## 参考资料

- vLLM 官方 Anatomy 文章：系统性解释 scheduler、PagedAttention、continuous batching、chunked prefill、speculative decoding 和 disaggregated P/D。
- vLLM internals 资料：从 block pool、KV cache manager 和 scheduler 角度解释 PagedAttention 的运行方式。

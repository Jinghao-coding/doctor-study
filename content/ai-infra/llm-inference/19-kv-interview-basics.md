## 缓存内容与计算过程

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q1：KV Cache 缓存什么？为什么通常不缓存 Q？</div>
<div class="qa-a"><p>在标准因果自注意力中，每层保存历史 token 的 Key 和 Value。生成新 token 时，新 Q 与历史 K 计算注意力，再对历史 V 加权；历史 Q 不参与这个新位置的输出，所以通常无需为后续生成保存。</p><p><strong>追问：历史 K/V 为什么可以复用？</strong>因果 mask 使过去位置看不到未来 token；模型权重、位置编码和输入前缀不变时，追加 token 不会改变过去位置的 K/V。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q2：Prefill 和 Decode 分别怎样读写 KV？缓存后每一步就是 O(1) 吗？</div>
<div class="qa-a"><p>Prefill 并行处理输入，逐层生成输入各位置的 K/V；Decode 通常处理一个新增位置，把它的 K/V 追加到缓存。对长度为 T 的全注意力上下文，新 Q 仍需读取历史 K/V，单步 attention 随 T 增长；缓存省掉的是重复执行历史位置的投影和前向计算。</p><p><strong>追问：生成 N 个 token 呢？</strong>若输入长度为 S，忽略层数和维度常数，新增位置的 attention 工作量约为 NS + N(N−1)/2；不能说 KV Cache 消除了长上下文的带宽成本。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q3：为什么普通训练通常不用推理式 KV Cache？</div>
<div class="qa-a"><p>Teacher forcing 训练已知整段目标，能一次并行计算各位置，并需要保留或重算反向传播所需激活。跨优化步骤复用旧 K/V 还会遇到权重变化导致缓存失效的问题。训练激活和生成服务的历史 KV 用途不同。</p><p><strong>追问：强化学习训练中的 rollout 呢？</strong>Rollout 是自回归推理，可以使用 KV Cache；后面的策略梯度更新属于训练阶段，应分别讨论。</p></div>
</div>

上述计算过程对应标准因果 Decoder，参见 [Transformers 缓存机制](https://huggingface.co/docs/transformers/cache_explanation)。

## 显存估算与并行分片

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q4：现场怎么算 KV Cache 占用？</div>
<div class="qa-a"><p>对各层 KV 结构一致、没有前缀共享和窗口淘汰的模型：总字节数 = 2 × 层数 L × KV 头数 Hkv × 每头维度 d × 每元素字节 b × 所有请求已缓存 token 数之和。2 代表 K、V 两份；请求长度不同就求和，不能随意用最大长度乘并发数当实际占用。</p><p><strong>计算例：</strong>假设 L=32、Hkv=8、d=128、BF16 为 2 字节，每 token 是 131072 字节，即 128 KiB；一个 8192 token 请求占 1 GiB，16 个这样的请求共 16 GiB。这是理想数据量，还没算 block 尾部浪费、量化尺度和运行时开销。</p><p><strong>追问：有 24 GiB 的 KV 预算是否能保证接 24 个？</strong>不能直接保证。它只是每个请求最多缓存 8192 token 时的理想上限；若还会增长、需要投机槽位或暂存，就必须继续预留。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q5：GQA、MQA 为什么省 KV？MLA 也套这个公式吗？</div>
<div class="qa-a"><p>MHA 的每个 Query head 对应一组 K/V；GQA 让一组 Query heads 共用 K/V；MQA 让所有 Query heads 共用一组。其他条件相同，KV 数据量与 Hkv 成正比。例如 32 个 Query heads、8 个 KV heads，比对应 MHA 的 KV 少到四分之一。不能把 Query head 数直接代入 GQA 的 KV 公式。</p><p><strong>追问：能只改推理配置把 MHA 变 GQA 吗？</strong>通常不能，它属于模型结构和权重组织。MLA 应按实际缓存的压缩 latent、位置编码分量及后端布局计算，也不能直接照搬普通 GQA 公式。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q6：TP=8，单卡 KV 就一定等于总量除以 8 吗？</div>
<div class="qa-a"><p>只有 KV heads 被均匀切到 8 个 rank、没有复制且各卡负责相同层数时，这个估算才成立。KV heads 少于 TP 时，一些实现会复制 KV heads；PP 则按每个 stage 的层数算。数据并行副本管理自己的请求，不能把全服务请求的 KV 再无条件除以副本数。</p><p><strong>追问：总显存够为什么某张卡 OOM？</strong>应按最吃紧 rank 的权重、KV、激活、通信缓冲和工作区检查；层数不均、复制和局部请求负载都会让平均值失真。</p></div>
</div>

## 优化收益与正确性

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q7：PagedAttention 和 FlashAttention 有什么区别？</div>
<div class="qa-a"><p>PagedAttention 用 block table 访问非连续的 KV blocks，并需要相应 attention 计算实现；它支持按需分配、共享和回收。FlashAttention 通过分块和在线 softmax 减少注意力中间矩阵的 HBM 读写。两者侧重点不同，可以组合，PagedAttention 也不是硬件 MMU 自动处理缺页。</p><p><strong>追问：分页之后不会浪费显存了吗？</strong>仍有最后一个未满 block 的内部浪费，以及元数据和预留空间。block 小能降低尾部浪费，但增加管理和寻址成本。</p></div>
</div>

分页算法与 vLLM 内存管理的关系参见 [PagedAttention 原论文](https://arxiv.org/abs/2309.06180)。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q8：KV 量化是不是显存减半、速度就翻倍？</div>
<div class="qa-a"><p>从 16 bit 改到 8 bit，理想 KV 数据部分减半；实际还要计入 scale、对齐和临时缓冲。速度取决于是否受 KV 带宽限制、解量化是否融合、kernel 支持和 batch 大小。若主要耗时在权重读取或通信，收益可能有限。</p><p><strong>追问：如何验证质量？</strong>对比长短上下文、检索和生成任务，检查指标与尾延迟。K 的误差会改变注意力权重，V 的误差改变加权结果；权重量化也会影响每一步前向，不能声称它的误差只发生一次。</p></div>
</div>

实现支持与量化尺度说明参见 [vLLM Quantized KV Cache](https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache/)。

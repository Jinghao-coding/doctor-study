## Attention 的计算与资源瓶颈

单头缩放点积 Attention 为：

$$
\operatorname{Attention}(Q,K,V)
=\operatorname{softmax}\left(\frac{QK^\top}{\sqrt{d_h}}+M\right)V
$$

其中序列长度为 $S$、头维度为 $d_h$ 时，$QK^\top$ 和注意力矩阵乘 $V$ 的计算量都是 $O(S^2d_h)$。朴素实现还会把 $S\times S$ 的 score 或 probability 中间矩阵写到 HBM，训练时保存反向所需状态。因此优化 Attention 需要区分三个问题：计算次数、HBM 数据搬运和随上下文增长的 KV Cache 容量。

<div class="table-scroll">

| 场景 | 主要压力 | 典型优化 |
|---|---|---|
| 训练与 Prefill | 长序列下 $S^2$ 计算和中间矩阵 IO | FlashAttention、融合、稀疏/局部 Attention |
| Decode | 每步读取历史 K/V，算术强度较低 | MQA/GQA、KV 量化、连续批处理 |
| Serving 容量管理 | 不同请求长度造成预留浪费和碎片 | PagedAttention、准入、回收与换出 |

</div>

## 保持精确语义的 GPU 执行优化

FlashAttention 仍然计算精确的标准 Attention。它把 Q、K、V 分块搬到片上 SRAM，在块内完成矩阵计算，并通过在线 Softmax 维护每行的最大值、归一化因子和部分输出，从而不必把完整 $S\times S$ 注意力矩阵反复写入和读出 HBM。

分块 Softmax 合并的关键是数值稳定。假设已经处理一部分 key，保存行最大值 $m_{old}$、指数和 $l_{old}$ 与未归一化输出累积；新块最大值为 $m_{new}$。合并时先令：

$$
m=\max(m_{old},m_{new})
$$

再把旧块和新块的指数和分别乘以 $e^{m_{old}-m}$、$e^{m_{new}-m}$ 后相加。这样可以逐块得到与整行 Softmax 等价的结果，同时避免保存完整 score 矩阵。

FlashAttention 改变的是计算顺序和内存访问，标准全注意力的渐进 FLOPs 仍是 $O(S^2d_h)$。它的核心收益来自减少 HBM 与片上存储之间的读写，并把多个步骤融合进更少的 kernel。原论文将其定义为 IO-aware exact attention，参见 [FlashAttention](https://arxiv.org/abs/2205.14135)。

## MHA、MQA 与 GQA：减少 KV 头数

设 Query 头数为 $H_q$，KV 头数为 $H_{kv}$：

<div class="table-scroll">

| 结构 | KV 头数 | KV 容量和 Decode 带宽 | 主要权衡 |
|---|---:|---|---|
| MHA | $H_{kv}=H_q$ | 最大 | 表达能力强，KV 成本高 |
| GQA | $1<H_{kv}<H_q$ | 按头数比例下降 | 在质量与推理效率间折中 |
| MQA | $H_{kv}=1$ | 最小 | 吞吐和容量更优，可能损失质量 |

</div>

对于 batch 为 $B$、层数为 $L$、缓存 token 数为 $S$、头维度为 $d_h$、每元素 $b$ 字节的 decoder，KV Cache 的近似容量为：

$$
M_{KV}=2BLSH_{kv}d_hb
$$

系数 2 表示 K 和 V。GQA/MQA 减少的是 $H_{kv}$，所以同时减少缓存容量和 Decode 每步读取 KV 的字节数。它们改变模型结构，不能像 kernel 优化一样在任意既有 checkpoint 上无条件切换。GQA 的原始工作讨论了从 MHA checkpoint 进行 uptraining 的办法，参见 [GQA](https://arxiv.org/abs/2305.13245)。

## 改变注意力连接范围或计算形式

<div class="table-scroll">

| 方法 | 核心思路 | 复杂度或收益 | 代价 |
|---|---|---|---|
| Sliding Window | 只关注相邻窗口 | 从全局平方交互降为与窗口宽度相关 | 单层不能直接看到所有远距离 token |
| Block Sparse | 只计算规定的块 | 跳过大量 score block | 稀疏模式和 kernel 效率共同决定实际加速 |
| Global + Local | 少量全局 token 配合局部窗口 | 保留部分全局信息 | 结构和任务相关，需要模型侧设计 |
| Linear Attention | 使用核技巧或改变结合顺序 | 尝试避免显式 $S^2$ 矩阵 | 通常改变标准 Softmax Attention 语义和精度特性 |

</div>

“理论复杂度降低”不保证 GPU 上更快。稀疏模式若不规则，会产生索引、分支和不连续访存；序列较短时，稠密 GEMM 或融合 kernel 可能更高效。判断收益需要同时看 FLOPs、算子形状、数据搬运和硬件利用率。

## KV Cache 的存储与容量优化

PagedAttention 把请求的逻辑 KV 序列映射到固定大小物理块，降低连续大块预留和外部碎片，并支持块级复用。它主要改变缓存的存储管理，不减少一个 token 在既定模型结构下产生的 KV 元素数，也不改变 Attention 的数学公式。

其他容量方向包括：

- KV 量化：降低每个元素字节数，需要控制量化误差和反量化开销；
- KV 淘汰或压缩：保留重要 token 或摘要，可能改变模型输出；
- 前缀缓存：复用相同前缀已经计算出的 KV，命中率取决于请求共享模式；
- 分层存储与换出：用 CPU 或其他层级扩大容量，但引入传输延迟；
- 准入与动态 batching：从系统层限制并发和 token 预算，避免容量失控。

## 数值精度与融合

Attention 中的 GEMM 可以利用 FP16、BF16 或更低精度的 Tensor Core 路径，但归约、最大值和 Softmax 累积通常需要更稳定的精度策略。低精度带来的收益包括更低的带宽与更高的矩阵吞吐，风险是溢出、下溢和误差累积。

融合 QKV projection、RoPE、mask、Softmax 或输出 projection 可以减少中间 tensor 落到 HBM 的次数以及 kernel launch 次数。是否能融合取决于 shape、数据布局、动态控制流和框架编译能力；融合过大还可能增加寄存器压力，降低 occupancy。

## 高频追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Attention 有哪些优化方向？</div>
<div class="qa-a">
<p>我会分四类。第一类保持数学语义，通过 FlashAttention、分块和融合减少 HBM 读写与 launch 开销；第二类用 MQA/GQA 减少 KV 头数，降低缓存容量和 Decode 带宽；第三类用滑动窗口、块稀疏或线性 Attention 减少交互范围或改变计算形式；第四类在 serving 层做 KV 分页、量化、复用、换出和准入。回答时要说明优化的是 FLOPs、IO 还是容量，以及是否改变模型结构或输出。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: FlashAttention 为什么更快？它把平方复杂度降下来了吗？</div>
<div class="qa-a">
<p>它主要通过 tiling、在线 Softmax 和融合减少 HBM 访问，不物化完整注意力矩阵，同时保持精确 Attention。标准全注意力的渐进计算复杂度仍然是平方级，所以不能说 FlashAttention 把 FLOPs 变成线性；它优化的是实际 GPU 执行中的 IO 和中间存储。</p>
</div>
</div>

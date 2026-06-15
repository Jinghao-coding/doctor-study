## 一句话结论

Roofline 用算术强度把 Transformer 算子分成 compute-bound 和 memory-bound。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Transformer 与大模型基础 |
| 章节类型 | 机制类（含公式） |
| 解决问题 | 围绕 Transformer 架构、计算量、Roofline、算子瓶颈和大模型推理/训练性能建立深度答案。 |
| 面试抓手 | 公式必须讲 FLOPs、bytes 和 ridge point。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-d">
<h3>Roofline：判断瓶颈在算力还是带宽</h3>
<p>一个计算任务的耗时，要么受限于<strong>算力</strong>（每秒能做多少浮点运算），要么受限于<strong>带宽</strong>（每秒能搬多少数据）。判断靠<strong>算术强度</strong>：</p>
<p>$$\text{算术强度} = \frac{\text{计算量 (FLOPs)}}{\text{数据搬运量 (Bytes)}}$$</p>
<table>
<tr><th>判定</th><th>条件</th><th>瓶颈</th><th>优化方向</th></tr>
<tr><td>compute-bound</td><td>算术强度 &gt; 机器平衡点</td><td>算力</td><td>TensorCore、低精度、提高利用率</td></tr>
<tr><td>memory-bound</td><td>算术强度 &lt; 机器平衡点</td><td>带宽</td><td>kernel fusion、量化、增大 batch</td></tr>
</table>
<p>机器平衡点 = 峰值算力 ÷ 峰值带宽。算术强度高于它卡算力，低于它卡带宽。</p>
</div>

<div class="card card-d">
<h3>哪些操作 compute-bound，哪些 memory-bound</h3>
<table>
<tr><th>操作</th><th>瓶颈</th><th>原因</th></tr>
<tr><td>大 batch 矩阵乘（QKV、FFN）</td><td>compute-bound</td><td>计算量随 batch 增长快，数据搬运增长慢，算术强度高</td></tr>
<tr><td>逐 token decode（batch 小）</td><td>memory-bound</td><td>矩阵乘退化成 GEMV，算术强度低，瓶颈是读权重带宽</td></tr>
<tr><td>Softmax、LayerNorm 等 element-wise</td><td>memory-bound</td><td>计算量相对访存量很小</td></tr>
</table>
</div>

<div class="card card-s">
<h3>串到 Prefill / Decode</h3>
<table>
<tr><th>阶段</th><th>计算形态</th><th>瓶颈</th><th>关键指标</th></tr>
<tr><td>Prefill</td><td>多 token 并行，大矩阵乘</td><td>compute-bound</td><td>TTFT</td></tr>
<tr><td>Decode</td><td>batch 小，GEMV，反复读权重</td><td>memory-bound</td><td>TPOT</td></tr>
</table>
<p>两阶段瓶颈相反，优化手段也相反：prefill 靠 chunked prefill、提高 TensorCore 利用率；decode 靠 continuous batching 摊销权重读取、靠 KV cache 量化和 PagedAttention 降带宽与显存压力。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 怎么判断一个 kernel 是 compute-bound 还是 memory-bound？</div>
<div class="qa-a"><p>算它的算术强度（FLOPs ÷ 访存 bytes），和机器平衡点（峰值算力 ÷ 峰值带宽）比较。高于平衡点就是 compute-bound，低于就是 memory-bound。比如 A100 平衡点 ≈ 312 TFLOPS / 2 TB/s ≈ 156 FLOP/byte，而 batch=1 decode 算术强度约为 1，远低于平衡点，是典型 memory-bound。</p></div>
</div>

## 面试回答

**30 秒版：**

Roofline 用算术强度把 Transformer 算子分成 compute-bound 和 memory-bound。 公式必须讲 FLOPs、bytes 和 ridge point。

**2 分钟版：**

我会先说明这个问题在 Transformer 与大模型基础 里的位置，再拆核心链路：输入是什么、系统如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：吞吐和延迟、显存和计算、隔离和利用率、简单实现和生产稳定性之间如何取舍。最后用观测指标或排障路径收束，说明如何判断方案真的有效。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

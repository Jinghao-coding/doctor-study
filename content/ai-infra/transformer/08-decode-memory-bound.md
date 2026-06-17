## 一句话结论

70B FP16 batch=1 decode 的算术强度约为 $1\,\mathrm{FLOP/byte}$，远低于 A100 平衡点，因此是 memory-bound。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Transformer 与大模型基础 |
| 章节类型 | 机制类（含公式） |
| 解决问题 | 围绕 Transformer 架构、计算量、Roofline、算子瓶颈和大模型推理/训练性能建立深度答案。 |
| 面试抓手 | 按计算量、访存量、算术强度三步算。 |

这一节用 Roofline 模型完整算清一个高频面试题：**70B FP16 模型在 A100 上 decode、batch=1、每次只生成 1 个 token，为什么是显存带宽瓶颈（memory-bound）而不是算力瓶颈？** 核心是三步——算计算量、算访存量、算算术强度，再和机器平衡点比较。

### 1. 为什么前向 FLOPs ≈ 2 × 参数量 × token 数

生成一个 token 时，模型里的权重基本都要参与一次矩阵乘。矩阵乘里一个权重参数通常对应一次乘法 + 一次加法：

$$ 1\text{ 个参数} \approx 2\text{ FLOPs} $$

所以：

$$ \text{FLOPs} \approx 2 \times \text{参数量} \times \text{生成 token 数} $$

70B 模型生成 1 个 token：

$$ 2 \times 70 \times 10^9 \times 1 = 1.4 \times 10^{11}\text{ FLOPs} = 140\text{ GFLOPs} $$

注意这是**每生成 1 个 token** 的计算量。

### 2. 为什么访存量 ≈ 140 GB

权重是 FP16，每个参数占 $2$ bytes：

$$ 70 \times 10^9 \times 2\text{ bytes} = 140 \times 10^9\text{ bytes} \approx 140\text{ GB} $$

在 batch=1 decode 时，每生成一个 token，都要把整套权重从 HBM 显存读一遍。关键反差是：**计算一个 token 只需 140 GFLOPs，但必须读 140 GB 权重。**

### 3. 算术强度怎么算

$$ \text{算术强度} = \frac{\text{计算量 FLOPs}}{\text{访存量 bytes}} = \frac{1.4 \times 10^{11}}{1.4 \times 10^{11}} = 1\text{ FLOP/byte} $$

含义：每从显存读取 1 byte，只能做约 1 次浮点运算。这个值非常低。

### 4. 为什么是 memory-bound

A100：理论算力约 $312$ TFLOPS，显存带宽约 $2$ TB/s。机器平衡点：

$$ \frac{312\text{ TFLOPS}}{2\text{ TB/s}} = 156\text{ FLOP/byte} $$

含义：一个任务的算术强度要达到 156 FLOP/byte，才可能把 A100 的计算单元喂饱。而 decode batch=1 只有 $1$ FLOP/byte，远小于 156，所以算力用不满，瓶颈是：

> 显存带宽不够快，权重读得太慢，计算单元大部分时间在等数据。

结论：**memory-bound**。

### 5. 换成时间直觉更好理解

**只看算力**：A100 算力 $312 \times 10^{12}$ FLOPs/s，算 1 个 token 需 $1.4 \times 10^{11}$ FLOPs：

$$ \frac{1.4 \times 10^{11}}{312 \times 10^{12}} \approx 0.45\text{ ms} $$

**看显存带宽**：读 $140$ GB 权重，带宽 $2$ TB/s = $2000$ GB/s：

$$ \frac{140\text{ GB}}{2000\text{ GB/s}} = 0.07\text{ s} = 70\text{ ms} $$

计算只要约 $0.45$ ms，读权重要约 $70$ ms，相差两个数量级。所以实际速度主要被显存带宽限制，而不是矩阵乘算力。

### 6. 核心结论

| 项目 | 数值 |
|---|---:|
| 参数量 | 70B |
| 权重精度 | FP16 |
| 每 token 计算量 | 约 140 GFLOPs |
| 每 token 访存量 | 约 140 GB |
| 算术强度 | 约 1 FLOP/byte |
| A100 平衡点 | 约 156 FLOP/byte |
| 结论 | memory-bound |

> batch=1 decode 时，每生成一个 token，计算量相对权重读取量太少，GPU 算力用不满，主要卡在显存带宽。

<div class="card card-d">
<h3>7. 为什么 batch 变大能改善</h3>
<p>batch 从 1 变成 $B$，同一份权重可以服务 $B$ 个 token。计算量约变成 $2 \times \text{参数量} \times B$，而权重读取仍近似 $\text{参数量} \times 2\text{ bytes}$，所以算术强度变成：</p>
<p>$$ \frac{2 \times \text{参数量} \times B}{2 \times \text{参数量}} = B\text{ FLOP/byte} $$</p>
<table>
<tr><th>batch</th><th>算术强度</th><th>状态</th></tr>
<tr><td>1</td><td>约 1 FLOP/byte</td><td>严重 memory-bound</td></tr>
<tr><td>8</td><td>约 8 FLOP/byte</td><td>仍 memory-bound</td></tr>
<tr><td>64</td><td>约 64 FLOP/byte</td><td>接近平衡点</td></tr>
<tr><td>156</td><td>约 156 FLOP/byte</td><td>接近 A100 平衡点，趋向 compute-bound</td></tr>
</table>
<div class="qa-summary">更大的 batch 复用权重、提高算术强度，让任务从 memory-bound 逐渐接近 compute-bound——这就是 continuous batching 提升吞吐的根本原因。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 一句话总结这道题。</div>
<div class="qa-a"><p>70B FP16 模型 batch=1 decode 每生成 1 个 token，需约 140 GFLOPs 计算，但要读约 140 GB 权重，算术强度只有 1 FLOP/byte，远低于 A100 的约 156 FLOP/byte 平衡点，所以瓶颈是显存带宽（memory-bound），不是 GPU 算力。加大 batch 复用权重可把算术强度提到约 $B$ FLOP/byte，逐渐趋向 compute-bound。</p></div>
</div>

## 面试回答

**30 秒版：**

70B FP16 batch=1 decode 的算术强度约为 $1\,\mathrm{FLOP/byte}$，远低于 A100 平衡点，因此是 memory-bound。 按计算量、访存量、算术强度三步算。

**2 分钟版：**

这道高频题问 70B FP16 模型在 A100 上 batch=1 decode、每次生成 1 个 token 为什么是 memory-bound，我按计算量、访存量、算术强度三步算。计算量：一个参数对应一次乘加约 2 FLOPs，FLOPs≈2×参数量×token 数，70B 生成 1 个 token 是 2×70×10^9≈140 GFLOPs。访存量：权重 FP16 每参数 2 bytes，70×10^9×2=140 GB，batch=1 时每生成一个 token 都要把整套权重从 HBM 读一遍。算术强度=140 GFLOPs÷140 GB≈1 FLOP/byte，即每读 1 byte 只做约 1 次浮点运算。A100 平衡点是 312 TFLOPS÷2 TB/s=156 FLOP/byte，要 156 才能喂饱计算单元，而 decode 只有 1，远低于 156，所以算力用不满、卡在显存带宽。换成时间直觉更清楚：纯算力算一个 token 约 0.45 ms，但读 140 GB 权重要约 70 ms，差两个数量级，主要被带宽限制。落点是 batch 变大能改善：batch=B 时同一份权重服务 B 个 token，算术强度变成约 B FLOP/byte，逐渐趋向 compute-bound，这正是 continuous batching 提升吞吐的根本原因。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

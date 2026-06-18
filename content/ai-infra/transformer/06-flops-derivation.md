## 一句话结论

单层 Transformer FLOPs 可以拆成线性层的 $nd^2$ 项和 attention 的 $n^2d$ 项。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Transformer 与大模型基础 |
| 章节类型 | 机制类（含公式） |
| 解决问题 | 围绕 Transformer 架构、计算量、Roofline、算子瓶颈和大模型推理/训练性能建立深度答案。 |
| 面试抓手 | 记住矩阵乘 $2MNK$，再数 QKV、输出投影、FFN 和两次 attention matmul。 |

先不用一上来背公式，而是把单层 Transformer 的计算量理解成两类：一类是各种线性层带来的 $nd^2$ 项，另一类是 Attention 两次大矩阵乘带来的 $n^2d$ 项。最终结论是：

$$ \text{总FLOPs} = 24nd^2 + 4n^2d $$

下面一步步推出它。

### 1. 单层主要算两件事

一个 Transformer Encoder Layer 主要包括 Self-Attention 和 FFN（前馈网络）两部分，所以：

$$ \text{总FLOPs} = \text{Attention 的 FLOPs} + \text{FFN 的 FLOPs} $$

### 2. 先理解矩阵乘法为什么是 $2MNK$

两个矩阵相乘：

$$ A_{M \times N} \times B_{N \times K} = C_{M \times K} $$

输出矩阵 $C$ 有 $M \times K$ 个元素，每个元素是一次长度为 $N$ 的向量点积：

$$ c_{ij} = a_{i1}b_{1j} + a_{i2}b_{2j} + \dots + a_{iN}b_{Nj} $$

一个元素约需 $N$ 次乘法 + $N$ 次加法 = $2N$ 次运算，共 $M \times K$ 个元素，所以：

$$ \text{FLOPs} = 2MNK $$

这是后面所有推导的基础。

### 3. Attention 部分

设输入 $X \in \mathbb{R}^{n \times d}$，其中 $n$ 是 token 数，$d$ 是每个 token 的向量维度。

**3.1 QKV 投影：$6nd^2$**

输入 $X$ 分别乘三个权重得到 Q、K、V：

$$ Q = XW_Q,\quad K = XW_K,\quad V = XW_V $$

其中 $X$ 是 $n \times d$，$W_Q, W_K, W_V$ 是 $d \times d$。一次投影是 $n \times d$ 乘 $d \times d$，按 $2MNK$（$M=n, N=d, K=d$）得 $2nd^2$。三次合计：

$$ 3 \times 2nd^2 = 6nd^2 $$

**3.2 计算 $QK^\top$：$2n^2d$**

Q 是 $n \times d$，$K^\top$ 是 $d \times n$，相乘得到 $n \times n$ 的注意力矩阵。按 $2MNK$（$M=n, N=d, K=n$）：

$$ 2 \times n \times d \times n = 2n^2 d $$

$n^2$ 的来源很关键：每个 token 都要和每个 token 算相关性，产生一个 $n \times n$ 矩阵。

**3.3 注意力权重乘 V：$2n^2d$**

Softmax 后的权重矩阵是 $n \times n$，V 是 $n \times d$，相乘得到 $n \times d$。按 $2MNK$（$M=n, N=n, K=d$）：

$$ 2 \times n \times n \times d = 2n^2 d $$

**3.4 输出投影：$2nd^2$**

Attention 输出后再过一个输出线性层，$n \times d$ 乘 $d \times d$，得 $2nd^2$。

**3.5 Attention 总和**

| 步骤 | FLOPs |
|---|---:|
| QKV 投影 | $6nd^2$ |
| $QK^\top$ | $2n^2d$ |
| 权重乘 V | $2n^2d$ |
| 输出投影 | $2nd^2$ |

$$ \text{Attention} = 6nd^2 + 2n^2d + 2n^2d + 2nd^2 = 8nd^2 + 4n^2d $$

### 4. FFN 部分

FFN 是两层线性层，维度变化 $d \rightarrow 4d \rightarrow d$。

**4.1 第一层 $d \rightarrow 4d$**：输入 $n \times d$，权重 $d \times 4d$：

$$ 2 \times n \times d \times 4d = 8nd^2 $$

**4.2 第二层 $4d \rightarrow d$**：输入 $n \times 4d$，权重 $4d \times d$：

$$ 2 \times n \times 4d \times d = 8nd^2 $$

**4.3 FFN 总和**：

$$ \text{FFN} = 8nd^2 + 8nd^2 = 16nd^2 $$

### 5. 合起来

$$ \text{Attention} = 8nd^2 + 4n^2d,\qquad \text{FFN} = 16nd^2 $$

$$ \text{总FLOPs} = 8nd^2 + 4n^2d + 16nd^2 = 24nd^2 + 4n^2d $$

### 6. 一句话理解

> Transformer 单层的计算量由两部分组成：线性层带来的 $nd^2$，和 Attention 两次大矩阵乘带来的 $n^2d$。

- $24nd^2$：来自 QKV 投影、输出投影、FFN；
- $4n^2d$：来自 $QK^\top$ 和注意力权重乘 V。

当 $n \ll d$ 时线性层（$nd^2$）占主导；当 $n$ 很大时注意力的 $n^2d$ 项成为瓶颈。

<div class="card card-w">
<h3>最容易卡住的点：为什么 $QK^\top$ 是 $2n^2d$</h3>
<p>如果卡在这一步，可以这样想：有 $n$ 个 query、$n$ 个 key，每个 query 都要和每个 key 算一次相似度，所以一共 $n\times n$ 个相似度；每个相似度是两个 $d$ 维向量点积，约 $2d$ 次运算；总共 $n\times n\times 2d = 2n^2d$。</p>
<div class="qa-summary">这就是 Attention 对序列长度是平方复杂度（$O(n^2)$）的根本原因，也是长上下文和 FlashAttention 要解决的核心问题。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 现场默写单层 Transformer 的 FLOPs，你怎么快速推？</div>
<div class="qa-a"><p>只记一个基本公式 $2MNK$，然后数有几个矩阵乘：QKV 三次投影 + 输出投影是 4 个 $n\times d$ 乘 $d\times d$，各 $2nd^2$，合 $8nd^2$；FFN 两层是 $8nd^2 \times 2 = 16nd^2$；这两类都是 $nd^2$，合 $24nd^2$。再加注意力两次大矩阵乘 $QK^\top$ 和权重乘 V，各 $2n^2d$，合 $4n^2d$。最终 $24nd^2 + 4n^2d$。整模型再乘层数，训练含反向约再 ×3。</p></div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

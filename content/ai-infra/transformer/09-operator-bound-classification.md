## 一句话结论

Transformer 不是整体只有一种瓶颈，prefill/decode、GEMM/softmax/layernorm/embedding 的 bound 类型不同。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Transformer 与大模型基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕 Transformer 架构、计算量、Roofline、算子瓶颈和大模型推理/训练性能建立深度答案。 |
| 面试抓手 | 按算子分类，避免“一句话说全模型 compute-bound”。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

判断一个算子是 compute-bound 还是 memory-bound，核心看算术强度：

$$ \text{算术强度} = \frac{\text{FLOPs}}{\text{访存 bytes}} $$

算术强度高于机器平衡点（A100 ≈ $\frac{312\text{ TFLOPS}}{2\text{ TB/s}} \approx 156$ FLOP/byte）就 compute-bound，远低于就 memory-bound。下面把 Transformer 各算子按这个标准过一遍。

<div class="card card-w">
<h3>一句话记忆</h3>
<p><strong>大而方的矩阵乘通常 compute-bound；小 batch、单 token、逐元素操作、归一化、softmax、KV cache 读写通常 memory-bound。</strong></p>
<ul>
<li><strong>Prefill</strong>：大量 token 并行，GEMM 大、权重复用充分 → 偏 compute-bound。</li>
<li><strong>Decode batch=1</strong>：每次只生成一个 token，反复读权重和 KV cache → 偏 memory-bound。</li>
<li><strong>Elementwise / reduction</strong>（LayerNorm、RMSNorm、Residual、RoPE、Softmax）→ 多数 memory-bound。</li>
<li><strong>多卡通信</strong>（AllReduce、AllGather）→ communication-bound，不属于单卡 compute/memory 二分。</li>
</ul>
</div>

<div class="card card-s">
<h3>逐算子细分类（Prefill vs Decode batch=1）</h3>
<table>
<tr><th>组件</th><th>Prefill</th><th>Decode batch=1</th><th>说明</th></tr>
<tr><td>QKV / 输出投影</td><td>compute-bound</td><td>memory-bound（GEMV）</td><td>decode 权重复用差</td></tr>
<tr><td>FFN up/gate/down</td><td>compute-bound</td><td>memory-bound（GEMV）</td><td>FFN 参数量大，decode 读权重成本高</td></tr>
<tr><td>$QK^\top$ score</td><td>compute-bound</td><td>memory-bound</td><td>decode 扫 K cache</td></tr>
<tr><td>Attention × V</td><td>compute-bound</td><td>memory-bound</td><td>decode 扫 V cache</td></tr>
<tr><td>Softmax</td><td>memory/latency-bound</td><td>memory/latency-bound</td><td>reduction + exp，复用低</td></tr>
<tr><td>LayerNorm / RMSNorm</td><td>memory-bound</td><td>memory-bound</td><td>逐元素 + reduction</td></tr>
<tr><td>Residual add</td><td>memory-bound</td><td>memory-bound</td><td>几乎纯读写</td></tr>
<tr><td>RoPE</td><td>memory-bound</td><td>memory-bound</td><td>elementwise</td></tr>
<tr><td>激活 GELU/SiLU</td><td>memory-bound</td><td>memory-bound</td><td>可与 GEMM 融合</td></tr>
<tr><td>Embedding lookup</td><td>memory-bound</td><td>memory-bound</td><td>查表，几乎无计算</td></tr>
<tr><td>KV cache 写</td><td>memory-bound</td><td>memory-bound</td><td>纯写显存</td></tr>
<tr><td>KV cache 读</td><td>不突出</td><td>memory-bound</td><td>decode 核心瓶颈</td></tr>
<tr><td>LM head</td><td>compute / memory</td><td>多偏 memory-bound</td><td>取决于 batch/vocab</td></tr>
<tr><td>Sampling / top-k/p</td><td>latency/memory-bound</td><td>latency/memory-bound</td><td>非大矩阵乘</td></tr>
<tr><td>AllReduce / AllGather</td><td colspan="2">communication-bound</td><td>多卡通信瓶颈</td></tr>
</table>
</div>

<div class="card card-m">
<h3>为什么大矩阵乘是 compute-bound</h3>
<p>QKV/输出投影、FFN 两层、LM head 本质都是 $Y=XW$。矩阵乘 $[M,K]\times[K,N]$ 计算量约 $2MKN$，访存量约 $MK+KN+MN$。当 $M,N,K$ 都大时 FLOPs 增长远快于访存，数据复用高，算术强度高 → compute-bound，能喂饱 TensorCore。</p>
<p><strong>但 decode batch=1 时退化</strong>：输入变成"瘦"矩阵 $[1,H]$，权重 $[H,H]$ 几乎没有 batch 维复用，每层大量时间花在从 HBM 读 $W_q,W_k,W_v,W_o,W_{up},W_{gate},W_{down}$ → 转为 memory-bound。这正是 70B FP16（权重约 140GB）单 token decode memory-bound 的根因。</p>
</div>

<div class="card card-d">
<h3>Attention 在两阶段的瓶颈相反</h3>
<p><strong>Prefill</strong>：处理整段 prompt，$QK^\top$ 形状 $[B,h,S,D]\times[B,h,D,S]\to[B,h,S,S]$，计算量 $O(B\cdot h\cdot S^2\cdot D)$，$S$ 大时是大矩阵乘 → compute-bound。FlashAttention 减少 attention matrix 的 HBM 读写后更接近高效 GEMM。</p>
<p><strong>Decode</strong>：query 长度为 1（$[B,h,1,D]$），但要扫历史 KV cache（$[B,h,S,D]$）。每个新 token 都要从 HBM 读大量 K/V，但每个元素参与计算很少 → memory-bound。这就是长上下文 decode 越来越慢的原因：不是单 token 计算爆炸，而是每步要读更长的 KV cache。</p>
</div>

<div class="card card-s">
<h3>为什么逐元素/归一化类必然 memory-bound</h3>
<p>以 Residual add $y=x+f(x)$ 为例（FP16）：读 $x$、读 $f(x)$、写 $y$ 共约 6 bytes，只做 1 FLOP，算术强度约 $\frac{1}{6}$ FLOP/byte，远低于 156 → 必然 memory-bound。LayerNorm/RMSNorm、RoPE、Embedding lookup、Softmax 同理：计算量相对访存量都很小。工程上常把它们与相邻 GEMM 融合（kernel fusion）来减少 HBM 往返。</p>
</div>

<div class="card card-m">
<h3>训练 vs 推理</h3>
<p><strong>训练</strong>：大部分时间在大矩阵乘（forward GEMM、backward input/weight GEMM）→ compute-bound；但 optimizer step（如 Adam 更新 $m,v$）要读写 parameter/gradient/m/v 多份状态，每参数计算有限 → memory-bound。</p>
<p><strong>推理</strong>：prefill 偏 compute-bound，decode 偏 memory-bound——这是 LLM serving 最重要的区别，也决定了 prefill/decode 分离部署、continuous batching 等优化方向。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 同一个 FFN，为什么 prefill 是 compute-bound，decode 却 memory-bound？</div>
<div class="qa-a"><p>看权重复用。prefill 一次处理 $B\times S$ 个 token，同一份 FFN 权重被大量 token 复用，算术强度高；decode batch=1 每次只过 1 个 token，权重几乎零复用，时间几乎全花在从 HBM 读那两层大权重上，算术强度掉到接近 GEMV 水平 → memory-bound。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么长上下文 decode 越来越慢？</div>
<div class="qa-a"><p>不是单 token 计算复杂度爆炸，而是 decode attention 是 memory-bound 的，每生成一个新 token 都要从 HBM 读一遍历史 KV cache。上下文越长，KV cache 越大，每步读取量线性增长，所以越来越慢。优化方向是降 KV cache 带宽/容量压力：PagedAttention、KV cache 量化、MQA/GQA、FlashAttention 等。</p></div>
</div>

## 面试回答

**30 秒版：**

Transformer 不是整体只有一种瓶颈，prefill/decode、GEMM/softmax/layernorm/embedding 的 bound 类型不同。 按算子分类，避免“一句话说全模型 compute-bound”。

**2 分钟版：**

我会先说明这个问题在 Transformer 与大模型基础 里的位置，再拆核心链路：输入是什么、系统如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：吞吐和延迟、显存和计算、隔离和利用率、简单实现和生产稳定性之间如何取舍。最后用观测指标或排障路径收束，说明如何判断方案真的有效。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

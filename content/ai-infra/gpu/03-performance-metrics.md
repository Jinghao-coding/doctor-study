## 一句话结论

GPU 性能指标要按“算力、显存、利用率、互联、能耗”五条线理解，再用 Roofline 把 kernel 归类为 compute-bound 或 memory-bound。面试中最重要的判断是：不要把理论 TFLOPS、GPU-Util 或显存占用单独当成“性能好”的证据。

## 核心概念

| 指标族 | 代表指标 | 回答什么问题 | 常见误区 |
|---|---|---|---|
| 算力 | TFLOPS、TOPS、Tensor Core Util | 计算单元的理论上限和实际吞吐 | 理论峰值不等于模型实际速度 |
| 显存带宽 | HBM GB/s、Memory Throughput | 数据能否及时喂给计算单元 | 显存容量和显存带宽不是一回事 |
| 显存容量 | VRAM used、peak active memory | 模型、激活、KV cache 能不能放下 | 显存占用高不代表 GPU 利用率高 |
| 利用率 | GPU-Util、SM Active、Occupancy | 时间上是否有活、空间上是否铺满 | GPU-Util 高不代表忙得有效 |
| 互联 | PCIe、NVLink、IB/RDMA、NCCL 时间 | 多卡和跨机通信是否拖慢 | 单卡指标无法解释多卡扩展效率 |
| 能耗 | Power、tokens/J、TFLOPS/W | 成本、供电、散热和能效 | 只看吞吐不看 TCO |

<div class="card card-m">
<h3>GPU 性能指标全景</h3>
<p>GPU 性能优化不要只看一个指标。面试中最好按“算力、显存、利用率、互联、能耗”五条线回答，然后用 Roofline 判断瓶颈。</p>
<div class="metric-map">
<div class="metric-card"><div class="metric-name">算力</div><div class="metric-value">TFLOPS / TOPS</div><p>衡量计算峰值和实际计算吞吐。关注理论峰值、实际 TFLOPS、Tensor Core 是否被用上。</p></div>
<div class="metric-card"><div class="metric-name">显存带宽</div><div class="metric-value">GB/s · TB/s</div><p>衡量 HBM 读写速度。Softmax、LayerNorm、KV Cache 读取通常更受带宽限制。</p></div>
<div class="metric-card"><div class="metric-name">显存容量</div><div class="metric-value">GB</div><p>决定模型权重、优化器状态、激活值和 KV Cache 能不能放下。</p></div>
<div class="metric-card"><div class="metric-name">利用率</div><div class="metric-value">SM Active · Occupancy</div><p>用于判断 GPU 是否在忙，但不能单独代表模型效率或吞吐。</p></div>
<div class="metric-card"><div class="metric-name">互联</div><div class="metric-value">NVLink · PCIe · IB</div><p>决定多卡训练、张量并行、流水并行和跨节点通信效率。</p></div>
<div class="metric-card"><div class="metric-name">能耗</div><div class="metric-value">Watt · tokens/J</div><p>数据中心场景必须关注功耗、散热、供电和单位吞吐成本。</p></div>
</div>
</div>

<div class="card card-s">
<h3>指标之间的关系图</h3>
<p>可以用下面这条链路理解性能指标：模型工作负载先决定计算量和访存量，再被 GPU 的算力、带宽、容量和互联约束，最终表现为吞吐、延迟和成本。</p>
<div class="metric-flow">
<svg viewBox="0 0 1040 360" role="img" aria-label="GPU performance metrics relation">
<defs>
<marker id="metricArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
<path d="M0,0 L0,6 L9,3 z" fill="var(--border, #dbe4f0)"></path>
</marker>
</defs>
<rect x="35" y="95" width="170" height="95" rx="14" class="metric-node workload" fill="var(--card-solid, #ffffff)" stroke="var(--pri, #2563eb)" stroke-opacity=".42" stroke-width="1.5"></rect>
<text x="62" y="132" class="metric-label" fill="var(--txt, #172033)">Workload</text>
<text x="62" y="156" class="metric-desc" fill="var(--muted, #667085)">FLOPs / Bytes</text>
<text x="62" y="176" class="metric-desc" fill="var(--muted, #667085)">batch · seq · shape</text>

<rect x="290" y="45" width="170" height="85" rx="14" class="metric-node compute" fill="var(--card-solid, #ffffff)" stroke="var(--sec, #059669)" stroke-opacity=".42" stroke-width="1.5"></rect>
<text x="318" y="80" class="metric-label" fill="var(--txt, #172033)">Compute Roof</text>
<text x="318" y="104" class="metric-desc" fill="var(--muted, #667085)">TFLOPS / Tensor Core</text>

<rect x="290" y="165" width="170" height="85" rx="14" class="metric-node memory" fill="var(--card-solid, #ffffff)" stroke="var(--warn, #d97706)" stroke-opacity=".42" stroke-width="1.5"></rect>
<text x="318" y="200" class="metric-label" fill="var(--txt, #172033)">Memory Roof</text>
<text x="318" y="224" class="metric-desc" fill="var(--muted, #667085)">HBM bandwidth / capacity</text>

<rect x="540" y="95" width="170" height="95" rx="14" class="metric-node interconnect" fill="var(--card-solid, #ffffff)" stroke="var(--acc, #7c3aed)" stroke-opacity=".42" stroke-width="1.5"></rect>
<text x="568" y="132" class="metric-label" fill="var(--txt, #172033)">Communication</text>
<text x="568" y="156" class="metric-desc" fill="var(--muted, #667085)">NVLink / PCIe / IB</text>
<text x="568" y="176" class="metric-desc" fill="var(--muted, #667085)">AllReduce · KV transfer</text>

<rect x="795" y="95" width="190" height="95" rx="14" class="metric-node output" fill="var(--card-solid, #ffffff)" stroke="var(--danger, #dc2626)" stroke-opacity=".42" stroke-width="1.5"></rect>
<text x="823" y="132" class="metric-label" fill="var(--txt, #172033)">Observed Result</text>
<text x="823" y="156" class="metric-desc" fill="var(--muted, #667085)">throughput · latency</text>
<text x="823" y="176" class="metric-desc" fill="var(--muted, #667085)">cost · utilization</text>

<path d="M205 142 C242 142 250 88 290 88" class="metric-arrow" stroke="var(--border, #dbe4f0)" stroke-width="1.8" fill="none" marker-end="url(#metricArrow)"></path>
<path d="M205 142 C242 142 250 208 290 208" class="metric-arrow" stroke="var(--border, #dbe4f0)" stroke-width="1.8" fill="none" marker-end="url(#metricArrow)"></path>
<path d="M460 88 C500 88 505 142 540 142" class="metric-arrow" stroke="var(--border, #dbe4f0)" stroke-width="1.8" fill="none" marker-end="url(#metricArrow)"></path>
<path d="M460 208 C500 208 505 142 540 142" class="metric-arrow" stroke="var(--border, #dbe4f0)" stroke-width="1.8" fill="none" marker-end="url(#metricArrow)"></path>
<path d="M710 142 C750 142 755 142 795 142" class="metric-arrow" stroke="var(--border, #dbe4f0)" stroke-width="1.8" fill="none" marker-end="url(#metricArrow)"></path>
<text x="300" y="314" class="metric-note" fill="var(--muted, #667085)">Roofline 判断：Arithmetic Intensity = FLOPs / Bytes；低于 ridge point 多半 memory-bound，高于 ridge point 才可能 compute-bound。</text>
</svg>
</div>
</div>

<div class="card card-s">
<h3>计算性能：TFLOPS 不是实际速度</h3>
<p>TFLOPS 是每秒浮点运算次数。厂商宣传的 A100 FP16 312 TFLOPS、H100 FP16 989 TFLOPS 都是理想条件下 Tensor Core 的理论峰值，真实模型通常达不到。</p>
<table>
<tr><th>精度</th><th>A100 理论峰值</th><th>H100 理论峰值</th><th>典型场景</th></tr>
<tr><td>FP64</td><td>9.7 TFLOPS</td><td>34 TFLOPS</td><td>科学计算，AI 训练较少使用</td></tr>
<tr><td>FP32</td><td>19.5 TFLOPS</td><td>67 TFLOPS</td><td>通用 CUDA 计算</td></tr>
<tr><td>TF32</td><td>156 TFLOPS</td><td>494 TFLOPS</td><td>Tensor Core 加速的 FP32 训练</td></tr>
<tr><td>FP16/BF16</td><td>312 TFLOPS</td><td>989 TFLOPS</td><td>混合精度训练、主流 LLM 训练</td></tr>
<tr><td>FP8</td><td>不支持</td><td>1979 TFLOPS</td><td>H100 Transformer Engine，推理和部分训练</td></tr>
<tr><td>INT8</td><td>624 TOPS</td><td>3958 TOPS</td><td>量化推理，吞吐优先</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">怎么估算理论峰值</div><p>简化理解：理论峰值 ≈ SM 数量 × 每个周期可完成的矩阵运算量 × 频率。Tensor Core 是矩阵乘加专用单元，所以 FP16/BF16/FP8 峰值远高于普通 FP32 CUDA Core。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么实际值低</div><p>真实模型会受到 HBM 带宽、kernel launch、算子碎片、通信等待、数据依赖、batch/shape 不规则和 Tensor Core 对齐条件影响。实际 TFLOPS 通常需要用 Nsight Compute、框架 profiler 或 MFU 估算。</p></div>
</div>

<div class="card card-d">
<h3>Roofline 模型：判断 kernel 是缺算力还是缺数据</h3>
<p>完整的 Roofline 模型定义、公式和图已经统一放在 <strong>性能预测与建模 / Roofline Model</strong>。本页只保留 GPU 指标视角：Roofline 用来把 kernel 的 FLOPs、Bytes、实际吞吐和硬件峰值放在一张图里，判断瓶颈是算力、显存带宽还是其他因素。</p>
<table>
<tr><th>要看什么</th><th>指标来源</th><th>说明</th></tr>
<tr><td>Arithmetic Intensity</td><td>FLOPs / Bytes</td><td>低于 ridge point 通常偏 memory-bound</td></tr>
<tr><td>Achieved FLOP/s</td><td>Nsight Compute / profiler</td><td>距离 compute roof 有多远</td></tr>
<tr><td>Memory Throughput</td><td>Nsight / DCGM</td><td>是否接近 HBM roof</td></tr>
<tr><td>Roofline 位置</td><td>Nsight Compute Roofline chart</td><td>判断优化方向：减少访存还是提高计算吞吐</td></tr>
</table>

<div class="qa-section"><div class="qa-section-title">Roofline 和 GPU Utilization 的关系</div>
<p><code>nvidia-smi GPU-Util</code> 只能告诉你 GPU 上有没有 kernel 在跑，Roofline 更进一步问：这个 kernel 的性能离硬件理论上限有多远？它是被内存带宽限制还是被计算峰值限制？所以 <strong>GPU Utilization 高不代表接近 Roofline</strong>。可能出现 GPU-Util = 100% 但 kernel 在 Roofline 图上离屋顶很远，原因可能是访存不合并、cache miss、occupancy 低、warp stall、Tensor Core 没用上、指令依赖、分支发散、kernel 太小等。</p>
</div>

<div class="qa-section"><div class="qa-section-title">怎么获取 Roofline？</div>
<p>Nsight Compute 支持 Roofline 分析，常见做法：</p>
<pre><code class="language-bash">ncu --set full ./your_program
# 或使用带 Roofline 的 section
ncu --section SpeedOfLight_RooflineChart ./your_program</code></pre>
<p>然后在 Nsight Compute UI 里看 Roofline 图，它通常会展示 arithmetic intensity、achieved FLOP/s、memory roof、compute roof、kernel 点位，以及 FP32 / FP64 / Tensor Core 等不同 roof。也可以手动估算：Arithmetic Intensity = FLOPs / Bytes，Achieved Performance = FLOPs / Kernel Time，Memory Bandwidth Used = Bytes / Kernel Time，然后对比硬件峰值。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么是 Roofline 模型？面试怎么回答？</div>
<div class="qa-a">
<p>Roofline 模型完整解释统一看 <strong>性能预测与建模 / Roofline Model</strong>。在 GPU 指标页里，我会把它作为诊断工具：先估 FLOPs 和 Bytes，算 Arithmetic Intensity，再和硬件 ridge point 比较，判断热点 kernel 是 memory-bound 还是 compute-bound。</p>
<div class="qa-summary">本页只记用途：Roofline 把 GPU 性能指标收敛成“缺数据还是缺算力”。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 Transformer 的 Attention 经常是瓶颈？</div>
<div class="qa-a"><p>Self-Attention 的 QK^T 计算量随序列长度平方增长，同时需要频繁读写 Q、K、V 和 attention score。FlashAttention 的核心价值不是只减少 FLOPs，而是通过分块、在线 softmax 和重计算减少 HBM 读写。</p></div>
</div>

</div>

<div class="card card-w">
<h3>GPU 利用率：高 Util 不等于高效率</h3>
<p><code>nvidia-smi</code> 的 GPU Utilization 表示采样窗口内 GPU 是否有 kernel 活跃，不能代表 Tensor Core 利用率、真实 TFLOPS 或端到端吞吐。</p>
<table>
<tr><th>指标</th><th>主要来源</th><th>真正含义</th><th>常见误区</th></tr>
<tr><td>GPU Utilization</td><td><code>nvidia-smi</code></td><td>采样周期内至少有 kernel 在执行的时间比例</td><td>100% 可能只是小 kernel 很密集，不代表算力打满</td></tr>
<tr><td>SM Active</td><td>DCGM / Nsight</td><td>SM 有活跃 warp 的时间比例</td><td>SM 忙不等于 Tensor Core 高效工作</td></tr>
<tr><td>Tensor Core Util</td><td>Nsight Compute</td><td>Tensor Core 管线使用程度</td><td>FP32 或 shape 不对齐时可能很低</td></tr>
<tr><td>Occupancy</td><td>Nsight Compute</td><td>每个 SM 上可驻留 warp 与理论上限的比例</td><td>高 occupancy 不一定高性能，低 occupancy 也可能是合理的寄存器/共享内存权衡</td></tr>
<tr><td>Memory Throughput</td><td>Nsight / DCGM</td><td>HBM 带宽使用情况</td><td>高带宽可能说明 memory-bound，不一定是好事</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: nvidia-smi 显示 GPU Util 100%，但训练很慢，为什么？</div>
<div class="qa-a"><p>可能是小 kernel 频繁启动、Tensor Core 没用上、CPU 数据加载慢、H2D/D2H 拷贝等待、多卡 NCCL 通信等待，或者模型本身 memory-bound。排查时要结合 Nsight Systems 看 timeline，再用 Nsight Compute 看单个 kernel 的 Tensor Core、SM、HBM 指标。</p></div>
</div>
</div>

<div class="card card-d">
<h3>多卡互联性能指标</h3>
<p>多 GPU 训练/推理时，互联决定扩展效率。节点内优先看 NVLink/NVSwitch，节点间看 InfiniBand/RoCE 和 NCCL 拓扑。</p>
<table>
<tr><th>互联方式</th><th>典型带宽</th><th>拓扑</th><th>主要影响</th></tr>
<tr><td>NVLink 3.0</td><td>A100 约 300 GB/s</td><td>GPU 点对点或经 NVSwitch</td><td>单机多卡 all-reduce、张量并行</td></tr>
<tr><td>NVLink 4.0</td><td>H100 约 450 GB/s</td><td>GPU 点对点或经 NVSwitch</td><td>Hopper 单机扩展效率</td></tr>
<tr><td>NVSwitch</td><td>高聚合带宽</td><td>单节点内近似全互联</td><td>降低拓扑不均衡影响</td></tr>
<tr><td>PCIe 4.0 x16</td><td>约 32 GB/s 单向</td><td>树形，经 CPU 或 PCIe Switch</td><td>CPU-GPU 拷贝、无 NVLink 卡间通信</td></tr>
<tr><td>PCIe 5.0 x16</td><td>约 64 GB/s 单向</td><td>树形</td><td>新一代 CPU-GPU 互联</td></tr>
<tr><td>InfiniBand NDR</td><td>400 Gbps = 50 GB/s</td><td>跨节点网络</td><td>多节点 all-reduce、参数同步</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">扩展效率</div><p>线性扩展效率 = 多卡实际吞吐 /（单卡吞吐 × 卡数）。节点间扩展效率通常低于单节点，因为跨节点带宽和延迟远不如 NVLink/NVSwitch。</p></div>
</div>

<div class="card card-r">
<h3>面试高频：如何判断瓶颈</h3>
<div class="diag-grid">
<div class="diag-item"><strong>SM Active 高 + HBM 高</strong><span>GPU 忙且大量访存，进一步看 Tensor Core 和 Roofline。</span></div>
<div class="diag-item"><strong>SM Active 低 + HBM 高</strong><span>典型 memory-bound，优化访存、融合算子、减少 KV/激活读写。</span></div>
<div class="diag-item"><strong>SM Active 低 + HBM 低</strong><span>GPU 没被喂饱，查 CPU、DataLoader、I/O、网络、调度等待。</span></div>
<div class="diag-item"><strong>GPU Util 高 + TFLOPS 低</strong><span>可能是小 kernel、Tensor Core 未使用、shape 不对齐或通信 kernel 占比高。</span></div>
<div class="diag-item"><strong>单卡快 + 多卡慢</strong><span>查 NCCL、拓扑、IB/RDMA、梯度 bucket、通信计算 overlap。</span></div>
<div class="diag-item"><strong>显存够但仍慢</strong><span>容量不是瓶颈，可能是带宽、NUMA、PCIe、page cache 或数据 pipeline。</span></div>
</div>
</div>

<div class="card card-r">
<h3>GPU 性能面试题</h3>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何计算一个模型训练需要多少显存？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先把显存拆成“模型状态 + 激活值 + 临时开销”，再说明不同优化策略会减少哪一部分。</p>
<div class="qa-section"><div class="qa-section-title">1. 模型状态</div><p>包括参数、梯度和优化器状态。以 Adam + FP16 混合精度为例，常用粗估是每个参数约 16 bytes：FP16 参数 2 bytes、FP16 梯度 2 bytes、FP32 master weight 4 bytes、Adam 一阶动量 4 bytes、二阶动量 4 bytes。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 激活值</div><p>激活值和 batch size、sequence length、hidden size、层数强相关，训练时需要保留中间结果用于反向传播。长序列 LLM 里，激活值经常比直觉中更大。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 临时开销</div><p>还要预留 CUDA workspace、attention score / KV cache、中间 tensor、通信 buffer、内存碎片等。实际跑训练时不能把显存算到 100%，通常要留安全余量。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 优化手段</div><p>ZeRO/FSDP 主要切分参数、梯度和优化器状态；activation checkpointing 通过重计算降低激活值；offload 把部分状态放到 CPU 或 NVMe；混合精度和量化降低单个元素字节数。</p></div>
<div class="qa-summary">面试口径：显存 ≈ 模型状态 + 激活值 + 临时 workspace/通信 buffer。Adam + FP16 可先按参数量 × 16 bytes 粗估模型状态，再叠加激活值和安全余量。</div>
</div>
</div>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: A100 和 H100 的主要区别是什么？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>不要只背参数表，建议按“架构、算力、显存/带宽、互联、软件特性、部署代价”来讲。</p>
<div class="qa-section"><div class="qa-section-title">1. 架构代际</div><p>A100 是 Ampere 架构，H100 是 Hopper 架构。H100 面向大模型训练和推理做了更多专用优化。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 计算能力</div><p>H100 的 FP16/BF16 Tensor Core 峰值明显高于 A100，并新增 FP8 Transformer Engine。对 LLM 训练和推理来说，FP8 能在合适场景下提升吞吐和降低显存占用。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 显存与带宽</div><p>A100 80GB 使用 HBM2e，H100 80GB 使用 HBM3，H100 显存带宽更高。带宽提升对 memory-bound 算子、attention、KV cache 读取很重要。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 互联与扩展</div><p>H100 支持更高代际的 NVLink/NVSwitch，单机多卡和多机训练的通信效率更好，适合大规模并行训练。</p></div>
<div class="qa-section"><div class="qa-section-title">5. 工程代价</div><p>H100 性能更强，但功耗、散热、供电和采购成本也更高。数据中心部署时要看机房能力、网络拓扑和整体 TCO，而不是只看单卡峰值。</p></div>
<div class="qa-summary">面试口径：H100 相比 A100 的核心升级是 Hopper 架构、FP8/Transformer Engine、更高 Tensor Core 算力、更高 HBM 带宽和更强互联；代价是功耗和部署要求更高。</div>
</div>
</div>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Tensor Core 为什么比 CUDA Core 快？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>本质区别是 CUDA Core 做通用标量/向量运算，Tensor Core 是矩阵乘加专用单元，专门加速深度学习里的 GEMM。</p>
<div class="qa-section"><div class="qa-section-title">1. 硬件定位不同</div><p>CUDA Core 更通用，适合执行标量或向量 FMA；Tensor Core 面向矩阵块乘加，可以在一个周期内完成小矩阵 tile 的大量乘加操作。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 工作负载匹配</div><p>神经网络里的 Linear、卷积、QKV projection、MLP、attention projection 最终都能转成矩阵乘。Tensor Core 正好针对这些高密度矩阵乘做了硬件加速。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 精度与吞吐权衡</div><p>Tensor Core 通常使用 TF32、FP16、BF16、FP8、INT8 等精度格式，通过降低数据位宽和专用矩阵管线换取更高吞吐。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 使用条件</div><p>并不是所有算子都会自动高效使用 Tensor Core。shape 对齐、数据类型、矩阵维度、框架 kernel 选择都会影响 Tensor Core 利用率。</p></div>
<div class="qa-summary">面试口径：Tensor Core 快是因为它不是“更快的 CUDA Core”，而是矩阵乘加专用硬件；深度学习核心算子大量是 GEMM，所以能获得数量级更高的吞吐。</div>
</div>
</div>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Memory Coalescing 是什么？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>Memory Coalescing 讨论的是一个 warp 内的内存访问能不能合并成少量连续内存事务。</p>
<div class="qa-section"><div class="qa-section-title">1. 基本定义</div><p>GPU 以 warp 为单位调度线程。如果同一个 warp 里的相邻线程访问连续、对齐的地址，硬件可以把多次访存合并成更少的 memory transaction。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 为什么重要</div><p>合并访问可以提高有效 HBM 带宽，减少访存事务数量，让 SM 少等数据。很多 memory-bound kernel 的优化重点就是提高访存连续性。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 反例</div><p>stride 访问、非对齐访问、随机访问、不同线程访问分散地址都会破坏 coalescing，导致同样的数据量需要更多 memory transaction。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 优化方向</div><p>常见做法包括调整数据布局、让线程映射到连续地址、使用 shared memory 做重排、向量化 load/store，以及减少不规则访问。</p></div>
<div class="qa-summary">面试口径：Coalescing 的目标是让一个 warp 的访存尽量连续且对齐，把零散访存合并成少量事务，从而提升有效带宽。</div>
</div>
</div>
</div>

## 关联模块

- `利用率诊断`：把 GPU-Util 深挖到 SM Active、Occupancy、Warp Stall。
- `瓶颈分类`：把指标组合映射到 compute-bound、memory-bound、communication-bound。
- `GPU 互联与数据路径`：解释 PCIe、NVLink、RDMA 对多卡性能的影响。
- `性能预测指标`：把这些指标进一步转成特征和标签。

<div class="card card-d">
<h3>官方参考</h3>
<div class="resource-grid">
<a class="resource-card" href="https://developer.nvidia.com/blog/nvidia-ampere-architecture-in-depth/"><div class="resource-type">official</div><div class="resource-title">NVIDIA Ampere Architecture</div><div class="resource-desc">A100 架构深度解析，SM、Tensor Core、HBM 详解。</div></a>
<a class="resource-card" href="https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/"><div class="resource-type">official</div><div class="resource-title">NVIDIA Hopper Architecture</div><div class="resource-desc">H100 架构深度解析，Transformer Engine、FP8、DPX。</div></a>
<a class="resource-card" href="https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html"><div class="resource-type">official</div><div class="resource-title">Nsight Compute Profiling Guide</div><div class="resource-desc">GPU 性能分析指标详解，Roofline、Occupancy、Memory 分析。</div></a>
<a class="resource-card" href="https://arxiv.org/abs/2205.05937"><div class="resource-type">paper</div><div class="resource-title">FlashAttention</div><div class="resource-desc">内存高效 Attention 算法，IO-Aware 优化经典论文。</div></a>
</div>
</div>

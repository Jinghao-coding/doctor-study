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

<p><strong>Roofline 模型</strong>是一个用来判断程序 / kernel 性能瓶颈的模型。它最常用于回答一个问题：</p>
<blockquote>一个 kernel 慢，到底是 <strong>算力不够 compute-bound</strong>，还是 <strong>数据搬运不够快 memory-bound</strong>？</blockquote>

<div class="qa-summary">一句话：Roofline 模型用"计算强度"和"实际性能"把 kernel 画到图上，看它被算力屋顶限制，还是被内存带宽屋顶限制。</div>

<div class="qa-section"><div class="qa-section-title">Roofline 图长什么样？</div>
<p>Roofline 图有两个坐标轴：X 轴是 Arithmetic Intensity（计算强度，单位 FLOPs/Byte），Y 轴是 Performance（实际计算性能，单位 FLOPs/s）。图上用两个"屋顶"限制程序性能：Memory Roof 是内存带宽屋顶（斜线），Compute Roof 是峰值算力屋顶（水平线）。Roofline 是一种简化的可视化性能模型，用来判断程序受 memory bandwidth 还是 arithmetic bandwidth / compute peak 限制[[Nsight Compute Profiling Guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html)]。</p>
<pre><code>性能 FLOPS/s
  ^
  |
  |                  ───────────────  Compute Roof
  |                 /
  |                /
  |               /
  |              /
  |_____________/____________________&gt; Arithmetic Intensity
              Ridge Point</code></pre>
</div>

<div class="qa-section"><div class="qa-section-title">Arithmetic Intensity 是什么？</div>
<p>计算强度定义为：<strong>Arithmetic Intensity = 总计算量 / 总数据搬运量 = FLOPs / Bytes</strong>。它回答的是：每搬运 1 byte 数据，能做多少次计算？例如 AI = 2 FLOPs/Byte，意思是每从内存搬 1 byte 数据，大约做 2 次浮点计算。计算强度低（比如 elementwise add，每个元素只做一次加法但要读两个数、写一个数），通常更容易 memory-bound；计算强度高（比如大矩阵乘，同一批数据被重复计算很多次），更可能 compute-bound。</p>
</div>

<div class="qa-section"><div class="qa-section-title">Roofline 的核心公式</div>
<div class="formula-box">
<div><strong>Attainable Performance = min(Peak Compute Performance, Peak Memory Bandwidth × Arithmetic Intensity)</strong></div>
<div>实际可达到性能 ≤ min(算力峰值, 内存带宽 × 计算强度)</div>
</div>
<p>两个限制：</p>
<ul>
<li><strong>Compute Roof</strong>：硬件峰值算力，比如 A100 FP16 Tensor Core 峰值 312 TFLOPS。不管 kernel 多优秀，理论上不可能超过这个峰值。</li>
<li><strong>Memory Roof</strong>：峰值显存带宽 × 计算强度。比如显存带宽 2 TB/s，计算强度 10 FLOPs/Byte，理论上限 = 2 TB/s × 10 = 20 TFLOPS。即使 GPU 峰值算力是 300 TFLOPS，这个 kernel 也可能只能到 20 TFLOPS，因为数据喂不上。</li>
</ul>
</div>

<div class="qa-section"><div class="qa-section-title">Ridge Point 是什么？</div>
<p>Roofline 图中斜线和水平线相交的点叫 Ridge Point（也叫 Machine Balance Point）。它表示要摆脱内存带宽瓶颈，至少需要多高的计算强度。</p>
<div class="formula-box">
<div><strong>Ridge Point = Peak Compute Performance / Peak Memory Bandwidth</strong></div>
</div>
<p>例如 Peak Compute = 312 TFLOPS，Peak Memory Bandwidth = 2 TB/s，则 Ridge Point = 312 / 2 = 156 FLOPs/Byte。意思是：如果某 kernel 的 Arithmetic Intensity 低于 156 FLOPs/Byte，它更可能 memory-bound；如果高于 156 FLOPs/Byte，它才有机会 compute-bound。</p>
</div>

<div class="qa-section"><div class="qa-section-title">怎么判断 memory-bound 还是 compute-bound？</div>
<p>看 kernel 点落在 Roofline 图的哪里：</p>
<table>
<tr><th>情况</th><th>特征</th><th>含义</th><th>优化方向</th></tr>
<tr><td>计算强度低，落在斜线区域</td><td>Performance 被 Memory Roof 限制</td><td><strong>memory-bound / bandwidth-bound</strong>：kernel 主要在等数据</td><td>减少 global memory 读写、提高 cache 命中、使用 shared memory 做数据复用、memory coalescing、融合算子、改善数据布局</td></tr>
<tr><td>计算强度高，落在水平线区域</td><td>Performance 被 Compute Roof 限制</td><td><strong>compute-bound</strong>：数据复用已经比较好，瓶颈在计算单元吞吐</td><td>使用 Tensor Core、更合适 dtype（FP16/BF16/TF32/INT8）、优化矩阵 shape 和 tile、提高指令吞吐、避免 warp stall</td></tr>
</table>
</div>

<div class="qa-section"><div class="qa-section-title">一个简单例子</div>
<p>假设某 GPU：Peak Compute = 100 TFLOPS，Peak Memory Bandwidth = 2 TB/s，则 Ridge Point = 50 FLOPs/Byte。</p>
<p><strong>Kernel A</strong>：Arithmetic Intensity = 5 FLOPs/Byte → Memory Roof = 2 TB/s × 5 = 10 TFLOPS → Attainable Performance = min(100, 10) = <strong>10 TFLOPS</strong>（memory-bound，即使优化也很难超过 10 TFLOPS）。</p>
<p><strong>Kernel B</strong>：Arithmetic Intensity = 100 FLOPs/Byte → Memory Roof = 2 TB/s × 100 = 200 TFLOPS → Attainable Performance = min(100, 200) = <strong>100 TFLOPS</strong>（compute-bound）。</p>
</div>

<div class="qa-section"><div class="qa-section-title">放到深度学习里怎么理解？</div>
<p>常见算子的 Roofline 位置大概是：</p>
<table>
<tr><th>算子</th><th>计算强度</th><th>常见瓶颈</th></tr>
<tr><td>Elementwise Add / ReLU</td><td>低</td><td>memory-bound</td></tr>
<tr><td>LayerNorm</td><td>偏低</td><td>memory-bound / latency-bound</td></tr>
<tr><td>Softmax</td><td>偏低到中等</td><td>memory-bound / latency-bound</td></tr>
<tr><td>Embedding / Gather</td><td>很低</td><td>memory-bound / memory latency</td></tr>
<tr><td>Small GEMM</td><td>中等</td><td>可能 launch / memory / compute 都有</td></tr>
<tr><td>Large GEMM</td><td>高</td><td>compute-bound，常看 Tensor Core</td></tr>
<tr><td>Conv</td><td>中高</td><td>通常可接近 compute-bound</td></tr>
<tr><td>Attention</td><td>取决于实现</td><td>naive 可能 memory-bound，FlashAttention 提高数据复用</td></tr>
</table>
<p>为什么 FlashAttention 快？一个 Roofline 视角是：它减少了 HBM 读写，提高了数据复用，因此提高了 arithmetic intensity，让 attention 更少受 memory roof 限制。</p>
</div>

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

<div class="qa-section"><div class="qa-section-title">Naive Roofline 数学表达</div>
<p>如果要用更形式化的数学公式表示：</p>
<div class="formula-box">
<div><strong>P<sub>max</sub> = min(P<sub>peak</sub>, I × b<sub>max</sub>)</strong></div>
</div>
<p>其中：</p>
<ul>
<li><strong>P<sub>max</sub></strong>：浮点操作性能上限（操作数/秒）</li>
<li><strong>P<sub>peak</sub></strong>：芯片可用的峰值浮点性能（操作数/秒）</li>
<li><strong>b<sub>max</sub></strong>：芯片可用的峰值内存带宽（字节/秒）</li>
<li><strong>I</strong>：计算强度（操作数/字节）= 总浮点操作数 / 总内存访问量</li>
</ul>
<p>水平和斜线的组合为该模型命名为 "Roofline model"。可以形象理解为：计算强度是触及屋顶的一根柱子——如果触及平坦部分，说明 compute-bound；触及斜屋顶部分，说明 memory-bound。更多推导细节可参考[[深入理解 roofline 模型]](https://www.armcvai.cn/2024-09-15/roofline-summary.html)。</p>
</div>

<div class="qa-section"><div class="qa-section-title">V100 / A100 / H100 硬件参数与 OI 对照表</div>
<p>不同 GPU 的 Ridge Point（OI）差异很大，这直接影响 kernel 处于 memory-bound 还是 compute-bound 的判断阈值：</p>
<table>
<tr><th>GPU</th><th>显存</th><th>CUDA 核心数</th><th>FP16 Tensor Core</th><th>FP32</th><th>最大内存带宽</th><th>Tensor OI（FP16）</th></tr>
<tr><td>V100-SXM</td><td>16 GB</td><td>5120</td><td>125 TFLOPS</td><td>15.7 TFLOPS</td><td>900 GB/s</td><td>138</td></tr>
<tr><td>A100-SXM</td><td>40 / 80 GB</td><td>6912</td><td>312 TFLOPS</td><td>19.5 TFLOPS</td><td>2039 GB/s</td><td>153</td></tr>
<tr><td>H100-SXM</td><td>80 GB</td><td>8192</td><td>989 TFLOPS</td><td>60 TFLOPS</td><td>3350 GB/s</td><td>295</td></tr>
</table>
<p>注意：V100 PCle 的 ops:byte ratio 在 40（L2 缓存）到 124.4（HBM）之间，取决于数据来源（片内 vs 片外）。A100 的 ops:byte ratio 是 208，这意味着每访问 1 字节内存时，GPU 可以完成 208 次浮点运算[[深入理解 roofline 模型]](https://www.armcvai.cn/2024-09-15/roofline-summary.html)。如果计算的 OI 低于 208，程序性能会受到内存带宽的限制。</p>
</div>

<div class="qa-section"><div class="qa-section-title">矩阵乘法的 Roofline 分析</div>
<p>矩阵乘法 C = A × B，其中 A ∈ R^{M×K}，B ∈ R^{K×N}，C ∈ R^{M×N}，数据类型为 FP16。其最小内存访问代价 MAC = MK + KN + MN。</p>
<div class="formula-box">
<div><strong>OI<sub>matmul</sub> = 2MNK / (MK + KN + MN)</strong></div>
<div><strong>Ridge Point<sub>A100</sub> = 312 / 2.03 ≈ 153</strong></div>
</div>
<p>在 A100-SXM 上运行矩阵乘法时，如果 OI<sub>matmul</sub> 低于 153，则处于内存受限；反之则计算受限。</p>
<p><strong>实例推演：</strong>一个 Linear 层权重为 512×1024，输入为 1024×4096，则：</p>
<pre><code class="language-text">Arithmetic Intensity = 2 × 512 × 1024 × 4096 / [2 × (512×1024 + 1024×4096 + 512×4096)]
                    ≈ 315 FLOPs/Byte</code></pre>
<p>315 > 124.4（V100 PCle 的 OI），因此该矩阵乘法在 V100 上受算术限制，GPU 将被充分利用[[深入理解 roofline 模型]](https://www.armcvai.cn/2024-09-15/roofline-summary.html)。</p>
</div>

<div class="qa-section"><div class="qa-section-title">LLM 推理的 Roofline 分析：Prefill 与 Decode 的瓶颈完全不同</div>
<p>LLM 推理中，一次前向传播对每个 token 和每个模型参数约需 2 次浮点运算。在非长上下文场景（context_length < 1024，batch_size = 1）下，随着输入 prompt 长度增加，操作强度呈线性增长：</p>
<table>
<tr><th>阶段</th><th>seq_len</th><th>典型 OI</th><th>瓶颈</th><th>原因</th></tr>
<tr><td>Prefill</td><td>较大（>200）</td><td>≈ 2 × seq_len（如 400+）</td><td><strong>compute-bound</strong></td><td>每个 token 的计算量随 seq_len 线性增长，远超 Ridge Point</td></tr>
<tr><td>Decode</td><td>固定 = 1</td><td>≈ 2</td><td><strong>memory-bound</strong></td><td>每生成一个 token 只做少量计算，但需要加载全部模型权重</td></tr>
</table>
<p>一个关键直觉：以 A100 为例，ops:byte ratio 是 208。计算 1 个 token 的 KV 值的计算强度约为 1，而计算 208 个 token 的 KV 值的计算强度则是 208。这意味着 <strong>计算 1 个 token 和计算 208 个 token 的时间几乎相同</strong>——因为低于 208 时，受内存带宽限制，内存加载时间主导性能；达到 208 时，才转为算力受限[[深入理解 roofline 模型]](https://www.armcvai.cn/2024-09-15/roofline-summary.html)。</p>
<p>这也可以解释为什么 prefill 和 decode 的瓶颈不同，以及为什么可以将它们分开调度到不同节点上。</p>
</div>

<div class="qa-section"><div class="qa-section-title">AI 应用性能优化策略总结</div>
<p>Roofline 模型最终指导的优化方向可以归纳为：</p>
<ul>
<li><strong>AI 推理时间取决于主要因素</strong>：内存读写时间 和 数学计算时间，而非次要因素（网络带宽、磁盘读写）。</li>
<li><strong>两个区域，两条策略</strong>：硬件不变的前提下，memory-bound 时减少内存访问代价 MAC（如融合算子、共享内存、数据复用）；compute-bound 时减少浮点运算次数 FLOPs 或提高计算效率（如 Tensor Core、更优 dtype、更优 tile）。</li>
<li><strong>实际推理时间 = max(内存读取时间, 数学计算时间)</strong>：取决于哪个更长。当处于内存受限时，内存读取时间长；当处于算力受限时，数学计算时间长。</li>
</ul>
<p>更多 Roofline 模型的深入分析、论文引用和实际案例，可以参考[[深入理解 roofline 模型]](https://www.armcvai.cn/2024-09-15/roofline-summary.html)。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么是 Roofline 模型？面试怎么回答？</div>
<div class="qa-a">
<p>Roofline 模型是一个用来分析程序性能上限和瓶颈的可视化模型。它的横轴是 arithmetic intensity（FLOPs per Byte），表示每搬运一个字节能做多少计算；纵轴是实际性能（FLOPs/s）。图上有两个屋顶：一个是由显存带宽决定的 memory roof（斜线），另一个是由硬件峰值算力决定的 compute roof（水平线）。一个 kernel 的性能上限等于 <code>min(峰值算力, 内存带宽 × 计算强度)</code>。如果 kernel 落在斜线区域，说明 memory-bound；如果落在水平区域，说明 compute-bound。它可以帮助我们判断优化方向：memory-bound 就优化访存和数据复用，compute-bound 就优化计算吞吐、Tensor Core、并行度等。</p>
<div class="qa-summary">Roofline = 两个屋顶 + 一个点。Memory Roof = 带宽 × 计算强度，Compute Roof = 峰值算力。点在斜线下 memory-bound，在横线下 compute-bound。一句话：用 FLOPs/Byte 判断 kernel 是缺数据，还是缺算力。</div>
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

<div class="card card-d">
<h3>官方参考</h3>
<div class="resource-grid">
<a class="resource-card" href="https://developer.nvidia.com/blog/nvidia-ampere-architecture-in-depth/"><div class="resource-type">official</div><div class="resource-title">NVIDIA Ampere Architecture</div><div class="resource-desc">A100 架构深度解析，SM、Tensor Core、HBM 详解。</div></a>
<a class="resource-card" href="https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/"><div class="resource-type">official</div><div class="resource-title">NVIDIA Hopper Architecture</div><div class="resource-desc">H100 架构深度解析，Transformer Engine、FP8、DPX。</div></a>
<a class="resource-card" href="https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html"><div class="resource-type">official</div><div class="resource-title">Nsight Compute Profiling Guide</div><div class="resource-desc">GPU 性能分析指标详解，Roofline、Occupancy、Memory 分析。</div></a>
<a class="resource-card" href="https://arxiv.org/abs/2205.05937"><div class="resource-type">paper</div><div class="resource-title">FlashAttention</div><div class="resource-desc">内存高效 Attention 算法，IO-Aware 优化经典论文。</div></a>
</div>
</div>

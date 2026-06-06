<div class="card card-m">
<h3>GPU 性能指标全景</h3>
<p>GPU 性能优化和面试中，必须掌握核心性能指标的定义、计算方式和实际意义。这些指标决定了模型训练/推理的效率和成本。</p>
<table>
<tr><th>指标类别</th><th>具体指标</th><th>定义</th><th>面试重点</th></tr>
<tr><td>计算性能</td><td>TFLOPS / GFLOPS</td><td>每秒浮点运算次数</td><td>理论峰值 vs 实际利用率，A100 FP16 312 TFLOPS 是理论值</td></tr>
<tr><td>显存带宽</td><td>GB/s</td><td>GPU 与 HBM 之间的数据传输速率</td><td>带宽瓶颈 vs 计算瓶颈，内存密集型算子受带宽限制</td></tr>
<tr><td>显存容量</td><td>GB</td><td>HBM 可存储的数据总量</td><td>模型参数 + 优化器状态 + 激活值，决定最大可训练模型</td></tr>
<tr><td>利用率</td><td>GPU Util / Tensor Core Util</td><td>GPU 活跃时间占比 / Tensor Core 活跃占比</td><td>高 GPU Util 不代表高效率，可能是内存拷贝等待</td></tr>
<tr><td>功耗</td><td>TDP / 实际功耗</td><td>热设计功耗 / 实际运行功耗</td><td>H100 TDP 700W，实际功耗影响数据中心供电和散热</td></tr>
<tr><td>互联带宽</td><td>NVLink / PCIe GB/s</td><td>GPU 间 / CPU-GPU 数据传输速率</td><td>多卡并行时互联带宽决定通信效率</td></tr>
</table>
</div>

<div class="card card-s">
<h3>计算性能指标详解</h3>
<p>TFLOPS 是面试中最常问的计算性能指标，但要区分理论峰值和实际利用率。</p>

<div class="qa-section"><div class="qa-section-title">理论峰值计算</div>
<p>TFLOPS = SM 数量 × 每个 SM 的 FMA 单元数 × 时钟频率 × 2（FMA 算两次运算）。<br>
A100 FP16 Tensor Core：108 SM × 256 ops/clock × 1.41 GHz × 2 = ~312 TFLOPS。</p></div>

<div class="qa-section"><div class="qa-section-title">实际利用率</div>
<p>实际 TFLOPS 通常只有理论值的 30%-60%。原因包括：内存带宽瓶颈、数据依赖、kernel launch 开销、通信等待、负载不均衡等。面试中要说明"高 GPU Util 不等于高计算效率"。</p></div>

<div class="qa-section"><div class="qa-section-title">精度对比</div>
<table>
<tr><th>精度</th><th>A100</th><th>H100</th><th>适用场景</th></tr>
<tr><td>FP64</td><td>9.7 TFLOPS</td><td>34 TFLOPS</td><td>科学计算，AI 很少用</td></tr>
<tr><td>FP32</td><td>19.5 TFLOPS</td><td>67 TFLOPS</td><td>通用计算，训练推理</td></tr>
<tr><td>TF32</td><td>156 TFLOPS</td><td>494 TFLOPS</td><td>Tensor Core 加速的 FP32，训练常用</td></tr>
<tr><td>FP16/BF16</td><td>312 TFLOPS</td><td>989 TFLOPS</td><td>混合精度训练，最常用</td></tr>
<tr><td>FP8</td><td>不支持</td><td>1979 TFLOPS</td><td>H100 新增，推理和某些训练场景</td></tr>
<tr><td>INT8</td><td>624 TOPS</td><td>3958 TOPS</td><td>量化推理，吞吐量优先</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 H100 FP8 算力是 FP16 的两倍？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">数据位宽减半</div><p>FP8 每个数占 8 bit，FP16 占 16 bit。同样的寄存器和带宽可以处理两倍数量的数据。</p></div>
<div class="qa-section"><div class="qa-section-title">Tensor Core 支持</div><p>H100 第四代 Tensor Core 原生支持 FP8 矩阵运算，硬件层面做了优化。</p></div>
<div class="qa-section"><div class="qa-section-title">精度权衡</div><p>FP8 精度较低，需要配合精度缩放（scaling）和损失回传稳定技术。不是所有模型都能直接用 FP8。</p></div>
<div class="qa-summary">FP8 = 精度换速度，适合对精度不敏感的推理场景，或配合 Transformer Engine 的训练场景。</div>
</div>
</div>
</div>

<div class="card card-s">
<h3>显存带宽与 Roofline 模型</h3>
<p>显存带宽是 GPU 性能的关键瓶颈之一。Roofline 模型帮助判断算子是计算瓶颈还是带宽瓶颈。</p>

<div class="qa-section"><div class="qa-section-title">带宽定义</div>
<p>显存带宽 = 显存位宽 × 显存频率 ÷ 8。A100 80GB 使用 HBM2e，位宽 5120-bit，频率 3.2 Gbps，带宽 = 5120 × 3.2 ÷ 8 = 2048 GB/s ≈ 2 TB/s。</p></div>

<div class="qa-section"><div class="qa-section-title">Roofline 模型</div>
<p>Roofline 模型描述算子的性能上限：</p>
<ul>
<li>计算强度（Arithmetic Intensity）= 计算量 FLOPs / 访存量 Bytes</li>
<li>如果计算强度 > 峰值 TFLOPS / 带宽 GB/s，算子是计算瓶颈（Compute Bound）</li>
<li>如果计算强度 < 峰值 TFLOPS / 带宽 GB/s，算子是带宽瓶颈（Memory Bound）</li>
</ul>
<p>A100 的"脊点"（Ridge Point）= 312 TFLOPS / 2 TB/s = 156 FLOPs/Byte。计算强度低于 156 的算子受带宽限制。</p>
</div>

<div class="qa-section"><div class="qa-section-title">常见算子类型</div>
<table>
<tr><th>算子</th><th>计算强度</th><th>瓶颈类型</th><th>优化方向</th></tr>
<tr><td>矩阵乘法 (GEMM)</td><td>高</td><td>Compute Bound</td><td>Tensor Core、分块、流水线</td></tr>
<tr><td>Softmax</td><td>低</td><td>Memory Bound</td><td>融合 kernel、减少访存</td></tr>
<tr><td>LayerNorm</td><td>低</td><td>Memory Bound</td><td>融合到前后算子中</td></tr>
<tr><td>Attention</td><td>中等</td><td>混合</td><td>FlashAttention、分页 KV Cache</td></tr>
<tr><td>Embedding Lookup</td><td>低</td><td>Memory Bound</td><td>量化、压缩</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 Transformer 的 Attention 是瓶颈？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">计算复杂度</div><p>Self-Attention 的 QK^T 计算量是 O(n²×d)，序列长度 n 增加时平方增长。长序列时计算量巨大。</p></div>
<div class="qa-section"><div class="qa-section-title">内存访问模式</div><p>Attention 需要频繁读写巨大的 Q、K、V 矩阵和 Attention Score 矩阵，访存量大且不规则，难以利用缓存。</p></div>
<div class="qa-section"><div class="qa-section-title">优化方案</div><p>FlashAttention 通过分块和重计算减少 HBM 访存；Sparse Attention 减少计算量；MQA/GQA 减少 KV Cache 存储。</p></div>
<div class="qa-summary">Attention 瓶颈 = 计算量 O(n²) + 访存量大 + 内存访问不规则。FlashAttention 是核心优化手段。</div>
</div>
</div>
</div>

<div class="card card-w">
<h3>GPU 利用率指标解读</h3>
<p>nvidia-smi 显示的 GPU 利用率不等于计算效率。面试中要区分不同利用率指标的含义。</p>

<table>
<tr><th>指标</th><th>来源</th><th>含义</th><th>面试陷阱</th></tr>
<tr><td>GPU Utilization</td><td>nvidia-smi</td><td>GPU 活跃时间占比（采样周期内至少有一个 kernel 在执行的时间比例）</td><td>100% Util 可能是小 kernel 频繁启动，实际吞吐量很低</td></tr>
<tr><td>Tensor Core Util</td><td>ncu / nsys</td><td>Tensor Core 实际活跃时间占比</td><td>FP32 运算不会用到 Tensor Core，此指标为 0 不代表有问题</td></tr>
<tr><td>Memory Utilization</td><td>nvidia-smi</td><td>显存带宽使用比例</td><td>高内存利用率说明带宽瓶颈，不一定是好事</td></tr>
<tr><td>SM Efficiency</td><td>ncu</td><td>SIMD 指令执行效率</td><td>低效率可能是 warp divergence 或资源竞争</td></tr>
<tr><td>Occupancy</td><td>ncu</td><td>每个 SM 上活跃的 warp 比例</td><td>高 Occupancy 不代表高性能，但低 Occupancy 通常有问题</td></tr>
</table>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: nvidia-smi 显示 GPU Util 100%，但模型训练很慢，为什么？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">小 kernel 频繁启动</div><p>大量 tiny kernel 导致 GPU 一直在跑，但每个 kernel 只做很少计算。启动开销占主导，有效计算比例低。</p></div>
<div class="qa-section"><div class="qa-section-title">内存拷贝等待</div><p>CPU-GPU 数据传输（H2D/D2H）期间 GPU 可能在等待，但 nvidia-smi 的采样方式可能显示为活跃。</p></div>
<div class="qa-section"><div class="qa-section-title">通信瓶颈</div><p>多卡训练时，GPU 可能在等待 NCCL 通信完成，但采样时刚好有通信 kernel 在跑，显示 100% Util。</p></div>
<div class="qa-section"><div class="qa-section-title">Tensor Core 未使用</div><p>如果代码没有使用混合精度或 Tensor Core，虽然 CUDA Core 在跑，但峰值算力远低于 Tensor Core。</p></div>
<div class="qa-summary">GPU Util 是时间占比，不是效率指标。需要用 nsys/ncu 分析实际 TFLOPS、内存带宽、Tensor Core 利用率。</div>
</div>
</div>
</div>

<div class="card card-d">
<h3>多卡互联性能指标</h3>
<p>多 GPU 训练/推理时，卡间互联带宽是决定扩展效率的关键。面试中经常问到 NVLink、PCIe、InfiniBand 的对比。</p>

<table>
<tr><th>互联方式</th><th>带宽（单向）</th><th>拓扑</th><th>典型场景</th></tr>
<tr><td>NVLink 3.0</td><td>300 GB/s（A100）</td><td>点对点或经 NVSwitch 全互联</td><td>单节点内 4/8 卡全互联</td></tr>
<tr><td>NVLink 4.0</td><td>450 GB/s（H100）</td><td>同上</td><td>单节点内 4/8 卡全互联</td></tr>
<tr><td>NVSwitch</td><td>聚合 4.8 TB/s（A100）</td><td>全互联交换</td><td>DGX 系列 8 卡全互联</td></tr>
<tr><td>PCIe 4.0 x16</td><td>32 GB/s</td><td>树形，经 CPU 或 PCIe Switch</td><td>CPU-GPU 通信、低速卡间通信</td></tr>
<tr><td>PCIe 5.0 x16</td><td>64 GB/s</td><td>同上</td><td>新一代 CPU-GPU 互联</td></tr>
<tr><td>InfiniBand NDR</td><td>400 Gbps = 50 GB/s</td><td>网络交换</td><td>多节点 GPU 集群互联</td></tr>
<tr><td>InfiniBand XDR</td><td>800 Gbps = 100 GB/s</td><td>网络交换</td><td>下一代多节点互联</td></tr>
</table>

<div class="qa-section"><div class="qa-section-title">扩展效率计算</div>
<p>线性扩展效率 = 多卡实际吞吐量 /（单卡吞吐量 × 卡数）。<br>
影响扩展效率的因素：通信量（模型并行 vs 数据并行）、通信带宽、通信频率、负载均衡。</p></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么多节点训练的扩展效率通常低于单节点？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">带宽差距</div><p>单节点 NVLink 300-450 GB/s，多节点 InfiniBand 通常 50-100 GB/s，差距 3-8 倍。通信成为瓶颈。</p></div>
<div class="qa-section"><div class="qa-section-title">通信频率</div><p>数据并行每次迭代都要 AllReduce 梯度。节点间通信延迟高，导致 GPU 等待时间增加。</p></div>
<div class="qa-section"><div class="qa-section-title">优化手段</div><p>梯度压缩、通信重叠（overlap computation and communication）、增大 batch size 减少通信频率、使用 NVLink + InfiniBand 混合拓扑。</p></div>
<div class="qa-summary">节点间带宽远低于节点内，是多节点扩展效率下降的主因。优化方向：减少通信量、重叠通信计算、提升有效带宽。</div>
</div>
</div>
</div>

<div class="card card-r">
<h3>GPU 性能面试高频题</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何计算一个模型训练需要多少显存？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">显存占用组成</div>
<p>模型参数 + 优化器状态（Adam 需要 2 倍参数）+ 梯度（1 倍参数）+ 激活值（与 batch size、序列长度相关）。</p></div>
<div class="qa-section"><div class="qa-section-title">估算公式</div>
<p>以 FP16 混合精度为例：显存 ≈ 参数 × (2 + 2 + 2) + 激活值。Adam 优化器需要保存一阶和二阶动量，各占 4 字节（FP32）。</p></div>
<div class="qa-section"><div class="qa-section-title">示例</div>
<p>7B 参数模型，FP16：参数 14 GB，Adam 状态 28 GB，梯度 14 GB，激活值假设 10 GB，总计约 66 GB。单卡 80GB A100 可以放下，但 40GB 不够。</p></div>
<div class="qa-summary">显存 = 参数 × (精度字节 + 优化器倍数 + 梯度精度) + 激活值。ZeRO、Offloading、Activation Checkpointing 可以大幅减少。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: A100 和 H100 的主要区别是什么？</div>
<div class="qa-a">
<div class="qa-grid"><div class="qa-mini"><strong>架构</strong>A100 Ampere，H100 Hopper。Hopper 新增 Transformer Engine、FP8 支持。</div><div class="qa-mini"><strong>算力</strong>H100 FP16 989 TFLOPS vs A100 312 TFLOPS，提升约 3 倍。</div><div class="qa-mini"><strong>显存</strong>H100 80GB HBM3 带宽 3.35 TB/s vs A100 2 TB/s，提升约 1.7 倍。</div><div class="qa-mini"><strong>互联</strong>H100 NVLink 4.0 450 GB/s vs A100 300 GB/s，提升 1.5 倍。</div><div class="qa-mini"><strong>功耗</strong>H100 TDP 700W vs A100 400W，功耗大幅提升，散热要求更高。</div><div class="qa-mini"><strong>专用单元</strong>H100 新增 Transformer Engine（动态精度管理）、DPX 指令（动态规划加速）。</div></div>
<div class="qa-summary">H100 = 更高算力 + 更高带宽 + FP8 + Transformer Engine + 更高功耗。不是简单的倍数提升，架构有本质变化。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么是 Tensor Core？为什么比普通 CUDA Core 快？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">专用矩阵运算单元</div><p>Tensor Core 是专门做矩阵乘加（D = A × B + C）的硬件单元，每个周期可以完成一个 4×4×4 FP16 矩阵运算。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么更快</div>
<p>普通 CUDA Core 每次只做 1 个 FMA（乘加），Tensor Core 一次做 64 个 FMA（4×4×4）。同样的时钟周期，吞吐量高几十倍。</p></div>
<div class="qa-section"><div class="qa-section-title">使用条件</div><p>需要满足：数据是 FP16/BF16/TF32/FP8 格式、矩阵维度对齐（如 8 的倍数）、使用 cuBLAS/cuDNN 等库自动调用。</p></div>
<div class="qa-summary">Tensor Core = 矩阵运算专用硬件，一次处理整个矩阵块，而不是单个元素。是深度学习加速的核心。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 的 Memory Coalescing 是什么？为什么重要？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">定义</div><p>当一个 warp（32 个线程）访问的内存地址是连续的，GPU 可以把多次访问合并成一次内存事务，减少访存次数。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么重要</div><p>GPU 显存带宽有限，但计算单元很多。如果访存不合并，大量带宽浪费在传输不必要的数据上，计算单元等待数据，整体效率下降。</p></div>
<div class="qa-section"><div class="qa-section-title">实际影响</div><p>矩阵运算中，行优先存储的矩阵按列访问会导致 stride 访问，不合并；转置后按行访问可以合并。这也是 FlashAttention 做分块的原因之一。</p></div>
<div class="qa-summary">Memory Coalescing = 合并内存访问，减少事务数。是 GPU 内存带宽优化的基础。</div>
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

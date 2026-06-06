<div class="card card-m">
<h3>性能预测视角：特征与标签映射</h3>
<p>在 MLSys 性能预测研究中，GPU 指标不是孤立的数字，而是构建预测模型的核心素材。整个指标体系可以按"输入特征维（静态属性）"和"输出标签维（动态运行时表现）"划分，形成完整的预测闭环。</p>

<div class="qa-section"><div class="qa-section-title">预测模型架构</div>
<p>输入特征库 (X) 包含算法特征（FLOPs、Shape）、硬件特征（峰值算力、带宽）、部署特征（3D 并行策略）；经过预测器模型（解析方程 / ML / GNN）；输出标签库 (Y) 包含时间指标（Step Time）、空间指标（Peak Active Memory）、效率指标（MFU、Occupancy）。</p></div>

<table>
<tr><th>维度</th><th>指标</th><th>角色</th><th>物理含义</th></tr>
<tr><td rowspan="3">算力与效率</td><td>Peak FLOPS</td><td>输入特征 X</td><td>硬件理论峰值算力，跨显卡预测的核心特征</td></tr>
<tr><td>FLOPs</td><td>输入特征 X</td><td>算法理论计算量，任务的绝对工作量</td></tr>
<tr><td>MFU</td><td>输出标签 Y</td><td>模型算力利用率，分布式训练效率的黄金标准</td></tr>
<tr><td rowspan="3">时间与空间</td><td>GPU Util</td><td>辅助特征 X / 标签 Y</td><td>时间维度占空比，不代表并发度</td></tr>
<tr><td>SM Active</td><td>输出标签 Y</td><td>SM 空间分布活跃度，防欺骗指标</td></tr>
<tr><td>SM Occupancy</td><td>特征 X / 标签 Y</td><td>延迟隐藏能力温度计</td></tr>
<tr><td rowspan="3">显存与通信</td><td>Arithmetic Intensity</td><td>输入特征 X</td><td>计算密度，划分算子瓶颈类型</td></tr>
<tr><td>Memory Util</td><td>输出标签 Y</td><td>显存带宽时间利用率（非容量占用率）</td></tr>
<tr><td>Peak Active Memory</td><td>输出标签 Y</td><td>峰值活跃显存，防 OOM 核心预测目标</td></tr>
</table>
</div>

<div class="card card-s">
<h3>算力与效率维度指标</h3>
<p>这一维度关注"模型理论上需要干多少活"与"硬件实际上转化了多少有效功"。</p>

<div class="qa-section"><div class="qa-section-title">Peak FLOPS（硬件理论峰值算力）—— 输入特征 X</div>
<p><strong>规范定义</strong>：GPU 在单位时间（每秒）内理论上能执行的最大浮点运算次数，通常以 TFLOPS 为单位。<br>
<strong>物理含义</strong>：硬件计算能力的绝对物理极限。不同精度（FP32、TF32、BF16、FP8）下的峰值完全不同。例如 H100 SXM 的 BF16 Tensor Core 峰值为 989 TFLOPS。<br>
<strong>科研应用</strong>：支持跨显卡预测的核心特征。若不输入具体的算力数值，预测模型将无法理解硬件升级带来的算力红利，无法实现跨平台泛化。</p></div>

<div class="qa-section"><div class="qa-section-title">FLOPs（算法理论计算量）—— 输入特征 X</div>
<p><strong>规范定义</strong>：执行某次特定计算任务（如一个 Batch 的前向传播）理论上最少需要消耗的浮点运算总次数（与硬件无关）。<br>
<strong>物理含义</strong>：任务的"绝对工作量"。例如矩阵乘法 C = A × B（A 维 M×K，B 维 K×N），理论 FLOPs = 2 × M × N × K（系数 2 源于每个位置需一次乘法和一次加法）。<br>
<strong>科研应用</strong>：评估算法复杂度的基石。预测模型不能简单用 时间 = 理论 FLOPs / 硬件峰值，因为该公式假设硬件效率为 100%。预测器的核心任务就是预测那损失掉的效率去了哪里。</p></div>

<div class="qa-section"><div class="qa-section-title">MFU（Model FLOPs Utilization，模型算力利用率）—— 输出标签 Y</div>
<p><strong>规范定义</strong>：在实际训练中，GPU 每秒实际输出的有效模型算力占其硬件理论峰值算力的比例。</p>
<p><strong>数学公式</strong>：</p>
<div class="formula">MFU = (模型单步理论计算量 FLOPs × 每秒实际吞吐量 Samples/s) / GPU 硬件理论峰值算力 FLOPS</div>
<p><strong>物理含义</strong>：大模型时代衡量分布式训练效率的黄金标准。它最硬核的地方在于：彻底剔除了为了省显存而进行的"激活值重计算（Recomputation）"带来的虚假硬件繁忙（HFU）。只承认最终盖在大楼里的砖，不承认建了拆、拆了建的返工。<br>
<strong>科研应用</strong>：分布式策略搜索（Auto-Parallelism）的最佳预测目标。预测出 MFU 随 3D 并行拓扑变化的曲线，能直接指导系统挑选出最优的部署方案。</p></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MFU 和 HFU 有什么区别？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">MFU（Model FLOPs Utilization）</div><p>只计算模型前向+反向传播的理论 FLOPs，不包含激活值重计算（Activation Recomputation/Checkpointing）带来的额外计算量。是衡量训练效率的"净效率"。</p></div>
<div class="qa-section"><div class="qa-section-title">HFU（Hardware FLOPs Utilization）</div><p>计算 GPU 实际执行的所有 FLOPs（包含重计算），除以硬件峰值。重计算会让 HFU 虚高，因为 GPU 在做"返工"。</p></div>
<div class="qa-section"><div class="qa-section-title">典型差异</div><p>使用 Activation Checkpointing 时，HFU 可能达到 60%，但 MFU 只有 45%。差距就是重计算带来的虚假繁忙。</p></div>
<div class="qa-summary">MFU = 净效率（不含返工），HFU = 毛效率（含返工）。论文和面试中应优先使用 MFU。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 大模型训练的 MFU 通常是多少？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">单卡场景</div><p>GPT-3 175B 单卡 MFU 约 35%-40%。主要损失来自：序列并行通信、激活值重计算、数据加载等待。</p></div>
<div class="qa-section"><div class="qa-section-title">多卡分布式</div><p>8 卡 A100 MFU 约 45%-52%（Megatron-LM 报告）。64 卡 MFU 约 52%-57%。通信开销随规模增加。</p></div>
<div class="qa-section"><div class="qa-section-title">业界标杆</div><p>GPT-4 训练 MFU 据报道约 38%-42%（含通信开销）。Llama 2 70B 约 50%+。超过 60% 通常需要极致优化。</p></div>
<div class="qa-summary">MFU 30%-50% 是常见范围，50%+ 是优秀水平。损失主要来自通信、重计算、数据加载和 kernel launch 开销。</div>
</div>
</div>
</div>

<div class="card card-s">
<h3>时间与空间利用率指标</h3>
<p>这一维度关注"硬件资源在时间上被占用了多久，在空间上被铺得有多满"。</p>

<div class="qa-section"><div class="qa-section-title">GPU Utilization（GPU 计算利用率）—— 辅助特征 X / 标签 Y</div>
<p><strong>规范定义</strong>：在给定采样周期内（如 1 秒），GPU 的内核引擎至少有一个活动内核在执行的时间比例。</p>
<div class="formula">GPU_Util = T(any_kernel_active) / T(sample) × 100%</div>
<p><strong>物理含义</strong>：时间维度的"有无"占空比，不代表并发度。哪怕 120 个 SM 中只有 1 个 SM 在跑一个微小的算子，其余 119 个全在闲置，GPU-Util 依然是 100%。<br>
<strong>科研应用</strong>：单独预测 GPU-Util 缺乏物理和数学单调性（学术价值低）。但可作为集群调度中预测进程是否死锁（Util 100% 但功耗极低）的特征。</p></div>

<div class="qa-section"><div class="qa-section-title">SM Active（SM 活跃度）—— 输出标签 Y</div>
<p><strong>规范定义</strong>：在给定采样周期内，至少有一个线程束（Warp，32 个线程）在 SM 上执行的时间比例（各 SM 的平均值）。<br>
<strong>物理含义</strong>：空间分布的防欺骗指标。它解决了 GPU-Util 空间粒度过粗的问题。若 120 个 SM 只有 1 个在干活，GPU-Util 是 100%，但 SM Active 只有约 0.83%。它能真正反映任务是否均匀、充分地平铺到了整个芯片上。<br>
<strong>科研应用</strong>：多流并发（CUDA Streams）、多租户混部（Colocation）或 MPS 调度预测的核心标签。用来预测空间填补带来的吞吐量收益。</p></div>

<div class="qa-section"><div class="qa-section-title">SM Occupancy（SM 占有率）—— 特征 X / 标签 Y</div>
<p><strong>规范定义</strong>：在 SM 处于活跃状态时，该 SM 中实际并发运行的 Warp 数量，占该 SM 硬件设计最大能支持的 Warp 数量的比例。<br>
<strong>物理含义</strong>：硬件"延迟隐藏（Latency Hiding）"能力的温度计。GPU 靠超大规模并发来掩盖访存延迟（当一个 Warp 读显存阻塞时，SM 立刻切换到另一个就绪的 Warp）。Occupancy 越高，手里的"替补队员"越多，硬件越不容易因为延迟而彻底空转。<br>
<strong>科研应用</strong>：作为输入特征 X：通过静态分析 CUDA 代码（寄存器用量、共享内存大小、Block Size），算出理论上限 Occupancy。作为输出标签 Y：在编译器调优（Auto-tuning）研究中，预测 Achieved Occupancy，用以评估算子修改后隐藏延迟的能力。</p></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: SM Active 和 SM Occupancy 有什么区别？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">SM Active</div><p>回答"有多少 SM 在干活"。是 SM 级别的时间占空比。如果 120 个 SM 中有 100 个至少有一个 Warp 在跑，SM Active ≈ 83%。</p></div>
<div class="qa-section"><div class="qa-section-title">SM Occupancy</div><p>回答"每个 SM 内部塞得有多满"。是 Warp 级别的空间填充率。如果每个 SM 最多支持 64 个 Warp，当前活跃 32 个，Occupancy = 50%。</p></div>
<div class="qa-section"><div class="qa-section-title">组合解读</div><p>SM Active 高 + Occupancy 低 = 任务铺到了很多 SM，但每个 SM 内部替补不够，容易因延迟空转。SM Active 低 + Occupancy 高 = 只有少数 SM 在干活，但每个 SM 塞得很满。</p></div>
<div class="qa-summary">SM Active = 芯片空间覆盖度（横向），SM Occupancy = 单 SM 内部填充度（纵向）。两者组合才能完整描述 GPU 空间利用率。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Occupancy 越高越好吗？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">不一定</div><p>高 Occupancy 意味着更多 Warp 可以用来隐藏延迟，但也意味着每个 Warp 分到的寄存器和共享内存更少。如果寄存器溢出到 Local Memory（实际是全局显存），反而会严重拖慢性能。</p></div>
<div class="qa-section"><div class="qa-section-title">最优 Occupancy</div><p>通常不是 100%。经验上 50%-75% 的 Occupancy 往往是最优的，因为此时每个 Warp 有足够的寄存器，同时又有足够的替补 Warp 来隐藏延迟。</p></div>
<div class="qa-section"><div class="qa-section-title">Occupancy 陷阱</div><p>Compute-Bound 算子（如大矩阵乘法）在高 Occupancy 时性能反而可能下降，因为 SM 内部资源（寄存器、共享内存、调度器）竞争加剧。</p></div>
<div class="qa-summary">Occupancy 是延迟隐藏的必要条件，但不是充分条件。50%-75% 通常是甜点区，100% 不一定最优。</div>
</div>
</div>
</div>

<div class="card card-w">
<h3>显存与数据流维度指标</h3>
<p>深度学习不仅卡在计算上，更多时候卡在数据搬运上。</p>

<div class="qa-section"><div class="qa-section-title">Arithmetic Intensity（计算密度 / 算力强度）—— 输入特征 X</div>
<p><strong>规范定义</strong>：在一个计算任务中，每从显存中读取/写入 1 个字节的数据，需要消耗多少次浮点运算。单位是 FLOPs/Byte。<br>
<strong>物理含义</strong>：划分算子类型的物理量。基于 Roofline 模型：Compute-Bound（计算受限）= 计算密度高于硬件瓶颈线，执行时间由硬件峰值算力决定；Memory-Bound（访存受限）= 计算密度低于硬件瓶颈线，执行时间由显存带宽决定。<br>
<strong>科研应用</strong>：指导预测模型进行"分流预测"。预测器能自动学会：对计算密集型算子用算力特征去预测时间，对访存密集型算子用带宽特征去预测时间。</p></div>

<div class="qa-section"><div class="qa-section-title">Memory Utilization（显存控制器利用率）—— 输出标签 Y</div>
<p><strong>严禁概念混淆</strong>：它不是显存容量占用率（VRAM Allocated），而是显存带宽的时间利用率。<br>
<strong>规范定义</strong>：在采样周期内，GPU 的显存控制器处于读取或写入活动状态的时间比例。<br>
<strong>物理含义</strong>：数据搬运总线的繁忙度。若该指标逼近 100%，说明系统瓶颈完全卡在显存吞吐（I/O 阻塞）上。<br>
<strong>科研应用</strong>：用于预测和判定 Memory-Bound 算子的加速空间。</p></div>

<div class="qa-section"><div class="qa-section-title">Peak Active Memory（峰值活跃显存占用）—— 输出标签 Y</div>
<p><strong>规范定义</strong>：在深度学习单步训练中（通常在前向传播与反向传播的交界处），真正被模型参数、梯度、激活值硬性占用的显存最大值。<br>
<strong>物理含义</strong>：模型运行的刚性空间需求（不含 PyTorch Caching Allocator 提前圈地预留的 Reserved Memory）。<br>
<strong>科研应用</strong>：防 OOM 调度器与显存编排系统的核心预测目标。精准预测该值可以实现最大化的显存填充率（Memory Colocation）。</p></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Peak Active Memory 和 Reserved Memory 有什么区别？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">Peak Active Memory</div><p>模型真正在用的显存：参数、梯度、优化器状态、激活值。是刚性需求，无法压缩。</p></div>
<div class="qa-section"><div class="qa-section-title">Reserved Memory</div><p>PyTorch Caching Allocator 提前向 GPU 申请的显存池。即使模型当前不用，这些显存也被 PyTorch 占着，方便后续快速分配而不用频繁调用 cudaMalloc。</p></div>
<div class="qa-section"><div class="qa-section-title">实际影响</div><p>nvidia-smi 显示的显存占用是 Reserved Memory，通常远大于 Active Memory。做显存预测和调度时，应该预测 Active Memory，而不是 nvidia-smi 的显示值。</p></div>
<div class="qa-summary">Active Memory = 真正在用，Reserved Memory = 提前占着。调度和预测应以 Active Memory 为准。</div>
</div>
</div>
</div>

<div class="card card-r">
<h3>核心指标联动诊断矩阵</h3>
<p>在预测模型或论文的 Motivation 部分，核心指标可以通过以下经典场景组合形成闭环诊断逻辑：</p>

<table>
<tr><th>场景</th><th>GPU-Util</th><th>SM Active</th><th>SM Occupancy</th><th>实际功耗</th><th>瓶颈诊断与预测方向</th></tr>
<tr><td><strong>A：网格太小</strong></td><td>高 (95%)</td><td>低 (5%)</td><td>高 (80%)</td><td>极低</td><td>Grid Under-population：任务划分的 Block 数量太少，根本没分够 SM。预测器应提示：增加 Batch Size 或调整 Grid 划分。</td></tr>
<tr><td><strong>B：访存阻塞</strong></td><td>高 (95%)</td><td>高 (90%)</td><td>低 (10%)</td><td>低</td><td>Memory-Bound：每个 SM 都分了任务，但寄存器或 Shared Memory 用太多导致替补 Warp 太少。一旦发生显存延迟，SM 就会空转。预测器应预测出算子耗时偏长。</td></tr>
<tr><td><strong>C：完美计算</strong></td><td>高 (95%)</td><td>高 (95%)</td><td>高 (85%)</td><td>极高 (近TDP)</td><td>Compute-Bound：空间填满了，内部替补也充足。此时执行时间主要由理论 FLOPs / 硬件峰值算力决定。预测精度极高。</td></tr>
<tr><td><strong>D：未用 Tensor Core</strong></td><td>高 (95%)</td><td>高 (90%)</td><td>高 (80%)</td><td>中低</td><td>Non-Tensor Core Active：GPU 极忙，但功耗上不去。说明没有调用 Tensor Core，全在做低效的普通 CUDA 标量计算。预测器应提示优化算子或开启混合精度。</td></tr>
</table>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何用这些指标组合诊断 GPU 性能瓶颈？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">诊断流程</div>
<p>1) 看 GPU-Util：低说明 GPU 闲置（CPU 瓶颈或数据加载瓶颈）；高则继续。<br>
2) 看 SM Active：低说明任务没铺满芯片（Grid 太小或并发不够）；高则继续。<br>
3) 看 SM Occupancy：低说明每个 SM 内部替补不够（寄存器/共享内存压力）；高则继续。<br>
4) 看功耗：低功耗 + 高活跃 = 没用 Tensor Core 或在做轻量标量运算；高功耗 = 真正的 Compute-Bound。</p></div>
<div class="qa-section"><div class="qa-section-title">工具链</div>
<p>nvidia-smi 看 GPU-Util 和 Memory Util；DCGM 看 SM Active；ncu（Nsight Compute）看 Occupancy 和 Tensor Core 利用率；nsys（Nsight Systems）看时间线和通信重叠。</p></div>
<div class="qa-summary">GPU-Util → SM Active → SM Occupancy → 功耗，逐层下钻，从粗到细定位瓶颈。</div>
</div>
</div>
</div>

<div class="card card-m">
<h3>性能预测特征工程实战</h3>
<p>构建 GPU 性能预测模型时，特征的选择和构造直接决定预测精度。以下是面向科研和工程的特征工程指南。</p>

<div class="qa-section"><div class="qa-section-title">输入特征库 (X) 设计</div>
<table>
<tr><th>类别</th><th>特征</th><th>来源</th><th>预测价值</th></tr>
<tr><td rowspan="3">算法特征</td><td>FLOPs（前向/反向）</td><td>模型结构分析</td><td>核心工作量，预测时间的分子</td></tr>
<tr><td>Activation Memory</td><td>模型结构 + Batch Size</td><td>预测显存需求和重计算开销</td></tr>
<tr><td>Arithmetic Intensity</td><td>FLOPs / 访存量</td><td>分流预测：Compute-Bound vs Memory-Bound</td></tr>
<tr><td rowspan="4">硬件特征</td><td>Peak FLOPS（各精度）</td><td>GPU Spec</td><td>跨显卡泛化的核心特征</td></tr>
<tr><td>Memory Bandwidth</td><td>GPU Spec</td><td>Memory-Bound 算子的时间预测基准</td></tr>
<tr><td>NVLink / PCIe 带宽</td><td>GPU Spec</td><td>多卡通信时间预测</td></tr>
<tr><td>SM 数量 / Warp 上限</td><td>GPU Spec</td><td>Occupancy 上限计算</td></tr>
<tr><td rowspan="3">部署特征</td><td>3D 并行拓扑（TP/PP/DP）</td><td>用户配置</td><td>通信量和计算分配的核心决定因素</td></tr>
<tr><td>Micro Batch Size</td><td>用户配置</td><td>影响 Occupancy 和通信频率</td></tr>
<tr><td>Gradient Accumulation Steps</td><td>用户配置</td><td>影响有效 Batch Size 和通信频率</td></tr>
</table>
</div>

<div class="qa-section"><div class="qa-section-title">输出标签库 (Y) 设计</div>
<table>
<tr><th>类别</th><th>标签</th><th>预测意义</th><th>典型精度目标</th></tr>
<tr><td>时间</td><td>Step Time / Iteration Time</td><td>训练速度的直接度量</td><td>±10% 以内</td></tr>
<tr><td>效率</td><td>MFU</td><td>分布式训练效率的黄金标准</td><td>±5% 以内</td></tr>
<tr><td>空间</td><td>Peak Active Memory</td><td>防 OOM 调度核心</td><td>±5% 以内</td></tr>
<tr><td>空间</td><td>SM Active / Occupancy</td><td>空间利用率诊断</td><td>±10% 以内</td></tr>
<tr><td>通信</td><td>Communication Time</td><td>多卡扩展效率</td><td>±15% 以内</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么预测 Step Time 比 MFU 更难？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">MFU 是归一化指标</div><p>MFU = 实际吞吐 / 理论峰值，已经消除了硬件绝对性能的影响。同一模型在不同硬件上的 MFU 差异通常在 10% 以内。</p></div>
<div class="qa-section"><div class="qa-section-title">Step Time 受硬件绝对性能影响</div><p>Step Time = FLOPs / (Peak FLOPS × MFU) + Communication Time + Data Loading Time。需要精确预测每个分项，误差会累积。</p></div>
<div class="qa-section"><div class="qa-section-title">通信时间最难预测</div><p>NCCL 通信时间受网络拓扑、拥塞、消息大小、集合通信算法等多个因素影响，变异性大。</p></div>
<div class="qa-summary">MFU 是相对指标，泛化性好；Step Time 是绝对指标，需要精确建模每个分项。预测 MFU 后再乘以硬件参数得到 Step Time 是更稳健的策略。</div>
</div>
</div>
</div>

<div class="card card-d">
<h3>DCGM 指标采集与实战</h3>
<p>NVIDIA DCGM（Data Center GPU Manager）是生产环境 GPU 指标采集的标准工具。了解它提供的指标对性能预测和集群调度至关重要。</p>

<table>
<tr><th>DCGM 指标</th><th>含义</th><th>对应概念</th><th>采集方式</th></tr>
<tr><td>DCGM_FI_DEV_GPU_UTIL</td><td>GPU 计算利用率</td><td>GPU-Util</td><td>dcgmi dmon -e 100</td></tr>
<tr><td>DCGM_FI_DEV_MEM_COPY_UTIL</td><td>显存带宽利用率</td><td>Memory Util</td><td>dcgmi dmon -e 101</td></tr>
<tr><td>DCGM_FI_DEV_SM_ACTIVITY</td><td>SM 活跃度</td><td>SM Active</td><td>dcgmi dmon -e 141</td></tr>
<tr><td>DCGM_FI_DEV_SM_OCCUPANCY</td><td>SM 占有率</td><td>SM Occupancy</td><td>dcgmi dmon -e 142</td></tr>
<tr><td>DCGM_FI_DEV_FB_USED</td><td>显存使用量</td><td>VRAM Allocated</td><td>dcgmi dmon -e 25</td></tr>
<tr><td>DCGM_FI_DEV_POWER_USAGE</td><td>实时功耗</td><td>Power</td><td>dcgmi dmon -e 14</td></tr>
<tr><td>DCGM_FI_DEV_PCIE_TX_THRU</td><td>PCIe 发送吞吐</td><td>PCIe Bandwidth</td><td>dcgmi dmon -e 17</td></tr>
<tr><td>DCGM_FI_DEV_NVLINK_THRU</td><td>NVLink 吞吐</td><td>NVLink Bandwidth</td><td>dcgmi dmon -e 220</td></tr>
</table>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: DCGM 和 nvidia-smi 有什么区别？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">nvidia-smi</div><p>单机命令行工具，适合手动查看。采样频率低（约 1/6 秒），指标种类有限（GPU-Util、Memory Util、显存占用、功耗）。</p></div>
<div class="qa-section"><div class="qa-section-title">DCGM</div><p>数据中心级 GPU 管理服务，支持多机采集、持续监控、字段级策略。提供更丰富的指标（SM Active、SM Occupancy、NVLink 吞吐等），是生产环境 GPU 监控的标准方案。</p></div>
<div class="qa-section"><div class="qa-section-title">ncu / nsys</div><p>Nsight Compute / Systems 是深度 profiling 工具，提供 kernel 级别的详细分析（Warp 效率、指令吞吐、内存事务），但开销大，不适合生产环境持续采集。</p></div>
<div class="qa-summary">nvidia-smi = 快速查看，DCGM = 生产监控，ncu/nsys = 深度分析。性能预测通常用 DCGM 指标做特征。</div>
</div>
</div>
</div>

<div class="card card-d">
<h3>官方参考</h3>
<div class="resource-grid">
<a class="resource-card" href="https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/feature-overview.html"><div class="resource-type">official</div><div class="resource-title">DCGM Feature Overview</div><div class="resource-desc">DCGM 指标字段完整列表和采集方式。</div></a>
<a class="resource-card" href="https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html"><div class="resource-type">official</div><div class="resource-title">Nsight Compute Profiling Guide</div><div class="resource-desc">SM Occupancy、Roofline、Kernel 分析详解。</div></a>
<a class="resource-card" href="https://arxiv.org/abs/2205.05937"><div class="resource-type">paper</div><div class="resource-title">FlashAttention</div><div class="resource-desc">IO-Aware 优化，Arithmetic Intensity 分析的经典案例。</div></a>
<a class="resource-card" href="https://arxiv.org/abs/2104.04473"><div class="resource-type">paper</div><div class="resource-title">Megatron-LM v3</div><div class="resource-desc">3D 并行策略、MFU 定义和测量方法。</div></a>
<a class="resource-card" href="https://developer.nvidia.com/blog/understanding-the-nvidia-ampere-architecture/"><div class="resource-type">official</div><div class="resource-title">Understanding Ampere Architecture</div><div class="resource-desc">SM、Warp、Tensor Core 的硬件原理。</div></a>
</div>
</div>

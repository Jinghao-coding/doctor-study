## 一句话结论

GPU 集群管理这一节需要服务面试复习：先给结论，再把链路、机制、权衡和回答模板讲清楚。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | GPU 集群管理 |
| 章节类型 | 系统类 |
| 解决问题 | 围绕调度框架、多租户、拓扑通信、故障容错和面试问答建立集群管理答案。 |
| 面试抓手 | 回答时先定范围，再讲核心链路，最后落到工程风险和面试追问。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m">
<h3>GPU 拓扑与通信：为什么"同是 8 卡"性能可以差 3 倍？</h3>
<p>两个训练任务都用了 8 张 A100，一个跑 AllReduce 需要 50ms，另一个需要 150ms。差异来自<strong>拓扑</strong>——8 张 GPU 在物理上怎么连接的。同一节点内 NVLink 互联的 8 卡，和跨两个节点 InfiniBand 互联的 8 卡，通信性能差 3-5 倍。</p>
<p>拓扑感知调度的核心洞察是：<strong>GPU 不是可互换的——同一数量的 GPU，不同拓扑下的通信性能差异巨大</strong>。调度器必须理解拓扑，把对通信敏感的任务放到拓扑更优的位置。</p>
<p><strong>怎么理解</strong>：同样 8 个人开会，坐在同一张桌子旁（NVLink）和在两个会议室视频连线（InfiniBand），沟通效率完全不同。</p>
</div>

<div class="card card-s">
<h3>拓扑层次详解</h3>
<table>
<tr><th>层级</th><th>互联</th><th>带宽</th><th>延迟</th><th>量级差异</th><th>训练通信影响</th></tr>
<tr><td>GPU 内部</td><td>SM ↔ HBM</td><td>2-4.8 TB/s</td><td>ns 级</td><td>基准</td><td>计算本身，不是瓶颈</td></tr>
<tr><td>节点内 GPU 间</td><td>NVLink / NVSwitch</td><td>300-900 GB/s</td><td>~1-5 μs</td><td>比节点间快 10-50x</td><td>TP 并行的生命线</td></tr>
<tr><td>节点内 CPU-GPU</td><td>PCIe Gen4/5</td><td>32-64 GB/s</td><td>~5-10 μs</td><td>比 NVLink 慢 10-20x</td><td>数据加载、ZeRO 参数获取</td></tr>
<tr><td>节点间</td><td>InfiniBand / RoCE</td><td>200-400 Gbps (25-50 GB/s)</td><td>~5-10 μs</td><td>比 NVLink 慢 10-20x</td><td>DP/PP 通信，可接受</td></tr>
<tr><td>机柜间</td><td>Spine 交换机</td><td>几百 Gbps</td><td>几十 μs</td><td>比节点间慢 5-10x</td><td>尽力避免跨机柜通信</td></tr>
</table>

<h4>NVLink vs PCIe vs InfiniBand：关键区别</h4>
<p><strong>NVLink</strong>：NVIDIA 专有高速互联，GPU 之间直接通信，不经过 CPU。A100 每张卡 12 条 NVLink，总带宽 600 GB/s；H100 升级到 900 GB/s。NVLink 是张量并行的<strong>必要条件</strong>——没有 NVLink，TP 的通信延迟会让 GPU 大部分时间在等数据。</p>
<p><strong>NVSwitch</strong>：NVLink 的交换芯片，让节点内所有 GPU 两两直连。8 卡 A100 服务器用 6 个 NVSwitch，实现 8 卡全互联（每对 GPU 间都有 NVLink）。没有 NVSwitch，8 卡只能部分互联（有些 GPU 对走 PCIe）。</p>
<p><strong>PCIe</strong>：通用总线，CPU 和 GPU 之间的标准通道。Gen4 x16 带宽 32 GB/s，Gen5 翻倍。GPU 间也可以走 PCIe（没有 NVLink 连接的 GPU 对），但带宽远低于 NVLink。</p>
<p><strong>InfiniBand</strong>：节点间高速网络，HDR 200 Gbps，NDR 400 Gbps。RDMA 能力让 GPU 可以直接写入远端 GPU 显存，不经 CPU。NCCL 默认使用 InfiniBand 做跨节点通信。</p>
<p><strong>怎么理解</strong>：NVLink 是"高铁"（节点内、超高速、专用轨道），PCIe 是"国道"（通用、较慢），InfiniBand 是"飞机"（跨城市、快速但有起飞延迟）。</p>

<h4>拓扑发现：调度器怎么知道拓扑？</h4>
<p>调度器需要知道每张 GPU 在哪个节点、和哪些 GPU 有 NVLink 连接。信息来源：</p>
<ol>
<li><strong>nvidia-smi topo -m</strong>：输出 GPU 拓扑矩阵，显示每对 GPU 之间的连接类型（NVLink/PCIe/SYS）。调度器可以定期采集。</li>
<li><strong>NFD（Node Feature Discovery）</strong>：自动发现节点硬件特征，打标签到 Node 对象上。如 <code>nvidia.com/gpu.topology=NVSwitch</code>。</li>
<li><strong>Device Plugin</strong>：NVIDIA device plugin 可以在 Allocate 时返回拓扑信息。但标准 device plugin 不传递拓扑，需要扩展。</li>
</ol>
</div>

<div class="card card-d">
<h3>集合通信原语详解</h3>
<p>分布式训练的核心通信操作由 NCCL 实现。理解每个原语的语义，才能理解不同并行策略为什么对拓扑有不同的偏好。</p>

<h4>1. AllReduce</h4>
<p><strong>操作</strong>：所有节点贡献数据，聚合（如求和）后结果广播回所有节点。</p>
<p><strong>训练用途</strong>：数据并行的梯度同步。每个 worker 算完本地梯度后，AllReduce 求平均。</p>
<p><strong>通信量</strong>：O(N × data_size)。Ring AllReduce 可以优化到 O(2(N-1)/N × data_size)。</p>
<p><strong>拓扑敏感性</strong>：中等。AllReduce 的通信量取决于模型大小，不是拓扑结构。但拓扑决定每次 AllReduce 的完成时间——NVLink 互联的 8 卡比跨节点 8 卡快 3-5 倍。</p>
<p><strong>怎么理解</strong>：8 个人各自算了一道题的部分答案，现在要把所有人的部分答案汇总，然后每个人拿到完整答案。</p>

<h4>2. AllGather</h4>
<p><strong>操作</strong>：每个节点贡献自己的数据，所有节点收集所有数据。</p>
<p><strong>和 AllReduce 的区别</strong>：AllReduce 先 Reduce（聚合）再广播结果，每个节点拿到的是聚合值。AllGather 不聚合，每个节点拿到的是所有节点的原始数据。</p>
<p><strong>训练用途</strong>：张量并行的前向/反向传播——每个 TP rank 计算局部结果，AllGather 拼出完整结果。</p>
<p><strong>拓扑敏感性</strong>：极高。AllGather 的通信量 = 所有 rank 的数据总量，比 AllReduce 大。必须走 NVLink，否则通信时间 >> 计算时间。</p>

<h4>3. ReduceScatter</h4>
<p><strong>操作</strong>：先 Reduce（聚合），再 Scatter（每个节点只拿自己负责的分片）。</p>
<p><strong>训练用途</strong>：ZeRO 优化器的梯度分片——ReduceScatter 后每个 rank 只保留自己负责的梯度分片，不需要完整的梯度。</p>
<p><strong>通信量</strong>：比 AllReduce 少——最终每个节点只拿 data_size/N 的数据。</p>
<p><strong>怎么理解</strong>：8 个人汇总答案后，每人只拿走自己负责的那部分，不需要完整答案。</p>

<h4>4. Broadcast</h4>
<p><strong>操作</strong>：一个节点（root）把数据广播给所有节点。</p>
<p><strong>训练用途</strong>：参数初始化（rank 0 广播初始权重）、模型同步。</p>
<p><strong>通信量</strong>：O(N × data_size)。但只需一个方向（root → others），比 AllReduce 少一半。</p>

<h4>5. P2P Send/Recv</h4>
<p><strong>操作</strong>：点对点传输，一个节点发送，一个节点接收。</p>
<p><strong>训练用途</strong>：流水线并行的 stage 间传递——stage 0 算完把中间激活发给 stage 1。</p>
<p><strong>拓扑敏感性</strong>：低。每次只传一对，带宽需求小。跨节点走 InfiniBand 可以接受。</p>
<p><strong>怎么理解</strong>：流水线上游把半成品递给下游，只有相邻两个 stage 在交互。</p>

<h4>6. All-to-All</h4>
<p><strong>操作</strong>：每个节点向所有其他节点发送不同的数据，同时从所有其他节点接收不同的数据。</p>
<p><strong>训练用途</strong>：MoE 模型的专家并行——token 被路由到不同专家所在的 GPU。</p>
<p><strong>拓扑敏感性</strong>：极高。通信量 O(N² × data_size/N)，所有节点对之间都有数据传输，对网络 bisection bandwidth 要求极高。</p>
</div>

<div class="card card-w">
<h3>并行策略的拓扑偏好</h3>
<p>不同并行策略对通信的要求不同，这直接决定了调度时应该把任务放在什么拓扑位置：</p>
<table>
<tr><th>策略</th><th>通信原语</th><th>通信频率</th><th>单次通信量</th><th>拓扑偏好</th><th>为什么</th></tr>
<tr><td>数据并行（DP）</td><td>AllReduce</td><td>每步 1 次</td><td>模型参数量 × 2</td><td>节点间即可</td><td>每步才同步一次，InfiniBand 带宽够用</td></tr>
<tr><td>张量并行（TP）</td><td>AllGather + ReduceScatter</td><td>每层前向+反向各 2 次</td><td>层参数量 × 2</td><td>必须同节点（NVLink）</td><td>每层都通信，频率极高，NVLink 是硬需求</td></tr>
<tr><td>流水线并行（PP）</td><td>P2P Send/Recv</td><td>每 micro-batch 1 次</td><td>激活值大小</td><td>可跨节点</td><td>点对点通信，量不大，InfiniBand 可接受</td></tr>
<tr><td>专家并行（EP）</td><td>All-to-All</td><td>每层 1 次</td><td>token 数 × hidden_dim</td><td>NVLink + 高带宽网络</td><td>All-to-All 需要全网带宽，拓扑要求最苛刻</td></tr>
<tr><td>ZeRO-3</td><td>AllGather + ReduceScatter</td><td>每层前向+反向各 1 次</td><td>参数分片量</td><td>节点间即可（DP 变体）</td><td>本质是 DP 的内存优化，通信模式类似</td></tr>
</table>

<h4>关键洞察：TP 必须同节点</h4>
<p>这是面试中最高频的拓扑问题。为什么 TP 必须放在同一 NVLink 节点内？</p>
<p><strong>数学推导</strong>：假设训练 GPT-3（175B 参数，96 层）。TP=8，每层 AllGather 通信量 ≈ 175B × 2 bytes / 8 ≈ 43.75 GB。前向 + 反向 = 4 次/层，96 层共 384 次 AllGather。</p>
<ul>
<li><strong>NVLink（600 GB/s）</strong>：43.75 GB / 600 GB/s ≈ 73ms/次。384 次 ≈ 28s/step。</li>
<li><strong>InfiniBand（50 GB/s）</strong>：43.75 GB / 50 GB/s ≈ 875ms/次。384 次 ≈ 336s/step。</li>
</ul>
<p>NVLink 下通信占训练时间的约 30%（可接受）。InfiniBand 下通信占训练时间的 90%+（不可接受——GPU 90% 时间在等数据）。所以 TP 必须 NVLink。</p>
</div>

<div class="card card-m">
<h3>3D 并行拓扑布局实战</h3>
<p>大模型训练通常组合 DP + TP + PP。以 64 GPU 训练 175B 模型为例：</p>
<ul>
<li><strong>TP = 8</strong>：节点内 8 卡 NVLink 互联，通信量最大但带宽最高</li>
<li><strong>PP = 4</strong>：跨 4 个节点做流水线，P2P 通信量小</li>
<li><strong>DP = 2</strong>：两组流水线做数据并行，AllReduce 同步梯度</li>
</ul>
<p><strong>物理布局</strong>：</p>
<pre>
节点 0: [TP group 0] ← NVLink → GPU 0-7
节点 1: [TP group 1] ← NVLink → GPU 8-15
节点 2: [TP group 2] ← NVLink → GPU 16-23
节点 3: [TP group 3] ← NVLink → GPU 24-31
节点 4: [TP group 4] ← NVLink → GPU 32-39
节点 5: [TP group 5] ← NVLink → GPU 40-47
节点 6: [TP group 6] ← NVLink → GPU 48-55
节点 7: [TP group 7] ← NVLink → GPU 56-63

Pipeline 0: 节点 0 → 节点 1 → 节点 2 → 节点 3  (PP=4, P2P over IB)
Pipeline 1: 节点 4 → 节点 5 → 节点 6 → 节点 7  (PP=4, P2P over IB)

DP group 0: Pipeline 0 和 Pipeline 1 之间 AllReduce 梯度 (DP=2, over IB)
</pre>
<p><strong>调度器的任务</strong>：确保 TP group 分配在同一节点，PP stage 尽量在同一机柜（减少 InfiniBand 跳数），DP group 可以跨机柜。</p>
<p><strong>怎么理解</strong>：像一个大型工程项目。8 个密切协作的工程师坐同一办公室（TP，高频沟通），4 个办公室依次传递半成品（PP，低频但有序），两组流水线定期同步进度（DP，频率最低）。</p>
</div>

<div class="card card-d">
<h3>NCCL：拓扑感知通信引擎</h3>
<p>NCCL（NVIDIA Collective Communication Library）是分布式训练通信的底层引擎。它自动根据 GPU 拓扑选择最优通信路径。</p>

<h4>NCCL 通道选择逻辑</h4>
<p>NCCL 检测 GPU 之间的所有可用路径，构建拓扑图，然后为每次集合通信选择最优通道：</p>
<ol>
<li><strong>节点内</strong>：优先 NVLink → 次选 PCIe → 最后 SYS（跨 NUMA）</li>
<li><strong>节点间</strong>：优先 InfiniBand → 次选 RoCE → 最后 Socket</li>
<li><strong>混合</strong>：NVLink 用于节点内 reduce，InfiniBand 用于节点间 scatter/gather</li>
</ol>
<p><strong>NCCL_TOPO_FILE</strong>：NCCL 读取拓扑文件来决定通道。调度器可以通过设置这个环境变量来影响 NCCL 的路径选择——例如告诉 NCCL "这些 GPU 在同一个机柜内，可以用更激进的树形算法"。</p>

<h4>Ring AllReduce 的拓扑依赖</h4>
<p>Ring AllReduce 是 NCCL 最常用的 AllReduce 算法。它把所有 GPU 排成一个逻辑环，数据在环上分步传递。</p>
<p><strong>拓扑要求</strong>：环上相邻 GPU 之间需要高带宽。如果环跨越了低带宽链路（如 PCIe 替代 NVLink），该链路成为瓶颈——环的速度取决于最慢的那一跳。</p>
<p><strong>NCCL 的优化</strong>：NCCL 会构建多个环，避免所有数据走同一条路径。在 8 卡 NVSwitch 服务器中，NCCL 通常构建 4 个环，充分利用 NVLink 的带宽。</p>

<h4>NCCL 超时：最常见的训练故障</h4>
<p><strong>现象</strong>：训练卡住，日志显示 <code>NCCL error: timeout</code>。</p>
<p><strong>原因</strong>：某个 rank 没有按时到达同步点。可能原因：(1) Gang 不完整——某个 worker 没启动成功；(2) 网络分区——某个节点网络断了；(3) GPU 挂了——ECC 错误导致 GPU 不可用但没被检测到；(4) 负载不均——某个 rank 的计算量特别大，其他 rank 等待超时。</p>
<p><strong>调度层面的解决</strong>：(1) Gang scheduling 确保所有 worker 同时启动；(2) 拓扑感知调度确保所有 worker 在合理拓扑内；(3) 健康检查——调度前确认节点和 GPU 健康；(4) NCCL 超时时间设置——太短导致误报，太长导致故障发现慢。</p>
</div>

<div class="card card-w">
<h3>拓扑与通信面试问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 TP 必须在同一节点？可以用 InfiniBand 替代 NVLink 吗？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>不行。TP 的通信频率是"每层每步 4 次"（前向 AllGather + ReduceScatter，反向 AllGather + ReduceScatter），96 层模型一步就有 384 次集合通信。NVLink（600 GB/s）下单次 AllGather 约 73ms，InfiniBand（50 GB/s）下约 875ms——慢 12 倍。384 次累积下来，InfiniBand 下训练一步的通信时间占 90%+，GPU 基本在等数据。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么 DP 可以跨节点</div><p>DP 每步只做 1 次 AllReduce，通信频率低一个量级。即使 InfiniBand 慢一些，通过 gradient accumulation + 通信-计算重叠，可以把通信时间隐藏在计算时间内。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"TP 和 DP 的本质区别是通信频率——TP 每层都要通信，DP 每步才通信一次。频率差两个量级，所以 TP 需要高一个量级的带宽。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 调度器怎么做拓扑感知？有哪些实现路径？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>五条实现路径，从简到复杂：</p>
<ol>
<li><strong>Node Label</strong>：给节点打标签（如 <code>topology=nvswitch</code>），Pod 通过 nodeSelector 选择。最简单，但粒度粗（只区分节点类型，不知道具体 GPU 拓扑）。</li>
<li><strong>NFD + NodeFeature</strong>：NFD 自动发现硬件特征（GPU 数量、NVLink 拓扑、InfiniBand 卡数），写入 Node 对象。调度器根据这些特征打分。比手动标签更准确，但 NFD 不感知 GPU 间的具体拓扑。</li>
<li><strong>Device Plugin 扩展</strong>：扩展 NVIDIA device plugin，在 Allocate 时返回 GPU 拓扑信息（哪些 GPU 有 NVLink 连接）。调度器据此做拓扑感知的分配。但 device plugin 的 Allocate 回调在调度决策之后，无法影响初始调度。</li>
<li><strong>Scheduler Plugin</strong>：写自定义的 Scheduling Framework 插件，在 Score 阶段根据拓扑信息给节点打分。例如"Pod 请求 4 GPU，这个节点有 4 张 NVLink 互联的 GPU → 高分"。控制力最强，但开发复杂。</li>
<li><strong>DRA（Dynamic Resource Allocation）</strong>：K8S 1.26+ 引入的新机制，通过 ResourceSlice 表达拓扑。调度器选择 ResourceSlice，驱动程序（driver）根据拓扑做精确分配。这是最优雅的方案，但还处于 Alpha/Beta 阶段。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">推荐路径</div><p>短期用 Node Label + NFD（够用，低风险），中期上 Scheduler Plugin（更精细），长期迁移到 DRA（K8S 原生支持，标准路径）。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"拓扑感知的实现路径不是一蹴而就的——从 Node Label 到 NFD 到 Scheduler Plugin 到 DRA，逐步演进。关键是当前阶段选择够用的方案，不追求一步到位。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: NCCL 通信卡住（超时）怎么排查？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>NCCL 超时的排查按"从上到下"的顺序：</p>
<ol>
<li><strong>检查 Gang 完整性</strong>：是不是所有 worker 都启动了？<code>kubectl get pods</code> 看 Pending 的 Pod。如果一个 worker 没启动，其他 worker 会永远等在 NCCL init。</li>
<li><strong>检查网络连通性</strong>：<code>nccl-test</code> 或 <code>ibv_devinfo</code> 检查 InfiniBand 是否正常。<code>ping</code> 检查节点间网络。网络分区是 NCCL 超时的常见原因。</li>
<li><strong>检查 GPU 健康</strong>：<code>nvidia-smi</code> 检查 GPU 是否正常。ECC 错误、温度过高都可能导致 GPU 无响应。</li>
<li><strong>检查 NCCL 配置</strong>：<code>NCCL_DEBUG=INFO</code> 查看详细日志。常见的配置问题：NCCL_SOCKET_IFNAME 设错（用了管理网络而非高速网络）、NCCL_IB_DISABLE=1 没开 IB。</li>
<li><strong>检查负载不均</strong>：某个 rank 处理的数据量特别大（数据倾斜），其他 rank 等待超时。检查数据分片策略。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">调度层面的预防</div><p>(1) Gang scheduling 防止部分启动；(2) 拓扑感知调度确保合理拓扑；(3) 节点健康检查在调度前排除故障节点；(4) 合理设置 <code>NCCL_COMM_BLOCKING</code> 和超时时间。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"NCCL 超时 80% 的原因是 Gang 不完整或网络问题，不是 NCCL 本身的 bug。先查 Pod 状态和网络，再看 NCCL 日志。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Ring AllReduce 和 Tree AllReduce 有什么区别？各适合什么场景？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><table>
<tr><th>维度</th><th>Ring AllReduce</th><th>Tree AllReduce</th></tr>
<tr><td>算法</td><td>GPU 排成环，数据分步沿环传递</td><td>GPU 排成树，先向上 reduce 再向下 broadcast</td></tr>
<tr><td>通信步数</td><td>2(N-1) 步（N = GPU 数）</td><td>2log(N) 步</td></tr>
<tr><td>每步通信量</td><td>data_size / N（均匀分片）</td><td>取决于树层级，根节点通信量最大</td></tr>
<tr><td>带宽利用</td><td>均匀——每个 GPU 发送接收量相同</td><td>不均匀——根节点是瓶颈</td></tr>
<tr><td>延迟</td><td>O(N)——步数线性增长</td><td>O(log N)——步数对数增长</td></tr>
</table></div>
<div class="qa-section"><div class="qa-section-title">适用场景</div><p>(1) <strong>小规模 + 高带宽</strong>（节点内 8 卡 NVLink）→ Ring AllReduce。延迟 O(N) 但 N=8 很小，带宽利用均匀。(2) <strong>大规模 + 节点间</strong>（64+ GPU 跨节点）→ Tree AllReduce 或 Ring + Tree 混合。延迟 O(log N) 在大规模下优势明显。(3) <strong>NCCL 的实际做法</strong>：节点内用 Ring，节点间用 Tree（或 CollNet，如果交换机支持）。混合策略兼顾延迟和带宽。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"Ring 和 Tree 不是非此即彼——Ring 带宽均匀但延迟线性，Tree 延迟对数但根节点瓶颈。实际系统都是混合使用：节点内 Ring，节点间 Tree。"</p></div>
</div>
</div>
</div>

## 面试回答

**30 秒版：**

GPU 集群管理这一节需要先定范围，再把机制和工程边界讲清楚。 按结论、链路、权衡、风险回答。

**2 分钟版：**

我会先说明这个问题在 GPU 集群管理 里的位置，再拆核心链路：输入是什么、系统如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：吞吐和延迟、显存和计算、隔离和利用率、简单实现和生产稳定性之间如何取舍。最后用观测指标或排障路径收束，说明如何判断方案真的有效。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

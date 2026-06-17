## 一句话结论

拓扑感知调度优化的不是 GPU 数量，而是 rank 通信图到硬件数据路径图的映射代价：节点内 NVLink/NVSwitch 比跨机 InfiniBand 快 10-50 倍，而通信又占训练时间 30-50%，所以 Tensor Parallel/MoE 必须放进同一 NVLink 域、GPU 与 NIC 要做 NUMA 对齐，再用拓扑质量阈值在等待时间和训练性能之间权衡。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 任务调度理论 |
| 章节类型 | 系统类 |
| 解决问题 | 围绕经典算法、多资源公平、Gang/Backfill、拓扑感知和抢占代价建立 GPU 集群调度理论答案。 |
| 面试抓手 | 回答时先定范围，再讲核心链路，最后落到工程风险和面试追问。 |

<div class="card card-m">
<h3>拓扑感知调度：GPU 集群调度的核心差异点</h3>
<p>普通 CPU 调度通常只关心资源数量是否足够，而 GPU 训练调度必须关心"资源之间的连接关系"。同样是 8 张 GPU，同机 NVSwitch、同机 PCIe、跨机 RDMA、跨机柜网络，对训练吞吐的影响完全不同。</p>
<p>为什么拓扑这么重要？因为大模型训练的通信时间可能占到总训练时间的 30-50%。如果 8 张 GPU 在同一节点用 NVLink 互联，AllReduce 一个 1GB 的梯度张量可能只需要 0.5ms；但如果 8 张 GPU 分散在 4 个节点走 InfiniBand，同样的操作可能需要 5ms。10 倍的差距，乘以每步训练都要做一次，最终训练速度可能差 2 倍以上。</p>
</div>

<div class="card card-s">
<h3>拓扑层次：从芯片到机房</h3>
<p>理解拓扑感知调度，必须先理解 GPU 集群的物理拓扑层次。每一层有不同的带宽、延迟和调度含义。</p>

<table>
<tr><th>层次</th><th>典型连接</th><th>带宽</th><th>延迟</th><th>调度含义</th></tr>
<tr><td>GPU 内部</td><td>SM、HBM、L2</td><td>2-4.8 TB/s</td><td>ns 级</td><td>影响单卡性能，不由调度器直接控制</td></tr>
<tr><td>节点内 GPU 间</td><td>NVLink / NVSwitch</td><td>300-900 GB/s</td><td>μs 级</td><td>张量并行必须放这里，通信密集型任务的最高优先级放置</td></tr>
<tr><td>CPU-GPU</td><td>PCIe Gen4/5</td><td>32-64 GB/s</td><td>μs 级</td><td>数据加载和 host-device copy 需要 NUMA 亲和</td></tr>
<tr><td>节点间</td><td>InfiniBand / RoCE</td><td>200-400 Gbps</td><td>几 μs</td><td>数据并行和流水线并行的跨节点通信</td></tr>
<tr><td>机架/机柜</td><td>ToR 交换机</td><td>几百 Gbps</td><td>几十 μs</td><td>大规模训练要减少跨机柜通信，避免拥塞</td></tr>
</table>

<h4>怎么理解这些数字</h4>
<p>关键不是记住具体数字，而是理解<strong>量级差异</strong>：</p>
<ul>
<li>NVLink 比 InfiniBand 快 <strong>10-50 倍</strong>（900 GB/s vs 50 GB/s）</li>
<li>InfiniBand 比以太网快 <strong>5-10 倍</strong>（400 Gbps vs 40-100 Gbps）</li>
<li>同节点 vs 跨节点的延迟差 <strong>1-2 个数量级</strong></li>
</ul>
<p>这些量级差异决定了：如果你把需要频繁通信的 worker 放错了位置，性能可能直接腰斩。</p>
</div>

<div class="card card-d">
<h3>通信路径模型：调度器真正要优化的对象</h3>
<p>拓扑感知调度不是简单地区分“同机”和“跨机”，而是要把训练通信映射到真实数据路径上。单机内 GPU-GPU 通信优先使用 NVLink/NVSwitch；CPU、GPU、NIC、NVMe 等设备之间通过 PCIe 连接；跨机 GPU-GPU 通信则依赖 NIC + InfiniBand/RoCE RDMA，理想情况下使用 GPUDirect RDMA 直接读写 GPU HBM。</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">识别 rank 通信图</div><div class="flow-desc">TP、DP、PP、MoE 的通信频率和通信量不同</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">映射硬件路径</div><div class="flow-desc">NVLink/NVSwitch、PCIe、GPU-NIC、RDMA、机架网络</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">过滤硬约束</div><div class="flow-desc">GPU 型号、显存、完整 NVSwitch 域、NIC 亲和、NUMA</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">按代价打分</div><div class="flow-desc">惩罚跨 Socket、host staging、跨机架、网络拥塞和碎片化</div></div>
<div class="flow-step"><div class="flow-index">05</div><div class="flow-title">绑定设备组合</div><div class="flow-desc">锁定具体 GPU/NIC，避免并发调度破坏拓扑假设</div></div>
</div>
<p>因此，调度器看待“4 张 GPU”时不应该只看数量，而要判断它们之间的路径：同 NVSwitch 域的 4 卡、同 PCIe switch 的 4 卡、跨 Socket 的 4 卡、跨机器 2+2，通信代价完全不同。跨机训练还要继续看 GPU 到 NIC 是否同 NUMA、RDMA 是否能走 GPUDirect、是否会退化成 CPU host staging。</p>
<div class="qa-summary">面试金句：拓扑感知调度优化的不是 GPU 数量，而是 rank 通信图到硬件数据路径图的映射代价。</div>
</div>

<div class="card card-d">
<h3>不同并行策略的拓扑偏好</h3>
<p>这是拓扑感知调度最核心的知识点。面试中经常问"为什么张量并行要放在同节点"。下面的表格解释了每种并行策略为什么有特定的拓扑偏好。</p>

<table>
<tr><th>并行策略</th><th>通信模式</th><th>通信频率</th><th>通信量/步</th><th>放置偏好</th><th>为什么</th></tr>
<tr><td>数据并行</td><td>AllReduce 梯度同步</td><td>每步一次</td><td>模型参数量 × 2/N（Ring AllReduce）</td><td>跨节点可行，但需要高带宽低延迟网络</td><td>通信量与参数量成正比，但 Ring AllReduce 均摊到 N 个节点，单个节点负载不高</td></tr>
<tr><td>张量并行</td><td>层内 AllReduce/AllGather</td><td>每层前向+反向各一次</td><td>激活值大小 × 层数 × 2</td><td>强依赖节点内 NVLink/NVSwitch</td><td>通信频率极高（每层都通信），如果走网络会严重拖慢训练</td></tr>
<tr><td>流水线并行</td><td>相邻 stage P2P 通信</td><td>每个 micro-batch</td><td>激活值大小</td><td>相邻 stage 靠近，跨节点也可接受</td><td>通信量小（只传激活值），P2P 不需要全局同步，网络能承受</td></tr>
<tr><td>专家并行</td><td>All-to-All</td><td>每层 MoE</td><td>专家路由的 token 分布</td><td>需要避免跨拥塞域</td><td>All-to-All 是最重的通信模式，每个 GPU 都要和所有其他 GPU 通信</td></tr>
<tr><td>ZeRO-3</td><td>AllGather + ReduceScatter</td><td>前向+反向各 N 次</td><td>参数/梯度分片大小</td><td>通信量大，需要高带宽网络</td><td>虽然省显存，但通信开销比普通数据并行大 1.5-3 倍</td></tr>
</table>

<h4>3D 并行的典型拓扑布局</h4>
<p>大模型训练通常组合使用 DP + TP + PP。以 64 GPU（8 节点 × 8 卡）训练 175B 模型为例：</p>
<ul>
<li><strong>TP = 8</strong>：同一节点的 8 卡做张量并行，利用 NVLink 的高带宽处理频繁的层内通信</li>
<li><strong>PP = 4</strong>：跨 4 个节点做流水线，P2P 通信量小，走 InfiniBand 即可</li>
<li><strong>DP = 2</strong>：2 组流水线做数据并行，每个 micro-batch 结束同步梯度</li>
</ul>
<p><strong>调度含义</strong>：调度器需要知道这个任务需要 4 个"完整节点"（每个节点 8 GPU 全用），而不是 32 个散落的 GPU。如果只给 4 张 GPU 在同一节点、28 张分散在其他节点，TP=8 就做不了。</p>
</div>

<div class="card card-w">
<h3>拓扑感知调度的实现路径</h3>
<p>面试中经常问"怎么在 K8S 里实现拓扑感知调度"。答案不是唯一的，要看你的集群规模和精度需求。</p>

<h4>5 种实现方式对比</h4>
<table>
<tr><th>方式</th><th>做法</th><th>精度</th><th>适用场景</th><th>局限</th></tr>
<tr><td>Node Label</td><td>把 GPU 型号、机架位置标为 label</td><td>粗粒度（节点级）</td><td>简单场景，只要区分 GPU 型号</td><td>表达不了设备级拓扑（如哪几张 GPU 之间有 NVLink）</td></tr>
<tr><td>NodeFeatureDiscovery</td><td>自动发现节点硬件信息并发布为 label/extended resource</td><td>粗粒度（节点级）</td><td>不想手动维护 label</td><td>和 Node Label 一样，只到节点级</td></tr>
<tr><td>Device Plugin + Topology Manager</td><td>节点侧在设备分配时考虑 NUMA 亲和</td><td>中粒度（NUMA/PCIe 拓扑）</td><td>单节点内资源对齐</td><td>只管单节点，不管跨节点拓扑</td></tr>
<tr><td>Scheduler Plugin</td><td>在 Filter/Score 阶段读取拓扑信息，对节点或设备组合打分</td><td>细粒度（可到设备级）</td><td>需要跨节点拓扑感知</td><td>开发成本高，需要维护拓扑数据</td></tr>
<tr><td>DRA / ResourceSlice</td><td>把设备属性、容量和拓扑结构化发布，调度器基于设备级信息匹配</td><td>最细粒度</td><td>未来方向，结构化表达</td><td>K8S 1.26+ 才支持，生态尚不成熟</td></tr>
</table>

<h4>推荐方案</h4>
<p><strong>短期</strong>：Node Label（区分 GPU 型号和机架）+ Scheduler Plugin（Filter/Score 中加拓扑打分）</p>
<p><strong>长期</strong>：DRA + ResourceSlice（结构化表达设备拓扑，调度器原生支持）</p>
</div>

<div class="card card-m">
<h3>拓扑调度的目标函数</h3>
<p>拓扑感知调度不是"让所有任务都拿到最优拓扑"——那会导致大量 GPU 在等完美组合。而是要找到一个<strong>可接受的拓扑质量</strong>，在等待时间和训练性能之间权衡。</p>

<h4>五种目标</h4>
<table>
<tr><th>目标</th><th>含义</th><th>什么时候用</th><th>风险</th></tr>
<tr><td>最小通信代价</td><td>把通信频繁的 rank 放最近</td><td>张量并行、MoE</td><td>可能增加排队时间</td></tr>
<tr><td>最大局部性</td><td>优先同节点/同机柜</td><td>3D 并行</td><td>可能造成资源碎片</td></tr>
<tr><td>最小碎片</td><td>保留完整 GPU 组给大任务</td><td>多租户集群</td><td>可能牺牲当前任务的最优拓扑</td></tr>
<tr><td>故障域分散</td><td>避免所有副本在同一故障域</td><td>在线推理、高可用训练</td><td>增加通信开销</td></tr>
<tr><td>性能预测最优</td><td>根据模型预测不同放置的训练吞吐</td><td>有性能预测模型时</td><td>依赖预测准确性</td></tr>
</table>

<h4>怎么理解这些目标的冲突</h4>
<p>最小通信代价和最小碎片是矛盾的：把通信密集的 worker 都放在一起（最小通信代价），可能导致大块 GPU 组被拆散（碎片化增加）。实际中通常的做法是：设定一个拓扑质量阈值（如"至少 70% 的 worker 在同节点或同机柜"），超过阈值就不等了。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不能只用 node label 表达 GPU 拓扑？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>Node Label 只能表达节点级静态属性（如 GPU 型号、机架位置），但表达不了三类关键的设备级关系：</p>
<ol>
<li><strong>GPU 之间的互联关系</strong>："GPU 0 和 GPU 1 之间有 NVLink，但 GPU 0 和 GPU 2 之间走 PCIe"。这决定了哪些 GPU 组合更适合张量并行。</li>
<li><strong>GPU 与 NUMA 节点的亲和性</strong>："GPU 0 离 NUMA 节点 0 更近，数据加载应该用 NUMA 0 的 CPU"。这影响 host-device copy 的延迟。</li>
<li><strong>MIG slice 的归属</strong>："MIG slice 1c.0 和 1c.1 属于同一张物理 GPU，不能同时分配给不同任务"。这是资源互斥约束。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">怎么解决</div><p>用 Scheduler Plugin 在 Filter/Score 阶段读取拓扑数据（如 DCGM 导出的 NVLink 拓扑），或用 DRA 的 ResourceSlice 结构化表达。</p></div>
<div class="qa-summary">面试要点：Label 是节点级的，GPU 拓扑是设备级的。级别不同，Label 做不了。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果集群资源不够让所有任务都拿到最优拓扑，怎么权衡？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>设拓扑质量阈值，而不是追求全局最优。</p></div>
<div class="qa-section"><div class="qa-section-title">具体做法</div><p>(1) <strong>定义拓扑质量分数</strong>：如"同节点 GPU 占比 × 1.0 + 同机柜 GPU 占比 × 0.5 + 跨机柜 GPU 占比 × 0.1"。(2) <strong>设可接受阈值</strong>：如"拓扑分数 ≥ 0.7 就不等了，直接调度"。(3) <strong>超时降级</strong>：等待最优拓扑超过 30 分钟，自动降级到次优拓扑。(4) <strong>按并行策略区分</strong>：TP 任务要求高拓扑质量（阈值 0.9），DP 任务可以低一些（阈值 0.5）。</p></div>
<div class="qa-summary">面试要点：不是"最优或不变"，而是"设定可接受的质量阈值，超阈值就调"。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 怎么衡量拓扑感知调度的效果？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">指标</div><p>三个维度：</p>
<ol>
<li><strong>训练性能提升</strong>：对比有/无拓扑感知时的 throughput（samples/s 或 tokens/s）。通常能提升 20-50%。</li>
<li><strong>JCT 改善</strong>：训练性能提升 → execution time 降低 → JCT 降低。但注意，等最优拓扑可能增加 waiting time。</li>
<li><strong>等待时间增加</strong>：拓扑感知调度可能让任务多等 5-30 分钟来凑更好的拓扑。需要看 JCT 的净改善是否为正。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">怎么设计消融实验</div><p>(1) 去掉拓扑感知（只看资源数量，不看位置）→ 看 JCT 和 throughput 变化。(2) 只对 TP 任务做拓扑感知，DP 任务不做 → 看不同并行策略的收益。(3) 调整拓扑质量阈值 → 看等待时间和训练性能的权衡曲线。</p></div>
<div class="qa-summary">面试要点：拓扑感知的收益看训练性能，代价看等待时间。消融实验要分别衡量两者。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试官问"为什么张量并行必须放在同节点"，怎么回答？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>因为张量并行每一层的前向和反向都要做 AllReduce/AllGather，通信频率远高于其他并行策略。一个 70 层的 Transformer，每步训练要做 70 × 2 = 140 次集合通信。如果走 InfiniBand（延迟 ~5μs），每次通信的延迟累积到 0.7ms/步。如果走 NVLink（延迟 ~0.5μs），只有 0.07ms/步。乘以数万步训练，差距巨大。</p></div>
<div class="qa-section"><div class="qa-section-title">补充</div><p>不只是延迟，带宽也是问题。NVLink 带宽 900 GB/s，InfiniBand 只有 ~50 GB/s。张量并行每次通信的激活值可能达到 GB 级别，带宽不够会严重拖慢训练。</p></div>
<div class="qa-summary">面试金句："张量并行的通信频率是'每层每步'，不是'每步一次'。这个量级的通信只有 NVLink 承受得起。"</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: DRA 怎么解决拓扑表达问题？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>DRA 引入了 ResourceSlice，可以结构化地描述每个设备的属性和设备间的关系。一个 ResourceSlice 可以说"这个节点有 8 张 GPU，其中 GPU 0-3 通过 NVLink 互联，GPU 4-7 通过 NVLink 互联，但两组之间走 PCIe"。调度器可以根据这些信息做设备级的拓扑匹配。</p></div>
<div class="qa-section"><div class="qa-section-title">和 Device Plugin 的区别</div><p>Device Plugin 只能报告设备列表（如 nvidia.com/gpu: 8），不能表达设备之间的关系。DRA 的 ResourceSlice 可以报告结构化的设备拓扑。这是从"资源计数"到"资源关系"的进化。</p></div>
<div class="qa-summary">面试要点：Device Plugin 是"我有 8 张 GPU"，DRA 是"我有 8 张 GPU，它们之间是这样连接的"。</div>
</div>
</div>

<div class="card card-m">
<h3>面试题：多机多卡下如何最小化通信开销？</h3>
<p>回答这类题时，不要只说“尽量放近”。更完整的回答是：先建立通信代价模型，再把并行策略映射到拓扑层次，最后在调度器的 Filter/Score/Reserve 阶段落地。</p>
<ol>
<li><strong>建模拓扑图</strong>：把 GPU、CPU Socket、NUMA node、PCIe root complex、NVLink/NVSwitch、NIC/RDMA、机架/交换机都建成图节点或边；边权可以表示带宽、延迟、拥塞和故障域。</li>
<li><strong>识别通信模式</strong>：TP 是层内高频 AllReduce/AllGather，MoE 是 All-to-All，DP 是每步梯度 AllReduce，PP 是相邻 stage P2P。不同通信模式对拓扑的敏感度不同。</li>
<li><strong>优先满足强约束</strong>：TP/MoE 优先放在同 NVLink/NVSwitch 域；GPU 与 NIC 尽量同 NUMA/同 PCIe root complex；需要 GDR 的任务避免 GPU 和 RDMA NIC 跨 Socket。</li>
<li><strong>再做软打分</strong>：如果不能完全满足，就用拓扑质量分数排序，例如同 NVLink 加高分、同 NUMA 加中分、跨 Socket/跨机架加惩罚。</li>
<li><strong>保留未来大块资源</strong>：不能为了当前小任务打散完整 8 卡 NVLink 节点或同机柜 RDMA 域，否则后续大任务会排队更久。</li>
</ol>
<p>调度器视角可以抽象成：</p>
<pre><code>score(placement) =
  - communication_cost(rank_graph, topology_graph)
  - fragmentation_cost(remaining_resources)
  - contention_cost(current_load)
  + locality_bonus(gpu_nic_numa_alignment)</code></pre>
<p>这里的关键是 rank graph：模型并行里的哪些 rank 通信最频繁，就应该在物理拓扑里放得最近。不能只按 GPU 数量调度。</p>
</div>

<div class="card card-d">
<h3>4 张 GPU 应该怎么分配？</h3>
<p>如果一个任务需要 4 张 GPU，优先级通常是：</p>
<table>
<tr><th>候选放置</th><th>优先级</th><th>原因</th><th>适合场景</th></tr>
<tr><td>同一 NVLink/NVSwitch 域内 4 卡</td><td>最高</td><td>GPU-GPU 通信带宽最高、延迟最低，TP/MoE 收益明显</td><td>张量并行、小规模预训练、通信密集训练</td></tr>
<tr><td>同一 Socket / 同 NUMA 下 4 卡</td><td>高</td><td>CPU 线程、内存、GPU、NIC 亲和性最好，减少跨 UPI/QPI</td><td>数据加载重、GDR/RDMA 依赖强</td></tr>
<tr><td>同节点但跨 NUMA / 跨 Socket</td><td>中</td><td>仍避免跨节点网络，但 CPU-GPU、GPU-NIC 可能走远端路径</td><td>DP 或通信不密集任务</td></tr>
<tr><td>跨节点 2+2 或 1+1+1+1</td><td>低</td><td>NCCL 通信走 RDMA/以太网，延迟和带宽都更差，还增加故障面</td><td>纯 DP、资源紧张时的降级方案</td></tr>
</table>
<p>跨 NUMA / 跨 Socket 的影响主要有三类：</p>
<ul>
<li><strong>Host-device copy 变慢</strong>：DataLoader 线程和 pinned memory 如果在远端 NUMA，H2D 拷贝会经过跨 Socket 互联。</li>
<li><strong>GPU-NIC 路径变差</strong>：GPU 和 RDMA NIC 不在同一 PCIe root/NUMA 时，GPUDirect RDMA 可能退化，增加 CPU/内存中转和链路延迟。</li>
<li><strong>NCCL 拓扑选择受影响</strong>：NCCL 会根据 NVLink、PCIe、NIC 拓扑选择 ring/tree，但差拓扑会让 collective 的慢边拖累整体。</li>
</ul>
<p>面试可以这样答：如果是 4 卡 TP，我倾向于同节点同 NVLink 域；如果是 DP，跨节点也能接受但要保证 RDMA 网络质量；如果同时有 RDMA 通信，就要把 GPU 和 NIC 做 NUMA 对齐。</p>
</div>

<div class="card card-w">
<h3>基础知识补全：NUMA、PCIe、NVLink、RDMA 分别影响什么</h3>
<table>
<tr><th>概念</th><th>是什么</th><th>调度里为什么重要</th></tr>
<tr><td>NUMA</td><td>多 Socket 服务器中，每个 CPU Socket 有本地内存，访问远端内存更慢</td><td>CPU 线程、内存页、GPU、NIC 要尽量同 NUMA，否则数据加载和网络路径变慢</td></tr>
<tr><td>PCIe root complex</td><td>CPU 到外设的 PCIe 根路径，GPU/NIC 可能挂在不同 root 下</td><td>决定 GPU-GPU P2P、GPU-NIC GDR 是否走本地路径</td></tr>
<tr><td>NVLink / NVSwitch</td><td>NVIDIA GPU 间高带宽互联</td><td>TP、MoE、频繁 collective 的核心拓扑资源</td></tr>
<tr><td>RDMA / InfiniBand / RoCE</td><td>跨节点低延迟高带宽网络，可绕过 CPU 做远端内存访问</td><td>多机训练、跨节点 AllReduce、KV cache 迁移和 P/D 分离推理都依赖它</td></tr>
<tr><td>GPUDirect RDMA</td><td>NIC 直接访问 GPU 显存，减少 CPU bounce buffer</td><td>要求 GPU 与 NIC 拓扑亲和，否则带宽和延迟可能明显退化</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何设计一个拓扑感知 GPU 调度算法？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答框架</div><p>先把任务抽象成 rank 通信图，把集群抽象成硬件拓扑图，然后做约束过滤和代价打分。Filter 阶段保证 GPU 型号、显存、同节点/同 NUMA、GPU-NIC 亲和等硬约束；Score 阶段最小化通信代价和碎片代价；Reserve 阶段锁定具体 GPU/NIC，避免并发绑定时重复分配。</p></div>
<div class="qa-section"><div class="qa-section-title">工程落点</div><p>短期可以用 Node Label + Scheduler Plugin + NVIDIA/DCGM 拓扑发现；节点内用 kubelet Topology Manager 对齐 CPU/Memory/Device；更长期可用 DRA ResourceSlice 表达 GPU/NIC/NUMA 属性，让 scheduler 直接做设备级匹配。</p></div>
<div class="qa-summary">面试金句：拓扑感知调度不是“找 4 张空闲 GPU”，而是“找通信图和硬件图代价最小的一组 GPU”。</div>
</div>
</div>

<div class="card card-s">
<h3>参考资料</h3>
<ul>
<li>Kubernetes Topology Manager 文档：说明 kubelet 如何协调 CPU Manager、Memory Manager、Device Manager 的 NUMA hint，避免 CPU 和设备跨 NUMA 分配。</li>
<li>NVIDIA rack-scale topology-aware scheduling 文章：强调 NVLink domain、clique/partition、GPU fabric 等硬件拓扑需要被调度系统理解。</li>
<li>AKS DRANET / DRA RDMA 资料：展示 GPU 与 RDMA NIC 同 NUMA 对齐对 GPUDirect RDMA 的重要性。</li>
</ul>
</div>

## 面试回答

**30 秒版：**

拓扑感知调度的本质是把 rank 通信图映射到硬件路径图，最小化通信代价而不是看 GPU 总数。同样 8 卡，同节点 NVLink 和跨机 InfiniBand 的 AllReduce 差 10 倍。所以 Tensor Parallel/MoE 这种每层都通信的策略必须放进同一 NVLink/NVSwitch 域，Pipeline Parallel 的 P2P 走跨机 IB 也能接受，GPU 和 RDMA NIC 还要做 NUMA 对齐保证 GPUDirect RDMA 不退化。

**2 分钟版：**

我会先点明拓扑感知调度优化的是连接关系而不是 GPU 数量，因为大模型训练的通信能占总时间 30-50%，而 NVLink 比 InfiniBand 快 10-50 倍。接着按拓扑层次展开：GPU 内部、节点内 NVLink/NVSwitch、CPU-GPU 的 PCIe、节点间 InfiniBand/RoCE、机架交换机，每层带宽和延迟差一两个数量级。然后把并行策略映射到拓扑：Tensor Parallel 每层前向反向都做 AllReduce，通信频率最高，必须同节点 NVLink；MoE 的 All-to-All 最重，要避免跨拥塞域；Pipeline Parallel 是相邻 stage P2P，通信量小，跨节点可接受；Data Parallel 每步一次 AllReduce，需要高带宽网络；ZeRO-3 通信量比普通 DP 大 1.5-3 倍。工程权衡上不能追求所有任务都拿最优拓扑，而是设拓扑质量阈值，超阈值就调度、超时就降级。实现路径短期用 Node Label 加 Scheduler Plugin 在 Filter/Score 做拓扑打分，节点内用 kubelet Topology Manager 对齐 NUMA，长期演进到 DRA 的 ResourceSlice 做设备级结构化表达，因为 Node Label 只能到节点级、表达不了哪几张 GPU 之间有 NVLink。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

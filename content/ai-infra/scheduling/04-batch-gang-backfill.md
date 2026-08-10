<div class="card card-m">
<h3>批调度：训练任务和普通在线服务的分水岭</h3>
<p>分布式训练、HPC 和大规模批任务通常不是单 Pod 独立运行，而是一组进程共同完成一个 job。批调度关注的不只是单个 Pod 能否放下，还包括一组 Pod 是否能同时启动、是否会造成资源碎片、是否会让大作业长期排队。</p>
<p>为什么批调度是 GPU 集群独有的问题？因为在线服务的每个 Pod 是独立的——挂一个副本不影响其他副本。但分布式训练的所有 worker 是一个整体——少一个 worker，NCCL AllReduce 就会阻塞，所有 GPU 空转。这种 all-or-nothing 的语义是批调度的核心。</p>
</div>

<div class="card card-d">
<h3>Gang、Backfill、Bin Packing 分别解决什么</h3>
<p>这几个词经常被一起问，但它们不是同一层问题。Gang Scheduling 是<strong>准入/启动语义</strong>，Backfill 是<strong>队列利用率优化</strong>，Bin Packing 是<strong>节点放置策略</strong>。三者可以组合在同一个调度系统里。</p>
<table>
<tr><th>概念</th><th>所在决策层</th><th>回答的问题</th><th>典型场景</th><th>主要风险</th></tr>
<tr><td>Gang Scheduling</td><td>准入控制 / Permit / PodGroup</td><td>一组 worker 是否能一起启动</td><td>分布式训练、MPI、HPC、强同步任务</td><td>等待时间增加，资源凑齐前不能启动</td></tr>
<tr><td>Backfilling</td><td>队列调度 / reservation</td><td>队头大任务暂时跑不了时，碎片资源能否先给短任务用</td><td>HPC、AI 训练队列、多租户实验平台</td><td>预测不准会延迟被保护任务，短任务可能过度插队</td></tr>
<tr><td>Bin Packing</td><td>节点放置 / Score</td><td>任务应该放到哪些节点，如何减少碎片</td><td>GPU 训练、批处理、成本敏感离线任务</td><td>热点、故障爆炸半径、拓扑质量下降</td></tr>
<tr><td>Preemption</td><td>运行中资源回收</td><td>高优任务来了，能否打断低优任务释放资源</td><td>混部、紧急任务、quota reclaim</td><td>训练进度损失、checkpoint 和重启成本</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Gang Scheduling 详解</h3>

<h4>问题背景：Partial Allocation</h4>
<p>假设一个 64 卡训练任务需要 8 个节点每个 8 GPU。如果默认调度器只找到了 7 个节点的资源，它会先启动 56 个 worker。这 56 个 worker 启动后执行 NCCL init，发现 world_size=64 但只有 56 个 rank 在线，于是<strong>阻塞等待</strong>。56 张 GPU 完全空转，而第 8 个节点的资源被其他小任务占走了。</p>
<p>这就是 partial allocation 问题——部分 Pod 先启动，但无法正常工作，白占 GPU。如果同时有 10 个大任务都在等资源，每个都先启动一部分，集群可能完全卡死。</p>

<h4>Gang Scheduling 的核心语义</h4>
<p><strong>All-or-nothing</strong>：一组 Pod 满足最小可运行数量后再整体放行，否则一起等待。</p>
<table>
<tr><th>概念</th><th>含义</th><th>设置建议</th><th>设错了的后果</th></tr>
<tr><td>PodGroup</td><td>一组需要共同调度的 Pod</td><td>按训练 job 划分，一个 job 一个 PodGroup</td><td>组太大会增加等待时间，组太小失去 gang 语义</td></tr>
<tr><td>minAvailable</td><td>最小可运行 Pod 数</td><td>通常等于 world_size，弹性训练时可以小于</td><td>太低：部分 Pod 空转；太高：永远等不到资源</td></tr>
<tr><td>Permit</td><td>绑定前等待同组 Pod 凑齐</td><td>设超时时间，超时后释放已预留资源</td><td>不设超时：已预留资源被占住，其他任务用不了</td></tr>
</table>

<h4>Gang Scheduling 的实现方式</h4>
<p><strong>方式 1：Volcano PodGroup</strong></p>
<p>Volcano 引入 PodGroup CRD，其中 minMember 字段定义 gang 大小。调度器在准入阶段检查：集群是否有足够资源同时满足 PodGroup 中 minMember 个 Pod？不够则整组放入 UnschedulableQ 等待。</p>
<p><strong>方式 2：K8S Scheduling Framework Coscheduling 插件</strong></p>
<p>在 QueueSort 阶段把同 PodGroup 的 Pod 排在一起；在 Permit 阶段等待同组 Pod 都通过 Filter；超时后 Unreserve 释放已预留的资源。</p>
<p><strong>方式 3：Kueue Workload + LocalQueue</strong></p>
<p>Kueue 在 ClusterQueue 层做准入控制——只有当 ClusterQueue 有足够配额和资源时，Workload 才被准入。Workload 本身是一组 Pod 的集合，天然有 gang 语义。</p>

<h4>Gang Scheduling 的面试回答框架</h4>
<ol>
<li><strong>问题是什么</strong>：partial allocation 导致 GPU 空转。</li>
<li><strong>解决思路</strong>：all-or-nothing，凑齐再启动。</li>
<li><strong>实现方式</strong>：PodGroup + Permit 阶段等待 + 超时释放。</li>
<li><strong>代价</strong>：增加大作业等待时间，因为必须等到所有资源同时可用。</li>
<li><strong>优化</strong>：弹性训练降低 minAvailable，backfill 利用等待期间的碎片资源。</li>
</ol>
<h4>适合和不适合的场景</h4>
<table>
<tr><th>适合 Gang</th><th>原因</th><th>不适合 Gang</th><th>原因</th></tr>
<tr><td>PyTorch DDP / MPI / Horovod</td><td>rank 必须同时在线，少一个会阻塞 collective</td><td>普通 Deployment 副本</td><td>每个副本独立服务，不需要 all-or-nothing</td></tr>
<tr><td>强同步 HPC job</td><td>进程之间有严格 barrier 和同步通信</td><td>无状态 worker 队列</td><td>worker 可以独立消费任务，缺几个只影响吞吐</td></tr>
<tr><td>多节点 benchmark</td><td>需要固定 world size 和拓扑，才能得到可比结果</td><td>弹性推理服务</td><td>副本数可以随负载扩缩，不要求同时启动</td></tr>
<tr><td>需要拓扑一致性的训练任务</td><td>要一次性拿到同类型 GPU、同网络域资源</td><td>短小 best-effort job</td><td>等待 gang 资源可能比执行时间还长</td></tr>
</table>
</div>

<div class="card card-d">
<h3>回填调度：保护队头任务的插空运行</h3>
<p>队头大任务暂时凑不齐资源时，FIFO 会把后面的任务一起挡住，导致碎片 GPU 空转。回填调度的核心做法是：先给队头任务计算一个未来启动时间，再允许后面的短任务或可抢占任务利用当前空闲资源，但不能破坏队头任务的启动时间。</p>
<p>例子：Job-A 是队头任务，需要 64 张 GPU，当前只有 8 张 GPU 空闲，预计 30 分钟后能凑齐 64 张。严格 FIFO 会让这 8 张 GPU 空闲 30 分钟；回填调度会允许 Job-B（2 GPU，5 分钟）和 Job-C（4 GPU，20 分钟）先跑，但不会允许 Job-D（8 GPU，2 小时）启动，因为它会延迟 Job-A。</p>
<table>
<tr><th>任务</th><th>资源需求</th><th>预计运行时间</th><th>是否可回填</th><th>原因</th></tr>
<tr><td>Job-B</td><td>2 GPU</td><td>5 分钟</td><td>可以</td><td>能在 30 分钟窗口内结束</td></tr>
<tr><td>Job-C</td><td>4 GPU</td><td>20 分钟</td><td>可以</td><td>能在队头任务启动前释放资源</td></tr>
<tr><td>Job-D</td><td>8 GPU</td><td>2 小时</td><td>不适合</td><td>会占用队头任务 30 分钟后的资源</td></tr>
</table>
<div class="qa-summary">回填不是让小任务无条件插队，而是在保护队头任务 reservation 的前提下利用碎片资源。</div>
</div>

<div class="card card-s">
<h3>Backfill 要判断哪些条件</h3>
<p>调度器要先回答三个问题：队头任务什么时候能启动，后面的任务现在能不能跑，后面的任务会不会影响队头任务启动。只要其中一个问题回答不清楚，回填就可能从“提高利用率”变成“破坏公平性”。</p>
<table>
<tr><th>需要的信息</th><th>具体含义</th><th>GPU 场景里的细化</th></tr>
<tr><td>当前可用资源</td><td>现在有多少资源可以立刻分配</td><td>不能只看 GPU 总数，还要看型号、显存、节点内空闲卡数和拓扑</td></tr>
<tr><td>队头任务需求</td><td>队头任务要什么资源才能启动</td><td>例如 64 张 H100、8 台 8 卡节点、同一 RDMA 网络域</td></tr>
<tr><td>运行中任务完成时间</td><td>未来什么时候会释放资源</td><td>依赖用户声明、历史统计、训练进度或在线预测</td></tr>
<tr><td>候选任务画像</td><td>后续任务是否适合插空运行</td><td>优先选择短任务、低优先级任务、可抢占任务、checkpoint 新鲜任务</td></tr>
<tr><td>租户状态</td><td>任务所属团队是否欠账或超额使用</td><td>回填不能长期占用资源不足租户未来应拿回的资源</td></tr>
</table>
</div>

<div class="card card-m">
<h3>经典策略对比</h3>
<table>
<tr><th>策略</th><th>保护对象</th><th>优点</th><th>缺点</th><th>适用场景</th></tr>
<tr><td>Conservative Backfill</td><td>队列中所有已等待任务</td><td>公平性更好，等待时间更可预测</td><td>过于保守，可回填空间少，实现复杂</td><td>强公平、多租户保障要求高的集群</td></tr>
<tr><td>EASY Backfill</td><td>只保护队头任务</td><td>实现简单，资源利用率高，最常见</td><td>队头后面的大任务可能被短任务反复插队</td><td>工程系统和面试讨论中的默认版本</td></tr>
<tr><td>Prediction-aware Backfill</td><td>由运行时间预测决定保护窗口</td><td>能更充分利用碎片窗口</td><td>预测不准会延迟被保护任务</td><td>有历史任务数据或在线进度信号的系统</td></tr>
</table>
<p>EASY Backfill 最值得重点掌握。它只给队头任务建立 reservation，后面的任务可以被回填，只要预计结束时间早于 reservation time，或者任务本身可抢占。为了避免后续大任务饥饿，工程上通常会加 aging、最大等待时间、租户公平或 quota debt 约束。</p>
</div>

<div class="card card-d">
<h3>EASY Backfill 的调度流程</h3>

<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">取队头任务</div><div class="flow-desc">每轮调度先看队列第一个任务</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">尝试直接启动</div><div class="flow-desc">如果队头任务现在能启动，直接调度</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">估计最早启动时间</div><div class="flow-desc">根据 running jobs 的预计完成时间模拟未来资源释放</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">建立逻辑预留</div><div class="flow-desc">记录 reservation time 和资源需求，避免后续任务破坏预留</div></div>
<div class="flow-step"><div class="flow-index">05</div><div class="flow-title">扫描后续任务</div><div class="flow-desc">逐个判断候选任务是否能使用当前碎片资源</div></div>
<div class="flow-step"><div class="flow-index">06</div><div class="flow-title">检查结束时间或抢占能力</div><div class="flow-desc">能按时结束，或可在 reservation time 被抢占，才允许回填</div></div>
<div class="flow-step"><div class="flow-index">07</div><div class="flow-title">到期回收</div><div class="flow-desc">回填任务超时未结束时优雅退出或强制抢占</div></div>
</div>

<pre><code>head = queue.first()

if can_schedule(head):
    schedule(head)
    return

head_start_time = estimate_earliest_start(head, running_jobs)
reserve(head, head_start_time)

for job in queue.after(head):
    if not fits_current_free_resources(job):
        continue
    if estimated_finish(job) &lt;= head_start_time:
        schedule_as_backfill(job)
    elif job.is_preemptible:
        schedule_as_preemptible_backfill(job, deadline=head_start_time)</code></pre>
</div>

<div class="card card-w">
<h3>GPU 集群里的工程难点</h3>
<table>
<tr><th>难点</th><th>为什么更难</th><th>工程处理</th></tr>
<tr><td>GPU 型号不等价</td><td>队头任务要 H100 时，V100 空闲也没用</td><td>按 GPU type 建模资源池，reservation 和 backfill 都带型号约束</td></tr>
<tr><td>拓扑不是总数问题</td><td>8 张空闲卡分散在 4 台机器上，无法满足单机 8 卡任务</td><td>Filter 阶段检查节点、NVLink、机架、RDMA 网络域</td></tr>
<tr><td>Gang Scheduling</td><td>训练任务通常是一组 worker，不是单个 Pod</td><td>以 PodGroup 或 Workload 为单位做回填判断</td></tr>
<tr><td>运行时间预测误差</td><td>训练时长受 epoch、数据量、checkpoint、提前停止和干扰影响</td><td>给预测时间加 buffer，降低高不确定任务的回填优先级</td></tr>
<tr><td>抢占成本高</td><td>训练任务被杀可能丢失长时间进度，还要重建 NCCL</td><td>优先回填短任务、best-effort 任务、checkpoint 新鲜任务</td></tr>
<tr><td>多租户公平</td><td>利用率优化可能压制资源不足租户</td><td>结合 quota、QAD、tenant debt 判断能否借用碎片资源</td></tr>
</table>
<p>如果要讲得更像 AI Infra，可以说调度器在 Filter 阶段判断候选任务是否能使用碎片 GPU，在 Score 阶段选择最不影响未来 reservation 的节点，在 Reserve 阶段标记这些资源属于 backfill usage。到 reservation time 时，如果回填任务还没结束，就按可抢占策略回收。</p>
</div>

<div class="card card-d">
<h3>如何避免 GPU 碎片：从放置到队列的组合拳</h3>
<p>GPU 碎片的典型问题是：集群总共还剩 8 张 GPU，但分散在 8 台机器上，每台只剩 1 张；一个需要单机 8 卡或 8 卡同拓扑的任务仍然无法运行。解决碎片不能只靠节点打分，需要队列、放置和回填一起设计。</p>
<table>
<tr><th>手段</th><th>作用</th><th>适用场景</th><th>代价</th></tr>
<tr><td>Bin Packing</td><td>把小任务尽量塞满已有节点，保留完整空闲节点</td><td>离线训练、批任务</td><td>热点和故障爆炸半径增加</td></tr>
<tr><td>Topology-aware placement</td><td>优先保留完整 NVLink / 机架 / RDMA 域</td><td>TP、MoE、NCCL-heavy 任务</td><td>调度等待可能增加</td></tr>
<tr><td>Backfill</td><td>用短任务填碎片，但不破坏大任务 reservation</td><td>HPC / AI 训练队列</td><td>依赖运行时间预测</td></tr>
<tr><td>Defragmentation</td><td>迁移或抢占低优任务，合并碎片资源</td><td>需要启动大 gang 时</td><td>抢占和重启成本</td></tr>
<tr><td>资源分层</td><td>按 GPU flavor、拓扑域、队列分池</td><td>异构 GPU 集群</td><td>资源池太细会降低利用率</td></tr>
</table>
</div>

<div class="card card-s">
<h3>长任务和短任务混部：不能只用 FIFO</h3>
<p>长任务需要稳定资源和较低抢占率，短任务需要低等待时间和快速反馈。只用 FIFO 会被队头大任务阻塞；只用 SJF 会让长任务饥饿。实际系统通常组合使用多队列、aging、backfill 和 quota。</p>
<table>
<tr><th>策略</th><th>解决什么</th><th>注意点</th></tr>
<tr><td>多队列</td><td>把交互式短任务、长期训练、best-effort 分开治理</td><td>队列之间需要公平共享</td></tr>
<tr><td>SJF / 预测排序</td><td>降低短任务等待时间和平均 JCT</td><td>长任务要 aging 兜底</td></tr>
<tr><td>Backfill</td><td>让短任务利用大任务等待期间的碎片窗口</td><td>不能破坏大任务 reservation</td></tr>
<tr><td>Checkpoint-aware preemption</td><td>必要时回收资源给高优任务</td><td>不能频繁打断长任务</td></tr>
<tr><td>Elastic training</td><td>长任务可以先小规模启动，资源充足后扩容</td><td>训练框架要支持 world size 变化</td></tr>
</table>
</div>

<div class="card card-m">
<h3>Elastic Training：弹性训练如何支持</h3>
<p>弹性训练允许训练任务在不同 worker/GPU 数量下继续运行，例如先用 32 卡启动，后续扩到 64 卡，资源紧张时缩回 16 卡。它能降低 gang 的启动等待，但需要训练框架、调度器和 checkpoint 协同。</p>
<table>
<tr><th>能力</th><th>设计要点</th><th>风险</th></tr>
<tr><td>弹性资源声明</td><td>声明 min/max/target，例如 min=16、target=64</td><td>min 太低会导致训练效率差</td></tr>
<tr><td>弹性准入</td><td>达到 min 就可启动，后续根据空闲资源扩容</td><td>过早启动可能拖长整体训练</td></tr>
<tr><td>动态 membership</td><td>rank/world size 变化时重建通信组</td><td>NCCL、优化器状态和数据分片要一致</td></tr>
<tr><td>checkpoint 支持</td><td>扩缩容时保存/加载一致状态</td><td>checkpoint I/O 压力变大</td></tr>
<tr><td>调度策略</td><td>扩容只使用不破坏高优 reservation 的资源</td><td>弹性任务可能长期占用借用资源</td></tr>
</table>
<div class="qa-summary">面试口径：弹性训练用更复杂的训练框架能力换更短等待时间和更高利用率，不是调度器单独能完成的。</div>
</div>

<div class="card card-w">
<h3>立即运行还是等待更好的资源组合？</h3>
<p>这是 AI 集群调度的核心取舍：立刻运行可以降低 waiting time，但可能拿到差拓扑、低性能或造成碎片；等待更好资源可以提高训练吞吐和后续调度质量，但会增加排队时间。</p>
<table>
<tr><th>判断维度</th><th>倾向立即运行</th><th>倾向等待</th></tr>
<tr><td>任务类型</td><td>短实验、低通信 DP、best-effort</td><td>大模型预训练、TP/MoE、强拓扑任务</td></tr>
<tr><td>等待成本</td><td>用户交互强，等待成本高</td><td>任务运行很长，等待几十分钟可接受</td></tr>
<tr><td>性能损失</td><td>差拓扑影响小</td><td>差拓扑会导致训练吞吐腰斩</td></tr>
<tr><td>资源碎片</td><td>当前放置不会破坏大块资源</td><td>当前放置会打散完整 8 卡节点</td></tr>
<tr><td>预测置信度</td><td>不知道未来资源何时释放</td><td>能可靠预测 reservation window</td></tr>
</table>
<div class="formula">$$\text{schedule now if } \text{waiting\_cost} > \text{performance\_loss} + \text{fragmentation\_cost}$$</div>
<p>工程实现通常不是精确求解，而是设阈值：拓扑质量分数达到阈值就运行；等待超过超时时间就降级；高优任务可以抢占或预留。</p>
</div>

<div class="card card-s">
<h3>QAD-aware Backfill</h3>
<p>在多租户 GPU 集群里，回填不能只看任务大小和运行时间。假设 A 团队长期资源不足，队头任务来自 A；B 团队已经拿到了超过保障份额的资源，后面有一个短任务想回填。即使 B 的任务很短，也不能长期占用 A 未来应恢复的资源。</p>
<p>QAD-aware Backfill 可以把候选任务分成三类：资源不足租户的短任务优先回填；资源正常租户的短任务按普通规则回填；资源充足或长期借用的租户只能使用不会影响 under-served tenant 恢复路径的碎片资源。这样 Backfill 同时服务两个目标：提高利用率，避免破坏租户保障。</p>
<table>
<tr><th>候选任务来源</th><th>回填倾向</th><th>原因</th></tr>
<tr><td>资源不足租户</td><td>优先</td><td>回填有助于缩小保障缺口</td></tr>
<tr><td>资源正常租户</td><td>正常判断</td><td>按运行时间、资源匹配和抢占能力决定</td></tr>
<tr><td>资源充足租户</td><td>谨慎</td><td>不能让已经占优的租户继续挤压欠账租户</td></tr>
</table>
</div>

<div class="card card-m">
<h3>面试怎么回答</h3>
<p>Backfill 的核心是：队头任务暂时跑不了时，不让资源空着，而是允许后面的小任务先利用空闲资源，但不能影响队头任务未来启动。</p>
<p>一个简单实现是：每轮调度先看队头任务，如果它能启动就直接启动；如果不能启动，就根据当前运行任务的预计结束时间估计队头任务最早什么时候能凑齐资源，并为它建立逻辑预留。然后扫描后面的任务，找当前资源能满足、预计能在队头任务启动前结束，或者本身可抢占的任务，把它们作为回填任务调度。</p>
<p>在 GPU 场景下，回填判断不能只看 GPU 数量，还要看 GPU 型号、拓扑、是否需要 Gang Scheduling，以及任务是否可抢占。如果运行时间预测不准，可以加安全 buffer，只选择短任务或 best-effort 任务回填；如果到队头任务预留启动时间时回填任务还没结束，就抢占回收资源。</p>
<div class="qa-summary">面试金句：Backfill 解决的是“队头任务暂时跑不了但资源不该空着”的问题，关键约束是不能破坏队头任务的未来启动时间。</div>
</div>

<div class="card card-w">
<h3>Checkpoint-aware Preemption 详解</h3>
<p>抢占在 AI 训练里不能只看优先级，还要看沉没成本。一个已经训练 20 小时但 3 小时没 checkpoint 的任务，被抢占代价可能远高于刚启动 5 分钟的任务。面试中如果只说"抢占低优先级"，是不够的——需要说清楚"代价感知抢占"。</p>

<h4>传统抢占 vs 代价感知抢占</h4>
<table>
<tr><th>维度</th><th>传统抢占</th><th>代价感知抢占</th></tr>
<tr><td>选择标准</td><td>优先级最低</td><td>抢占代价最低</td></tr>
<tr><td>考虑因素</td><td>只有优先级</td><td>沉没成本、checkpoint 新鲜度、重启成本</td></tr>
<tr><td>释放效率</td><td>可能杀了一个大任务才释放 1 张 GPU</td><td>选择释放资源量/代价比值最高的牺牲者</td></tr>
<tr><td>用户感知</td><td>"我跑了好久突然被杀了"</td><td>"刚启动不久就被调度走了，还算合理"</td></tr>
</table>

<h4>抢占代价的五个维度</h4>
<table>
<tr><th>维度</th><th>含义</th><th>怎么衡量</th><th>调度含义</th></tr>
<tr><td>Checkpoint age</td><td>距离最近 checkpoint 的时间</td><td>当前时间 - 最近 checkpoint 时间</td><td>越短越适合被抢占——回滚损失小</td></tr>
<tr><td>Runtime so far</td><td>已经运行多久</td><td>当前时间 - 启动时间</td><td>越长沉没成本越高，不适合抢占</td></tr>
<tr><td>Release value</td><td>抢占后能释放多少关键资源</td><td>任务占用的 GPU 数量和拓扑质量</td><td>释放整组 NVLink GPU 比释放分散 GPU 更有价值</td></tr>
<tr><td>Restart cost</td><td>重启需要的额外成本</td><td>镜像拉取时间 + 模型加载时间 + NCCL 初始化时间</td><td>重启成本高则降低抢占优先级</td></tr>
<tr><td>Tenant debt</td><td>租户是否长期超额使用资源</td><td>历史借用时长和借用量的加权和</td><td>超额租户更适合被回收</td></tr>
</table>

<h4>抢占决策的打分函数</h4>
<p>一个简化的代价感知抢占打分函数：</p>
<p><code>\text{preemption\_score}(victim) = \text{release\_value}(victim) / (\text{checkpoint\_age}(victim) + \text{restart\_cost}(victim))</code></p>
<p>选择 \text{preemption\_score} 最高的牺牲者。直觉：释放资源量越大越好，回滚损失和重启成本越小越好。</p>
<p><strong>手动推演</strong>：需要释放 4 张 GPU。</p>
<ul>
<li>任务 X：占 8 GPU（同节点 NVLink），运行 20 小时，1 小时前 checkpoint，重启需 30 分钟。score = 8 / (1 + 0.5) = 5.33</li>
<li>任务 Y：占 4 GPU（跨节点），运行 2 小时，5 分钟前 checkpoint，重启需 10 分钟。score = 4 / (0.08 + 0.17) = 16</li>
<li>任务 Z：占 2 GPU，运行 5 分钟，无 checkpoint（刚启动），重启需 15 分钟。score = 2 / (0.08 + 0.25) = 6.06</li>
</ul>
<p>选择 Y：虽然只释放 4 张 GPU（刚好够用），但 checkpoint 新鲜、运行时间短，抢占代价最低。如果需要 8 张 GPU，就选 X。</p>

<h4>优雅抢占 vs 强制抢占</h4>
<p><strong>优雅抢占</strong>：通知任务"请尽快 checkpoint 并退出"。任务收到信号后做一次 checkpoint，然后主动退出。优点：进度零损失；缺点：等待时间不确定。</p>
<p><strong>强制抢占</strong>：直接杀掉 Pod。优点：立即释放资源；缺点：进度可能回滚到上次 checkpoint。</p>
<p><strong>实际做法</strong>：给一个优雅期（如 5 分钟），超时未退出则强制杀掉。这样既给任务机会做 checkpoint，又不会无限等待。</p>
</div>

<div class="card card-m">
<h3>弹性训练与调度</h3>
<p>弹性训练把"固定 world size"变成"可变 world size"，可以缓解资源碎片和排队时间。调度器不一定要等到 64 张 GPU 才启动任务，而是可以先用 32 张运行，后续资源释放后再扩容。</p>

<h4>弹性训练怎么工作</h4>
<p><strong>传统训练</strong>：world_size=64 固定，必须凑齐 64 张 GPU 才能启动。NCCL 通信组在启动时确定，运行中不变。</p>
<p><strong>弹性训练</strong>：world_size 可变。训练框架（如 PyTorch Elastic/torchrun、Elastic Horovod）支持动态 rendezvous——worker 数量变化时重新组建通信组，调整 batch size 和 learning rate，然后继续训练。</p>

<h4>弹性训练的调度好处</h4>
<table>
<tr><th>场景</th><th>没有弹性</th><th>有弹性</th></tr>
<tr><td>资源碎片</td><td>需要 64 卡但只有 56 卡空闲，任务继续排队</td><td>先用 56 卡启动，等剩余 8 卡释放后扩容</td></tr>
<tr><td>GPU 回收</td><td>必须杀掉整个任务来释放 GPU</td><td>缩减 world size 释放部分 GPU，训练继续</td></tr>
<tr><td>优先级抢占</td><td>高优先级任务来了，低优先级任务被全部杀掉</td><td>低优先级任务缩减 world size，释放的 GPU 给高优先级</td></tr>
</table>

<h4>弹性训练的代价</h4>
<ul>
<li><strong>训练吞吐变化</strong>：从 64 卡缩到 32 卡，每步训练时间翻倍。</li>
<li><strong>Batch size 和 learning rate 需要适配</strong>：worker 数量变化时，global batch size 变了，learning rate 通常需要线性缩放（或按其他规则调整）。</li>
<li><strong>重同步成本</strong>：worker 变更时需要重新 rendezvous、重建 NCCL 通信组、调整数据分片。这个过程可能需要几分钟。</li>
<li><strong>不是所有任务都支持</strong>：有些模型（如大模型张量并行）对 world size 有严格限制，不能随意缩。</li>
</ul>

<h4>弹性训练的面试回答框架</h4>
<ol>
<li><strong>问题</strong>：固定 world size 导致排队时间长、碎片利用率低、抢占代价大。</li>
<li><strong>解决</strong>：world size 可变，训练框架支持动态 rendezvous。</li>
<li><strong>调度配合</strong>：Gang 的 minAvailable 可以小于 world size，资源够 minAvailable 就启动，后续扩容。</li>
<li><strong>代价</strong>：batch size/learning rate 适配、重同步成本、不是所有模型都支持。</li>
</ol>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Gang、Backfill、Preemption 三者怎么一起用？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>三者分别处理不同的问题，不是替代关系：</p>
<ul>
<li><strong>Gang</strong>：保证分布式训练不会 partial allocation——要么全启动，要么全等。</li>
<li><strong>Backfill</strong>：在 Gang 等待期间利用碎片资源——让短任务先跑，不影响大 gang 预计启动时间。</li>
<li><strong>Preemption</strong>：在高优先级任务需要资源时释放——选择代价最小的牺牲者。</li>
</ul></div>
<div class="qa-section"><div class="qa-section-title">组合使用</div><p>流程：(1) 新 gang 提交 → 检查资源是否够 → 不够则进入等待队列（Gang 语义）；(2) 等待期间，小任务可以 backfill 利用空闲资源（Backfill）；(3) 当高优先级 gang 到来且资源不够时，选择代价最小的运行中任务抢占（Preemption）；(4) 被抢占的任务如果有弹性训练能力，可以缩减而非杀死。</p></div>
<div class="qa-summary">面试要点：三者是互补的——Gang 保证原子性，Backfill 提高利用率，Preemption 保证优先级。缺了任何一个，系统都有明显缺陷。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Gang Scheduling 会导致大作业饥饿吗？怎么解决？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">问题</div><p>会。如果集群里小任务源源不断，每次释放的 GPU 都被小任务抢占，大 gang 可能永远凑不齐资源。这叫"大作业饥饿"。</p></div>
<div class="qa-section"><div class="qa-section-title">解决思路</div><p>(1) <strong>资源预留</strong>：为大 gang 预留资源，不允许小任务占用预留部分。(2) <strong>Aging</strong>：等待时间越长，gang 的调度优先级越高，最终总能排到队首。(3) <strong>Backfill 约束</strong>：小任务 backfill 时必须保证不推迟 gang 的预计启动时间。(4) <strong>弹性训练</strong>：降低 minAvailable，用更少的 GPU 启动，减少等待时间。</p></div>
<div class="qa-summary">面试要点：Gang 的饥饿问题是经典面试题。要从"预留、aging、backfill 约束、弹性"四个角度给出解法。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 GPU 集群的 Backfill 比 CPU 集群难做？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>三个原因：</p>
<ol>
<li><strong>GPU 任务通常是独占整卡</strong>：CPU 任务可以只占 0.5 核，留下 0.5 核给别人。但 GPU 任务通常独占整卡，不像 CPU 可以"挤一挤"。所以 GPU 集群的 backfill 窗口更难找——只有整卡空闲时才能 backfill。</li>
<li><strong>Gang 语义增加了约束</strong>：不是"1 个 Pod 能放就行"，而是"一组 Pod 必须同时能放"。大 gang 等待期间，碎片可能分散在不同节点，小 gang 也放不进去。</li>
<li><strong>拓扑约束</strong>：即使有空闲 GPU，如果拓扑位置不合适（如跨节点太多），backfill 任务的性能可能很差，不值得跑。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">怎么缓解</div><p>GPU sharing（MPS/time-slicing）可以创造 backfill 机会——让小任务和已有任务合用同一张卡。代价是可能的性能干扰。</p></div>
<div class="qa-summary">面试要点：GPU 独占性 + Gang 语义 + 拓扑约束，三重限制让 GPU 集群的 backfill 更难。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果 checkpoint 频率很低（如每 4 小时一次），抢占决策应该怎么调整？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>checkpoint 频率低意味着 checkpoint age 可能很大，抢占代价高。调整策略：</p>
<ol>
<li><strong>优先抢占刚启动的任务</strong>：它们没有太多进度可损失。</li>
<li><strong>触发紧急 checkpoint</strong>：通知任务"请立即做一次 checkpoint"，等待完成后抢占。虽然增加了延迟，但避免了小时级的进度损失。</li>
<li><strong>考虑优雅抢占</strong>：给任务更多时间来 checkpoint 和退出。如果是训练任务，5-10 分钟的优雅期可能换来巨大的进度保护。</li>
<li><strong>调整 checkpoint 频率策略</strong>：如果集群经常需要抢占，可以建议用户提高 checkpoint 频率，或者平台提供自动异步 checkpoint。</li>
</ol></div>
<div class="qa-summary">面试要点：低 checkpoint 频率让抢占代价飙升。解决方案不是"不做抢占"，而是"做代价感知抢占 + 优雅终止 + 紧急 checkpoint"。</div>
</div>
</div>

<div class="card card-m">
<h3>大模型训练被抢占时，如何弹性伸缩而不中断？</h3>
<p>Megatron/DeepSpeed 这类大模型训练通常依赖固定 world size、张量并行、流水线并行和数据并行组合。严格 Gang 模式下，少一个 rank 就会阻塞 collective；如果发生节点故障或高优先级抢占，传统做法是整组失败后从 checkpoint 重启。弹性训练的目标是把“整组重启”变成“保存状态、重建 rank 拓扑、继续训练”。</p>
<table>
<tr><th>环节</th><th>要做什么</th><th>关键风险</th></tr>
<tr><td>故障/抢占感知</td><td>平台发现节点 NotReady、Pod eviction、PriorityClass 抢占或任务心跳丢失</td><td>误判会导致不必要重组</td></tr>
<tr><td>优雅冻结</td><td>通知 trainer 停止取新 batch，等待当前 micro-batch / pipeline flush 完成</td><td>强杀会丢进度，pipeline 中间状态难恢复</td></tr>
<tr><td>保存 checkpoint</td><td>保存模型参数、优化器状态、LR scheduler、RNG、数据迭代器、并行拓扑 metadata</td><td>ZeRO/TP/PP 分片 checkpoint 与新 world size 不兼容</td></tr>
<tr><td>重新 rendezvous</td><td>按剩余或新增 GPU 重建 rank/world size、DP/TP/PP group、NCCL communicator</td><td>TP/PP 通常有整除和拓扑约束，不能任意缩放</td></tr>
<tr><td>状态重分片</td><td>把旧 checkpoint 转换到新并行配置，重新切分 optimizer/model state</td><td>转换成本和共享存储带宽可能成为瓶颈</td></tr>
<tr><td>恢复训练</td><td>从同一个 global step / consumed samples 继续，调整 global batch 和 LR 规则</td><td>batch size 改变会影响收敛，需要策略约束</td></tr>
</table>
<p>面试要点：弹性训练不是 scheduler 单独完成的能力，而是 <strong>调度器 + 训练框架 + checkpoint 格式 + 共享存储</strong> 协同。调度器负责 min/max/target 资源和抢占策略，训练框架负责 rank 重组和状态恢复。</p>
</div>

<div class="card card-d">
<h3>Megatron/DeepSpeed 场景下的弹性边界</h3>
<p>不是所有并行维度都适合频繁变化：</p>
<table>
<tr><th>并行维度</th><th>是否适合弹性变化</th><th>原因</th><th>调度建议</th></tr>
<tr><td>Data Parallel</td><td>相对适合</td><td>DP rank 数变化主要影响 global batch、梯度同步组和数据分片</td><td>优先在 DP 维度做扩缩容</td></tr>
<tr><td>Tensor Parallel</td><td>不适合频繁变化</td><td>模型层内权重和通信 pattern 与 TP degree 强绑定</td><td>尽量固定 TP，并放在同 NVLink 域</td></tr>
<tr><td>Pipeline Parallel</td><td>谨慎变化</td><td>层切分、micro-batch、pipeline bubble 与 stage 数绑定</td><td>只在大规模重启或计划性调整时变化</td></tr>
<tr><td>ZeRO DP Sharding</td><td>可变化但依赖 checkpoint 转换</td><td>优化器状态和参数分片跟 rank 数相关</td><td>使用通用/可重分片 checkpoint 格式</td></tr>
</table>
<p>因此，一个实用策略是：<strong>TP/PP 固定，DP 弹性。</strong>例如每个节点内 8 卡固定做 TP=8，节点数变化只改变 DP 组数量。这样拓扑约束更稳定，checkpoint 重分片也更可控。</p>
</div>

<div class="card card-w">
<h3>Checkpoint 如何高效保存和恢复？</h3>
<p>大模型 checkpoint 的难点不是“把文件写下来”，而是状态巨大、分片复杂、恢复拓扑可能不同。高效 checkpoint 要同时降低保存停顿、恢复重分片成本和共享存储压力。</p>
<table>
<tr><th>状态</th><th>为什么必须保存</th><th>遗漏后果</th></tr>
<tr><td>模型参数</td><td>训练主体状态</td><td>无法恢复模型权重</td></tr>
<tr><td>优化器状态</td><td>Adam moment、ZeRO shard 通常比参数还大</td><td>恢复后收敛曲线异常或等价于重新 warmup</td></tr>
<tr><td>LR scheduler / global step</td><td>保证学习率和训练步数一致</td><td>学习率错位，训练不稳定</td></tr>
<tr><td>RNG state</td><td>保证 dropout、数据增强、采样可复现</td><td>恢复前后结果不可复现</td></tr>
<tr><td>Data loader / consumed samples</td><td>避免重复或跳过数据</td><td>训练样本统计错误</td></tr>
<tr><td>Parallelism metadata</td><td>记录 TP/PP/DP/ZeRO 分片方式</td><td>新拓扑无法正确重组 checkpoint</td></tr>
</table>
<p>工程优化手段：</p>
<ul>
<li><strong>分布式并行写</strong>：每个 rank 写自己的 shard，避免单 rank 聚合所有状态。</li>
<li><strong>异步 checkpoint</strong>：训练线程尽快继续，后台 I/O 写入共享存储；需要额外内存或 staging buffer。</li>
<li><strong>增量/差量 checkpoint</strong>：只保存变化状态，降低 I/O，但实现复杂。</li>
<li><strong>分层存储</strong>：本地 NVMe 做 staging，后台刷到 NFS/S3/HDFS；恢复时优先读本地或同机架副本。</li>
<li><strong>通用 checkpoint 格式</strong>：保存足够 metadata，支持从 TP/PP/ZeRO 的某种分片恢复到另一种分片。</li>
</ul>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果高优先级任务抢占 16 张 GPU，低优大模型训练如何不中断？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答框架</div><p>优先判断低优训练是否支持弹性。如果支持，尽量在 DP 维度缩容，而不是整组杀掉。调度器给 trainer 发送优雅抢占信号，trainer 完成当前 step 或 pipeline flush 后保存 checkpoint，释放被抢占节点，剩余 worker 重新 rendezvous，按新的 DP size 重建通信组并从同一 global step 继续。</p></div>
<div class="qa-section"><div class="qa-section-title">关键细节</div><p>TP/PP 尽量不变；checkpoint 要在共享存储上；恢复后要调整 global batch 或 gradient accumulation，保持有效 batch size 尽量稳定；如果无法弹性缩容，则做 checkpoint-aware preemption，选择 checkpoint 最新、重启成本最低的任务牺牲。</p></div>
<div class="qa-summary">面试金句：大模型弹性训练通常不是“随便少几张卡继续跑”，而是“固定 TP/PP，优先弹性 DP，并通过 checkpoint 重分片恢复”。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Checkpoint 频率怎么选？越频繁越好吗？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>不是。频率越高，抢占回滚损失越小，但 I/O 开销越大、训练停顿越多、共享存储压力越高。频率应该由失败率、抢占率、单次 checkpoint 耗时和可接受回滚时间共同决定。</p></div>
<div class="qa-section"><div class="qa-section-title">工程公式</div><p>可以用近似目标：最小化 <code>checkpoint_overhead_per_hour + expected_lost_work_per_hour</code>。如果集群抢占频繁或硬件故障率高，就提高 checkpoint 频率；如果是稳定独占集群，就降低频率并做异步 checkpoint。</p></div>
<div class="qa-summary">面试要点：checkpoint 是保险，不是免费操作。频率要根据故障/抢占概率和 I/O 成本折中。</div>
</div>
</div>

<div class="card card-s">
<h3>参考资料</h3>
<ul>
<li>DeepSpeed training/checkpointing 文档：覆盖 ZeRO、模型并行、checkpoint API 和大模型训练状态管理。</li>
<li>Universal Checkpointing 论文和 DeepSpeed 教程：强调 checkpoint 应支持不同并行配置之间的转换，用于故障恢复和弹性资源管理。</li>
<li>DeepSpeed elastic training 资料：说明动态 GPU 可用性变化时，需要 launcher、checkpoint 和 rank 重组协同。</li>
</ul>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试官问"你怎么设计训练任务的抢占策略"，怎么回答？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答框架</div>
<ol>
<li><strong>先说为什么训练抢占和普通 Pod 抢占不同</strong>：训练抢占有沉没成本（进度损失）、重启成本（模型加载+NCCL 重建）、拓扑成本（好的位置被让出来了）。</li>
<li><strong>再说代价感知抢占</strong>：不是简单看优先级，而是看 \text{release\_value} / (\text{checkpoint\_age} + \text{restart\_cost})。选这个比值最高的牺牲者。</li>
<li><strong>然后说优雅抢占</strong>：给任务优雅期做 checkpoint，超时后强制终止。</li>
<li><strong>最后说弹性训练</strong>：如果任务支持弹性，可以缩减 world size 而不是杀掉，释放部分 GPU 但训练继续。</li>
</ol>
</div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"训练任务的抢占不是简单的优先级排序，而是代价优化问题。好的抢占策略选择'最值得杀'的牺牲者——释放资源多、进度损失少、重启成本低。"</p></div>
</div>
</div>

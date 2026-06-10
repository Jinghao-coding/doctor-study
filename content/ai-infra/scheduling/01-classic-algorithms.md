<div class="card card-m">
<h3>经典调度算法：从直觉到数学</h3>
<p>经典调度算法是所有调度系统的基础。不管你用的是 K8S 默认调度器、Volcano 还是自研调度器，底层的排序逻辑一定逃不出这几个经典算法的思想。面试中，面试官期望你不只是知道算法名字，还能说清楚：<strong>为什么这个算法最优？最优的条件是什么？在什么条件下它会失败？</strong></p>
</div>

<div class="card card-d">
<h3>操作系统算法到 AI 集群调度的映射</h3>
<p>FIFO、SJF、Round Robin、优先级、CFS 这些名字来自操作系统，但在 AI Infra 里会变成队列排序、准入控制、租户公平、抢占和节点放置策略。学习时建议把它们分成两层：<strong>排序层</strong>决定“谁先被考虑”，<strong>放置层</strong>决定“放到哪里”。</p>
<table>
<tr><th>OS 调度概念</th><th>核心含义</th><th>集群调度中的对应物</th><th>AI Infra 注意点</th></tr>
<tr><td>FIFO / FCFS</td><td>按到达顺序执行</td><td>队列按提交时间排序</td><td>大 gang 任务可能造成 head-of-line blocking</td></tr>
<tr><td>SJF</td><td>短任务优先</td><td>短实验、短 inference batch、短 pipeline stage 优先</td><td>需要运行时长预测，长任务要配 aging 防饥饿</td></tr>
<tr><td>Round Robin</td><td>时间片轮转</td><td>队列/租户轮转，按 ClusterQueue 轮转取任务</td><td>GPU 任务不适合频繁时间片切换，但适合队列级轮转</td></tr>
<tr><td>优先级调度</td><td>高优先级先执行</td><td>PriorityClass、Queue priority、抢占</td><td>低优任务要有 aging 或保障份额，否则会长期饥饿</td></tr>
<tr><td>CFS</td><td>按虚拟运行时间实现公平份额</td><td>按 dominant share、quota debt 或保障度做公平调度</td><td>多资源场景不能只按 GPU 数公平，要看 CPU/内存/GPU/NIC 的主导资源</td></tr>
</table>
</div>

<div class="card card-s">
<h3>基础调度策略详解</h3>

<h4>1. FIFO（First In First Out）</h4>
<p><strong>定义</strong>：先到的任务先调度。不看任务大小、不看优先级、不看紧急程度。</p>
<p><strong>怎么理解</strong>：超市排队。先来先结账，不管你买 1 件还是 100 件。</p>
<p><strong>优点</strong>：实现最简单，不需要任何预测信息（不需要知道任务运行多久），天然公平（按到达顺序）。</p>
<p><strong>致命问题：Head-of-line blocking</strong>：如果队首是一个 10 小时的训练任务，后面 100 个 5 分钟的实验任务全部被阻塞。</p>
<p><strong>面试中怎么答</strong>：FIFO 是所有调度器的默认起点。面试时不要说"FIFO 不好"——要说"FIFO 在什么场景下够用，什么场景下不够"。对于同质任务（运行时间差不多），FIFO 就够了。对于异质任务（短实验 + 长训练），FIFO 的 head-of-line blocking 就不可接受了。</p>

<h4>2. SJF（Shortest Job First）</h4>
<p><strong>定义</strong>：运行时间最短的任务优先调度。不可抢占——一旦开始就必须跑完。</p>
<p><strong>核心性质：SJF 最小化平均等待时间</strong></p>
<p><strong>直觉证明</strong>：假设队列里有任务 A(1h) 和 B(10h)。如果先 A 后 B：A 等 0h，B 等 1h，平均等待 = 0.5h。如果先 B 后 A：B 等 0h，A 等 10h，平均等待 = 5h。短任务排前面，它们的等待时间短（因为本身短），长任务无论排哪里都要等，放后面只增加一个"短任务的执行时间"。所以短任务优先永远不劣。</p>
<p><strong>致命问题：饥饿</strong>：如果短任务源源不断到达，长任务可能永远排不上。</p>
<p><strong>前提条件</strong>：必须知道任务的运行时间。在 GPU 集群里，用户声明、历史统计或在线预测可以提供这个信息。</p>
<p><strong>面试中怎么答</strong>：面试官问"为什么 SJF 最优"，你应该：(1) 说"它最小化平均等待时间"；(2) 用简单的数字例子说明；(3) 补"但它会导致饥饿，需要 aging 或配额保障来缓解"。</p>

<h4>3. SRTF（Shortest Remaining Time First）</h4>
<p><strong>定义</strong>：SJF 的抢占版本。按<strong>剩余</strong>时间排序，新来的短作业可以打断正在执行的长作业。</p>
<p><strong>和 SJF 的本质区别</strong>：SJF 按总执行时间排序，任务一旦开始就不可中断。SRTF 按剩余时间排序，每当新任务到达时重新排序，可以抢占。</p>
<p><strong>什么时候比 SJF 更好</strong>：当任务到达时间不确定时。例如多 agent 工作流中，不断有新 stage 到达。SRTF 可以让新来的短 stage 立即执行，避免被正在执行的长 stage 阻塞。</p>
<p><strong>额外代价</strong>：(1) 需要抢占机制；(2) 需要更精确的剩余时间预测；(3) 抢占本身的成本（训练任务可能需要回滚到 checkpoint）。</p>
<p><strong>怎么理解</strong>：SJF 像"餐厅只接受预约，上桌了就不赶人走"。SRTF 像"急诊室分诊——新来了更急的病人，正在处理的可以先放一放"。</p>

<h4>4. EDF（Earliest Deadline First）</h4>
<p><strong>定义</strong>：截止时间最近的任务优先调度。可抢占。</p>
<p><strong>适用场景</strong>：有明确 deadline 的任务。如实时系统、数据 Pipeline（"明早 8 点前必须跑完"）、模型发布倒计时。</p>
<p><strong>最优性</strong>：在任务可抢占且 deadline 可知的前提下，EDF 是最优的——如果 EDF 都调不了，没有任何算法能调。</p>
<p><strong>局限</strong>：(1) 需要知道 deadline；(2) 系统过载时，所有接近 deadline 的任务会"集体崩溃"；(3) GPU 训练任务通常没有明确的 deadline，所以 EDF 在 GPU 集群中用得少。</p>
<p><strong>怎么理解</strong>：EDF 像"赶飞机"——谁离登机时间最近谁先走安检。</p>

<h4>5. Round Robin</h4>
<p><strong>定义</strong>：每个任务分配一个时间片，时间片用完就换下一个任务。循环往复。</p>
<p><strong>优点</strong>：绝对公平——每个任务获得相等的 CPU 时间。</p>
<p><strong>局限</strong>：(1) 上下文切换开销大——GPU 训练任务切换代价极高（模型加载 + NCCL 重建），不适合频繁切换；(2) 时间片大小难选——太小浪费切换时间，太大又退化成 FIFO。</p>
<p><strong>GPU 集群里几乎不用</strong>：因为 GPU 任务不能"切一小段就换"。但"按队列轮转调度"的思想（如 Kueue 的 ClusterQueue 轮转）是 Round Robin 的变体。</p>

<h4>6. 优先级调度</h4>
<p><strong>定义</strong>：按静态或动态优先级排序调度。优先级可以基于业务重要性、紧急程度、资源效率等。</p>
<p><strong>静态 vs 动态优先级</strong>：静态优先级在提交时确定，运行中不变。动态优先级可以变化——例如 aging（等待越久优先级越高）、或者基于 QAD（保障度低的队列优先级提升）。</p>
<p><strong>问题</strong>：低优先级任务可能饥饿。需要 aging 或配额保障来缓解。</p>
</div>

<div class="card card-d">
<h3>算法对比与选择</h3>
<table>
<tr><th>算法</th><th>可抢占</th><th>需要预测</th><th>最优性</th><th>饥饿风险</th><th>GPU 集群适用性</th></tr>
<tr><td>FIFO</td><td>否</td><td>否</td><td>同质任务最优</td><td>无</td><td>默认基线</td></tr>
<tr><td>SJF</td><td>否</td><td>是（运行时间）</td><td>最小化平均等待</td><td>长任务饥饿</td><td>短实验优先场景</td></tr>
<tr><td>SRTF</td><td>是</td><td>是（剩余时间）</td><td>最小化平均等待</td><td>长任务饥饿</td><td>多 agent 工作流</td></tr>
<tr><td>EDF</td><td>是</td><td>是（deadline）</td><td>实时最优</td><td>过载崩溃</td><td>Pipeline 场景</td></tr>
<tr><td>Round Robin</td><td>是</td><td>否</td><td>公平最优</td><td>无</td><td>几乎不用</td></tr>
<tr><td>优先级</td><td>可选</td><td>否</td><td>取决于优先级设定</td><td>低优先级饥饿</td><td>最常用</td></tr>
</table>

<h4>实际系统的组合策略</h4>
<p>真实调度器不会只用一个算法，而是<strong>组合使用</strong>：</p>
<ul>
<li><strong>排序阶段</strong>：优先级 + SJF（同优先级内按运行时间排序）</li>
<li><strong>准入阶段</strong>：Gang 检查 + Quota 检查</li>
<li><strong>放置阶段</strong>：Bin Packing + 拓扑打分</li>
<li><strong>抢占阶段</strong>：优先级 + 代价感知</li>
</ul>
<p>面试中，你要说清楚"每个决策点用了哪个算法的什么思想"，而不是笼统地说"用了 SJF"。</p>
</div>

<div class="card card-w">
<h3>Bin Packing vs Spread</h3>
<p>这是放置策略的经典对比，面试中经常出现。</p>

<h4>Bin Packing</h4>
<p><strong>定义</strong>：尽量把任务塞到已有节点，减少碎片。它来自装箱问题：给定一批物品和若干箱子，希望用尽可能少的箱子装下所有物品。在调度里，物品是 Pod/Job 的资源需求，箱子是 Node 或资源池。</p>
<p><strong>类比</strong>：装箱——先把一个箱子装满，再开新的。</p>
<p><strong>GPU 集群为什么常用</strong>：GPU 是昂贵资源，碎片化（节点 A 剩 1 GPU，节点 B 也剩 1 GPU，但需要 2 GPU 的任务放不进去）是最大浪费。Bin Packing 尽量让某些节点跑满，留出完整的空闲节点给大 gang。</p>
<p><strong>风险</strong>：(1) 单节点故障影响更多任务（爆炸半径大）；(2) 热点——某些节点过于拥挤。</p>

<h4>Bin Packing 在调度器里怎么实现</h4>
<table>
<tr><th>层次</th><th>做法</th><th>直觉</th><th>风险控制</th></tr>
<tr><td>Filter</td><td>过滤放不下 CPU/内存/GPU/端口/拓扑约束的节点</td><td>先保证可行</td><td>不要为了装箱破坏硬约束</td></tr>
<tr><td>Score</td><td>给“放入后剩余资源更少、更紧凑”的节点更高分</td><td>优先填满已有节点</td><td>加入温度、故障域、拓扑质量权重</td></tr>
<tr><td>Reserve</td><td>暂存被选节点上的资源占用</td><td>避免并发调度重复占用</td><td>失败时必须 Unreserve</td></tr>
<tr><td>全局队列</td><td>把小任务回填到碎片，把大任务留完整资源窗口</td><td>减少碎片累积</td><td>配合 backfill 和 aging 避免大任务/小任务互相伤害</td></tr>
</table>

<h4>Spread</h4>
<p><strong>定义</strong>：尽量把任务分散到不同节点。</p>
<p><strong>类比</strong>：分散投资——不把鸡蛋放在一个篮子里。</p>
<p><strong>适用场景</strong>：在线推理服务——需要高可用，节点挂了不能影响所有副本。</p>
<p><strong>风险</strong>：碎片化——每个节点都剩一点 GPU，但凑不出大块。</p>

<h4>选择建议</h4>
<table>
<tr><th>场景</th><th>推荐策略</th><th>原因</th></tr>
<tr><td>离线训练</td><td>Bin Packing</td><td>减少碎片，大 gang 更容易放得下</td></tr>
<tr><td>在线推理</td><td>Spread</td><td>高可用，单节点故障影响小</td></tr>
<tr><td>混合部署</td><td>推理 Spread + 训练 Bin Packing</td><td>不同任务类型用不同策略</td></tr>
<tr><td>多租户实验平台</td><td>Bin Packing + 故障域约束</td><td>减少碎片但避免单点故障</td></tr>
</table>
</div>

<div class="card card-m">
<h3>经典算法面试问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Head-of-line blocking 怎么解决？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>三种思路：</p>
<ol>
<li><strong>预测驱动排序</strong>：SRTF/SJF 让短任务先执行，减少被长任务阻塞的概率。这解决的是"队首长任务阻塞后面短任务"的问题。</li>
<li><strong>抢占</strong>：长任务阻塞时强制让位给高优先级任务。这解决的是"正在执行的任务不能被打断"的问题。</li>
<li><strong>多队列</strong>：不同类型任务分开排队，互不干扰。这解决的是"不同类型任务对延迟要求不同"的问题。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">组合使用</div><p>实际系统中常常同时使用多种：SRTF 排序 + 抢占 + 分队列。例如 K8S 调度器有多个 Queue（ActiveQ、BackoffQ、UnschedulableQ），在 ActiveQ 内部按优先级排序，高优先级任务可以触发 preemption。</p></div>
<div class="qa-summary">面试要点：三种思路各有适用场景，实际系统是组合使用的。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: SJF 为什么最优？会有什么问题？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">最优性证明（直觉版）</div><p>SJF 最小化平均等待时间。把短任务排前面，它们的等待时间短（因为本身短，不会让后面等太久）。长任务无论排哪里都要等前面的任务，放后面只增加一个"短任务的执行时间"，放前面却让所有后面的人都多等它的长时间。所以短任务优先永远不劣。</p></div>
<div class="qa-section"><div class="qa-section-title">问题：饥饿</div><p>如果短任务源源不断到达，长任务可能永远排不上。一个训练 20 小时的大任务，如果前面总有 5 分钟的实验任务插队，它可能等一天都启动不了。</p></div>
<div class="qa-section"><div class="qa-section-title">解决</div><p>(1) <strong>Aging</strong>：等待时间越长优先级越高。等了 N 小时的长任务优先级会超过刚到的短任务。(2) <strong>配额保障</strong>：每个租户至少获得一定比例的调度机会。(3) <strong>词典序排序</strong>：先看保障度（是否满足配额），再看运行时间。保障度不足的任务优先，同保障度内按 SJF 排序。</p></div>
<div class="qa-summary">面试要点：说清楚最优性 + 饥饿问题 + 三种解决思路。不要只说"SJF 最优"而忽略饥饿。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 抢占的代价有哪些？怎么降低？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">代价</div><p>(1) <strong>进度浪费</strong>：被抢占作业已完成的计算全部丢失（除非有 checkpoint）。一个训练了 20 小时、3 小时没 checkpoint 的任务被抢占，回滚到 17 小时前的状态。(2) <strong>重启开销</strong>：重新排队、加载模型/数据、重建 NCCL 通信组——可能需要 5-30 分钟。(3) <strong>系统开销</strong>：保存状态、清理资源、通知相关组件。</p></div>
<div class="qa-section"><div class="qa-section-title">降低代价</div><p>(1) <strong>Checkpoint 机制</strong>：定期保存进度，减少进度损失。代价是 I/O 开销。(2) <strong>代价基抢占</strong>：选择沉没成本最小的牺牲者——checkpoint 新鲜、运行时间短的任务优先被抢占。(3) <strong>在自然间隔抢占</strong>：在 stage 边界、epoch 结束时抢占，进度损失为零。需要训练框架配合。(4) <strong>优雅终止</strong>：通知任务"请 checkpoint 后退出"，给 5 分钟优雅期。(5) <strong>弹性训练</strong>：缩减 world size 而非杀掉整个任务，释放部分 GPU 但训练继续。</p></div>
<div class="qa-summary">面试要点：抢占不是免费的。列出具体代价，再给出具体降低方案，比只说"可以做抢占"更有区分度。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 多维资源调度的挑战？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>GPU 集群的资源是多维的——CPU、内存、GPU、网络带宽。三个核心挑战：</p>
<ol>
<li><strong>碎片化</strong>：某些维度剩余很多，但另一个维度不够，整个节点不可用。例如一个节点剩 7 GPU 但内存用完了，那 7 GPU 也是浪费的。</li>
<li><strong>耦合性</strong>：GPU 任务通常也需要大量 CPU 做数据预处理。一个任务分配了 8 GPU 但 CPU 不够，数据加载跟不上，GPU 在等数据。</li>
<li><strong>异构性</strong>：不同 GPU 型号性能差异大。1 张 H100 ≈ 4 张 V100，但调度器可能只看到"1 张 GPU"。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">解决思路</div><p>DRF 从理论上解决公平性，但实际中还需要拓扑感知（NVLink 拓扑）、亲和性约束（CPU-GPU NUMA）和异构资源表达（GPU flavor）。</p></div>
<div class="qa-summary">面试要点：多维资源调度的核心挑战是"碎片化 + 耦合性 + 异构性"，不是简单地"维度多了"。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 调度延迟和调度质量的 trade-off？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心矛盾</div><p>更好的调度决策需要更多信息（拓扑、负载预测、历史数据）和更多计算（更复杂的打分函数），但用户不想等太久——任务提交后应该尽快开始。</p></div>
<div class="qa-section"><div class="qa-section-title">四种解决方式</div><p>(1) <strong>两阶段调度</strong>：Filter 快速排除明显不行的（几十毫秒），Score 只在少量候选中精选（几百毫秒）。大部分节点在 Filter 阶段就被淘汰了。(2) <strong>缓存</strong>：Informer 本地缓存节点和 Pod 信息，避免每次调度都查 API Server。(3) <strong>近似算法</strong>：不需要最优解，"足够好"就行。例如只对 top-K 候选节点做详细打分。(4) <strong>异步</strong>：Bind 阶段异步执行，不阻塞下一个 Pod 的调度周期。调度器和 binder 是并行工作的。</p></div>
<div class="qa-section"><div class="qa-section-title">K8S 的实际做法</div><p>K8S scheduler 的一个 scheduling cycle 约 10-100ms。它用 Informer cache + 两阶段 Filter/Score + 异步 Bind 来保证延迟可接受。</p></div>
<div class="qa-summary">面试要点：调度是"质量 vs 延迟"的 trade-off，K8S 用缓存 + 两阶段 + 近似 + 异步来平衡。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试官问"你怎么选择调度算法"，怎么回答？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答框架</div><p>不要说"我选 XX 算法"，而要说"我根据场景选择"：</p>
<ol>
<li><strong>先定场景</strong>：推理/训练/实验平台？不同场景对延迟、吞吐、公平性的要求不同。</li>
<li><strong>再看约束</strong>：是否有 gang 需求？是否有 deadline？是否需要预测运行时间？</li>
<li><strong>然后选排序策略</strong>：同质任务用 FIFO，异质任务用优先级 + SJF，有 deadline 用 EDF。</li>
<li><strong>最后说组合</strong>：实际系统是组合使用的——排序用 SJF/DRF，准入用 Gang/Quota，放置用 Bin Packing + 拓扑打分，抢占用代价感知。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"调度算法的选择不是非此即彼，而是根据场景在经典算法的基础上组合和调整。关键是说清楚每个决策点用了什么思想、为什么这样选。"</p></div>
</div>
</div>
</div>

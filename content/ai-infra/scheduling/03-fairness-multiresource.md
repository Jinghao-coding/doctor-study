<div class="card card-m">
<h3>多资源公平：调度方向的核心基本功</h3>
<p>GPU 集群不是单资源系统。一个训练任务同时消耗 GPU、CPU、内存、网络、存储带宽和拓扑位置。多资源公平要解决的问题是：当不同租户的资源需求形态不同，系统如何定义"公平"。</p>
<p>为什么这个问题难？因为"公平"本身就没有唯一答案。团队 A 跑 CV 任务需要大量 GPU 但很少内存，团队 B 跑 NLP 任务 GPU 和内存需求差不多。如果只看 GPU 数量均分，B 觉得 CPU 被忽视；如果只看内存均分，A 觉得 GPU 被忽视。所以核心问题是：<strong>在多维资源空间里，怎么定义"公平"这个概念</strong>。</p>
</div>

<div class="card card-s">
<h3>基础概念：从单资源公平到多资源公平</h3>

<h4>Max-Min Fairness（单资源）</h4>
<p>这是公平性算法的起点，只处理一种资源。</p>
<p><strong>定义</strong>：按需分配，每个用户至少获得 1/N 份额，不需要更多的用户把多余份额让给需要的人。递归地最大化最小分配。</p>
<p><strong>手动推演</strong>：集群有 100 张 GPU，4 个用户分别需要 50、30、15、40 张。</p>
<ol>
<li>初始每人 100/4 = 25 张。用户 3 只需要 15，多出 10。</li>
<li>剩余 75 张分给 3 人，每人 25。用户 2 只需要 30，已拿 25，还需 5，多出 20。</li>
<li>剩余 60 张分给 2 人，每人 30。用户 1 需要 50 但只拿到 30，用户 4 需要 40 也拿到 30。</li>
<li>最终：用户 1 = 30，用户 2 = 30，用户 3 = 15，用户 4 = 30。</li>
</ol>
<p><strong>怎么理解</strong>：Max-Min Fairness 就像分蛋糕——先均分，吃不完的人把多余的分给不够的人，反复进行直到没有人能拿到更多。它保证"最穷的人尽可能不穷"。</p>
<p><strong>局限</strong>：只处理单一资源。如果集群有 GPU 和 CPU 两种资源，用户 A 需要 (8 GPU, 2 CPU)，用户 B 需要 (2 GPU, 8 CPU)，Max-Min Fairness 不知道怎么在两个维度上同时定义"公平"。</p>

<h4>Proportional Share（按比例分配）</h4>
<p><strong>定义</strong>：按权重分配资源。团队 A 权重 3，团队 B 权重 1，那 A 拿 75% 的资源，B 拿 25%。</p>
<p><strong>适用场景</strong>：适合有明确组织权重的治理场景，比如公司级"大团队多分，小团队少分"。</p>
<p><strong>局限</strong>：权重是人为设定的，不自动处理多维瓶颈。如果团队 A 权重高但只消耗 GPU，团队 B 权重低但 CPU 是瓶颈，按权重分 GPU 可能对 B 来说 CPU 完全不够。Proportional Share 不理解"哪种资源是瓶颈"。</p>
<p><strong>怎么理解</strong>：Proportional Share 像"按出资比例分红"，简单直接但不关心每个股东实际缺什么。</p>
</div>

<div class="card card-d">
<h3>DRF（Dominant Resource Fairness）详解</h3>
<p>DRF 是多资源公平调度的基石算法，由 Ghodsi et al. 2011 提出。几乎所有面试里问到"多资源公平"都期望你从 DRF 开始回答。</p>

<h4>核心思想</h4>
<p>每个用户的<strong>主导资源</strong>（dominant resource）是它在所有资源维度中占比最高的那一维。DRF 试图让不同用户的 dominant share 尽量接近，而不是让某个维度的资源被某个用户独占。</p>

<h4>逐步推演</h4>
<p>集群有 <code>&lt;9 CPU, 18 GB 内存&gt;</code>。用户 A 的任务需要 <code>&lt;1 CPU, 4 GB&gt;</code>，用户 B 的任务需要 <code>&lt;3 CPU, 1 GB&gt;</code>。</p>
<p><strong>Step 1：计算每个用户每个维度的占比</strong></p>
<ul>
<li>用户 A 一个任务占 CPU 1/9 ≈ 11%，内存 4/18 ≈ 22%。<strong>A 的主导资源是内存，dominant share = 22%</strong></li>
<li>用户 B 一个任务占 CPU 3/9 ≈ 33%，内存 1/18 ≈ 6%。<strong>B 的主导资源是 CPU，dominant share = 33%</strong></li>
</ul>
<p><strong>Step 2：每次选择 dominant share 最低的用户分配一个任务</strong></p>
<ul>
<li>Round 1：A 的 dominant share = 0，B = 0。先给 A。A 运行 1 个任务：A 的 share 变为 (1/9, 4/18)。</li>
<li>Round 2：A 的 dominant share = 4/18 ≈ 22%，B = 0。给 B。B 运行 1 个任务：B 的 share 变为 (3/9, 1/18)。</li>
<li>Round 3：A 的 dominant share = 4/18 ≈ 22%，B = 3/9 ≈ 33%。给 A。A 运行第 2 个任务：A = (2/9, 8/18)。</li>
<li>Round 4：A 的 dominant share = 8/18 ≈ 44%，B = 3/9 ≈ 33%。给 B。B 运行第 2 个任务：B = (6/9, 2/18)。</li>
<li>Round 5：A 的 dominant share = 8/18 ≈ 44%，B = 6/9 ≈ 67%。给 A。A 运行第 3 个任务：A = (3/9, 12/18)。</li>
<li>Round 6：资源余量：CPU = 9-3-6 = 0。CPU 用完了，无法继续分配。</li>
</ul>
<p><strong>最终分配</strong>：A 运行 3 个任务，B 运行 2 个任务。A 的 dominant share = 12/18 ≈ 67%，B 的 dominant share = 6/9 ≈ 67%。两者主导资源份额相等，这就是 DRF 的目标。</p>

<h4>DRF 的三个关键性质</h4>
<ol>
<li><strong>Sharing Incentive（共享激励）</strong>：每个用户分到的资源不少于均分。如果用户独占集群，不会比共享时更好。</li>
<li><strong>Envy-freeness（无嫉妒）</strong>：没有任何用户会觉得别人的分配比自己的更好。A 不会想和 B 换。</li>
<li><strong>Pareto Efficiency（帕累托效率）</strong>：不存在另一种分配方式能让某个用户更好而不让其他用户更差。</li>
</ol>
<p><strong>怎么理解这三个性质</strong>：Sharing Incentive 是"参与比不参与更好"；Envy-freeness 是"没有后悔"；Pareto Efficiency 是"没有浪费"。三个一起保证"公平且高效"。</p>

<h4>DRF 在 GPU 集群中的应用</h4>
<p>GPU 集群的资源维度通常是 <code>&lt;GPU, CPU, 内存, 网络带宽&gt;</code>。一个训练任务的 dominant resource 通常是 GPU，但如果一个任务只用 1 GPU 但消耗大量 CPU 做数据预处理，那 CPU 可能是它的 dominant resource。</p>
<p><strong>实际部署中的变体</strong>：原生 DRF 不理解异构 GPU、拓扑位置和任务优先级。工业界通常用 DRF 的思想做基础，然后叠加：(1) 按 GPU flavor 分开算 dominant share；(2) 拓扑位置作为软约束在 Score 阶段叠加；(3) 优先级作为权重乘在 dominant share 上。</p>
</div>

<div class="card card-w">
<h3>Elastic Quota 和 QAD：从理论到工程</h3>
<p>DRF 是理论算法，Elastic Quota 和 QAD 是工程落地方案。面试中如果你能从 DRF 过渡到工程实现，会很加分。</p>

<h4>Elastic Quota</h4>
<p><strong>核心思想</strong>：每个队列/租户有 min（保障量）和 max（上限）。min 保证资源不比这个少，max 限制最多用这么多。当某些队列的 min 没用完时，其他队列可以临时借用超过自己 min 但不超过 max 的资源。</p>
<p><strong>手动推演</strong>：集群 100 张 GPU。队列 A min=30, max=60；队列 B min=50, max=80。</p>
<ul>
<li>队列 A 当前用了 10 张，队列 B 当前用了 50 张。A 的 min 没用完（还剩 20 张保障量），B 已经用满自己的 min。</li>
<li>B 想启动新任务需要 10 张 GPU。此时 B 的 min 已满足，它可以借用 A 空闲的 20 张。B 的使用量变为 60，不超过 max=80。</li>
<li>后来 A 提交了新任务需要 20 张 GPU。调度器需要从 B 那里回收 20 张（B 借用了 A 的配额），让 A 的使用量从 10 增加到 30（达到 min）。</li>
</ul>
<p><strong>怎么理解</strong>：Elastic Quota 像"公司工位"。你的团队保障有 30 个工位（min），但上限是 60 个（max）。如果你只坐了 10 个，其他团队可以临时坐。但你回来的时候，坐你工位的人必须让出来。</p>
<p><strong>关键难点</strong>：回收策略。从谁那里回收？回收多少？回收的任务怎么处理？这直接决定了 Elastic Quota 在生产环境是否可用。</p>

<h4>QAD（Quota Assurance Degree）</h4>
<p><strong>定义</strong>：QAD = 实际获得资源 / 保障配额。如果队列 A 的保障量是 30 张 GPU，当前只拿到 27 张，QAD = 27/30 = 0.9。</p>
<p><strong>和 Elastic Quota 的区别</strong>：Elastic Quota 用 min/max 做离散阈值，QAD 用连续值表达保障程度。</p>
<p><strong>为什么 QAD 更好</strong>：</p>
<ul>
<li><strong>更细粒度</strong>：不是"满足/不满足"的二值判断，而是"满足到什么程度"。调度器可以设 QAD 阈值（如 ≥ 0.95），低于这个值就触发回收。</li>
<li><strong>更适合做抢占决策</strong>：抢占谁的资源？看哪个借用者的 QAD 最低、哪个保障租户的 QAD 最不满足。这比简单的"超过 min 就回收"更精确。</li>
<li><strong>更容易做渐进式回收</strong>：不需要一次性把所有借用资源都回收回来，而是回收到 QAD 达标为止。</li>
</ul>
<p><strong>怎么理解</strong>：QAD 像"手机电量百分比"。不是说"有电/没电"，而是告诉你"还剩 90%"。调度器看到 QAD < 0.95，就知道需要开始"充电"了。</p>

<h4>三者关系总结</h4>
<table>
<tr><th>机制</th><th>解决什么问题</th><th>优势</th><th>局限</th><th>怎么理解</th></tr>
<tr><td>DRF</td><td>多维资源的公平定义</td><td>理论优美，有数学性质保证</td><td>不理解拓扑、优先级和工程约束</td><td>分蛋糕的数学理论</td></tr>
<tr><td>Elastic Quota</td><td>保障+弹性的工程实现</td><td>落地简单，min/max 直观</td><td>回收策略粗糙，没有连续保障度</td><td>工位的保障和借用</td></tr>
<tr><td>QAD</td><td>保障度的精细表达</td><td>连续值、可设阈值、可渐进回收</td><td>需要持续监控和计算</td><td>手机电量百分比</td></tr>
</table>
</div>

<div class="card card-s">
<h3>GPU 集群里的公平性难点</h3>
<p>理论算法在 GPU 集群里会遇到哪些"理论没覆盖"的问题？面试中如果你能说出这些，说明你不只是背了算法，而是理解了工程现实。</p>

<h4>1. 异构 GPU：1 张 H100 ≠ 1 张 V100</h4>
<p><strong>问题</strong>：DRF 的基本假设是同类资源可互换。但 H100 的算力约是 V100 的 4 倍。如果一个用户分到 8 张 V100，另一个分到 8 张 H100，按数量看"公平"了，但实际算力差距巨大。</p>
<p><strong>解决思路</strong>：(1) 按 GPU flavor 分开计算 dominant share——H100 是一种资源，V100 是另一种。(2) 用算力等价因子归一化——1 H100 ≈ 4 V100，然后按归一化后的量做公平分配。(3) Kueue 的 ResourceFlavor 天然支持这种拆分。</p>
<p><strong>面试怎么答</strong>：先说"异构 GPU 打破了 DRF 同类资源可互换的假设"，然后给出 2-3 种解决思路，最后说"选择哪种取决于集群异构程度和运维复杂度"。</p>

<h4>2. 拓扑资源：同样是 8 张 GPU，性能可能差 2 倍</h4>
<p><strong>问题</strong>：8 张 GPU 在同一节点 NVLink 互联，和 8 张 GPU 分散在 4 个节点，训练吞吐可能差 2 倍以上。DRF 不区分拓扑位置。</p>
<p><strong>解决思路</strong>：拓扑在 Score 阶段叠加，不在 Fairness 阶段处理。Fairness 只管"数量公平"，Topology 只管"位置优化"。</p>
<p><strong>面试怎么答</strong>：DRF 保证份额公平，拓扑保证性能最优，两者是不同层面的问题。不要试图在 DRF 里加入拓扑——会让问题无解。</p>

<h4>3. 任务弹性：4 卡能跑，8 卡也能跑</h4>
<p><strong>问题</strong>：有些训练任务可以弹性伸缩（4/8/16 卡都行），有些必须固定 world size。如果只看"分配了多少 GPU"，弹性任务可能总是拿到更多。</p>
<p><strong>解决思路</strong>：弹性任务的 GPU 需求按"目标 world size"算 dominant share，而不是按"实际拿到多少"。这样弹性任务借到额外 GPU 不会影响公平性计算。</p>

<h4>4. 抢占成本：长时间训练被抢占代价极高</h4>
<p><strong>问题</strong>：DRF 不理解抢占代价。如果为了满足另一个用户的 dominant share 而抢占一个训练了 20 小时的任务，公平性指标改善了，但实际产出可能变差了。</p>
<p><strong>解决思路</strong>：在抢占决策中叠加代价感知——不是简单地选 dominant share 最高的抢占，而是选"释放资源量 / 抢占代价"比值最高的牺牲者。</p>
</div>

<div class="card card-m">
<h3>从公平性到队列设计</h3>
<p>面试中经常问"怎么设计一个多租户 GPU 集群的队列系统"。这里把公平性理论映射到工程实现。</p>

<h4>队列五大能力</h4>
<table>
<tr><th>能力</th><th>解决什么问题</th><th>设计要点</th><th>不做的后果</th></tr>
<tr><td>Quota（配额）</td><td>团队资源保障</td><td>min/max、hard/soft、按 GPU flavor 区分</td><td>大团队占满所有资源，小团队永远排不上</td></tr>
<tr><td>Borrowing（借用）</td><td>提高利用率</td><td>空闲资源可借，但要记录来源和可回收性</td><td>保障配额空闲时其他人在排队，利用率低</td></tr>
<tr><td>Reclaim（回收）</td><td>保障租户需要资源时拿回来</td><td>选择低优先级、低沉没成本、checkpoint 新鲜的任务</td><td>保障形同虚设——借出去的资源收不回来</td></tr>
<tr><td>Admission（准入）</td><td>避免已运行任务半死不活</td><td>资源不够时先排队，而不是让部分 worker 占住 GPU</td><td>部分 Pod 占住 GPU 但 gang 凑不齐，GPU 空转</td></tr>
<tr><td>Hierarchy（层级）</td><td>组织结构复杂时治理</td><td>公司/部门/团队多级队列与权重</td><td>100 个团队用扁平队列，配额管理爆炸</td></tr>
</table>

<h4>队列设计的面试回答框架</h4>
<ol>
<li><strong>先说 Quota</strong>：每个队列有保障配额（min）和上限（max），min 是硬承诺，max 是弹性天花板。</li>
<li><strong>再说 Borrowing</strong>：空闲资源允许借用，但标记为"可回收"——保障租户需要时必须能拿回来。</li>
<li><strong>然后说 Reclaim</strong>：回收策略是关键——优先回收 QAD 低的借用者、沉没成本小的任务、checkpoint 新鲜的任务。</li>
<li><strong>再说 Admission</strong>：Gang 任务要准入控制——没有足够资源就不让任何 Pod 启动，避免 partial allocation。</li>
<li><strong>最后说 Hierarchy</strong>：公司/部门/团队三级队列，权重在各级分配。</li>
</ol>
</div>

<div class="card card-d">
<h3>多租户 GPU 调度器：公平性怎么落地</h3>
<p>多租户场景不能只靠 Kubernetes Namespace 或 ResourceQuota。真正的公平调度至少要有队列、配额、借用、回收、优先级和审计。面试回答时可以从“保障谁、允许谁借、从谁回收、怎么避免饥饿”四个问题展开。</p>
<table>
<tr><th>机制</th><th>解决的问题</th><th>设计要点</th><th>常见追问</th></tr>
<tr><td>队列 Queue</td><td>把不同团队/业务隔离成可治理单元</td><td>支持层级队列：公司 / 部门 / 团队 / 项目</td><td>为什么不用一个全局 FIFO？</td></tr>
<tr><td>配额 Quota</td><td>给团队资源保障和上限</td><td>min 是保障，max 是上限；按 GPU flavor 拆分</td><td>H100 和 A100 能不能混算？</td></tr>
<tr><td>借用 Borrowing</td><td>避免空闲配额浪费</td><td>空闲资源可借，但要记录 owner 和 borrower</td><td>借用资源什么时候归还？</td></tr>
<tr><td>回收 Reclaim</td><td>保障租户需要资源时拿回来</td><td>优先回收低优先级、checkpoint 新鲜、沉没成本小的任务</td><td>如何避免回收造成大量损失？</td></tr>
<tr><td>优先级 Priority</td><td>表达业务重要性</td><td>线上推理、紧急评测、关键训练高于 best-effort 实验</td><td>低优任务会不会永远饿死？</td></tr>
<tr><td>Aging</td><td>避免长时间等待</td><td>等待越久，动态优先级越高</td><td>aging 会不会破坏业务优先级？</td></tr>
</table>
<div class="qa-summary">面试口径：公平不是平均分资源，而是在保障配额、弹性借用和可控回收之间取得平衡。</div>
</div>

<div class="card card-w">
<h3>高优任务抢占低优任务：代价不能忽略</h3>
<p>抢占是解决高优任务等待的手段，但在 AI 训练里非常昂贵。一个 Pod 被杀不只是“重启一下”，还可能丢失 checkpoint 之后的训练进度、重建 NCCL 通信组、重新加载模型和数据。</p>
<table>
<tr><th>代价</th><th>含义</th><th>缓解方式</th></tr>
<tr><td>进度损失</td><td>回滚到上一次 checkpoint</td><td>checkpoint-aware preemption，优先抢 checkpoint 新鲜任务</td></tr>
<tr><td>重启成本</td><td>排队、拉镜像、加载模型、初始化通信</td><td>镜像预热、本地缓存、NCCL 初始化优化</td></tr>
<tr><td>通信重建</td><td>DDP/NCCL world 重新建立</td><td>弹性训练或 gang 级别重启</td></tr>
<tr><td>用户体验</td><td>长期训练被频繁打断</td><td>抢占次数限制、冷却时间、优雅抢占</td></tr>
<tr><td>系统抖动</td><td>大量任务被杀和重启造成控制面压力</td><td>分批抢占、限速、队列级回收</td></tr>
</table>
<p>工程上常用一个简化打分：释放资源价值越高越适合抢，占用资源越少但 checkpoint 很旧的任务不一定适合抢。</p>
<div class="formula">$$\text{preemption\_score} = \text{release\_value} / (\text{checkpoint\_age} + \text{restart\_cost} + \text{disruption\_penalty})$$</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么只用 ResourceQuota 不够做 GPU 多租户调度？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>Namespace ResourceQuota 是静态上限——"你最多用这么多"。但 GPU 多租户需要：(1) 排队——满了之后不是拒绝，而是排队等待；(2) 公平分享——不同租户按份额或 dominant share 分配；(3) 借用与回收——空闲资源允许借用，但保障租户需要时能拿回来；(4) Gang admission——一组 Pod 要么全放行，要么全排队；(5) 按 GPU flavor 区分配额——A100 和 H100 不能混着算。ResourceQuota 做不到这些。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么这样设计</div><p>ResourceQuota 是 K8S 早期为在线服务设计的，假设每个 Pod 独立运行、资源需求固定、不需要排队。GPU 训练任务打破了所有这些假设。</p></div>
<div class="qa-summary">面试要点：ResourceQuota 是"静态上限"，GPU 多租户需要的是"动态排队+公平+借用回收+Gang 准入"。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: DRF 的 dominant share 计算过程，能手动推一遍吗？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">场景</div><p>集群 <code>&lt;9 CPU, 18 GB 内存&gt;</code>。用户 A 任务需要 <code>&lt;1 CPU, 4 GB&gt;</code>，用户 B 任务需要 <code>&lt;3 CPU, 1 GB&gt;</code>。</p></div>
<div class="qa-section"><div class="qa-section-title">推演</div><p>A 的主导资源是内存（4/18 > 1/9），B 的主导资源是 CPU（3/9 > 1/18）。DRF 优先给 dominant share 低的用户分配。</p>
<p>Round 1: A(0,0) B(0,0) → 给 A → A=(1/9, 4/18), dominant=4/18</p>
<p>Round 2: A=4/18 B=0 → 给 B → B=(3/9, 1/18), dominant=3/9</p>
<p>Round 3: A=4/18 B=3/9 → 给 A → A=(2/9, 8/18), dominant=8/18</p>
<p>Round 4: A=8/18 B=3/9 → 给 B → B=(6/9, 2/18), dominant=6/9</p>
<p>Round 5: A=8/18 B=6/9 → 给 A → A=(3/9, 12/18), dominant=12/18</p>
<p>Round 6: CPU 余量 = 9-3-6 = 0，停止。最终 A=3任务, B=2任务, 双方 dominant share 均为 67%。</p></div>
<div class="qa-summary">面试要点：能手动推演 DRF，说清楚 dominant resource 是哪一维、每轮为什么选这个用户、什么时候停。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Elastic Quota 的回收策略怎么设计？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>回收要解决三个问题：从谁那里回收、回收多少、回收的任务怎么处理。</p></div>
<div class="qa-section"><div class="qa-section-title">从谁那里回收</div><p>优先选择：(1) 借用量最大的队列——他们超出保障最多，回收对他们的 QAD 影响最小；(2) 正在运行的任务中沉没成本最低的——刚启动不久的、checkpoint 新鲜的；(3) 优先级最低的任务。</p></div>
<div class="qa-section"><div class="qa-section-title">回收多少</div><p>渐进式回收，不是一次全收。目标是让保障租户的 QAD 恢复到阈值（如 0.95）。例如保障租户差 5 张 GPU，就回收 5 张，不多收。</p></div>
<div class="qa-section"><div class="qa-section-title">回收的任务怎么处理</div><p>三种方式：(1) 优雅终止——等任务 checkpoint 后停止（延迟最高但对用户最友好）；(2) 检查点后终止——触发一次紧急 checkpoint，然后停止；(3) 立即终止——对低优先级或短任务适用。具体选哪种取决于任务的 checkpoint 频率和优先级。</p></div>
<div class="qa-summary">面试要点：回收不是简单的"杀掉低优先级"，而是要考虑沉没成本、渐进式回收和优雅终止。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果两个用户的 dominant resource 一样怎么办？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>DRF 退化成单资源公平分配。如果两个用户的 dominant resource 都是 GPU，那 DRF 等价于在 GPU 维度上做 Max-Min Fairness。这不是 bug，而是 DRF 在特定负载下的自然行为。</p></div>
<div class="qa-section"><div class="qa-section-title">实际影响</div><p>GPU 集群里很多用户的主导资源都是 GPU。这时候 DRF 的多资源优势不明显，更像是"GPU 数量的 Max-Min Fairness"。但加入 CPU、内存、网络带宽后，不同用户的 dominant resource 就会分化。</p></div>
<div class="qa-summary">面试要点：说清楚 DRF 在不同负载下的退化行为，比单纯背算法更能展示理解深度。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: DRF 的 Sharing Incentive 性质是什么意思？为什么重要？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">定义</div><p>Sharing Incentive：每个用户在共享系统里分到的资源，不少于把总资源均分后自己独占那一份。即：参与共享不比独占差。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么重要</div><p>这是公平性的底线。如果某个用户发现"我参与共享拿到的资源还不如我自己独占 1/N 集群"，他就没有动力参与共享，整个多租户系统的基础就崩了。</p></div>
<div class="qa-section"><div class="qa-section-title">反例</div><p>如果用"按 GPU 数量均分"，但某个用户需要的资源主要是内存（他的任务每个只需要 1 GPU 但要 64GB 内存），均分 GPU 后他拿到的内存可能远低于 1/N。这时 Sharing Incentive 被违反了——他参与共享不如独占。DRF 通过看 dominant resource 来保证这一点。</p></div>
<div class="qa-summary">面试要点：Sharing Incentive 是"参与共享的最低动力"，DRF 通过 dominant share 来保证这一点。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试官问"你怎么设计多租户 GPU 集群的公平性"，怎么回答？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答框架（4 步）</div>
<ol>
<li><strong>定义公平</strong>：先说在 GPU 集群里"公平"是多维的——GPU、CPU、内存、拓扑。用 DRF 的 dominant share 定义公平。</li>
<li><strong>工程实现</strong>：DRF 是理论，工程上用 Elastic Quota + QAD。min 保障、max 上限、空闲借用、QAD 驱动回收。</li>
<li><strong>GPU 特有问题</strong>：异构 GPU 按 flavor 分开算、拓扑在 Score 叠加、弹性任务按目标 world size 算、抢占要代价感知。</li>
<li><strong>验证方法</strong>：用 dominant share 的基尼系数或 QAD 分布衡量公平性，用 JCT 和利用率衡量效率，看公平性和效率的 trade-off。</li>
</ol>
</div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"公平性不是均分，而是在多维资源空间里让每个用户的瓶颈资源都不吃亏。DRF 解决了定义问题，Elastic Quota + QAD 解决了工程实现问题，异构 GPU 和拓扑是 GPU 集群特有的延伸。"</p></div>
</div>
</div>

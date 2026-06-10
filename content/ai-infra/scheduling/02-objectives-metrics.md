<div class="card card-m">
<h3>为什么调度要先定目标函数</h3>
<p>很多人学调度会直接跳到算法——"怎么排序、怎么打分、怎么抢占"。但调度本质上是一个<strong>多目标优化问题</strong>：你在优化某个指标的同时，必然在牺牲另一个指标。如果不确定优化什么，算法就无从谈起。</p>
<p>举个例子：同样的集群，如果你优化<strong>平均 JCT</strong>，短作业优先（SJF）是最好的；但如果你优化<strong>公平性</strong>，SJF 会让长作业饥饿。两个目标都合理，但策略完全不同。</p>
<p>所以学调度的第一步，不是学算法，而是搞清楚<strong>每个指标衡量什么、谁在用它、它和别的指标怎么冲突</strong>。</p>
</div>

<div class="card card-s">
<h3>核心指标详解</h3>

<h4>1. Waiting Time（等待时间）</h4>
<p>定义：从任务提交到任务开始执行的时间。注意是"开始执行"，不是"执行完毕"。</p>
<p>为什么重要：它衡量的是<strong>用户感知的响应速度</strong>。一个实验提交后等了 2 小时才开始跑，体验就很差。对于交互式任务、开发调试和在线推理，等待时间是最直接的体验指标。</p>
<p>面试中怎么用：当面试官问"你的调度器如何改善用户体验"，如果你的系统侧重排队策略，waiting time 就是你最该展示的指标。但要注意，降低等待时间不等于降低 JCT——一个任务可能等 1 分钟就启动了，但跑了 10 小时。</p>
<p>怎么理解：想象你在超市排队。Waiting time 就是你从拿号到开始结账的时间。前面人少就快，前面有个人买了一整车东西就慢。SJF 相当于"买得少的人先结账"。</p>

<h4>2. JCT（Job Completion Time）</h4>
<p>定义：从任务提交到任务完成的总时间 = waiting time + execution time。</p>
<p>为什么重要：对于离线训练、批处理和 HPC 任务，用户最关心的是"我什么时候能拿到结果"，而不是"什么时候开始跑"。JCT 是 AI 训练调度论文里最常用的指标。</p>
<p>面试中怎么用：面试官问"你的调度策略对训练任务有什么好处"，你应该从 JCT 切入，但要分解成 waiting time 和 execution time 分别说明。例如拓扑感知调度不改变等待时间，但通过减少通信开销来降低 execution time，从而降低 JCT。</p>
<p>怎么理解：JCT = 排队时间 + 跑的时间。改善排队靠排序和准入策略，改善跑的时间靠拓扑放置和资源分配。</p>

<h4>3. Makespan</h4>
<p>定义：一批任务中，最后一个完成的时间。衡量的是"整批活什么时候干完"。</p>
<p>为什么重要：在批处理场景下，运维更关心"这批任务什么时候全部跑完"而不是单个任务体验。例如一个数据 Pipeline 要在明早 8 点前跑完，makespan 就是关键指标。</p>
<p>面试中怎么用：问"你怎么衡量一个批调度系统的效率"时，makespan 是答案之一，但要补一句——它和公平性冲突，因为最优 makespan 可能意味着某些任务被无限推迟。</p>
<p>怎么理解：Makespan 是站在管理员视角，JCT 是站在用户视角。两个视角对"好调度"的定义不同。</p>

<h4>4. Throughput（吞吐量）</h4>
<p>定义：单位时间内完成的任务数，或单位时间内处理的 token/images 数。</p>
<p>为什么重要：集群运营商和平台团队最关心吞吐，因为它直接对应资源产出效率。同样 100 张 GPU，如果调度策略能让每天完成的训练任务数从 50 增加到 80，相当于节省了 37.5% 的硬件成本。</p>
<p>面试中怎么用：不要把吞吐和利用率混淆——吞吐是产出，利用率是资源使用率。高利用率不一定意味着高吞吐（可能在跑低效任务），但低利用率通常意味着吞吐也不高。</p>
<p>怎么理解：吞吐 = 集群的"产出速度"。利用率 = 集群的"忙碌程度"。忙碌不等于高效。</p>

<h4>5. Utilization（资源利用率）</h4>
<p>定义：已使用资源 / 总资源。常见的有 GPU 利用率、CPU 利用率、内存利用率、网络带宽利用率。</p>
<p>为什么重要：GPU 利用率是 AI Infra 里最常被关注的指标。一个 8 卡 A100 节点的 GPU 利用率如果只有 30%，意味着 70% 的算力在闲置，而一张 A100 售价超过 1 万美元。</p>
<p>常见误区：高利用率 ≠ 好调度。如果一个调度器把所有任务都塞到少数节点上，利用率确实高，但可能牺牲了拓扑质量、公平性或故障隔离。利用率是一个"不该太低，但也不是越高越好"的指标。</p>
<p>面试中怎么用：当面试官问"怎么提高 GPU 利用率"，你应该先问"什么类型的任务"。在线推理可以通过 continuous batching 提高；离线训练可以通过 bin packing 减少碎片；GPU sharing 可以让小任务合用一张卡。但每种方法都有代价——bin packing 可能增加故障爆炸半径，GPU sharing 可能有性能干扰。</p>

<h4>6. Fairness（公平性）</h4>
<p>定义：不同用户或团队之间资源分配的均衡程度。常用指标包括 dominant share 的基尼系数、max-min fairness 偏差、SLO violation 率等。</p>
<p>为什么重要：多租户 GPU 集群里，如果只用 throughput 做目标，调度器会偏向"资源效率高"的大团队，小团队的任务可能永远排不上。公平性保证每个团队都能获得合理份额。</p>
<p>面试中怎么用：公平性通常和利用率冲突。面试时要说明"怎么定义公平"比"要不要公平"更重要。是按 GPU 数量公平，还是按 dominant share 公平，还是按配额保障度公平？不同的定义会导致不同的策略。</p>
<p>怎么理解：公平不是均分。团队 A 有 100 个 researcher，团队 B 有 5 个 researcher，均分 50/50 对 B 来说过于慷慨。按人头、按配额、按保障度是三种不同的公平定义。</p>

<h4>7. SLO Violation Rate（服务等级违约率）</h4>
<p>定义：不满足服务等级目标（如延迟 P99 &lt; 200ms、任务 24h 内完成）的请求或任务比例。</p>
<p>为什么重要：在线推理场景下，SLO 是最核心的约束。GPU 调度不能只追求利用率，而要保证推理服务的 tail latency 满足 SLO。</p>
<p>面试中怎么用：如果面试官问"在线推理和离线训练怎么混部"，SLO violation rate 就是衡量混部是否成功的指标。推理的 SLO 是硬约束，训练可以弹性让步。</p>

<h4>8. Preemption Cost（抢占代价）</h4>
<p>定义：抢占一个正在运行的任务所造成的进度损失、重启成本和系统开销。</p>
<p>为什么重要：传统调度论文里抢占就是"杀掉低优先级，运行高优先级"，但在 AI 训练里，一个训练任务被抢占后可能要回滚到数小时前的 checkpoint，重新加载模型和数据，重建 NCCL 通信组。这些代价远大于一个在线服务 Pod 被驱逐后重启。</p>
<p>面试中怎么用：如果你研究的是训练任务调度，抢占代价是你必须要考虑的维度。面试时应该说明"代价基抢占"怎么选择牺牲者——不是简单看优先级，而是看 checkpoint 新鲜度、运行时长、释放资源量和重启成本。</p>
</div>

<div class="card card-d">
<h3>不同场景的指标优先级</h3>
<p>面试中最常问的问题之一就是"这个指标在你的场景里排第几"。没有统一答案，但可以按场景给出典型排序：</p>

<h4>在线推理场景</h4>
<ol>
<li><strong>SLO / Tail Latency</strong>——推理服务的核心承诺</li>
<li><strong>Throughput</strong>——单位时间处理的 token/请求数</li>
<li><strong>GPU Utilization</strong>——但不应牺牲 SLO</li>
<li><strong>Fairness</strong>——多模型之间</li>
</ol>
<p>推理场景不太关心 JCT 和抢占——推理请求是毫秒级，没有 checkpoint 概念。</p>

<h4>离线训练场景</h4>
<ol>
<li><strong>JCT</strong>——用户最关心什么时候出结果</li>
<li><strong>GPU Utilization</strong>——训练成本高，碎片化是浪费</li>
<li><strong>Fairness</strong>——多团队共享时避免饥饿</li>
<li><strong>Preemption Cost</strong>——训练抢占代价大</li>
</ol>
<p>训练场景不太关心单个请求延迟和 SLO。</p>

<h4>实验平台场景</h4>
<ol>
<li><strong>Waiting Time</strong>——实验反馈速度决定研发效率</li>
<li><strong>Fairness</strong>——多个 researcher 共享集群</li>
<li><strong>Utilization</strong>——但不应过度影响反馈速度</li>
</ol>
<p>实验平台的特点是短作业多、交互性强、用户等待容忍度低。</p>

<h4>大模型预训练场景</h4>
<ol>
<li><strong>Stability</strong>——训练一旦开始，尽量不中断</li>
<li><strong>Topology Quality</strong>——通信效率直接影响训练速度</li>
<li><strong>Fault Tolerance</strong>——硬件故障必须快速恢复</li>
<li><strong>Utilization</strong>——但稳定性更重要</li>
</ol>
<p>大模型预训练的特点是时间长（数周到数月）、GPU 多（数百到数千）、中断代价极高。这个场景下，频繁抢占、gang 不满足、拓扑差都是不可接受的。</p>
</div>

<div class="card card-w">
<h3>指标之间的典型冲突</h3>
<p>理解冲突比理解指标本身更重要。面试中如果能说清楚冲突和权衡，比单纯罗列指标更有区分度。</p>

<h4>公平性 vs 利用率</h4>
<p>严格配额可以保证公平，但可能导致某些队列空闲时其他队列不能用。例如团队 A 的 32 张 GPU 配额只用了 10 张，团队 B 的任务在排队，但配额不允许 B 借用 A 的空闲 GPU。解决方式是弹性借用——允许借用，但在保障租户需要时能回收。</p>

<h4>短作业优先 vs 长作业饥饿</h4>
<p>SJF/SRTF 能降低平均 JCT，但长作业可能永远排不上。解决方式是 aging（等待越久优先级越高）或配额保障（每个租户至少获得一定比例的调度机会）。</p>

<h4>拓扑最优 vs 调度延迟</h4>
<p>等待同机柜或同 NVLink 资源可以提升训练性能，但会增加排队时间。如果所有任务都要求"最优拓扑"，大部分时间 GPU 在等完美组合而不是干活。解决方式是设定可接受的拓扑质量阈值，超过阈值就不等了。</p>

<h4>抢占效率 vs 进度损失</h4>
<p>抢占可以快速释放资源给高优先级任务，但训练任务的 checkpoint 可能是 1 小时前的，被抢占意味着 1 小时的计算白费。解决方式是代价基抢占——优先抢占 checkpoint 新鲜、运行时间短的任务。</p>

<h4>装箱 vs 故障域隔离</h4>
<p>Bin packing 降低碎片，但把任务集中到少数节点会增加单节点故障的影响范围。解决方式是按故障域分级——在线服务尽量分散，训练任务可以集中但需要快速恢复机制。</p>
</div>

<div class="card card-d">
<h3>公平性、吞吐量、延迟、资源利用率的 trade-off</h3>
<p>调度系统不可能同时把所有指标都推到最优。面试里最重要的不是说“我都优化”，而是说明你的场景下哪个指标是硬约束、哪个是优化目标、哪个可以让步。</p>
<table>
<tr><th>优化目标</th><th>常用策略</th><th>通常牺牲什么</th><th>适用场景</th><th>风险</th></tr>
<tr><td>公平性</td><td>quota、DRF、CFS-like share、aging</td><td>短期利用率和整体吞吐</td><td>多租户平台、共享 GPU 集群</td><td>严格隔离会让空闲配额不能被借用</td></tr>
<tr><td>吞吐量</td><td>SJF、batching、bin packing、提高并发</td><td>单个任务延迟和长任务公平</td><td>离线批处理、低优训练队列</td><td>短任务偏置导致长任务饥饿</td></tr>
<tr><td>低延迟</td><td>优先级、预留资源、抢占、spread</td><td>资源利用率和吞吐</td><td>在线推理、交互式 notebook、紧急任务</td><td>预留过多会造成 GPU 闲置</td></tr>
<tr><td>高资源利用率</td><td>backfill、bin packing、GPU sharing、超卖</td><td>SLO、故障隔离、公平性</td><td>成本敏感平台、离线混部</td><td>“忙但没产出”，或互相干扰</td></tr>
</table>
<div class="qa-summary">回答模板：先说场景，再定硬约束，然后说明优化目标和牺牲项。例如在线推理把 SLO 当硬约束，训练队列把利用率/JCT 当优化目标，多租户平台把公平性当底线。</div>
</div>

<div class="card card-s">
<h3>在线调度 vs 离线调度</h3>
<p>在线和离线不是“线上服务”和“离线任务”的简单同义词，而是算法是否提前知道完整输入的区别。在线调度只能看到已经到达的任务，必须边到达边决策；离线调度提前知道全部任务、资源和运行时间，可以做全局优化。</p>
<table>
<tr><th>维度</th><th>在线调度 Online Scheduling</th><th>离线调度 Offline Scheduling</th></tr>
<tr><td>信息可见性</td><td>只知道当前和历史任务，不知道未来</td><td>提前知道完整任务集合和约束</td></tr>
<tr><td>决策方式</td><td>每个任务到达时立即或短时间内决策</td><td>可以全局搜索、排序、规划</td></tr>
<tr><td>典型系统</td><td>K8s scheduler、在线推理调度、交互式实验平台</td><td>批处理排程、生产计划、trace replay 仿真</td></tr>
<tr><td>评价重点</td><td>竞争比、延迟、鲁棒性、实时响应</td><td>全局最优性、makespan、平均 JCT</td></tr>
<tr><td>工程难点</td><td>未来不确定、任务时长预测不准、不能频繁反悔</td><td>求解复杂度高，假设可能不符合真实在线环境</td></tr>
</table>
<p>AI 集群大多数实际调度是在线调度，但会吸收离线思想：用历史 trace 训练预测器，用未来资源释放估计做 backfill，用离线仿真评估策略。</p>
</div>

<div class="card card-m">
<h3>面试回答模板</h3>
<p>当面试官问"你怎么衡量调度系统的好坏"，用这个框架回答：</p>
<ol>
<li><strong>先定场景</strong>——推理、训练、实验平台、大模型预训练？不同场景的指标优先级不同。</li>
<li><strong>再说核心指标</strong>——选 2-3 个最重要的，说清楚定义和为什么重要。</li>
<li><strong>然后说冲突</strong>——这些指标之间的矛盾是什么，你怎么权衡。</li>
<li><strong>最后说实验</strong>——你用什么 trace、什么 baseline、什么 workload 证明了你的策略改善了哪些指标。</li>
</ol>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试官问"JCT 和 waiting time 有什么区别"，怎么回答？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">定义区别</div><p>JCT = waiting time + execution time。Waiting time 只衡量排队，JCT 衡量从提交到完成的全部时间。</p></div>
<div class="qa-section"><div class="qa-section-title">策略含义不同</div><p>降低 waiting time 靠排队策略（排序、准入、抢占）。降低 execution time 靠放置策略（拓扑、资源分配、GPU sharing）。降低 JCT 需要两者配合。</p></div>
<div class="qa-section"><div class="qa-section-title">例子</div><p>拓扑感知调度可能不改变 waiting time（甚至可能增加，因为等更好拓扑），但通过减少通信开销降低了 execution time，最终 JCT 反而更低。</p></div>
<div class="qa-summary">面试要点：JCT 是用户视角的全链路指标，waiting time 只反映排队阶段。两者改善手段不同。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 利用率高是不是就说明调度好？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">不一定</div><p>高利用率可能意味着：(1) 确实调度合理，资源被高效使用；(2) 任务都挤在少数节点，牺牲了拓扑和故障隔离；(3) GPU 在做无效计算，例如 NCCL 等待、数据加载瓶颈或 MPS 干扰。</p></div>
<div class="qa-section"><div class="qa-section-title">怎么判断</div><p>看利用率的同时看吞吐、JCT 和 SLO。如果利用率高但吞吐低，说明 GPU 在"忙但没产出"。如果利用率高但 JCT 也在增加，说明调度可能在做过度装箱。</p></div>
<div class="qa-summary">面试要点：利用率是必要条件但不是充分条件。要结合产出指标一起看。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 调度论文里一般报告哪些指标？怎么设计消融实验？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心指标</div><p>离线训练论文通常报告 JCT（平均和中位数）、waiting time、GPU 利用率。多租户论文加上公平性（dominant share 偏差或配额保障度）。在线推理加上 SLO violation rate 和 tail latency。</p></div>
<div class="qa-section"><div class="qa-section-title">消融设计</div><p>每次去掉一个机制，看哪个指标退化了。例如去掉拓扑感知，JCT 可能增加但 waiting time 不变；去掉公平性，小团队的 waiting time 可能急剧增加；去掉抢占，高优先级任务的 waiting time 增加。</p></div>
<div class="qa-section"><div class="qa-section-title">基线选择</div><p>和默认 scheduler 比，和 Volcano/Kueue 比，和同领域论文比。如果只和自己去掉了某些机制的版本比，说服力有限。</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试官问"你的调度器优化了什么指标，牺牲了什么"，怎么回答？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答结构</div><p>(1) 优化了什么：明确说指标名，例如"优化了 P90 JCT，降低了 25%"。(2) 牺牲了什么：例如"在极端负载下，短作业的 waiting time 略有增加，因为我们优先调度 gang 任务"。(3) 为什么可接受：例如"增加的 waiting time 在 5 分钟以内，但 gang 任务的 JCT 改善了 30%，整体集群利用率提高了 15%"。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么这样回答好</div><p>面试官不期望你优化所有指标，但期望你说清楚权衡。能说清楚"牺牲了什么、为什么可接受"比"什么都优化了"更有说服力。</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Makespan 和平均 JCT 有什么区别？优化一个会改善另一个吗？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">定义</div><p>Makespan 是"最后一个任务什么时候完成"，平均 JCT 是"所有任务的平均完成时间"。Makespan 是管理员视角，平均 JCT 是用户视角。</p></div>
<div class="qa-section"><div class="qa-section-title">关系</div><p>优化平均 JCT 通常会让短任务先跑（SJF），但这可能推迟长任务的完成时间，从而增加 makespan。反过来，如果优化 makespan，可能需要所有任务并行跑，但这会增加资源竞争和通信开销，单个任务的 JCT 不一定改善。</p></div>
<div class="qa-section"><div class="qa-section-title">什么时候用哪个</div><p>批处理和数据 Pipeline 关心 makespan；交互式训练和实验平台关心平均 JCT；多租户平台还要看公平性。</p></div>
</div>
</div>

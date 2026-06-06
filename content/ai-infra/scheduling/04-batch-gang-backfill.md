<div class="card card-m">
<h3>批调度：训练任务和普通在线服务的分水岭</h3>
<p>分布式训练、HPC 和大规模批任务通常不是单 Pod 独立运行，而是一组进程共同完成一个 job。批调度关注的不只是单个 Pod 能否放下，还包括一组 Pod 是否能同时启动、是否会造成资源碎片、是否会让大作业长期排队。</p>
<p>为什么批调度是 GPU 集群独有的问题？因为在线服务的每个 Pod 是独立的——挂一个副本不影响其他副本。但分布式训练的所有 worker 是一个整体——少一个 worker，NCCL AllReduce 就会阻塞，所有 GPU 空转。这种 all-or-nothing 的语义是批调度的核心。</p>
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
</div>

<div class="card card-d">
<h3>Backfill Scheduling 详解</h3>
<p>Gang Scheduling 解决了"不该启动的部分 Pod"问题，但引入了新问题：大 gang 在等待时，集群可能有碎片资源在空转。Backfill 的思路就是：能不能让小任务"见缝插针"，利用大 gang 等待期间的碎片资源？</p>

<h4>Backfill 的核心前提</h4>
<p>Backfill 需要知道两件事：(1) 大作业什么时候能启动（需要预测已有任务的完成时间）；(2) 小作业能不能在大作业启动前跑完（需要预测小作业的运行时间）。两个预测都有误差，这是 backfill 的根本风险。</p>

<h4>三种 Backfill 策略</h4>

<p><strong>1. Conservative Backfill</strong></p>
<p>给所有等待作业保留预计启动时间。小作业 backfill 的前提是：不影响任何等待作业的预计启动时间。</p>
<p><strong>手动推演</strong>：集群有 4 张 GPU。Job A（需要 4 GPU，预计运行 10 小时）正在运行。Job B（需要 4 GPU，预计运行 5 小时）在排队。Job C（需要 1 GPU，预计运行 2 小时）也想排队。</p>
<ul>
<li>Job A 预计 10 小时后完成，之后 Job B 可以启动。</li>
<li>Job C 需要 1 GPU，但如果现在给 C 分配 1 GPU，A 只剩 3 GPU，可能影响 A 的完成时间。</li>
<li>Conservative：如果 A 用了全部 4 GPU，C 不能 backfill（没有空闲 GPU）。如果 A 只用了 3 GPU，C 可以 backfill，前提是 C 在 A 预计完成前能跑完。</li>
</ul>
<p><strong>优点</strong>：公平性最强，任何已有预约都不会被打破。</p>
<p><strong>缺点</strong>：太保守，利用率提升有限。</p>

<p><strong>2. EASY Backfill（Extensible Argonne Scheduling System）</strong></p>
<p>只保护队首作业的预计启动时间，其他排队作业不保证。小作业只要不影响队首大作业，就可以 backfill。</p>
<p><strong>手动推演</strong>：同上场景。Job B 是队首，预计 10 小时后启动。Job C 需要 1 GPU，2 小时跑完。只要 C 在 10 小时内完成（2 < 10），就可以 backfill。</p>
<p><strong>优点</strong>：实现简单，利用率比 Conservative 高。</p>
<p><strong>缺点</strong>：只保护队首，后面的排队作业可能被推迟。如果有 Job D 排在 Job B 后面，D 的启动时间不保证。</p>

<p><strong>3. Prediction-aware Backfill</strong></p>
<p>依赖运行时间预测来判断小作业能否在"窗口"内完成。预测越准确，backfill 效果越好。</p>
<p><strong>预测方法</strong>：</p>
<ul>
<li><strong>用户声明</strong>：用户提交时填写预计运行时间。简单但不准，用户倾向于高估。</li>
<li><strong>历史统计</strong>：根据同类任务的历史运行时间预测。比用户声明准，但冷启动问题。</li>
<li><strong>在线学习</strong>：根据任务已运行的时间和进度预测剩余时间。最准但最复杂。</li>
</ul>
<p><strong>核心风险</strong>：预测不准。如果小作业没有按时完成，会推迟大作业启动，破坏公平性和用户预期。</p>
<p><strong>缓解措施</strong>：(1) 设安全系数——预测时间乘以 1.2-1.5 倍；(2) 设 backfill 截止——到期未完成则强制终止；(3) 优先级倒挂——backfill 任务优先级低于正常任务，到期可被抢占。</p>

<h4>Backfill 的面试回答框架</h4>
<ol>
<li><strong>问题是什么</strong>：大 gang 等待期间碎片资源空转。</li>
<li><strong>解决思路</strong>：让小任务"见缝插针"，但要不推迟大任务启动。</li>
<li><strong>三种策略</strong>：Conservative（全保护）、EASY（只保队首）、Prediction-aware（基于预测）。</li>
<li><strong>核心风险</strong>：运行时间预测不准，导致大任务被推迟。</li>
<li><strong>在 GPU 集群中的特殊考虑</strong>：GPU 任务通常是独占整卡，不像 CPU 可以留一点余量，所以 backfill 窗口更难找。GPU sharing（MPS/time-slicing）可以创造 backfill 机会。</li>
</ol>
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
<p><code>preemption_score(victim) = release_value(victim) / (checkpoint_age(victim) + restart_cost(victim))</code></p>
<p>选择 preemption_score 最高的牺牲者。直觉：释放资源量越大越好，回滚损失和重启成本越小越好。</p>
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

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试官问"你怎么设计训练任务的抢占策略"，怎么回答？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答框架</div>
<ol>
<li><strong>先说为什么训练抢占和普通 Pod 抢占不同</strong>：训练抢占有沉没成本（进度损失）、重启成本（模型加载+NCCL 重建）、拓扑成本（好的位置被让出来了）。</li>
<li><strong>再说代价感知抢占</strong>：不是简单看优先级，而是看 release_value / (checkpoint_age + restart_cost)。选这个比值最高的牺牲者。</li>
<li><strong>然后说优雅抢占</strong>：给任务优雅期做 checkpoint，超时后强制终止。</li>
<li><strong>最后说弹性训练</strong>：如果任务支持弹性，可以缩减 world size 而不是杀掉，释放部分 GPU 但训练继续。</li>
</ol>
</div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"训练任务的抢占不是简单的优先级排序，而是代价优化问题。好的抢占策略选择'最值得杀'的牺牲者——释放资源多、进度损失少、重启成本低。"</p></div>
</div>
</div>

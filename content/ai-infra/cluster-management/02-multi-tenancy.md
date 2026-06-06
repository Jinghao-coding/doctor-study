<div class="card card-m">
<h3>多租户管理：为什么"配额"不是简单地"分一下 GPU"？</h3>
<p>多租户管理的本质问题是：<strong>如何在保证每个租户基本权益的前提下，最大化集群利用率？</strong></p>
<p>最简单的方案是"固定配额"——A 团队分 40 张 GPU，B 团队分 60 张 GPU，互不干扰。问题是：A 团队晚上不用 GPU，B 团队晚上要跑实验，但 B 不能用 A 闲置的 GPU——因为"那是 A 的配额"。结果集群利用率只有 40%。</p>
<p>所以多租户管理的核心矛盾是：<strong>保障性（guarantee）vs 弹性（elasticity）</strong>。保障性强 → 利用率低；弹性强 → 可能损害保障。所有配额方案都在这个光谱上找平衡。</p>
<p><strong>怎么理解</strong>：像公司停车位。固定配额 = 每人一个固定车位，你的车位空着别人也不能停。弹性配额 = 每人有保底车位（来了肯定有位），但空着时别人可以临时用，你来了别人得让出来。</p>
</div>

<div class="card card-s">
<h3>四种配额方案详解</h3>

<h4>1. 固定配额（Static Quota）</h4>
<p><strong>定义</strong>：每个租户分配固定的 GPU 数量，互不借用。K8S 原生的 ResourceQuota 就是这种模型。</p>
<p><strong>怎么理解</strong>：买断制——你买了 40 张 GPU，不用也归你，别人不能用。</p>
<p><strong>优点</strong>：(1) 强保障——你的 GPU 永远不会被别人抢走；(2) 实现最简单——ResourceQuota + Namespace 隔离就够了。</p>
<p><strong>致命问题</strong>：利用率低。实测数据：固定配额的 GPU 集群平均利用率通常只有 30-40%，因为总有租户的配额闲置（夜间、周末、实验间隙）。</p>
<p><strong>面试中怎么答</strong>：不要说"固定配额不好"——要说"固定配额在什么场景下够用"：小型团队（GPU 少，每个租户都满载）、合规要求严格（不能混用资源的场景）。问题在于规模大了之后利用率不可接受。</p>

<h4>2. ElasticQuota（弹性配额）</h4>
<p><strong>定义</strong>：每个租户有 <code>min</code>（保障量）和 <code>max</code>（上限）。日常使用 min 以内的资源有保障；闲置时可以借用其他租户的 min 值，但总量不超过 max；被借用方需要时可以抢占回收。</p>
<p><strong>怎么理解</strong>：信用卡 + 信用额度——你有 5 万信用额度（min = 5 万保障），最多可以刷 10 万（max = 10 万上限），但超出 5 万的部分银行随时可以收回。</p>
<p><strong>手动推演</strong>：100 GPU 集群，A 团队 min=30/max=60，B 团队 min=40/max=80</p>
<ul>
<li>T1：A 用 30，B 用 40，剩 30 闲置 → A 可以借用，用 60（到 max）</li>
<li>T2：B 要用 70 → A 借用了 30 中的 30 需要让出 → 抢占 A 的 30 GPU → A 回到 30（min），B 用 70</li>
<li>T3：B 只用 40 → 剩 60 闲置 → A 又可以借用，用 60</li>
</ul>
<p><strong>关键机制：抢占回收</strong>。当 min 拥有者需要资源但被借用者占用时，借用者的 Pod 会被抢占。抢占策略影响很大——简单的优先级抢占可能杀掉一个训练了 10 小时的任务。</p>
<p><strong>局限</strong>：(1) min/max 是静态值，不能动态调整；(2) 抢占不考虑沉没成本；(3) 没有"保障度"的概念——min 只是名义保障，实际保障度取决于抢占的及时性。</p>

<h4>3. 弹性保障（QAD 驱动）</h4>
<p><strong>定义</strong>：不设 max 上限，借用不受限，但通过 QAD（Quota Assurance Degree，配额保障度）来持续监控和保障每个租户的权益。</p>
<p><strong>QAD 是什么</strong>：QAD = 实际获得资源时间 / 应获得资源时间。例如一个租户的 guarantee 是 30 GPU，过去 24 小时内他需要 30 GPU 的总时间是 20 小时，其中 18 小时确实获得了 30 GPU，则 QAD = 18/20 = 0.9。</p>
<p><strong>怎么理解 QAD</strong>：像手机电池健康度。你的电池设计容量是 100%，实际充满只有 90%，电池健康度就是 90%。QAD 就是"配额健康度"——你的保障配额有多少时间是真正可用的。</p>
<p><strong>为什么比 ElasticQuota 更好</strong>：</p>
<ul>
<li><strong>无 max 限制</strong>：借用没有硬上限，利用率更高。只要 QAD 不降低，你借多少都行。</li>
<li><strong>信号更精细</strong>：ElasticQuota 只有"在 min 内 / 超出 min"两个状态。QAD 是连续值（0.0-1.0），能做更精细的调度决策——QAD=0.95 的队列和 QAD=0.6 的队列，优先级显然不同。</li>
<li><strong>驱动回收</strong>：当某个租户的 QAD 低于阈值（如 0.95），调度器优先从借用者回收资源，而不是等到租户主动请求。</li>
</ul>
<p><strong>手动推演</strong>：100 GPU，A 团队 guarantee=30，B 团队 guarantee=40</p>
<ul>
<li>T1：A 用 30，B 用 40，剩 30 闲置 → A 借用 30，A 总共 60 GPU</li>
<li>T2：A 的 QAD = 1.0（一直在 30 以上），B 的 QAD = 1.0 → 一切正常</li>
<li>T3：B 需要用 60 但只有 40（A 借了 30）→ 调度器检测到 B 的 QAD 可能降到 0.67 → 触发回收 A 的 20 GPU → A 回到 40，B 获得 60</li>
<li>关键：A 不一定要退回 guarantee=30，只要 B 的需求被满足就行。A 保留了 40（比 guarantee 多 10），B 获得了 60（比 guarantee 多 20）。总量 100 刚好用满。</li>
</ul>
<p><strong>面试金句</strong>："ElasticQuota 是离散的保障信号——要么在 min 内要么超出。QAD 是连续的保障信号——像监控'配额健康度'一样持续度量保障水平，驱动更精细的调度决策。"</p>

<h4>4. DRF（主导资源公平）</h4>
<p><strong>定义</strong>：多维资源场景下的公平分配。每个租户的"主导资源"（占集群该资源比例最高的那个维度）获得相等份额。详见调度理论模块的 DRF 章节。</p>
<p><strong>在多租户中的角色</strong>：DRF 解决的是公平性，不是保障性。它没有 min/max 的概念，只是确保每个租户的"最大需求维度"被公平对待。适合无保障要求的共享集群。</p>
</div>

<div class="card card-d">
<h3>配额方案对比</h3>
<table>
<tr><th>维度</th><th>固定配额</th><th>ElasticQuota</th><th>QAD 驱动</th><th>DRF</th></tr>
<tr><td>保障性</td><td>强（100%）</td><td>中（min 保障，抢占可能延迟）</td><td>强（QAD ≥ 0.95）</td><td>弱（无保障承诺）</td></tr>
<tr><td>弹性</td><td>无</td><td>中（max 上限）</td><td>强（无上限借用）</td><td>中（按比例分配）</td></tr>
<tr><td>回收机制</td><td>不需要</td><td>抢占（简单优先级）</td><td>QAD 驱动回收（更精细）</td><td>不需要</td></tr>
<tr><td>公平度量</td><td>—</td><td>—</td><td>QAD 连续值</td><td>Dominant Share</td></tr>
<tr><td>利用率</td><td>低（30-40%）</td><td>中（60-70%）</td><td>高（80%+）</td><td>中高</td></tr>
<tr><td>实现复杂度</td><td>低</td><td>中</td><td>高</td><td>中</td></tr>
<tr><td>适用规模</td><td>小</td><td>中</td><td>大</td><td>共享研究集群</td></tr>
</table>
</div>

<div class="card card-w">
<h3>多租户隔离的四个层次</h3>
<p>配额管理解决的是"每个租户能用多少"，隔离解决的是"租户之间互相不影响"。隔离有四个层次，从粗到细：</p>

<h4>第一层：Namespace 级别</h4>
<p><strong>机制</strong>：K8S 原生的 ResourceQuota + LimitRange。</p>
<p><strong>ResourceQuota</strong>：限制一个 Namespace 的总资源量（如最多 16 GPU）。硬限制，超了 Pod 创建直接被拒绝。</p>
<p><strong>LimitRange</strong>：限制单个 Pod 的资源范围（如每个 Pod 最多 4 GPU，最少 1 GPU）。防止一个 Pod 吃掉整个 Namespace 的配额。</p>
<p><strong>隔离能力</strong>：资源量隔离。不同 Namespace 的资源预算独立。</p>
<p><strong>局限</strong>：(1) 不支持弹性——ResourceQuota 是硬限制，空闲资源不能被其他 Namespace 用；(2) 不做性能隔离——同一节点上两个 Namespace 的 Pod 可能互相干扰。</p>
<p><strong>怎么理解</strong>：公司报销制度——每个部门有固定报销额度（ResourceQuota），单次报销有上下限（LimitRange），但额度用不完不能转给其他部门。</p>

<h4>第二层：Queue 级别</h4>
<p><strong>机制</strong>：Volcano Queue / Kueue ClusterQueue / Yunikorn Queue。</p>
<p><strong>增强能力</strong>：(1) 弹性配额——支持 borrowing 和 reclaim；(2) 公平调度——Queue 内部可以按 DRF/proportion 调度；(3) 优先级——不同 Queue 可以有不同优先级；(4) 排队——配额不足时任务排队等待，而不是直接拒绝。</p>
<p><strong>为什么比 Namespace 更好</strong>：ResourceQuota 是"硬墙"——超了就拒绝。Queue 是"弹性门"——超了可以借用，还可以排队等。后者更适合 GPU 集群的动态负载。</p>

<h4>第三层：节点级别</h4>
<p><strong>机制</strong>：NodeSelector / NodeAffinity / Taint-Toleration。</p>
<p><strong>做法</strong>：把特定节点（或节点组）专属于特定租户。例如给 A 团队的节点打上 <code>tenant=A:NoSchedule</code> taint，只有带 A 团队 toleration 的 Pod 才能调度上去。</p>
<p><strong>为什么需要</strong>：(1) <strong>合规要求</strong>：某些数据只能在特定机器上处理；(2) <strong>性能隔离</strong>：训练任务独占节点，避免推理任务的延迟抖动；(3) <strong>硬件差异</strong>：A 团队的模型需要 A100，B 团队 V100 就够了。</p>
<p><strong>局限</strong>：降低利用率——专属于某个租户的节点即使闲置，其他租户也不能用。</p>

<h4>第四层：GPU 级别</h4>
<p><strong>机制</strong>：MIG（Multi-Instance GPU）硬件切片 / MPS（Multi-Process Service）软件共享。</p>
<p><strong>MIG</strong>：A100/H100 支持将一张 GPU 硬件切分为最多 7 个实例，每个实例有独立的 SM、L2 cache、显存带宽。硬件级隔离——一个实例的故障和性能波动不影响其他实例。</p>
<p><strong>MPS</strong>：软件层面的 GPU 共享，多个进程共享同一 GPU 的 SM。轻量级，但没有硬件隔离——一个进程的 kernel 可能影响其他进程的延迟。</p>
<p><strong>怎么理解</strong>：MIG 像"合租公寓的独立房间"——各有各的卧室和卫生间。MPS 像"合租公寓的公共空间"——共享客厅和厨房，一人做饭另一人可能要等。</p>
<p><strong>选择建议</strong>：</p>
<table>
<tr><th>场景</th><th>推荐</th><th>原因</th></tr>
<tr><td>训练任务（需要强隔离）</td><td>MIG 或独占</td><td>性能波动不可接受</td></tr>
<tr><td>轻量推理（延迟不敏感）</td><td>MPS</td><td>利用率高，隔离要求低</td></tr>
<tr><td>数据预处理 + 训练混跑</td><td>MPS</td><td>预处理是 I/O 密集，GPU 利用率低，可以和训练共享</td></tr>
<tr><td>合规要求（数据不能混）</td><td>MIG</td><td>硬件级隔离满足合规</td></tr>
</table>
</div>

<div class="card card-m">
<h3>多租户管理面试问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ElasticQuota 的抢占有什么问题？怎么改进？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>ElasticQuota 的抢占是简单的优先级抢占——当 guarantee 拥有者需要资源时，驱逐借用者中优先级最低的 Pod。三个问题：</p>
<ol>
<li><strong>不考虑沉没成本</strong>：一个训练了 20 小时的任务和一个刚启动 5 分钟的任务，如果优先级相同，可能抢占前者。前者的进度损失远大于后者。</li>
<li><strong>抢占延迟</strong>：从触发抢占到实际释放资源可能需要几分钟（优雅终止期 + checkpoint + 资源清理），在此期间 guarantee 拥有者一直在等。</li>
<li><strong>级联抢占</strong>：抢占 A 的资源可能不够，还需要抢占 B 的，B 又依赖 C 释放的节点……级联效应导致调度不可预测。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">改进方向</div><p>(1) <strong>代价感知抢占</strong>：优先抢占沉没成本低的任务（运行时间短、checkpoint 新鲜）。参见调度理论模块的 checkpoint-aware preemption。(2) <strong>预回收</strong>：基于 QAD 信号，在 QAD 接近阈值时提前触发回收，而不是等到 guarantee 拥有者来请求时才抢占。(3) <strong>优雅终止</strong>：通知借用者"请 checkpoint 后退出"，给 5 分钟优雅期，而不是直接杀 Pod。(4) <strong>弹性缩容</strong>：如果任务支持弹性训练，缩减 world size 而非杀掉整个任务。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"抢占不是免费的——它有沉没成本、延迟和级联效应。好的配额系统应该让抢占尽量少发生、尽量低代价、尽量可预测。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何设计一个支持 10 个团队共享 200 GPU 的配额系统？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">回答框架（5 步）</div><p>(1) <strong>配额模型</strong>：选择 ElasticQuota（min/max）或 QAD 驱动。10 个团队 + 200 GPU 规模下，ElasticQuota 可以工作，但 QAD 驱动利用率更高。建议 QAD 驱动 + guarantee 保障。</p>
<p>(2) <strong>保障量分配</strong>：根据团队历史使用量和业务优先级分配 guarantee。例如核心训练团队 guarantee=40，实验团队 guarantee=10。总和应 ≤ 集群总量（200），保证不超卖。</p>
<p>(3) <strong>借用和回收</strong>：借用无上限（或设安全上限），回收由 QAD 驱动——任何团队 QAD < 0.95 时触发回收。回收策略用代价感知抢占。</p>
<p>(4) <strong>隔离层次</strong>：Namespace 级别（ResourceQuota 兜底）+ Queue 级别（Volcano/Kueue 管理）+ 节点级别（大团队专属节点组）。</p>
<p>(5) <strong>监控</strong>：实时 QAD 看板、借用/回收日志、每团队利用率趋势。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"配额系统设计的关键不是选哪个模型，而是说清楚 guarantee 怎么定、借用怎么管、回收怎么触发、代价怎么控制。这四个问题回答清楚了，配额系统就立住了。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MIG 和 MPS 的区别？什么场景用哪个？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><table>
<tr><th>维度</th><th>MIG</th><th>MPS</th></tr>
<tr><td>隔离级别</td><td>硬件（独立 SM、L2、显存带宽）</td><td>软件（共享 SM，MPS server 调度）</td></tr>
<tr><td>实例数</td><td>最多 7 个（A100）</td><td>无硬限制</td></tr>
<tr><td>性能隔离</td><td>强——一个实例不影响其他</td><td>弱——一个进程的 kernel 可能阻塞其他</td></tr>
<tr><td>故障隔离</td><td>强——一个实例故障不影响其他</td><td>弱——一个进程崩溃可能影响 MPS server</td></tr>
<tr><td>利用率</td><td>中（静态切分，可能浪费）</td><td>高（动态共享）</td></tr>
<tr><td>灵活性</td><td>低（切分比例预设，运行中不能调）</td><td>高（随时加/减共享进程）</td></tr>
<tr><td>GPU 型号</td><td>A100/H100</td><td>大部分 NVIDIA GPU</td></tr>
</table></div>
<div class="qa-section"><div class="qa-section-title">场景推荐</div><p>(1) <strong>训练 + 训练共享</strong> → MIG。训练任务对性能波动敏感，需要硬件隔离。(2) <strong>推理 + 推理共享</strong> → MPS。推理任务可以利用 MPS 的高利用率。(3) <strong>训练 + 数据预处理</strong> → MPS。预处理是 I/O 密集，GPU 空闲时间多，MPS 让训练利用这些空闲。(4) <strong>合规/多租户隔离</strong> → MIG。硬件隔离满足合规要求。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"MIG 用硬件换隔离，MPS 用共享换利用率。选择取决于你对性能确定性的要求——训练需要确定性，推理更看重利用率。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 多租户场景下如何防止"吵闹的邻居"？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>"吵闹的邻居"（Noisy Neighbor）指同一物理资源上，一个租户的高负载影响其他租户的性能。在 GPU 集群中主要表现为：</p>
<ol>
<li><strong>共享节点上的 GPU 争抢</strong>：MPS 共享时，一个大 kernel 占满 SM，其他进程排队。</li>
<li><strong>网络带宽争抢</strong>：训练任务的 AllReduce 占满 InfiniBand 带宽，推理任务的网络延迟飙升。</li>
<li><strong>存储 I/O 争抢</strong>：checkpoint 写入占满存储带宽，其他任务的数据加载变慢。</li>
</ol></div>
<div class="qa-section"><div class="qa-section-title">解决策略</div><p>(1) <strong>隔离</strong>：节点级隔离（不同租户不同节点）或 GPU 级隔离（MIG 硬件切分）。这是最彻底但最浪费资源的方案。(2) <strong>干扰感知调度</strong>：调度器感知任务间的性能干扰，避免把"吵闹"的任务和"敏感"的任务放一起。需要性能模型来预测干扰程度。(3) <strong>资源限流</strong>：对 GPU 使用率、网络带宽、存储 I/O 设置 cgroup 限制，防止单个租户占满共享资源。(4) <strong>监控 + 自动迁移</strong>：检测到干扰时，自动将"受害者"迁移到其他节点。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"吵闹邻居的本质是共享资源的争抢。解决路径从粗到细：隔离（不共享）→ 干扰感知（有选择地共享）→ 限流（共享但约束）→ 监控（出问题再处理）。"</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Namespace 隔离和 Queue 隔离有什么区别？什么时候用哪个？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心回答</div><p>Namespace 隔离是 K8S 原生的"硬墙"——ResourceQuota 限制总量，超了直接拒绝。Queue 隔离是批调度框架的"弹性门"——配额不足时排队等待或借用，而不是直接拒绝。</p></div>
<div class="qa-section"><div class="qa-section-title">关键区别</div><table>
<tr><th>维度</th><th>Namespace + ResourceQuota</th><th>Queue</th></tr>
<tr><td>超配额行为</td><td>直接拒绝 Pod 创建</td><td>排队等待或借用</td></tr>
<tr><td>弹性</td><td>无（硬限制）</td><td>有（borrowing/reclaim）</td></tr>
<tr><td>公平性</td><td>无调度公平性</td><td>DRF/proportion 公平调度</td></tr>
<tr><td>Gang 支持</td><td>不支持</td><td>支持（PodGroup/Workload）</td></tr>
<tr><td>多维度资源</td><td>支持（CPU/GPU/内存各自限制）</td><td>支持（且更灵活）</td></tr>
</table></div>
<div class="qa-section"><div class="qa-section-title">什么时候用哪个</div><p>(1) <strong>只用 Namespace</strong>：微服务场景，没有 Gang 需求，每个 Namespace 的负载相对稳定。(2) <strong>只用 Queue</strong>：训练场景，需要 Gang + 弹性配额 + 公平调度。(3) <strong>两者结合</strong>（推荐）：Namespace 做身份隔离和 RBAC（谁能访问什么），Queue 做资源治理和调度。Namespace 是"权限边界"，Queue 是"资源边界"。</p></div>
<div class="qa-section"><div class="qa-section-title">面试金句</div><p>"Namespace 解决'谁能做什么'（权限），Queue 解决'能用多少资源'（调度）。它们不是替代关系，而是互补——Namespace 做安全边界，Queue 做弹性治理。"</p></div>
</div>
</div>
</div>

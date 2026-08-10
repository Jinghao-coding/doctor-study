## 核心调度链路

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: kube-scheduler 的完整调度流程是什么？</div>
<div class="qa-a">
<div class="qa-summary">Pod 从 SchedulingQueue 出队后，经过 PreFilter、Filter、PostFilter、PreScore、Score、Reserve、Permit、PreBind、Bind 和 PostBind；前半段选节点，后半段提交绑定。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Scheduler 基于 Cache Snapshot 计算可行节点，Filter 排除节点，Score 排序；选定节点后先在 Cache 中 Assume，Reserve 维护插件状态，Permit 可等待 Gang 条件，最后异步执行绑定周期。失败时 Forget Assume 并按原因进入 BackoffQ 或 UnschedulablePods。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>Scheduler 只选择 Node，不创建容器；具体设备 ID 在传统 Device Plugin 路径中通常由 kubelet 侧分配。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 一次调度为什么拆成 Scheduling Cycle 和 Binding Cycle？</div>
<div class="qa-a">
<div class="qa-summary">Scheduling Cycle 计算“选哪个 Node”，Binding Cycle 把决定提交给集群；前者串行执行，后者可并发，从而既避免选点阶段互相踩状态，又把较慢的绑定 I/O 移出串行热路径。</div>
<div class="qa-section"><div class="qa-section-title">Scheduling Cycle</div><p>从队列取一个 Pod，读取 Cache Snapshot，经 PreFilter/Filter/Score 选出候选 Node，再进行 Assume、Reserve 和 Permit。调度周期按 Pod 串行运行，配合 Assumed Pod 让下一次选点能看到尚未完成 Bind 的资源占用。</p></div>
<div class="qa-section"><div class="qa-section-title">Binding Cycle</div><p>执行等待 Permit、PreBind、Bind 和 PostBind，把选点结果真正写入 API Server。绑定可能涉及 API 请求或外部插件，允许多个 Pod 的 binding cycle 并发可隐藏这些延迟、提高吞吐。</p></div>
<div class="qa-section"><div class="qa-section-title">失败边界</div><p>任一周期失败，Pod 都会按原因返回调度队列；进入 reserved 状态后失败还要按逆序执行 Unreserve，并清理 Assumed Pod。阶段拆分提升吞吐，不代表可以忽略回滚和 Cache 一致性。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: PreFilter → Filter → PostFilter → PreScore → Score → Reserve → Permit → PreBind → Bind 各自负责什么？</div>
<div class="qa-a">
<table>
<tr><th>扩展点</th><th>职责</th><th>调用粒度/边界</th></tr>
<tr><td>PreFilter</td><td>预计算 Pod 级状态，或提前判定整个周期不可调度</td><td>每个 Pod 一次，结果可写 CycleState</td></tr>
<tr><td>Filter</td><td>检查单个 Node 是否满足硬约束</td><td>每个候选 Node，可并行</td></tr>
<tr><td>PostFilter</td><td>无可行 Node 后执行补救，例如默认抢占</td><td>不是普通 Filter 之后必经的“再过滤”</td></tr>
<tr><td>PreScore</td><td>为打分预计算全局或 Pod 级数据</td><td>每个 Pod 一次</td></tr>
<tr><td>Score</td><td>对每个可行 Node 给偏好分</td><td>每个可行 Node；插件可再 NormalizeScore</td></tr>
<tr><td>Reserve</td><td>节点选定后通知有状态插件维护临时账本</td><td>不是写 Node 对象或保证物理资源已交付</td></tr>
<tr><td>Permit</td><td>批准、拒绝或限时等待绑定</td><td>常用于 Gang/配额等协调</td></tr>
<tr><td>PreBind</td><td>绑定前完成必须成功的准备动作</td><td>失败会阻止 Bind 并触发回滚</td></tr>
<tr><td>Bind</td><td>提交 Pod→Node 绑定</td><td>某个 Bind 插件成功即结束该扩展点；常用 DefaultBinder</td></tr>
</table>
<div class="qa-summary">硬约束放 Filter，偏好放 Score，状态占用放 Reserve/Unreserve，跨 Pod 等待放 Permit，提交前置动作放 PreBind；不要把远程慢调用塞进每节点 Filter/Score 热路径。</div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Reserve 成功后 Permit、PreBind 或 Bind 失败，如何回滚？</div>
<div class="qa-a">
<div class="qa-summary">Framework 会调用所有已执行 Reserve 插件的 <code>Unreserve</code>，顺序与 Reserve 相反；Scheduler 还要 Forget Assumed Pod，再把 Pod 重新入队。</div>
<div class="qa-section"><div class="qa-section-title">插件责任</div><p><code>Unreserve</code> 只清理由该插件维护的临时状态，例如 GPU 拓扑账本、外部 reservation 或 gang 占位。它必须幂等且不能返回错误，因为 Reserve 自身失败、Permit deny/timeout、PreBind/Bind 失败都可能触发它。</p></div>
<div class="qa-section"><div class="qa-section-title">Scheduler 责任</div><p>清理 Cache 中的 Assume，避免后续 Pod 看到幽灵占用；失败 Pod 根据错误与退避策略回到 BackoffQ/UnschedulablePods。若插件创建了外部资源，还必须用稳定 ID 处理超时后“请求其实已成功”的不确定性。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Filter 和 Score 分别解决什么问题？常见插件有哪些？</div>
<div class="qa-a">
<div class="qa-summary">Filter 判断节点能不能放，Score 判断可行节点中放哪里更好。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>常见 Filter 包括 NodeResourcesFit、TaintToleration、NodeAffinity、VolumeBinding 和 PodTopologySpread；Score 可使用 NodeResourcesFit、ImageLocality、InterPodAffinity、PodTopologySpread 等。Filter 返回不可行原因，Score 结果归一化后按权重汇总。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>硬约束应进入 Filter，偏好进入 Score；把硬约束只写成低分可能仍把 Pod 放到错误节点。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 多个 Score 插件的分数如何归一化和加权？</div>
<div class="qa-a">
<div class="qa-summary">每个 Score 插件先产生自己节点分数，可选用 NormalizeScore 在插件内部统一尺度；Scheduler 再把各插件分数乘配置权重并求和，最高总分节点胜出。</div>
<div class="qa-section"><div class="qa-section-title">计算</div><p>可理解为 <code>total(node) = Σ normalizedScore(plugin, node) × weight(plugin)</code>。NormalizeScore 是单插件跨候选节点的后处理，不是把所有插件混在一起归一化；插件返回值仍须落在 Framework 允许的分数范围。</p></div>
<div class="qa-section"><div class="qa-section-title">权衡</div><p>权重表达策略优先级，但不能把硬约束“加很大权重”代替 Filter。调权前要看各插件分数分布：如果一个插件几乎总是 0/100，可能压过数个变化平缓的插件；自定义插件应记录原始分、归一化分和最终加权贡献。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Scheduler Cache、Snapshot 和 API Server 状态有什么区别？</div>
<div class="qa-a">
<div class="qa-summary">API Server 是持久化事实来源；Scheduler Cache 是事件驱动的内存视图；Snapshot 是一个调度周期使用的只读一致视图。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Informer 持续更新 Cache，调度前把 NodeInfo 复制或增量更新到 Snapshot，避免在遍历节点时被并发事件改变。Cache 还保存 Assumed Pod，因此它可能短暂领先于 API Server；失败或超时后必须 Forget，避免幽灵占用。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>Cache 不是新的 source of truth，它允许短暂不一致，但要靠事件和过期机制收敛。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么需要 Assumed Pod？</div>
<div class="qa-a">
<div class="qa-summary">因为 Bind API 有延迟，Scheduler 先在本地假设资源已占用，才能继续调度下一个 Pod 而不重复分配同一份资源。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>选定节点后 Cache 立即扣减资源，再异步执行 Reserve、Permit 和 Bind。绑定成功后真实 Pod 事件确认状态；失败则执行 Unreserve 和 Forget。它用乐观并发提高吞吐，但要求完整回滚。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>Assume 卡住会表现为 Scheduler 认为资源不足，但 Node Status 看起来还有容量，应检查绑定错误和 assumed pod 过期。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Assume 成功但 Bind 失败，或者 Scheduler 随后崩溃，会发生什么？</div>
<div class="qa-a">
<div class="qa-summary">Assume 只是当前 Scheduler 进程的乐观 Cache 状态，不是 API 持久化；明确 Bind 失败会 Unreserve + Forget + 重试，进程崩溃后新实例从 API 对象重建 Cache。</div>
<div class="qa-section"><div class="qa-section-title">Bind 明确失败</div><p>绑定周期失败时先回滚 Reserve 插件，再从 Cache Forget Assumed Pod，记录调度错误并把 Pod 退避重试。否则本地 Cache 会长期虚假扣减节点资源。</p></div>
<div class="qa-section"><div class="qa-section-title">Scheduler 崩溃</div><p>内存中的 Assume 随进程消失。新 leader List/Watch API Server：若 Bind 未成功，Pod 仍无 <code>spec.nodeName</code>，会重新入队；若 Bind 已成功但旧 Scheduler 只是在响应返回前崩溃，API 中已有绑定，新实例按已调度 Pod 处理，不会重新选点。</p></div>
<div class="qa-section"><div class="qa-section-title">超时边界</div><p>网络超时代表结果未知，不能把它简单等同于失败；需要重新读取 Pod 当前状态。Assume + API 对象的 UID/resourceVersion 校验让这套乐观流程最终收敛，但不提供跨外部系统的事务。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ActiveQ、BackoffQ 和 UnschedulablePods 分别是什么？</div>
<div class="qa-a">
<div class="qa-summary">ActiveQ 存等待调度的 Pod；BackoffQ 存失败后等待退避的 Pod；UnschedulablePods 按失败原因等待相关集群事件触发重试。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>新 Pod 进入 ActiveQ；调度错误通常进入指数退避；确实无可行节点的 Pod 进入 UnschedulablePods。Node、PVC、Pod 等事件通过 QueueingHint 判断是否可能解决原失败原因，避免所有 Pending Pod 被无差别唤醒。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>Resync 或任意事件都全量重试会造成惊群和无效调度。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么事件会让不可调度 Pod 重新入队？QueueingHint 解决了什么？</div>
<div class="qa-a">
<div class="qa-summary">只有可能改变原失败原因的已注册集群事件才应唤醒 Pod；QueueingHint 结合具体 Pod 与对象的新旧值判断该变化是否值得重试，减少大队列被无差别激活。</div>
<div class="qa-section"><div class="qa-section-title">典型事件</div><p>例如 Node 新增、Allocatable/label/taint 改变，Pod 删除释放资源，PVC/PV/StorageClass 变化，ResourceClaim/ResourceSlice 更新，以及导致失败的亲和对象变化。真正依赖哪些事件由返回 Unschedulable 的插件通过 EnqueueExtension 注册。</p></div>
<div class="qa-section"><div class="qa-section-title">流转</div><p>Hint 判断“可能可调度”后，Pod 根据是否仍处于 backoff 进入 BackoffQ 或 ActiveQ；判断无关则留在 UnschedulablePods。超时 flush 是安全网，但如果大量 Pod 只能靠 flush 后才成功，应检查插件的事件注册和 QueueingHint。</p></div>
<div class="qa-section"><div class="qa-section-title">性能价值</div><p>没有精细 Hint 时，一次 Node 或 Pod 更新可能唤醒成千上万个与它无关的 Pending Pod，重复执行昂贵的 Filter/Score。QueueingHint 把“资源类型相关”进一步细化为“这次字段变化对这个 Pod 相关”。</p></div>
</div></div>

## 约束、抢占与扩展

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Taint/Toleration、NodeAffinity 和 PodAffinity 有什么区别？</div>
<div class="qa-a">
<div class="qa-summary">Taint 从节点侧排斥 Pod，Toleration 只表示允许；NodeAffinity 选择节点属性；PodAffinity/AntiAffinity 根据其他 Pod 的位置表达聚合或分散。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>专用 GPU 节点常用 taint 建立默认隔离，再用 node affinity 选择型号；服务高可用可用 topology spread 或 anti-affinity 跨故障域分散。多个约束同时存在时必须全部满足。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>Toleration 不会主动把 Pod 吸引到该节点；大规模 PodAffinity 扫描成本较高。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Kubernetes 默认抢占是怎么发生的？</div>
<div class="qa-a">
<div class="qa-summary">高优 Pod 无法调度时，PostFilter 可在候选节点上模拟删除低优 Pod，选择受影响最小且能满足高优 Pod 的节点，再由控制面驱逐 victims。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>PriorityClass 决定优先级，抢占只处理资源和调度约束，不理解训练进度、Checkpoint 或 NCCL 重建成本。PDB 会参与受害者选择但不保证绝对不被抢占。</p></div>
<div class="qa-section"><div class="qa-section-title">AI Infra 追问</div><p>训练平台应做代价感知抢占：综合释放资源、Checkpoint 新鲜度、重启成本和拓扑价值，并提供优雅退出窗口。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: nominatedNodeName 是什么？为什么不一定等于最终 nodeName？</div>
<div class="qa-a">
<div class="qa-summary"><code>status.nominatedNodeName</code> 是对 Pending Pod 的候选节点提名，常见于抢占；<code>spec.nodeName</code> 才是完成绑定后的节点。提名是 best-effort，不是资源锁。</div>
<div class="qa-section"><div class="qa-section-title">为什么会不同</div><p>victims 仍在优雅退出时，其他 Node 可能先变得可用；也可能有更高优 Pod 抢走被提名节点，或集群状态/约束变化使该节点不再可行。Scheduler 可以清除或覆盖 nomination，再把 Pod 绑定到其他节点。</p></div>
<div class="qa-section"><div class="qa-section-title">当前边界</div><p>较新的 Kubernetes 也允许外部组件提名节点，Scheduler 仍可忽略该建议。排障时用 nominatedNodeName 观察抢占意图，不能把它当作 Pod 已经调度成功。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么已经驱逐 victims，抢占者仍可能调度不上？PDB 有什么影响？</div>
<div class="qa-a">
<div class="qa-summary">驱逐只创造“预计可用”的候选空间；victims 的优雅终止、并发调度和约束变化都可能让这个机会消失。PDB 参与选择但只是 best-effort，不是抢占的绝对禁止条件。</div>
<div class="qa-section"><div class="qa-section-title">仍失败的原因</div><p>victims 尚未退出；更高优 Pod 先占用节点；卷、端口、亲和/反亲和或拓扑状态发生变化；Pod 依赖跨节点反亲和而默认抢占不做 cross-node preemption；外部资源或 PreBind/Bind 失败。Scheduler 会重新排队并再次计算，而不是强绑 nominated Node。</p></div>
<div class="qa-section"><div class="qa-section-title">PDB</div><p>默认抢占在选择候选/victims 时优先寻找不违反 PDB 的方案，并以违反数量作为重要比较因素；若没有不违反 PDB 的可行方案，仍可能抢占受 PDB 保护的低优 Pod。PDB 保护的是可用副本预算，不保证某个具体 Pod 永不被抢占。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何实现训练任务的代价感知抢占？</div>
<div class="qa-a">
<div class="qa-summary">把“释放资源后能否放下”作为硬条件，再最小化 victims 的业务损失；成本至少包含优先级、Checkpoint 年龄、已运行时间、重启/NCCL 重建成本、PDB 影响和被破坏的 GPU 拓扑价值。</div>
<div class="qa-section"><div class="qa-section-title">实现位置</div><p>可在自定义 PostFilter/抢占插件中模拟候选 Node 与 victim 集合，或由批调度器在 Job/PodGroup 层统一决策。单 Pod 默认抢占不了解 Job 完成度，因此训练场景通常还要让 Operator/队列提供可被 Scheduler 本地读取的任务成本状态。</p></div>
<div class="qa-section"><div class="qa-section-title">执行协议</div><p>先请求 checkpoint/优雅退出并设置最大宽限时间，再驱逐；用 UID、attempt 和 fencing 避免旧实例继续写输出。还要设置 aging/fairness，避免“已经运行很久所以永远不能抢占”导致高优任务饥饿。</p></div>
<div class="qa-section"><div class="qa-section-title">验证</div><p>同时看高优任务等待时间、被浪费 GPU-hours、checkpoint 恢复耗时、PDB violation、抢占后成功率与重复抢占次数，不能只优化驱逐数量。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么时候选择 Scheduler Plugin、Extender 或独立 Scheduler？</div>
<div class="qa-a">
<div class="qa-summary">要进入原生调度周期并共享 Cache 时用 Framework Plugin；兼容旧系统或远程过滤打分时用 Extender；需要不同队列和生命周期语义时考虑独立 Scheduler。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Plugin 性能最好但与 Kubernetes 版本耦合；Extender 通过 HTTP 调用，简单但延迟高、扩展点有限；独立 Scheduler 隔离最强，但要自己解决 Cache、抢占、HA、可观测和版本维护。简单准入排队优先复用 Kueue/Volcano。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>不要为了一个 Score 规则重写完整调度器，也不要把 Admission Webhook 当成持续调度控制器。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Scheduler 如何做 HA？为什么多副本不等于并行调度？</div>
<div class="qa-a">
<div class="qa-summary">相同职责的 kube-scheduler 副本通过 API Server 中的 Lease 做 Leader Election，通常只有 leader 调度、其他副本热备；它提升故障可用性，不增加正常时吞吐。</div>
<div class="qa-section"><div class="qa-section-title">故障切换</div><p>Leader 按 leaseDuration/renewDeadline/retryPeriod 续约，失联后 standby 竞争 Lease 并从 API 对象和 Informer Cache 恢复工作。参数过小会因控制面抖动频繁切主，过大则延长调度停顿。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么不是多活</div><p>各副本有独立队列、Cache 和 Assumed Pod 状态；若同时处理同一批未绑定 Pod，会竞争 Binding 并造成重复计算。默认调度的 Scheduling Cycle 按 Pod 串行，配置中的 <code>parallelism</code> 主要并行节点级 Filter/Score 工作，不是让多个副本并行取同一队列。</p></div>
<div class="qa-section"><div class="qa-section-title">真正的并行边界</div><p>Binding Cycle 可并发；若运行多个不同 <code>schedulerName</code> 的调度器，可处理明确分流的 Pod，但它们不共享 Cache，对共享 Node/设备仍可能竞争，必须接受放置质量、抢占和运维复杂度。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: percentageOfNodesToScore 为什么能提高吞吐？降低采样比例会牺牲什么？</div>
<div class="qa-a">
<div class="qa-summary">Scheduler 找到达到阈值数量的 feasible Nodes 后就停止继续做 Filter，并只对这批节点 Score；减少每个 Pod 的节点级插件调用，代价是可能错过全局最优放置。</div>
<div class="qa-section"><div class="qa-section-title">机制</div><p>参数是全体 Node 的百分比阈值。默认值随集群规模从约 50% 下降到 10%，自动值下限为 5%；实现还有至少寻找 100 个 feasible Nodes 的保护，小集群通常仍会检查全部节点。节点遍历会轮转并跨 zone 交错，避免永远只采样固定前缀。</p></div>
<div class="qa-section"><div class="qa-section-title">牺牲</div><p>采样越低，Filter/Score 延迟通常越小，但最优节点被看到的概率下降，可能恶化拓扑分散、装箱率、能耗、镜像本地性与 GPU 碎片，并放大自定义 Score 策略的随机性。调度结果仍满足硬约束，只是“可行中的最优”质量下降。</p></div>
<div class="qa-section"><div class="qa-section-title">复杂度</div><p>PreFilter 通常按 Pod/关联对象做一次；Filter/Score 成本首先乘以实际评估的 Node 数 <code>N</code>。若插件每个节点再扫描现有 Pod 或设备，则会接近 <code>O(N×P_node)</code> 或 <code>O(N×D_node)</code>；应在 PreFilter/PreScore 预聚合，并用索引或位图把每节点判断压到近似 O(1)。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 调度吞吐下降时看哪些指标？如何定位 Filter/Score 插件和不可调度队列抖动？</div>
<div class="qa-a">
<div class="qa-summary">先区分“入队太快、算法变慢、绑定变慢、还是多数 Pod 本来就不可调度”，再按 queue、result、extension_point、plugin 四个维度下钻。</div>
<div class="qa-section"><div class="qa-section-title">总量与队列</div><p>看成功的 <code>scheduler_schedule_attempts_total</code> rate、<code>scheduler_pending_pods</code> 的 active/backoff/unschedulable/gated 分布，以及 Pod 端到端 scheduling latency。ActiveQ 增长多为处理能力不足，BackoffQ 增长多为重复失败，Unschedulable 增长要按失败插件和资源原因拆。</p></div>
<div class="qa-section"><div class="qa-section-title">扩展点与插件</div><p>用稳定指标 <code>scheduler_framework_extension_point_duration_seconds</code> 先定位 Filter、Score、Permit 或 Bind 阶段，再用 alpha 指标 <code>scheduler_plugin_execution_duration_seconds</code> 按 plugin/extension_point 看调用次数与 P95/P99。Filter/Score 是节点级热路径，要把单次耗时乘实际候选节点数；排查外部 RPC、锁竞争、全量扫描、Cache miss、日志过量和 GC。</p></div>
<div class="qa-section"><div class="qa-section-title">队列抖动</div><p>用 <code>scheduler_queue_incoming_pods_total</code> 找出高频入队事件，检查失败插件是否注册过宽的事件与 QueueingHint；<code>scheduler_pod_scheduled_after_flush_total</code> 持续增长则提示 Hint/事件注册可能漏唤醒。修复方式包括更精确的 Hint、正确 backoff、SchedulingGates/队列准入、减少无意义对象更新，并先解决大批 Pod 的共同硬约束。</p></div>
<div class="qa-section"><div class="qa-section-title">验证</div><p>用 scheduler simulator 或生产快照回放相同 Pod，比较插件启停、节点采样比例和候选节点规模；同时确认 API Server/etcd 与 Bind 请求延迟，避免把控制面写瓶颈误判成 Score 慢。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么默认调度器不够支持分布式训练？</div>
<div class="qa-a">
<div class="qa-summary">默认调度单元是单 Pod，缺少作业级 Gang、队列公平、Checkpoint 代价和 GPU/NVLink 拓扑语义。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>DDP/MPI/NCCL 任务只启动部分 Worker 时无法有效运行，却已经占用 GPU。平台需要在准入层判断整个 Job 是否达到 <code>minAvailable</code>，再统一放行；还要用队列、配额、Backfill、拓扑打分和代价感知抢占管理作业级目标。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>Volcano 偏批调度执行，Kueue 偏队列和准入；实际也可组合原生 Scheduler 或其他调度器。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果实现 GPU 拓扑感知插件，应该放在哪些扩展点？</div>
<div class="qa-a">
<div class="qa-summary">PreFilter 解析并缓存需求，Filter 保证拓扑硬约束，Score 优化放置质量，Reserve/Unreserve 维护并发账本；只有存在成组等待时才用 Permit，设备级状态变化还要配 QueueingHint。</div>
<div class="qa-section"><div class="qa-section-title">PreFilter / Filter</div><p>PreFilter 从 Pod、ResourceClaim 或任务 CR 中提取 GPU 数、型号、NVLink island、NUMA/NIC 距离和 gang 标识写入 CycleState；Filter 判断节点是否存在满足数量、健康和连通性的可用设备集合。无法妥协的型号、显存或同 island 要求必须是 Filter 硬约束。</p></div>
<div class="qa-section"><div class="qa-section-title">PreScore / Score</div><p>PreScore 汇总候选节点的拓扑/碎片信息；Score 在可行节点中比较连续空闲卡、NVLink/NIC/NUMA 距离、装箱后碎片和为大任务保留完整 island 的价值。小任务是否填碎片是策略，不是通用事实。</p></div>
<div class="qa-section"><div class="qa-section-title">Reserve / Permit / PreBind</div><p>Reserve 用 Pod UID 对选定设备集合做临时占位，Unreserve 幂等释放，避免并发 binding cycle 看到同一组设备；Permit 只在需要 Gang/配额同步放行时等待。若必须在绑定前准备 ResourceClaim 或外部分配，可放 PreBind，但应避免长 RPC；通常仍由 DefaultBinder 完成 Pod 绑定。</p></div>
<div class="qa-section"><div class="qa-section-title">状态来源</div><p>设备级属性优先用 DRA ResourceSlice/ResourceClaim 或受控 CRD/Node 画像表达，插件通过 Informer 本地缓存读取。Filter/Score 不能逐 Node 请求 Prometheus 或远程模型；相关资源更新应注册 EnqueueExtension/QueueingHint 唤醒受影响 Pod。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>总空闲 GPU 数足够不代表能形成任务需要的同机或同拓扑集合。</p></div>
</div></div>

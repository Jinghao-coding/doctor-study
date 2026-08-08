## 一句话结论

Scheduler 面试题不能停留在“Filter 后 Score”。需要讲清队列、Snapshot、Assume、调度周期与绑定周期，并说明普通 Pod 调度为什么不能直接满足 Gang、GPU 拓扑、公平性和高代价抢占。

## 核心调度链路

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: kube-scheduler 的完整调度流程是什么？</div>
<div class="qa-a">
<div class="qa-summary">Pod 从 SchedulingQueue 出队后，经过 PreFilter、Filter、PostFilter、PreScore、Score、Reserve、Permit、PreBind、Bind 和 PostBind；前半段选节点，后半段提交绑定。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Scheduler 基于 Cache Snapshot 计算可行节点，Filter 排除节点，Score 排序；选定节点后先在 Cache 中 Assume，Reserve 维护插件状态，Permit 可等待 Gang 条件，最后异步执行绑定周期。失败时 Forget Assume 并按原因进入 BackoffQ 或 UnschedulablePods。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>Scheduler 只选择 Node，不创建容器；具体设备 ID 在传统 Device Plugin 路径中通常由 kubelet 侧分配。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Filter 和 Score 分别解决什么问题？常见插件有哪些？</div>
<div class="qa-a">
<div class="qa-summary">Filter 判断节点能不能放，Score 判断可行节点中放哪里更好。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>常见 Filter 包括 NodeResourcesFit、TaintToleration、NodeAffinity、VolumeBinding 和 PodTopologySpread；Score 可使用 NodeResourcesFit、ImageLocality、InterPodAffinity、PodTopologySpread 等。Filter 返回不可行原因，Score 结果归一化后按权重汇总。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>硬约束应进入 Filter，偏好进入 Score；把硬约束只写成低分可能仍把 Pod 放到错误节点。</p></div>
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
<div class="qa-q">Q: ActiveQ、BackoffQ 和 UnschedulablePods 分别是什么？</div>
<div class="qa-a">
<div class="qa-summary">ActiveQ 存等待调度的 Pod；BackoffQ 存失败后等待退避的 Pod；UnschedulablePods 按失败原因等待相关集群事件触发重试。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>新 Pod 进入 ActiveQ；调度错误通常进入指数退避；确实无可行节点的 Pod 进入 UnschedulablePods。Node、PVC、Pod 等事件通过 QueueingHint 判断是否可能解决原失败原因，避免所有 Pending Pod 被无差别唤醒。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>Resync 或任意事件都全量重试会造成惊群和无效调度。</p></div>
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
<div class="qa-q">Q: 什么时候选择 Scheduler Plugin、Extender 或独立 Scheduler？</div>
<div class="qa-a">
<div class="qa-summary">要进入原生调度周期并共享 Cache 时用 Framework Plugin；兼容旧系统或远程过滤打分时用 Extender；需要不同队列和生命周期语义时考虑独立 Scheduler。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Plugin 性能最好但与 Kubernetes 版本耦合；Extender 通过 HTTP 调用，简单但延迟高、扩展点有限；独立 Scheduler 隔离最强，但要自己解决 Cache、抢占、HA、可观测和版本维护。简单准入排队优先复用 Kueue/Volcano。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>不要为了一个 Score 规则重写完整调度器，也不要把 Admission Webhook 当成持续调度控制器。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么默认调度器不够支持分布式训练？</div>
<div class="qa-a">
<div class="qa-summary">默认调度单元是单 Pod，缺少作业级 Gang、队列公平、Checkpoint 代价和 GPU/NVLink 拓扑语义。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>DDP/MPI/NCCL 任务只启动部分 Worker 时无法有效运行，却已经占用 GPU。平台需要在准入层判断整个 Job 是否达到 <code>minAvailable</code>，再统一放行；还要用队列、配额、Backfill、拓扑打分和代价感知抢占管理作业级目标。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>Volcano 偏批调度执行，Kueue 偏队列和准入；实际也可组合原生 Scheduler 或其他调度器。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 碎片和拓扑感知调度怎么做？</div>
<div class="qa-a">
<div class="qa-summary">先在 Filter 满足型号、显存、健康、Gang 等硬约束，再在 Score 中综合连续空闲卡、NVLink/NIC/NUMA 距离和放置后的碎片代价。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>小任务可优先填充已有碎片，大任务保留完整节点或 NVLink island；用 Reservation 防止长期饥饿，用 Backfill 利用等待窗口。短期可通过 Node Label、拓扑发现和 Scheduler Plugin 实现，设备级属性逐步可用 DRA ResourceSlice/Claim 表达。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>总空闲 GPU 数足够不代表能形成任务需要的同机或同拓扑集合。</p></div>
</div></div>

## 关联模块

- `Scheduler 主链路`：队列、Cache、Assume、绑定与抢占源码路径。
- `插件开发与扩展点`：各 Framework Hook 和工程代码骨架。
- `任务调度理论`：Gang、Backfill、公平性、碎片与代价感知抢占。
- `GPU 集群管理`：Volcano、Kueue、拓扑和故障恢复。

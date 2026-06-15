## 一句话结论

Workload Controller 的本质是 reconcile：持续把实际状态拉回期望状态。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Kubernetes 核心 |
| 章节类型 | 系统类 |
| 解决问题 | 围绕控制面、调度资源模型、Workload Controller、网络存储、安全多租户、排障和 AI Infra GPU/DRA 建立平台面试答案。 |
| 面试抓手 | 区分 Deployment/StatefulSet/Job/Operator 的边界。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m">
<p><strong>Workload 与 Controller：声明式系统的核心。</strong></p>
<p>Workload 解决“如何管理一组 Pod”，Controller 解决“如何让实际状态持续逼近期望状态”。面试中不要只背 Deployment、StatefulSet、DaemonSet、Job 的用途，还要讲清楚 <strong>Informer → WorkQueue → Reconcile → 更新 status</strong> 这条控制循环。</p>
</div>

<div class="card card-m">
<h3>第一部分：Workload（管理 Pod 生命周期与副本形态）</h3>
<p>Workload 这一部分回答“应该用哪种对象来管理 Pod”。先理解 Pod 生命周期和探针，再学习 Deployment、StatefulSet、DaemonSet、Job、CronJob 的选型边界，最后落到发布链路和 AI Infra 场景。</p>
</div>

<div class="card card-s">
<h4>Pod 生命周期与探针</h4>
<table>
<tr><th>阶段/机制</th><th>含义</th><th>面试重点</th></tr>
<tr><td>Pending</td><td>Pod 已创建但还未全部容器运行</td><td>可能卡在调度、镜像、网络、存储、资源</td></tr>
<tr><td>Running</td><td>Pod 已绑定节点，至少一个容器运行或启动/重启中</td><td>Running 不代表业务 ready</td></tr>
<tr><td>Succeeded / Failed</td><td>所有容器正常退出或至少一个失败退出</td><td>Job/CronJob 重点关注退出码和重试策略</td></tr>
<tr><td>livenessProbe</td><td>判断容器是否需要重启</td><td>配置过激会导致反复重启</td></tr>
<tr><td>readinessProbe</td><td>判断 Pod 是否可接流量</td><td>失败会从 Service endpoints 移除</td></tr>
<tr><td>startupProbe</td><td>保护慢启动应用</td><td>启动成功前禁用 liveness/readiness 的失败影响</td></tr>
</table>
</div>

<div class="card card-d">
<h4>Workload 控制器选型</h4>
<p>Workload 控制器的本质不是“换一种 Pod 写法”，而是把不同类型应用的生命周期管理模式固化下来。选型时不要先背名字，而要先问五个问题：这个任务是否长期运行？是否无状态？是否需要稳定身份和稳定存储？是否必须每个节点都运行？是否以完成为目标而不是持续服务？</p>
<table>
<tr><th>控制器</th><th>核心语义</th><th>适合场景</th><th>不适合场景</th><th>面试追问</th></tr>
<tr><td>Deployment</td><td>维护一组可替换的无状态 Pod 副本</td><td>Web API、推理服务、网关、普通无状态 worker</td><td>需要稳定 Pod 名称、每个副本独立存储、严格启动顺序的服务</td><td>ReplicaSet、滚动发布、回滚、<code>maxSurge</code>/<code>maxUnavailable</code></td></tr>
<tr><td>StatefulSet</td><td>维护有序、有稳定身份和稳定存储的 Pod 集合</td><td>数据库、ZooKeeper/etcd、Kafka、需要固定 ordinal 的训练/服务组件</td><td>副本完全等价、随便替换即可的无状态服务</td><td>Headless Service、PVC 模板、ordinal、有序扩缩容</td></tr>
<tr><td>DaemonSet</td><td>保证符合条件的每个 Node 上运行一个 Pod</td><td>日志采集、监控 agent、CNI、CSI node plugin、GPU/Device Plugin</td><td>只想运行固定副本数，或者只想对外提供水平扩缩容服务</td><td>节点新增自动补 Pod、nodeSelector/tolerations、滚动升级 agent</td></tr>
<tr><td>Job</td><td>运行到成功完成为止，关注完成数和失败重试</td><td>离线计算、一次性数据处理、模型转换、批量压测、训练前预处理</td><td>需要长期常驻、持续接流量的服务</td><td><code>backoffLimit</code>、<code>parallelism</code>、<code>completions</code>、Indexed Job</td></tr>
<tr><td>CronJob</td><td>按时间周期创建 Job</td><td>定时清理、周期报表、定期 checkpoint 校验、定时数据同步</td><td>强实时任务、必须精确到秒且不能受控制面延迟影响的任务</td><td><code>concurrencyPolicy</code>、<code>startingDeadlineSeconds</code>、历史保留</td></tr>
</table>
</div>

<div class="card card-s">
<h4>选型决策树：先看生命周期，再看身份和放置约束</h4>
<table>
<tr><th>问题</th><th>如果答案是 yes</th><th>通常选择</th><th>原因</th></tr>
<tr><td>任务是否只需要跑完一次或跑完 N 个分片？</td><td>是</td><td>Job</td><td>Job 关心成功完成、失败重试和并行完成数，而不是常驻副本</td></tr>
<tr><td>任务是否按固定周期触发？</td><td>是</td><td>CronJob</td><td>CronJob 负责按 schedule 创建 Job，并处理错过调度和并发策略</td></tr>
<tr><td>是否要求每个节点都运行一个组件？</td><td>是</td><td>DaemonSet</td><td>节点级 agent 的目标不是副本数，而是覆盖所有符合条件的节点</td></tr>
<tr><td>每个副本是否需要稳定网络身份或独立持久化存储？</td><td>是</td><td>StatefulSet</td><td>StatefulSet 提供稳定 Pod 名、ordinal、PVC 和有序生命周期</td></tr>
<tr><td>副本是否完全等价、可替换、可水平扩缩容？</td><td>是</td><td>Deployment</td><td>Deployment 最适合无状态服务滚动发布、扩缩容和回滚</td></tr>
</table>
<div class="qa-summary">一句话：Deployment 管“可替换副本”，StatefulSet 管“有身份副本”，DaemonSet 管“每节点一个”，Job 管“跑完即止”，CronJob 管“定时跑完”。</div>
</div>

<div class="card card-w">
<h4>AI Infra 场景怎么选</h4>
<table>
<tr><th>场景</th><th>推荐控制器</th><th>为什么</th><th>容易踩坑</th></tr>
<tr><td>在线推理服务</td><td>Deployment</td><td>请求无状态，副本可替换，适合 HPA、滚动发布和回滚</td><td>如果有本地 KV cache / 模型 warmup，要用 readiness 控制接流量时机</td></tr>
<tr><td>每台 GPU 节点运行 device plugin</td><td>DaemonSet</td><td>需要覆盖所有 GPU 节点，并随节点加入自动部署</td><td>要配 nodeSelector、tolerations，避免部署到非 GPU 节点</td></tr>
<tr><td>NCCL benchmark / 模型转换 / 数据预处理</td><td>Job</td><td>目标是完成任务并退出，失败可按策略重试</td><td>不要用 Deployment 跑一次性任务，否则失败语义和完成语义不清楚</td></tr>
<tr><td>周期性清理 checkpoint 或生成资源报表</td><td>CronJob</td><td>按时间创建 Job，并控制并发和历史保留</td><td>要设置 <code>concurrencyPolicy</code>，避免上一次未完成时重复跑</td></tr>
<tr><td>带稳定身份的分布式存储或协调组件</td><td>StatefulSet</td><td>每个副本需要固定名称、固定存储和有序启动</td><td>不要把普通无状态服务强行做 StatefulSet，会增加运维复杂度</td></tr>
<tr><td>PyTorch/Volcano/Kubeflow 训练任务</td><td>通常不是原生 Deployment，而是 Job/CRD/Operator</td><td>训练需要 gang、角色、rank、状态机、失败恢复和队列准入</td><td>原生 Job 不理解训练语义；复杂训练通常要 TrainingJob / PyTorchJob / VolcanoJob</td></tr>
</table>
</div>

<div class="card card-r">
<h4>高频误区</h4>
<ul>
<li><strong>误区 1：有多个副本就用 Deployment。</strong>如果副本有固定身份、固定磁盘或有序启动要求，应考虑 StatefulSet。</li>
<li><strong>误区 2：跑一次的任务也用 Deployment。</strong>Deployment 追求长期副本数稳定，任务完成退出后会被重新拉起；一次性任务应该用 Job。</li>
<li><strong>误区 3：定时任务直接在应用里 sleep 循环。</strong>CronJob 可以把调度、失败重试、历史保留和并发策略交给 Kubernetes 管理。</li>
<li><strong>误区 4：DaemonSet 等于每台机器一定有一个 Pod。</strong>它只会在符合 nodeSelector、affinity、taints/tolerations 等条件的节点上创建 Pod。</li>
<li><strong>误区 5：StatefulSet 自动解决数据一致性。</strong>StatefulSet 只提供稳定身份和存储，数据复制、选主、分片、故障恢复仍然是应用或 Operator 的职责。</li>
</ul>
</div>

<div class="card card-m">
<h4>Deployment 滚动发布链路</h4>
<ol>
<li>用户修改 Deployment template，例如镜像 tag。</li>
<li>Deployment Controller 发现 template hash 变化，创建新的 ReplicaSet。</li>
<li>按 <code>maxSurge</code> 增加新 Pod，按 <code>maxUnavailable</code> 减少旧 Pod。</li>
<li>新 Pod readiness 通过后才进入 Service endpoints，逐步承接流量。</li>
<li>旧 ReplicaSet 保留一定 revision，支持 <code>kubectl rollout undo</code> 回滚。</li>
</ol>
<p>发布排障要看 Deployment condition、ReplicaSet、Pod events、readiness probe、镜像拉取和应用日志。</p>
</div>

<div class="card card-m">
<h3>第二部分：Controller（让实际状态持续逼近期望状态）</h3>
<p>Controller 这一部分回答“系统如何自动修正状态”。核心不是事件回调，而是基于 Informer 缓存、WorkQueue 和 Reconcile 循环，把用户声明的 spec 转换为实际资源，并把结果写回 status。</p>
</div>

<div class="card card-s">
<h4>Controller Pattern：Informer、WorkQueue、Reconcile</h4>
<table>
<tr><th>组件</th><th>作用</th><th>为什么需要</th></tr>
<tr><td>Reflector</td><td>List/Watch API Server，把变化写入本地缓存</td><td>减少控制器直接打 API Server 的压力</td></tr>
<tr><td>Informer</td><td>维护对象缓存，并触发事件回调</td><td>让控制器以事件驱动方式工作</td></tr>
<tr><td>Indexer / Lister</td><td>按 namespace/name 或索引查询缓存</td><td>提高读取效率</td></tr>
<tr><td>WorkQueue</td><td>保存需要处理的对象 key，支持去重和限速</td><td>事件和业务处理解耦，失败可重试</td></tr>
<tr><td>Reconcile</td><td>读取当前状态，计算差异，执行修正动作</td><td>控制器的核心逻辑</td></tr>
<tr><td>Status / Conditions</td><td>对外暴露控制结果和阶段状态</td><td>便于用户和其他控制器观测</td></tr>
</table>
</div>

<div class="card card-w">
<h4>CRD / Operator：先把三个层次讲清楚</h4>
<p><strong>Operator = CRD + Controller + 领域运维逻辑。</strong>面试时不要只说“Operator 是自定义控制器”，而要把三层拆开：CRD 让 Kubernetes 认识一种新的资源类型；Controller 负责 watch 这种资源并不断 reconcile；Operator 在 reconcile 里放入某个领域的生命周期管理经验，例如训练任务启动、失败恢复、扩缩容、checkpoint 清理和状态回写。</p>
<table>
<tr><th>层次</th><th>解决的问题</th><th>面试中要讲清楚</th></tr>
<tr><td>CRD</td><td>把领域对象注册成 Kubernetes API 资源</td><td>例如 <code>TrainingJob</code>、<code>RayCluster</code>、<code>InferenceService</code>，用户可以像操作 Pod 一样 <code>kubectl apply/get/describe</code></td></tr>
<tr><td>Controller</td><td>持续把实际状态修正到期望状态</td><td>通过 Informer 监听事件，放入 WorkQueue，由 Reconcile 创建/更新/删除下游资源</td></tr>
<tr><td>Operator</td><td>把领域运维知识自动化</td><td>不仅创建 Pod，还要处理启动顺序、故障恢复、状态机、外部资源清理、升级和多租户策略</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">一句话理解</div><p>CRD 是“用户提交的订单格式”，Controller 是“订单处理流水线”，Operator 是“懂这个业务的自动运维机器人”。如果只是创建几个 Pod，那只是 Controller；如果它还理解训练任务什么时候算成功、失败后怎么重试、checkpoint 怎么清理、队列资源怎么释放，才更接近 Operator。</p></div>
</div>

<div class="card card-s">
<h4>CRD 对象应该怎么设计：spec、status、conditions</h4>
<p>CRD 设计的核心是把“用户想要什么”和“系统观察到什么”分开。<code>spec</code> 是用户声明的期望状态，<code>status</code> 是控制器观察和计算出的实际状态，<code>conditions</code> 是结构化阶段信息。这个边界如果混乱，Operator 很容易变成不可维护的脚本。</p>
<table>
<tr><th>字段</th><th>应该放什么</th><th>不应该放什么</th><th>训练任务例子</th></tr>
<tr><td><code>spec</code></td><td>用户声明的期望状态</td><td>运行时变化、错误原因、Pod 实际 IP</td><td>镜像、启动命令、worker 数、GPU 数、队列、优先级、容错策略</td></tr>
<tr><td><code>status</code></td><td>系统观测到的实际状态</td><td>用户配置项</td><td>当前 phase、已创建 Pod 数、ready worker 数、最近一次失败原因、checkpoint 路径</td></tr>
<tr><td><code>conditions</code></td><td>可机器读取的状态条件</td><td>大段非结构化日志</td><td><code>Admitted</code>、<code>PodsCreated</code>、<code>WorkersReady</code>、<code>Running</code>、<code>Failed</code></td></tr>
<tr><td><code>metadata.ownerReferences</code></td><td>表达父子资源归属</td><td>跨 namespace 乱指向</td><td>Worker Pod、Service、ConfigMap 归属于 TrainingJob，TrainingJob 删除后级联回收</td></tr>
<tr><td><code>metadata.finalizers</code></td><td>删除前必须完成的外部清理</td><td>永远不移除的阻塞标记</td><td>释放队列占用、删除外部 checkpoint 临时目录、清理临时 Service/DNS 记录</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">面试高频追问</div><p><strong>为什么 Controller 不应该随意改 spec？</strong>因为 spec 是用户意图，Controller 如果偷偷修改 spec，就会破坏声明式系统的可预测性。正确做法是：默认值通过 admission/defaulting 处理，运行时状态写入 status，异常原因写入 status.conditions。</p></div>
</div>

<div class="card card-d">
<h4>Reconcile 到底在做什么：从“事件驱动”到“状态驱动”</h4>
<p>Operator 不是收到一个事件就执行一次脚本，而是每次 reconcile 都重新读取当前世界，计算期望状态和实际状态的差异，然后执行最小修正动作。这样即使事件丢失、Controller 重启、Pod 被人工删除，也能最终恢复一致。</p>
<div class="sched-flow">
<svg viewBox="0 0 980 250" role="img" aria-label="Operator reconcile flow">
<defs>
<marker id="operatorArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
<path d="M0,0 L0,6 L9,3 z" fill="currentColor"></path>
</marker>
</defs>
<rect x="35" y="80" width="135" height="70" class="sched-node sched-api"></rect>
<text x="58" y="112" class="sched-label">TrainingJob</text>
<text x="58" y="134" class="sched-desc">用户声明 spec</text>
<path d="M170 115 C205 115 215 115 250 115" class="sched-arrow" style="marker-end:url(#operatorArrow)"></path>
<rect x="250" y="80" width="135" height="70" class="sched-node sched-cache"></rect>
<text x="282" y="112" class="sched-label">Informer</text>
<text x="282" y="134" class="sched-desc">List / Watch</text>
<path d="M385 115 C420 115 430 115 465 115" class="sched-arrow" style="marker-end:url(#operatorArrow)"></path>
<rect x="465" y="80" width="135" height="70" class="sched-node sched-queue"></rect>
<text x="492" y="112" class="sched-label">WorkQueue</text>
<text x="492" y="134" class="sched-desc">去重 / 限速 / 重试</text>
<path d="M600 115 C635 115 645 115 680 115" class="sched-arrow" style="marker-end:url(#operatorArrow)"></path>
<rect x="680" y="80" width="135" height="70" class="sched-node sched-bind"></rect>
<text x="710" y="112" class="sched-label">Reconcile</text>
<text x="710" y="134" class="sched-desc">计算差异并修正</text>
<path d="M748 150 C748 198 128 198 102 150" class="sched-arrow sched-dashed" style="marker-end:url(#operatorArrow)"></path>
<text x="280" y="224" class="sched-desc">循环：创建/更新 Pod、Service、ConfigMap；写 status；失败后重新入队</text>
</svg>
</div>
<table>
<tr><th>Reconcile 步骤</th><th>要做什么</th><th>TrainingJob 例子</th></tr>
<tr><td>1. 读取对象</td><td>从缓存/API Server 获取 CR 当前状态</td><td>读 TrainingJob 的 spec、status、deletionTimestamp</td></tr>
<tr><td>2. 处理删除</td><td>如果对象正在删除，执行 finalizer 清理</td><td>释放队列 quota、删除临时 checkpoint、移除 finalizer</td></tr>
<tr><td>3. 计算期望状态</td><td>根据 spec 推导应存在的下游资源</td><td>应该有 1 个 master Pod、N 个 worker Pod、Service、ConfigMap</td></tr>
<tr><td>4. 对比实际状态</td><td>检查下游资源是否缺失、过期、异常</td><td>发现 worker-3 被删了，或者镜像版本与 spec 不一致</td></tr>
<tr><td>5. 执行动作</td><td>只做必要的 create/update/delete</td><td>补 Pod、更新 ConfigMap、触发重试、暂停任务</td></tr>
<tr><td>6. 更新 status</td><td>把结果以结构化方式反馈给用户</td><td>写入 Running、Ready workers=7/8、LastError=NCCL timeout</td></tr>
</table>
</div>

<div class="card card-m">
<h4>AI 训练任务 Operator 如何设计：从 CRD 到训练状态机</h4>
<p>训练任务 Operator 的关键不是“创建一堆 Pod”，而是把训练任务抽象成一个可恢复、可观测、可排队、可清理的状态机。它要同时理解 Kubernetes 资源、训练框架语义和调度系统边界。</p>
<div class="queue-detail-grid">
<div class="queue-detail"><h4>1. TrainingJob spec</h4><p>描述用户想要的训练任务：镜像、启动命令、worker 数、每个 worker 的 GPU/CPU/内存、数据路径、checkpoint 策略、队列、优先级、容错策略。</p></div>
<div class="queue-detail active"><h4>2. 下游 Kubernetes 资源</h4><p>Operator 根据 spec 创建 Pod/StatefulSet、Service、ConfigMap、Secret、PVC，并通过 OwnerReference 建立归属关系。</p></div>
<div class="queue-detail backoff"><h4>3. 调度与准入</h4><p>大规模训练不能直接创建一堆 Pod 抢资源。Operator 通常要和 Kueue、Volcano 或自研队列系统配合，等资源整体准入后再启动。</p></div>
<div class="queue-detail unsched"><h4>4. 状态与容错</h4><p>Operator 通过 status.conditions 暴露 Pending、Admitted、PodsCreated、WorkersReady、Running、Restarting、Succeeded、Failed 等阶段。</p></div>
</div>
<table>
<tr><th>状态</th><th>含义</th><th>Operator 动作</th><th>用户能看到什么</th></tr>
<tr><td>Pending</td><td>TrainingJob 已提交，但还没获得资源</td><td>创建队列对象或等待 quota/Gang 准入</td><td>等待原因、队列位置、资源缺口</td></tr>
<tr><td>Admitted</td><td>资源准入通过，可以创建训练资源</td><td>创建 Pod、Service、ConfigMap、Secret</td><td>已准入、开始拉起 worker</td></tr>
<tr><td>WorkersReady</td><td>训练所需 worker 已 ready</td><td>确认 rendezvous endpoint、写入启动配置</td><td>ready worker 数、master endpoint</td></tr>
<tr><td>Running</td><td>训练进程正在运行</td><td>持续观察 Pod、日志、退出码、checkpoint 心跳</td><td>训练运行时长、重启次数、最近 checkpoint</td></tr>
<tr><td>Restarting</td><td>部分 worker 失败，正在恢复</td><td>按策略重建 Pod、触发从 checkpoint 恢复或弹性缩容</td><td>失败原因、恢复进度、retry count</td></tr>
<tr><td>Succeeded / Failed</td><td>训练成功完成或不可恢复失败</td><td>写最终状态，按策略保留或清理资源</td><td>完成时间、失败原因、输出路径</td></tr>
</table>
</div>

<div class="card card-r">
<h4>AI 训练 Operator 的边界：不要和 Scheduler / Device Plugin 混在一起</h4>
<p>这部分是面试官最常追问的地方。Operator、Scheduler Plugin、Device Plugin/DRA 都和 GPU 训练有关，但它们管的层次完全不同。答清楚边界，说明你真的理解 Kubernetes 扩展体系。</p>
<table>
<tr><th>组件</th><th>它负责什么</th><th>不负责什么</th><th>训练场景例子</th></tr>
<tr><td>TrainingJob Operator</td><td>任务生命周期和业务编排</td><td>不决定具体 Pod 放到哪台机器</td><td>创建 worker Pod、写 status、失败恢复、清理 checkpoint 临时资源</td></tr>
<tr><td>Queue / Admission</td><td>任务是否允许进入集群消费资源</td><td>不负责单个 Pod 的节点打分</td><td>Kueue 判断队列 quota 是否足够，Volcano 判断 PodGroup 是否满足 minMember</td></tr>
<tr><td>Scheduler / Scheduler Plugin</td><td>Pod/PodGroup 放到哪些节点</td><td>不理解完整训练业务生命周期</td><td>Gang、拓扑感知、优先级、抢占、GPU/NVLink 亲和</td></tr>
<tr><td>Device Plugin / DRA</td><td>设备发现、上报和容器内设备交付</td><td>不决定训练任务状态机</td><td>把 GPU、MIG、RDMA 网卡暴露给 kubelet，并把设备挂进容器</td></tr>
</table>
<div class="qa-summary">面试口径：Operator 管“这个训练任务应该经历什么生命周期”，Scheduler 管“Pod 应该放在哪里”，Device Plugin/DRA 管“设备如何被发现并交付给容器”。</div>
</div>

<div class="card card-w">
<h4>Kubebuilder 实战：从脚手架到第一个 Operator</h4>
<p>前面的内容解决“Operator 是什么”，Kubebuilder 解决“怎么把它写出来”。Kubebuilder 的价值不是替你写业务逻辑，而是把项目骨架、CRD 生成、RBAC、Webhook、部署 YAML、测试目录这些重复工程化工作标准化。参考文章把完整流程拆成：初始化项目、创建 API、完善 CRD、实现 Controller、可选 Webhook、本地调试、构建镜像和部署清单。</p>
<table>
<tr><th>步骤</th><th>命令 / 产物</th><th>你要真正理解什么</th></tr>
<tr><td>初始化项目</td><td><code>kubebuilder init --domain example.com --repo github.com/xxx/operator</code></td><td><code>domain</code> 会参与 CRD group，例如 <code>training.ai.example.com</code>；<code>repo</code> 是 Go module 路径</td></tr>
<tr><td>创建 API</td><td><code>kubebuilder create api --group core --version v1 --kind Application --namespaced=true</code></td><td>这里本质是在定义一个 GVK：Group、Version、Kind；同时生成 API 类型、CRD 样例、Controller 骨架</td></tr>
<tr><td>完善类型</td><td><code>api/v1/*_types.go</code></td><td>在 Go struct 中定义 <code>Spec</code> 和 <code>Status</code>，再由 controller-gen 生成 CRD schema 和 deepcopy 代码</td></tr>
<tr><td>实现控制器</td><td><code>internal/controller/*_controller.go</code></td><td>核心不是写事件回调，而是在 <code>Reconcile</code> 中反复读取对象、处理删除、创建/更新下游资源、回写 status</td></tr>
<tr><td>生成清单</td><td><code>make manifests</code>、<code>make install</code></td><td>生成 CRD、RBAC、Webhook 等 YAML，并把 CRD 安装到集群</td></tr>
<tr><td>本地运行</td><td><code>make run</code></td><td>Controller 可在本地连远程 kubeconfig 调试，但 Webhook 调试通常需要额外处理证书和访问路径</td></tr>
<tr><td>部署上线</td><td><code>IMG=xxx make docker-buildx</code>、<code>make build-installer</code></td><td>把 Controller 打成镜像，并生成包含 CRD、RBAC、Deployment 的安装包</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">我的理解</div><p>Kubebuilder 不是一个“魔法框架”，它只是把 Kubernetes controller 的标准套路固化下来：API 类型放在 <code>api/</code>，控制循环放在 <code>internal/controller/</code>，部署资源放在 <code>config/</code>。真正体现能力的地方仍然是：你能否把业务对象建模成清晰的 spec/status，并写出幂等、可重试、可观测的 reconcile。</p></div>
<div class="qa-section"><div class="qa-section-title">参考来源</div><p>本节实战流程参考了 <a href="https://www.lixueduan.com/posts/kubernetes/35-build-operator-by-kubebuilder/" target="_blank" rel="noopener">K8s Operator 开发 Part1：快速上手 Kubebuilder，构建你的第一个 K8s Operator</a>，并结合 AI 训练任务 Operator 场景做了重新组织和补充。</p></div>
</div>

<div class="card card-s">
<h4>GVK / GVR：写 Operator 前必须分清的两个标识</h4>
<p>CRD 注册进 API Server 之后，会同时涉及“这个对象是什么”和“我通过 REST 路径怎么访问它”。这就是 GVK 和 GVR 的区别。面试时如果能讲清这个点，说明你不是只会套 Kubebuilder 命令。</p>
<table>
<tr><th>概念</th><th>组成</th><th>更常出现在哪里</th><th>例子</th></tr>
<tr><td>GVK</td><td>Group / Version / Kind</td><td>对象类型识别、Scheme 注册、Controller 处理对象</td><td><code>training.ai.example.com / v1 / TrainingJob</code></td></tr>
<tr><td>GVR</td><td>Group / Version / Resource</td><td>REST 访问、dynamic client、kubectl 资源路径</td><td><code>training.ai.example.com / v1 / trainingjobs</code></td></tr>
<tr><td>核心区别</td><td>Kind 是单数类型名，Resource 通常是复数资源名</td><td>GVK 偏“类型系统”，GVR 偏“API 访问路径”</td><td><code>Kind=Pod</code>，<code>Resource=pods</code></td></tr>
</table>
<div class="qa-summary">面试口径：GVK 用来说明“这是什么类型的对象”，GVR 用来说明“通过哪个 API 资源路径操作它”。Controller 代码里经常关心 GVK/Scheme，动态客户端和 RESTMapper 经常关心 GVR。</div>
</div>

<div class="card card-d">
<h4>Reconcile 代码骨架：Application Demo 到 TrainingJob 的迁移</h4>
<p>参考文章中的 Application Demo 很适合入门：用户提交一个 Application CR，里面包含 <code>spec.image</code> 和 <code>spec.enabled</code>；Controller 根据它创建、更新或删除 Deployment，并把 Deployment 是否 ready 写回 <code>status.ready</code>。把这个例子迁移到 AI 训练场景，就是把 Deployment 换成一组 role 化的 worker/master Pod、Service、ConfigMap、PVC、队列对象和状态机。</p>
<pre><code>// 典型 Reconcile 思路，不是完整可运行代码
func Reconcile(ctx, req) {
  // 1. 根据 namespace/name 获取 CR；NotFound 通常说明对象已删除，直接返回
  job := getTrainingJob(req.NamespacedName)

  // 2. 处理 deletionTimestamp：如果正在删除，先跑 finalizer 清理外部资源
  if job.IsDeleting() {
    cleanupQueueQuota(job)
    cleanupTemporaryCheckpoint(job)
    removeFinalizer(job)
    return
  }

  // 3. 确保 finalizer 存在，保证后续删除前有机会清理外部资源
  ensureFinalizer(job)

  // 4. 根据 spec 计算期望资源：Pod/Service/ConfigMap/PVC/PodGroup 或 Workload
  desired := buildDesiredTrainingResources(job.Spec)

  // 5. 对比实际状态，只做必要的 create/update/delete
  syncOwnedResources(desired)

  // 6. 观察下游资源状态，回写 status.conditions
  updateTrainingJobStatus(job)
}</code></pre>
<table>
<tr><th>Application Demo</th><th>TrainingJob Operator</th><th>设计变化</th></tr>
<tr><td><code>spec.image</code></td><td>镜像、启动命令、role、GPU 数、数据路径</td><td>从单应用部署变成分布式训练拓扑</td></tr>
<tr><td><code>spec.enabled</code></td><td>队列准入、暂停/恢复、重试策略</td><td>是否运行不只是布尔值，还要受 quota、Gang、优先级影响</td></tr>
<tr><td>Deployment ready</td><td>Master/Worker ready、Rendezvous、Checkpoint 心跳</td><td>训练任务 ready 需要结合框架语义</td></tr>
<tr><td><code>status.ready</code></td><td><code>status.phase</code> + <code>conditions</code> + replica 统计 + last error</td><td>状态要能支持排障，而不是只有 true/false</td></tr>
</table>
</div>

<div class="card card-m">
<h4>Webhook：把默认值和校验前移到 Admission 阶段</h4>
<p>Operator 里经常有两类逻辑不要放到 Reconcile 里硬兜底：一类是默认值，一类是非法输入校验。Kubebuilder 可以生成 Webhook 骨架，常见命令是 <code>kubebuilder create webhook --group core --version v1 --kind Application --defaulting --programmatic-validation</code>。</p>
<table>
<tr><th>Webhook 类型</th><th>作用</th><th>Application 例子</th><th>TrainingJob 例子</th></tr>
<tr><td>Mutating Admission Webhook</td><td>给对象补默认值或注入字段</td><td>没有写 <code>enabled</code> 时默认设为 true</td><td>默认 restartPolicy、backoffLimit、checkpoint interval、priorityClass</td></tr>
<tr><td>Validating Admission Webhook</td><td>拒绝非法对象</td><td>校验 <code>spec.image</code> 格式</td><td>校验 GPU 数必须大于 0，worker 数和并行策略匹配，队列名合法</td></tr>
<tr><td>Reconcile</td><td>处理运行时状态收敛</td><td>创建或删除 Deployment</td><td>创建训练资源、等待准入、失败恢复、写 status</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">我的思考</div><p>Webhook 和 Reconcile 的边界要清楚：Webhook 负责“对象能不能进入系统、进入前补什么默认值”，Reconcile 负责“对象已经进入系统后，如何让实际状态收敛”。不要依赖 Reconcile 才发现明显非法的 spec，否则用户会看到对象创建成功但长期失败；也不要在 Webhook 里做耗时外部调用，否则会拖慢 API Server 的写路径。</p></div>
</div>

<div class="card card-w">
<h4>从 Kubebuilder 到生产级 Operator：面试应该主动补充什么</h4>
<p>文章中的流程能帮助你快速跑通第一个 Operator，但面试官通常会继续问“生产环境怎么做”。你需要主动补上工程化、稳定性和可观测性维度。</p>
<table>
<tr><th>维度</th><th>入门 Demo 常见做法</th><th>生产级思考</th></tr>
<tr><td>幂等性</td><td>看到事件就创建资源</td><td>每次 reconcile 都先读实际状态，已存在则比较差异，避免重复创建和重复副作用</td></tr>
<tr><td>OwnerReference</td><td>只创建子资源</td><td>给 Pod/Service/ConfigMap 设置 owner，利用 Kubernetes GC 自动清理内部资源</td></tr>
<tr><td>Finalizer</td><td>可能不处理删除</td><td>清理外部队列占用、对象存储临时目录、实验追踪记录；清理逻辑必须可重试、可超时</td></tr>
<tr><td>Status Conflict</td><td>直接 update status</td><td>处理 resourceVersion 冲突，必要时重试；用 <code>observedGeneration</code> 表示 status 对应哪一版 spec</td></tr>
<tr><td>权限</td><td>给较大的 RBAC</td><td>按最小权限生成和审查 RBAC，避免 Controller 具备不必要的集群级权限</td></tr>
<tr><td>可观测性</td><td>只看日志</td><td>补充 events、conditions、metrics、trace id、reconcile latency、queue depth、error rate</td></tr>
<tr><td>升级兼容</td><td>只有一个版本</td><td>考虑 CRD versioning、conversion webhook、字段废弃策略和向后兼容</td></tr>
</table>
<div class="qa-summary">面试口径：Kubebuilder 帮你生成 Operator 的工程骨架，生产级 Operator 的关键是 API 设计、幂等 Reconcile、删除清理、状态可观测、权限最小化和版本演进。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果让你现场设计一个 TrainingJob CRD，你会包含哪些字段？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心 spec</div><p>至少包括：镜像、启动命令、replica/role 定义、每个 role 的资源请求、队列名、优先级、重试次数、checkpoint 配置、数据输入输出路径、环境变量和 Secret 引用。</p></div>
<div class="qa-section"><div class="qa-section-title">核心 status</div><p>至少包括：phase、conditions、readyReplicas、activeReplicas、failedReplicas、startTime、completionTime、lastCheckpoint、lastFailureReason、observedGeneration。</p></div>
<div class="qa-section"><div class="qa-section-title">设计原则</div><p>spec 表达用户意图，status 表达系统事实；不要把运行时状态塞回 spec，也不要让用户通过改 status 控制系统。</p></div>
<div class="qa-summary">面试口径：TrainingJob CRD 的设计重点是 role 化资源声明、队列准入、容错恢复和可观测状态，而不是简单包一层 PodTemplate。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: TrainingJob Operator 如何处理删除？为什么需要 Finalizer？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">为什么需要</div><p>OwnerReference 只能清理 Kubernetes 内部子资源，但训练任务可能还占着外部系统资源，例如队列占用、临时 checkpoint、对象存储目录、外部 DNS/Service 注册、实验追踪记录。</p></div>
<div class="qa-section"><div class="qa-section-title">删除流程</div><p>用户删除 TrainingJob 后，对象先进入 deletionTimestamp 状态；Operator 看到后执行外部清理；清理成功后移除 finalizer；API Server 最终真正删除对象。</p></div>
<div class="qa-section"><div class="qa-section-title">常见坑</div><p>如果清理逻辑失败但 finalizer 不移除，对象会一直 Terminating；所以 finalizer 逻辑必须幂等、可重试、可超时，并能把失败原因写入 status/events。</p></div>
<div class="qa-summary">面试口径：Finalizer 是删除前的外部资源清理协议，关键是幂等、可重试和失败可观测。</div>
</div>
</div>

<div class="card card-m">

<h4>Workload 与 Controller 高频问答</h4>

<p>本模块的问答按“概念 → 作用 → 链路/排查 → 面试口径”组织，避免只背一段结论。</p>

</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Deployment 和 StatefulSet 有什么区别？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. Deployment 的定位</div><p>Deployment 面向无状态服务，重点是副本数、滚动发布、回滚和通过 Service 做负载均衡。</p></div>
<div class="qa-section"><div class="qa-section-title">2. StatefulSet 的定位</div><p>StatefulSet 面向有状态服务，提供稳定序号、稳定网络身份和稳定 PVC，Pod 通常按顺序创建、更新和删除。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 存储与网络差异</div><p>Deployment 的 Pod 名称和挂载存储通常不稳定；StatefulSet 常配 Headless Service 和 volumeClaimTemplates，让每个副本有固定身份。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 适用场景</div><p>Web 服务、无状态 API 适合 Deployment；数据库、消息队列、需要固定 rank/身份的训练组件更适合 StatefulSet。</p></div>
<div class="qa-summary">面试口径：Deployment 管无状态弹性副本，StatefulSet 管有状态、有序、稳定身份和稳定存储的副本。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Informer 为什么重要？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 概念</div><p>Informer 是 controller-runtime/client-go 中的 List/Watch 缓存机制，会把 API Server 中的对象变化同步到本地缓存。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 作用</div><p>它减少 controller 直接频繁访问 API Server 的压力，并把对象变化转成事件回调。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 和 WorkQueue 的关系</div><p>Informer 收到事件后通常只入队 namespace/name key，真正业务逻辑由 worker 从 WorkQueue 取出后 reconcile。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 生产价值</div><p>本地缓存、事件驱动、失败重试、限速和去重，是 Kubernetes controller 能大规模运行的基础。</p></div>
<div class="qa-summary">面试口径：Informer 负责高效 watch 和缓存对象，WorkQueue 负责解耦事件与处理，Reconcile 负责把实际状态修正到期望状态。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 Controller 不直接 watch 后立刻处理对象，而要放 WorkQueue？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 解耦事件与处理</div><p>watch 回调应该尽快返回，避免业务处理阻塞事件接收，WorkQueue 把“收到事件”和“处理对象”拆开。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 去重</div><p>同一个对象短时间多次变化时，队列可以合并 key，避免重复处理。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 限速与重试</div><p>处理失败可以重新入队并退避，避免 tight loop 打爆 API Server 或外部系统。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 并发控制</div><p>多个 worker 可以并发消费队列，同时保持同一对象按 key 维度可控处理。</p></div>
<div class="qa-summary">面试口径：WorkQueue 是 controller 的缓冲层，解决去重、限速、失败重试和并发控制。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Operator 和普通 Controller 有什么区别？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 共同点</div><p>二者都基于 watch、queue、reconcile 模式，持续把实际状态逼近期望状态。</p></div>
<div class="qa-section"><div class="qa-section-title">2. Operator 的特点</div><p>Operator 通常包含 CRD 和领域运维逻辑，不只是管理原生资源，还把数据库、训练任务、推理服务等运维知识编码进去。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 作用</div><p>它能自动处理部署、扩缩容、备份、故障切换、版本升级、状态回写等复杂生命周期。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 边界</div><p>Operator 负责编排和生命周期，不应该替代 scheduler 做底层放置决策，也不应该替代 Device Plugin/DRA 做设备发现交付。</p></div>
<div class="qa-summary">面试口径：Controller 是控制模式，Operator 是“CRD + Controller + 领域运维知识”的产品化控制器。</div>
</div>
</div>

## 面试回答

**30 秒版：**

Workload Controller 的本质是 reconcile：持续把实际状态拉回期望状态。 区分 Deployment/StatefulSet/Job/Operator 的边界。

**2 分钟版：**

我会先说明这个问题在 Kubernetes 核心 里的位置，再拆核心链路：输入是什么、系统如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：吞吐和延迟、显存和计算、隔离和利用率、简单实现和生产稳定性之间如何取舍。最后用观测指标或排障路径收束，说明如何判断方案真的有效。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

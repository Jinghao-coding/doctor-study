<div class="card card-m">
<h3>Workload 与 Controller：声明式系统的核心</h3>
<p>Workload 解决“如何管理一组 Pod”，Controller 解决“如何让实际状态持续逼近期望状态”。面试中不要只背 Deployment、StatefulSet、DaemonSet、Job 的用途，还要讲清楚 <strong>Informer → WorkQueue → Reconcile → 更新 status</strong> 这条控制循环。</p>
</div>

<div class="card card-s">
<h3>Pod 生命周期与探针</h3>
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
<h3>Workload 控制器选型</h3>
<table>
<tr><th>控制器</th><th>适合场景</th><th>关键机制</th><th>常见追问</th></tr>
<tr><td>Deployment</td><td>无状态服务</td><td>ReplicaSet、滚动发布、回滚</td><td>maxSurge / maxUnavailable 如何影响发布</td></tr>
<tr><td>StatefulSet</td><td>有状态服务</td><td>稳定网络身份、稳定存储、有序部署/删除</td><td>为什么常配 Headless Service 和 PVC</td></tr>
<tr><td>DaemonSet</td><td>每个节点一个 agent</td><td>节点新增自动补 Pod</td><td>CNI、日志采集、Device Plugin 为什么用它</td></tr>
<tr><td>Job</td><td>一次性任务</td><td>成功完成、失败重试、并行度</td><td>backoffLimit、completionMode、Indexed Job</td></tr>
<tr><td>CronJob</td><td>周期任务</td><td>按时间创建 Job</td><td>并发策略、错过调度、历史保留</td></tr>
</table>
</div>

<div class="card card-m">
<h3>Deployment 滚动发布链路</h3>
<ol>
<li>用户修改 Deployment template，例如镜像 tag。</li>
<li>Deployment Controller 发现 template hash 变化，创建新的 ReplicaSet。</li>
<li>按 <code>maxSurge</code> 增加新 Pod，按 <code>maxUnavailable</code> 减少旧 Pod。</li>
<li>新 Pod readiness 通过后才进入 Service endpoints，逐步承接流量。</li>
<li>旧 ReplicaSet 保留一定 revision，支持 <code>kubectl rollout undo</code> 回滚。</li>
</ol>
<p>发布排障要看 Deployment condition、ReplicaSet、Pod events、readiness probe、镜像拉取和应用日志。</p>
</div>

<div class="card card-s">
<h3>Controller Pattern：Informer、WorkQueue、Reconcile</h3>
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
<h3>CRD / Operator 面试重点</h3>
<p><strong>Operator = CRD + Controller + 领域运维逻辑。</strong>CRD 扩展 Kubernetes API，Controller 监听这些自定义资源并执行 reconcile，Operator 则把数据库、训练任务、推理服务等领域知识编码进控制循环。</p>
<table>
<tr><th>概念</th><th>含义</th><th>追问点</th></tr>
<tr><td>spec</td><td>用户声明的期望状态</td><td>不要在控制器里随意改用户 spec</td></tr>
<tr><td>status</td><td>系统观测到的实际状态</td><td>通常由 controller 写入</td></tr>
<tr><td>conditions</td><td>结构化状态条件</td><td>Ready、Progressing、Failed 等</td></tr>
<tr><td>OwnerReference</td><td>表达对象归属关系</td><td>用于级联删除和垃圾回收</td></tr>
<tr><td>Finalizer</td><td>删除前的清理钩子</td><td>清理外部资源，处理卡删除问题</td></tr>
<tr><td>Leader Election</td><td>多副本控制器只让一个活跃</td><td>保证 HA 与避免重复执行</td></tr>
</table>
</div>

<div class="card card-d">
<h3>AI 训练任务 Operator 如何设计</h3>
<ol>
<li>定义 TrainingJob CRD：包含镜像、worker 数、资源、队列、容错策略。</li>
<li>Controller watch TrainingJob，创建 worker Pod、Service、ConfigMap、Secret。</li>
<li>用 status.conditions 暴露 Pending、Running、Succeeded、Failed。</li>
<li>结合 Gang Scheduling 或 Kueue 控制整体入队和资源准入。</li>
<li>用 Finalizer 清理外部 checkpoint、临时 Service 或队列占用。</li>
</ol>
<p>边界要说清楚：Operator 管生命周期和业务编排，Scheduler Plugin 管 Pod/任务放到哪里，Device Plugin/DRA 管设备发现与交付。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 Controller 不直接 watch 后立刻处理对象，而要放 WorkQueue？</div>
<div class="qa-a"><p>WorkQueue 可以去重、限速、重试，并把事件接收和业务处理解耦。Informer 事件可能很频繁，如果直接处理容易阻塞 watch 回调，也不利于失败重试和并发控制。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Operator 和普通 Controller 有什么区别？</div>
<div class="qa-a"><p>普通 Controller 是 Kubernetes 控制模式，Operator 是把某个领域的运维知识封装成 CRD 与 Controller。例如数据库 Operator 不只是创建 Pod，还会处理备份、扩缩容、故障切换和版本升级。</p></div>
</div>

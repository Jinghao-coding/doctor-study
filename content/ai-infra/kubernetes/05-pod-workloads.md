<div class="card card-m">
<h3>Pod 生命周期：从提交到退出</h3>
<p>Pod 是 Kubernetes 最小调度单元，但真正运行的是 Pod 内的容器。面试里不要只说“Pod 被调度到节点”，而要把 API Server、Scheduler、kubelet、CRI、CNI、CSI 串起来。</p>
<table>
<tr><th>阶段</th><th>关键动作</th><th>常见状态/现象</th><th>面试要点</th></tr>
<tr><td>提交</td><td>用户通过 kubectl、控制器或 API 创建 Pod 对象</td><td>对象进入 API Server，写入 etcd</td><td>API Server 做认证、鉴权、准入、默认值填充和资源校验</td></tr>
<tr><td>调度</td><td>Scheduler 监听未绑定 Pod，执行 Filter/Score/Bind</td><td>Pending</td><td>Pending 可能是还没调度，也可能是调度失败或镜像还没拉取，要结合 Events 判断</td></tr>
<tr><td>节点接管</td><td>目标节点 kubelet watch 到 spec.nodeName 指向自己的 Pod</td><td>ContainerCreating</td><td>kubelet 不是被 scheduler 直接调用，而是 watch API Server</td></tr>
<tr><td>准备运行</td><td>拉镜像、挂载 volume、配置网络、调用 CRI 创建容器</td><td>ContainerCreating / ImagePullBackOff</td><td>网络由 CNI 负责，存储由 CSI 或内置 volume plugin 负责</td></tr>
<tr><td>运行</td><td>容器进程启动，探针开始工作，kubelet 持续上报状态</td><td>Running / Ready</td><td>Running 不等于可接流量，Ready 才会进入 Service endpoints</td></tr>
<tr><td>终止</td><td>删除 Pod 后进入优雅终止：PreStop、SIGTERM、terminationGracePeriodSeconds、SIGKILL</td><td>Terminating</td><td>优雅终止影响滚动发布、抢占、drain 和服务无损下线</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Pod Phase 与 Container State</h3>
<p>Pod 的状态经常被混淆。Pod phase 是 Pod 级别的粗粒度状态，Container state 是容器级别的状态。排查问题时要结合 <code>kubectl describe pod</code>、Events、containerStatuses、日志一起看。</p>
<table>
<tr><th>概念</th><th>典型取值</th><th>解释</th><th>排查意义</th></tr>
<tr><td>Pod Phase</td><td>Pending、Running、Succeeded、Failed、Unknown</td><td>Pod 生命周期的高层状态</td><td>只能粗略判断阶段，不能直接定位根因</td></tr>
<tr><td>Container State</td><td>Waiting、Running、Terminated</td><td>单个容器当前状态</td><td>Waiting reason 常见为 ImagePullBackOff、CrashLoopBackOff、CreateContainerConfigError</td></tr>
<tr><td>Pod Conditions</td><td>PodScheduled、Initialized、ContainersReady、Ready</td><td>由 kubelet 和控制面维护的条件集合</td><td>Ready 决定是否进入 Service endpoints</td></tr>
<tr><td>Events</td><td>FailedScheduling、Pulled、Created、Started、BackOff</td><td>关键事件流水</td><td>面试和生产排查中最先看的信息之一</td></tr>
</table>
</div>

<div class="card card-w">
<h3>探针：liveness / readiness / startup</h3>
<p>探针是 Pod 稳定性面试最高频内容之一。核心是区分“进程是否活着”和“是否可以接流量”。错误配置探针会导致服务抖动、滚动发布卡住或流量打到未初始化实例。</p>
<table>
<tr><th>探针</th><th>判断什么</th><th>失败后行为</th><th>适用场景</th></tr>
<tr><td>livenessProbe</td><td>容器是否还活着</td><td>kubelet 重启容器</td><td>死锁、进程假死、主循环卡住</td></tr>
<tr><td>readinessProbe</td><td>容器是否可以接流量</td><td>从 Service endpoints 移除，不重启容器</td><td>依赖未就绪、模型未加载、缓存预热中</td></tr>
<tr><td>startupProbe</td><td>慢启动应用是否完成启动</td><td>失败超过阈值后重启容器；成功前抑制 liveness/readiness</td><td>Java 大应用、模型服务加载权重、初始化时间长</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: readinessProbe 和 livenessProbe 配错会怎样？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">readiness 配得太严</div><p>实例会长期不进入 endpoints，Deployment 可能滚动发布卡住，Service 没有足够后端。</p></div>
<div class="qa-section"><div class="qa-section-title">liveness 配得太严</div><p>应用初始化或短暂抖动时被 kubelet 频繁重启，形成 CrashLoopBackOff。</p></div>
<div class="qa-summary">面试记忆：readiness 控流量，liveness 控重启，startup 保护慢启动。</div>
</div>
</div>
</div>

<div class="card card-m">
<h3>Workload 控制器对比</h3>
<p>控制器的本质是 Reconcile loop：不断比较期望状态和实际状态，并把实际状态收敛到期望状态。面试中经常要求解释不同 Workload 为什么存在，以及如何选择。</p>
<table>
<tr><th>控制器</th><th>核心语义</th><th>典型场景</th><th>面试重点</th></tr>
<tr><td>ReplicaSet</td><td>保证指定数量 Pod 副本</td><td>通常由 Deployment 管理，不直接手写</td><td>Deployment 通过 ReplicaSet 实现版本切换</td></tr>
<tr><td>Deployment</td><td>无状态服务滚动发布、回滚、扩缩容</td><td>Web 服务、API 服务、无状态模型服务</td><td>maxSurge、maxUnavailable、rollout、rollback</td></tr>
<tr><td>StatefulSet</td><td>稳定网络标识、稳定存储、有序部署和删除</td><td>数据库、ZooKeeper、分布式训练 worker 固定身份</td><td>Pod 名称有序，配合 Headless Service 和 PVC template</td></tr>
<tr><td>DaemonSet</td><td>每个或部分节点运行一个 Pod</td><td>日志采集、监控 agent、CNI、CSI、GPU device plugin</td><td>适合节点级守护进程，新增节点自动部署</td></tr>
<tr><td>Job</td><td>运行到完成的一次性任务</td><td>离线处理、数据迁移、一次性训练任务</td><td>completions、parallelism、backoffLimit</td></tr>
<tr><td>CronJob</td><td>按时间周期创建 Job</td><td>定时清理、周期报表、定时数据任务</td><td>concurrencyPolicy、startingDeadlineSeconds</td></tr>
</table>
</div>

<div class="card card-d">
<h3>滚动发布、回滚与无损下线</h3>
<p>Deployment 发布机制是基础设施面试常问的工程题。要说明流量如何从旧版本迁到新版本，以及如何避免把流量打到未就绪或正在退出的 Pod。</p>
<div class="comp-grid">
<div class="comp-item"><div class="comp-name">maxSurge</div><div class="comp-role">滚动发布时允许额外创建的新 Pod 数量或比例。</div><div class="comp-detail">提高 maxSurge 可以加快发布，但会临时占用更多资源。</div></div>
<div class="comp-item"><div class="comp-name">maxUnavailable</div><div class="comp-role">发布过程中允许不可用的 Pod 数量或比例。</div><div class="comp-detail">设置过高会影响可用性，设置为 0 通常要求先拉起新实例再下线旧实例。</div></div>
<div class="comp-item"><div class="comp-name">readinessProbe</div><div class="comp-role">新 Pod Ready 后才进入 Service endpoints。</div><div class="comp-detail">模型服务常用 readiness 等待模型权重加载完成。</div></div>
<div class="comp-item"><div class="comp-name">preStop + SIGTERM</div><div class="comp-role">删除旧 Pod 前先执行钩子并发送终止信号。</div><div class="comp-detail">应用应停止接新请求、等待存量请求完成，再退出。</div></div>
</div>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何解释一次 Deployment 滚动发布？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">版本控制</div><p>Deployment 创建新的 ReplicaSet，并逐步增加新 ReplicaSet 的副本数，同时减少旧 ReplicaSet 的副本数。</p></div>
<div class="qa-section"><div class="qa-section-title">可用性控制</div><p>maxSurge 控制可额外创建多少新 Pod，maxUnavailable 控制最多允许多少 Pod 不可用。</p></div>
<div class="qa-section"><div class="qa-section-title">流量控制</div><p>只有 readinessProbe 成功的 Pod 才会进入 Service endpoints；删除旧 Pod 时依赖 PreStop 和 terminationGracePeriodSeconds 做无损下线。</p></div>
</div>
</div>
</div>

<div class="card card-s">
<h3>StatefulSet 与 AI 训练</h3>
<p>StatefulSet 不只用于数据库，也常用于需要稳定身份的分布式训练和参数服务器架构。它保证 Pod 名称稳定，例如 <code>trainer-0</code>、<code>trainer-1</code>，配合 Headless Service 可以让 worker 之间互相发现。</p>
<table>
<tr><th>能力</th><th>StatefulSet 表现</th><th>为什么重要</th></tr>
<tr><td>稳定 Pod 名称</td><td>按 ordinal 命名：name-0、name-1、name-2</td><td>训练任务可用 ordinal 推导 rank</td></tr>
<tr><td>稳定网络身份</td><td>配合 Headless Service 得到稳定 DNS</td><td>worker 可通过 DNS 互相发现</td></tr>
<tr><td>稳定存储</td><td>volumeClaimTemplates 为每个 Pod 创建独立 PVC</td><td>有状态服务重启后仍挂回自己的存储</td></tr>
<tr><td>有序启动/删除</td><td>默认按 ordinal 顺序处理</td><td>适合需要主从顺序或成员发现的系统</td></tr>
</table>
</div>

<div class="card card-d">
<h3>官方参考</h3>
<div class="resource-grid">
<a class="resource-card" href="https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/"><div class="resource-type">official</div><div class="resource-title">Pod Lifecycle</div><div class="resource-desc">Pod phase、conditions、container states、restart policy 等生命周期基础。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/"><div class="resource-type">official</div><div class="resource-title">Liveness / Readiness / Startup Probes</div><div class="resource-desc">三类探针配置、行为差异和常见使用方式。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/workloads/controllers/deployment/"><div class="resource-type">official</div><div class="resource-title">Deployment</div><div class="resource-desc">滚动发布、回滚、扩缩容、ReplicaSet 关系。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/"><div class="resource-type">official</div><div class="resource-title">StatefulSet</div><div class="resource-desc">稳定身份、稳定存储、有序部署删除。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/"><div class="resource-type">official</div><div class="resource-title">DaemonSet</div><div class="resource-desc">节点级守护进程，常见于 CNI、CSI、日志采集、device plugin。</div></a>
</div>
</div>

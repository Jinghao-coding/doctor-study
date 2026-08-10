<div class="card card-m">
<h3>Pod 生命周期不是一条 phase 状态机</h3>
<p><code>status.phase</code> 只是 Pod 的粗粒度摘要；排障时必须同时看容器状态、Pod Conditions、Events 和 <code>kubectl</code> 展示的 STATUS。<code>CrashLoopBackOff</code>、<code>ContainerCreating</code>、<code>Terminating</code> 都不是 Pod phase。</p>
<table>
<tr><th>Pod phase</th><th>准确语义</th><th>常见现场</th></tr>
<tr><td><code>Pending</code></td><td>对象已被集群接受，但至少一个容器尚未完成设置并准备运行</td><td>等待调度、拉镜像、挂载卷、创建 sandbox</td></tr>
<tr><td><code>Running</code></td><td>已绑定 Node，所有容器已创建，至少一个容器正在运行或启动/重启中</td><td>业务可能仍未 Ready，也可能正在 CrashLoop</td></tr>
<tr><td><code>Succeeded</code></td><td>所有容器成功终止，并且不会再重启</td><td>Job 的 Pod 正常完成</td></tr>
<tr><td><code>Failed</code></td><td>所有容器均已终止，至少一个失败终止，且不会自动重启</td><td>退出码非 0、被系统终止、Pod 级失败</td></tr>
<tr><td><code>Unknown</code></td><td>控制面无法取得 Pod 状态</td><td>常见于 API Server 与目标 Node 通信异常</td></tr>
</table>
</div>

<div class="card card-s">
<h3>四层状态必须分开看</h3>
<table>
<tr><th>层次</th><th>典型字段</th><th>回答什么问题</th></tr>
<tr><td>Pod phase</td><td><code>status.phase</code></td><td>Pod 当前处于哪类粗粒度阶段</td></tr>
<tr><td>Container state</td><td><code>Waiting / Running / Terminated</code>、<code>lastState</code>、exit code</td><td>某个容器为什么没运行、退出或反复重启</td></tr>
<tr><td>Pod Conditions</td><td><code>PodScheduled</code>、<code>Initialized</code>、<code>PodReadyToStartContainers</code>、<code>ContainersReady</code>、<code>Ready</code></td><td>调度、初始化、sandbox/网络/卷、容器就绪分别完成没有</td></tr>
<tr><td>展示与事件</td><td><code>kubectl get</code> STATUS、Events</td><td><code>ImagePullBackOff</code>、<code>CrashLoopBackOff</code> 等可操作原因</td></tr>
</table>
<div class="qa-summary"><code>Running ≠ Ready</code>：Running 只描述生命周期阶段；只有 <code>Ready=True</code> 且满足自定义 readiness gates，Pod 才应进入匹配 Service 的正常负载均衡池。</div>
</div>

<div class="card card-d">
<h3>从绑定到 Ready 的节点侧链路</h3>
<div class="flow" role="list" aria-label="Pod 从绑定到 Ready 的节点侧流程">
<div class="flow-step" role="listitem"><div class="flow-index">01</div><div class="flow-title">PodScheduled</div><div class="flow-desc">scheduler 完成 Binding</div></div>
<div class="flow-step" role="listitem"><div class="flow-index">02</div><div class="flow-title">节点准入与资源准备</div><div class="flow-desc">kubelet admission、CSI volume、设备资源</div></div>
<div class="flow-step" role="listitem"><div class="flow-index">03</div><div class="flow-title">Sandbox 与网络</div><div class="flow-desc">CRI RunPodSandbox，runtime 调 CNI</div></div>
<div class="flow-step" role="listitem"><div class="flow-index">04</div><div class="flow-title">初始化</div><div class="flow-desc">init container 依次完成</div></div>
<div class="flow-step" role="listitem"><div class="flow-index">05</div><div class="flow-title">业务容器就绪</div><div class="flow-desc">启动容器，探针与 readiness gates 通过</div></div>
</div>
<p><code>PodReadyToStartContainers=True</code> 表示 sandbox 已创建、网络已配置、所需卷已挂载，动态资源也已分配；它比只看 <code>ContainerCreating</code> 更能定位节点准备阶段卡在哪里。</p>
</div>

<div class="card card-w">
<h3>三类探针的动作边界</h3>
<table>
<tr><th>探针</th><th>失败后的动作</th><th>适合检测</th><th>常见错误</th></tr>
<tr><td><code>startupProbe</code></td><td>达到失败阈值后杀容器并按 restartPolicy 处理；成功前不执行 liveness/readiness</td><td>模型加载、JVM 启动、数据恢复等慢启动</td><td>窗口短于真实最慢启动时间</td></tr>
<tr><td><code>livenessProbe</code></td><td>达到失败阈值后由 kubelet 重启容器</td><td>死锁、永久失活</td><td>把下游依赖抖动当成自身不可恢复故障，形成重启风暴</td></tr>
<tr><td><code>readinessProbe</code></td><td>标记容器/Pod NotReady，不重启容器；EndpointSlice 不再把它作为普通就绪端点</td><td>预热未完成、临时过载、依赖暂不可用</td><td>与 liveness 使用同样严格的判定，扩大故障</td></tr>
</table>
<p>readiness 还可以由 <code>spec.readinessGates</code> 增加自定义条件。此时容器都 Ready 仍不够，所有 readiness gate 对应的 PodCondition 也必须为 <code>True</code>。</p>
</div>

<div class="card card-s">
<h3>restartPolicy、退避与“谁在重试”</h3>
<table>
<tr><th>机制</th><th>执行者</th><th>作用范围</th><th>关键语义</th></tr>
<tr><td><code>restartPolicy: Always</code></td><td>kubelet</td><td>同一 Pod 内的容器</td><td>无论退出码如何都重启；Deployment 等长期服务默认只允许这一语义</td></tr>
<tr><td><code>OnFailure</code></td><td>kubelet</td><td>同一 Pod 内的容器</td><td>仅失败退出时重启；Job 可用</td></tr>
<tr><td><code>Never</code></td><td>kubelet</td><td>同一 Pod 内的容器</td><td>容器退出后不在原 Pod 重启；Job Controller 可创建替代 Pod</td></tr>
<tr><td><code>CrashLoopBackOff</code></td><td>kubelet</td><td>容器重启节流</td><td>表示容器反复失败后的指数退避，不是 Pod phase</td></tr>
</table>
<div class="qa-summary">先分清两层重试：kubelet 根据 <code>restartPolicy</code> 在原 Pod 内重启容器；Job Controller 根据 Job 失败策略决定是否创建新的 Pod。</div>
</div>

<div class="card card-r">
<h3>删除与优雅终止</h3>
<ol>
<li>API 对象写入 <code>deletionTimestamp</code>，端点就绪条件被更新，常规流量不应再进入该 Pod。</li>
<li>kubelet 执行容器的 <code>preStop</code> hook（如果配置），随后让 runtime 向容器主进程发送终止信号。</li>
<li>应用在 <code>terminationGracePeriodSeconds</code> 内停止接流量、完成在途请求并刷盘。</li>
<li>宽限期耗尽后，剩余进程会被强制终止；kubelet 完成本地清理，API 对象最终删除。</li>
</ol>
<p><strong>边界：</strong><code>preStop</code> 会占用终止宽限期；强制删除、节点失联或进程不处理终止信号时，不能假设一定完成优雅退出。</p>
</div>

<div class="card card-d">
<h3>常用 Workload 语义压缩</h3>
<table>
<tr><th>对象</th><th>控制目标</th><th>最关键的身份/完成语义</th></tr>
<tr><td>Deployment</td><td>维持可替换副本并滚动发布</td><td>Pod 可互换；通过 ReplicaSet 管副本</td></tr>
<tr><td>StatefulSet</td><td>维持有序且身份稳定的副本集合</td><td>ordinal、稳定网络身份、可选的每副本 PVC</td></tr>
<tr><td>DaemonSet</td><td>覆盖所有或部分符合条件的 Node</td><td>控制目标是 Node 覆盖率，不是固定副本数</td></tr>
<tr><td>Job</td><td>达到成功完成条件后停止</td><td>completion、失败重试、可重复执行容忍</td></tr>
<tr><td>CronJob</td><td>按近似时间表创建 Job</td><td>并发策略、错过调度、幂等性</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod 是 Running，为什么 Service 仍然没有流量？</div>
<div class="qa-a">
<p>先看 <code>Ready</code> 和 <code>ContainersReady</code>，再看 readiness probe、readiness gates 与 EndpointSlice。Running 只说明容器已经创建且至少一个仍在运行或启动/重启；预热未完成、readiness 失败或自定义 gate 未满足时，Pod 仍不应接普通流量。</p>
<div class="qa-summary">排查顺序：Pod Conditions → probe 结果与 Events → EndpointSlice 的 ready/serving/terminating 条件 → Service selector。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pending、ContainerCreating、CrashLoopBackOff 分别偏哪一段？</div>
<div class="qa-a">
<p><code>Pending</code> 是 Pod phase，覆盖未调度和节点准备阶段；<code>ContainerCreating</code> 是 kubectl 常见展示原因，通常偏卷、sandbox、CNI、镜像等节点准备；<code>CrashLoopBackOff</code> 表示容器已尝试启动但反复失败，重点看 lastState、exit code、日志、命令和探针。</p>
</div>
</div>

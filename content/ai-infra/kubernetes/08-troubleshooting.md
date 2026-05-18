<div class="card card-m">
<h3>排查总方法：先分层，再定位</h3>
<p>Kubernetes 故障排查不要一上来就猜。面试中推荐按对象状态、事件、日志、资源、网络、存储、节点这几层递进。</p>
<table>
<tr><th>层次</th><th>常用命令</th><th>看什么</th><th>常见结论</th></tr>
<tr><td>对象状态</td><td>kubectl get pod -o wide</td><td>phase、node、restart、age、IP</td><td>确认是 Pending、Running 但不 Ready、CrashLoop 还是 Terminating</td></tr>
<tr><td>事件</td><td>kubectl describe pod</td><td>Events、conditions、container state reason</td><td>FailedScheduling、FailedMount、ImagePullBackOff、BackOff</td></tr>
<tr><td>日志</td><td>kubectl logs / logs --previous</td><td>应用启动日志、退出前日志</td><td>应用崩溃、配置错误、依赖不可达</td></tr>
<tr><td>资源</td><td>kubectl top、describe node、quota</td><td>requests、limits、allocatable、quota</td><td>资源不足、namespace 配额不足、OOM</td></tr>
<tr><td>网络</td><td>nslookup、curl、tcpdump、endpoints</td><td>DNS、Service、Pod IP、NetworkPolicy</td><td>DNS 不通、Service 没 endpoints、策略阻断</td></tr>
<tr><td>存储</td><td>get pvc/pv、describe pvc、CSI logs</td><td>绑定、attach、mount</td><td>PVC Pending、FailedMount、zone 冲突</td></tr>
<tr><td>节点</td><td>describe node、kubelet logs、runtime logs</td><td>NodeReady、DiskPressure、MemoryPressure</td><td>节点不可用、磁盘压力、kubelet 异常</td></tr>
</table>
</div>

<div class="card card-w">
<h3>Pod Pending 排查</h3>
<p>Pending 不是单一问题，它可能发生在调度前、调度失败、PVC 未绑定、镜像拉取前等待等多个阶段。最可靠入口是 <code>kubectl describe pod</code> 里的 Events。</p>
<div class="comp-grid">
<div class="comp-item"><div class="comp-name">FailedScheduling</div><div class="comp-role">调度器无法找到合适节点。</div><div class="comp-detail">检查 CPU/Memory/GPU requests、nodeSelector、affinity、taints、topology spread、quota。</div></div>
<div class="comp-item"><div class="comp-name">PVC Pending</div><div class="comp-role">Pod 引用的 PVC 尚未绑定。</div><div class="comp-detail">检查 StorageClass、PV 绑定、CSI provisioner、WaitForFirstConsumer、zone。</div></div>
<div class="comp-item"><div class="comp-name">Unschedulable</div><div class="comp-role">调度硬约束无法满足。</div><div class="comp-detail">重点看 Events 中 scheduler 给出的节点过滤原因。</div></div>
<div class="comp-item"><div class="comp-name">GPU Pending</div><div class="comp-role">GPU 扩展资源不足或未上报。</div><div class="comp-detail">检查 nvidia-device-plugin、node allocatable、MIG 配置、资源名是否一致。</div></div>
</div>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod 一直 Pending，你怎么回答排查流程？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">先看事件</div><p>先 describe pod，看 Events 是否是 FailedScheduling、FailedMount、PVC Pending 或 quota 限制。</p></div>
<div class="qa-section"><div class="qa-section-title">再看资源和约束</div><p>如果是调度失败，检查 requests、节点 allocatable、taints/tolerations、nodeSelector、affinity、topologySpreadConstraints。</p></div>
<div class="qa-section"><div class="qa-section-title">专项检查</div><p>如果是 GPU Pod，检查 device plugin 和 nvidia.com/gpu 上报；如果是有状态 Pod，检查 PVC/PV/StorageClass。</p></div>
<div class="qa-summary">面试顺序：Events → 资源 → 调度约束 → PVC/存储 → GPU/device plugin → scheduler 日志。</div>
</div>
</div>
</div>

<div class="card card-r">
<h3>CrashLoopBackOff 排查</h3>
<p>CrashLoopBackOff 表示容器启动后不断退出，kubelet 按退避策略重启容器。不要只看当前日志，还要看上一次崩溃前的日志。</p>
<table>
<tr><th>方向</th><th>命令/信息</th><th>可能原因</th><th>处理思路</th></tr>
<tr><td>退出码</td><td>containerStatuses.lastState.terminated.exitCode</td><td>非 0 退出、信号终止</td><td>结合应用日志定位异常</td></tr>
<tr><td>上次日志</td><td>kubectl logs pod -c container --previous</td><td>当前容器已重启，当前日志不完整</td><td>查看崩溃前堆栈和错误</td></tr>
<tr><td>配置错误</td><td>env、configMap、secret、command、args</td><td>缺少配置、参数错误、启动命令错误</td><td>核对 Deployment spec 和配置版本</td></tr>
<tr><td>探针误杀</td><td>describe pod events</td><td>livenessProbe 过早或过严</td><td>增加 startupProbe，调大 initialDelay/failureThreshold</td></tr>
<tr><td>OOMKilled</td><td>reason=OOMKilled</td><td>内存 limit 太小或内存泄漏</td><td>调高 limit、分析内存、检查 QoS</td></tr>
</table>
</div>

<div class="card card-w">
<h3>ImagePullBackOff / ErrImagePull</h3>
<p>镜像拉取失败通常与镜像名、tag、仓库权限、网络、镜像架构有关。BackOff 表示 kubelet 已经失败过并进入退避重试。</p>
<table>
<tr><th>原因</th><th>表现</th><th>排查</th></tr>
<tr><td>镜像名或 tag 错误</td><td>manifest not found</td><td>核对 image 字段和镜像仓库 tag</td></tr>
<tr><td>私有仓库无权限</td><td>unauthorized / denied</td><td>检查 imagePullSecrets、ServiceAccount、仓库权限</td></tr>
<tr><td>节点网络不通</td><td>timeout / connection refused</td><td>在节点侧检查 DNS、代理、仓库连通性</td></tr>
<tr><td>架构不匹配</td><td>exec format error 或拉取失败</td><td>检查 amd64/arm64 镜像 manifest</td></tr>
<tr><td>拉取策略</td><td>使用旧镜像或每次都拉</td><td>理解 imagePullPolicy: Always / IfNotPresent / Never</td></tr>
</table>
</div>

<div class="card card-m">
<h3>Service 不通排查</h3>
<p>Service 不通要拆成 DNS、Service 抽象、Endpoint、Pod 本身、NetworkPolicy、节点转发规则几层。</p>
<ol>
<li>确认 Service 存在：<code>kubectl get svc</code>。</li>
<li>确认 Service selector 能选中 Pod：检查 label 和 selector 是否匹配。</li>
<li>确认 EndpointSlice 有后端：<code>kubectl get endpointslice</code>。</li>
<li>确认 Pod Ready：未 Ready 的 Pod 不会进入 endpoints。</li>
<li>在同 namespace 内用 service name 测试 DNS。</li>
<li>绕过 DNS 直接访问 ClusterIP。</li>
<li>绕过 Service 直接访问 Pod IP 和 containerPort。</li>
<li>检查 NetworkPolicy、kube-proxy、CNI 和节点防火墙。</li>
</ol>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Service 有 ClusterIP 但没有流量，最常见是什么？</div>
<div class="qa-a">
<div class="qa-grid"><div class="qa-mini"><strong>selector 不匹配</strong>Service 没有选中任何 Pod，EndpointSlice 为空。</div><div class="qa-mini"><strong>Pod 未 Ready</strong>Pod Running 但 readiness 失败，不进入 endpoints。</div><div class="qa-mini"><strong>targetPort 错误</strong>Service 转发到错误端口。</div><div class="qa-mini"><strong>网络策略阻断</strong>NetworkPolicy 或 CNI 策略拒绝访问。</div></div>
</div>
</div>
</div>

<div class="card card-s">
<h3>Node NotReady 排查</h3>
<table>
<tr><th>方向</th><th>看什么</th><th>典型原因</th></tr>
<tr><td>Node Conditions</td><td>Ready、MemoryPressure、DiskPressure、PIDPressure、NetworkUnavailable</td><td>节点资源压力、网络不可用</td></tr>
<tr><td>kubelet</td><td>kubelet 进程和日志</td><td>kubelet crash、证书过期、无法访问 API Server</td></tr>
<tr><td>容器运行时</td><td>containerd/docker 状态</td><td>runtime 挂死、镜像存储异常</td></tr>
<tr><td>CNI</td><td>CNI DaemonSet、节点网络</td><td>CNI 插件异常导致 NetworkUnavailable</td></tr>
<tr><td>磁盘</td><td>imagefs/nodefs 使用率</td><td>镜像太多、日志太多、磁盘压力触发驱逐</td></tr>
</table>
</div>

<div class="card card-d">
<h3>HPA / VPA / PDB / drain 排查点</h3>
<table>
<tr><th>对象</th><th>常见问题</th><th>排查要点</th></tr>
<tr><td>HPA</td><td>不扩容或扩容异常</td><td>metrics-server 是否正常、目标指标是否存在、requests 是否设置、冷却窗口</td></tr>
<tr><td>VPA</td><td>推荐值不符合预期或驱逐重建</td><td>推荐模式、updateMode、历史样本、和 HPA 是否冲突</td></tr>
<tr><td>PDB</td><td>节点 drain 卡住</td><td>minAvailable/maxUnavailable 是否过严，当前可用副本是否不足</td></tr>
<tr><td>drain</td><td>Pod 无法驱逐</td><td>DaemonSet、local storage、PDB、静态 Pod、有状态服务</td></tr>
</table>
</div>

<div class="card card-d">
<h3>官方参考</h3>
<div class="resource-grid">
<a class="resource-card" href="https://kubernetes.io/docs/tasks/debug/"><div class="resource-type">official</div><div class="resource-title">Debug Applications</div><div class="resource-desc">Kubernetes 官方调试任务入口。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/"><div class="resource-type">official</div><div class="resource-title">Debug Pods</div><div class="resource-desc">Pod 状态、日志、事件、exec 调试。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/tasks/debug/debug-cluster/"><div class="resource-type">official</div><div class="resource-title">Debug Clusters</div><div class="resource-desc">集群和节点级排查。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/workloads/pods/disruptions/"><div class="resource-type">official</div><div class="resource-title">Disruptions</div><div class="resource-desc">自愿/非自愿中断、PDB 和 drain 相关概念。</div></a>
</div>
</div>

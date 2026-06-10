<div class="card card-m">
<h3>故障排查总方法：从症状反推链路</h3>
<p>Kubernetes 排障不要一上来背命令，而要按链路拆：<strong>API 对象是否存在 → 调度是否成功 → kubelet 是否执行 → 网络/存储是否就绪 → 应用是否健康 → 控制器是否持续修正。</strong></p>
<ol>
<li>先看状态：<code>kubectl get</code>、<code>kubectl describe</code>、Events。</li>
<li>再看控制器：Deployment/ReplicaSet/Job/StatefulSet 的 conditions。</li>
<li>再看节点：Node condition、kubelet、container runtime、CNI、CSI。</li>
<li>再看应用：容器日志、探针、启动参数、依赖服务。</li>
<li>最后看系统性问题：资源压力、API Server、etcd、scheduler、网络插件、存储后端。</li>
</ol>
</div>

<div class="card card-s">
<h3>高频故障速查</h3>
<table>
<tr><th>症状</th><th>优先看什么</th><th>常见原因</th><th>定位方向</th></tr>
<tr><td>Pod Pending</td><td>Pod Events、scheduler 日志</td><td>资源不足、污点、亲和性、PVC、配额、DRA claim</td><td>调度与准入链路</td></tr>
<tr><td>ContainerCreating</td><td>Events、kubelet 日志</td><td>镜像、CNI、CSI mount、sandbox 创建失败</td><td>节点执行链路</td></tr>
<tr><td>CrashLoopBackOff</td><td>容器日志、退出码、探针</td><td>程序启动失败、配置错误、依赖不可用、liveness 过激</td><td>应用与探针</td></tr>
<tr><td>ImagePullBackOff</td><td>Events、镜像仓库、Secret</td><td>镜像不存在、权限错误、网络不可达</td><td>镜像拉取链路</td></tr>
<tr><td>Service 不通</td><td>Service、EndpointSlice、readiness、DNS</td><td>selector 错、无 endpoints、网络策略、kube-proxy/CNI</td><td>网络链路</td></tr>
<tr><td>Node NotReady</td><td>Node conditions、kubelet、runtime</td><td>节点宕机、磁盘/内存压力、网络异常、证书问题</td><td>节点健康</td></tr>
<tr><td>PVC Pending</td><td>PVC Events、StorageClass、CSI</td><td>StorageClass 不存在、容量不足、拓扑不匹配、provisioner 异常</td><td>存储链路</td></tr>
</table>
</div>

<div class="card card-w">
<h3>Pod Pending 深入排查</h3>
<ol>
<li>看 <code>kubectl describe pod</code> 中 FailedScheduling 的具体原因。</li>
<li>如果是资源不足，对比 Pod requests 和 Node allocatable，注意 DaemonSet、系统预留和碎片。</li>
<li>如果是污点，检查 tolerations；如果是亲和性，检查 nodeSelector、nodeAffinity、podAffinity。</li>
<li>如果是 PVC，检查 PVC 是否 Bound，StorageClass 的 <code>volumeBindingMode</code> 和存储拓扑。</li>
<li>如果是配额，检查 ResourceQuota、LimitRange、队列配额。</li>
<li>如果是 GPU，检查扩展资源、Device Plugin、DRA ResourceClaim/ResourceSlice。</li>
<li>必要时查看 scheduler 日志和调度器 profile/plugin 配置。</li>
</ol>
</div>

<div class="card card-d">
<h3>CrashLoopBackOff 与 ImagePullBackOff</h3>
<table>
<tr><th>问题</th><th>关键观察</th><th>处理思路</th></tr>
<tr><td>CrashLoopBackOff</td><td><code>kubectl logs --previous</code>、退出码、启动耗时</td><td>修配置、依赖、启动命令；区分应用崩溃和探针杀死</td></tr>
<tr><td>OOMKilled</td><td>last state、内存 limit、应用内存曲线</td><td>调大 limit、修内存泄漏、优化 batch size</td></tr>
<tr><td>Probe failed</td><td>liveness/readiness/startup 配置</td><td>慢启动用 startupProbe，readiness 不应导致重启</td></tr>
<tr><td>ImagePullBackOff</td><td>Events 中的 registry 错误</td><td>检查镜像名、tag、Secret、仓库网络、证书</td></tr>
<tr><td>ErrImagePull</td><td>首次拉取失败</td><td>修复后 kubelet 会重试，或删除 Pod 触发重建</td></tr>
</table>
</div>

<div class="card card-m">
<h3>稳定性治理：HPA / VPA / PDB / drain</h3>
<table>
<tr><th>机制</th><th>解决什么问题</th><th>注意点</th></tr>
<tr><td>HPA</td><td>按指标水平扩缩副本</td><td>依赖 metrics，扩缩容要结合 readiness 和冷启动</td></tr>
<tr><td>VPA</td><td>推荐或调整单 Pod 资源</td><td>自动模式可能重建 Pod，和 HPA 同时使用要谨慎</td></tr>
<tr><td>PDB</td><td>限制自愿驱逐时不可用副本数</td><td>不能阻止节点故障，只影响 drain/升级等自愿驱逐</td></tr>
<tr><td>drain</td><td>节点维护前驱逐 Pod</td><td>受 PDB、DaemonSet、emptyDir、本地盘影响</td></tr>
<tr><td>TopologySpread</td><td>让副本跨节点/可用区分散</td><td>提高容灾，避免热点</td></tr>
</table>
</div>

<div class="card card-s">
<h3>大规模集群稳定性关注点</h3>
<table>
<tr><th>层面</th><th>风险</th><th>治理手段</th></tr>
<tr><td>API Server</td><td>高 QPS、watch 风暴、大对象膨胀</td><td>限流、分页、合理 watch、减少频繁 status 更新</td></tr>
<tr><td>etcd</td><td>存储膨胀、慢查询、碎片、磁盘延迟</td><td>监控 fsync、compact、defrag、备份恢复演练</td></tr>
<tr><td>scheduler</td><td>调度队列堆积、插件耗时、资源碎片</td><td>profile 优化、批调度准入、减少复杂亲和性</td></tr>
<tr><td>节点</td><td>kubelet 压力、镜像拉取风暴、磁盘压力</td><td>镜像预热、系统预留、节点池隔离、驱逐阈值</td></tr>
<tr><td>网络</td><td>连接数、DNS QPS、Service 规模、策略复杂</td><td>CoreDNS 扩容、NodeLocal DNSCache、eBPF 可观测</td></tr>
<tr><td>AI 训练</td><td>Gang 任务占用大量资源、失败重试风暴</td><td>队列准入、配额、checkpoint、失败退避、作业优先级</td></tr>
</table>
</div>

<div class="card card-m">

<h3>故障排查与稳定性高频问答</h3>

<p>本模块的问答按“概念 → 作用 → 链路/排查 → 面试口径”组织，避免只背一段结论。</p>

</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod Pending 你会怎么排查？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 先定位阶段</div><p>Pending 可能卡在调度、PVC、配额、准入或镜像前准备阶段，先看 Pod Events 确认具体原因。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 调度失败</div><p>如果是 FailedScheduling，检查 requests、Node allocatable、污点容忍、亲和性、拓扑约束、优先级抢占。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 依赖未满足</div><p>如果事件指向 PVC、ResourceClaim、Quota、LimitRange 或队列准入，就去对应模块看存储、DRA、配额和批调度。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 节点执行前问题</div><p>如果已经绑定但仍 Pending/ContainerCreating，检查 kubelet、CNI、CSI、container runtime、镜像拉取和 sandbox 创建。</p></div>
<div class="qa-summary">面试口径：Pending 不是单一问题，要先看 Events 判断卡在调度、存储、配额、设备还是节点执行链路。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CrashLoopBackOff 怎么排查？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 理解概念</div><p>CrashLoopBackOff 表示容器反复启动失败，kubelet 正在按退避策略重启它；它是结果，不是根因。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 先看日志和退出码</div><p>看 <code>kubectl logs</code> 和 <code>kubectl logs --previous</code>，再看 lastState、exitCode、reason、启动命令和参数。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 区分常见根因</div><p>配置错误、依赖不可达、启动命令错误、权限问题、镜像入口错误、OOMKilled、应用主动退出都可能导致循环重启。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 检查探针</div><p>livenessProbe 过激会把慢启动应用杀死；慢启动应使用 startupProbe，readiness 失败不应导致重启。</p></div>
<div class="qa-summary">面试口径：CrashLoopBackOff 按“日志/退出码 → 配置和依赖 → OOM → 探针”排查，先找容器为什么退出。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Node NotReady 怎么排查？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 看 Node conditions</div><p>先看 Ready、MemoryPressure、DiskPressure、PIDPressure、NetworkUnavailable，判断是资源压力还是节点不可达。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 看节点侧组件</div><p>登录节点检查 kubelet、container runtime、CNI、磁盘、内存、网络、证书和系统日志。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 看控制面连接</div><p>确认 API Server 能否收到节点心跳，网络、防火墙、证书过期、kubelet bootstrap 都可能影响上报。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 看影响面</div><p>评估该节点上的 Pod 是否 Unknown/Terminating，是否需要 cordon、drain、重建或等待节点恢复。</p></div>
<div class="qa-summary">面试口径：Node NotReady 先看 conditions，再查 kubelet/runtime/CNI/资源压力和控制面连通性，最后评估 Pod 迁移影响。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 大规模集群为什么要关注 watch 和对象大小？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. watch 的作用</div><p>Kubernetes 组件大量依赖 List/Watch 感知对象变化，watch 是控制器、scheduler、kubelet 协作的基础。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 对象过大的风险</div><p>Node status、Pod status、ResourceSlice 等对象过大会增加 API Server 序列化、网络传输、缓存和 etcd 存储压力。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 更新过频的风险</div><p>频繁 status 更新会放大 watch 广播和 etcd 写入压力，导致控制面 QPS、延迟和内存上升。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 治理方式</div><p>控制对象大小、减少无意义 status 更新、合理分片、使用分页和限流，DRA 用 ResourceSlice 也是为了避免 Node 对象无限膨胀。</p></div>
<div class="qa-summary">面试口径：大集群稳定性要控制 watch 数量、对象大小和更新频率，否则 API Server 与 etcd 会成为瓶颈。</div>
</div>
</div>

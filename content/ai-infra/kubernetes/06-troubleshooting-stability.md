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

<div class="card card-s">
<h3>Pod Phase、重启策略与镜像策略速查</h3>
<table>
<tr><th>对象/字段</th><th>常见值</th><th>面试抓手</th></tr>
<tr><td>Pod Phase</td><td>Pending / Running / Succeeded / Failed / Unknown</td><td>Phase 是 Pod 总体状态，不等同于单个容器状态</td></tr>
<tr><td>Container State</td><td>Waiting / Running / Terminated</td><td>CrashLoopBackOff、ImagePullBackOff 属于 Waiting reason</td></tr>
<tr><td><code>restartPolicy</code></td><td>Always / OnFailure / Never</td><td>Deployment 通常 Always；Job 常用 OnFailure / Never</td></tr>
<tr><td><code>imagePullPolicy</code></td><td>Always / IfNotPresent / Never</td><td><code>:latest</code> 默认 Always；生产建议固定 tag 或 digest</td></tr>
</table>
<div class="qa-summary">面试口径：Pod Phase 看整体，Container State 看容器细节；重启策略控制退出后是否重启，镜像策略控制启动前是否拉镜像。</div>
</div>

<div class="card card-m">
<h3>Probe 三件套</h3>
<table>
<tr><th>Probe</th><th>作用</th><th>失败后行为</th></tr>
<tr><td><code>readinessProbe</code></td><td>判断能否接流量</td><td>从 Service endpoints 移除，不重启容器</td></tr>
<tr><td><code>livenessProbe</code></td><td>判断是否需要自愈重启</td><td>kubelet 重启容器</td></tr>
<tr><td><code>startupProbe</code></td><td>给慢启动应用更长启动窗口</td><td>成功前延迟 liveness/readiness 生效</td></tr>
</table>
<div class="qa-summary">面试口径：readiness 管流量，liveness 管重启，startup 保护慢启动。</div>
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

<div class="card card-d">
<h3>etcd 故障排查：raft、defrag、备份</h3>
<p>etcd 是 K8s 的"单点真相"，控制面所有问题最终都会落到 etcd 上。面试常考 etcd 抖动后控制面有什么症状，怎么定位。</p>
<table>
<tr><th>典型症状</th><th>底层原因</th><th>处理</th></tr>
<tr><td>API Server 5xx、kubectl 卡顿</td><td>etcd leader 选举失败 / 慢盘</td><td>看 <code>etcd_server_has_leader</code>、<code>etcd_disk_wal_fsync_duration_seconds</code>，换 SSD 或独立磁盘</td></tr>
<tr><td>etcd "took too long" 警告</td><td>大事务、慢盘、内存压力</td><td>分析慢请求的 key 前缀，限制大对象（CRD/Lease 风暴）</td></tr>
<tr><td>etcd 数据库膨胀</td><td>历史 revision 太多没有 compact</td><td>开启 auto compaction，定期 <code>etcdctl defrag</code></td></tr>
<tr><td>NOSPACE alarm</td><td>db size 超 quota</td><td>调大 <code>--quota-backend-bytes</code>、defrag、删冗余对象</td></tr>
<tr><td>raft 心跳超时</td><td>跨可用区 / 跨地域延迟过高</td><td>etcd 必须低延迟，建议同 AZ 同机房；不要跨 region 部署 etcd</td></tr>
<tr><td>数据损坏</td><td>磁盘故障 / 异常关机</td><td>需要从 snapshot 恢复，所以备份和恢复演练必须常态化</td></tr>
</table>
<table>
<tr><th>关键指标</th><th>含义</th><th>报警阈值参考</th></tr>
<tr><td><code>etcd_server_has_leader</code></td><td>是否有 leader</td><td>持续 0 立刻告警</td></tr>
<tr><td><code>etcd_server_leader_changes_seen_total</code></td><td>leader 变更次数</td><td>短时多次切主，通常是慢盘或网络</td></tr>
<tr><td><code>etcd_disk_wal_fsync_duration_seconds</code> p99</td><td>WAL 落盘耗时</td><td>&gt;25ms 危险，需要立刻查盘</td></tr>
<tr><td><code>etcd_disk_backend_commit_duration_seconds</code> p99</td><td>事务提交耗时</td><td>&gt;25ms 危险</td></tr>
<tr><td><code>etcd_mvcc_db_total_size_in_bytes</code></td><td>数据库大小</td><td>接近 quota 时安排 defrag</td></tr>
</table>
<div class="qa-summary">面试口径：etcd 出问题先看 leader、WAL fsync、backend commit 三个指标；优化方向是独立 SSD、控制对象数量和 watch 风暴、定期 compact + defrag、跨 AZ 三节点而不是跨 region。</div>
</div>

<div class="card card-w">
<h3>控制面 HA：API Server / Scheduler / Controller Manager</h3>
<p>控制面的高可用模式不一样：API Server 是<strong>无状态</strong>，多副本同时工作，前面挂 LB；Scheduler 和 Controller Manager 是<strong>有状态</strong>，多副本通过 leader election 选主，一主多备。</p>
<table>
<tr><th>组件</th><th>HA 模式</th><th>关键依赖</th><th>面试要点</th></tr>
<tr><td>API Server</td><td>多副本 active-active</td><td>前置 LB（HAProxy / 云 LB）+ etcd</td><td>客户端用 LB VIP 而不是直连某个节点</td></tr>
<tr><td>etcd</td><td>奇数节点 raft 集群（3 / 5）</td><td>低延迟磁盘和网络</td><td>quorum 是 N/2+1，3 节点最多挂 1，5 节点最多挂 2</td></tr>
<tr><td>kube-scheduler</td><td>leader election，主备</td><td>API Server 上的 Lease 对象</td><td>主副本挂掉后秒级切主，调度短暂停顿</td></tr>
<tr><td>kube-controller-manager</td><td>leader election，主备</td><td>同上</td><td>同上，注意 <code>--leader-elect-renew-deadline</code></td></tr>
<tr><td>cloud-controller-manager</td><td>leader election</td><td>云 API</td><td>主备切换不要太频繁，否则云资源回收抖动</td></tr>
<tr><td>kubelet / kube-proxy</td><td>每节点一个，独立</td><td>API Server 可达</td><td>没有 HA 概念，节点级单点</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">面试口径</div><p>控制面 HA 不是简单"复制 3 份"：API Server 是无状态多活，etcd 是 raft quorum，scheduler / CM 是 leader election 主备。整体 SLO 取决于<strong>木桶最短板</strong>，绝大多数事故的根因都在 etcd（慢盘、跨 AZ 延迟、对象膨胀）。</p></div>
</div>

<div class="card card-s">
<h3>API Server 过载：怎么定位与缓解</h3>
<p>"控制面慢"是大集群最常见的"症状"，背后可能是 API Server / etcd / 客户端任意一环。</p>
<table>
<tr><th>分层</th><th>常见原因</th><th>定位指标</th></tr>
<tr><td>客户端</td><td>controller 写循环、watch 重连风暴、finalizer 死循环</td><td><code>apiserver_request_total</code> 按 user / verb / resource 拆</td></tr>
<tr><td>API Server</td><td>反序列化大对象、admission webhook 慢、APF 排队</td><td><code>apiserver_request_duration_seconds</code>、<code>apiserver_admission_webhook_admission_duration_seconds</code></td></tr>
<tr><td>etcd</td><td>慢盘、leader 抖动、db 太大</td><td><code>etcd_disk_*</code> 系列指标</td></tr>
<tr><td>watch 缓存</td><td>cacher 满 → resourceVersion too old / watch error</td><td><code>apiserver_watch_cache_*</code></td></tr>
</table>
<table>
<tr><th>缓解动作</th><th>说明</th></tr>
<tr><td>开启/调优 APF</td><td>把关键 controller 提到独立 PriorityLevel，普通客户端限流</td></tr>
<tr><td>缩减对象数量和大小</td><td>合并 status 更新、清理无主 Pod / Event、Lease 用 v1 版</td></tr>
<tr><td>合理分页 List</td><td>客户端禁止 List 全量大资源（Pod / Event），改为 paginated 或 informer</td></tr>
<tr><td>升级 etcd 磁盘</td><td>独立 NVMe，避免和 kubelet / 容器盘共用</td></tr>
<tr><td>限制 webhook</td><td>缩短超时、failurePolicy=Ignore、避免阻塞核心资源</td></tr>
</table>
</div>

<div class="card card-d">
<h3>集群网络故障：DNS、conntrack、MTU</h3>
<p>"Pod 偶发超时"通常不是业务代码而是网络层的问题。这几个高频根因建议背下来。</p>
<table>
<tr><th>故障</th><th>典型症状</th><th>定位</th><th>修复</th></tr>
<tr><td>CoreDNS 抖动</td><td>偶发解析失败、5s 延迟</td><td><code>kubectl logs coredns</code>、客户端 <code>ndots</code>、retry</td><td>启用 NodeLocal DNSCache，调小 ndots 或写 FQDN</td></tr>
<tr><td>conntrack 表打满</td><td>连接 reset、新连接建立失败</td><td>看节点 <code>nf_conntrack_count</code> / <code>max</code></td><td>调大 <code>nf_conntrack_max</code>，必要时切 eBPF 模式绕过</td></tr>
<tr><td>MTU 不一致</td><td>大包丢失、TLS 握手失败但 ping 通</td><td>抓包看是否在大包处卡住</td><td>统一 overlay MTU（如 1450）、检查 PMTUD 是否被 ICMP 黑洞</td></tr>
<tr><td>kube-proxy 同步慢</td><td>新建 Service 几十秒不通</td><td>看 kube-proxy <code>sync_proxy_rules_duration_seconds</code></td><td>切到 IPVS / eBPF</td></tr>
<tr><td>NetworkPolicy 误杀</td><td>原本通的连接突然不通</td><td>对比 NP 变更和现象时间线</td><td>放行 DNS、明确 Egress 列表</td></tr>
<tr><td>跨 AZ / region 抖动</td><td>P99 高、AllReduce 慢</td><td>看物理网络指标 + 拓扑感知调度</td><td>训练任务 same leaf 调度，避免跨 spine</td></tr>
</table>
</div>

<div class="card card-m">
<h3>故障排查 SOP：从现象到根因的标准动作</h3>
<p>面试常被问"线上 Pod 怎么排查"，面试官想看的不是技巧而是<strong>系统化方法</strong>。下面这个 SOP 适用于绝大多数 K8s 故障。</p>
<table>
<tr><th>步骤</th><th>看什么</th><th>命令 / 工具</th></tr>
<tr><td>1. 现象</td><td>Pod 状态、Service 通否、用户报错</td><td><code>kubectl get pods -o wide</code>、<code>kubectl describe</code></td></tr>
<tr><td>2. Events</td><td>调度、拉镜像、探针、OOM 都会留痕</td><td><code>kubectl get events --sort-by=.lastTimestamp</code></td></tr>
<tr><td>3. 容器日志</td><td>当前 + 上一容器的日志</td><td><code>kubectl logs -f</code>、<code>kubectl logs --previous</code></td></tr>
<tr><td>4. 节点侧</td><td>kubelet / runtime / 内核日志</td><td>登录节点 <code>journalctl -u kubelet</code>、<code>dmesg -T</code></td></tr>
<tr><td>5. 控制面</td><td>API Server / scheduler / CM / etcd</td><td>看指标和日志，确认控制面是否同样异常</td></tr>
<tr><td>6. 网络面</td><td>DNS / Service / NetworkPolicy / CNI</td><td>从故障 Pod 内 <code>nslookup</code> / <code>curl</code>，再到节点抓包</td></tr>
<tr><td>7. 时间线对照</td><td>变更（发布、配置、节点回收）</td><td>结合 audit log 和 CMDB 找时间相关性</td></tr>
<tr><td>8. 假设验证</td><td>缩小到一个假设，主动复现</td><td>测试 namespace、灰度修复、最小复现脚本</td></tr>
</table>
<div class="qa-summary">面试口径：故障排查不是猜，要按"现象 → events → 日志 → 节点 → 控制面 → 网络 → 变更时间线"的顺序逐层下钻；先收敛假设，再做最小复现验证。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: etcd 抖动会让 K8s 出现什么症状？怎么定位？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从用户能看到的症状反推到 etcd 指标，再讲常见根因。</p>
<div class="qa-section"><div class="qa-section-title">1. 用户侧症状</div><p><code>kubectl</code> 卡顿、API Server 5xx、controller reconcile 间断、scheduler 调度停顿、Pod status 上报滞后。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 控制面指标</div><p>看 API Server 写延迟（<code>apiserver_request_duration_seconds</code>）和 etcd 的 <code>has_leader</code>、<code>leader_changes_seen_total</code>、<code>wal_fsync</code>、<code>backend_commit</code>。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 常见根因</div><p>慢盘（fsync 飙到几十毫秒）、跨 AZ 延迟、db 太大没 compact、Lease/Event 风暴、大对象（如巨型 ConfigMap）频繁更新。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 缓解</div><p>独立 NVMe、定期 compact + defrag、限制单对象大小、修客户端 watch 风暴；恶劣情况下从 snapshot 恢复。</p></div>
<div class="qa-summary">面试口径：etcd 抖动表现为控制面整体慢，定位看 leader / WAL fsync / backend commit，根因多在磁盘和对象膨胀。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 控制面 HA 怎么设计？为什么不能跨 region 部署 etcd？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>区分组件无状态 / 有状态，再讲 etcd 对延迟的硬性要求。</p>
<div class="qa-section"><div class="qa-section-title">1. 无状态组件</div><p>API Server 多副本 active-active，前面挂 LB；客户端访问的是 LB VIP，不绑定节点。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 有状态组件</div><p>scheduler / controller-manager 通过 Lease 做 leader election，主备秒级切换；切换时短暂停顿是可接受的。</p></div>
<div class="qa-section"><div class="qa-section-title">3. etcd 是 raft</div><p>raft 每次写都需要 quorum，跨 region 的网络延迟（几十毫秒）会让每次写延迟翻倍，整个 K8s 慢到不可用。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 推荐部署</div><p>etcd 同 region 跨 AZ 三节点（最多挂 1）或五节点（最多挂 2）；跨 region 用多集群联邦或 fleet，而不是单集群跨 region。</p></div>
<div class="qa-summary">面试口径：控制面 HA = API Server 多活 + etcd raft quorum + scheduler/CM leader election；etcd 不能跨 region 是因为 raft 每写都要 quorum，延迟敏感。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod 偶发超时但不是 OOM，可能是什么？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>排除业务后聚焦"网络层 / 内核层 / DNS"。</p>
<div class="qa-section"><div class="qa-section-title">1. DNS</div><p>CoreDNS 抖动 + 客户端没 NodeLocal DNSCache 时，常见 5s 超时（resolv.conf 默认 timeout）；ndots 过大也放大 DNS 次数。</p></div>
<div class="qa-section"><div class="qa-section-title">2. conntrack</div><p>节点 <code>nf_conntrack_max</code> 不够大，新连接被丢；典型症状是高峰期连接重置、ECONNRESET。</p></div>
<div class="qa-section"><div class="qa-section-title">3. MTU</div><p>overlay MTU 没和物理网卡对齐，TLS 握手等大包卡住，但小包（ping）正常，迷惑性强。</p></div>
<div class="qa-section"><div class="qa-section-title">4. kube-proxy</div><p>iptables 模式下 Service 变更扫描慢、conntrack 老化也会偶发；切 IPVS / eBPF 通常能稳定下来。</p></div>
<div class="qa-summary">面试口径：偶发超时优先看 DNS（5s 这个数字几乎就是签名）、conntrack 容量、MTU 一致性，再看 kube-proxy 模式。</div>
</div>
</div>

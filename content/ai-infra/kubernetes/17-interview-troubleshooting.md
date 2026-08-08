## 一句话结论

Kubernetes 排障先判断对象卡在哪个生命周期阶段，再查看该阶段的控制器、事件和日志。不要从“重启 Pod”开始，也不要只看最终 Error；应该沿 `API → 调度 → 节点 → 容器 → 网络/存储 → 应用` 缩小范围。

## 总体诊断树

```flow
对象是否创建成功 | kubectl get、API 错误、Admission、Quota
Pod 是否完成调度 | Pending、Events、scheduler、requests/约束
节点是否能启动 Sandbox | kubelet、CRI、CNI、镜像、Volume
容器是否持续运行 | Exit Code、OOM、Probe、应用日志
服务是否可达 | Ready、EndpointSlice、DNS、NetworkPolicy、数据面
业务是否健康 | 延迟、错误率、依赖、资源与应用指标
```

## 高频现象

| 现象 | 核心检查 | 常见原因 |
|---|---|---|
| Pod Pending | `describe pod` Events、Node Allocatable、约束 | 资源不足、taint、affinity、PVC、配额、Gang 准入 |
| ContainerCreating | kubelet、CRI/CNI/CSI、镜像事件 | Sandbox、网络、挂卷或镜像问题 |
| CrashLoopBackOff | `logs --previous`、Exit Code、Probe | 应用退出、配置错误、OOM、Liveness 误杀 |
| ImagePullBackOff | 镜像名、凭据、DNS、Registry | Secret、权限、网络、限流 |
| Service 不通 | Ready、EndpointSlice、端口、DNS、NetworkPolicy | Selector 错、readiness 失败、targetPort 错 |
| Node NotReady | Lease/Condition、kubelet、runtime、磁盘/网络 | kubelet 心跳、CRI 卡死、DiskPressure、证书 |
| Pod 被 Evicted | Node Pressure、ephemeral-storage、taint | Memory/Disk/PID Pressure 或节点驱逐 |
| API Server 延迟高 | APF、etcd、Webhook、请求量 | 慢 Webhook、大对象、高 Watch/List 压力 |

## 常用命令顺序

```bash
kubectl get pod -A -o wide
kubectl describe pod <pod> -n <ns>
kubectl get events -n <ns> --sort-by=.lastTimestamp
kubectl logs <pod> -n <ns> --all-containers --previous
kubectl get pod <pod> -n <ns> -o yaml
kubectl describe node <node>
kubectl get endpointslice -n <ns> -l kubernetes.io/service-name=<svc>
```

`describe` 的 Events 适合确认调度、拉镜像、挂卷和 Probe 失败，但事件有保留窗口，不能代替组件日志和长期指标。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod 一直 Pending，你怎么排查？</div>
<div class="qa-a"><p>先看 Pod Events 中 scheduler 的不可调度原因，再逐项核对 requests 与 Node Allocatable、taint/toleration、nodeSelector/affinity、TopologySpread、PVC binding、ResourceQuota 和队列/Gang 准入。如果是 GPU，再确认 Device Plugin/DRA 的资源是否注册以及对应节点是否健康。最后才考虑扩容或修改约束。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod Running，但 Service 访问不到，怎么查？</div>
<div class="qa-a"><p>Running 只说明容器进程存在。先确认 Readiness 和 EndpointSlice 是否包含 Pod IP，再检查 Service selector、port/targetPort、应用监听地址、DNS、NetworkPolicy，以及 kube-proxy/eBPF 数据面。分别从同 Pod、同节点、跨节点和集群外测试，确定故障边界。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Node NotReady 后 Pod 会立刻迁移吗？</div>
<div class="qa-a"><p>不会简单地立刻迁移。控制面根据 Node Lease/Condition 和容忍时间判断失联，随后通过 taint-based eviction 处理 Pod；DaemonSet、Static Pod、带特殊 toleration 或本地存储的工作负载行为不同。原节点上的容器也可能仍在运行，因此还要考虑网络分区下的双实例和一致性风险。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod 一直 ContainerCreating，怎么排查？</div>
<div class="qa-a">
<div class="qa-summary">Pod 已经完成调度，重点检查节点侧的 kubelet、CRI、CNI、CSI、Sandbox 和镜像路径。</div>
<div class="qa-section"><div class="qa-section-title">排查路径</div><p>先看 Events 判断是 PullImage、FailedCreatePodSandBox 还是 FailedMount；再看 kubelet/containerd 日志、CNI IPAM 和节点网络、PVC/CSI Node 日志、磁盘与 inode。用 <code>crictl pods/images/ps</code> 确认 Runtime 侧实际状态。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>ContainerCreating 通常不是 Scheduler 问题；不要在没看 Events 前反复删除 Pod。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CrashLoopBackOff 怎么排查？</div>
<div class="qa-a">
<div class="qa-summary">CrashLoopBackOff 是容器反复退出后的退避状态，根因要从上一次退出日志、Exit Code、OOM 和 Probe 中找。</div>
<div class="qa-section"><div class="qa-section-title">排查路径</div><p>查看 <code>kubectl logs --previous</code>、<code>status.containerStatuses</code>、Events 和应用配置；Exit 137 重点检查 OOM/强制终止，Exit 1 看应用错误，Liveness 失败看探针阈值和依赖。必要时用临时调试容器检查文件、DNS 和网络。</p></div>
<div class="qa-section"><div class="qa-section-title">修复验证</div><p>修复后观察重启计数、Readiness、错误率和一段稳定窗口，不能只看 Pod 暂时变绿。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ImagePullBackOff 怎么排查？</div>
<div class="qa-a">
<div class="qa-summary">先从 Events 中区分镜像不存在、鉴权失败、网络/DNS、证书和 Registry 限流，再到目标节点复现拉取。</div>
<div class="qa-section"><div class="qa-section-title">排查路径</div><p>核对 registry、repository、tag/digest 和架构；检查 imagePullSecret 是否在正确 Namespace 且 ServiceAccount 已引用；在节点用 <code>crictl pull</code> 验证 Runtime endpoint、代理、DNS、CA 和镜像仓库连通性。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>本地 Docker 能拉取不代表 kubelet 使用的 containerd 配置、凭据和证书相同。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: PVC 已经 Bound，但 Pod 仍然挂载失败，怎么查？</div>
<div class="qa-a">
<div class="qa-summary">Bound 只说明 PVC 与 PV 已绑定，仍要检查 Attach、节点拓扑、CSI Node Mount、访问模式、权限和存储后端。</div>
<div class="qa-section"><div class="qa-section-title">排查路径</div><p>查看 Pod Events、VolumeAttachment、PV nodeAffinity、StorageClass、CSI Controller/Node 日志；确认 RWO 卷没有仍挂在旧节点，目标节点可访问存储，设备格式和 mount 目录正常，fsGroup/SELinux 权限正确。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p><code>WaitForFirstConsumer</code> 会把绑定推迟到调度时，这是为了同时满足存储和节点拓扑，不是控制器卡住。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: API Server 延迟突然升高，或者大量 Pod 同时创建导致控制面抖动，怎么处理？</div>
<div class="qa-a">
<div class="qa-summary">先用 API SLI 和请求分类定位是 etcd、Webhook、Watch/List 风暴、APF 排队还是对象写入热点，再限流止损。</div>
<div class="qa-section"><div class="qa-section-title">排查路径</div><p>检查 apiserver request latency/inflight、APF queue、etcd fsync/DB size、Webhook 延迟、审计日志和 Scheduler/Controller Queue。临时降低提交并发、暂停异常 Controller、隔离慢 Webhook；长期使用 APF、批量创建限速、Shared Informer、合理 resync 和控制器工作队列。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>盲目扩 API Server 不能解决慢 etcd、同步外部 Webhook 或客户端持续全量 List。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 节点能运行 nvidia-smi，但 Node 没有 nvidia.com/gpu，怎么查？</div>
<div class="qa-a">
<div class="qa-summary">宿主机 Driver 正常，故障大概率在 Device Plugin、kubelet 注册目录或设备健康上报链路。</div>
<div class="qa-section"><div class="qa-section-title">排查路径</div><p>检查 Device Plugin DaemonSet 是否落到目标节点、toleration/nodeSelector、插件日志和 <code>/var/lib/kubelet/device-plugins/</code> Socket；确认插件容器能访问 NVML/设备节点，MIG strategy 与节点状态一致，kubelet 日志没有注册错误。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>不要手工给 Node Status 写 GPU 数量；Capacity 必须由 kubelet Device Manager 根据健康设备维护。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 分布式训练只启动了部分 Worker，剩余 Pod Pending，怎么处理？</div>
<div class="qa-a">
<div class="qa-summary">这是典型的逐 Pod 调度与作业级 Gang 需求冲突：先停止无效占卡，再用 PodGroup/队列做成组准入。</div>
<div class="qa-section"><div class="qa-section-title">排查路径</div><p>确认 Pending 原因是总量、拓扑、配额还是 taint；检查所有 Rank 的资源和约束是否一致、训练 Operator 状态、NCCL 初始化日志。若资源无法凑齐，应释放已启动 Worker，避免它们空等并占用 GPU。</p></div>
<div class="qa-section"><div class="qa-section-title">长期方案</div><p>使用 Volcano/Kueue/支持 Gang 的调度体系，在准入时检查 <code>minAvailable</code>、队列配额和拓扑集合；弹性训练则明确 min/max world size 和 Checkpoint 语义。</p></div>
</div></div>

## 复盘要求

- 记录故障时间线、影响范围、直接原因和系统性原因。
- 修复后用相同请求和负载验证，不只看 Pod 变绿。
- 把临时命令转化为告警、Runbook、准入规则或自动修复能力。

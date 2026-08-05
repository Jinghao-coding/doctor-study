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

## 复盘要求

- 记录故障时间线、影响范围、直接原因和系统性原因。
- 修复后用相同请求和负载验证，不只看 Pod 变绿。
- 把临时命令转化为告警、Runbook、准入规则或自动修复能力。

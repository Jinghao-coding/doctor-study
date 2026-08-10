<div class="figure">
<img src="../../../resources/images/k8s-scheduler/kubernetes-components-official.svg" alt="Kubernetes 官方集群组件架构图" loading="lazy">
<p class="caption">Kubernetes 官方组件图：控制面负责状态存储、控制与调度，节点侧由 kubelet、kube-proxy 和容器运行时承载 Pod。来源：<a href="https://kubernetes.io/docs/concepts/overview/components/">Kubernetes Components</a>。</p>
</div>

## 高频追问压缩表

| 问题 | 回答抓手 | 易错点 |
|---|---|---|
| Kubernetes 架构有哪些组件？ | 控制面保存和决策；节点面负责运行与上报 | 不要把 scheduler 说成创建容器 |
| Pod 创建后发生什么？ | Admission、持久化、调度、kubelet、CRI、CNI、CSI、Probe | 不要漏掉异步控制循环 |
| Deployment 如何滚动更新？ | ReplicaSet、maxSurge/maxUnavailable、readiness | Pod Running 不等于可接流量 |
| Informer 为什么不用一直 List？ | List 建初始状态，Watch 增量更新，本地 Cache 降低 API 压力 | Watch 断开要根据 resourceVersion 恢复 |
| Controller 如何保证可靠？ | 幂等 Reconcile、WorkQueue、重试、Finalizer、Status | 不要把事件处理写成一次性脚本 |
| Scheduler 的 Filter/Score/Bind 是什么？ | 先排除不可行节点，再排序，最后绑定 | 具体资源分配可能仍在 kubelet 侧完成 |
| requests 和 limits 区别？ | requests 参与调度与保障；limits 约束运行上限 | GPU Extended Resource 规则不同于 CPU |
| QoS 如何决定？ | Guaranteed/Burstable/BestEffort 来自 request/limit 配置 | QoS 不是业务优先级 |
| Service 怎么转发流量？ | Service/EndpointSlice + kube-proxy 或 eBPF 数据面 | Service 本身不是守护进程代理 |
| Headless Service 有什么用？ | 不分配 ClusterIP，DNS 返回后端地址 | 常用于 StatefulSet，但两者不是绑定关系 |
| PV/PVC/StorageClass/CSI 关系？ | 声明、绑定、动态供给与节点挂载 | PVC Bound 不等于应用一定能 Mount |
| ConfigMap/Secret 更新会怎样？ | Volume 投射可更新但有延迟；环境变量不会自动刷新 | Secret 只是 base64，不等于加密 |
| RBAC、Admission、Pod Security 区别？ | 授权、准入变更/校验、Pod 安全约束 | 顺序和职责不要混淆 |
| Liveness/Readiness/Startup Probe？ | 重启、摘流量、保护慢启动 | Liveness 配错会制造重启风暴 |
| HPA、VPA、Cluster Autoscaler？ | Pod 副本、单 Pod 资源建议/调整、节点容量 | 扩容速度和指标延迟影响 SLO |

## Pod 创建主链路

```flow
客户端提交对象 | API Server 做认证、授权、准入与校验
写入 etcd | 返回对象，不等待 Pod 真正运行
Controller 补齐期望对象 | Deployment 创建 ReplicaSet，ReplicaSet 创建 Pod
Scheduler 选择 Node | Filter、Score、Reserve/Permit、PreBind、Bind
kubelet 同步 Pod | CRI 创建 Sandbox/Container，CNI 配网，CSI 挂卷
Probe 与状态回报 | EndpointSlice 根据 Ready 状态接入流量
```

## 基础机制直接问答

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Kubernetes 整体架构有哪些组件？</div>
<div class="qa-a">
<div class="qa-summary">控制面负责保存状态和做决策，节点面负责运行工作负载并持续上报状态。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>控制面包括 API Server、etcd、Scheduler、Controller Manager 和可选的 Cloud Controller Manager；节点侧包括 kubelet、容器运行时和 kube-proxy/eBPF 数据面。API Server 是统一状态入口，其他组件通过 List/Watch 和写 API 解耦协作。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>Scheduler 只选择节点，kubelet 才负责在节点上调用 CRI/CNI/CSI；etcd 保存状态，不直接向节点下发命令。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>不要把 Service、Controller 或 Scheduler 说成真正创建容器的数据面组件。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 一个 Pod 从提交到 Running/Ready 的完整流程是什么？</div>
<div class="qa-a">
<div class="qa-summary">请求经过 API Server 写入 etcd，Controller 补齐对象，Scheduler 绑定节点，kubelet 再调用 CSI、CRI 和 CNI 创建运行环境，最后由 Probe 决定是否 Ready。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>API Server 依次执行认证、授权、准入、默认值和校验；Deployment/ReplicaSet Controller 创建 Pod；Scheduler Filter/Score 后写入 NodeName；kubelet Watch 到 Pod，准备 Volume、创建 Sandbox、配置网络、拉镜像并启动容器，随后回写状态。Readiness 成功后 EndpointSlice 才接入流量。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>API 返回创建成功只是对象已持久化，不表示 Pod 已经运行；整个过程是多个异步控制循环。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>CNI 通常在 RunPodSandbox 路径由 Runtime 侧调用，CSI 挂载和镜像拉取的先后可能并行或受实现影响，不要背成绝对同步脚本。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: API Server 为什么是 Kubernetes 的统一入口？</div>
<div class="qa-a">
<div class="qa-summary">它统一认证、授权、准入、版本转换、校验、乐观并发、审计和 Watch，保证所有组件遵循同一套对象语义。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>只有 API Server 直接访问 etcd，可以集中维护权限、资源版本和存储格式。Controller、Scheduler、kubelet 都面向 API 对象协作，从而避免组件之间点对点耦合，也便于扩展 CRD、Webhook 和聚合 API。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>请求量大时还要考虑 API Priority and Fairness、Watch Cache、Webhook 延迟和 etcd 性能。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: kubelet、containerd、runc、containerd-shim 和 pause 容器分别是什么？</div>
<div class="qa-a">
<div class="qa-summary">kubelet 编排本节点 Pod；containerd 提供 CRI 和容器生命周期；runc 创建 OCI 容器；shim 托管容器进程；pause 容器持有 Pod 共享 namespace。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>kubelet 通过 CRI 调用 containerd，containerd 管镜像、Snapshot 和 Task，再由 shim 调用 runc 创建进程。业务容器加入 Pod Sandbox 的 network/IPC 等 namespace，因此业务容器重启时 Pod IP 可以保持不变。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>移除 dockershim 不代表 Docker 格式镜像不能运行；镜像格式与节点运行时是两件事。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: requests、limits 和 QoS 的关系是什么？</div>
<div class="qa-a">
<div class="qa-summary">requests 参与调度和资源保障，limits 约束运行上限；Pod 的 CPU/内存配置共同决定 Guaranteed、Burstable 或 BestEffort QoS。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Scheduler 按 requests 判断节点是否可行；CPU limit 通常由 CFS bandwidth 控制，内存超过 limit 可能 OOM。所有容器 CPU/内存 request 等于 limit 且都设置时为 Guaranteed；完全不设置为 BestEffort，其余为 Burstable。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>GPU Extended Resource 通常只允许整数 request/limit，资源语义不同于可压缩的 CPU。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>QoS 不等于 PriorityClass；一个 Guaranteed Pod 也不一定比高优 Burstable Pod 更先调度。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Informer 为什么不是不停地全量 List？</div>
<div class="qa-a">
<div class="qa-summary">Informer 用 List 建立初始状态，再用 Watch 接收增量变化，并通过本地 Cache 降低 API Server 压力。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Reflector 把 List/Watch 结果写入 DeltaFIFO，Controller 消费事件并更新 Indexer/Store，再把对象 Key 放入 WorkQueue。Watch 断开、resourceVersion 过旧或遇到 compaction 时，需要重新 List 后继续 Watch。</p></div>
<div class="qa-section"><div class="qa-section-title">追问</div><p>事件可能重复、合并或丢失，所以 Controller 不能依赖“每个事件只处理一次”，而要根据缓存中的当前状态做幂等 Reconcile。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Kubernetes 为什么使用声明式 API？</div>
<div class="qa-a"><p>用户提交期望状态，Controller 持续比较期望与实际并执行幂等 Reconcile。这样控制器崩溃、事件丢失或短暂失败后仍可通过重新观察状态继续收敛，不依赖一条不可恢复的命令执行链。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: etcd 挂了，已经运行的 Pod 会立刻停止吗？</div>
<div class="qa-a"><p>通常不会立刻停止，节点上的容器仍由 kubelet 和 runtime 维持；但控制面无法可靠读写集群状态，新建、更新、调度和控制器收敛会受阻。还要区分单成员故障与 etcd 丢失法定多数，恢复时重点保证数据一致性和备份有效性。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 Controller 的 Reconcile 必须幂等？</div>
<div class="qa-a"><p>Watch 事件可能重复、合并或丢失，控制器也会因失败重试和定期 Resync 再次处理同一对象。Reconcile 应根据当前状态计算下一步，使执行一次和多次得到相同结果，而不是依赖“事件只来一次”。</p></div>
</div>

## 回答原则

- 先说组件职责，再讲数据流或控制流。
- 明确 API 写成功和资源真正 Ready 是两个时间点。
- 涉及故障时说明缓存、重试、幂等和最终一致性。
- 涉及资源时区分调度请求、运行限制和业务实际消耗。

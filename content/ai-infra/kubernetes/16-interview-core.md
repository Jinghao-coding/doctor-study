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
<div class="qa-q">Q: 执行 kubectl apply -f pod.yaml 后，Pod 到容器 Running 的完整链路是什么？为什么完成调度后仍可能长时间不 Running？</div>
<div class="qa-a">
<div class="qa-summary"><code>kubectl</code> 只提交对象；API Server 持久化，Scheduler 写绑定，目标节点 kubelet 才把声明转换成 sandbox、网络、卷和容器进程。</div>
<div class="qa-section"><div class="qa-section-title">1. API Server 与 etcd</div><p><code>kubectl</code> 读取 YAML 并向 API Server 发请求。API Server 完成认证、鉴权、准入、默认值、版本转换和校验，再把 Pod 对象持久化到 etcd 并返回；etcd 只保存经 API Server 写入的对象状态，不向节点发命令。若提交的是 Deployment，Deployment/ReplicaSet Controller 会先创建真正待调度的 Pod。</p></div>
<div class="qa-section"><div class="qa-section-title">2. Scheduler</div><p>Scheduler 从队列取出 <code>spec.nodeName</code> 为空的 Pod，基于 requests、Node 状态、亲和性、taint、存储和插件执行 Filter、Score 等流程，选出 Node，并通过 Binding/API 更新把决定写回 API Server；它不直接通知 kubelet，也不创建容器。</p></div>
<div class="qa-section"><div class="qa-section-title">3. kubelet、Runtime 与 CNI</div><p>目标节点 kubelet watch 到分配给本节点的 Pod，准备 Secret/ConfigMap 和 volume，通过 CRI 请求 containerd/CRI-O 拉镜像并执行 <code>RunPodSandbox</code>。Runtime 的 CRI 实现通常在 sandbox 路径调用 CNI，创建网络命名空间、分配 Pod IP 和配置路由；随后 Runtime 创建并启动 init container、sidecar 和业务容器。kubelet 查询 Runtime 状态并回写 Pod status。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 已调度但不 Running</div><p><code>PodScheduled=True</code> 只代表选点完成。Pod 仍可能卡在 PVC attach/mount、Secret/ConfigMap 获取、sandbox 创建、CNI/IPAM、镜像拉取、Runtime/磁盘异常、init container 未完成或设备准备。先用 Events 区分 <code>FailedMount</code>、<code>FailedCreatePodSandBox</code>、<code>ErrImagePull</code> 等，再查目标节点 kubelet、Runtime、CNI/CSI。容器进入 Running 后也可能因 readiness 失败而长期不 Ready。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>Pod phase 在完成调度后仍可保持 <code>Pending</code>，而 <code>kubectl</code> 的 STATUS 显示 <code>ContainerCreating</code>；CNI 通常由 Runtime 的 CRI 实现调用，卷准备与镜像拉取也不要背成所有实现都完全相同的串行步骤。</p></div>
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
<div class="qa-q">Q: requests 和 limits 分别在哪里生效？它们与 QoS 有什么关系？</div>
<div class="qa-a">
<div class="qa-summary">requests 主要在调度、节点资源记账和竞争保障中生效；limits 主要由 kubelet/Runtime 写入 Linux cgroup，约束容器运行时上限。</div>
<div class="qa-section"><div class="qa-section-title">展开</div><p>Scheduler 用各容器 requests 的合计而不是实时使用量做放置；kubelet 将 CPU request 转为相对 CPU 权重，并把内存 request 用于 QoS 与节点压力驱逐判断。CPU limit 通过 cgroup CPU bandwidth（cgroup v2 常见为 <code>cpu.max</code>）节流，内存 limit 通过 cgroup 内存上限约束，超限分配可能触发 OOM kill。所有容器 CPU/内存 request 与 limit 均设置且逐项相等时为 Guaranteed；完全不设置为 BestEffort，其余通常为 Burstable。</p></div>
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

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 多副本 Controller 如何避免重复处理？Leader Election 解决了什么，又没解决什么？</div>
<div class="qa-a">
<div class="qa-summary">WorkQueue 只在单进程内按 key 合并并发；多副本通常用 API Server 中的 Lease 选出一个活跃实例，但最终正确性仍必须依赖幂等、乐观并发和外部副作用去重。</div>
<div class="qa-section"><div class="qa-section-title">进程内</div><p>WorkQueue 的 dirty/processing 集合避免同一个 key 被多个 worker 同时重复消费；处理期间再来的更新把 key 标记为 dirty，<code>Done</code> 后重新入队，从而不会漏掉“处理期间又变了”。</p></div>
<div class="qa-section"><div class="qa-section-title">多副本</div><p>不同 Controller 副本有独立 Cache 和 WorkQueue，天然可能同时处理同一对象。controller-runtime Manager 常通过 <code>coordination.k8s.io/v1 Lease</code> 进行 Leader Election，让通常只有 leader 启动需要选主的 controller。</p></div>
<div class="qa-section"><div class="qa-section-title">边界</div><p>Leader Election 提供故障切换并减少常态重复执行，不提供 exactly-once、事务或 fencing，也不会自动分片来提升吞吐。旧 leader 在失联/暂停窗口中的外部调用与新 leader 接管可能重叠，因此创建子资源要用稳定名称和 OwnerReference，更新对象要处理 <code>resourceVersion</code> 冲突，调用云 API 等外部系统要使用幂等键或 fencing token。</p></div>
</div></div>

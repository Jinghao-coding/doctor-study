## 一句话结论

Kubernetes 高频面试不是背对象定义，而是解释声明式 API 如何通过控制循环收敛到真实状态。回答任何机制题都可以沿 `API Server → etcd → Watch/Informer → Controller/Scheduler → kubelet → Runtime` 这条链路展开。

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

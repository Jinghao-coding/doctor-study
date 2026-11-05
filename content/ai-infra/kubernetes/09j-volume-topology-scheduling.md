## 存储会改变可调度节点集合

Pod 申请的 CPU、GPU、网络及存储需要在同一放置方案中成立。一个已绑定到特定可用区或本地盘的 PVC，会通过对应 PV 的拓扑约束限制 Pod 的节点选择。

假设训练 Pod 需要 1 张 GPU 和一个本地数据卷：

| 节点 | 空闲 GPU | 对应数据卷 | 可否运行 |
|---|---:|---|---|
| gpu-a | 1 | 无法访问 | 存储条件不满足 |
| gpu-b | 0 | 本地 PV 位于该节点 | 等待 GPU 释放或调整资源 |
| gpu-c | 2 | 无法访问 | 存储条件不满足 |

此时集群有 3 张空闲 GPU，Pod 仍可能 Pending。抢占 gpu-a 上的其他 Pod 也不能让 gpu-a 获得 gpu-b 的本地数据。需要在 gpu-b 释放 GPU，或通过应用与存储支持的复制、恢复流程重新准备数据。

## Immediate 与 WaitForFirstConsumer

`StorageClass.volumeBindingMode` 控制何时绑定或动态创建卷。`Immediate` 可以在 PVC 创建后就确定存储；`WaitForFirstConsumer` 延迟这一决策，让调度器把使用 PVC 的 Pod 约束一起考虑。[Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/#volume-binding-mode)

| 模式 | 决策顺序 | 主要影响 |
|---|---|---|
| Immediate | PVC 创建 → 绑定或供给存储 → Pod 在可访问存储的节点中调度 | 卷可能先落到与 GPU、亲和性条件不匹配的位置 |
| WaitForFirstConsumer | Pod 参与调度 → 联合考虑节点和卷 → 确认卷绑定后绑定 Pod | 减少提前确定存储造成的拓扑冲突 |

对预创建的 local PV，可以使用如下 StorageClass：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-training-data
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
```

这个配置不会自动创建本地磁盘或 PV。管理员仍需准备路径、PV 容量、访问模式及 `nodeAffinity`；PVC 则声明匹配的 StorageClass 和需求。

## VolumeBinding 插件怎样推进

以下函数关系按 Kubernetes `v1.34.0` 的 `VolumeBinding` 实现解释，省略可选打分逻辑：

```flow
PreFilter | 检查 PVC，将已绑定、延迟绑定等需求整理进本轮状态
Filter | 对候选节点检查 PV 拓扑、静态卷匹配或动态供给可行性
Reserve | 在本地 PV/PVC cache 中 Assume 选中的卷分配
PreBind | 更新相关 PV/PVC API 状态，等待卷绑定完成
Bind | 将 Pod 绑定到节点
节点执行 | 按驱动路径完成 attach、设备准备和 mount，启动容器
```

`Reserve` 让后续调度看见暂记的卷占用；`PreBind` 通过 `BindPodVolumes` 发起必要的 API 更新并等待绑定结果。失败路径的 `Unreserve` 清理本地 assumed 状态。它不会把已完成的远端卷创建自动撤销成一个跨系统事务。

源码依据：[volume_binding.go](https://github.com/kubernetes/kubernetes/blob/v1.34.0/pkg/scheduler/framework/plugins/volumebinding/volume_binding.go)、[binder.go](https://github.com/kubernetes/kubernetes/blob/v1.34.0/pkg/scheduler/framework/plugins/volumebinding/binder.go)。PVC 已 Bound、Pod 已 Scheduled、卷已挂载和容器已 Ready，是不同的状态。

## 为什么设置 nodeName 可能让 PVC 一直等待

对于尚未绑定的 WFFC PVC，直接在 Pod 上写 `spec.nodeName` 会绕过 scheduler，也绕过需要它推进的延迟卷绑定流程。需要指定节点时，应让节点约束参与调度，例如：

```yaml
# Pod spec 片段
nodeSelector:
  kubernetes.io/hostname: gpu-b
```

节点标签值应以实际对象为准。这里的目的，是保留 scheduler 联合判断节点资源和卷条件的过程。[官方说明](https://kubernetes.io/docs/concepts/storage/storage-classes/#volume-binding-mode)

## 容量信息是调度输入，不是物理预留

对启用容量跟踪的 CSI 驱动，scheduler 可使用 `CSIStorageCapacity` 判断候选拓扑是否有足够存储。它要求驱动、StorageClass 的 WFFC 模式及相关能力正确配合。

容量信息可能过时；多个请求也可能竞争同一存储。节点暂选成功后，真实供给仍可能失败并触发重新选择。一个 Pod 使用多个卷时，部分卷已创建还可能使后续选择受限。WFFC 提高联合决策成功的机会，不提供多个卷创建的原子性。[Storage Capacity](https://kubernetes.io/docs/concepts/storage/storage-capacity/)

## RWO 与 RWOP 的粒度

| 访问模式 | 核心语义 | 不能据此推导的结论 |
|---|---|---|
| ReadWriteOnce，RWO | 单节点读写挂载 | 不等于只允许一个 Pod；同节点多个 Pod 仍可能访问 |
| ReadWriteMany，RWX | 多节点读写挂载 | 应用仍需处理并发写入和数据一致性 |
| ReadWriteOncePod，RWOP | 单 Pod 使用，要求支持它的 CSI 路径 | 不替代应用事务、checkpoint 提交和数据完整性检查 |

访问模式首先参与卷匹配和挂载约束；它们不是通用的文件权限控制或数据库锁。[Persistent Volumes：Access Modes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes)

## 从 Pending 到挂载失败的诊断

```bash
kubectl get pod,pvc -n <namespace>
kubectl describe pod <pod> -n <namespace>
kubectl describe pvc <claim> -n <namespace>
kubectl get sc <storage-class> -o yaml
kubectl get pv <volume> -o yaml
kubectl get csidriver
kubectl get csistoragecapacity -A
```

| 观察 | 解释与下一步 |
|---|---|
| PVC 等待 first consumer，尚无使用它的 Pod | 延迟绑定可能是预期状态，先确认消费者是否创建 |
| Pod 有 FailedScheduling / volume node affinity conflict | 比较 PV 的节点约束与 Pod 的 GPU、taint、affinity 条件 |
| PVC 出现 selected-node，但 provision 失败 | 检查 provisioner 事件、后端容量、权限和拓扑 |
| PVC Bound，Pod 尚未 Scheduled | 继续检查计算资源、调度约束和其他 PVC |
| Pod 已 Scheduled，出现 FailedAttachVolume / FailedMount | 转向 CSI Controller、节点插件、旧节点挂载和后端存储 |

节点故障后重新创建 Pod，不会自动搬走 local PV 中的数据。恢复时需要分别确认计算容量、存储可达性和数据有效性。机制及来源核对：2026-11-05。

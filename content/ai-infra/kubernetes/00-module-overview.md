## Kubernetes 在 AI Infra 中的定位

Kubernetes 是 AI Infra 的**编排底座**。训练任务、推理服务、GPU 共享、弹性伸缩，几乎都跑在 K8s 之上。它负责把"一堆机器和 GPU"抽象成可声明、可调度、可自愈的资源池。

面试考 K8s，本质是确认：你是否理解一个 Pod 从提交到运行的完整控制链路，以及 GPU 这种特殊资源是如何接入调度与设备管理的。

<div class="card card-d">
<h3>一句话定位</h3>
<p>K8s 把集群抽象成 <strong>声明式 API + 控制器 reconcile + 调度器绑定</strong>：你写期望状态，控制器不断把实际状态拉向期望。AI Infra 在它之上扩展了 GPU 资源、批调度（Gang）和拓扑感知。</p>
</div>

## 与其他模块的关系

| 关联模块 | 关系 | 关键连接点 |
|---|---|---|
| 任务调度理论 | K8s 调度器是理论的工程落地 | Scheduling Framework、抢占、QoS |
| GPU 集群管理 | Volcano/Kueue 扩展 K8s 批调度 | Device Plugin、Gang、DRA |
| GPU 硬件 | GPU 通过设备插件接入 | MIG/MPS、Extended Resource、Topology |
| 容器与 cgroup（OS） | Pod 之下是容器隔离 | namespace、cgroup、limits/requests |
| 系统设计题 | 训练/推理平台基于 K8s | Operator、CRD、多租户 |

## 本模块包含哪些内容

| 板块 | 覆盖内容 | 典型面试问题 |
|---|---|---|
| 架构与调度 | 控制面/数据面、Pod 主链路、Scheduling Framework、scheduler 内部机制 | 一个 Pod 从 apply 到 Running 经历了什么？ |
| 工作负载与基础设施 | Deployment/StatefulSet/Job、Informer、Reconcile、CNI/CSI | Controller 的 reconcile 循环怎么工作？ |
| 安全与运维 | RBAC、Admission、Webhook、Quota、故障排查 | Pod 一直 Pending 怎么查？ |
| AI Infra 与扩展 | Device Plugin、MIG、Gang、Kueue/Volcano、DRA、Operator | GPU 在 K8s 里怎么被调度？DRA 解决什么？ |

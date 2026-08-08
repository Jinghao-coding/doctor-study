## 问题定义

Kubernetes 平台设计题的核心是：在不破坏 Kubernetes 声明式和最终一致性模型的前提下，为多租户工作负载提供安全、稳定、可扩展的交付与运行能力。回答要覆盖控制面、数据面、租户边界、资源治理、可观测性和灾难恢复。

## 目标与约束

| 目标 | 设计问题 |
|---|---|
| 多租户安全 | Namespace、RBAC、NetworkPolicy、Pod Security、Secret 如何隔离？ |
| 资源治理 | Quota、LimitRange、Priority、队列和公平性如何组合？ |
| 发布稳定性 | Readiness、PDB、滚动更新、灰度、回滚如何配合？ |
| 平台扩展 | 什么时候写 Controller、Admission Webhook、Scheduler Plugin？ |
| 可观测性 | 如何覆盖 API、Controller、Node、Pod、网络和业务 SLO？ |
| 容灾 | etcd、控制面、节点池和跨集群如何恢复？ |

## 参考架构

```flow
入口与身份 | SSO/OIDC、RBAC、Namespace、审计
策略与准入 | Quota、LimitRange、Pod Security、Policy/Webhook
交付控制面 | GitOps、Helm/Kustomize、渐进式发布、回滚
工作负载控制 | Deployment/StatefulSet/Job/Operator、队列与优先级
基础设施 | 多节点池、CNI、CSI、Runtime、GPU/特殊设备
可观测与治理 | Metrics/Logs/Traces、事件、成本、SLO、容量
容灾 | etcd 备份恢复、控制面 HA、节点重建、跨集群预案
```

## 扩展点怎么选

| 需求 | 优先选择 | 原因 |
|---|---|---|
| 默认字段、校验安全策略 | Mutating/Validating Admission | 写入 etcd 前统一治理 |
| 管理有生命周期的领域对象 | CRD + Controller/Operator | 使用声明式状态与 Reconcile |
| 改变节点可行性或排序 | Scheduler Framework Plugin | 进入 Filter/Score/Reserve 等调度阶段 |
| 简单批任务排队和配额 | Kueue/Volcano 等成熟系统 | 避免自研完整调度器 |
| 周期性检查和修复 | Controller | 可幂等重试并记录 Status |

## 关键权衡

### 单集群还是多集群

单集群资源利用率和治理一致性更好，但故障域与权限面更大；多集群隔离和容灾更强，但会增加发布、流量、配额和观测复杂度。通常按环境、地域、监管边界和故障域拆分，而不是每个团队一个集群。

### Webhook 可靠性

Webhook 位于 API 写链路，超时或不可用会影响整个集群对象创建。应设置短超时、明确 `failurePolicy`、高可用部署、避免外部依赖，并监控延迟和拒绝率。能用内置策略完成的，不要默认上 Webhook。

### 状态与幂等

Controller 不应把关键状态只放在内存；以 API 对象 Spec/Status、Finalizer 和外部系统的可查询状态为依据。每次 Reconcile 都从当前事实重新计算下一步，使重试、主备切换和事件重复仍然安全。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何设计 Kubernetes 多租户平台？</div>
<div class="qa-a"><p>我会从身份、隔离、资源和运营四层设计：OIDC/RBAC 与审计确定谁能做什么；Namespace、NetworkPolicy、Pod Security 和 Secret 管理隔离工作负载；ResourceQuota、LimitRange、PriorityClass 和队列实现保障与公平；GitOps、可观测、成本归集和自助门户提供持续运营。对强不信任租户还要考虑独立节点池、Sandbox Runtime 甚至独立集群。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何保证一次 Kubernetes 集群升级安全？</div>
<div class="qa-a"><p>先核对版本偏差和废弃 API，升级前验证 etcd 备份与恢复；在测试集群和少量节点池做 Canary，控制面按支持顺序升级，再滚动节点。使用 PDB、Surge 节点、Drain 和业务 SLO 控制影响，同时验证 CNI、CSI、Runtime、Device Plugin、Webhook 与 Operator 兼容性，出现异常按预案停止扩散或回滚节点镜像。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何设计批训练与在线推理共存的集群？</div>
<div class="qa-a"><p>先用节点池、taint/toleration 和优先级建立基础隔离；在线推理按 SLO 保留容量并快速扩缩，批训练通过队列、配额、Gang 和可 Checkpoint 抢占使用弹性资源。调度同时考虑 GPU 型号、拓扑和共享干扰，监控不仅看利用率，还要看推理尾延迟、训练 JCT、抢占浪费和单位成本。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何设计一个多租户 GPU Kubernetes 平台？</div>
<div class="qa-a">
<div class="qa-summary">先定义租户保障与 SLO，再把平台拆成身份准入、资源抽象、队列调度、节点运行时、可观测和故障恢复六层。</div>
<div class="qa-section"><div class="qa-section-title">核心架构</div><p>OIDC/RBAC/Namespace 确定身份；Quota/Queue 定义保障和借用；整卡、MIG、HAMi 等资源通过 Device Plugin/DRA 暴露；Scheduler 做 Gang、拓扑、公平和抢占；GPU Operator 管节点软件栈；DCGM 与业务指标共同提供健康和计费。</p></div>
<div class="qa-section"><div class="qa-section-title">关键权衡</div><p>强隔离和高利用率冲突：生产推理优先整卡/MIG，研发任务可共享；空闲保障资源可以借用，但必须有有界回收和 Checkpoint-aware Preemption。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>只设计 Scheduler 不够，还要说明资源账本、任务状态、故障域、升级和租户可观测性。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 训练任务的队列、配额和公平性系统怎么设计？</div>
<div class="qa-a">
<div class="qa-summary">用作业级队列做准入，给租户配置保障额度和上限，空闲资源允许借用，需求恢复时按代价有界回收。</div>
<div class="qa-section"><div class="qa-section-title">核心链路</div><p>TrainingJob 进入 LocalQueue/业务队列，Admission Controller 根据 ClusterQueue、ResourceFlavor 和 cohort 判断能否准入；Scheduler 只处理已准入 Pod。公平性可结合 DRF、权重和年龄，避免大作业饿死可用 Reservation，等待窗口可用 Backfill。</p></div>
<div class="qa-section"><div class="qa-section-title">抢占策略</div><p>受害者得分综合超额借用量、优先级、Checkpoint age、重启成本和能否释放目标拓扑，不用简单的“最低优先级先杀”。</p></div>
<div class="qa-section"><div class="qa-section-title">指标</div><p>等待时间、JCT、保障满足率、借用率、抢占浪费、GPU 碎片和队列饥饿时间。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何同时解决 GPU 碎片和拓扑质量？</div>
<div class="qa-a">
<div class="qa-summary">把型号、显存、Gang 和拓扑作为可行性约束，把放置后碎片、通信距离和干扰作为优化目标，并为大任务保留完整资源集合。</div>
<div class="qa-section"><div class="qa-section-title">方案</div><p>维护 GPU/NVLink/NIC/NUMA 拓扑画像；Filter 只保留满足硬约束的节点集合，Score 做 topology-aware bin packing；小任务填已有碎片，大任务拿完整节点或 NVLink island；Reservation 防止大任务一直等不到连续资源，Backfill 在保留窗口内运行短任务。</p></div>
<div class="qa-section"><div class="qa-section-title">重排边界</div><p>在线 Defragmentation 必须考虑训练 Checkpoint、推理 SLO 和迁移成本；MIG geometry 重配通常需要维护窗口。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 平台的监控和 SLO 怎么设计？</div>
<div class="qa-a">
<div class="qa-summary">同时监控业务结果、调度效率、Kubernetes 控制链路和 GPU 硬件，避免把 GPU-Util 当成唯一目标。</div>
<div class="qa-section"><div class="qa-section-title">指标层次</div><p>业务层看推理 P99/错误率、训练吞吐/JCT；调度层看排队、失败原因、碎片和抢占；节点层看 kubelet/runtime/Device Plugin；硬件层看 SM Active、显存、功耗、温度、ECC/Xid、PCIe/NVLink；平台层看租户保障和单位成本。</p></div>
<div class="qa-section"><div class="qa-section-title">告警与归因</div><p>告警必须关联 Job、Pod、Node、GPU UUID 和租户，保留事件时间线。Xid 等硬故障触发自动隔离，性能异常先比较业务吞吐和通信/数据加载指标。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>高 GPU-Util 可能来自等待、无效 Kernel 或共享干扰，不等于用户任务完成得更快。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何安全升级 NVIDIA Driver、Container Toolkit、Device Plugin 和 GPU Operator？</div>
<div class="qa-a">
<div class="qa-summary">先锁定兼容矩阵并在独立节点池 Canary，再按“隔离节点—迁移任务—升级节点栈—运行 Canary—逐批放量”滚动执行。</div>
<div class="qa-section"><div class="qa-section-title">升级准备</div><p>明确 Driver、Kernel、CUDA、Toolkit、containerd、Device Plugin、Operator 和 MIG 配置的版本组合；验证镜像、GitOps values、回滚节点镜像和训练 Checkpoint。不要在同一节点让宿主机包管理器和 Driver Container 同时管理驱动。</p></div>
<div class="qa-section"><div class="qa-section-title">执行</div><p>Cordon/Drain 一个 Canary 节点池，升级后验证 <code>nvidia-smi</code>、CDI、Node Allocatable、CUDA Canary、NCCL、DCGM 和 Xid；观察稳定窗口后分批推进。失败时停止扩散并回滚节点镜像或 Operator values。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>GPU 节点 Ready 不代表 GPU 栈 Ready；必须等 Device Plugin、Validator 和业务 Canary 全部通过。</p></div>
</div></div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何设计 GPU 节点故障隔离和训练任务自动恢复？</div>
<div class="qa-a">
<div class="qa-summary">用快速检测和资源隔离控制故障扩散，用 Job Controller、Checkpoint 与 Elastic/Rendezvous 降低恢复时间。</div>
<div class="qa-section"><div class="qa-section-title">检测与隔离</div><p>DCGM、NPD、kubelet 和网络监控发现 Xid/ECC、GPU 掉卡、Node NotReady 或 NCCL Hang；自动给节点 taint/cordon，Device Plugin 标记 Unhealthy，并保存硬件和任务时间线。</p></div>
<div class="qa-section"><div class="qa-section-title">恢复</div><p>小规模 Worker 故障可由 PyTorch Elastic 等重建成员；固定 world size 或大故障从最近可验证 Checkpoint 整组重启。恢复前确认替代节点拓扑、镜像、数据和 Checkpoint 可访问，并避免任务再次落回故障节点。</p></div>
<div class="qa-section"><div class="qa-section-title">指标</div><p>检测时间、隔离时间、MTTR、Checkpoint age、恢复成功率和故障导致的 GPU 小时损失。</p></div>
</div></div>

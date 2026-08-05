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

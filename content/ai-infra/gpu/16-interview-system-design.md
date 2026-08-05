## 问题定义

设计一个多租户 GPU 平台，不是简单把 `nvidia.com/gpu` 加到 Pod limits。系统需要同时解决设备接入、资源抽象、调度放置、共享隔离、作业生命周期、可观测性、故障恢复与成本治理。

## 目标与约束

| 目标 | 需要回答的问题 |
|---|---|
| 利用率 | 整卡、大卡小任务、碎片和空闲资源怎么处理？ |
| 性能 | 如何避免共享干扰，如何保证训练/推理 SLO？ |
| 公平性 | 队列、租户、项目之间如何配额、借用和回收？ |
| 可用性 | 掉卡、Xid、节点故障、作业 Hang 怎么恢复？ |
| 可运营性 | 如何计量 GPU·hour、显存·hour、排队时间和成本？ |

## 核心架构

```flow
节点资源层 | Driver、Container Toolkit/CDI、Device Plugin/DRA、DCGM
资源目录层 | 型号、显存、MIG Profile、拓扑、健康与租户标签
准入与队列层 | 默认值、配额校验、优先级、Kueue/Volcano
调度层 | Gang、拓扑、Bin Packing、共享干扰、抢占与 Backfill
运行层 | Job/Operator、Checkpoint、重试、弹性伸缩
观测与治理层 | SLO、GPU 健康、利用率、成本、审计与容量规划
```

## 关键权衡

### 资源抽象

- 整卡：路径最简单、隔离清楚，适合大训练和稳定推理。
- MIG：强隔离，适合规格固定、SLO 明确的小推理；需要管理 Profile 碎片与重配。
- MPS/Time-Slicing：提高轻负载利用率，但必须接受共享干扰和故障域扩大。
- HAMi 等方案：可表达显存/算力份额，但要验证限制精度、兼容性、升级和故障恢复。

### 调度策略

先满足硬约束：型号、显存、健康、节点池、拓扑和 Gang；再对可行节点打分：碎片、NVLink/NIC 距离、干扰、能耗和数据位置。训练任务通常重视 Gang、拓扑与 Checkpoint；在线推理更重视 SLO、容量冗余和快速扩容。

### 配额与抢占

使用“保障额度 + 弹性借用 + 有界回收”。抢占前要计算收益、重启成本和 Checkpoint 新鲜度，避免为了释放一张卡导致多机训练整体重启。

## 故障与扩展

- Device Plugin/Driver 故障：节点隔离，停止新任务进入，保留诊断现场。
- Xid/ECC/掉卡：标记设备或节点不健康，驱逐策略要区分训练和在线推理。
- 训练节点故障：依赖 Job Controller、Checkpoint 和 Rank 重建。
- 调度器故障：队列状态和资源账本应可重建，绑定操作保持幂等。
- 指标异常：监控业务 SLO 与硬件指标，避免仅根据 GPU-Util 自动扩缩容。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何设计 GPU 资源调度的 Score 函数？</div>
<div class="qa-a"><p>先把不满足型号、显存、健康、拓扑硬约束的节点在 Filter 阶段排除；Score 再组合碎片、拓扑距离、共享干扰、数据局部性和能耗。各项必须归一化并配权重，同时记录每次打分理由，便于解释为什么任务落在某个节点。训练和推理应使用不同 Profile，不能用一套权重解决所有工作负载。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么只使用 Kubernetes 原生整数 GPU 不够？</div>
<div class="qa-a"><p>整数 Extended Resource 能完成基本设备数量调度，但无法天然表达显存容量、型号属性、互联拓扑、共享干扰和动态配置。平台通常需要标签/亲和性、调度插件、队列系统，以及 Device Plugin/DRA 或 GPU 共享方案共同补足这些语义。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何衡量 GPU 平台是否做好了？</div>
<div class="qa-a"><p>至少看排队时间与 JCT、GPU·hour 有效利用、任务成功率、SLO 违约率、碎片率、抢占浪费、故障恢复时间和单位有效 Token/训练样本成本。利用率只是一项过程指标，不能替代用户侧吞吐、延迟与成本。</p></div>
</div>

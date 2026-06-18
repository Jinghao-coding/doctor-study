## 一句话结论

GPU 调度工业场景题不要背单个算法，而要先识别场景类型：异构资源、多租户配额、Gang/组调度、Backfill、抢占、碎片治理、拓扑感知、训练/推理混部、海量小作业、弹性训练、故障恢复。每类题都按同一套路回答：**题目边界 -> 硬约束 -> 优化目标 -> 调度策略 -> 工程落地 -> 指标验证 -> 风险兜底**。

## 场景题总览

| 场景 | 面试官真正想看 | 关键词 |
|---|---|---|
| 异构 GPU 调度 | 你是否能把 GPU 从“数量”升级成 flavor / 显存 / 性能 / 拓扑资源 | `ResourceFlavor`、node pool、型号匹配、性能归一 |
| 多租户配额 | 你是否理解公平和利用率冲突 | quota、fairshare、cohort、借用、回收 |
| Gang / 组调度 | 你是否知道分布式训练 All-or-Nothing 语义 | PodGroup、minAvailable、准入、死锁 |
| Backfill | 你是否能处理大任务等资源时的小任务填空 | 短作业、预计时长、reservation |
| 抢占 | 你是否知道 GPU 训练抢占代价很高 | priority、checkpoint、victim cost |
| 碎片治理 | 你是否能解释 GPU 利用率低的结构性原因 | bin packing、defrag、reservation |
| 拓扑感知 | 你是否知道同样 GPU 数量性能可能差很多 | NVLink、NVSwitch、RDMA、NUMA、NIC affinity |
| 训练/推理混部 | 你是否能保护在线 SLO | MIG、MPS、time-slicing、priority、isolation |
| 海量小 GPU 作业 | 你是否能考虑调度器吞吐和显存切分 | fractional GPU、best-fit、batch scheduling |
| 弹性训练 | 你是否能把调度和训练框架语义结合 | min/max workers、elastic quota、world size |
| 故障恢复 | 你是否能把调度和稳定性闭环 | DCGM、Xid、drain、reschedule、checkpoint |

## 通用回答骨架

```flow
澄清场景 | 训练/推理/评测/小作业，单 Pod 还是多 Pod，在线还是离线
定义资源 | GPU 型号、显存、CPU、内存、网络、存储、拓扑、故障域
确定硬约束 | 显存够、型号兼容、Gang 满足、SLO 不破、租户 quota 不越界
选择目标 | 吞吐、等待时间、JCT、公平性、SLO、利用率、成本
设计策略 | 队列排序、准入、Filter/Score、Backfill、抢占、弹性
工程落地 | Kueue/Volcano/YuniKorn/Scheduler Plugin/Operator/metrics
验证效果 | queue time、JCT、GPU util、fragmentation、SLO violation、preemption cost
```

## 1. 异构 GPU 调度

### 题目

集群里有 A10、A100、H100 等不同 GPU，显存、算力、互联能力都不同。用户提交训练/推理任务时只写“需要 N 张 GPU”，导致高端卡被低端任务占用，低端卡又跑不了大模型。你会怎么设计调度？

### 解题思路

| 步骤 | 方案 |
|---|---|
| 资源抽象 | 把 GPU 建模成 `flavor`：型号、显存、算力、互联、可用精度、成本 |
| 作业画像 | 记录任务最低需求：显存、算力、精度、是否需要 NVLink、是否支持降级 |
| 队列分池 | 按 GPU flavor / node pool 分池，避免强弱卡混成一个 `nvidia.com/gpu` |
| 匹配策略 | 先满足硬约束，再按性价比或性能归一化打分 |
| 降级策略 | 允许任务声明 preferred / acceptable flavor，资源紧张时降级 |
| 观测指标 | 不同 flavor 的利用率、等待时间、错配率、单位任务成本 |

### 回答要点

不要只说“打 label”。更完整的回答是：label 只是表达方式，核心是资源语义。工业系统里可以用 Kueue 的 `ResourceFlavor` 表达不同实例类型、GPU 型号或拓扑域；也可以在自研调度器里维护 `GPUFlavor` 表，把任务需求和资源池做匹配。

<div class="qa-summary">面试金句：异构 GPU 调度的核心不是“识别型号”，而是把型号、显存、性能和成本变成可调度语义。</div>

## 2. 多租户配额与弹性借用

### 题目

多个团队共享 GPU 集群。每个团队有保障配额，但某些团队白天不用，另一些团队任务排队。如何既保证公平，又提高整体利用率？

### 解题思路

```flow
基础配额 | 每个团队有 nominal quota / deserved quota
空闲借用 | 低于配额的队列暂时借给高需求队列
公平排序 | 按 dominant share / fairshare / quota debt 排队
回收机制 | 原配额团队需要资源时，回收借用资源
抢占策略 | 优先抢占低优先级、借用资源、checkpoint 新鲜的任务
```

| 机制 | 作用 | 风险 |
|---|---|---|
| Hard quota | 强公平 | 利用率低，空闲配额不能被借 |
| Elastic quota | 空闲资源可借 | 需要可解释的回收策略 |
| Cohort | 多个队列共享一组可借资源 | 策略复杂，容易出现争议 |
| Fairshare | 按权重分空闲资源 | 要处理优先级和长期债务 |
| Preemption | 快速归还资源 | GPU 训练抢占代价高 |

### 工业映射

- Kueue：`ClusterQueue` 管资源池和 quota，`Cohort` 支持队列之间借用。
- Volcano：Queue resource management 支持 reclaim / preempt 等队列资源治理。
- Run:ai / KAI：常见概念是 deserved quota、over-quota、fairshare。

<div class="qa-summary">面试金句：多租户 GPU 调度不是“平均分卡”，而是“保障配额 + 空闲借用 + 可解释回收”。</div>

## 3. Gang / 组调度

### 题目

一个分布式训练任务需要 8 个 worker 同时启动。默认 Kubernetes 逐 Pod 调度，可能先启动 7 个 Pod，最后 1 个卡住，前 7 个占着 GPU 但无法训练。怎么解决？

### 解题思路

| 步骤 | 方案 |
|---|---|
| 建模 | 把一组 Pod 抽象成一个 Job / PodGroup / Workload |
| 准入 | 只有资源满足 `minAvailable` 时才允许整体进入调度 |
| Reserve | 先为整组预留资源，避免部分占用 |
| Timeout | 超时不能满足时释放 reservation |
| Queue | 组任务在队列中等待，避免污染普通 scheduler |
| Backfill | 大 gang 等待时允许短任务填空 |

### 常见追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Gang Scheduling 的缺点是什么？</div>
<div class="qa-a"><p>主要是 head-of-line blocking 和资源空等。大任务需要整组资源，如果一直凑不齐，会堵住队列。解决方式是分队列、reservation timeout、backfill、elastic gang、aging，以及把 min/max worker 语义暴露给训练框架。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Gang 和普通优先级抢占怎么结合？</div>
<div class="qa-a"><p>抢占必须 gang-aware。不能只抢一个 Pod，而要判断抢占后是否能让整个 incoming gang 成功启动；victim 也最好按 Job/Gang 粒度选择，避免把别人的分布式训练打残。</p></div>
</div>

## 4. Backfill：大任务等资源，小任务如何填空

### 题目

队首有一个 64 卡训练任务，但当前只有 48 卡空闲。后面有很多 1-2 卡短作业。直接 FIFO 会让 48 张 GPU 空等，怎么提高利用率又不饿死大任务？

### 解题思路

| 步骤 | 方案 |
|---|---|
| 为大任务估计最早启动时间 | 根据运行中任务预计释放时间和 reservation 计算 |
| 回填短任务 | 只允许预计能在 reservation 前结束的短任务运行 |
| 限制回填窗口 | 避免短作业不断插队导致大任务永远等不到 |
| 加 aging | 大任务等待越久优先级越高 |
| 观测 | backfill 命中率、reservation miss、queue time |

<div class="qa-summary">面试金句：Backfill 不是让小任务随便插队，而是在不破坏大任务 reservation 的前提下填碎片。</div>

## 5. 抢占与代价感知

### 题目

高优先级任务来了，资源不足。你会不会抢占低优先级任务？怎么选择 victim？

### 解题思路

抢占不是免费的，尤其是训练任务。victim 选择要考虑：

| 维度 | 含义 |
|---|---|
| 优先级 | 低优任务优先被抢 |
| 是否借用资源 | over-quota / borrowed 任务优先被回收 |
| checkpoint 新鲜度 | checkpoint 越新，进度损失越小 |
| 已运行时间 | 刚运行不久的任务沉没成本低 |
| 释放资源匹配度 | 释放的 GPU 型号、数量、拓扑是否正好满足 incoming |
| 重启成本 | 镜像、数据、NCCL 初始化、模型加载成本 |
| 是否 gang | 避免只杀分布式任务的一部分 |

```flow
找候选 victim | 低优先级、借用资源、可抢占
估算收益 | 释放 GPU 数量、型号、拓扑、CPU/内存
估算代价 | checkpoint age、运行时长、重启成本、SLO 影响
选择集合 | 最小代价满足 incoming gang
优雅终止 | 通知 checkpoint，超时强杀
```

<div class="qa-summary">面试金句：GPU 抢占不是 kill 低优 Pod，而是用最小进度损失换足够可用资源。</div>

## 6. GPU 碎片治理

### 题目

集群总 GPU 空闲很多，但大任务总是排不上，因为每台机器只剩 1-2 张卡，凑不出完整 8 卡节点。怎么治理碎片？

### 解题思路

| 碎片类型 | 例子 | 治理方式 |
|---|---|---|
| 卡数碎片 | 每节点剩 1 卡，8 卡任务跑不了 | bin packing、reservation、defrag |
| 显存碎片 | 同卡剩余显存零散，小显存作业能跑，大显存作业不能跑 | best-fit、fractional GPU 分桶 |
| 多维碎片 | GPU 有剩余但 CPU/内存不够 | 多维打分、CPU/GPU 配比感知 |
| 拓扑碎片 | 卡数够但 NVLink 域被拆散 | 保留完整 clique / node group |
| 队列碎片 | 某队列有资源但无任务，另队列排队 | elastic quota / borrowing |

回答时先说碎片的类型，再说策略组合：放置阶段用 bin packing 保留大块；队列阶段用 backfill 填小洞；资源池阶段按 flavor / topology 分池；长期用 defrag 或迁移低优任务整理资源。

## 7. 拓扑感知调度

### 题目

同样申请 8 张 GPU，为什么放在同一 NVSwitch 节点和跨 4 个节点性能差很多？调度器怎么感知拓扑？

### 解题思路

| 并行策略 | 通信特征 | 放置偏好 |
|---|---|---|
| TP | 每层高频 AllReduce/AllGather | 同节点 NVLink/NVSwitch |
| PP | 相邻 stage 传 activation | 相邻 stage 尽量近 |
| DP | 每步梯度 AllReduce | 可跨节点，但需要 RDMA |
| EP/MoE | All-to-All | 避免跨拥塞域 |

落地方式：

- 短期：node label + scheduler plugin + GPU/NIC/NUMA 拓扑缓存。
- 中期：device plugin 上报拓扑信息，调度器自定义 Score。
- 长期：DRA / ResourceSlice 表达设备级属性和拓扑。

<div class="qa-summary">面试金句：拓扑感知调度优化的是 rank 通信图到硬件拓扑图的映射代价。</div>

## 8. 训练和推理混部

### 题目

同一批 GPU 既跑在线推理，也跑离线训练。如何提高利用率，同时保证推理 P99 不受影响？

### 解题思路

| 隔离方式 | 隔离强度 | 适用场景 |
|---|---|---|
| 物理节点隔离 | 最强 | 核心在线推理，严格 SLO |
| MIG | 强 | A100/H100 上推理 + 小任务混部 |
| MPS | 中 | 可接受一定干扰的多进程共享 |
| Time slicing | 弱 | 离线推理、实验任务 |
| 只按优先级抢占 | 弱 | 可重试低优训练任务 |

回答要点：

1. 推理 SLO 是硬约束，训练是可让步任务。
2. 先用节点池或 MIG 保护强 SLO 推理。
3. 对可混部场景，用限额、优先级、监控和自动驱逐保护推理。
4. 观测 P99、TPOT、GPU memory、SM/HBM、context switch 和训练吞吐。

## 9. 海量小 GPU 作业调度

这个场景已经单独展开：海量 C++ 短作业、几 GB 显存、同卡多进程、异构 GPU/CPU/内存配比。核心是显存主导的在线多维装箱。

关键回答：

```flow
资源画像 | actual gpu_mem/cpu/mem/duration
GPU flavor 分池 | 型号和显存容量隔离
候选索引 | remaining memory buckets + machine residual CPU/mem
Best-fit | 减少显存碎片，保留大块资源
Batch scheduling | 支撑几千万作业规模
反馈预测 | 修正用户申报，降低 OOM 和过度预留
```

## 10. 弹性训练调度

### 题目

训练任务能接受 4-8 个 worker，资源不足时希望先用 4 个跑起来，有资源再扩到 8 个；节点故障时也希望缩容继续。调度器怎么支持？

### 解题思路

| 问题 | 方案 |
|---|---|
| 如何表达弹性 | `min/target/max` workers，或 elastic workload |
| 如何准入 | 至少满足 min 才启动，target/max 作为扩容目标 |
| 如何扩容 | 有空闲资源时增加 worker，训练框架重建 rendezvous |
| 如何缩容 | 节点故障或抢占时减少 worker，继续训练 |
| 一致性风险 | world size 变化影响 batch size、学习率、BN、数据切分 |
| 调度风险 | 扩容不能无限抢占别人，要受 quota/fairshare 约束 |

<div class="qa-summary">面试金句：弹性训练不是单纯调度问题，它要求调度器、训练框架和 checkpoint/rendezvous 协同。</div>

## 11. 故障感知调度

### 题目

GPU 集群经常出现 Xid、ECC、NVLink 错误、节点 NotReady。调度器如何避免把任务调到坏资源上？运行中故障如何恢复？

### 解题思路

```flow
健康采集 | DCGM / node exporter / kubelet condition / IB metrics
资源标记 | node taint、GPU device health、unschedulable
调度过滤 | Filter 阶段排除坏卡、坏节点、拥塞域
任务恢复 | 重调度、弹性缩容、checkpoint 重启
闭环治理 | 故障统计、自动隔离、维修后恢复、容量扣减
```

指标：

- GPU Xid / ECC / temperature / power。
- NVLink error、PCIe replay、IB symbol error。
- Node condition、kubelet/runtime health。
- 任务失败率、重试率、checkpoint 恢复时间。

## 工业系统对照

| 系统 | 适合回答的点 |
|---|---|
| Kubernetes default scheduler | Filter/Score/Preemption 基础框架，但缺少批调度、Gang、公平队列、GPU 拓扑 |
| Volcano | Gang、Queue、Binpack、Reclaim、Preempt，适合批训练和大数据场景 |
| Kueue | LocalQueue、ClusterQueue、ResourceFlavor、Cohort、quota borrowing，适合准入队列和多租户 |
| YuniKorn | 层级队列、Application 调度、Gang、reservation，适合多租户批处理和 Spark/Hadoop 风格负载 |
| Run:ai / KAI | quota/fairshare、GPU fractions、over-quota、AI 工作负载 GPU 共享 |
| 自研 Scheduler Plugin | 需要深度定制拓扑、干扰预测、显存切分、训练框架语义时 |

## 参考资料

- Kueue docs: ClusterQueue / ResourceFlavor / Cohort / Fair Sharing。
- Volcano docs: Gang Scheduling、Queue Resource Management、Binpack、Preempt / Reclaim。
- Apache YuniKorn docs: hierarchical queues、Gang Scheduling、reservation。
- NVIDIA Run:ai Scheduler docs: fairshare、deserved quota、GPU fractions。
- Kubernetes docs: scheduler framework、PriorityClass、preemption。

## 关联模块

- `多资源公平调度`：DRF、Elastic Quota、借用和回收。
- `批调度、Gang 与 Backfill`：组调度、回填、抢占和 checkpoint。
- `拓扑感知调度`：GPU/NIC/NUMA/NVLink/RDMA 放置。
- `海量小显存 GPU 作业调度`：短作业高吞吐和 fractional GPU 装箱。

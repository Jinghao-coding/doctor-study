## 队列调度从哪些对象开始

Volcano 的 Queue 是组织资源分配和公平策略的逻辑对象，包含一组 PodGroup。它可以与物理 GPU 池关联，但 Queue 本身不等于一组固定节点。PodGroup 描述最低协同运行条件；VolcanoJob 描述用户作业的角色、副本和生命周期，由 controller 创建所需对象。

```text
用户作业 → API 校验身份、资源声明和运行配置
  → VolcanoJob controller 创建 Pod / PodGroup
  → Scheduler cache 汇总 Nodes、Jobs、Queues
  → OpenSession：插件注册排序、准入、可分配、可回收等函数
  → 按配置执行 actions：enqueue、allocate、reclaim 等
  → 分配计划提交，异步绑定 / 驱逐
  → Pod 真实状态经 watch 回到 cache，下一轮重算
```

Action 决定当前做哪一步，Plugin 提供该步使用的规则，Session 提供一次周期的状态。API 接收成功、准入成功、完成节点绑定、容器启动和服务健康，是不同的完成条件。

## 配额字段必须与插件一起解释

| 字段/状态 | 含义 | 容易混淆的地方 |
|---|---|---|
| `guarantee.resource` | 为队列保留的资源底线 | 与可借用的软份额不同，其他队列不能使用其保留额度 |
| `deserved` | capacity 插件使用的期望份额 | 超出后可成为回收对象；不是绝对的启动时间保证 |
| `weight` | proportion 插件计算份额的相对权重 | 不能当作所有插件都生效的固定份额 |
| `capability` | 队列资源使用上限 | 需结合集群及其他队列 guarantee 得到可用上界 |
| `reclaimable` | 该队列额外占用是否允许被其他队列回收 | 标记可回收不等于受害作业已有 checkpoint |
| allocated / inqueue / reserved | 已分配、已准入和暂记的不同用量 | 核算要明确集合并避免重复计数 |

配置应满足相应资源维度上的 `guarantee ≤ deserved ≤ capability`。已配置字段是否生效取决于插件和版本；不能只展示 Queue YAML 就声称所有保障都成立。

## 一次借用与回收

假设同一资源维度有 16 张可用 GPU，A/B 的 deserved 各为 8，capability 各为 16，guarantee 各为 2。A 使用 12 张、B 使用 4 张时，A 超出软份额使用了 4 张。B 需求增加到 8 张后，调度器可以从 A 选择可回收任务，释放相应资源供 B 使用。

需要检查受害任务所在节点和卡型是否满足 B、受害者是否允许驱逐、A 的最低保障与作业 gang 约束是否被破坏、终止耗时是否在容忍范围内。若 A 的作业不能拆分，回收量可能大于 4；如果没有合法受害者，B 可能继续等待。公平份额不能消除作业不可分割与拓扑限制。

## `enqueue`、`allocate`、`reclaim`、`preempt`、`backfill`

| Action | 当前主线中的关键职责 | 不能直接推导的能力 |
|---|---|---|
| enqueue | 检查 Job/PodGroup 准入，推进 Pending → Inqueue | 已准入不保证立即有节点可运行 |
| allocate | 排序队列/作业/任务，节点过滤与评分，尝试分配 | 总 GPU 数足够不代表型号、拓扑和 gang 都可满足 |
| reclaim | 在不同队列间选择可回收的额外占用，调用插件判断受害者 | 不负责应用 checkpoint 或服务流量迁移 |
| preempt | 在同队列任务间按规则抢占，也有作业内任务处理 | 不能把它概括为任意跨队列高优抢占 |
| backfill | 当前源码筛选 BestEffort 的 Pending/Pipelined task 进行补充调度 | 不是默认根据预计运行时间做 EASY 式作业插空 |

上述解释对应 classic actions 的源码，新增 gangpreempt/gangreclaim 等路径需分别核对。实际动作顺序由配置决定，不能背成不可变流水线。

## Gang 的承诺边界

调度器尝试为作业安排足够的成员，通过 JobReady 等条件决定分配计划是否可以提交，不满足时回滚本轮未提交的分配。`minMember` 表达最低成员数；可弹性作业的最低数可以小于全部副本。

Gang 减少了资源只给一部分 worker、其他 worker 长期等不到资源的问题，但 Kubernetes 绑定、镜像拉取、容器启动仍是异步过程。节点故障或启动失败需要 Job controller 的重试/重启策略处理；“原子调度条件”不等于所有进程在同一时刻健康。

## 异构队列与自动选卡

一个租户逻辑队列可以允许多种设备，但资源准入和实际放置必须保留设备维度：厂商、型号、显存、驱动/runtime、算子支持、互联、存储和镜像。不同 GPU 都用 `nvidia.com/gpu` 时，这个扩展资源名只表达数量；标签可以约束放置，却不会自动形成 A100/H100 分开的配额账本。

两种常见实现是按卡型建子队列并在上层统一入口，或保留统一逻辑队列、增加设备类别与用量核算。国产卡需要对应 device plugin / DRA 驱动和容器运行环境；把多个资源数字加在一起并不能让训练代码跨厂商兼容。

自动选卡应先过滤技术上不能运行的设备，再估计候选组合的排队时间、运行时间、成本及 SLO 达成情况。使用历史性能画像时记录模型、batch、并行规模、精度和输入分布。预测失准要回到实际反馈修正，并保留用户指定类型或禁迁移的约束。

## 并发准入与故障反馈

多个候选如果都只读取同一份已分配快照，可能同时看到余量。实现应在一次决策域内对通过检查的候选暂记额度，后续候选看到已准入与暂记占用；重试按作业 ID 去重；失败、终态和过期时释放。多副本 admission 服务还需统一决策域，例如 leader、带版本的持久状态或原子预留，不能依赖各进程独立 map 获得全局硬保障。

物理资源尚在 Terminating 时不能当作已经空闲。调度失败应记录可解释原因：配额不足、gang 不满足、设备不兼容、节点资源碎片、拓扑不满足、插件拒绝或绑定失败。业务平台状态最终要与 Kubernetes 真实对象收敛。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：基于 Volcano，怎样设计一套队列调度？</div>
<div class="qa-a"><p>先按租户和资源约束定义 Queue，把最低启动条件放到 PodGroup，作业生命周期交给 Job controller。调度层用配额插件判断准入和可分配额度，再按队列公平、作业优先级及节点约束分配。允许借用时明确软份额、硬上限和回收规则。执行后通过 watch 反馈，处理并发预留、重试和失败清理，并向用户暴露排队原因。平台特有规则可接插件或 Extender，但要说明启用配置与故障策略。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：一个 Queue 能混合 A100、H100 和国产卡吗？</div>
<div class="qa-a"><p>逻辑上可以统一管理，但必须分别表达资源类型和兼容性。配额核算要知道占用了哪种设备，放置时要检查镜像、算子、显存和通信。最容易落地的是统一租户入口、内部按卡型子队列管理；进一步自动选卡则需要性能画像与约束过滤。统一队列不意味着所有卡可以互换，也不意味着同一个分布式作业可以任意混卡。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q：高优任务回收在线推理资源，怎样保证服务？</div>
<div class="qa-a"><p>资源抢占与服务迁移需要协同。可计划回收时先在目标位置预留资源、启动和加载模型，通过健康与容量验证后接流量，再排空旧实例并释放。若本地调度器已强制驱逐旧 Pod，只能依靠存活容量和恢复速度降低影响。PDB 不能保证阻止所有调度抢占；需要预留容量、回收宽限期和明确的服务优先级规则。</p></div>
</div>

来源：[Kubernetes 抢占与 PDB](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)、[Queue 字段](https://volcano.sh/docs/concepts/queue/)、[调度框架](https://volcano.sh/docs/scheduler/overview/)、[capacity 插件](https://github.com/volcano-sh/volcano/blob/ac7f6a4dfe30d992c3b293ea5974c646e3da5da7/pkg/scheduler/plugins/capacity/capacity.go)、[preempt](https://github.com/volcano-sh/volcano/blob/ac7f6a4dfe30d992c3b293ea5974c646e3da5da7/pkg/scheduler/actions/preempt/preempt.go)、[reclaim](https://github.com/volcano-sh/volcano/blob/ac7f6a4dfe30d992c3b293ea5974c646e3da5da7/pkg/scheduler/actions/reclaim/reclaim.go)、[backfill](https://github.com/volcano-sh/volcano/blob/ac7f6a4dfe30d992c3b293ea5974c646e3da5da7/pkg/scheduler/actions/backfill/backfill.go)。核对日期：2026-10-29；异构选卡与业务恢复部分为基于约束的设计讨论。

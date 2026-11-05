## 分配计划先改变 Session，再推进实际执行

Volcano 的一次调度周期在 Session 中组织 Job、Queue、Node 和插件规则。尝试为一个作业分配多个 Task 时，需要让后续候选看见前面已经暂记的占用，也需要在方案不可行时撤销这些变化。`Statement` 负责记录这组操作。

下面的源码解释固定于提交 `ac7f6a4dfe30d992c3b293ea5974c646e3da5da7`，不把不同版本的分支和配置混在一起：

```flow
NewStatement | 创建本轮操作记录
Allocate / Pipeline / Evict | 修改 Session 内任务、节点及插件核算，记录操作
作业就绪检查 | 依据 JobReady、JobPipelined 等结果决定后续分支
Commit | 推进分配、驱逐等操作；Allocate 进入异步绑定链路
Discard | 逆序撤销尚未提交操作的 Session 变化
状态回流 | 实际 Pod 和节点变化经 cache 进入后续调度周期
```

源码入口：[Statement](https://github.com/volcano-sh/volcano/blob/ac7f6a4dfe30d992c3b293ea5974c646e3da5da7/pkg/scheduler/framework/statement.go)、[allocate Action](https://github.com/volcano-sh/volcano/blob/ac7f6a4dfe30d992c3b293ea5974c646e3da5da7/pkg/scheduler/actions/allocate/allocate.go)。

## Allocate 与 Commit 的执行位置

| 操作 | 该版本的关键行为 | 此时能确认什么 |
|---|---|---|
| `Statement.Allocate` | 更新 Session 中的 Task 状态和节点占用，调用分配回调，记录操作 | 本轮计划已暂记该分配 |
| `Statement.Pipeline` | 记录未来资源上的任务安排，更新相应核算 | 本轮存在等待资源释放的计划 |
| `Statement.Commit` 中的 allocate | 创建绑定上下文，通过 `cache.AddBindTask` 提交，更新为 Binding | 分配已交给绑定执行链路 |
| `Statement.Discard` | 逆序调用撤销操作，并触发相应释放回调 | 本轮未提交的暂记变化被撤销 |

`Allocate` 中对 Task 的节点字段赋值发生在调度器对象视图里，不能直接解释为 API Server 已保存 Pod 绑定。`Commit` 之后还需要绑定请求成功、kubelet 启动容器及应用完成初始化。

`Commit` 逐项推进操作并处理各项错误，既不是多个 Pod 的单次 API 原子提交，也不能在部分 Pod 已绑定后通过 `Discard` 自动撤销整个实际世界。Gang 控制的是满足作业条件后才推进分配，运行阶段的部分失败仍需生命周期控制器处理。

## Idle、Releasing 与 Pipelined

| 资源状态 | 含义 | 调度上的用途 |
|---|---|---|
| `Idle` | 当前资源视图中的空闲量 | 判断能否立即安排 Task |
| `Used` | 已使用量，包括仍在终止的 Pod | 不能因发出删除请求就减去全部占用 |
| `Releasing` | 正在释放的资源量 | 参与未来可用量估计 |
| `Pipelined` | 已经安排给等待任务的未来资源量 | 避免在同一视图内重复承诺 |

该版本的 `NodeInfo.FutureIdle()` 按资源维度计算：

```text
FutureIdle = Idle + Releasing - Pipelined
```

假设节点总计 8 张 GPU，`Idle=2`、`Used=6`，其中有 4 张处于 `Releasing`，另有 3 张已被未来任务计划占用，则 `FutureIdle=2+4-3=3`。`Releasing` 是已使用量中的一部分，不能再把它当作新增物理容量。

新的 3 卡任务可能满足未来资源条件，却不满足当前 `Idle=2` 的立即分配条件；新的 4 卡任务连未来条件也不满足。这里的状态都是调度核算，设备进程是否退出、驱动是否清理完毕仍要靠实际执行确认。

源码依据：[NodeInfo 与 FutureIdle](https://github.com/volcano-sh/volcano/blob/ac7f6a4dfe30d992c3b293ea5974c646e3da5da7/pkg/scheduler/api/node_info.go)。

## Pipeline 为什么不等于已经预订成功

在所核对的 `allocateResourcesForTask` 中，需求满足 `node.Idle` 时调用 `Allocate`；当前空闲不足、但满足 `node.FutureIdle()` 时尝试 `Pipeline`。这让调度器能够把正在释放的资源纳入计划。

需要继续检查计划如何跨越周期。在该提交中，`Statement.pipeline()` 的函数体为空，而 allocate 的外层分支只在 `JobReady` 时调用 `Commit`。因此，不能仅凭看到 `Pipelined` 字样就声称创建了一个跨重启、跨调度器共享的持久资源预约。

不同版本可能调整计划保留和提交流程。分析时应沿着“修改哪个对象 → 是否进入 cache → 是否写入 API → 下一轮怎样恢复”逐层核实。`FutureIdle` 也没有编码一个可靠的资源释放截止时间。

## Gang 可行性需要落到具体资源组合

假设 Job 最少需要 4 个各占 1 卡的 Worker。先暂记了 3 个 Worker，并不意味着它们应该立即绑定。如果第四个 Worker 被硬拓扑、卷或配额条件阻挡，提前启动前三个可能造成整组等待。

Statement 让调度器可以先检查一组安排，再决定提交或撤销。存在 Pipeline 时，还要检查作业是否仅满足未来可行条件，不能把所有未提交分支都概括为同一种回滚。实际就绪判断由启用的插件、作业最低成员及相关策略共同决定。

最低成员数满足也不意味着所有副本都已经安排；弹性作业的最低数可能小于总副本数。更不意味着后续通信组建立、数据读取和训练进展一定成功。

## 回收完成要有实际反馈

```text
选中受害者
  → Session 暂记释放计划
  → 提交驱逐操作
  → Pod 终止、应用退出和资源清理
  → 观察到节点资源可用
  → 新任务绑定、启动并达到业务就绪
```

这条链路中的 checkpoint、流量排空和模型重载需要应用或平台配合。调度器选择受害者，并不会自动得到应用恢复能力。把受害者标记为 `Releasing` 也无法给高优任务提供完整的启动时限保证。

平台可记录计划 ID、Job UID、受害 Pod UID、目标资源及各阶段时间，再根据真实对象对账。UID 能区分同名重建对象；操作超时后应先确认原动作结果，避免把延迟成功当作失败重复执行。这是平台实现建议，不是上述 Statement 接口自动提供的账本。

## 故障现象与责任位置

| 现象 | 优先检查 |
|---|---|
| 总 GPU 足够，Job 不就绪 | 最低成员、角色需求、各节点可行性、拓扑与卷约束 |
| Session 中已 Allocate，Pod 仍无 nodeName | 是否 Commit、AddBindTask 是否成功、绑定执行日志 |
| 受害者已选出，新任务仍等待 | 驱逐是否提交、终止是否完成、FutureIdle 是否被其他计划占用 |
| 出现 Pipelined 后重启，计划不再可见 | 对应版本的 cache/API 持久化与重建路径 |
| 部分 Pod 已运行，其他成员启动失败 | Job controller 的重试策略、Pod Events、应用组恢复 |
| 回收数量够了，目标作业仍放不下 | 释放资源的型号、节点、拓扑是否构成合法组合 |

源码与说明核对：2026-11-05。数值例子为资源核算演示。

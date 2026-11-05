## 场景一：Gang Scheduling

分布式训练通常需要足够的 Worker/Rank 形成协同运行集合；如果只调度了一部分，已占 GPU 的 Pod 可能一直等待其他成员，造成资源浪费。

```flow
作业提交 | 声明框架对应的最低成员数、角色和资源需求
队列准入 | 判断配额与准入策略
试分配或预留 | 逐步记入候选节点占用，避免重复承诺资源
整组就绪检查 | 判断是否满足最低运行条件
提交与执行 | 推进绑定和启动，根据失败位置释放预留或恢复作业
```

Gang 不代表所有 Pod 同一时刻物理启动，而是避免“部分成员长期占着资源却无法形成可运行集合”。

Scheduling Framework 的成组调度插件可以使用 Reserve、Permit 和 Unreserve；Volcano 则通过自身的 Session、Statement 和 Gang 插件组织分配。未提交的预留可以回滚，已经成功绑定或启动的 Pod 需要另行处理，不能假定多 Pod 绑定具有跨对象事务原子性。[Scheduling Framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)

## 场景二：Backfill

大任务等待成组资源时，可让预计运行时间较短的小任务填补空档，但必须保证不会推迟已承诺的大任务启动时间。

Backfill 依赖：

- 对等待作业建立保守预约窗口。
- 估计候选小任务的运行时间或可中断性。
- 超时可终止或 Checkpoint，避免小任务越跑越久。
- 监控估计偏差，防止系统性饿死大任务。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Backfill 和普通 Best-Effort 有什么区别？</div>
<div class="qa-a"><p>Backfill 以“不破坏前序作业的资源预约”为约束，利用可证明的时间空洞；普通 Best-Effort 只是低优先级使用空闲资源，若没有运行时长或回收机制，可能阻塞大任务。</p></div>
</div>

## 场景三：代价感知抢占

抢占决策应最小化总损失，而不是简单杀最低优先级：

| 成本 | 判断信号 |
|---|---|
| 已完成工作浪费 | 已运行时间、剩余时间估计 |
| 恢复成本 | 最近 Checkpoint、Checkpoint 大小、加载速度 |
| 分布式放大 | 抢占一张卡是否导致整个 Job 重启 |
| 业务影响 | Deadline、SLO、租户保障额度 |
| 碎片收益 | 抢占后是否真的组成目标资源集合 |

先尝试队列借用回收、缩容、暂停或迁移；只有收益明确时再终止任务。

## 场景四：弹性训练与故障感知

调度器只能决定资源，训练框架必须支持成员变化、Rendezvous、数据分片重平衡、学习率/Global Batch 语义和 Checkpoint。弹性扩容不一定提高效率：跨节点拓扑变差、通信增大或数据重分片都可能抵消新增算力。

故障处理要区分：

- 设备故障：Xid/ECC/掉卡，隔离设备或节点。
- Rank 故障：判断能否局部重启或需要整组恢复。
- 网络分区：防止重复训练成员和一致性问题。
- Checkpoint 故障：验证可读性和版本，而不只看文件存在。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么时候适合抢占一个训练任务？</div>
<div class="qa-a"><p>目标任务优先级或保障需求足够高，被抢占任务有较新 Checkpoint、恢复成本可控，而且释放资源能够形成目标任务真正需要的拓扑集合时。若只释放零散 GPU 或导致一个大作业整体重启，抢占收益可能为负。</p></div>
</div>

## 常见误区

- Gang 只配置 `minAvailable`，却没有超时、回滚和队列准入。
- Backfill 不估计运行时间，也没有终止边界。
- 把“Pod 能重启”误认为“训练状态能恢复”。
- 弹性扩容只看卡数，不重新评估通信和 Global Batch 语义。

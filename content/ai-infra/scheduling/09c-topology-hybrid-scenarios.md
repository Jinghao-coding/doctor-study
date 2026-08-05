## 一句话结论

GPU 调度的高阶问题不再是“有没有空卡”，而是空卡之间的连接、工作负载是否相互干扰，以及调度器能否在高提交速率下稳定做出决策。

## 场景一：拓扑感知放置

### 硬约束与软目标

- 硬约束：卡数、显存、型号、健康、同一故障域或指定互联能力。
- 软目标：优先同一 NVLink/NVSwitch 域、GPU 与 NIC 同 NUMA、减少跨 Socket/跨机通信。

```flow
采集拓扑 | GPU-CPU-NIC、PCIe Root、NVLink/NVSwitch、网络域
映射并行策略 | TP 更敏感带宽，DP 更依赖跨机 Collective
Filter | 排除不能形成所需拓扑集合的节点
Score | 比较通信代价、碎片、数据位置与拥塞
运行时校准 | NCCL 时间、链路吞吐和 Step Time 回写
```

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 Node 上有 8 张空卡，8 卡训练仍可能很慢？</div>
<div class="qa-a"><p>卡可能分属不同 PCIe Root 或 NUMA 域，GPU-NIC 路径也可能跨 Socket；调度数量满足但通信代价很高。还要检查进程 Rank 与拓扑映射、NCCL 选择的链路以及是否与其他任务争用互联。</p></div>
</div>

## 场景二：训练和推理混部

在线推理关心 P99、容量冗余和快速扩缩；离线训练关心吞吐、JCT 与 Gang。混部可提高利用率，但必须建立隔离和可回收边界：

| 策略 | 适用性 | 风险 |
|---|---|---|
| 独立节点池 | 最稳定、边界清楚 | 利用率可能较低 |
| MIG | 推理规格稳定、需要强隔离 | Profile 碎片和重配成本 |
| MPS/Time-Slicing | 轻负载或可容忍干扰 | P99 抖动、故障域扩大 |
| 低优先级训练借用 | 推理有稳定保留容量 | 回收速度与 Checkpoint 成本 |

混部决策要以推理 SLO 为硬约束，训练吞吐收益为优化目标；不能只因为 GPU-Util 低就自动塞入训练任务。

## 场景三：海量小 GPU 作业

短作业下，调度、镜像拉取、容器启动和结果提交可能比 GPU 计算本身更贵。设计重点从单次最优变成控制面吞吐：

- Admission 层做限流、合并和配额，防止 API Server 被突发请求打满。
- 调度 Cache 与索引减少全量扫描，用分层队列隔离租户。
- 尽量复用 Worker/容器或使用常驻执行器，摊薄冷启动。
- 镜像预热、数据局部性和批量提交降低 I/O 开销。
- 使用 Best-Fit/Backfill 控制显存碎片，但设置最大等待时间。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何评估调度器在海量小作业下是否成为瓶颈？</div>
<div class="qa-a"><p>分解提交到运行的时间：准入排队、Scheduling Cycle、Binding Cycle、kubelet/CRI 启动、镜像和数据准备。监控队列长度、调度吞吐、P95/P99 调度延迟、失败重试、API Server 和 etcd 压力，并对比作业实际 GPU 运行时间。如果控制面开销接近作业计算时间，应优先做常驻执行、批量化和缓存。</p></div>
</div>

## 常见误区

- 把拓扑标签当作静态真相，不处理设备故障和节点变更。
- 把训练吞吐优化直接套到在线推理，忽视尾延迟。
- 用共享机制提高名义利用率，却没有干扰监控和降级策略。
- 小作业只优化 Score 算法，不测 API、队列、绑定和启动链路。

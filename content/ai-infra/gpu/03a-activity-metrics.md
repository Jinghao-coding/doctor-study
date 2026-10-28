## GPU Util：有 kernel 执行的时间比例

`nvidia-smi utilization.gpu` 表示设备采样窗口内，至少一个 kernel 正在执行的时间占比，单位是百分比。设采样窗口为 `T`，其中有 kernel 执行的时间合计为 `t_busy`，则 `GPU Util = t_busy / T × 100%`。设备内部采样窗口、监控抓取周期和查询时间窗是三件事；每秒抓取一次，并不意味着设备精确统计了这整整一秒。[NVML 定义](https://docs.nvidia.com/deploy/archive/R535/nvml-api/structnvmlUtilization__t.html)

<div class="table-scroll">

| 观测 | 可能意味着什么、有什么影响 | 下一步判断 |
|---|---|---|
| 高 | kernel 执行时间连续；可能是有效计算，也可能是低效访存、通信或等待型 kernel | 看 SM 覆盖、实际带宽、热点 kernel 与业务吞吐 |
| 低 | 有较多无 kernel 的时间；可能流量少、CPU/I/O 供给慢、同步、阶段切换或提交开销大 | 在相同负载下对齐请求队列与 CPU/GPU 时间线；低需求时无需强行“拉高” |
| 持续为 0 | 所观测样本没有 kernel 活动，是闲置候选信号 | 核对数据有效性、进程归属、显存驻留和恢复请求；不能当作未来空闲保证 |

</div>

**100% 不等于全部 SM 满负荷，更不等于峰值 FLOP/s。** 一个小 kernel 连续运行也能让它很高。单纯的 CPU 等待或拷贝间隙不能直接解释同一张卡、同一窗口内持续 100% 的 kernel 活动；应检查其他进程、采样窗口或 GPU 上仍在执行的通信工作。

<div class="qa open" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU Util 为 20%，能把剩下 80% 算力借给另一个任务吗？</div>
<div class="qa-a"><p>不能直接这样算。20% 是历史窗口内有 kernel 执行的时间比例，不是资源配额，也不保证下一刻还有 80% 空间。要结合任务是否会恢复、显存能否容纳以及干扰情况决定。采用互斥门控时，则由恢复信号触发使用权交接。</p></div>
</div>

## SM Active：时间和 SM 覆盖共同决定

设 GPU 有 `N` 个 SM，观察时长为 `T`；`a_i(t)` 在第 `i` 个 SM 上存在活跃 warp 时为 1，否则为 0。直观地，`SM Active = Σ_i ∫a_i(t)dt / (N × T)`。它是跨 SM、跨时间的活动比例，通常以 0–1 或百分比显示。活跃 warp 包括等待内存的 warp，不只包含正在完成算术指令的 warp。[DCGM Profiling](https://docs.nvidia.com/datacenter/dcgm/latest/learn/modules/profiling.html)

**低值既可能是 SM 没铺开，也可能是时间上有空洞。** 例如假设有 100 个 SM：20 个 SM 活跃一整秒，或者 100 个 SM 只活跃 0.2 秒，SM Active 都约为 0.2；仅看平均值分不清这两种情况。前一种通常要检查 grid、batch 和任务规模，后一种先检查供给与调度间隙。

**高值说明多数 SM 在多数时间有驻留工作，但不保证工作推进得快。** 如果 active warp 多数在等待访存或依赖，仍可能吞吐低。应继续看 eligible warp、带宽、管线活动和执行时间。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU Util 高、SM Active 低，你怎么解释？</div>
<div class="qa-a"><p>我先保证两者对应同一设备和时间范围。如果 kernel 持续运行，但只覆盖少量 SM，就会出现这种组合。接着看 grid 和工作量，尝试增大可并行的工作；同时检查带宽是否已成限制，不能直接把“SM 没铺满”理解成一定能线性加速。</p></div>
</div>

## Occupancy：驻留多少 warp，不是有多少 warp 能立即执行

Occupancy 比较每个 SM 上驻留的 warp 数与硬件支持的最大驻留 warp 数。理论 occupancy 根据线程块大小、寄存器、共享内存和硬件上限计算；实际 occupancy 从运行期间观测。Nsight 的 `active`、`elapsed` 等归一化后缀与采集范围会影响数值，不能把不同工具中的同名百分比直接相除。[Nsight Compute Occupancy](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html#sections-and-rules)

假设某架构每个 SM 最多驻留 64 个 warp，某时刻驻留 16 个，则该时刻为 25%。这 16 个 warp 可能多数等待数据；它们不是 16 个“马上能发射”的 warp。

<div class="table-scroll">

| 观测 | 影响与可能原因 | 检查或优化 |
|---|---|---|
| 低 | 可用于隐藏延迟的 warp 少；也可能是每个线程需要更多寄存器/共享内存的合理选择 | 查每 block 资源、grid、尾部不均衡；比较调整前后 kernel 时间 |
| 高 | 驻留并发较多，有机会隐藏等待；仍可能全部卡在相同依赖上 | 查 eligible/issued、内存与同步，而不是继续追求驻留数量 |
| 理论高、实际低 | 工作量不足、block 时长不均或尾部阶段可能拉低实际值 | 查看各阶段与 block 工作量，而不是只改寄存器限制 |

</div>

强行限制寄存器以提高 occupancy，可能导致 spill 到 local memory，增加访存，反而变慢。**调优目标是执行时间，occupancy 是解释资源与延迟隐藏关系的中间量。**

## Eligible、Issued 与 Warp Stall：工作能否向前推进

`active/resident` 表示 warp 驻留；`eligible` 表示当前具备发射条件；`issued` 表示被调度器选中并发射。相关指标可能按每调度器、每周期计数，也可能是周期占比，应先读单位。它们不能混成一个“warp 利用率”。

Eligible 少、issue 槽频繁空闲，说明缺少可以执行的指令；原因可能是依赖、内存、同步或驻留工作不足。Eligible 多而部分 warp 未被选择，可能只是每周期发射能力有限：`Not Selected` 高并不必然是问题。只要持续有其他 warp 发射，某个 warp 等待不一定影响吞吐。

<div class="table-scroll">

| Stall 类型 | 核心含义 | 高时应核对什么 |
|---|---|---|
| Long Scoreboard | 等待 L1TEX 路径相关的依赖结果，例如 global/local/texture load | 缓存、访问合并、依赖链；不直接等同于 HBM 带宽饱和 |
| Short Scoreboard | 等待 MIO 路径相关依赖，常涉及 shared memory 等 | shared bank conflict、相关指令依赖和算子代码 |
| Barrier | 等待线程同步条件 | block 内负载是否不均、同步频率能否减少 |
| Math Pipe Throttle | 目标计算管线暂时无法接收更多工作 | 指令集中于哪条管线、是否可增加独立指令或减少冗余 |
| MIO Throttle | MIO 指令队列压力 | 指令密度、shared/local 等访问及发射瓶颈 |
| Not Selected | warp 可发射，但该周期选择了其他 warp | 先看 issue 是否充分；高值可能表示可选工作充足 |

</div>

Stall 指标可能来自采样次数或 warp 周期；分母不同，不能机械相加，也不能直接当成整个程序的停顿时间。**先确认存在未被隐藏的等待，再优化其原因。** [Nsight Compute Warp Stall Reasons](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html#warp-stall-reasons)

## Tensor 管线活动与 SM Throughput

Tensor 管线活动表示相关管线在统计周期中的活动程度。高值说明矩阵计算管线持续使用，但指令形状、精度、有效元素和额外计算仍影响实际 FLOP/s。低值对于搬运、归约、采样等任务可能正常；对于耗时占比很高的 GEMM，应检查 dtype、矩阵形状、选用的 kernel 和库。[DCGM Tensor Activity](https://docs.nvidia.com/datacenter/dcgm/latest/learn/modules/profiling.html)

Nsight 的 `SM Throughput`、`Compute Throughput` 等汇总通常由相关吞吐指标按工具规则组合，可能体现最繁忙的子管线相对峰值，**不是“所有 ALU 的平均忙碌程度”，也不能一律当作实际 FLOP/s/理论 FLOP/s。** 高值提示进一步展开子管线；低值提示查等待、工作规模和供给。不同架构先用工具查询可用指标及 breakdown。[Nsight Throughput Metrics](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html#metrics-structure)

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Occupancy 和 SM Active 都高，为什么还很慢？</div>
<div class="qa-a"><p>它们说明很多 SM 上驻留着工作，不保证这些工作每个周期都能发射。我会看 eligible warp 和 issue，再结合 stall 判断在等数据、依赖还是同步。即使发射充分，也要看执行的是有效计算还是重复搬运，最终用 kernel 时间和端到端吞吐验证。</p></div>
</div>

## 显存容量：Used、Free、Allocated、Reserved

设备显存 `Used/Free` 表示当前容量使用与剩余，单位是 byte、MiB 或 GiB；它包含的范围与框架统计不同。PyTorch 的 `memory_allocated` 统计张量等通过其分配器占用的内存，`memory_reserved` 统计缓存分配器管理的内存；CUDA context、其他库和其他进程的开销可能不在同一账本里。[PyTorch CUDA Memory Management](https://docs.pytorch.org/docs/stable/notes/cuda.html#cuda-memory-management)

<div class="table-scroll">

| 观测 | 对系统的影响 | 正确判断与动作 |
|---|---|---|
| 设备 Used 高、Free 低 | 并发、KV 增长和临时 workspace 空间受限，峰值时更易 OOM | 拆出权重、激活/KV、临时区、其他进程，估计峰值后再准入 |
| Used 低 | 容量有余量 | 不代表计算、带宽或互联也有余量；增加 batch 前检查对应瓶颈 |
| Reserved 明显高于 Allocated | 缓存池保留较多空间 | 可能是正常复用，也可能存在碎片；差值本身不是碎片率 |
| 平均 Used 不高但 OOM | 瞬时峰值、单次大申请、碎片、私有池或并发竞争可能使申请失败 | 查失败申请大小、峰值与内存快照，而不是只看低频面板 |

</div>

`empty_cache()` 释放符合条件的未使用缓存块，不能释放仍被张量引用的显存。KV 的逻辑块被释放后，如果引擎仍保留整个预分配池，设备层 Used 也可能不下降。**暂停计算、逻辑释放 KV、把显存归还给驱动，是三个不同动作。** [PyTorch empty_cache](https://docs.pytorch.org/docs/stable/generated/torch.cuda.memory.empty_cache.html)

<div class="qa open" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 显存占了 90%，GPU Util 为 0，矛盾吗？</div>
<div class="qa-a"><p>不矛盾。显存是状态驻留，GPU Util 是计算执行的时间活动。模型权重、KV 和框架缓存可以长期保留，但任务此时在等请求或用户操作。借给另一个任务前，需要检查剩余容量；把前一个进程停算，并不会自动腾出这 90% 显存。</p></div>
</div>

## 内存活动：utilization.memory 与 DRAM Active

`NVML utilization.memory` 是采样窗口内设备内存发生读写的时间占比；`DRAM Active` 是设备内存收发数据的周期比例。它们都描述活动，不能替代显存容量，也不能不加区分地当作实际字节带宽除以峰值。[NVML](https://docs.nvidia.com/deploy/archive/R535/nvml-api/structnvmlUtilization__t.html)、[DCGM DRAM Activity](https://docs.nvidia.com/datacenter/dcgm/latest/learn/modules/profiling.html)

高值说明内存接口持续有活动，可能是有效流式访问，也可能有重复或低效搬运。低值可能是计算密集、缓存复用充分，也可能是等待型访问、并行访存请求不足或上游没有供给。判断是否受带宽限制，还要看实际字节吞吐、访问效率和计算时间；带宽不高的内存依赖链也可能受访存延迟限制。

## 实际带宽、有效带宽与访存效率

设一次操作耗时 `t` 秒，实际在目标存储层传输了 `B_actual` 字节，则实际带宽是 `B_actual / t`。应用真正需要的数据量为 `B_useful`，则有效带宽是 `B_useful / t`。比较前明确是 HBM、L2、PCIe 还是网络，以及 GB/s（十进制）和 GiB/s（二进制）。缓存命中使某层流量变小，不能拿应用请求字节数直接当 HBM 实际流量。[CUDA 有效带宽](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#effective-bandwidth-calculation)

<div class="table-scroll">

| 观测 | 可能影响 | 下一步 |
|---|---|---|
| 实际带宽接近同环境可达上限 | 继续增加并行度可能难以提速，共置任务更容易相互争用 | 减少搬运、提高复用、融合或压缩；验证数值要求 |
| 实际带宽高、有效带宽低 | 很多流量没有转化为有用数据，浪费带宽 | 检查事务/sector 数、重复读取、数据布局与访问合并 |
| 实际带宽低、访存等待高 | 可能是依赖串行、请求不足、随机访问或同步，不能排除内存瓶颈 | 用时间线和 kernel 计数器区分延迟、发射和带宽限制 |
| 实际带宽低、计算吞吐高 | 数据复用可能良好，计算可能成为主要约束 | 核对热点计算管线和 Roofline，而非强行增加内存流量 |

</div>

教学例子：应用需要读取 32 MB，但分散访问导致目标层实际传输 128 MB，耗时 1 ms。有效带宽为 32 GB/s，实际带宽为 128 GB/s。访问合并后即使面板显示的实际带宽下降，只要任务耗时缩短，就是有效优化。这里的数字为构造示例，实际事务粒度和缓存行为取决于架构。

## L2 命中率与内存事务

L2 命中率通常按指定请求或 sector 计数，计算命中数除以总查询数；必须明确读、写、sector/request 的口径。高值常意味着复用好、HBM 流量减少，但大量重复访问也可能让命中率高而程序仍慢。低值可能是缓存容量不足、访问冲突，也可能是合理的一次性流式读取。**先问这些数据是否值得复用，再判断是否应该追求更高命中率。** [Nsight Memory Workload Analysis](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html#memory-workload-analysis)

访问合并讨论同一 warp 的访问能否用较少事务完成。事务数相对有效字节过多，通常会增加流量和延迟；改善数据布局、线程到数据的映射或分块可能有帮助。不是所有多 sector 访问都低效：先根据操作宽度和实际所需字节计算合理事务数。Shared memory bank conflict 同样要看额外事务和 kernel 时间，而不是只凭冲突计数判定整体瓶颈。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 显存带宽低，为什么 kernel 还可能受内存限制？</div>
<div class="qa-a"><p>带宽是单位时间传了多少数据，延迟是一次访问等多久。如果下一次访问依赖上一次返回，不能同时发出足够多请求，就可能一直等内存，但总带宽很低。此时要增加独立访问、改善局部性或隐藏延迟；单纯换一张峰值带宽更高的卡，收益未必明显。</p></div>
</div>

## 峰值与采样口径

低频设备采样可能漏掉短暂分配峰值。框架峰值计数应在目标区间开始前重置，并在异步工作完成后读取；同时保留设备侧和其他进程的记录。训练需区分前向、反向、优化器更新，推理需区分模型加载、Prefill、Decode 与缓存增长。**容量按可能出现的峰值和可执行的预算控制，不能按平均显存做硬保证。**

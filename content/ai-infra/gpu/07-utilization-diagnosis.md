## 从业务变化定位到执行原因

```flow
固定比较条件 | 模型、精度、输入长度、batch、缓存状态与设备配置
确认业务变化 | Step Time、TTFT/ITL、吞吐、失败率、排队或交还延迟
核对监控口径 | 设备/进程归属、时间窗口、数据新鲜度、单位与计数器类型
定位执行阶段 | CPU 供给、GPU kernel、拷贝、通信、同步、加载和恢复
分析热点 | SM/warp、实际带宽、管线、缓存、功率与频率
选择可验证动作 | 每次改变可解释的因素，比较同条件下端到端结果
```

**先判断有无等待需求，再讨论利用率偏低是否需要优化。** 没有请求时设备空闲是正常现象；队列持续积压而 GPU 存在执行空洞，才需要解释供给、准入或执行链路的问题。不存在脱离负载的统一“30% 以下不正常”规则。

## 指标组合与判别动作

<div class="table-scroll">

| 观测组合 | 可检验的解释 | 下一步证据 | 对应动作与代价 |
|---|---|---|---|
| Util、SM Active 都低，队列积压 | CPU、I/O、同步或提交使 GPU 出现间隙 | 对齐数据就绪、API 提交、kernel 起止 | 改善供给、批量化或减少同步；不能只扩大 GPU 配额 |
| Util 高、SM Active 低 | 持续 kernel 只覆盖少数 SM，也可能存在口径差异 | 同窗分卡数据、grid、batch 与时间线 | 增加并行工作或调整 kernel；收益受带宽等约束 |
| SM Active/Occupancy 高，eligible 少 | 驻留 warp 大多在等依赖、内存或同步 | stall 原因、issue 空洞、源码位置 | 缩短依赖、提高复用或增加独立工作；不是继续堆驻留数 |
| 内存活动高、实际带宽接近可达上限 | 访存流量限制推进 | 有效/实际字节、热点耗时、Roofline | 融合、复用或减少数据量；同时检查精度与寄存器代价 |
| 带宽低、Long Scoreboard 高 | 可能受内存延迟或串行依赖限制 | 访问模式、缓存、并行未完成请求 | 改善局部性或增加独立访问；不能仅凭低带宽排除访存瓶颈 |
| NCCL 耗时长、链路流量低 | 慢 rank、同步等待、小消息或拓扑异常 | 各 rank 进入 collective 的时间与消息规模 | 修复负载不均、合并消息或改进放置，先确定原因 |
| 显存平均不高却 OOM | 短峰值、碎片、私有池或其他进程竞争 | 失败申请大小、峰值、allocator snapshot | 调整并发、KV 预算和生命周期，保留足够峰值空间 |
| Util 高，时钟与吞吐下降 | 可能降频，也可能业务阶段改变 | clock event reason、功率/温度、相同阶段基线 | 处理已确认的功率/散热约束；不能只凭功率高推定异常 |

</div>

这些组合提供假设，不是排除其他原因的判决。多卡任务保留逐卡数据；“90% 和 10% 的均值为 50%”会掩盖明显的不均衡。不要让聚合后的平均值替代慢 rank 和热点分析。

## 监控、时间线和 kernel 分析分别解决什么

<div class="table-scroll">

| 工具层次 | 主要问题 | 测量限制 |
|---|---|---|
| nvidia-smi / DCGM / Prometheus | 哪个设备、何时出现利用率、容量或健康变化 | 采样不是完整事件轨迹；设备指标不自动等于进程贡献 |
| Nsight Systems / NVTX | CPU、CUDA API、kernel、memcpy 与同步在时间上如何交错 | 需要聚焦代表区间，并识别采集开销 |
| Nsight Compute | 热点 kernel 的 warp、管线、访存和资源限制 | 可能重放或序列化 kernel；不能把采集时的端到端耗时直接当正常性能 |
| 框架 profiler / 引擎请求指标 | kernel 对应哪个算子、请求处于哪个阶段 | CPU 时间、GPU 时间和异步重叠不能简单求和 |

</div>

可先只读设备状态，再对可控实验选择 profiling 范围：

```bash
nvidia-smi --query-gpu=timestamp,uuid,utilization.gpu,utilization.memory,memory.used,memory.free,power.draw,clocks.sm,temperature.gpu --format=csv -l 1
nvidia-smi -q -d POWER,CLOCK,TEMPERATURE,PERFORMANCE
ncu --list-sections
```

按安装版本列出可用 section/metrics 后，选择热点 kernel 与小范围采集；不默认在共享生产任务上执行全量 replay。采集器可能争用硬件计数器，暂停 profiling 的空白样本不能当作空闲。[Nsight Compute 采集机制](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html#metric-collection)、[Nsight Systems](https://docs.nvidia.com/nsight-systems/UserGuide/index.html)

## 闲置检测与使用权门控

**发现空闲与发现原任务恢复，采用的信号可能不同。** 借用前，可以用原任务持续无 GPU 活动和显存条件筛选；推理接管后，整卡指标混入推理工作，不能继续用整卡 Util 判断开发任务是否恢复。

对于 CUDA API 门控设计，开发侧的新计算请求可触发交还：先停止推理新提交，协调在途计算和多卡通信，再放行开发侧。指标用于验证切换后的活动和交还延迟。若两侧状态不能同时驻留，还要实际释放推理显存；关计算门不释放内存。

数据缺失应记为未知。若使用 max_over_time(...)=0，只能说明纳入统计的样本为零，不能证明采样间隙不存在短 kernel。多卡任务的整组回收要明确所有成员卡的条件，避免一张卡闲置就错误代表整组。

<div class="qa open" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU Util 长期 100%，业务吞吐还是低，你会怎么查？</div>
<div class="qa-a"><p>我先固定输入、batch 和时间窗口，确认高利用率来自目标任务。然后用时间线看 GPU 在执行计算、搬运相关 kernel 还是通信。若小 kernel 只覆盖少量 SM，查并行度；若 SM 活跃但 warp 难以发射，查等待；若带宽或某条管线接近上限，查有效工作与冗余。最后验证 step time 或达标吞吐，不能把 Util 本身作为优化终点。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 低利用率应该回收，还是先优化任务？</div>
<div class="qa-a"><p>先看任务是否确实在等待计算需求。如果开发者暂时没有 GPU 工作，可以按约定借用窗口；如果请求在排队但 GPU 没有被供给，就应该定位 CPU、I/O 或同步。回收策略还要满足使用权和恢复约定，不能把一个低利用率阈值同时当成性能诊断和删除任务的依据。</p></div>
</div>

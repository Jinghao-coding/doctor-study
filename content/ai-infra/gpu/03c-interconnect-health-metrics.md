## PCIe、NVLink 与网络吞吐

链路吞吐是统计区间内传输字节数除以时间，单位通常为 B/s 或 GB/s；网络规格也常用 bit/s，8 bit 才是 1 byte。明确 TX/RX 的观察端、单链路还是全部链路，以及单向还是双向。链路理论规格、协议有效吞吐、应用实际吞吐不是同一个数。[DCGM 互联指标](https://docs.nvidia.com/datacenter/dcgm/latest/learn/modules/profiling.html)

**高吞吐**说明链路承载了大量流量，若接近当前拓扑下的可达上限，模型加载、KV 迁移或集合通信可能受限。也要检查这些流量是否来自重复搬运。**低吞吐**可能是数据量小或通信被计算隐藏，也可能是小消息延迟、慢 rank、错误路径、NUMA 或链路异常。不能用“没有跑满带宽”排除通信瓶颈。

性能下降时，比较同一消息大小与并发下的实际路径，核对 PCIe 代际/宽度、GPU-NIC 拓扑、错误/重传及请求发起时刻。路径选择影响端到端吞吐，拓扑图本身不是实测带宽。

## NCCL 延迟、algbw 与 busbw

`algbw` 是集合通信操作的逻辑数据大小除以耗时；`busbw` 根据 collective 类型和参与 rank 数进行归一化。若 AllReduce 的逻辑数据大小为 `S` 字节、时间为 `t` 秒、rank 数为 `n`，nccl-tests 使用 `algbw = S/t`，`busbw = algbw × 2(n−1)/n`。**busbw 是测试的归一化口径，不是某一物理链路的直接读数。** [NVIDIA nccl-tests](https://github.com/NVIDIA/nccl-tests/blob/master/doc/PERFORMANCE.md)

<div class="table-scroll">

| 观测 | 可能意味着什么 | 怎么判断影响 |
|---|---|---|
| 大消息 algbw/busbw 高 | collective 吞吐较好 | 与相同 GPU 数、拓扑、数据类型和大小比较 |
| 小消息带宽低、延迟基本固定 | 固定启动和同步代价占比大 | 看每轮通信次数及其关键路径延迟，而不是只追带宽 |
| NCCL 时间长，但链路流量低 | 某些 rank 进入晚、同步等待或通信进展受阻 | 对齐各 rank 的计算结束和 collective 进入时刻 |
| NCCL 占用高但 step 不变慢 | 可能与计算充分重叠 | 看未被重叠隐藏的通信时间；不能把所有 kernel 时长直接相加 |

</div>

同步训练的整体进度受到慢 rank 限制。比较各 rank 的 step time、计算完成时刻和通信进入时间，可以区分“网络慢”和“大家在等一个计算慢的 rank”。多卡恢复还要保证 collective 的参与关系和顺序一致。

<div class="qa open" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU Util 都很高，但多卡扩展很差，是网络带宽不够吗？</div>
<div class="qa-a"><p>不一定。通信 kernel 也可能使 GPU 看起来很忙，而真正拖慢整体的是慢 rank 或同步。我要先对齐各 rank 的时间线，看大家什么时候进入 collective，再看链路吞吐和拓扑。如果通信确实在关键路径上，才进一步优化通信量、消息合并、放置或计算通信重叠。</p></div>
</div>

## 功率、能耗与单位 Token 成本

功率 `P` 的单位是 W，即 J/s；区间能耗 `E = ∫P(t)dt`，单位为 J。完成有效输出 Token 数为 `N`，则能效为 `N/E` tokens/J，反向是 `E/N` J/token。要明确统计的是 GPU、整机还是整个服务，以及是否包括空闲、加载、迁移与重算成本。

高功率可能来自高强度有效计算，也可能是低效工作；低功率可能是空闲、访存型负载、限功耗或供给不足。**单独看功率不能判断效率，应比较相同输出质量和延迟要求下的 tokens/J。** 例：1000 tokens/s、500 W 对应 2 tokens/J；若调整后为 900 tokens/s、400 W，则为 2.25 tokens/J，但还要确认吞吐和延迟目标是否接受这一下降。

单位 Token 的财务成本还包括设备折旧、CPU/网络/存储及运维，不能从 GPU 电耗直接推成完整服务成本。功率字段是瞬时还是平均、采样频率和测量范围应按设备与版本确认。[nvidia-smi Power Readings](https://docs.nvidia.com/deploy/nvidia-smi/index.html)

## 时钟、温度、P-state 与降频原因

SM/显存时钟通常用 MHz，温度用 °C，P-state 是离散性能状态。时钟升高可能提高相应管线或内存能力，但最终收益取决于瓶颈；时钟低也可能只是低需求下的正常节能。

<div class="table-scroll">

| 观测 | 可能影响 | 必须补充的证据 |
|---|---|---|
| 高负载时吞吐下降、SM 时钟下降 | 计算能力可能受频率限制 | 对齐 power/thermal clock event reason、功率上限与时间线 |
| 温度高 | 可能接近设备温控边界 | 查看该型号的阈值和热降频状态，不能设统一温度结论 |
| 功率接近上限 | 可能发生功率管理 | 是否确实出现 power cap 原因，以及频率和吞吐变化 |
| P0 或其他高性能状态 | 设备处于相应工作状态 | 不等于算力满载；反之也不能只凭非 P0 判断异常 |

</div>

用 `nvidia-smi -q -d POWER,CLOCK,TEMPERATURE,PERFORMANCE` 读取状态，再关联同一业务阶段。**观察到低频之后仍需区分“需求变少导致降频”和“降频限制了业务”。** [nvidia-smi Clock Event Reasons](https://docs.nvidia.com/deploy/nvidia-smi/index.html#clocks-event-reasons)

## ECC、Xid 与链路错误

ECC 要分可纠正/不可纠正错误、易失/累计计数以及内存位置。历史累计数高不等于本轮新故障；本轮持续新增错误、不可纠正事件或异常恢复则需要结合时间、设备与驱动日志处理。Xid 是事件类别编号，**数值大不代表严重程度更高**，应查具体代码含义。[NVIDIA Xid Errors](https://docs.nvidia.com/deploy/xid-errors/index.html)

链路 CRC、重传或相关错误计数升高，可能降低有效吞吐或引发超时；先区分累计值和区间增量，并核对计数是否重置。错误为零也不排除软件同步、配置或负载不均问题。影响可靠性的设备应由平台健康策略处理，而不是通过降低 batch 掩盖。

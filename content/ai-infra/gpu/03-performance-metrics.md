## 指标的对象与层次

**资源被分配、显存被占用、GPU 有活动、执行效率高、业务完成得快，是五个不同判断。** 一个模型可以占着大量显存等待请求；一个通信 kernel 可以让 GPU 持续有活动，却没有增加模型的有效计算。

<div class="table-scroll">

| 层次 | 代表指标 | 定义必须说清的对象 | 指标高不自动意味着什么 |
|---|---|---|---|
| 资源分配 | GPU 数、配额、卡时分配率 | 可调度资源、物理卡/分片、统计时段 | 分配多不等于计算多 |
| 状态容量 | FB Used/Free、Allocated/Reserved、KV 池占用 | 设备、进程、框架分配器或缓存池 | 占用多不等于执行快 |
| 执行活动 | GPU Util、SM Active、Tensor/DRAM 活动 | 设备/SM/管线以及采样窗口 | 活动多不等于有效吞吐高 |
| 指令推进 | Occupancy、eligible/issued warp、stall | warp 驻留、发射条件与归一化分母 | 驻留多不等于可发射多 |
| 执行效率 | 实际 FLOP/s、带宽、MFU/HFU、Roofline | 必要工作/实际执行、字节层级、峰值口径 | 局部高效不等于端到端改善 |
| 互联与健康 | PCIe/NVLink、NCCL、功率/温度/错误 | 路径、方向、增量、时间与设备 | 带宽或功率高不等于瓶颈已确定 |
| 业务结果 | step time、TTFT/ITL/TPOT、goodput、JCT | 请求、任务、测量起止点与 SLO | 吞吐高不等于质量和延迟都合格 |

</div>

## 数值可比需要相同口径

- **对象一致**：整卡、MIG 实例、进程、Pod 与请求不能混为一个实体；共享卡附上 Pod 标签，也不自动具有精确进程归属。
- **窗口一致**：设备采样周期、Prometheus 抓取周期和时间聚合窗口分别记录。某个 kernel 的 active-cycle 指标，不能直接与整分钟 elapsed-time 指标比较。
- **单位一致**：比例 0–1 与百分数 0–100；byte 与 bit；GB 与 GiB；FLOPs 与 FLOP/s；W 与 J。先换算，再比较。
- **基线一致**：同一模型、精度、输入输出长度、batch、并行度、缓存冷热和硬件配置。FP16 稠密实际计算不能除以宣传中的稀疏峰值。
- **数据有效**：缺失、过期、不支持和计数器复用不能当作零；累计 counter 与已有速率 gauge 采用不同查询方式。

<div class="card card-s">
<h3>指标之间的关系图</h3>
<p>可以用下面这条链路理解性能指标：模型工作负载先决定计算量和访存量，再被 GPU 的算力、带宽、容量和互联约束，最终表现为吞吐、延迟和成本。</p>
<div class="metric-flow">
<svg viewBox="0 0 1040 360" role="img" aria-label="GPU performance metrics relation">
<defs>
<marker id="metricArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
<path d="M0,0 L0,6 L9,3 z" fill="var(--border, #dbe4f0)"></path>
</marker>
</defs>
<rect x="35" y="95" width="170" height="95" rx="14" class="metric-node workload" fill="var(--card-solid, #ffffff)" stroke="var(--pri, #2563eb)" stroke-opacity=".42" stroke-width="1.5"></rect>
<text x="62" y="132" class="metric-label" fill="var(--txt, #172033)">Workload</text>
<text x="62" y="156" class="metric-desc" fill="var(--muted, #667085)">FLOPs / Bytes</text>
<text x="62" y="176" class="metric-desc" fill="var(--muted, #667085)">batch · seq · shape</text>

<rect x="290" y="45" width="170" height="85" rx="14" class="metric-node compute" fill="var(--card-solid, #ffffff)" stroke="var(--sec, #059669)" stroke-opacity=".42" stroke-width="1.5"></rect>
<text x="318" y="80" class="metric-label" fill="var(--txt, #172033)">Compute Roof</text>
<text x="318" y="104" class="metric-desc" fill="var(--muted, #667085)">TFLOPS / Tensor Core</text>

<rect x="290" y="165" width="170" height="85" rx="14" class="metric-node memory" fill="var(--card-solid, #ffffff)" stroke="var(--warn, #d97706)" stroke-opacity=".42" stroke-width="1.5"></rect>
<text x="318" y="200" class="metric-label" fill="var(--txt, #172033)">Memory Roof</text>
<text x="318" y="224" class="metric-desc" fill="var(--muted, #667085)">HBM bandwidth</text>

<rect x="540" y="95" width="170" height="95" rx="14" class="metric-node interconnect" fill="var(--card-solid, #ffffff)" stroke="var(--acc, #7c3aed)" stroke-opacity=".42" stroke-width="1.5"></rect>
<text x="568" y="132" class="metric-label" fill="var(--txt, #172033)">Communication</text>
<text x="568" y="156" class="metric-desc" fill="var(--muted, #667085)">NVLink / PCIe / IB</text>
<text x="568" y="176" class="metric-desc" fill="var(--muted, #667085)">AllReduce · KV transfer</text>

<rect x="795" y="95" width="190" height="95" rx="14" class="metric-node output" fill="var(--card-solid, #ffffff)" stroke="var(--danger, #dc2626)" stroke-opacity=".42" stroke-width="1.5"></rect>
<text x="823" y="132" class="metric-label" fill="var(--txt, #172033)">Observed Result</text>
<text x="823" y="156" class="metric-desc" fill="var(--muted, #667085)">throughput · latency</text>
<text x="823" y="176" class="metric-desc" fill="var(--muted, #667085)">cost · utilization</text>

<path d="M205 142 C242 142 250 88 290 88" class="metric-arrow" stroke="var(--border, #dbe4f0)" stroke-width="1.8" fill="none" marker-end="url(#metricArrow)"></path>
<path d="M205 142 C242 142 250 208 290 208" class="metric-arrow" stroke="var(--border, #dbe4f0)" stroke-width="1.8" fill="none" marker-end="url(#metricArrow)"></path>
<path d="M460 88 C500 88 505 142 540 142" class="metric-arrow" stroke="var(--border, #dbe4f0)" stroke-width="1.8" fill="none" marker-end="url(#metricArrow)"></path>
<path d="M460 208 C500 208 505 142 540 142" class="metric-arrow" stroke="var(--border, #dbe4f0)" stroke-width="1.8" fill="none" marker-end="url(#metricArrow)"></path>
<path d="M710 142 C750 142 755 142 795 142" class="metric-arrow" stroke="var(--border, #dbe4f0)" stroke-width="1.8" fill="none" marker-end="url(#metricArrow)"></path>
<text x="300" y="314" class="metric-note" fill="var(--muted, #667085)">Roofline 判断：Arithmetic Intensity = FLOPs / Bytes；比较计算与带宽上界；实际瓶颈还需结合时间线和热点计数器。</text>
</svg>
</div>
</div>

## 高低与优化方向

“高”和“低”首先相对于同样任务、阶段与配置的基线。高值可能表示资源被有效使用，也可能表示该资源被低效工作占满；低值可能表示供给不足，也可能是合理的缓存复用或低需求。先建立可检验的解释，再看时间线与最终产出。

<div class="qa open" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 你如何理解 GPU 利用率和性能之间的关系？</div>
<div class="qa-a"><p>我会把“分到了资源、占着显存、有计算活动、执行效率高、业务产出好”分开。GPU Util 看 kernel 活动时间，SM Active 看 SM 在时间上的活动，Occupancy 看驻留 warp，带宽和计算吞吐解释执行限制，最后用任务时间和达标吞吐验证。不能从一个利用率百分比直接推出剩余算力或性能瓶颈。</p></div>
</div>

定义依据：[NVML](https://docs.nvidia.com/deploy/archive/R535/nvml-api/structnvmlUtilization__t.html)、[DCGM Profiling](https://docs.nvidia.com/datacenter/dcgm/latest/learn/modules/profiling.html)、[Nsight Compute](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html)。具体字段名和支持范围以实际设备、采集器与工具版本为准。

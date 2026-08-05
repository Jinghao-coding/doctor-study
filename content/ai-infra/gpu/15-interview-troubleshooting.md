## 一句话结论

GPU 故障排查必须从业务指标开始，再沿主机、容器、CUDA、GPU Kernel、互联逐层缩小范围。`nvidia-smi` 是入口，不是结论；最终修复必须用同一负载复测吞吐、延迟和稳定性。

## 通用诊断路径

```flow
界定现象 | 单卡/单机/多机，持续/偶发，从何时开始
确认业务影响 | Step Time、Token/s、TTFT、TPOT、失败率
检查设备健康 | Xid、ECC、温度、功耗、时钟、掉卡
检查供给链 | CPU、DataLoader、磁盘、网络、H2D
分析 Timeline | 空洞、Memcpy、同步、NCCL、Kernel 碎片
深挖热点 Kernel | SM、Tensor Core、HBM、Occupancy、Warp Stall
修复并复测 | 同一输入、同一并发、同一指标窗口
```

## 典型场景

| 现象 | 优先检查 | 常见根因 |
|---|---|---|
| GPU-Util 长期很低 | CPU、DataLoader、队列、H2D、请求量 | 输入供给不足、Batch 小、同步点多 |
| GPU-Util 高但吞吐低 | SM/Tensor/HBM、Kernel Timeline | Memory-bound、小 Kernel、未使用 Tensor Core |
| 显存占用高但 GPU 空转 | 进程状态、队列、模型阶段 | 权重/KV/缓存常驻，不代表正在计算 |
| CUDA OOM | Active/Reserved、峰值、碎片、Batch | 模型真需求超限或缓存分配器碎片 |
| Pod 申请 GPU 一直 Pending | Node Allocatable、taint、affinity、配额 | Device Plugin 未注册、资源不足、约束冲突 |
| Pod 内 `nvidia-smi` 失败 | Allocate、CDI/runtime、驱动库、device node | Toolkit/CDI 配置或 Driver 注入失败 |
| 多卡训练 Hang | rank 状态、NCCL 日志、网络、拓扑 | 某 Rank 异常、collective 不一致、链路故障 |
| 性能突然下降 | 功耗/时钟/温度、Xid、后台进程 | 降频、ECC、共享干扰、拓扑变化 |

## 常用命令与意义

```bash
nvidia-smi -L
nvidia-smi topo -m
nvidia-smi dmon -s pucvmet
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv
dcgmi diag -r 1
```

- `nvidia-smi -L`：确认设备和 UUID，不说明 CUDA 工作负载正常。
- `topo -m`：检查 GPU-GPU、GPU-NIC、NUMA 路径，不直接等于实测带宽。
- `dmon`：看一段时间内的利用率、功耗、时钟、温度和错误趋势。
- DCGM 诊断：验证健康状态；生产执行更重级别测试前要确认不会影响业务。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 利用率从 90% 掉到 20%，如何排查？</div>
<div class="qa-a"><p>先比较同一业务阶段的 Step Time 或 Token/s，确认不是 Eval、Checkpoint 或流量变化。再判断单卡还是所有 Rank 同时下降：单卡优先查设备健康、进程和局部拓扑；全局下降优先查数据、存储、网络和同步。随后用 Timeline 找空洞或 NCCL/Memcpy 占比，对热点 Kernel 再看 HBM、SM、Tensor Core 与 Warp Stall，最后复现并验证修复。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: `nvidia-smi` 能看到卡，但 Kubernetes Node 没有 `nvidia.com/gpu`，问题在哪？</div>
<div class="qa-a"><p>Host Driver 已经基本正常，但 Kubernetes 资源注册链未打通。检查 Device Plugin DaemonSet 是否落到该节点、是否能访问设备、是否在 <code>/var/lib/kubelet/device-plugins/</code> 注册、ListAndWatch 是否上报健康设备，以及 kubelet 是否完成 Node Status 更新。此时 Container Toolkit 仍可能有问题，但它主要影响容器注入，不是 Node 资源完全缺失的第一嫌疑。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何区分显存容量瓶颈和显存带宽瓶颈？</div>
<div class="qa-a"><p>容量瓶颈表现为 OOM、可容纳 Batch/KV Cache 受限，核心单位是 GB；带宽瓶颈表现为 Kernel 持续搬数据、算力管线吃不满，核心单位是 GB/s。前者看 Active/Reserved/Peak Memory，后者看 HBM Throughput、算术强度和 Warp Stall。</p></div>
</div>

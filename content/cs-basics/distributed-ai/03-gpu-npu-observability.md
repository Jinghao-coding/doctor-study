## 一句话结论

GPU-Util 只说明采样窗口内 GPU「有没有在忙」，不等于算力用满、更不等于吞吐高。真正判断 GPU 是否高效，要同时看显存、SM Active、Tensor Core 利用率、HBM 带宽、NCCL 通信占比和端到端吞吐——只盯 GPU-Util 是最常见的误判。
<div class="card card-m"><h3>GPU 观测不要只看 GPU-Util</h3><p>GPU-Util 表示采样窗口内 GPU 是否忙，不等于 Tensor Core 用满，也不等于模型吞吐高。排查要同时看显存、拓扑、SM Active、HBM、NCCL、数据加载和端到端吞吐。</p></div>
<table><tr><th>目标</th><th>看什么</th><th>工具</th></tr><tr><td>设备可见性</td><td>GPU 数量、型号、UUID</td><td><code>nvidia-smi -L</code></td></tr><tr><td>显存</td><td>used/free、进程占用</td><td><code>nvidia-smi</code>、框架 summary</td></tr><tr><td>拓扑</td><td>GPU-GPU、GPU-NIC</td><td><code>nvidia-smi topo -m</code></td></tr><tr><td>计算效率</td><td>SM Active、Tensor Core、MFU</td><td>DCGM、Nsight、Profiler</td></tr></table>
<div class="qa" onclick="this.classList.toggle('open')"><div class="qa-q">Q: GPU-Util 100% 但训练很慢，可能是什么原因？</div><div class="qa-a"><p>可能是小 kernel 连续运行但算力利用低，或通信 kernel 占比高，或 HBM/PCIe/NVLink 瓶颈，或数据加载间歇造成 pipeline 不稳。应看 timeline、SM Active、Tensor Core 利用率、NCCL 时间和端到端吞吐。</p></div></div>

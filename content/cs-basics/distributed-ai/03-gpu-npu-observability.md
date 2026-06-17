## 一句话结论

GPU-Util 只说明采样窗口内 GPU「有没有在忙」，不等于算力用满、更不等于吞吐高。真正判断 GPU 是否高效，要同时看显存、SM Active、Tensor Core 利用率、HBM 带宽、NCCL 通信占比和端到端吞吐——只盯 GPU-Util 是最常见的误判。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 分布式 AI 基础 |
| 章节类型 | 排障诊断类 |
| 解决问题 | 围绕 role/replica/rank、通信存储、GPU/NPU 可观测性建立分布式训练和推理基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>GPU 观测不要只看 GPU-Util</h3><p>GPU-Util 表示采样窗口内 GPU 是否忙，不等于 Tensor Core 用满，也不等于模型吞吐高。排查要同时看显存、拓扑、SM Active、HBM、NCCL、数据加载和端到端吞吐。</p></div>
<table><tr><th>目标</th><th>看什么</th><th>工具</th></tr><tr><td>设备可见性</td><td>GPU 数量、型号、UUID</td><td><code>nvidia-smi -L</code></td></tr><tr><td>显存</td><td>used/free、进程占用</td><td><code>nvidia-smi</code>、框架 summary</td></tr><tr><td>拓扑</td><td>GPU-GPU、GPU-NIC</td><td><code>nvidia-smi topo -m</code></td></tr><tr><td>计算效率</td><td>SM Active、Tensor Core、MFU</td><td>DCGM、Nsight、Profiler</td></tr></table>
<div class="qa" onclick="this.classList.toggle('open')"><div class="qa-q">Q: GPU-Util 100% 但训练很慢，可能是什么原因？</div><div class="qa-a"><p>可能是小 kernel 连续运行但算力利用低，或通信 kernel 占比高，或 HBM/PCIe/NVLink 瓶颈，或数据加载间歇造成 pipeline 不稳。应看 timeline、SM Active、Tensor Core 利用率、NCCL 时间和端到端吞吐。</p></div></div>

## 面试回答

**30 秒版：**

GPU-Util 高只代表 GPU 在忙，可能是小 kernel 连续跑、通信 kernel 占比高，或被 HBM/PCIe/NVLink 卡住。我会按层次看：设备可见性用 nvidia-smi -L，显存和拓扑用 nvidia-smi 和 topo -m，计算效率用 DCGM/Nsight 看 SM Active 和 Tensor Core，最后落到端到端吞吐和 MFU。

**2 分钟版：**

我会先纠正一个常见误区：GPU-Util 100% 不代表训练快。它只是采样窗口里有 kernel 在执行，可能是大量小 kernel、可能是 NCCL 通信 kernel，真正的算力利用要看 SM Active 和 Tensor Core 利用率，整体效率看 MFU。然后讲分层观测：第一层设备可见性，确认卡数、型号、UUID；第二层显存和拓扑，看占用和 GPU-GPU/GPU-NIC 连接方式；第三层计算效率，用 DCGM、Nsight、Profiler 看 SM、Tensor Core、HBM 带宽。接着讲典型场景：GPU-Util 高但训练慢，通常是数据加载间歇导致 pipeline 不稳、通信占比过高、或 HBM 带宽打满——这时要看 timeline 把计算、通信、等待分开。最后收束：观测的目的是定位瓶颈在算力、访存、通信还是数据，所以单一指标不够，要组合 timeline 和端到端吞吐一起判断。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

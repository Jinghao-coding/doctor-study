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

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

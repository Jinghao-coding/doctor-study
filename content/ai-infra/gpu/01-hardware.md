## 一句话结论

GPU 硬件要从三类资源理解：SM/Tensor Core 决定计算吞吐，HBM 决定显存容量和带宽，NVLink/NVSwitch/PCIe 决定数据在 GPU、CPU 和网卡之间怎么流动。面试里不要只背型号参数，要能把“算力、显存、互联”对应到训练和推理瓶颈。

## 核心概念

| 概念 | 作用 | 面试抓手 |
|---|---|---|
| SM（Streaming Multiprocessor） | GPU 的主要计算组织单元，内部包含 warp scheduler、CUDA Core、Tensor Core、寄存器和 shared memory | 看 kernel 能不能把 SM 铺满 |
| CUDA Core | 常规数值执行单元，处理 FP32/INT 等标量或向量指令 | 不要直接类比 CPU core |
| Tensor Core | 矩阵乘加专用硬件，支持 FP16/BF16/TF32/FP8/INT8 等不同精度 | 深度学习 GEMM、卷积、Attention 的核心加速点 |
| HBM | 高带宽显存，存放模型权重、激活、梯度、KV cache | Decode、embedding、elementwise 常受 HBM 带宽限制 |
| L2 Cache | 多个 SM 共享的缓存层 | 缓解重复访问，影响访存效率 |
| NVLink / NVSwitch | GPU-GPU 高速互联和单机多卡交换 | 影响 tensor parallel、pipeline parallel、all-reduce |
| PCIe | CPU-GPU、GPU-NIC、部分 GPU-GPU 数据路径 | H2D/D2H、GPUDirect RDMA、NUMA 亲和都和它相关 |

## 主流 GPU 对比

| 指标 | A100 80GB | H100 80GB | H200 141GB |
|---|---:|---:|---:|
| 架构 | Ampere | Hopper | Hopper |
| SM 数 | 108 | 132 | 132 |
| FP16/BF16 Tensor Core 峰值 | 312 TFLOPS | 989 TFLOPS | 989 TFLOPS |
| 显存 | 80GB HBM2e | 80GB HBM3 | 141GB HBM3e |
| 显存带宽 | 2.0 TB/s | 3.35 TB/s | 4.8 TB/s |
| NVLink 单向带宽 | 300 GB/s | 450 GB/s | 450 GB/s |
| TDP | 400W | 700W | 700W |

## 关键机制

GPU 性能通常由下面几类资源共同决定：

1. 计算资源：SM 数量、Tensor Core 能力、时钟频率、支持的数据类型。
2. 片上资源：寄存器、shared memory、L1/L2 cache，决定 occupancy 和数据复用能力。
3. 显存资源：HBM 容量决定能放下多大模型和 batch，HBM 带宽决定 memory-bound 算子的上限。
4. 互联资源：PCIe/NVLink/NVSwitch/RDMA 决定多卡和跨机通信效率。
5. 功耗散热：训练集群里功耗墙、降频和散热也会影响实际吞吐。

## 常见误区

| 误区 | 正确理解 |
|---|---|
| TFLOPS 越高训练一定越快 | 只有算子能用上 Tensor Core 且数据供给跟得上，峰值算力才有意义。 |
| 显存越大就是性能越强 | 容量解决“放不放得下”，带宽和算子效率决定“跑得快不快”。 |
| CUDA Core 数量可以直接比较 GPU 性能 | 深度学习更要看 SM、Tensor Core、HBM、互联和实际 kernel 效率。 |
| 单卡强就代表多卡也强 | 多卡性能还受 NVLink/NVSwitch、PCIe、RDMA、NCCL 拓扑影响。 |

## 面试回答

**30 秒版：**

GPU 硬件可以按计算、显存和互联三层讲。计算层看 SM、CUDA Core、Tensor Core，决定矩阵乘和一般 kernel 的吞吐；显存层看 HBM 容量和带宽，决定模型、激活、KV cache 能不能放下以及 decode 这类 memory-bound 阶段的上限；互联层看 PCIe、NVLink、NVSwitch 和 RDMA，决定 CPU-GPU 拷贝、多卡训练和跨机通信效率。

**追问口径：**

如果面试官问 A100/H100/H200 的区别，可以回答：H100 相比 A100 主要提升 Hopper 架构、Tensor Core 能力、FP8 支持、显存带宽和 NVLink 带宽；H200 进一步把显存容量和 HBM3e 带宽拉高，更适合大模型推理中 KV cache 压力大的场景。

## 关联模块

- `CPU vs GPU`：先理解 GPU 为什么为吞吐而设计。
- `CUDA 执行模型`：把 SM、warp、block 和 kernel 执行关系串起来。
- `性能指标`：用 TFLOPS、HBM 带宽、Roofline 判断硬件上限。
- `GPU 互联与数据路径`：继续看 PCIe、NVLink、NVSwitch、RDMA 的真实数据流。

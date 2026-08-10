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

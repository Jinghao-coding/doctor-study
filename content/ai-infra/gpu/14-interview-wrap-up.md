## 一句话结论

GPU 面试回答要围绕四条链路：硬件如何提供并行吞吐、CUDA 如何组织执行、数据如何在内存与互联之间流动、资源如何共享并被诊断。只背显卡参数和 `nvidia-smi` 不足以说明系统能力。

## 高频追问压缩表

| 问题 | 回答主线 | 易错点 |
|---|---|---|
| CPU 和 GPU 为什么设计不同？ | CPU 优化低延迟控制流和大缓存；GPU 用大量执行单元与高带宽追求吞吐 | 不要只说“GPU 核多” |
| SM、Block、Warp、Thread 什么关系？ | Grid 包含 Block；Block 被分配到 SM；Thread 按 Warp 执行 | Block 不能跨 SM 同时执行 |
| Warp Divergence 为什么慢？ | 同一 Warp 的分支路径需要分别执行，有效并行度下降 | 不等于所有分支都会串行 |
| Shared Memory 有什么用？ | Block 内可编程片上缓存，用于复用和线程协作 | 它容量有限，过多会压低 Occupancy |
| Pinned Memory 为什么更快？ | 页被锁定，DMA 可稳定访问，也能支持异步拷贝 | 不是越多越好，会减少 OS 可分页内存 |
| Stream 和 Event 的区别？ | Stream 是有序任务队列；Event 用于依赖和计时 | 多 Stream 不保证自动并行 |
| Occupancy 越高越好吗？ | 它帮助隐藏延迟，但寄存器/Shared Memory/指令效率同样重要 | 100% 不是最终目标 |
| GPU-Util 100% 为什么还慢？ | 继续看 SM、Tensor Core、HBM、Warp Stall 和业务吞吐 | GPU-Util 不等于峰值算力利用率 |
| MIG、MPS、Time-Slicing 怎么选？ | MIG 强隔离；MPS 提升进程并发；Time-Slicing 低成本复用 | Time-Slicing 不保证固定性能份额 |
| NVLink、PCIe、RDMA 分别在哪？ | GPU-GPU、Host/设备路径、跨机网络数据面 | 不要把 NVLink 当跨机网络 |

## 关键机制串联

```flow
CPU 提交 Kernel | CUDA Runtime/Driver 准备 launch 与参数
Grid/Block 映射 SM | 受寄存器、Shared Memory 和 Block 数限制
Warp 发射指令 | 分支、依赖、访存导致 Stall
数据经过内存层次 | Register/Shared/L2/HBM
多设备互联 | PCIe/NVLink/NVSwitch/RDMA
业务指标验收 | Step Time、Token/s、TTFT、TPOT、成本
```

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 GPU 适合深度学习？</div>
<div class="qa-a"><p>深度学习的主要计算是规则的大规模矩阵乘和向量操作，具有高数据并行度。GPU 用大量 SM、Warp 和 Tensor Core 提供吞吐，并用 HBM 提供高带宽；代价是复杂控制流和强串行任务不占优势。工程上还必须通过批处理、合适的矩阵形状和内存复用才能真正利用这些硬件。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CUDA Kernel 从 CPU 到 GPU 是怎么执行的？</div>
<div class="qa-a"><p>Host 代码通过 CUDA Runtime/Driver 发起异步 Kernel Launch，指定 Grid 和 Block。GPU 将 Block 分配到满足资源约束的 SM，SM 再以 Warp 为单位选择就绪指令执行。Kernel 完成不代表 Host 已同步，只有遇到显式同步、相关数据依赖或阻塞 API 时 CPU 才需要等待。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MIG、MPS、Time-Slicing 和 HAMi 的本质区别？</div>
<div class="qa-a"><p>MIG 在支持的 GPU 上做硬件级实例切分，隔离最强但形状固定、重配有成本；MPS 让多个 CUDA 进程共享执行上下文并并发提交，利用率高但故障和性能隔离弱；Time-Slicing 主要轮转上下文并扩大 Kubernetes 可调度份额，不提供显存或固定算力隔离；HAMi 在 Kubernetes 层增加显存/算力感知的调度与容器侧限制，工程灵活但需要额外组件和验证。</p></div>
</div>

## 跨模块关联

- LLM 推理：HBM、KV Cache、Prefill/Decode 与 Continuous Batching。
- 分布式训练：NCCL、拓扑、通信计算重叠和 MFU。
- Kubernetes：Device Plugin、Extended Resource、DRA 与节点接入。
- 调度与集群：共享、干扰、碎片、拓扑和多租户治理。

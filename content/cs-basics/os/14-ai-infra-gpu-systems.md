## AI Infra 面试模块：GPU 训练/推理相关系统层知识

这部分是区分普通后端候选人和 AI Infra 候选人的关键。面试官通常关心你是否理解 CPU、内存、PCIe、GPU、驱动和 CUDA runtime 之间的数据路径，以及系统瓶颈如何影响 GPU 利用率。

### 需要掌握

- CPU、内存、PCIe、GPU 之间的数据路径：数据通常从磁盘/网络进入 CPU 内存，再通过 PCIe/NVLink 进入 GPU HBM。
- DMA：设备绕过 CPU 指令拷贝，直接在设备和内存之间传输数据。
- pinned memory/page-locked memory：锁定物理页，避免换页，使 DMA 可以稳定访问。
- CPU 到 GPU 数据拷贝瓶颈：可能来自 CPU 解码、内存带宽、PCIe 带宽、pageable memory staging、NUMA 跨 socket。
- NUMA、PCIe topology、GPU affinity：GPU 挂在哪个 CPU socket/PCIe switch 下会影响数据路径。
- GPU 进程、驱动、CUDA runtime：应用通过 CUDA runtime/driver 提交 kernel、内存分配和拷贝。
- 多进程使用 GPU 的资源竞争：显存、SM、显存带宽、copy engine、上下文和 MPS/MIG 隔离。

### AI Infra 相关关注点

- DataLoader 中 `pin_memory=True` 可以把 batch 放入 pinned memory，使 H2D 拷贝更高效，尤其配合 non_blocking copy 和 CUDA stream。
- GPU 利用率低要判断是计算、通信、I/O、CPU 预处理、H2D 拷贝还是调度排队瓶颈。
- 多卡训练中 PCIe/NVLink 拓扑决定 GPU 间通信路径，跨 NUMA 或跨 PCIe switch 可能降低 all-reduce 性能。
- 推理服务中 batch、队列、CPU 前处理、GPU 执行、后处理、网络写回需要流水线化。

<div class="card card-d">
<h3>GPU 利用率低的分层判断</h3>
<ol>
<li>看 SM utilization / GPU-Util：低说明计算单元没持续工作。</li>
<li>看显存占用：高只代表资源被占，不代表计算忙。</li>
<li>看 PCIe/NVLink 吞吐：高可能是 H2D/D2H 或通信瓶颈。</li>
<li>看 CPU worker 和 DataLoader queue：CPU 供给不足会导致 GPU 等 batch。</li>
<li>看 NCCL 日志和网络指标：分布式训练可能卡在通信。</li>
</ol>
</div>

### 高频问题

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: pinned memory 为什么能提升 H2D 拷贝性能？</div>
<div class="qa-a"><p>普通 pageable memory 可能被 OS 换页，GPU DMA 不能直接安全访问，驱动通常需要先拷到 pinned staging buffer 再 DMA 到 GPU。pinned memory 锁定物理页，避免换页，使 DMA 可以直接传输，减少额外拷贝并支持异步 H2D。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 利用率低但显存占用高，可能是什么原因？</div>
<div class="qa-a"><p>显存高可能只是模型权重、optimizer state、KV cache 或缓存 allocator 常驻，并不代表 GPU 正在计算。利用率低可能是 DataLoader 慢、CPU 前处理慢、H2D 拷贝没重叠、网络通信等待、batch 太小、请求不足或 kernel launch 间隙大。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 多卡训练通信慢，可能和拓扑有什么关系？</div>
<div class="qa-a"><p>GPU 之间可能通过 NVLink、NVSwitch、同一 PCIe switch、跨 PCIe root complex 或跨 NUMA socket 通信，路径不同带宽和延迟差异很大。rank 放置不匹配拓扑时，all-reduce 可能跨慢链路；NIC 和 GPU 不在同一 locality 时，RDMA/GPUDirect 效果也会变差。</p></div>
</div>

## 一句话结论

GPU 利用率低的分层判断 是 操作系统基础 的核心知识点，面试回答要先给结论，再说明机制边界、工程场景和常见误区。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 操作系统基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕进程线程、调度、虚拟内存、IO、多路复用、死锁、观测和 AI Infra OS 问题建立系统基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心概念、系统链路或关键机制，把知识点映射到工程场景。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

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

## 面试回答

**30 秒版：**

14 ai infra gpu systems 是 操作系统基础 中的一个基础知识点，面试回答要先给结论，再说明机制、边界和工程场景。 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。

**2 分钟版：**

我会先说明这个知识点在 操作系统基础 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

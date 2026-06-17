## 一句话结论

NUMA 是多 Socket 服务器的非统一内存访问架构，每个 Socket 有自己直连的本地内存，访问本地内存延迟低带宽高，跨 Socket 访问要走 UPI/QPI/Infinity Fabric，延迟升高、带宽下降还会抢占互联链路。大模型训练不是 GPU 自己算，而是 CPU、内存、GPU、PCIe/NVLink、NIC 的协同，所以 NUMA 绑定的核心原则就是让一个 rank 的 CPU 线程、内存页、GPU 和 NIC 尽量落在同一个 NUMA domain，否则 DataLoader、H2D 拷贝和 RDMA 都可能跨 Socket 导致 GPU 等数据。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Linux Kernel for AI Infra |
| 章节类型 | 机制类 |
| 解决问题 | 围绕 NUMA、cgroup、hugepage、THP、IO、zero-copy 等内核机制建立 AI Infra 系统答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 为什么大模型系统要关心 NUMA？

大模型训练和推理不是“GPU 自己算”这么简单，而是 **CPU、内存、GPU、PCIe/NVLink、网卡、磁盘 I/O** 的协同调度问题。GPU 算力很强，但如果 Linux 内核侧的 NUMA、CPU 绑核、内存分配和设备亲和性不合理，就会出现 GPU 等数据、CPU 争抢、远端内存访问、H2D 拷贝变慢、RDMA 抖动等问题。

**NUMA** 是 **Non-Uniform Memory Access，非统一内存访问架构**。在多 Socket 服务器中，每个 CPU Socket 通常有自己直连的内存控制器和本地内存。

```text
Socket 0 ── 本地内存 0
Socket 1 ── 本地内存 1
```

CPU 访问自己 Socket 直连的内存，叫 **local memory access**；访问另一个 Socket 连接的内存，叫 **remote memory access**。

| 访问类型 | 延迟 | 带宽 | 额外影响 |
|---|---|---|---|
| 本地内存访问 | 低 | 高 | 不占用 Socket 间互联 |
| 远端内存访问 | 高 | 低 | 占用 UPI/QPI/Infinity Fabric 等 Socket 间链路 |

Socket 间通常通过 UPI、QPI、Infinity Fabric 等互联链路通信。这个链路的带宽和延迟通常弱于本地内存控制器，因此远端访问会带来明显性能损耗。

## 跨 Socket 访问会怎样？

假设一个训练进程的 CPU 线程绑定在 Socket 0：

```text
CPU Thread → Socket 0
```

但它的大量内存页实际分配在 Socket 1：

```text
Memory Pages → Socket 1
```

访问路径会变成：

```flow
Socket 0 CPU Core | 训练线程或 DataLoader worker
Socket 间互联 | UPI / QPI / Infinity Fabric
Socket 1 Memory Controller | 远端内存控制器
Socket 1 DRAM | 实际数据所在内存
```

后果包括：

1. **内存访问延迟升高**：CPU 每次访问远端内存都要跨 Socket。
2. **有效内存带宽下降**：本地 DRAM 带宽不能充分利用，访问受限于 Socket 间互联。
3. **Socket 间链路拥塞**：多个进程跨 Socket 访问会挤占 UPI/QPI/IF。
4. **DataLoader 性能下降**：解码、预处理、batch 拼接依赖 CPU 和内存带宽，远端访问会导致 GPU 等数据。
5. **GPU-NIC 通信路径变差**：GPU 或 NIC 挂在 Socket 0，但 buffer 在 Socket 1，会让 H2D、RDMA 或 staging 路径跨 Socket。

典型糟糕路径：

```flow
Socket 1 Memory | 数据缓冲区实际在远端 NUMA node
Socket 间互联 | 跨 Socket 搬运
Socket 0 PCIe Root Complex | GPU / NIC 所在侧
GPU / NIC | H2D 拷贝或 RDMA 收发
```

这会影响 CPU 到 GPU 的 H2D 拷贝、GPU 到 CPU pinned memory 的 staging、RDMA 网卡收发、数据加载吞吐和多卡训练通信稳定性。

## 多卡机器上的 NUMA 绑定原则

核心原则是：

> **让 CPU 线程、内存、GPU、NIC 尽量落在同一个 NUMA domain / Socket 附近。**

一台 8 卡服务器的拓扑可能类似：

```text
Socket 0
  ├── CPU cores 0-63
  ├── Memory node 0
  ├── GPU 0, GPU 1, GPU 2, GPU 3
  └── NIC 0

Socket 1
  ├── CPU cores 64-127
  ├── Memory node 1
  ├── GPU 4, GPU 5, GPU 6, GPU 7
  └── NIC 1
```

比较好的绑定方式是：

```text
rank 0 → GPU 0 → Socket 0 CPU cores → NUMA node 0 memory
rank 1 → GPU 1 → Socket 0 CPU cores → NUMA node 0 memory
rank 4 → GPU 4 → Socket 1 CPU cores → NUMA node 1 memory
rank 5 → GPU 5 → Socket 1 CPU cores → NUMA node 1 memory
```

要避免：

```text
rank 0 → GPU 0 挂 Socket 0
CPU 线程 → Socket 1
内存页 → NUMA node 1
```

这种绑定会导致 CPU 数据处理、H2D 拷贝、GPU-NIC 通信都可能跨 Socket。

## 常用 NUMA 绑定方法

### 使用 numactl

将进程绑定到 NUMA node 0：

```bash
numactl --cpunodebind=0 --membind=0 python train.py
```

含义是：

```text
CPU 尽量使用 node 0
内存也从 node 0 分配
```

如果是 8 卡机器，可以按 rank 或 GPU 分组：

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 numactl --cpunodebind=0 --membind=0 python train.py
CUDA_VISIBLE_DEVICES=4,5,6,7 numactl --cpunodebind=1 --membind=1 python train.py
```

### 结合 taskset

`taskset` 可以绑定 CPU core：

```bash
taskset -c 0-31 python train.py
```

但它只管 CPU affinity，不直接管内存分配。实际生产中常常组合使用：

```bash
numactl --membind=0 taskset -c 0-31 python train.py
```

### 容器中通过 cpuset + device 分配

在 Kubernetes 或容器环境中，通常通过这些能力保证拓扑接近：

- CPU cpuset
- memory NUMA policy
- GPU device assignment
- `NVIDIA_VISIBLE_DEVICES`
- Topology Manager
- Device Plugin

目标是让容器的 CPU cores、内存、GPU、NIC 在拓扑上接近。

## 排查和观测

| 目标 | 命令 | 看什么 |
|---|---|---|
| 查看 NUMA node | `numactl --hardware` | CPU core、内存 node 分布 |
| 查看 GPU/NIC 拓扑 | `nvidia-smi topo -m` | GPU-GPU、GPU-NIC、GPU-CPU 亲和性 |
| 查看进程 NUMA 分布 | `numastat -p <pid>` | 进程内存页落在哪些 node |
| 查看 CPU 亲和 | `taskset -pc <pid>` | 进程允许在哪些 CPU core 运行 |
| 查看系统拓扑 | `lstopo` | CPU、PCIe、GPU、NIC 的完整层级 |

排查训练慢时，如果 GPU Util 周期性掉低，要同时看 CPU worker 是否跨 NUMA、page cache 是否抖动、H2D 是否跨 Socket、NIC 是否和 GPU 不亲和。

## 面试回答模板

NUMA 是多 Socket 服务器中的非统一内存访问架构，每个 Socket 有自己的本地内存。CPU 访问本地内存延迟低、带宽高，访问远端 Socket 的内存需要经过 Socket 间互联，会增加延迟、降低带宽，并造成链路拥塞。在多卡训练服务器中，NUMA 绑定的目标是让进程的 CPU 线程、内存、GPU 和 NIC 尽量位于同一个 NUMA domain。常见做法是根据 `nvidia-smi topo -m`、`numactl --hardware` 等拓扑信息，把每个 rank 绑定到离目标 GPU 最近的 CPU core 和内存节点，避免 GPU 挂在 Socket 0，但 CPU 和内存却落在 Socket 1。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 GPU 训练中 NUMA 绑定会影响吞吐？</div>
<div class="qa-a"><p>因为训练不是只有 GPU 计算，还包括 CPU DataLoader、数据解码、batch 拼接、H2D 拷贝和 RDMA 通信。如果 CPU 线程、内存页、GPU、NIC 分布在不同 Socket，数据路径会跨 Socket，延迟升高、带宽下降，还会占用 Socket 间互联。结果就是 GPU 可能周期性等数据，NCCL 或 H2D 也可能抖动。</p><div class="qa-summary">面试口径：NUMA 绑定优化的是 CPU、内存、GPU、NIC 的端到端数据路径。</div></div>
</div>

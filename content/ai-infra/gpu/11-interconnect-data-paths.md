## 一句话结论

在 8 卡 H100/A100 训练服务器里，**单机内 GPU-GPU 通信优先走 NVLink/NVSwitch，跨机优先走 GPUDirect RDMA，PCIe 则承担 CPU、GPU、NIC、NVMe 之间的通用 I/O**。理解这三者不是为了背硬件名词，而是为了回答一个 AI Infra 的核心问题：同样是「8 张 GPU」，为什么放置位置不同，训练吞吐和延迟会差很多？

## 系统链路

```flow
单机内 GPU-GPU | 优先走 NVLink / NVSwitch，高带宽、低延迟
CPU / GPU / NIC / SSD | 通过 PCIe 连接，负责通用 I/O 和设备互联
跨服务器 GPU-GPU | 通过 NIC + InfiniBand/RoCE RDMA 网络传输
调度器决策 | 把通信频繁的 rank 放到更近、更宽、更低延迟的路径上
```

## 三者定位

| 技术 | 主要用途 | 典型通信范围 | 特点 | 训练中的角色 |
|---|---|---|---|---|
| **NVLink / NVSwitch** | GPU-GPU 高速互联 | 单机内，或 NVLink Switch 扩展域 | 高带宽、低延迟、面向 GPU 内存访问 | 单机内 AllReduce、张量并行、Pipeline stage 间通信 |
| **PCIe** | 通用 I/O 总线 | CPU-GPU、GPU-NIC、GPU-SSD、部分 GPU-GPU P2P | 通用性强，但带宽和延迟弱于 NVLink | Host 到 GPU 拷贝、GPU 到 NIC、无 NVLink 时的 GPU-GPU fallback |
| **RDMA / InfiniBand / RoCE** | 跨服务器远程直接内存访问 | 服务器之间 | 绕过远端 CPU、低 CPU 开销、适合大规模集群 | 跨节点梯度同步、参数交换、分布式训练通信 |

简单类比：

- **NVLink**：GPU 之间的“高速内环路”。
- **PCIe**：服务器内部设备之间的“通用高速公路”。
- **RDMA**：服务器之间的“跨城专线”。

## 带宽差异

### NVLink：单机 GPU-GPU 通信的最高优先级

对 H100 来说，NVIDIA 给出的 H100 SXM 互联规格是 **NVLink 900 GB/s**，H100 NVL 的 PCIe 形态则列出 **NVLink 600 GB/s** 和 **PCIe Gen5 128 GB/s**。

对 A100 来说，NVIDIA 给出的 A100 80GB SXM 互联规格是 **NVLink 600 GB/s**，PCIe Gen4 为 **64 GB/s**，并且 A100 PCIe 版本通过 NVLink Bridge 主要支持最多两张 GPU 的桥接。

这里要注意：

- NVIDIA 规格表里的 **600 GB/s、900 GB/s** 通常是 GPU 级别的 NVLink 聚合带宽。
- 这是面向 **GPU-GPU** 的专用互联，不是 CPU-GPU 通用总线。
- 在 8 卡 SXM 服务器里，NVLink 往往不是简单点对点线缆，而是通过 **NVSwitch** 形成交换网络，让多张 GPU 之间可以高带宽互联。

### PCIe：通用但相对慢

PCIe 的带宽按 **代际 × lane 数**计算。PCI-SIG 说明 PCIe 4.0 每 lane 每方向支持 16.0 GT/s，PCIe 5.0 每 lane 每方向支持 32.0 GT/s。

常见 GPU 是 x16 链路，可以近似理解为：

| PCIe 版本 | 常见 x16 单向有效量级 | 双向合计量级 | 常见对应 GPU |
|---|---:|---:|---|
| **PCIe Gen4 x16** | 约 32 GB/s | 约 64 GB/s | A100 PCIe |
| **PCIe Gen5 x16** | 约 64 GB/s | 约 128 GB/s | H100 PCIe |

所以 PCIe 和 NVLink 的差距很明显：

| 对比项 | 典型带宽量级 |
|---|---:|
| A100 SXM NVLink | 约 600 GB/s |
| A100 PCIe Gen4 | 约 64 GB/s 双向合计 |
| H100 SXM NVLink | 约 900 GB/s |
| H100 PCIe Gen5 | 约 128 GB/s 双向合计 |

也就是说，**NVLink 的 GPU-GPU 带宽通常是 PCIe 的数倍到十几倍**。这也是为什么张量并行、MoE All-to-All、频繁 collective 更偏好单机 NVLink/NVSwitch。

### RDMA / InfiniBand：跨机通信的主力

跨服务器时，数据不能直接走 NVLink，通常走 **InfiniBand 或 RoCE RDMA**。NVIDIA Quantum-2 InfiniBand 平台支持最高 **400 Gb/s**，ConnectX-7 InfiniBand 适配器也支持单端口或双端口 **400 Gb/s**。

换算一下：

```text
400 Gb/s ÷ 8 ≈ 50 GB/s
```

所以一张 400G 网卡的理论线速大约是 **50 GB/s**。如果一台服务器有多张 400G NIC，例如 8 张 GPU 搭配 4 到 8 张 NIC，就可以通过 multi-rail 并行提升跨机总带宽。

但即便如此，跨机 RDMA 的单链路带宽通常仍低于单机内 NVLink/NVSwitch：

- 单 GPU NVLink 聚合：数百 GB/s 级别。
- 单 400G RDMA NIC：约 50 GB/s 线速级别。
- 多 NIC 可以并行，但会受 PCIe、NUMA、交换机、拥塞控制、通信库调度影响。

## 延迟差异

延迟比带宽更依赖平台、拓扑、驱动、通信库和消息大小，所以很难给一个绝对固定值。工程上可以按这个顺序理解：

```text
NVLink/NVSwitch 延迟最低
  < PCIe P2P
  < 跨 Socket PCIe / Host staging
  < RDMA 跨机
```

### NVLink / NVSwitch 延迟

NVLink 面向 GPU-GPU 通信，路径短、协议栈轻、带宽高。单机内 GPU 之间做 AllReduce、AllGather、ReduceScatter 时，如果能走 NVLink/NVSwitch，通常是最优路径。

在 8 卡 SXM 服务器里，GPU 间通信通常是：

```flow
GPU HBM | 源 GPU 的参数、梯度、激活值或 KV Cache
GPU NVLink interface | 从 GPU 内存侧进入 NVLink 通道
NVSwitch | 在单机内部做 GPU-GPU 交换
目标 GPU NVLink interface | 目标 GPU 接收数据
目标 GPU HBM | 数据写入目标 GPU 显存
```

CPU 不负责搬运这段数据，只负责启动 kernel、提交通信操作、管理进程和页表等控制逻辑。

### PCIe 延迟

PCIe 是通用 I/O 协议，层次更多，路径可能经过：

```flow
GPU | 源设备
PCIe switch / root complex | 进入 PCIe 拓扑
CPU socket | 可能经过本地 CPU root
另一个 PCIe root / switch | 跨 root 或跨 Socket 时路径变长
目标 GPU 或 NIC | 目标设备接收数据
```

如果两张 GPU 在同一个 PCIe switch 下，PCIe P2P 还算可接受；如果跨 Socket，则可能经过 CPU 间互联，例如 UPI、Infinity Fabric 等，延迟和抖动都会上升。

更糟糕的情况是不能直接 P2P，需要走 host staging：

```flow
GPU0 HBM | 源 GPU 显存
CPU pinned memory | 先落到主机页锁定内存
GPU1 HBM | 再从主机内存拷贝到目标 GPU
```

这会额外消耗 CPU 内存带宽，并增加一次或多次拷贝。

### RDMA 延迟

RDMA 的优势是跨机时避免远端 CPU 参与数据搬运。NVIDIA 对 GPUDirect 的描述是，网络适配器和存储设备可以直接读写 GPU memory，从而消除不必要的内存拷贝、降低 CPU 开销和延迟。

但跨机 RDMA 仍然要经过：

```flow
本机 GPU | 源 GPU HBM
本机 PCIe / PCIe switch / root complex | GPU 到 NIC 的本机路径
本机 NIC | RDMA 网卡发起网络传输
网络交换机 | InfiniBand / RoCE fabric
远端 NIC | 远端服务器接收
远端 PCIe | NIC 到远端 GPU 的本机路径
远端 GPU | 数据写入远端 GPU HBM
```

所以它通常比单机 NVLink/NVSwitch 延迟更高，并且容易受网络拥塞、交换机层级、路由、ECN/PFC、RoCE/IB 配置影响。

## 一台 8 卡 H100/A100 服务器内部，数据如何流转？

这里分两种常见形态：**SXM/HGX 8 卡服务器**和**PCIe 8 卡服务器**。

### 8 卡 H100/A100 SXM/HGX：主路径是 NVLink + NVSwitch

高端 8 卡 A100/H100 训练服务器通常使用 SXM 模组和 HGX/DGX 形态。以这种形态为例，单机内 GPU-GPU 通信一般不走 PCIe，而是走：

```flow
GPU0 HBM | 源 GPU 的梯度、激活值、KV Cache 或参数分片
GPU0 NVLink | 离开源 GPU
NVSwitch fabric | 单机内交换网络
GPU1/GPU2/.../GPU7 NVLink | 进入目标 GPU
目标 GPU HBM | 写入目标显存
```

在这种服务器内：

1. **GPU 自己的计算数据在 HBM 中**。
   模型参数、梯度、激活值、KV Cache 等主要在 GPU HBM。H100 SXM 的 GPU memory bandwidth 是 **3.35 TB/s**，H100 NVL 规格中列出的 memory bandwidth 是 **3.9 TB/s**。A100 80GB PCIe/SXM 的 GPU memory bandwidth 分别列为 **1,935 GB/s** 和 **2,039 GB/s**。

2. **GPU-GPU 通信走 NVLink/NVSwitch**。
   例如 GPU0 要把梯度 chunk 发给 GPU3，数据从 GPU0 HBM 读出，经 NVLink 进入 NVSwitch，再通过 NVLink 到 GPU3 HBM。CPU 不拷贝这段数据。

3. **CPU 主要负责控制和调度**。
   CPU 会启动 CUDA kernel、初始化 NCCL communicator、管理进程、内存注册、同步等，但真正的数据平面不应该经过 CPU 内存。

4. **PCIe 仍然存在，但不是 GPU-GPU 主通道**。
   PCIe 仍负责 CPU-GPU 控制、Host memory 到 GPU memory 的数据加载、GPU 到 NIC 的路径、GPU 到 NVMe 或存储路径，以及没有 NVLink 可用时的 fallback。

### 8 卡 PCIe 服务器：GPU-GPU 可能走 PCIe P2P 或 Host staging

如果是 PCIe 形态的 8 卡服务器，拓扑就更复杂。典型路径可能是：

```flow
GPU0 | 源 GPU
PCIe switch | 同 switch 下 P2P
GPU1 | 目标 GPU
```

也可能是：

```flow
GPU0 | 源 GPU
PCIe switch | 本地 PCIe switch
CPU root complex | 本地 CPU root
CPU interconnect | 跨 Socket，例如 UPI / Infinity Fabric
另一个 CPU root complex | 远端 Socket root
PCIe switch | 远端 PCIe switch
GPU5 | 目标 GPU
```

如果 P2P 不可用，可能退化为：

```flow
GPU0 HBM | 源 GPU 显存
CPU pinned memory | 主机中转缓冲区
GPU5 HBM | 目标 GPU 显存
```

这就是为什么 8 卡 PCIe 服务器做大模型训练时，性能通常不如 8 卡 SXM/NVSwitch 服务器。PCIe 服务器不是不能训练，而是 GPU-GPU 通信密集型任务会更容易被互联瓶颈限制。

## 单机内 AllReduce 数据如何走？

以 8 卡数据并行训练为例，每张 GPU 都有一份模型副本，每轮 backward 后需要同步梯度。NCCL 通常会根据拓扑选择 ring、tree、CollNet、NVLS 等算法。概念上可以理解为：

```text
GPU0 梯度 chunk A → GPU1 → GPU2 → ... → GPU7
GPU1 梯度 chunk B → GPU2 → GPU3 → ... → GPU0
...
```

在 SXM/NVSwitch 机器里，这些 chunk 主要沿 NVLink/NVSwitch 交换。

更具体地说：

1. 每张 GPU 把梯度切成多个 chunk。
2. reduce-scatter 阶段，每个 chunk 沿环或树传播，并在目标 GPU 上累加。
3. all-gather 阶段，累加后的结果再分发回所有 GPU。
4. 如果 NVLink/NVSwitch 可用，NCCL 会尽量让通信走 GPU-GPU 高速路径。
5. 如果某些 GPU 间只能走 PCIe，通信图会变慢，尤其是跨 Socket GPU 对。

因此在单机 8 卡服务器中，**拓扑好坏直接影响 AllReduce 的有效带宽**。

## 服务器之间，数据如何流转？

跨服务器时，NVLink 通常只管本机内 GPU；跨机要靠 NIC 和网络。理想路径是 **GPUDirect RDMA**。

### 有 GPUDirect RDMA 时

假设 Server A 的 GPU0 要发数据给 Server B 的 GPU3，理想路径是：

```flow
Server A GPU0 HBM | 源 GPU 显存
Server A PCIe / PCIe switch | GPU 到 NIC 的本机路径
Server A RDMA NIC | NIC 直接读 GPU memory
InfiniBand/RoCE 网络交换机 | 跨机传输
Server B RDMA NIC | 远端 NIC 接收
Server B PCIe / PCIe switch | NIC 到远端 GPU 的路径
Server B GPU3 HBM | 写入远端 GPU 显存
```

这个路径的关键点是：

- NIC 可以直接读写 GPU memory。
- 数据不需要先拷贝到 CPU DRAM。
- CPU 主要负责控制面，例如注册内存、提交 work request、处理中断或轮询 completion queue。
- 数据面由 GPU、PCIe、NIC、网络交换机完成。

NVIDIA 对 GPUDirect RDMA 的说明是，它为远程系统中的 NVIDIA GPU 提供直接通信，并消除系统 CPU 和经由系统内存的数据 buffer copy。

### 没有 GPUDirect RDMA 或拓扑不佳时

如果不能直接从 GPU memory 做 RDMA，可能退化为：

```flow
Server A GPU0 HBM | 源 GPU 显存
Server A CPU pinned memory | 本机 host staging
Server A NIC | 从 CPU 内存发包
网络 | 跨机传输
Server B NIC | 远端接收
Server B CPU pinned memory | 远端 host staging
Server B GPU3 HBM | 再拷贝到目标 GPU
```

这会多出两侧 host memory staging：

- GPU → CPU 内存。
- CPU 内存 → NIC。
- 远端 NIC → CPU 内存。
- CPU 内存 → GPU。

这类路径会显著增加延迟、占用 CPU 内存带宽，并降低通信吞吐。

## 8 卡 H100/A100 多机训练的典型通信层级

多机多卡训练通常采用**分层通信**：

```flow
单机内 GPU ↔ GPU | NVLink / NVSwitch
跨机器 GPU ↔ NIC ↔ 网络 ↔ NIC ↔ GPU | GPUDirect RDMA
CPU 控制面 | 控制、调度、内存注册、进程管理，不应成为大规模数据搬运路径
```

以两台 8 卡服务器做 AllReduce 为例，较优通信流程通常是：

1. **每台机器内部先 reduce**。
   8 张 GPU 先通过 NVLink/NVSwitch 做本机内 reduce-scatter，这样可以把本机内的高带宽利用起来。

2. **每台机器通过 NIC 跨机交换部分结果**。
   每台服务器的 GPU 数据通过 GPUDirect RDMA 发到对端。如果有多张 NIC，会做 multi-rail 并行。

3. **每台机器内部再 all-gather**。
   跨机同步完成后，再通过本机 NVLink/NVSwitch 分发给本机所有 GPU。

这就是为什么大规模训练通信库通常会做 topology-aware 优化：**先用单机内最快的 NVLink/NVSwitch，跨机部分才使用 RDMA**。

## 为什么 NUMA、Socket、NIC 亲和性很重要？

即使都有 H100/A100 和 400G RDMA，性能也可能差很多，原因是本机内 GPU 到 NIC 的路径不同。

### 情况一：GPU 和 NIC 在同一 PCIe switch / 同一 Socket 下

```flow
GPU | 源 GPU
PCIe switch | 本地 PCIe 路径
NIC | 同 switch 或同 Socket 下的 RDMA 网卡
```

这是比较理想的路径：

- 路径短。
- 不跨 CPU socket。
- PCIe 带宽更可控。
- GPUDirect RDMA 效率较高。

### 情况二：GPU 和 NIC 跨 Socket

```flow
GPU | 源 GPU
PCIe switch | GPU 所在侧
CPU Socket 0 | 本地 socket
CPU interconnect | 跨 Socket 互联
CPU Socket 1 | NIC 所在侧
PCIe root complex | 远端 root
NIC | 目标 RDMA 网卡
```

这会带来：

- 更高延迟。
- 更低有效带宽。
- 更强抖动。
- CPU socket 间互联被占用。
- 多任务并发时更容易产生瓶颈。

所以调度 8 卡任务时，不仅要看 GPU-GPU 是否同属 NVLink/NVSwitch 域，还要看 **GPU-NIC 路径**。跨机训练时，GPU 到 NIC 的亲和性几乎和 GPU 到 GPU 的亲和性一样重要。

## 通信路径优先级总结

### 单机内 GPU-GPU

```flow
优先级 1：NVLink / NVSwitch | 单机内最优 GPU-GPU 路径
优先级 2：PCIe P2P，同 PCIe switch | 没有 NVLink 时的较优 fallback
优先级 3：PCIe P2P，跨 root complex / 跨 Socket | 路径变长，延迟和抖动增加
优先级 4：GPU → CPU pinned memory → GPU | Host staging，通常应避免
```

### 跨机 GPU-GPU

```flow
优先级 1：GPU HBM → 本地 NIC → RDMA 网络 → 远端 NIC → 远端 GPU HBM | GPUDirect RDMA，理想路径
优先级 2：GPU HBM → 本地 CPU 内存 → NIC → 网络 → 远端 CPU 内存 → 远端 GPU HBM | Host staging，性能较差
```

### 综合排序

```flow
NVLink/NVSwitch 单机内通信 | GPU-GPU 最优路径
PCIe P2P 单机内通信 | 通用总线上的设备间直连
GPUDirect RDMA 跨机通信 | 跨服务器的理想数据路径
Host staging 跨机通信 | 经过 CPU 内存中转，尽量避免
```

注意：这里的排序是工程上的常见优先级，不代表所有消息大小下都绝对成立。小消息更敏感于 latency，大消息更敏感于 bandwidth，实际还要看 NCCL 算法、batch size、通信 overlap、网络拥塞和拓扑绑定。

## 对调度和性能优化的启示

### 单机 8 卡任务

如果任务正好需要 8 张 GPU，最优是：

```text
同一台 HGX/DGX 8 卡机器
  + 同一 NVSwitch fabric
  + GPU 到 NIC 拓扑均衡
```

不建议把一个强通信任务拆成：

```text
4 卡在机器 A + 4 卡在机器 B
```

除非单机没有 8 卡资源，或者任务本身跨机并行效率很好。因为这样会把本来可以走 NVLink/NVSwitch 的通信变成 RDMA 跨机通信。

### 4 卡任务

如果一个任务只需要 4 张 GPU，优先级通常是：

1. 同一 NVLink/NVSwitch 域内的 4 张 GPU。
2. 同一 PCIe switch 或同一 Socket 下的 4 张 GPU。
3. 同机但跨 Socket 的 4 张 GPU。
4. 跨机器 2+2 或 1+3。

原因是跨 Socket 和跨机都会增加通信路径长度，并引入 PCIe、CPU interconnect、NIC、交换机等额外瓶颈。

### 多机 8×N 卡任务

多机训练时，调度器需要同时考虑：

- 每台机器内部是否是完整 8 卡 NVSwitch 拓扑。
- 每张 GPU 到 NIC 的距离。
- NIC 数量和 rail 分布。
- 多台机器是否在同一 leaf switch 或同一网络 pod。
- 是否有 RDMA 拥塞。
- NCCL topology file 或自动探测结果是否正确。

## 常见排查命令

| 目标 | 命令 / 工具 | 看什么 |
|---|---|---|
| 查看 GPU-GPU / GPU-NIC 拓扑 | `nvidia-smi topo -m` | GPU 是否 NVLink 互联，GPU 到 NIC 是否同 NUMA |
| 查看 NCCL 选择的路径 | `NCCL_DEBUG=INFO NCCL_DEBUG_SUBSYS=INIT,GRAPH` | ring/tree/NVLS/IB 路径是否符合预期 |
| 查看 IB/RDMA 设备 | `ibstat`、`ibv_devinfo` | 端口速率、链路状态、HCA 能力 |
| 查看 PCIe 拓扑 | `lspci -tv` | GPU、NIC、PCIe switch、root complex 关系 |
| 查看 NUMA 拓扑 | `numactl --hardware`、`lstopo` | CPU、内存、PCIe 设备亲和性 |

排查时不要只看“有没有 8 张 GPU”，而要同时看：

- GPU-GPU 是否走 NVLink/NVSwitch。
- GPU-NIC 是否跨 Socket。
- RDMA 是否启用 GPUDirect。
- NCCL 是否真的选择了 IB/RDMA，而不是 fallback 到 TCP。
- 是否存在某个慢 rank、慢 NIC 或拥塞路径拖累整体。

## 一句话面试版回答

NVLink/NVSwitch 是 8 卡 H100/A100 服务器内部 GPU-GPU 通信的主路径，带宽可达数百 GB/s 到 900 GB/s 级别；PCIe 是 CPU、GPU、NIC 之间的通用 I/O 总线，A100 常见是 Gen4，H100 常见是 Gen5，带宽明显低于 NVLink；RDMA 是跨服务器通信机制，通常通过 InfiniBand 或 RoCE，把本机 GPU memory 经 NIC 和网络直接写到远端 GPU memory，避免 CPU host memory staging。单机内训练通信应优先走 NVLink/NVSwitch，跨机时应使用 GPUDirect RDMA，并尽量保证 GPU-NIC 在同一 NUMA/SOCKET/PCIe switch 附近，否则跨 Socket 会增加延迟、降低有效带宽并引入抖动。

## 参考资料

1. [NVIDIA H100 Tensor Core GPU](https://www.nvidia.com/en-us/data-center/h100/)
2. [NVIDIA A100 Tensor Core GPU](https://www.nvidia.com/en-us/data-center/a100/)
3. [PCI-SIG: PCIe 5.0 bit rates](https://pcisig.com/what-bit-rates-does-pcie-50-specification-support-and-how-does-it-compare-prior-pcie-generations)
4. [NVIDIA Quantum-2 InfiniBand Platform](https://www.nvidia.com/en-us/networking/quantum2/)
5. [NVIDIA GPUDirect](https://developer.nvidia.com/gpudirect)

## cgroups 是什么？

**cgroups** 是 Linux 内核提供的资源控制机制，全称是 **control groups**。它可以限制、统计、隔离一组进程的资源使用。

常见资源包括：

- CPU
- 内存
- I/O
- 进程数
- 设备访问权限
- 网络优先级

容器本质上大量依赖：

```text
namespace + cgroups + capabilities + seccomp
```

其中：

- **namespace** 负责“看见什么”。
- **cgroups** 负责“能用多少”。
- **capabilities/seccomp** 负责“能做什么”。

## cgroups v1 与 v2

### cgroups v1

cgroups v1 是多层级、多 controller 模型：

```text
/sys/fs/cgroup/cpu/...
/sys/fs/cgroup/memory/...
/sys/fs/cgroup/blkio/...
/sys/fs/cgroup/devices/...
```

不同资源 controller 可以有不同的 cgroup 树。优点是灵活、历史兼容性好；缺点是层级复杂，不同 controller 行为不统一。

### cgroups v2

cgroups v2 是统一层级模型：

```text
/sys/fs/cgroup/...
```

所有 controller 在同一棵树上协同工作。它的接口更统一，语义更清晰，也更适合现代容器运行时和 systemd 管理。

| 维度 | cgroups v1 | cgroups v2 |
|---|---|---|
| 层级模型 | 多 hierarchy | 统一 hierarchy |
| controller 行为 | 不同 controller 差异大 | 语义更统一 |
| 容器生态 | 历史兼容多 | 现代发行版逐步默认 |
| AI Infra 关注 | 老集群常见 | 新集群、systemd、K8s 新版本更常见 |

## CPU 限制：quota、weight、cpuset

CPU 资源常见控制方式包括三类。

### CPU quota / period

限制一段周期内最多可用多少 CPU 时间。

例如 cgroups v2：

```text
cpu.max = 200000 100000
```

含义可以理解为：

```text
每 100ms 周期内最多使用 200ms CPU 时间
```

也就是最多约等于 2 个 CPU core。

### CPU weight / shares

用于相对权重分配。多个 cgroup 竞争 CPU 时，权重高的获得更多 CPU 时间。它不是硬上限，而是竞争时的比例。

### cpuset

限制进程只能运行在哪些 CPU core 上。

```text
cpuset.cpus = 0-31
```

表示这个 cgroup 只能使用 0 到 31 号 CPU。在大模型训练中，`cpuset` 很重要，因为它可以配合 NUMA 绑定，让某个训练进程只使用靠近目标 GPU 的 CPU cores。

```flow
调度器分配 GPU | 例如容器获得 GPU0
选择邻近 CPU cores | 例如 Socket0 的 0-31 号 core
设置 cpuset | 限制容器 CPU affinity
设置内存策略 | 尽量从同 NUMA node 分配内存
减少跨 Socket | DataLoader、H2D、RDMA 路径更稳定
```

## 内存限制：memory.max、memory.high、swap

内存 controller 可以限制：

- 最大内存使用量
- swap 使用
- 内存压力
- OOM 行为
- page cache 使用

典型限制包括：

```text
memory.max
memory.high
memory.swap.max
```

其中：

- `memory.max` 是硬限制，超过后可能触发 OOM。
- `memory.high` 是软限制，超过后会触发 reclaim 和 throttling。
- `memory.swap.max` 控制 swap 使用。

在训练/推理场景中，如果容器内存限制过紧，可能出现：

- DataLoader worker 被 OOM kill。
- page cache 不够导致权重加载变慢。
- 频繁 reclaim 导致吞吐抖动。
- pinned memory 分配失败。
- 推理服务 P99 因内存回收而升高。

## I/O 限制：带宽、IOPS、权重

I/O controller 可以限制块设备读写，例如：

- 读带宽上限
- 写带宽上限
- IOPS 上限
- I/O 权重

典型场景：

```text
一个推理服务正在加载 100GB 权重
另一个训练任务正在读取海量样本
```

如果没有 I/O 隔离，可能互相影响：

- 权重加载变慢。
- 训练数据读取抖动。
- page cache 被冲掉。
- 延迟 P99 升高。

因此生产集群中经常需要对不同任务做 I/O QoS，例如训练任务、在线推理服务、模型分发服务、checkpoint 写入任务不能无约束地抢同一块盘或同一个网络存储。

## cgroups 怎么感知 GPU？

严格说：

> **Linux cgroups 原生并不知道“GPU 算力百分比”这种资源。**

cgroups 对 GPU 的管理主要不是通过“限制 GPU SM 使用率”实现的，而是通过 **设备访问控制** 和 **容器运行时注入** 实现的。

## 路径一：devices controller

Linux 中 GPU 设备通常表现为字符设备文件：

```text
/dev/nvidia0
/dev/nvidia1
/dev/nvidiactl
/dev/nvidia-uvm
/dev/nvidia-uvm-tools
```

cgroups 的 devices controller 可以控制进程是否允许访问这些设备。

例如，容器只被允许访问：

```text
/dev/nvidia0
/dev/nvidiactl
/dev/nvidia-uvm
```

那么它就只能看到或使用 GPU 0。这种方式控制的是：

```text
能不能打开某个 GPU 设备文件
```

不是直接控制：

```text
GPU 算力使用 30%
GPU 显存最多 20GB
GPU HBM 带宽最多 50%
```

## 路径二：NVIDIA Container Toolkit

容器中使用 GPU 通常依赖 NVIDIA Container Toolkit。它会根据环境变量或容器配置，把对应 GPU 设备、驱动库、运行时依赖挂载到容器中。

常见控制变量包括：

```text
NVIDIA_VISIBLE_DEVICES
NVIDIA_DRIVER_CAPABILITIES
```

例如：

```bash
docker run --gpus '"device=0,1"' ...
```

容器内通常只会看到指定 GPU。在 Kubernetes 中，通常通过：

```text
NVIDIA Device Plugin
Kubelet
Container Runtime
NVIDIA Container Toolkit
```

协同实现 GPU 分配。

## GPU 显存和算力怎么隔离？

cgroups 本身通常不直接精细限制 GPU SM、Tensor Core、HBM 带宽或显存容量；这些通常需要 GPU 驱动、MIG、MPS、容器运行时和上层调度器协同完成。

| 方案 | 隔离对象 | 优点 | 局限 |
|---|---|---|---|
| 整卡分配 | 一张或多张完整 GPU | 简单、隔离相对好 | 资源利用率可能低 |
| MIG | GPU 硬件实例 | 硬件级切分，显存/算力相对隔离 | 仅特定 GPU 支持，规格固定 |
| MPS | 多进程共享 GPU | 降低上下文切换，提高小 kernel 并发 | 隔离弱于 MIG |
| time-slicing | 时间片共享 | 简单，适合开发/低优任务 | 性能抖动明显 |
| 框架限制 | 进程级显存策略 | 易用，例如 PyTorch fraction | 不是真正硬隔离 |
| 调度器记录 | 上层资源账本 | 能做配额和准入控制 | 依赖平台实现 |

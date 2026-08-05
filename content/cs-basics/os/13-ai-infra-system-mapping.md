## 一句话结论

操作系统专题负责解释进程、虚拟内存、I/O、调度和隔离这些底层机制；容器、GPU、训练和推理专题负责解释它们在具体 AI Infra 系统里如何落地。复习时要能完成“现象 → OS 机制 → 专项模块”的映射，但不要在 OS 页面重复背一遍专项实现。

## 知识边界

| OS 基础 | 在 AI Infra 中的现象 | 深入模块 |
|---|---|---|
| namespace、cgroup、rootfs | 容器隔离、OOMKilled、CPU throttling、`/dev/shm` 不足 | Linux 与容器、Linux 内核与大模型 |
| 虚拟内存、page cache、mmap | 权重加载慢、RSS 与 page cache 混淆、缺页抖动 | Linux 内核与大模型、LLM 推理 |
| NUMA、CPU affinity | DataLoader 供给不足、跨 Socket H2D、GPU-NIC 路径变长 | 计算机组成、GPU |
| DMA、pinned memory | H2D/D2H 拷贝与计算无法重叠 | GPU |
| epoll、线程池、协程 | 推理网关排队、CPU 前后处理、连接数扩展 | LLM 推理 |
| 文件系统与 I/O | 数据集小文件、Checkpoint、模型冷启动 | 分布式训练、LLM 推理 |
| signal、进程生命周期 | Pod 优雅终止、训练任务保存 Checkpoint | Kubernetes、分布式训练 |
| perf、strace、eBPF | CPU 热点、系统调用阻塞、长尾延迟 | 各专项排障页 |

## 面试回答方法

遇到系统问题时先分四层，不要一上来只报命令：

```flow
业务现象 | 吞吐、延迟、失败率、GPU 空转
进程与容器 | 状态、线程、cgroup、OOM、FD、共享内存
主机资源 | CPU、内存、NUMA、磁盘、网络
加速器与分布式 | H2D、SM、HBM、NCCL、GPU 拓扑
```

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 容器 OOM 和宿主机 OOM 怎么区分？</div>
<div class="qa-a"><p>先看 Pod termination reason、exit code 137 和事件，再看对应 cgroup 的 <code>memory.current</code>、<code>memory.max</code> 与 <code>memory.events</code>。如果进程触及容器 memory limit，通常是 cgroup 内 OOM；如果节点整体内存耗尽，则还要结合宿主机 <code>dmesg</code>、系统可用内存和其他进程判断。详细隔离机制放在“Linux 与容器”。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 利用率低为什么也可能是操作系统问题？</div>
<div class="qa-a"><p>GPU 可能在等 CPU 解码、DataLoader、page fault、磁盘或网络 I/O，也可能因为 NUMA 放置不当导致 H2D 路径变长。OS 负责解释供给链为什么阻塞；SM Active、Warp Stall 和 NCCL 等 GPU 专项判断放在 GPU 与分布式训练页面。</p></div>
</div>

## 常见误区

- cgroup 能限制 CPU、内存和设备访问，不等于它能直接切分 GPU 的 SM 与 HBM。
- 显存占用高只说明资源常驻，不说明 GPU 正在高效计算。
- `top` 中 CPU 不满不能排除单核热点、锁竞争、系统调用等待和 NUMA 问题。
- `mmap` 不等于数据已经进入物理内存；首次访问仍可能触发缺页。

## 关联模块

- `Linux 与容器基础`：namespace、cgroup、rootfs、CRI/OCI 的完整实现。
- `Linux 内核与大模型系统`：NUMA、大页、零拷贝和权重加载。
- `GPU 硬件与资源共享`：CUDA、数据搬运、GPU 共享与性能诊断。
- `Kubernetes 核心`：Pod 生命周期、资源模型和节点排障。
- `LLM 推理系统 / 分布式训练`：OS 机制在 Serving 与训练链路中的具体表现。

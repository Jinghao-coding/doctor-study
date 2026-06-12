## 操作系统在 AI Infra 中的定位

操作系统是所有 AI Infra 系统运行的**底座**。无论是训练任务、推理服务，还是调度器、存储链路，最终都要落到操作系统提供的几个核心抽象上：进程/线程、虚拟内存、文件与 I/O、网络套接字、设备访问。

面试里考操作系统，本质是想确认一件事：你能不能把"上层框架的现象"翻译成"系统层的原因"。比如训练慢、显存 OOM、推理 p99 抖动、DataLoader 打不满 GPU，背后几乎都是 OS 层的并发、内存、I/O 或调度问题。

<div class="card card-d">
<h3>一句话定位</h3>
<p>上层的 PyTorch / vLLM / NCCL / K8s 都是把任务翻译成 <strong>进程、内存页、文件描述符、socket、设备 ioctl</strong> 这些 OS 原语来执行；懂 OS，才能解释清楚性能和稳定性问题的根因。</p>
</div>

## 与其他模块的关系

| 关联模块 | 关系 | OS 中对应的知识点 |
|---|---|---|
| 计算机组成原理 / GPU | OS 之下是硬件 | NUMA、PCIe、cache、DMA、pinned memory |
| 容器与 K8s / 集群管理 | OS 之上是隔离与编排 | namespace、cgroup、容器 OOM、CPU throttling |
| 分布式训练 | 并发与通信落到 OS | 线程/进程、GIL、NCCL 背后的 socket/RDMA |
| LLM 推理系统 | 内存与延迟落到 OS | KV cache 显存、page cache、p99 抖动排查 |
| 计算机网络 | 网络栈的系统调用入口 | socket、epoll、TCP 状态机、零拷贝 |

## 本模块包含哪些内容

下面每个标签页都是一个独立板块，建议按"先底层机制、再 AI Infra 场景"的顺序看：

| 板块 | 覆盖内容 | 典型面试问题 |
|---|---|---|
| 进程线程并发 | 进程/线程/协程、IPC、同步、死锁、GIL、DataLoader | 进程和线程区别？Python 多线程为什么吃不满多核？ |
| 内存管理 | 虚拟内存、分页、TLB、mmap、COW、page cache、OOM、NUMA | 训练任务 OOM 怎么定位？mmap 加载权重的代价？ |
| 文件系统与 I/O | fd/inode、buffered/direct I/O、fsync、epoll、零拷贝 | checkpoint 保存慢怎么优化？fsync 为什么卡？ |
| CPU 调度与性能 | 调度、上下文切换、load/iowait/steal、cache、perf | CPU 利用率高但吞吐低怎么查？ |
| 网络与系统调用 | socket、握手挥手、TIME_WAIT、epoll LT/ET | 分布式训练通信慢从系统层怎么查？ |
| 容器与 cgroup | namespace、cgroup、容器 OOM、CPU throttling、/dev/shm | 容器内任务被 OOM kill 怎么排查？ |
| GPU 系统层 | DMA、pinned memory、NUMA 亲和、PCIe 拓扑、H2D 流水 | pinned memory 为什么能提升 H2D？ |
| 排障工具链 | top/pidstat/iostat/ss/strace/perf/nvidia-smi、p99 排查 | 线上问题你怎么一步步定位？ |

## 推荐复习优先级

| 优先级 | 板块 | 原因 |
|---|---|---|
| P0 | 进程线程并发 | 高频基础，和训练数据加载、推理服务强相关 |
| P0 | 内存管理 | OOM、mmap、page cache、COW 都是 AI Infra 常见问题 |
| P0 | 文件系统与 I/O | 数据加载、checkpoint、权重加载经常涉及 |
| P0 | 排障工具链 | 面试常考"线上问题怎么定位" |
| P1 | CPU 调度与性能 | 性能优化、服务吞吐、GPU feeding 相关 |
| P1 | 网络与系统调用 | 分布式训练、推理服务、RPC 必备 |
| P1 | 容器与 cgroup | AI Infra 基本都运行在容器 / K8s 环境中 |
| P1 | GPU 系统层 | 区分普通后端候选人与 AI Infra 候选人的关键 |

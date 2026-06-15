## 一句话结论

Linux CFS 和 CUDA thread/block 调度都叫“调度”，但它们解决的是完全不同层次的问题。

**Linux CFS 是 CPU 上的操作系统调度器**，调度对象是进程或线程，目标是公平性、响应性和 CPU 时间共享。它通过 `vruntime`、优先级权重、抢占和上下文切换来决定哪个任务运行。

**CUDA thread block 调度主要由 GPU 硬件完成**，调度对象是 kernel grid 中的 block，也叫 CTA。GPU 把 block 分配到 SM 上执行；block 一旦驻留在某个 SM 上，通常会运行到完成。SM 内部再通过 warp scheduler 在多个 ready warp 之间切换，以隐藏访存和执行延迟。

**CUDA Stream/Event 又是另一层**。它们不是 kernel 内部 thread 的调度器，而是 CUDA 程序员用来表达任务级异步执行和依赖关系的工具。

## 系统链路

```flow
Linux CFS | OS 决定哪个进程/线程拿到 CPU 时间片
CUDA Stream/Event | 程序员组织 H2D、kernel、D2H 等 GPU 任务的顺序和依赖
CUDA Block 调度 | GPU 把 grid 里的 block 分配到 SM
Warp Scheduler | SM 内部选择 ready warp 发射指令
```

## 为什么这个问题容易混淆？

因为“线程”这个词在 CPU 和 GPU 里含义不同。

| 名词 | CPU/Linux 语境 | CUDA/GPU 语境 |
|---|---|---|
| Thread | OS 可调度实体，可能对应内核线程或用户线程 | CUDA 逻辑执行单元，运行同一份 kernel 代码 |
| Scheduler | Linux 内核调度器，决定哪个 task 运行在 CPU core | GPU 硬件/驱动/runtime 多层机制，把 block/warp 放到硬件上执行 |
| Context switch | 保存/恢复 CPU 寄存器、地址空间、内核栈等 | GPU block/warp 不是按 CFS 时间片做频繁 OS 式切换 |
| Fairness | 多进程共享 CPU 时间，要尽量公平 | GPU kernel 更关心吞吐、occupancy 和 latency hiding |
| Preemption | CFS 可以抢占当前 CPU task | block 一旦驻留 SM 通常运行到完成，GPU 任务抢占粒度更粗、代价更高 |

所以面试回答时要先分层：

- **CPU OS 调度层**：进程/线程如何共享 CPU。
- **CUDA 任务提交层**：stream/event 如何组织 GPU work。
- **GPU kernel 执行层**：block/warp 如何映射到 SM。
- **集群资源调度层**：K8s/Volcano/YARN 等如何分配 GPU 设备给任务。

不要把这四层混成一个“GPU 调度器”。

## Linux CFS：公平地分 CPU 时间

CFS 全称是 Completely Fair Scheduler，目标不是让某个任务跑到最快，而是在多个 runnable task 之间尽量公平地分配 CPU 时间，同时兼顾交互响应。

### CFS 调度对象

CFS 调度的是 Linux 内核里的 `task_struct`。对用户来说，它可以表现为：

- 一个进程；
- 一个线程；
- 一个容器里的某个线程；
- 一个 cgroup 下的一组任务。

在 Linux 里，线程和进程最终都可以作为调度实体参与 CPU 调度。CFS 不关心这个任务是不是 AI 训练、数据加载、推理服务、日志线程，它只看到“这个 runnable task 需要 CPU”。

### vruntime：谁“欠 CPU 时间”最多

CFS 的核心指标是 `vruntime`，可以理解成“加权后的虚拟运行时间”。

- 任务真实运行越久，`vruntime` 越大。
- nice 值越低、优先级越高，权重越大，同样运行一段真实时间，`vruntime` 增长越慢。
- 调度器倾向于选择 `vruntime` 最小的任务运行，因为它看起来“拿到的公平份额最少”。

直觉上：

```text
谁的 vruntime 小，说明谁相对更“饿”，应该优先给 CPU。
谁的 vruntime 大，说明谁已经跑得比较多，可以先等一等。
```

这和传统时间片轮转不一样。Round Robin 更像“每个人轮流拿固定时间片”；CFS 更像“持续维护每个人已经拿到的公平份额”。

### nice、weight 和公平份额

Linux 的 nice 值会影响任务权重。

| nice 值 | 权重直觉 | 结果 |
|---|---|---|
| 更小，例如 `-10` | 权重更大 | 同样时间内获得更多 CPU 份额 |
| 默认 `0` | 默认权重 | 普通任务 |
| 更大，例如 `10` | 权重更小 | 更愿意让出 CPU |

CFS 不是简单地“高优先级永远先跑”。它通过权重影响 `vruntime` 增长速度，让高权重任务在长期上获得更多 CPU 时间，但仍然允许其他任务运行。

### runqueue 和红黑树

每个 CPU 通常有自己的 runqueue。CFS 会把 runnable task 按 `vruntime` 组织起来，经典实现使用红黑树。

```flow
任务变为 runnable | 进入当前 CPU 的 CFS runqueue
按 vruntime 排序 | vruntime 小的任务排在更靠左的位置
选择最左任务 | 调度器选择 vruntime 最小的 task
运行一段时间 | task 的 vruntime 增加
重新入队或继续运行 | 根据抢占、阻塞、唤醒和时间粒度决定
```

这个结构的意义是：调度器能快速找到“最应该运行”的任务。

### 抢占和上下文切换

CFS 是抢占式调度。当前任务正在 CPU 上运行时，如果出现一个更应该运行的任务，调度器可以触发抢占。

常见触发点包括：

- 周期性 tick 或调度时钟更新；
- 当前任务主动阻塞，例如等待 IO、锁、网络；
- 新任务唤醒，例如交互请求到来；
- 当前任务运行超过合理粒度；
- 更高优先级或更小 `vruntime` 的任务需要运行。

CPU 上下文切换通常涉及：

- 保存当前任务寄存器状态；
- 切换内核栈；
- 切换或更新地址空间相关状态；
- 更新调度统计；
- 恢复下一个任务的执行上下文。

上下文切换不是免费的。线程数过多、锁竞争严重、频繁唤醒阻塞，都可能导致 CPU 时间花在调度和切换上，而不是有效计算上。

## CUDA Stream/Event：任务级异步调度

对 CUDA 程序员来说，Stream/Event 是控制 GPU work 提交顺序和依赖的工具。

**Stream 是 GPU 任务队列**：

- 同一个 stream 内的操作按提交顺序执行；
- 不同 stream 的操作可以并发执行，但前提是硬件资源允许；
- 常见操作包括 H2D 拷贝、kernel launch、D2H 拷贝、event record/wait。

**Event 是依赖和计时工具**：

- 可以记录某个 stream 上的进度点；
- 可以让另一个 stream 等待这个 event；
- 可以用于测量 GPU 端耗时；
- 可以避免 CPU 端粗暴 `cudaDeviceSynchronize()`。

```flow
CPU 提交任务 | 把 H2D、kernel、D2H 放进一个或多个 stream
Stream 保证顺序 | 同一 stream 内先提交的先执行
Event 表达依赖 | 一个 stream 可以等待另一个 stream 的完成点
GPU runtime/driver 派发 | 把 ready 的 work 交给 GPU 执行
硬件执行 kernel | 进入 block/SM/warp 层级
```

这里要强调：**stream 不等于 SM 调度器**。Stream 决定的是 kernel、memcpy 等任务之间的顺序和并发机会；block 和 warp 怎么在 SM 里执行，是更底层的硬件执行机制。

## CUDA Block / Warp 调度：吞吐优先

一次 kernel launch 会产生一个 grid，grid 里包含很多 block。GPU 的工作是把这些 block 分配到 SM 上执行。

### block 是调度到 SM 的基本单位

block 也常被称为 CTA（Cooperative Thread Array）。一个 block 里的 thread 可以：

- 共享 shared memory；
- 使用 `__syncthreads()` 做 block 内同步；
- 通过 thread/block index 处理不同数据。

GPU 硬件会把 block 调度到某个 SM。一个 block 一旦驻留到 SM 上，通常不会像 CPU task 那样被 CFS 时间片频繁抢占并迁移到另一个 SM，而是运行到完成。

这带来两个重要结论：

- 不同 block 之间默认没有执行顺序保证。
- block 数量要足够多，否则 SM 可能吃不满。

### block residency：为什么不是想放多少就放多少

一个 SM 能同时驻留多少个 block，受多种资源限制：

| 限制项 | 为什么影响 block 驻留 |
|---|---|
| 每个 block 的 thread 数 | SM 可同时容纳的 thread/warp 数有限 |
| 每个 thread 的 register 数 | register file 容量有限，register pressure 高会降低 occupancy |
| 每个 block 的 shared memory | shared memory 被 block 独占，使用多会减少可驻留 block |
| 架构上限 | 每个 SM 最大 block 数、warp 数、thread 数有硬件限制 |

所以 CUDA 调优不是“block 越大越好”。block 太小，单个 block 并行度不足；block 太大，可能占用太多 register/shared memory，导致 SM 上可同时驻留的 warp 变少。

### warp scheduler：隐藏内存延迟

block 被放到 SM 后，block 内 thread 会被组织成 warp。NVIDIA GPU 上一个 warp 通常是 32 个 thread。SM 内部的 warp scheduler 会在多个 ready warp 之间选择并发射指令。

它的关键目标不是公平，而是吞吐：

- 某个 warp 等 HBM 访存时，切换到另一个 ready warp；
- 某个 warp 遇到长延迟指令时，让其他 warp 填补流水线；
- 通过足够多 active warp 隐藏内存和执行延迟。

```flow
Block 驻留 SM | block 占用 register、shared memory、thread slots
Thread 组成 warp | 通常 32 个 thread 一组
Warp 等待访存 | 当前 warp 可能 stalled
选择 ready warp | warp scheduler 发射另一个可执行 warp
提高吞吐 | 用并发 warp 隐藏延迟，而不是追求单线程低延迟
```

这就是 GPU 和 CPU 的核心差异之一：CPU 用复杂控制逻辑优化单线程延迟；GPU 用大量 warp 并发隐藏延迟，追求整体吞吐。

## CFS vs CUDA 调度：核心对比

| 维度 | Linux CFS | CUDA block/warp 调度 |
|---|---|---|
| 所在层级 | 操作系统内核 | GPU runtime/driver + GPU 硬件 |
| 调度对象 | 进程/线程，也就是 task | grid 中的 block/CTA；SM 内部的 warp |
| 目标 | 公平性、响应性、CPU 时间共享 | 吞吐、occupancy、隐藏访存延迟 |
| 核心指标 | `vruntime`、nice/weight、调度延迟 | active warps、occupancy、warp stall、SM utilization |
| 抢占方式 | 可以抢占当前 CPU task | block 通常运行到完成，GPU 任务抢占粒度更粗 |
| 切换代价 | CPU 上下文切换较频繁，但相对可控 | GPU kernel/上下文抢占代价更高，不适合频繁时间片化 |
| 公平性 | 明确追求公平份额 | 不以线程公平为主，强调硬件利用率 |
| 程序员控制 | nice、cgroup、affinity、priority、policy | grid/block 配置、stream/event、kernel 设计 |
| 典型问题 | 线程过多、上下文切换、锁竞争、CPU 抢占 | block 太少、occupancy 低、warp divergence、访存不合并 |

面试中最容易犯的错是说“GPU 也像 CPU 一样靠 OS 调度每个 thread”。这不对。CUDA thread 是 GPU kernel 内的逻辑执行单元，不是 Linux CFS 直接调度的 OS thread。

## Stream/Event vs Thread Block/Warp：不同层次

对 CUDA 程序员来说，最需要区分的是这两层：

| 层次 | 你控制什么 | 典型 API / 概念 | 解决什么问题 |
|---|---|---|---|
| 任务级调度 | kernel、memcpy、依赖、并发机会 | `cudaStream_t`、`cudaEvent_t`、`cudaMemcpyAsync` | 计算/拷贝重叠，多 kernel 并发，减少 CPU 等待 |
| kernel 内执行 | block 数、thread 数、shared memory、访存模式 | `gridDim`、`blockDim`、`threadIdx`、warp、SM | 铺满 SM，减少 divergence，提高 occupancy 和访存效率 |

例子：

```text
stream1: H2D batch0 → kernel batch0 → D2H result0
stream2: H2D batch1 → kernel batch1 → D2H result1
```

这是 stream 层的并发组织。每个 `kernel batchX` 内部又会被拆成 grid/block/thread，并由 GPU 把 block 分配到 SM、把 thread 组织成 warp。

换句话说：

- Stream/Event 解决“多个 GPU 任务之间怎么排队、等待、重叠”。
- Block/Warp 调度解决“一个 kernel 内部怎么并行执行”。

## 和 AI Infra 的关系

这个对比不是纯 CUDA 八股。它能解释很多系统现象。

### 为什么 GPU 训练任务不适合像 CPU 一样频繁抢占？

CPU 线程抢占和上下文切换相对常见，CFS 正是为共享 CPU 时间设计的。但 GPU 训练任务通常有：

- 大量显存状态：模型参数、梯度、optimizer state、activation；
- NCCL communicator 和多 rank 同步；
- kernel 执行和通信 overlap；
- CUDA context、缓存分配器、通信 buffer；
- checkpoint 恢复成本。

如果频繁像 CPU 时间片一样抢占 GPU 训练任务，可能会导致上下文切换、显存迁移、通信重建和 checkpoint 回滚成本远大于收益。所以集群调度里 GPU 抢占往往要 checkpoint-aware、gang-aware，而不是简单时间片轮转。

### 为什么 Time Slicing 和 MPS 不等于 CUDA block 调度？

Kubernetes / NVIDIA device plugin 里的 GPU time-slicing、MPS 属于多进程/多 Pod 共享 GPU 的资源管理机制。

- Time Slicing：多个进程或容器按时间片共享 GPU。
- MPS：多个 CUDA 进程通过 MPS server 更高效共享 GPU 执行资源。
- CUDA block/warp 调度：一个 kernel 内部 block 和 warp 如何映射到 SM。

它们层次不同。不能说“开了 time-slicing 后，K8s 会调度 CUDA thread block”。K8s 只调度 Pod；NVIDIA device plugin/driver 负责 GPU 资源共享；kernel 内部 block/warp 仍由 GPU 硬件调度。

### 为什么 CPU 线程很多会拖慢 GPU 任务？

GPU kernel 虽然在 GPU 上执行，但 GPU 程序仍依赖 CPU：

- CPU 负责 dataloader、预处理、tokenization；
- CPU 发起 kernel launch；
- CPU 提交 H2D/D2H；
- CPU 管理 CUDA runtime、NCCL、RPC；
- CPU 处理服务端请求、排队和调度。

如果 CPU 侧线程过多、上下文切换严重、NUMA 绑定不合理或 dataloader 卡住，GPU 可能出现空洞：SM 没活干、GPU Util 周期性下降。此时问题不是 CUDA block 调度，而是 CPU 供给链路和 OS 调度压力。

## 高频面试问答

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Linux CFS 和 CUDA thread block 调度有什么本质区别？</div>
<div class="qa-a">
<p>Linux CFS 是 CPU 上的操作系统调度器，调度对象是进程或线程，目标是公平性、响应性和 CPU 时间共享。它用 <code>vruntime</code>、nice 权重、抢占和上下文切换决定哪个 task 在 CPU core 上运行。CUDA thread block 调度是 GPU kernel 内部的执行机制，调度对象是 grid 中的 block/CTA，GPU 把 block 分配到 SM 上；block 内 thread 再组成 warp，由 SM 的 warp scheduler 选择 ready warp 发射指令。CPU 调度强调公平和低延迟，GPU 调度强调吞吐和隐藏内存延迟。</p>
<div class="qa-summary">面试口径：CFS 调 OS task，CUDA block 调 kernel 内工作单元；前者公平，后者吞吐。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CUDA Stream/Event 和 Thread Block/Warp 调度是什么关系？</div>
<div class="qa-a">
<p>它们处在不同层次。Stream/Event 是任务级异步调度和依赖管理工具，用来组织 H2D、kernel、D2H 等 GPU work 的顺序、等待和重叠。同一个 stream 内顺序执行，不同 stream 可以并发；event 可以表达跨 stream 依赖。Thread Block/Warp 调度是 kernel 内部的硬件并行执行机制：一个 kernel launch 产生 grid，grid 中的 block 被调度到 SM，block 内 thread 被组织成 warp，SM 的 warp scheduler 在 ready warp 之间切换。</p>
<div class="qa-summary">一句话：Stream 管 kernel 之间，block/warp 管 kernel 里面。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU block 一旦被调度到 SM 后，会像 CPU 线程一样被频繁抢占吗？</div>
<div class="qa-a">
<p>通常不会。CPU 线程是 OS 调度实体，CFS 可以通过时间片和抢占频繁切换 runnable task。CUDA block 是 kernel 内部的工作单元，一旦驻留到某个 SM 上，通常运行到完成；SM 内部通过切换 ready warp 来隐藏延迟，而不是像 OS 一样把 block 按时间片迁移来迁移去。现代 GPU 支持某些粒度的抢占能力，但相对 CPU task 抢占更粗、更贵，AI 训练平台也不会把它当作常规公平时间片机制使用。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 GPU 调度更强调吞吐而不是公平？</div>
<div class="qa-a">
<p>GPU 的设计目标是把大量相似计算并行执行，尽量提高 SM、Tensor Core、HBM 带宽等资源的利用率。kernel 内部的 thread/warp 往往属于同一个计算任务，不需要像多用户 CPU 进程那样做强公平分配。SM 的 warp scheduler 更关心哪个 warp ready、能不能填满流水线、能不能隐藏访存延迟。公平性通常出现在更上层，例如多 Pod 共享 GPU、集群队列 quota、租户配额，而不是单个 kernel 内每个 CUDA thread 的公平时间片。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果 GPU 利用率周期性掉低，这和 CFS 有关系吗？</div>
<div class="qa-a">
<p>可能有间接关系。GPU 利用率掉低可能是 GPU kernel 本身太小、block 不足、访存低效，也可能是 CPU 侧没有及时喂数据。CPU 侧 dataloader、tokenizer、RPC worker、kernel launch 线程都受 Linux 调度影响。如果 CPU 线程过多、上下文切换严重、NUMA 远端访问、锁竞争或 IO 阻塞，GPU 就会等输入或等 launch，表现为周期性空洞。因此排查时要同时看 GPU timeline 和 CPU 侧 perf/top/线程状态，而不是只看 CUDA kernel。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CFS 的 vruntime 可以类比 GPU 的什么指标？</div>
<div class="qa-a">
<p>严格来说没有一一对应。<code>vruntime</code> 是 CFS 为了公平分配 CPU 时间定义的虚拟运行时间，用来决定哪个 OS task 更应该运行。GPU kernel 内部没有为每个 CUDA thread 维护类似 <code>vruntime</code> 的公平指标。GPU 更常看的指标是 active warps、occupancy、warp stall、SM Active、memory coalescing、HBM bandwidth 等，它们衡量的是硬件吞吐和延迟隐藏效果，而不是公平份额。</p>
</div>
</div>

## 一句话结论

关键指标 是 操作系统基础 的核心知识点，面试回答要先给结论，再说明机制边界、工程场景和常见误区。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 操作系统基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕进程线程、调度、虚拟内存、IO、多路复用、死锁、观测和 AI Infra OS 问题建立系统基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心概念、系统链路或关键机制，把知识点映射到工程场景。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

## AI Infra 面试模块：内存管理

AI Infra 的内存问题往往同时涉及虚拟内存、物理内存、page cache、cgroup limit、shared memory、NUMA locality 和 GPU pinned memory。面试回答要能把 Linux 内存机制和训练/推理场景联系起来。

### 需要掌握

- 虚拟内存、物理内存、地址空间：进程访问虚拟地址，MMU 通过页表翻译成物理地址。
- 分页、页表、TLB、缺页中断：页表保存映射，TLB 缓存地址翻译，缺页中断负责按需分配或换入。
- `mmap`：把文件或匿名内存映射到进程虚拟地址空间，访问时按需触发 page fault。
- copy-on-write：fork 后父子进程共享物理页，写入时才复制。
- 堆、栈、内存碎片、内存泄漏：堆用于动态分配，栈用于函数调用，泄漏会让 RSS 持续增长。
- `malloc/free` 基本思路：用户态 allocator 管理空闲块，必要时通过 `brk` 或 `mmap` 向内核申请。
- page cache 与 buffer cache：Linux 用空闲内存缓存文件内容，提高重复读取性能。
- swap：内存压力下把匿名页换出到磁盘，但训练/推理任务触发 swap 通常会导致吞吐断崖式下降。
- NUMA：本地内存访问快，远端内存访问延迟高、带宽低。

<div class="card card-s">
<h3>关键指标</h3>
<table>
<thead><tr><th>指标</th><th>含义</th><th>排查意义</th></tr></thead>
<tbody>
<tr><td>VIRT / VMS</td><td>虚拟地址空间大小</td><td>大不代表真实占用物理内存。</td></tr>
<tr><td>RES / RSS</td><td>实际驻留物理内存</td><td>判断进程真实内存压力的关键。</td></tr>
<tr><td>SHR</td><td>共享页</td><td>共享库、mmap 权重、shared memory 都会体现在这里。</td></tr>
<tr><td>Page Cache</td><td>文件缓存</td><td>看似占满内存，但通常可回收。</td></tr>
<tr><td>Major Fault</td><td>需要磁盘 I/O 的缺页</td><td>权重加载慢、训练抖动的重要信号。</td></tr>
<tr><td>Minor Fault</td><td>不需要磁盘 I/O 的缺页</td><td>匿名页分配、COW、已有页重新映射。</td></tr>
</tbody>
</table>
</div>

### AI Infra 相关关注点

- 大模型训练中的 CPU 内存、GPU 显存、page cache 之间是联动的：CPU 数据准备慢会饿死 GPU，GPU 显存不足会 OOM，page cache 不足会让重复读数据变慢。
- `mmap` 加载大模型权重可以避免一次性读取全文件，支持多进程共享 page cache，但访问时可能触发 page fault，导致启动抖动。
- fork DataLoader 时，父进程中已有的大对象初始会 COW 共享；worker 一旦写入对象，物理内存会复制，RSS 可能突然增大。
- OOM 定位要区分进程 RSS、VMS、shared memory、page cache、cgroup memory limit、宿主机 OOM 和容器 OOM。
- NUMA 绑定不合理会让 CPU worker 访问远端内存，或者跨 socket 给 GPU 准备数据，导致吞吐下降。

<div class="card card-m">
<h3>Linux OOM 与容器 OOM</h3>
<p>宿主机 OOM 是整机内存压力下由内核 OOM killer 选择进程杀掉；容器 OOM 是 cgroup memory limit 被突破，内核在该 cgroup 内杀进程。容器中 page cache、shared memory、DataLoader worker、日志 buffer、主进程 RSS 都可能共同顶满 limit。</p>
</div>

### 高频问题

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 虚拟内存解决了什么问题？</div>
<div class="qa-a"><p>虚拟内存提供进程隔离、连续地址空间、按需分配、换页、共享库和 mmap 能力。它让进程看到自己的虚拟地址空间，由 MMU 和页表映射到物理内存。代价是地址翻译需要 TLB/page table，缺页会进入内核，major fault 还会触发磁盘 I/O。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: malloc 后一定立刻占用物理内存吗？</div>
<div class="qa-a"><p>不一定。malloc 可能只是分配虚拟地址或复用 allocator 的空闲块，物理页通常在第一次写入时通过缺页中断分配。可以概括为：虚拟内存是承诺，物理内存是触碰页面后兑现。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: page cache 为什么会让内存看起来“被占满”？</div>
<div class="qa-a"><p>Linux 会尽量用空闲内存缓存文件页，提升后续读取性能，所以 free 看到的空闲内存可能很少。但 page cache 通常是可回收的，内存压力来时可以释放。排查时要看 available、cache、cgroup limit 和真正不可回收的 RSS。</p></div>
</div>

## 面试回答

**30 秒版：**

09 ai infra memory 是 操作系统基础 中的一个基础知识点，面试回答要先给结论，再说明机制、边界和工程场景。 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。

**2 分钟版：**

我会先说明这个知识点在 操作系统基础 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

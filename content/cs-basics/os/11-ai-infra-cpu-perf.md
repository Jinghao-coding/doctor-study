## AI Infra 面试模块：CPU 调度与性能分析

AI Infra 里 CPU 不是“辅助资源”。数据预处理、tokenizer、detokenizer、请求调度、网络协议栈、NCCL 辅助线程、checkpoint 序列化都可能让 CPU 成为瓶颈。

### 需要掌握

- 进程调度基本原理：内核从 runnable 队列中选择下一个任务运行。
- 时间片、优先级、抢占、上下文切换：调度器在公平性、响应时间和吞吐之间取舍。
- CPU load average 与 CPU utilization：load 包含 runnable 和不可中断睡眠任务；utilization 表示 CPU 实际忙碌比例。
- user、system、iowait、steal：分别代表用户态执行、内核态执行、等待 I/O、虚拟化环境被宿主抢占。
- cache locality、CPU cache、false sharing：线程迁移和共享 cache line 会影响吞吐。
- 软中断、硬中断：硬中断来自设备，软中断常用于网络包处理等延后工作。
- perf、top、htop、pidstat、vmstat、sar 等工具的基本使用。

### AI Infra 相关关注点

- GPU 训练时 CPU 数据准备不足会让 GPU 空转。
- 高 QPS 推理服务中，CPU 前处理、tokenizer、JSON 序列化、日志和网络协议栈可能成为瓶颈。
- 多线程服务中锁竞争、上下文切换过高、cache miss 过高会导致吞吐下降和 p99 抖动。
- 容器环境下 CPU quota、cpuset、CFS throttling 会让服务“看起来还有 CPU”，但实际被限流。

<div class="card card-s">
<h3>load high 不等于 CPU busy</h3>
<p>Linux load average 会统计 runnable 任务和 D 状态不可中断睡眠任务。大量任务卡在磁盘或网络 I/O，也会推高 load，但 CPU utilization 可能不高。因此判断 CPU 瓶颈要同时看 load、utilization、run queue、iowait、context switch 和线程栈。</p>
</div>

### 高频问题

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: load average 高是否一定说明 CPU 忙？</div>
<div class="qa-a"><p>不一定。load 包含 runnable 和不可中断睡眠任务。I/O 卡住、网络存储慢、D 状态进程多都可能让 load 很高。要结合 CPU utilization、iowait、run queue 和 D 状态进程判断。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: iowait 高说明什么？</div>
<div class="qa-a"><p>iowait 表示 CPU 空闲但系统中有任务在等 I/O。它提示 I/O 可能拖慢任务，但还要结合 iostat 的 await、util、吞吐和应用访问模式判断。训练中 iowait 高常见于数据集读取、checkpoint 或网络存储。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何用 perf 分析 CPU hotspot？</div>
<div class="qa-a"><p>先用 <code>perf top -p &lt;pid&gt;</code> 在线看热点，再用 <code>perf record -g -p &lt;pid&gt; -- sleep 30</code> 采样调用栈，最后用 <code>perf report</code> 或火焰图分析热点是在业务函数、系统调用、锁、内核网络栈、内存拷贝还是调度函数。</p></div>
</div>

## 一句话结论

这页是 OS 模块的收束：准备分三层——概念准确（每个机制能说清解决什么问题、原理、性能代价、在训练/推理里怎么体现）、能结合场景分析（GPU 利用率低、DataLoader 慢、OOM、p99 抖动、通信慢怎么排查）、熟悉 top/iostat/perf/nvidia-smi 等工具链。系统排查题用固定模板回答：先界定现象，再分层拆链路，用指标验证假设，最后给优化方案。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 操作系统基础 |
| 章节类型 | 面试收束类 |
| 解决问题 | 围绕进程线程、调度、虚拟内存、IO、多路复用、死锁、观测和 AI Infra OS 问题建立系统基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 准备方式与最小复习清单

这一页用于最后收束：怎样从概念走到场景分析，面试前最小需要覆盖哪些问题，以及常用工具链。

### 推荐准备方式

<div class="card card-s">
<h3>第一层：概念准确</h3>
<p>每个模块至少能解释：这个机制解决什么问题；核心原理是什么；有什么性能代价；它在 AI 训练或推理场景中如何体现。</p>
</div>

<div class="card card-d">
<h3>第二层：能结合场景分析</h3>
<ul>
<li>GPU 利用率低如何排查。</li>
<li>DataLoader 很慢如何优化。</li>
<li>训练任务 OOM 如何定位。</li>
<li>推理服务 p99 延迟升高如何分析。</li>
<li>分布式训练通信慢如何定位。</li>
<li>checkpoint 保存很慢如何优化。</li>
<li>容器内任务被 OOM kill 如何排查。</li>
</ul>
</div>

<div class="card card-m">
<h3>第三层：熟悉工具链</h3>
<pre><code>top / htop
ps
free
vmstat
iostat
pidstat
sar
ss
lsof
strace
perf
dmesg
nvidia-smi</code></pre>
<p>如果面试偏 Infra 或性能优化，建议进一步了解：</p>
<pre><code>numactl
numastat
ethtool
tcpdump
bcc / bpftrace
nsenter
cgget / systemd-cgtop</code></pre>
</div>

### 最小复习清单

1. 进程、线程、协程的区别。
2. 线程同步、死锁、锁竞争。
3. 虚拟内存、分页、缺页中断、TLB。
4. mmap、page cache、copy-on-write。
5. Linux OOM 与容器 OOM。
6. read/write、mmap、direct I/O 的区别。
7. epoll 原理与使用场景。
8. CPU load、utilization、iowait、context switch 的含义。
9. TCP 三次握手、四次挥手、TIME_WAIT。
10. namespace、cgroup、容器资源限制。
11. pinned memory、NUMA、PCIe topology 对训练性能的影响。
12. GPU 利用率低、服务延迟高、训练 OOM 的排查路径。

<div class="card card-w">
<h3>系统排查题回答模板</h3>
<ol>
<li><strong>先界定现象</strong>：影响范围、开始时间、是否稳定复现、p50/p99/吞吐/GPU 利用率哪个变坏。</li>
<li><strong>再分层拆链路</strong>：应用队列、CPU、内存、I/O、网络、GPU、容器限制、下游依赖。</li>
<li><strong>用指标验证假设</strong>：用 top、pidstat、iostat、ss、strace、perf、nvidia-smi、日志和 trace 逐层收敛。</li>
<li><strong>最后给优化方案</strong>：调参数、改并发模型、减少拷贝、增加缓存、调整 NUMA/绑核、优化 I/O 格式、扩容或限流。</li>
</ol>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

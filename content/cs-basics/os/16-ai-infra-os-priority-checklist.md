## 准备方式与最小复习清单

面试前需要能把 OS 概念映射到 AI Infra 场景，并掌握覆盖常见故障的最小工具链。

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

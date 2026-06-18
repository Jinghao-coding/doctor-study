## 一句话结论

排障要体现分层思维：先界定现象（影响范围、开始时间、是否稳定复现、是 p99 还是吞吐还是 GPU 利用率变坏），再按链路分层拆（应用队列、CPU、内存、I/O、网络、GPU、容器限制、下游依赖），用指标和工具逐层验证假设，最后给优化方案。指标发现异常、日志解释语义、trace 串联请求链路，这套方法对 GPU 空转、p99 抖动、OOM 都通用。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 操作系统基础 |
| 章节类型 | 排障诊断类 |
| 解决问题 | 围绕进程线程、调度、虚拟内存、IO、多路复用、死锁、观测和 AI Infra OS 问题建立系统基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## AI Infra 面试模块：系统可观测性与故障排查

AI Infra 面试经常问“线上问题怎么定位”。回答这类问题要体现分层思维：先界定现象，再看资源指标，再抓进程、系统调用、日志和 trace，最后形成假设并验证。

### 需要掌握

- 常用系统指标：CPU、内存、磁盘、网络、FD、线程数、上下文切换、系统调用耗时。
- 常用命令：top、htop、ps、free、vmstat、iostat、pidstat、sar、ss、lsof、strace、perf、dmesg。
- 日志、指标、trace 的定位思路：指标发现异常，日志解释语义，trace 串联请求链路。
- 系统调用耗时分析：strace 可以看到进程卡在 futex、read、write、poll、connect、fsync 等调用上。
- core dump、gdb 基础：进程崩溃或卡死时查看调用栈、线程状态和锁等待。

### AI Infra 相关关注点

- 训练任务卡住：看 GPU、CPU、DataLoader、NCCL 日志、网络、磁盘和进程栈。
- 吞吐下降：看 batch 时间拆分、CPU feeding、H2D、GPU compute、通信、checkpoint 和日志写入。
- GPU 空转：看 DataLoader queue、CPU worker、I/O、网络存储、tokenizer、请求流量。
- OOM：区分 CPU OOM、GPU OOM、容器 OOM、/dev/shm 不足和 allocator fragmentation。
- checkpoint 慢：看序列化、磁盘吞吐、网络存储、fsync、并发写和 dirty page writeback。
- 推理 p99 抖动：拆成排队、batching、CPU 前后处理、GPU 执行、网络、锁竞争、GC、下游依赖。

<div class="card card-d">
<h3>训练任务 GPU 利用率突然下降如何排查</h3>
<ol>
<li>先确认影响范围：单卡、单机、多机，还是所有卡同时下降。</li>
<li>看 GPU 指标：SM utilization、显存、PCIe/NVLink、power、temperature、ECC。</li>
<li>看 CPU 和 DataLoader：worker 是否打满，队列是否为空，上下文切换是否高。</li>
<li>看 I/O：iostat、网络存储、数据集小文件、page fault、解码耗时。</li>
<li>看通信：NCCL 日志、网络丢包/拥塞、rank 是否 hang。</li>
<li>看应用日志和 trace：是否 checkpoint、eval、日志上报、数据增强异常。</li>
</ol>
</div>

### 高频问题

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 推理服务 p99 latency 突然升高，你如何定位？</div>
<div class="qa-a"><p>先按请求链路拆分：入口排队、网络、鉴权/路由、tokenize、batch scheduler、GPU prefill/decode、detokenize、响应写回。再看资源：CPU、GPU、显存、队列长度、batch size、KV cache、网络连接、锁等待和 GC。最后用 trace 对比 p50/p99 请求，定位是哪一段变长。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 进程卡住没有日志，如何分析？</div>
<div class="qa-a"><p>先用 ps/top 看进程状态，是 R、S、D 还是 zombie；用 strace -p 看是否卡在 futex、read、poll、connect、fsync；用 pstack/gdb 看线程栈；用 lsof/ss 看 fd 和网络连接；用 dmesg 看 OOM、磁盘、驱动错误。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如何判断是 CPU 瓶颈、I/O 瓶颈还是网络瓶颈？</div>
<div class="qa-a"><p>CPU 瓶颈通常表现为 CPU util 高、run queue 长、perf 热点明显；I/O 瓶颈表现为 iowait、磁盘 await/util 高、read/write 慢、major fault 多；网络瓶颈表现为吞吐接近上限、丢包/重传、RTT 增大、socket buffer 堆积。</p></div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

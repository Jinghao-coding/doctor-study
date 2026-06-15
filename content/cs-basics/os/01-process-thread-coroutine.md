## 一句话结论

进程、线程、协程：资源边界和调度主体 是 操作系统基础 的核心知识点，面试回答要先给结论，再说明机制边界、工程场景和常见误区。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 操作系统基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕进程线程、调度、虚拟内存、IO、多路复用、死锁、观测和 AI Infra OS 问题建立系统基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心概念、系统链路或关键机制，把知识点映射到工程场景。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m">
<h3>进程、线程、协程：资源边界和调度主体</h3>
<p>操作系统面试里，进程、线程、协程不是三个孤立定义，而是三种不同层次的执行模型。核心问题是：谁拥有资源，谁被内核调度，谁在用户态切换。</p>
<table>
<tr><th>概念</th><th>资源边界</th><th>调度者</th><th>切换成本</th><th>适合场景</th><th>典型风险</th></tr>
<tr><td>进程</td><td>独立虚拟地址空间、文件描述符、信号处理、资源限制</td><td>内核</td><td>最高</td><td>强隔离、多服务、多 worker、容器主进程</td><td>IPC 成本高，共享状态复杂</td></tr>
<tr><td>线程</td><td>共享进程地址空间，独立栈和寄存器上下文</td><td>内核</td><td>中等</td><td>CPU 并行、I/O 并发、推理 worker pool</td><td>锁竞争、数据竞争、死锁、false sharing</td></tr>
<tr><td>协程</td><td>运行在线程内，共享进程/线程资源</td><td>用户态 runtime</td><td>最低</td><td>高并发 I/O、异步 RPC、事件循环</td><td>阻塞调用会卡住调度线程，不能自动利用多核</td></tr>
</table>
<div class="qa-summary">一句话：进程是资源隔离单位，线程是内核调度单位，协程是用户态调度的轻量执行单元。</div>
</div>

<div class="card card-s">
<h3>上下文切换到底切什么</h3>
<table>
<tr><th>切换类型</th><th>需要保存/恢复</th><th>代价来源</th><th>排查信号</th></tr>
<tr><td>进程切换</td><td>寄存器、内核栈、页表/地址空间、调度状态</td><td>TLB 失效、cache 污染、内核调度</td><td><code>pidstat -w</code>、<code>vmstat cs</code></td></tr>
<tr><td>线程切换</td><td>寄存器、线程栈、调度状态</td><td>内核调度、cache 污染、锁等待</td><td><code>top -H</code>、<code>perf sched</code></td></tr>
<tr><td>协程切换</td><td>用户态栈/状态机、少量寄存器</td><td>runtime 调度，通常无需内核态</td><td>runtime profiler、事件循环延迟</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 进程、线程、协程有什么区别？面试怎么回答？</div>
<div class="qa-a"><p><strong>回答思路：</strong>先按资源隔离、调度主体和切换成本三条线回答，再补适用场景。</p><div class="qa-section"><div class="qa-section-title">进程</div><p>进程拥有独立地址空间和资源边界，隔离性最好，适合服务拆分和容器主进程，但跨进程通信成本较高。</p></div><div class="qa-section"><div class="qa-section-title">线程</div><p>线程共享进程地址空间，是内核实际调度的执行实体，适合多核并行，但需要处理锁、数据竞争和死锁。</p></div><div class="qa-section"><div class="qa-section-title">协程</div><p>协程是用户态调度的轻量执行单元，适合 I/O 密集和高并发，但单个线程内的协程不能自动利用多核，阻塞调用会影响整个调度线程。</p></div><div class="qa-summary">面试口径：进程看隔离，线程看并行，协程看轻量异步；不要只背定义，要说出调度和资源边界。</div></div>
</div>

## 面试回答

**30 秒版：**

01 process thread coroutine 是 操作系统基础 中的一个基础知识点，面试回答要先给结论，再说明机制、边界和工程场景。 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。

**2 分钟版：**

我会先说明这个知识点在 操作系统基础 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

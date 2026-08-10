## AI Infra 面试模块：进程、线程与并发模型

AI Infra 面试里，进程、线程和协程不是概念背诵题，而是资源隔离、调度成本、数据加载吞吐和推理服务并发模型的基础。

<div class="card card-s">
<h3>核心概念定义</h3>
<table>
<thead><tr><th>概念</th><th>定义</th><th>面试重点</th></tr></thead>
<tbody>
<tr><td>进程</td><td>操作系统分配资源的基本单位，有独立虚拟地址空间、文件描述符表、信号处理和权限上下文。</td><td>隔离性强，崩溃影响小；创建和切换成本高于线程。</td></tr>
<tr><td>线程</td><td>进程内的执行流，共享进程地址空间和打开文件，拥有独立栈、寄存器上下文和调度状态。</td><td>通信方便、切换较轻；需要处理锁竞争、数据竞争和内存安全。</td></tr>
<tr><td>协程</td><td>用户态轻量执行流，由语言运行时或框架调度，通常用于大量 I/O 等待型并发。</td><td>切换不必进入内核；阻塞系统调用会阻塞承载线程，必须配合非阻塞 I/O。</td></tr>
<tr><td>IPC</td><td>进程间通信机制，包括 pipe、socket、shared memory、message queue、signal。</td><td>共享内存最快但同步复杂；socket 通用但有拷贝和协议开销。</td></tr>
<tr><td>同步原语</td><td>mutex、rwlock、semaphore、condition variable、barrier 等。</td><td>要能说明互斥、通知、资源计数、阶段同步分别适合什么场景。</td></tr>
</tbody>
</table>
</div>

### 需要掌握

- 进程与线程的区别：地址空间、资源隔离、崩溃影响范围、上下文切换成本。
- 用户态线程与内核态线程的区别：用户态切换快，内核态线程可被 OS 真正调度到多核。
- 多进程、多线程在 CPU 密集型和 I/O 密集型任务中的适用场景。
- 线程池为什么存在：避免频繁创建销毁线程，限制并发度，保护下游资源。
- 协程为什么适合网络服务：大量连接多数时间在等待 I/O，用少量线程承载大量逻辑执行流。
- 死锁产生条件：互斥、占有且等待、不可剥夺、循环等待。

<div class="card card-m">
<h3>上下文切换成本来自哪里</h3>
<p>上下文切换要保存和恢复寄存器、程序计数器、栈指针、调度状态。进程切换还可能切换地址空间和页表，破坏 TLB；线程切换虽然共享地址空间，但仍会破坏 cache locality。大量线程竞争锁或频繁阻塞唤醒，会导致 CPU 时间消耗在调度和内核态，而不是业务计算。</p>
</div>

### AI Infra 相关关注点

- DataLoader 多进程加载数据可以绕过 Python GIL，但会引入进程间队列、pickle/IPC、shared memory 和 copy-on-write 成本。
- Python GIL 会限制纯 Python CPU 密集型多线程并行，训练框架常用多进程、C++ 后端释放 GIL、CUDA 异步执行来绕过。
- 推理服务常用线程池处理 tokenizer、detokenizer、网络收发、日志和业务逻辑；线程过多会造成 context switch 和锁竞争。
- CPU 线程数、NUMA 绑核、DataLoader worker 数量会影响 GPU feeding，CPU 准备 batch 不连续会让 GPU 周期性空转。
- 多 worker 数据预处理要关注队列深度、worker 异常退出、共享内存大小和主进程是否及时消费。

### 高频问题

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 进程和线程有什么区别？什么时候用多进程，什么时候用多线程？</div>
<div class="qa-a"><p>进程是资源分配单位，线程是执行调度单位。进程有独立地址空间，隔离性强，适合强隔离、绕过 GIL、崩溃不互相影响的场景；线程共享地址空间，通信方便，适合 I/O 密集、共享状态多、延迟敏感的服务。AI Infra 中，Python 数据预处理常用多进程，推理服务前后处理和网络收发常用线程池或协程。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: mutex 和 semaphore 的区别是什么？</div>
<div class="qa-a"><p>mutex 是互斥锁，用来保护临界区，一般强调谁加锁谁解锁；semaphore 是计数信号量，用来表示可用资源数量，可以允许多个执行流同时进入。连接池容量、GPU slot、队列容量更像 semaphore；共享 map、调度器状态更新更适合 mutex/rwlock。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Python 多线程为什么不能很好利用多核 CPU？</div>
<div class="qa-a"><p>CPython 有 GIL，同一时刻通常只有一个线程执行 Python bytecode，所以纯 Python CPU 密集型多线程不能真正并行利用多核。但 I/O 阻塞、C++ 扩展、CUDA kernel launch 等可能释放 GIL，因此训练框架常通过 C++/CUDA 后端、多进程 DataLoader 和异步 pipeline 提升吞吐。</p></div>
</div>

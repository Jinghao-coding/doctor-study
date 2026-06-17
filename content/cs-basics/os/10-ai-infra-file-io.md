## 一句话结论

一次 read 的路径是：进入内核查 fd 和 page cache，命中就拷给用户 buffer，未命中就发起磁盘或网络存储 I/O 读入 cache 再拷贝。AI Infra 里这条路径决定训练数据加载、checkpoint 和权重加载吞吐，排障要拆到系统调用、page cache miss、磁盘/网络存储延迟、小文件 metadata 和解码这几层。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 操作系统基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕进程线程、调度、虚拟内存、IO、多路复用、死锁、观测和 AI Infra OS 问题建立系统基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## AI Infra 面试模块：文件系统与 I/O

文件系统与 I/O 直接影响训练数据加载、checkpoint 保存、模型权重加载和推理服务吞吐。面试中要能从文件抽象讲到内核路径，再落到性能瓶颈定位。

### 需要掌握

- inode、目录项、文件描述符：inode 保存文件元数据和数据块位置，目录项把文件名映射到 inode，fd 是进程打开文件后的句柄。
- buffered I/O：`read/write` 经过 page cache，适合复用和小块读取。
- direct I/O：绕过 page cache，适合应用自管缓存的大文件顺序读写，但要求 buffer、offset、size 对齐。
- sync/async I/O：同步 I/O 调用方等待完成，异步 I/O 提交请求后由完成事件通知。
- `read/write`、`pread/pwrite`、`mmap`：`pread/pwrite` 带 offset 且不改变文件偏移，适合多线程并发读写。
- dirty page 与 `fsync`：写入先进入 page cache 形成脏页，`fsync` 强制落盘，可能很慢。
- 顺序读写与随机读写：顺序访问利用预读和连续带宽，随机访问受寻址、队列深度和 metadata 影响。
- SSD/NVMe：延迟低、并发队列强，但小 I/O、同步刷盘、文件碎片仍可能成为瓶颈。
- I/O 多路复用：select、poll、epoll 让少量线程管理大量 fd。
- 零拷贝：sendfile、splice、DMA、mmap 等减少用户态/内核态拷贝和上下文切换。

<div class="card card-s">
<h3>一次 read 的典型路径</h3>
<p>应用调用 read 进入内核；内核检查 fd、文件偏移和 page cache；如果命中，把 page cache 内容拷贝到用户 buffer；如果未命中，提交磁盘或网络存储 I/O，把数据读入 page cache，再拷贝给用户。这个路径可能慢在系统调用、page cache miss、磁盘 I/O、metadata、CPU copy、网络存储或文件格式解码。</p>
</div>

### AI Infra 相关关注点

- 训练数据读取瓶颈要拆成：磁盘/对象存储带宽、网络存储延迟、文件数量和 metadata、解码、数据增强、CPU worker、batch queue 深度。
- 小文件过多会导致 `open/stat/readdir` metadata 开销高，即使总数据量不大也会拖慢 DataLoader。
- checkpoint 保存慢可能来自序列化、CPU 到磁盘写入、网络文件系统、`fsync`、单文件过大、并发写冲突。
- 模型权重加载时，`mmap`、顺序读、预读、page cache 预热、并行 shard 加载都会影响启动时间。
- 推理服务要把网络 I/O、请求解析、排队、batching、GPU 执行和响应写回解耦。
- 高吞吐服务常用 epoll/事件循环/异步 I/O/零拷贝降低线程数和拷贝成本。

<div class="card card-d">
<h3>训练时 GPU 利用率低，I/O 层怎么排查</h3>
<ol>
<li>看 GPU 利用率是否周期性掉到 0，如果是，常见原因是 batch feeding 不连续。</li>
<li>看 DataLoader worker CPU 是否打满，队列是否为空，是否被图像解码或数据增强拖慢。</li>
<li>用 iostat 看磁盘 util、await、吞吐；用网络监控看远端存储带宽和延迟。</li>
<li>看文件数量和单文件大小，小文件多时优先考虑打包格式或顺序读。</li>
<li>看 page cache 命中和 major fault，判断是否频繁从磁盘或网络存储重新取数据。</li>
</ol>
</div>

### 高频问题

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 文件描述符和 inode 的关系是什么？</div>
<div class="qa-a"><p>inode 是文件系统中的文件元数据对象，文件名通过目录项映射到 inode。进程 open 文件后得到 fd，fd 指向内核 open file description，其中包含文件偏移和打开模式。多个 fd 可以指向同一个 inode，也可以共享或不共享文件偏移。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: epoll 相比 select/poll 的优势是什么？</div>
<div class="qa-a"><p>select/poll 每次都要传入 fd 集合并线性扫描，epoll 把关注的 fd 注册到内核对象里，就绪事件通过 ready list 返回，避免每次全量扫描，更适合大量连接但少量活跃的高并发服务。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: fsync 为什么可能很慢？</div>
<div class="qa-a"><p>write 返回通常只表示数据进入 page cache，不代表落盘。fsync 要等待脏页写回、文件系统 journal、设备 flush、网络存储确认和其他 I/O 排队。checkpoint 或日志频繁 fsync 会显著影响吞吐和延迟。</p></div>
</div>

## 面试回答

**30 秒版：**

文件系统里 inode 存元数据和数据块位置、目录项把文件名映射到 inode、fd 是打开后的句柄。一次 read 进内核查 fd 和 page cache，命中拷给用户 buffer，未命中发起 I/O。buffered I/O 走 page cache、Direct I/O 绕过但要对齐，write 返回只到 page cache、fsync 才落盘。AI Infra 排训练 I/O 瓶颈要拆磁盘带宽、网络存储延迟、小文件 metadata、解码和 worker 队列深度。

**2 分钟版：**

文件 I/O 先讲抽象再讲路径：inode 保存文件元数据和数据块位置，目录项把文件名映射到 inode，进程 open 后拿到 fd 指向内核的 open file description（含偏移和打开模式）。一次 read 进内核检查 fd、偏移和 page cache，命中就把 cache 内容拷到用户 buffer，未命中就发起磁盘或网络存储 I/O，读进 page cache 再拷给用户，所以慢点可能在系统调用、cache miss、磁盘 I/O、metadata、CPU copy 或文件解码。机制上要分清 buffered I/O 走 page cache 适合复用小读、Direct I/O 绕过 cache 适合应用自管的大文件顺序读但要对齐，write 返回只代表进 page cache 形成脏页、fsync 才强制落盘且可能很慢。落到 AI Infra，训练数据读取瓶颈要拆成磁盘/对象存储带宽、网络存储延迟、文件数量和 metadata、解码、CPU worker 和 batch 队列深度——小文件过多会让 open/stat/readdir 拖慢 DataLoader，checkpoint 慢常来自序列化和 fsync，权重加载靠 mmap、顺序读、预读和并行 shard 优化。具体排查时先看 GPU 利用率是否周期性掉零（batch feeding 不连续），再看 worker CPU 和队列、iostat 的 util/await、文件数量和 page cache 命中。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

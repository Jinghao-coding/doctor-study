## 一句话结论

CUDA stream 是 GPU 侧的异步任务队列，同一个 stream 内顺序执行，不同 stream 在资源允许时可以并行。优化目标是用 pinned memory、`cudaMemcpyAsync`、event 和多缓冲，把 CPU 准备、H2D/D2H 拷贝和 kernel 计算流水线化。

## 核心概念

本节关注“如何用 stream/event 把拷贝、kernel 和 CPU 准备组织成异步流水线”。H2D/D2H 的触发场景和 DataLoader 诊断见 `Host-Device 数据拷贝`。

GPU 有自己的显存（HBM），CPU 也有自己的内存（DDR）。数据在两者之间搬运，就是 H2D（Host to Device）和 D2H（Device to Host）拷贝。

因为 H2D/D2H 走的是 PCIe 或 NVLink，带宽远低于 GPU 内部 HBM 带宽。一次不注意的同步拷贝可能让 GPU 空等数百微秒，这在推理低延迟场景下尤其致命。

<table>
<tr><th>路径</th><th>典型带宽</th><th>延迟</th><th>常见场景</th></tr>
<tr><td>CPU → GPU（PCIe 4.0 x16）</td><td>~25 GB/s（双向 ~50 GB/s）</td><td>~10 μs 起步</td><td>输入数据、模型加载</td></tr>
<tr><td>GPU → CPU（PCIe 4.0 x16）</td><td>~25 GB/s</td><td>~10 μs 起步</td><td>读取推理结果、日志</td></tr>
<tr><td>GPU → GPU（NVLink 3.0）</td><td>~300 GB/s</td><td>~5 μs</td><td>张量并行、NCCL 通信</td></tr>
<tr><td>GPU → GPU（PCIe）</td><td>~25 GB/s</td><td>~10 μs</td><td>无 NVLink 的卡间通信</td></tr>
</table>

## 系统链路

**同步拷贝**（`cudaMemcpy`）：CPU 发起后阻塞等待完成，GPU 和 CPU 都在等。适合初始化、模型加载等不在乎延迟的场景。

**异步拷贝**（`cudaMemcpyAsync`）：CPU 发起后立即返回，拷贝在 GPU 端异步执行。必须配合 CUDA stream 使用，才能实现计算和拷贝重叠。

<pre><code class="language-cpp">// 同步：CPU 阻塞等待
cudaMemcpy(d_ptr, h_ptr, size, cudaMemcpyHostToDevice);

// 异步：CPU 立即返回，拷贝在 stream 上执行
cudaMemcpyAsync(d_ptr, h_ptr, size, cudaMemcpyHostToDevice, stream);</code></pre>

## 关键机制

<table>
<tr><th>策略</th><th>原理</th><th>效果</th></tr>
<tr><td>Pinned Memory（页锁定内存）</td><td>用 <code>cudaMallocHost</code> 分配 CPU 端不可换页内存，DMA 直接传输</td><td>异步拷贝带宽可提升 2-3×</td></tr>
<tr><td>计算与拷贝重叠</td><td>用多个 CUDA stream，一个算当前 batch，另一个拷下一个 batch</td><td>隐藏拷贝延迟</td></tr>
<tr><td>减少不必要的 D2H</td><td>尽量让数据留在 GPU，减少中间结果回传 CPU</td><td>减少拷贝次数和延迟</td></tr>
<tr><td>批量传输</td><td>多次小拷贝合并为一次大拷贝</td><td>减少启动开销</td></tr>
<tr><td>Unified Memory</td><td><code>cudaMallocManaged</code> 让 CPU/GPU 共享地址空间，按需迁移</td><td>编程简单，但性能不如手动管理</td></tr>
</table>

**Pinned Memory 为什么更快：**

普通 `malloc` 分配的内存是可换页的，GPU DMA 无法直接访问，需要先拷贝到临时 pinned buffer 再传输，多了一次隐式拷贝。`cudaMallocHost` 分配的内存被锁定在物理页上，GPU DMA 可以直接传输，省掉中间环节。但 pinned memory 不可换页，会占用实际物理内存，不能无限分配。

CUDA stream 是 GPU 上的任务队列。同一个 stream 内的操作**按提交顺序串行执行**；不同 stream 之间的操作**可以并行执行**（如果硬件资源允许）。

<pre><code class="language-cpp">cudaStream_t stream1, stream2;
cudaStreamCreate(&stream1);
cudaStreamCreate(&stream2);

// stream1：拷贝输入 + 计算
cudaMemcpyAsync(d_in1, h_in1, size, cudaMemcpyHostToDevice, stream1);
kernel_a&lt;&lt;&lt;grid, block, 0, stream1&gt;&gt;&gt;(d_in1, d_out1);

// stream2：同时拷贝另一组输入 + 计算
cudaMemcpyAsync(d_in2, h_in2, size, cudaMemcpyHostToDevice, stream2);
kernel_b&lt;&lt;&lt;grid, block, 0, stream2&gt;&gt;&gt;(d_in2, d_out2);

// 等待两个 stream 都完成
cudaStreamSynchronize(stream1);
cudaStreamSynchronize(stream2);</code></pre>

## 资源模型

推理或训练中，经典优化是让数据拷贝和计算重叠。三缓冲（triple buffering）是最常见的模式：

<pre><code>Buffer A: GPU 正在计算（kernel 执行中）
Buffer B: H2D 正在拷贝下一批数据（DMA 传输中）
Buffer C: CPU 正在准备再下一批数据

下一个时间步：
  A 计算完成 → D2H 取结果
  B 拷贝完成 → 开始计算
  C 准备完成 → 开始 H2D 拷贝</code></pre>

这样 GPU 不用等 CPU 准备数据，CPU 也不用等 GPU 算完，三者流水线化。

实现要点：

- 每个缓冲区用独立的 CUDA stream。
- 输入数据用 pinned memory 分配。
- 用 `cudaMemcpyAsync` 而不是 `cudaMemcpy`。
- 用 `cudaStreamSynchronize` 或 event 等待完成。
- 缓冲区数量通常 2 或 3，多了收益递减。

## 常见误区

| 误区 | 正确理解 |
|---|---|
| 用了多个 stream 就一定并行 | 并行取决于硬件资源、依赖关系、默认 stream 语义和 kernel 是否占满 SM。 |
| `cudaMemcpyAsync` 一定异步 | H2D 异步拷贝通常需要 pinned memory；pageable memory 可能触发隐式同步或 staging copy。 |
| 默认 stream 可以直接用于重叠 | 默认 stream 可能和其他 stream 隐式同步，做流水线应使用自定义 stream 和 event。 |
| stream 越多越好 | stream 过多会增加调度复杂度，资源冲突时收益有限。 |

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 默认 stream（stream 0）和自定义 stream 有什么区别？</div>
<div class="qa-a"><p>默认 stream（NULL / 0）是同步流——它会和所有其他 stream 隐式同步。如果你把操作提交到默认 stream，它会等所有其他 stream 完成；其他 stream 也会等它完成。自定义 stream 之间没有这种隐式同步，所以可以实现真正的并行。要做计算拷贝重叠，必须用自定义 stream。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 两个 stream 一定能并行吗？</div>
<div class="qa-a"><p>不一定。并行取决于硬件资源是否足够。如果两个 stream 的 kernel 都需要全部 SM，它们会被串行执行；如果一个在拷贝（使用 DMA engine / copy engine），一个在计算（使用 SM），它们可以并行，因为用的是不同硬件单元。这也是为什么计算+拷贝重叠比计算+计算重叠更容易实现——DMA engine 和 SM 是独立的硬件资源。</p></div>
</div>

## 关联模块

- `Host-Device 数据拷贝`：定位 H2D/D2H 触发点和 DataLoader 问题。
- `CUDA 执行模型`：理解 stream、kernel、block/warp 的层级差异。
- `利用率诊断`：在 Nsight Systems timeline 中识别 memcpy、空洞和同步。

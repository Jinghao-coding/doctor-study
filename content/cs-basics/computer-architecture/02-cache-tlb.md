## 一句话结论

Cache 和 TLB 都是用「空间换时间」缓解访存慢的硬件：Cache 缓存数据、TLB 缓存地址翻译，两者命中率都依赖程序的访问局部性，所以高性能代码的本质是写出对 cache 和 TLB 友好的内存访问模式。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 计算机组成基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕 CPU、缓存、TLB、DMA、PCIe、NUMA 等 AI Infra 底层系统知识建立基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>Cache、TLB 和局部性</h3><p>Cache 利用时间局部性和空间局部性减少内存访问；TLB 缓存虚拟地址到物理地址的页表翻译结果。Cache miss 和 TLB miss 都会显著拖慢程序。</p></div>
<div class="card card-s"><h3>False Sharing</h3><p>多个线程修改不同变量，但这些变量落在同一 cache line 上，会导致 cache coherence 协议反复让 cache line 在 core 之间迁移。现象是 CPU 利用率高但吞吐低。</p><div class="qa-summary">解决：padding、alignas、按线程分片计数、减少共享写。</div></div>
<div class="card card-d"><h3>面试排查入口</h3><table><tr><th>问题</th><th>现象</th><th>工具</th></tr><tr><td>Cache miss 高</td><td>CPU 等内存</td><td><code>perf stat</code>、PMU</td></tr><tr><td>TLB miss 高</td><td>随机访问大内存慢</td><td><code>perf stat</code>、hugepage</td></tr><tr><td>False sharing</td><td>多线程扩展性差</td><td><code>perf c2c</code>、benchmark 对比</td></tr></table></div>

## 面试回答

**30 秒版：**

Cache 缓存数据、TLB 缓存虚拟地址到物理地址的翻译，命中靠局部性。Cache miss 让 CPU 等内存，TLB miss 触发 page walk，false sharing 则让同一 cache line 在核间反复迁移——这三类都表现为「CPU 忙但吞吐低」，要用 perf 区分。

**2 分钟版：**

我会先讲两层缓存：Cache 利用时间和空间局部性减少访存，TLB 缓存页表翻译减少 page walk。然后讲三类典型问题和定位手段：cache miss 高说明数据局部性差，用 perf stat 看 miss rate；TLB miss 高常见于随机访问大内存，可以用 hugepage 减少页表项；false sharing 是多线程改写落在同一 cache line 的不同变量，导致 coherence 协议反复让 cache line 迁移，用 perf c2c 定位，靠 padding 或 alignas 隔离。最后收束到 AI Infra：高并发数据处理、计数器、无锁结构里 false sharing 很常见，按线程分片、按 cache line 对齐是常规优化。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

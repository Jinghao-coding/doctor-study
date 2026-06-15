## 一句话结论

Cache、TLB 和局部性 是 计算机组成基础 的核心知识点，面试回答要先给结论，再说明机制边界、工程场景和常见误区。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 计算机组成基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕 CPU、缓存、TLB、DMA、PCIe、NUMA 等 AI Infra 底层系统知识建立基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心概念、系统链路或关键机制，把知识点映射到工程场景。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m"><h3>Cache、TLB 和局部性</h3><p>Cache 利用时间局部性和空间局部性减少内存访问；TLB 缓存虚拟地址到物理地址的页表翻译结果。Cache miss 和 TLB miss 都会显著拖慢程序。</p></div>
<div class="card card-s"><h3>False Sharing</h3><p>多个线程修改不同变量，但这些变量落在同一 cache line 上，会导致 cache coherence 协议反复让 cache line 在 core 之间迁移。现象是 CPU 利用率高但吞吐低。</p><div class="qa-summary">解决：padding、alignas、按线程分片计数、减少共享写。</div></div>
<div class="card card-d"><h3>面试排查入口</h3><table><tr><th>问题</th><th>现象</th><th>工具</th></tr><tr><td>Cache miss 高</td><td>CPU 等内存</td><td><code>perf stat</code>、PMU</td></tr><tr><td>TLB miss 高</td><td>随机访问大内存慢</td><td><code>perf stat</code>、hugepage</td></tr><tr><td>False sharing</td><td>多线程扩展性差</td><td><code>perf c2c</code>、benchmark 对比</td></tr></table></div>

## 面试回答

**30 秒版：**

02 cache tlb 是 计算机组成基础 中的一个基础知识点，面试回答要先给结论，再说明机制、边界和工程场景。 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。

**2 分钟版：**

我会先说明这个知识点在 计算机组成基础 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

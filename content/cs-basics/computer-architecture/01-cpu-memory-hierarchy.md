## 一句话结论

CPU 性能不只看核数，更取决于数据离 CPU 有多近：寄存器、L1/L2/L3、本地 DRAM、远端 NUMA 内存的延迟逐级放大，越往下带宽越低，所以很多“CPU 跑满但吞吐上不去”的问题本质是访存而非算力。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 计算机组成基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕 CPU、缓存、TLB、DMA、PCIe、NUMA 等 AI Infra 底层系统知识建立基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>CPU 与内存层次</h3><p>程序性能不仅取决于 CPU core 数，还取决于数据是否在寄存器、L1/L2/L3 cache、内存还是远端 NUMA 内存中。越靠近 CPU，容量越小、延迟越低、带宽越高。</p></div>
<div class="card card-d"><h3>层次结构</h3><table><tr><th>层次</th><th>特点</th><th>性能影响</th></tr><tr><td>寄存器</td><td>CPU 内部，最快</td><td>编译器优化和指令级并行</td></tr><tr><td>L1/L2 Cache</td><td>每 core 或小范围共享</td><td>热数据命中时极快</td></tr><tr><td>L3 Cache</td><td>多 core 共享</td><td>跨线程共享数据常经过 L3</td></tr><tr><td>DRAM</td><td>容量大但延迟高</td><td>内存带宽瓶颈常见</td></tr><tr><td>远端 NUMA 内存</td><td>跨 socket 访问</td><td>延迟更高，带宽更低</td></tr></table></div>
<div class="qa" onclick="this.classList.toggle('open')"><div class="qa-q">Q: 为什么线程数增加后吞吐可能下降？</div><div class="qa-a"><p>线程数增加会带来上下文切换、锁竞争、cache line 抖动、内存带宽竞争和 NUMA 远端访问。CPU core 变忙不代表有效吞吐提升。</p></div></div>

## 面试回答

**30 秒版：**

现代 CPU 的瓶颈往往不是算力而是访存。寄存器、L1/L2/L3、本地 DRAM、远端 NUMA 内存的延迟逐级放大、带宽逐级下降，所以优化的核心是让热数据尽量靠近 CPU、保持访问局部性，而不是单纯堆核数。

**2 分钟版：**

我会先讲层次：寄存器最快但极小，L1/L2 每核私有、L3 多核共享，再往下是本地 DRAM 和跨 socket 的远端 NUMA 内存，延迟从纳秒到上百纳秒逐级放大，带宽逐级下降。接着讲为什么重要：程序如果频繁 cache miss 或跨 NUMA 访存，CPU 会大量时间在等内存，表现为「CPU 跑满但吞吐上不去」。然后讲工程手段：提升空间/时间局部性、按 cache line 对齐避免 false sharing、用 numactl 做内存和 CPU 绑核、大页减少 TLB miss。最后收束到 AI Infra：数据加载线程要靠近目标 GPU 所在的 NUMA 节点，否则 host-to-device 拷贝会跨 socket，拖慢整个训练 pipeline。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

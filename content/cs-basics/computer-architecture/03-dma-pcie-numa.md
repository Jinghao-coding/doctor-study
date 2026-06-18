## 一句话结论

DMA、PCIe 和 NUMA 共同决定了数据在 CPU、GPU、NIC、NVMe 之间「怎么走、走多快」：DMA 让设备绕过 CPU 搬数据，PCIe 是设备互联的带宽上限，NUMA 决定设备和内存的亲和距离——AI Infra 里大量性能问题不是 GPU 不够快，而是数据到 GPU 的路径太差。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 计算机组成基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕 CPU、缓存、TLB、DMA、PCIe、NUMA 等 AI Infra 底层系统知识建立基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>DMA、PCIe 与 NUMA 拓扑</h3><p>DMA 允许设备绕过 CPU 直接读写内存；PCIe 是 CPU、GPU、NIC、NVMe 等设备的主要互联；NUMA 决定 CPU、内存、GPU、NIC 之间的亲和关系。</p></div>
<div class="card card-d"><h3>AI Infra 为什么关心这些</h3><table><tr><th>概念</th><th>影响</th><th>典型场景</th></tr><tr><td>DMA</td><td>降低 CPU copy 开销</td><td>GPU copy、RDMA、NVMe 数据加载</td></tr><tr><td>PCIe</td><td>限制 host-device 带宽</td><td>CPU 到 GPU 数据搬运</td></tr><tr><td>NUMA locality</td><td>影响 CPU-GPU/NIC 距离</td><td>数据加载线程应靠近目标 GPU/NIC</td></tr><tr><td>GPU-NIC affinity</td><td>影响 RDMA/NCCL 性能</td><td>跨节点 AllReduce</td></tr></table></div>
<div class="card card-s">
<h3>设备路径怎么读</h3>
<p>在一台多 Socket 服务器里，GPU、NIC、NVMe 通常挂在不同 PCIe switch 或 root complex 下。路径越短、越少跨 Socket，延迟越低、带宽越稳定。AI Infra 里常见的性能问题不是“GPU 不够快”，而是数据从 CPU、NIC 或另一张 GPU 到目标 GPU 的路径太差。</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">同 PCIe switch</div><div class="flow-desc">GPU-GPU P2P 或 GPU-NIC 路径较短</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">同 Socket / 同 NUMA</div><div class="flow-desc">CPU 线程、内存页、GPU、NIC 亲和性较好</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">跨 Socket</div><div class="flow-desc">经过 CPU interconnect，延迟和抖动上升</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">Host staging</div><div class="flow-desc">P2P/GDR 不可用时经 CPU pinned memory 中转，代价最高</div></div>
</div>
</div>
<div class="qa" onclick="this.classList.toggle('open')"><div class="qa-q">Q: 为什么 GPU 训练要看 <code>nvidia-smi topo -m</code>？</div><div class="qa-a"><p>它能显示 GPU-GPU、GPU-NIC、GPU-CPU 的拓扑关系。张量并行、NCCL、RDMA 和数据加载都受拓扑影响；同样 8 张 GPU，NVLink 内互联和跨 PCIe/跨节点性能差异很大。</p></div></div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

## GPU 在 AI Infra 中的定位

GPU 是 AI Infra 的**算力底座**。训练和推理的所有计算最终都跑在 GPU 的 SM、Tensor Core 和 HBM 上，上层的并行策略、调度、推理引擎都是在"如何把 GPU 喂饱、用满、共享好"这件事上做文章。

面试考 GPU，本质是确认：你是否理解算力、显存、互联三类资源的真实约束，以及如何把"训练慢 / 利用率低 / 显存不够"翻译成具体的硬件瓶颈。

<div class="card card-d">
<h3>一句话定位</h3>
<p>GPU 决定了 AI 系统的算力上限；理解 <strong>SM/Tensor Core 算力、HBM 带宽与容量、NVLink/PCIe 互联</strong> 这三类资源，才能解释清楚训练吞吐和推理延迟的真实瓶颈。</p>
</div>

## 与其他模块的关系

| 关联模块 | 关系 | 本模块提供的基础 |
|---|---|---|
| 分布式训练 | 多卡训练建立在 GPU 互联之上 | NVLink/PCIe、GPUDirect、拓扑亲和 |
| LLM 推理系统 | KV cache、吞吐受显存与带宽约束 | HBM 容量/带宽、利用率诊断 |
| 任务调度 / 集群管理 | 共享与放置依赖 GPU 资源模型 | MIG、MPS、time-slicing、CUDA VMM |
| 操作系统 / 组成原理 | GPU 之下是主机与总线 | DMA、pinned memory、NUMA、PCIe |
| 性能预测 | 利用率特征是预测输入 | SM Active、Occupancy、MFU、DCGM |

## 本模块包含哪些内容

| 板块 | 覆盖内容 | 典型面试问题 |
|---|---|---|
| 硬件与互联基础 | CPU vs GPU、A100/H100/H200、HBM、NVLink/PCIe、RDMA | 为什么 GPU 适合深度学习？NVLink 和 PCIe 差别？ |
| 执行模型与调度 | CUDA grid/block/thread/warp/SM、Stream、H2D 拷贝 | warp 是什么？pinned memory 为什么快？ |
| 共享与隔离 | MIG、MPS、时间片、CUDA VMM、K8s GPU 共享 | MIG 和 MPS 区别？怎么在 K8s 里共享 GPU？ |
| 性能与诊断 | TFLOPS、Roofline、利用率、瓶颈分类、性能预测 | GPU 利用率低怎么定位？怎么判断计算/显存/通信瓶颈？ |

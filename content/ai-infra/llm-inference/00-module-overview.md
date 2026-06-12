## LLM 推理系统在 AI Infra 中的定位

LLM 推理系统是把训练好的模型**对外提供服务**的那一层。它要在有限的 GPU 显存和算力下，同时满足低延迟（TTFT/TPOT）和高吞吐（QPS/tokens），是 AI Infra 里直接面向线上 SLO 的模块。

面试考推理系统，本质是确认：你是否理解 prefill 与 decode 两个阶段截然不同的资源特征，以及 KV cache 为什么是显存和吞吐的核心矛盾。

<div class="card card-d">
<h3>一句话定位</h3>
<p>推理系统的全部优化都围绕一件事：<strong>在显存放得下 KV cache 的前提下，尽量提高 batch 和吞吐，同时压住 p99 延迟</strong>。理解 prefill（计算密集）和 decode（访存密集）的差异是一切的起点。</p>
</div>

## 与其他模块的关系

| 关联模块 | 关系 | 关键连接点 |
|---|---|---|
| GPU 硬件 | 推理吞吐受显存与带宽约束 | HBM 容量装 KV cache、带宽决定 decode 速度 |
| 任务调度 / 集群管理 | 多模型多副本的部署与共享 | 模型驻留、请求路由、GPU 共享 |
| 系统设计题 | 推理系统是高频设计题 | 多模型推理、KV 缓存管理系统 |
| 操作系统 | 延迟抖动落到系统层 | page cache、p99 排查、显存 OOM |
| 性能预测 | 输出长度/延迟预测辅助调度 | 序列长度、batch、KV 占用建模 |

## 本模块包含哪些内容

| 板块 | 覆盖内容 | 典型面试问题 |
|---|---|---|
| 总览与流程 | 端到端链路、prefill/decode 区别、请求生命周期 | 一个 prompt 进来到吐出 token 经历了什么？ |
| Prefill 与 Decode | TTFT、首 token、TPOT、memory-bound | 为什么 decode 是访存密集？ |
| KV Cache 与 Attention | KV 缓存、PagedAttention、FlashAttention、GQA | KV cache 占多少显存？PagedAttention 解决什么？ |
| 性能与优化 | 吞吐/延迟指标、MFU、Batching、量化、投机解码 | 怎么提升推理吞吐？投机解码为什么能加速？ |
| 引擎与面试 | vLLM/TGI/TensorRT-LLM 对比、学习路线、面试清单 | vLLM 为什么快？怎么选推理引擎？ |

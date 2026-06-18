## 一句话结论

当前站点已经覆盖 AI Infra 面试的主干：模型基础、GPU/CUDA、LLM 推理、分布式训练、Kubernetes、调度、集群管理、性能建模、系统设计和计算机基础。主要遗漏不是单个算法，而是**生产化闭环**：数据和模型资产如何进入平台、服务如何观测和守 SLO、容量成本如何规划、发布安全和事故复盘如何闭环。

## 覆盖现状

| 方向 | 当前覆盖 | 面试风险 |
|---|---|---|
| 模型与算子 | Transformer、FLOPs、Roofline、Attention、Decode memory-bound | 基础充分，后续可补 MoE/多模态细节 |
| GPU 与 CUDA | 硬件、互联、MIG/MPS、VMM、Stream、Occupancy、诊断 | 主线充分，适合回答性能排查题 |
| LLM 推理 | Prefill/Decode、KV cache、PagedAttention、FlashAttention、vLLM、调度优化 | 主线充分，后续可补 TensorRT-LLM / Triton 部署对比 |
| 分布式训练 | DP/TP/PP、ZeRO/FSDP、NCCL、训练排障 | 主线充分，后续可补 MoE/EP 和训练数据管道 |
| K8s / 调度 / 集群 | Scheduler、Operator、DRA、Volcano/Kueue/YuniKorn、多租户、容错 | 主线充分，适合平台岗 |
| CS 基础 | OS、网络、Linux/容器、NUMA、I/O、C++、分布式基础 | 覆盖广，后续可按面试频率继续收束 |
| 生产化闭环 | 分散出现在 K8s、集群、系统设计、CS 基础里 | 缺少统一页面，容易在综合设计题里答散 |

## 明显缺口

| 缺口 | 为什么重要 | 建议优先级 |
|---|---|---|
| 数据与模型制品链路 | 面试会追问数据集、checkpoint、模型注册、镜像、版本、血缘和回滚，不只是训练/推理运行时 | P0 |
| 可观测性与 SLO | AI Infra 平台岗常问如何发现、定位和治理慢请求、训练 hang、GPU 利用率低、调度延迟和容量风险 | P0 |
| 容量规划与成本 | 生产平台不仅要跑通，还要解释 quota、峰值、碎片、能耗、tokens/J、GPU 型号选型和扩容依据 | P0 |
| 发布与安全治理 | 推理服务、训练平台、Operator 和调度器都涉及灰度、回滚、权限、Secret、镜像供应链和事故复盘 | P1 |
| Serving runtime 对比 | vLLM 已覆盖较多，Triton Inference Server、TensorRT-LLM、ONNX Runtime、Ray Serve 可补成部署选型页 | P1 |
| 数据工程与训练管道 | 数据校验、shuffle、缓存、冷热分层、样本去重、在线特征/离线数据一致性可作为训练平台补充 | P1 |
| MLOps / LLMOps 流程 | 评测、模型准入、A/B、提示词版本、Agent 工具权限和离线回放可作为 Agent 与系统设计补充 | P2 |

## 补齐策略

```flow
先补横向闭环 | 数据、模型、观测、容量、安全贯穿所有主题
再补部署选型 | vLLM / Triton / TensorRT-LLM / Ray Serve 做对比
最后补专题深挖 | MoE、数据管道、LLMOps、评测准入按岗位需要扩展
```

## 关联模块

- `LLM 推理系统`：补齐 serving engine 之外的部署、SLO 和发布治理。
- `分布式训练`：补齐数据、checkpoint、模型制品和训练平台生命周期。
- `Kubernetes 核心`：补齐 Operator、RBAC、Secret、Admission、发布和事故治理。
- `GPU 集群管理`：补齐容量规划、成本、配额、碎片和可观测性闭环。

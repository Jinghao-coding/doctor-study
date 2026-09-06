## 从 Agent 请求到输出长度

Maestro 把 Agent 请求的执行成本提前转成调度信号：先预测这次调用是否涉及工具，再预测会生成多少 token，最后将长度换算成时间和显存需求。工具调用通常生成较短的结构化参数，分析与总结通常生成较长文本；同样的输入长度，执行成本可能相差很大。

`python-predictor` 将预测封装成 FastAPI 服务。一次请求携带会话 ID、Agent 名称、消息、可用工具和阶段上下文；响应返回工具调用概率、预测输出长度和输入 token 数。

```text
messages + tools ──→ 输入 token 计数
        │
        └─────────→ MiniLM → 384 维语义向量
                                  │
                     ┌────────────┴────────────┐
                     ↓                         ↓
                 全局 PCA                  Agent 专属 PCA
                  32 维                       32 维
                     │                         │
结构化特征 ──────→ 全局 LightGBM 分类器         │
                     │                         │
                  工具调用概率 ──────→ Agent 专属 LightGBM 回归器
                                               ↑
                                          结构化特征
                                               │
                                       log(1 + 输出长度)
                                               ↓
                                      expm1 → 预测 token 数
```

两阶段之间传递连续概率，不先用阈值把请求硬分成两类。Agent 的差异主要通过选择专属回归器和专属 PCA 来表达。

## 输入特征怎样获得

<div class="table-scroll">

| 信息 | 实现字段或来源 | 提供的判断依据 |
|---|---|---|
| 输入长度 | `node_input_tokens`；对消息与工具应用配置的 tokenizer 和 chat template | 当前上下文规模 |
| 工具数量 | `len(request.tools)` | 可用工具的多少；不等于实际会调用工具 |
| 思考模式 | `is_thinking_mode` | 当前请求是否开启思考模式 |
| 阶段位置 | `node_index_in_graph`、`is_first_node` | 当前处于会话中的哪个阶段 |
| 同一 Agent 的调用次数 | `model_index_in_agent`；接口根据 Redis 中已回传的节点计数 | 首次执行还是再次调用 |
| 上一阶段输出长度 | `prev_node_output_length`；优先使用请求值，缺失时查 Redis | 上游刚刚产生的信息规模 |
| 输入语义 | System prompt、user/assistant 对话、工具名称和描述 | 请求到底要做什么 |

</div>

`agent_name` 用于查找模型包，`session_id` 用于关联会话上下文。当前特征选择配置纳入基础字段、阶段上下文字段、PCA 特征，并为回归器追加 `classifier_probability`；图的入度、出度、深度和角色 one-hot 不是这份配置中的显式输入。

代码也保留了历史均值、输出／输入比率等统计特征的生成与读取能力。最终哪些字段进入模型，由训练生成的 `feature_names` 决定；当前配置没有选择这些历史统计列。

## 文本编码与两套 PCA

语义编码使用 `all-MiniLM-L6-v2`，通过 ONNX Runtime 执行。默认长文本策略将内容切成最多 510 个 token 的窗口，步长为 255；窗口加上特殊 token 后按 512 长度组织，批量编码。每个窗口做带 mask 的 mean pooling 和归一化，再聚合窗口向量，得到 384 维表示。

全局分类器和各 Agent 回归器分别保存自己的 PCA 参数。两者复用同一个原始语义向量，但投影方向不同：全局 PCA 面向多种 Agent 的工具调用模式，Agent PCA 面向该角色的长度变化。降维后，语义特征与结构化特征一起输入树模型。

PCA 的运行时计算为：

```text
低维向量 = (原始向量 - 训练均值) × 主成分矩阵的转置
```

这将语义模型负责的“理解输入”与树模型负责的“预测成本”分开，也便于复用编码结果。预测器内部支持传入预计算向量；普通 `/predict` 接口仍从文本调用编码器。

## 分类和回归怎样训练

全局分类器以 `is_tool_call` 为标签，采用 LightGBM 二分类；Agent 回归器以真实生成 token 数 `usage_completion_tokens` 为目标，先做 `log1p` 变换。全局分类器的预测概率作为额外特征注入回归器训练，与在线预测保持相同的两阶段结构。

当前服务训练配置如下：

<div class="table-scroll">

| 项目 | 配置 |
|---|---|
| 全局分类器 | binary objective，500 棵树，学习率 0.05 |
| 每个 Agent 的回归器 | quantile objective，`alpha=0.5`，300 棵树，学习率 0.05 |
| 回归目标 | `log1p(usage_completion_tokens)` |
| 推理输出 | `max(0, expm1(预测值))`，转成整数 |
| 单 Agent 最小训练样本数 | 50 |
| 每次加载的数据窗口 | 最近 12,000 条记录，再按时间排序 |
| 样本权重 | 按样本新旧顺序指数衰减，近期样本权重更高 |

</div>

`medium` 对应中位数预测。若要针对 KV 低估采用保守预算，应在资源估计与准入策略中设置余量，而不是把这个 `alpha=0.5` 的回归器解释成已经偏向高估。

论文方法包含分类概率的 isotonic 校准和冷启动时的共享全局模型；当前服务直接使用分类器的 `predict_proba`，缺少 Agent 模型或全局分类器时返回默认 150 token。这是论文方法与后续服务版本的具体差异。

## 长度怎样变成调度与 KV 预算

论文将输出长度转换为模型相关的执行时间和显存估计：

```text
阶段执行时间 ≈ 该模型的 prefill 时间(输入长度)
             + 该模型的平均每 token decode 时间 × 预测输出长度

KV 需求 ≈ 该模型每 token 的 KV 字节数 × (输入长度 + 预测输出长度)
```

例如，一个 32 层、8 个 KV heads、head_dim 为 128 的 BF16 模型，每 token KV 为 128 KiB。输入 2048 token、预测输出 512 token，则全模型 KV 数据量约 320 MiB；若预算另留 20% 余量，则为 384 MiB。实际分配再考虑 block 对齐、TP/PP 分布和其他显存占用。

预测为调度器提供“这次调用预计要运行多久、需要多少空间”的信号。PagedAttention 负责高效管理已经发生的 KV 分配，两者可以配合：利用预测安排任务和模型驻留，再由运行时根据真实容量决定能否继续分配。

`/predict` 服务本身返回长度和概率，不执行显存页映射。后续 Concerto 通过 `predictor_runtime.py` 接入这些字段，并用于请求级投机长度选择；这是同一预测能力在新决策层中的复用。

## 运行反馈与服务开销

节点完成后通过 `/callback/node` 回传真实 token 用量和运行信息，暂存到 Redis；工作流完成后由 Celery 汇总、补充上下文与 embedding，再持久化。后台任务根据增量计数触发训练，Agent 模型更新后通知服务重载。

这条链路实现的是“运行反馈—异步训练—模型更新”，训练不放在单次请求的同步路径中。新到达的数据可以用于后续更新，具体更新频率由阈值控制；代码快照中的两个训练触发阈值均为 1,000,000。

服务启动时预加载 Agent 模型，预测线程将树模型限制为单线程；文本编码和模型计算放到受限工作线程中，避免阻塞 FastAPI 的事件循环。耗时分别记录编码、特征准备、Redis、分类、回归，以及接口排队与处理时间，便于判断瓶颈究竟在哪里。

来源：Maestro 论文 §III-B、§III-D；`concerto-runtime` 提交 `8ee8969` 中的 `moarks-20260125/python-predictor/src/`，主要包括 `config.py`、`training/predictor.py`、`training/trainer.py`、`training/bert_encoder.py`、`api/prediction.py`、`tasks.py`；接入逻辑位于 `tpds-p0-p1-experiments-20260724/predictor_runtime.py`。代码快照日期为 2026-08-29。

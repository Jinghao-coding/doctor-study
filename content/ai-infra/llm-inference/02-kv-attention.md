## 一句话结论

请求生命周期要把 API 接入、tokenization、调度、prefill、decode、stream 返回和缓存释放串成一条链。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | LLM 推理系统 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕请求生命周期、Prefill/Decode、KV Cache、Attention 优化、Serving Engine 和性能瓶颈建立系统化面试答案。 |
| 面试抓手 | 回答时不要只讲模型 forward，要把引擎调度和 KV cache 管理一起讲。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

## 请求生命周期

一次 LLM 推理请求不是“直接进模型然后输出文本”，而是经过接入、排队、调度、计算、采样和返回等多个环节。理解这条链路，才能判断 TTFT、TPOT、吞吐和显存问题分别发生在哪里。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 KV 缓存只缓存 K 和 V，不缓存 Q？</div>
<div class="qa-a"><p>一个东西值不值得缓存，不看它"重不重要"，而看它"后面还会不会再次被用到"。Q 只在当前这一步有用一次——当前 token 的 Query 只需要和历史 K/V 做注意力计算；而 K、V 会在后面每一步继续被反复用到——未来每个新 token 的 Query 都需要和所有历史 token 的 Key 做匹配。所以 KV cache 只缓存 K 和 V，不缓存 Q，不是因为 Q 不重要，而是因为 Q 不需要重复使用。</p></div>
</div>

<h3>PagedAttention（vLLM）</h3>
<p>传统 KV 缓存预分配连续内存，最大长度固定，短请求浪费严重。PagedAttention 借鉴操作系统虚拟内存的分页思想：</p>
<ul>
<li>把 KV 缓存切成固定大小的 block（如 16 token 一块）</li>
<li>用 block table 维护逻辑到物理的映射</li>
<li>按需分配，请求结束释放，消除内部碎片</li>
<li>支持 copy-on-write，多个 beam 可共享公共前缀</li>
</ul>

## 端到端流程

| 阶段 | 输入 | 主要动作 | 输出 |
|---|---|---|---|
| 请求接入 | 用户 Prompt、生成参数 | 鉴权、限流、参数校验 | 标准化请求 |
| Tokenization | 文本 Prompt | 切分为 token ID | token 序列 |
| 调度排队 | token 序列、优先级、SLO | 选择进入 batch 的请求 | 执行计划 |
| Prefill | 完整 Prompt token | 并行计算上下文和 attention | 初始 KV Cache |
| Decode | 历史 KV Cache、新 token | 逐 token 自回归生成 | 新 token、更新后的 KV Cache |
| 采样与返回 | logits、采样参数 | temperature、top-p、top-k、反序列化 | 流式文本或完整文本 |

## 调度器职责

调度器决定“哪些请求先跑、哪些请求一起跑、显存不够时怎么办”。它需要同时处理计算资源、显存资源和服务延迟目标。

| 职责 | 说明 |
|---|---|
| 准入控制 | 根据显存、batch、优先级决定请求能否进入运行队列 |
| Batch 组织 | 把多个请求组合成更高效的执行批次 |
| KV Cache 分配 | 为每个请求分配或复用 KV block |
| 抢占与恢复 | 显存不足时换出、重算或终止低优先级请求 |
| 完成回收 | 请求结束后释放 KV Cache 和调度状态 |

## 核心路径

```flow
用户请求 | Prompt、会话上下文、生成参数进入服务层
网关 / API Server | 鉴权、限流、参数校验、路由到推理引擎
Tokenizer | 文本转 token IDs，必要时应用聊天模板
Scheduler | 组织 batch、分配 KV Cache、决定 prefill/decode 顺序
Prefill Worker | 处理完整 prompt，写入初始 KV Cache
Decode Worker | 每轮生成新 token，并追加 K/V
Sampler | 根据 logits 执行 temperature、top-p、top-k 等采样
Stream Response | detokenize 后通过 SSE/WebSocket/HTTP 返回
```

## 常见问题定位

| 现象 | 更可能的问题位置 | 排查方向 |
|---|---|---|
| 首 token 很慢 | 排队、Tokenization、Prefill | 看 TTFT、prefill batch、prompt 长度 |
| 输出过程中卡顿 | Decode、采样、流式返回 | 看 TPOT、KV Cache 读取、网络返回 |
| 并发上不去 | KV Cache、显存、调度 | 看显存余量、block 碎片、最大 batch |
| GPU 利用率低 | Decode memory-bound | 看 MFU、HBM 带宽、batch size |
| P99 抖动大 | 长 prompt 阻塞、抢占、换出 | 看 chunked prefill、优先级调度 |

## 面试回答

**30 秒版：**

请求生命周期要把 API 接入、tokenization、调度、prefill、decode、stream 返回和缓存释放串成一条链。 回答时不要只讲模型 forward，要把引擎调度和 KV cache 管理一起讲。

**2 分钟版：**

我会先说明这个问题在 LLM 推理系统 里的位置，再拆核心链路：输入是什么、系统如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：吞吐和延迟、显存和计算、隔离和利用率、简单实现和生产稳定性之间如何取舍。最后用观测指标或排障路径收束，说明如何判断方案真的有效。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

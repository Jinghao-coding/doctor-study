## 一句话结论

系统设计题这一节需要服务面试复习：先给结论，再把链路、机制、权衡和回答模板讲清楚。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 系统设计题 |
| 章节类型 | 系统设计类 |
| 解决问题 | 围绕多模型推理、多租户调度、分布式训练平台和 KV Cache 管理形成可复述设计题框架。 |
| 面试抓手 | 回答时先定范围，再讲核心链路，最后落到工程风险和面试追问。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-w">
<h3>题目</h3>
<p>为 LLM 推理集群设计高效的 KV 缓存管理系统。</p>

<h3>设计要点</h3>
<ol>
<li><strong>分页管理</strong>：借鉴 PagedAttention，KV 缓存切成固定大小 block，block table 维护映射</li>
<li><strong>按需分配</strong>：不预分配最大长度，根据预测输出长度分配初始 block，不够时动态追加</li>
<li><strong>前缀共享</strong>：相同系统 prompt 的请求共享 KV 缓存前缀（RadixAttention），copy-on-write 语义</li>
<li><strong>层级存储</strong>：GPU → CPU → 磁盘三级缓存。热请求在 GPU，暂停的请求 offload 到 CPU</li>
<li><strong>驱逐策略</strong>：LRU 基础上考虑请求优先级——低优先级请求的 KV 先被驱逐</li>
<li><strong>内存核算</strong>：M_kv + M_res ≤ M_total，准入控制防止过载</li>
</ol>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">追问：多模型场景下 KV 缓存管理有什么额外挑战？</div>
<div class="qa-a"><p>(1) <strong>异构 block 大小</strong>：不同模型的 head_dim、num_heads 不同，block 大小不统一。解决：统一到字节粒度的 slab allocator。(2) <strong>模型切换时的缓存失效</strong>：模型从 GPU 换出时，其 KV 缓存也要处理——可以保留等模型回来，也可以驱逐释放空间。(3) <strong>预测准确性依赖模型</strong>：不同模型的输出长度分布不同，需要 per-model 预测器。</p></div>
</div>
</div>

## 面试回答

**30 秒版：**

系统设计题这一节需要先定范围，再把机制和工程边界讲清楚。 按结论、链路、权衡、风险回答。

**2 分钟版：**

我会先说明这个问题在 系统设计题 里的位置，再拆核心链路：输入是什么、系统如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：吞吐和延迟、显存和计算、隔离和利用率、简单实现和生产稳定性之间如何取舍。最后用观测指标或排障路径收束，说明如何判断方案真的有效。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

## 一句话结论

设计 KV 缓存管理系统的核心是把显存当成稀缺资源精细经营：分页（PagedAttention）消除碎片、按需分配避免预占、前缀共享复用系统 prompt、GPU/CPU/磁盘层级存储 offload 冷请求、再加准入控制守住 M_kv + M_res ≤ M_total。答题主线是「显存利用率 vs 命中延迟」的权衡。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 系统设计题 |
| 章节类型 | 系统设计类 |
| 解决问题 | 围绕多模型推理、多租户调度、分布式训练平台和 KV Cache 管理形成可复述设计题框架。 |
| 面试抓手 | 回答时先定范围，再讲核心链路，最后落到工程风险和面试追问。 |

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

我会把 KV 缓存当显存资源管理问题来设计：用 PagedAttention 把缓存切成固定 block 消除碎片，按需分配而不是预占最大长度，相同前缀做 RadixAttention 共享 + copy-on-write，热请求留 GPU、冷请求 offload 到 CPU/磁盘，最后用准入控制保证 M_kv + M_res 不超 M_total。

**2 分钟版：**

我会先定问题范围：KV 缓存随序列长度线性增长，是 decode 阶段最主要的显存消耗，目标是在不 OOM 的前提下最大化并发和吞吐。然后讲核心机制：分页管理用 block table 维护逻辑到物理 block 的映射，像虚拟内存一样消除外部碎片；按需分配根据预测输出长度给初始 block、不够再追加；前缀共享让相同系统 prompt 的请求复用同一份 KV，写时复制避免相互污染。接着讲层级存储和驱逐：GPU 放热请求，暂停或低优先级请求 offload 到 CPU 甚至磁盘，驱逐在 LRU 基础上叠加请求优先级。然后讲准入控制：每个请求进来先核算显存够不够，不够就排队而非强行接收。最后讲权衡和多模型挑战：offload 省显存但增加换入延迟，前缀共享提升命中但要处理失效；多模型下 block 大小异构要统一到字节粒度 slab，模型换出时缓存要决定保留还是释放，输出长度预测要 per-model。判断方案有效就看显存利用率、缓存命中率和 OOM/驱逐频率。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

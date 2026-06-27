## 一句话结论

设计 KV 缓存管理系统的核心是把显存当成稀缺资源精细经营：分页（PagedAttention）消除碎片、按需分配避免预占、前缀共享复用系统 prompt、GPU/CPU/磁盘层级存储 offload 冷请求、再加准入控制守住 M_kv + M_res ≤ M_total。答题主线是「显存利用率 vs 命中延迟」的权衡。
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

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

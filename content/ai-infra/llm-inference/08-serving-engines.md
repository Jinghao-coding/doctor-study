<div class="card card-m">
<h3>AI Infra 视角：推理引擎 = 调度器 + 内存系统 + 计算后端 + 分布式策略 + Serving 工程</h3>
<p>面向应用的人只需要会用 vLLM 启服务；做 AI Infra 必须能讲清楚引擎内部的请求调度、KV 内存管理、CUDA Kernel 选择、并行切分和容错。下面把推理引擎拆成 5 个子系统，每个子系统直接给出原理、关键数据结构、源码定位和实战要点。</p>
</div>

<div class="card card-s">
<h3>掌握深度分层</h3>
<table>
<tr><th>层级</th><th>定位</th><th>典型岗位</th><th>必须能回答</th></tr>
<tr><td>L1 会用</td><td>启服务、调参、压测</td><td>算法工程师</td><td>怎么起 vLLM、怎么调 max-num-seqs</td></tr>
<tr><td>L2 会调优</td><td>读懂指标，定位瓶颈</td><td>应用侧 Infra</td><td>TTFT 高怎么排查、batch 满了为什么吞吐反降</td></tr>
<tr><td>L3 懂原理</td><td>解释 PagedAttention、continuous batching、chunked prefill</td><td>AI Infra 初级</td><td>KV 块为什么分页，prefill 和 decode 怎么共存</td></tr>
<tr><td>L4 会改源码</td><td>读 vLLM/SGLang 调度器，写自定义 sampler、kernel</td><td>AI Infra 中高级</td><td>vLLM Scheduler 的 waiting/running/swapped 状态机</td></tr>
<tr><td>L5 能设计</td><td>从零设计推理系统、做 PD 分离、做多机调度</td><td>资深 / 专家</td><td>千卡 serving 集群怎么做请求路由、KV 迁移、容灾</td></tr>
</table>
<p>AI Infra 岗一般要求 L3-L4，资深岗要求 L4-L5。</p>
</div>

<div class="card card-w">
<h3>子系统一：调度器（Scheduler）</h3>
<p>调度器决定每个 forward step 跑哪些请求。vLLM 的 Scheduler 是 Python 实现，核心数据结构是三个队列 + 一组 SequenceGroup 状态机。</p>
<p><strong>状态机：</strong>每个请求是一个 SequenceGroup，状态在 <code>WAITING → RUNNING → SWAPPED → FINISHED</code> 之间迁移。WAITING 在 waiting 队列里排队等显存；RUNNING 进入 running 队列每个 step 参与 forward；显存不够时被抢占，KV 丢弃则回到 WAITING（recompute），KV 拷到 CPU 则进入 swapped 队列（swap）。</p>
<p><strong>调度循环：</strong>每个 step 调用 <code>schedule()</code>，先尝试唤醒 swapped，再调度 running 的 decode，再用剩余 token budget 调度 waiting 的 prefill；预算由 <code>max_num_batched_tokens</code> 限制，并发由 <code>max_num_seqs</code> 限制。</p>
<p><strong>抢占：</strong>当 running + 新 prefill 总 KV 块超过可用块时，按 FCFS 反向抢占最近加入的请求；抢占策略 <code>recompute</code>（默认，丢 KV 重算）或 <code>swap</code>（拷到 CPU pinned memory）。</p>
<p><strong>源码：</strong><code>vllm/core/scheduler.py</code> 的 <code>_schedule_default()</code>、<code>_schedule_chunked_prefill()</code>、<code>_preempt()</code>；SGLang 在 <code>python/sglang/srt/managers/scheduler.py</code>，使用 RadixAttention 前缀树而非简单队列。</p>
</div>

<div class="card card-s">
<h3>子系统二：KV Cache 内存管理（PagedAttention 详解）</h3>
<p>KV Cache 是显存第一稀缺资源。PagedAttention 把 KV 像 OS 虚拟内存一样按 block 管理，把碎片率从 60-80% 压到 &lt; 4%。</p>
<p><strong>核心数据结构：</strong></p>
<ul>
<li><code>BlockManager</code>：维护物理 block 池（gpu_blocks、cpu_blocks），用 free list 管理空闲块，引用计数管理共享。</li>
<li><code>BlockTable</code>：每个 SequenceGroup 一张表，逻辑块号 → 物理块号。生成新 token 时，<code>logical_block_id = pos // block_size</code>，满了就 <code>allocate</code> 一块新物理块挂到表尾。</li>
<li><code>block_size</code>：默认 16。太小 block table 大、kernel 访存碎；太大内部碎片回到老问题、prefix 共享粒度变粗。</li>
</ul>
<p><strong>Copy-on-Write：</strong>parallel sampling / beam search 共享前缀块，引用计数 &gt; 1；任一分支要写入时，先 copy 一份再写，引用计数减一。这就是 vLLM 比 HuggingFace generate 在 beam=4 时省 4 倍显存的原因。</p>
<p><strong>Prefix Cache：</strong>对相同前缀（系统提示词、few-shot）的物理块加哈希签名，跨请求复用，命中后 prefill 阶段直接跳过这些块的计算。开关：<code>enable_prefix_caching=True</code>；命中率指标：<code>vllm:gpu_prefix_cache_hit_rate</code>。</p>
<p><strong>FP8 KV：</strong>显存减半，可翻倍 batch 或上下文长度。需要 SM89+（Ada/Hopper），attention kernel 需支持 FP8 反量化；长上下文（&gt;32k）和数学/代码任务要做精度回归。</p>
</div>

<div class="card card-w">
<h3>子系统三：计算后端与 Kernel</h3>
<p>同一算法不同 kernel 实现吞吐能差 2-5 倍。AI Infra 必须能看懂下面这些 kernel 的优化点。</p>
<p><strong>FlashAttention v2：</strong>把 attention 拆成外层 query block、内层 K/V block，按 K/V 维度做 online softmax，所有中间 S=QK^T、P=softmax(S) 不落 HBM，全部留在 SRAM；并行维度从 batch×head 加到 batch×head×seq_q，长序列也能打满 SM。</p>
<p><strong>FlashAttention v3：</strong>针对 H100。① warp specialization（生产者 warp 跑 TMA load，消费者 warp 跑 GEMM/softmax）；② async copy（TMA + cp.async）让 load 和 compute overlap；③ FP8 路径用 incoherent processing 抵消量化误差；典型 H100 SXM 上接近 75% MFU。</p>
<p><strong>PagedAttention kernel：</strong>不同于 FlashAttention 的 contiguous KV，它每个 query token 要按 block table 间接寻址 KV 块；用 <code>__ldg</code> 做 read-only cache，每个 thread block 处理一个 query token 的多个 head，KV 按 block 顺序加载。</p>
<p><strong>FlashInfer：</strong>把 PagedAttention + FlashAttention 合并实现，支持 ragged batch、多种 KV layout（NHD/HND）、动态 block size，vLLM v0.6+ 默认 backend 之一。</p>
<p><strong>CUDA Graphs：</strong>decode step 形状固定（batch_size 一定时 input shape 不变），把整个 step 的 kernel launch 序列录成 graph，replay 一次替代上百次 launch；Llama-3-8B BF16 在 A100 上能减 10-15% 延迟。前提是 input shape 不能变，所以 vLLM 给常用 batch_size 各 capture 一份。</p>
<p><strong>算子融合：</strong>fused RMSNorm + QKV proj、fused SiLU + gate proj、fused MoE（top-k + dispatch + grouped GEMM）；TensorRT-LLM 通过 plugin 把 attention + rotary + KV append 融成一个 kernel。</p>
</div>

<div class="card card-s">
<h3>子系统四：并行与分布式策略</h3>
<p>大模型推理必然涉及多卡多机，下面是 4 种并行的具体含义和通信开销。</p>
<p><strong>Tensor Parallel（TP）：</strong>按列切权重矩阵。Attention：QKV 投影按 head 切，attention 内部不通信，output 投影按行切，每层 attention 末尾一次 all-reduce。FFN：第一层按列切，第二层按行切，FFN 末尾一次 all-reduce。每层 2 次 all-reduce，单 token 通信量 ≈ 2 × hidden_dim × dtype_size。Llama-70B TP=8 在 A100 NVLink 上 all-reduce 占 forward 时间 15-25%；跨机走 IB 会到 50%+，所以 TP 不跨机。</p>
<p><strong>Pipeline Parallel（PP）：</strong>按层切到不同 GPU，micro-batch 流水。推理 decode 阶段每次只生成 1 个 token，micro-batch 数受限，bubble 严重，所以推理很少单独用 PP，通常和 TP 混合或仅用于跨机。</p>
<p><strong>Expert Parallel（EP）：</strong>MoE 模型把专家分到不同 GPU。每层 2 次 all-to-all：dispatch（按路由结果把 token 发给对应 expert 卡）、combine（算完再聚回原卡）。瓶颈是 all-to-all 跨机带宽和路由不均；DeepSeek 用 DeepEP 在 H800 NVLink 上做了大量优化，redundant experts 解决热点。</p>
<p><strong>Data Parallel（DP）：</strong>多副本，配请求路由层；推理服务的横向扩展默认就是 DP。Attention DP + FFN/MoE EP 是当前 MoE 大模型部署的常见组合（SGLang/DeepSeek-V3）。</p>
<p><strong>Sequence Parallel：</strong>长上下文场景把序列维度切到不同卡，配合 Ring Attention 或 Striped Attention 做 KV 通信，主要解决单卡放不下超长 prompt 的 KV。</p>
</div>

<div class="card card-w">
<h3>子系统五：Serving 工程化</h3>
<p>这部分决定能不能扛生产流量。</p>
<p><strong>请求生命周期：</strong>HTTP/gRPC 入口 → tokenizer（独立进程或 worker，避免阻塞）→ 调度器队列 → forward → detokenizer（流式逐 token decode）→ SSE/WebSocket 推流。</p>
<p><strong>OpenAI 兼容协议：</strong>路径 <code>/v1/chat/completions</code>、<code>/v1/completions</code>、<code>/v1/embeddings</code>；流式用 SSE，<code>data: {...}\n\n</code>，结束 <code>data: [DONE]</code>。tool calling、structured output（JSON schema、正则约束）走 Outlines/XGrammar。</p>
<p><strong>核心指标（Prometheus）：</strong></p>
<ul>
<li><code>vllm:time_to_first_token_seconds</code>：TTFT 直方图，p50/p95/p99 都要看。</li>
<li><code>vllm:time_per_output_token_seconds</code>：TPOT。</li>
<li><code>vllm:e2e_request_latency_seconds</code>：端到端。</li>
<li><code>vllm:request_queue_time_seconds</code>：队列时长，TTFT 涨先看这个。</li>
<li><code>vllm:num_preemptions_total</code>：抢占次数，常见瓶颈信号。</li>
<li><code>vllm:gpu_cache_usage_perc</code>、<code>vllm:gpu_prefix_cache_hit_rate</code>：KV 占用与命中。</li>
<li><code>vllm:num_requests_running/waiting/swapped</code>：三队列长度。</li>
</ul>
<p><strong>容错与隔离：</strong>OOM 自救（recompute/swap）、单卡 NCCL timeout 检测踢出、慢节点用 p99 兜底、超长请求隔离独立队列防尾延迟、请求级超时和取消（client 断开后调度器要立刻 abort 释放 KV）。</p>
<p><strong>滚动升级：</strong>weight 持久化到本地 NVMe，新副本起来读完再切流量；KV 一般不持久化（除非 PD 分离场景做 KV migration）。</p>
</div>

<div class="card card-m">
<h3>关键技术点 1：Continuous Batching</h3>
<p>调度粒度从 request 级降到 iteration（token）级。Static batching 整批进出，最长那条没结束全 batch 都得等；continuous batching（Orca OSDI'22 提出）每个 forward step 都重组 batch：完成的请求立即返回 finish 槽位，等待中的请求立即加入。</p>
<p><strong>关键实现点：</strong>① 不同请求 KV 长度不同，必须配 PagedAttention 这种支持 ragged batch 的内存管理才能真正落地；② 每个 step 重新构建 attention mask 和位置索引；③ token budget 控制单 step 最多处理 N 个 token，避免 prefill 把 step 拉爆。</p>
<p><strong>瓶颈：</strong>当 batch 已打满 token budget 或 KV 块用满，新请求触发 preemption；<code>max_num_batched_tokens</code> 太小吞吐上不去，太大 TPOT 抖动。Llama-3-8B BF16 在 H100 上典型设 8192-16384。</p>
</div>

<div class="card card-s">
<h3>关键技术点 2：Chunked Prefill</h3>
<p>Prefill 是 compute-bound，单条 8k prompt 一次 forward 把 GPU 占满几百毫秒，期间 decode 的 TPOT 直接卡死，造成尾延迟。Sarathi-Serve 提出把 prefill 拆 chunk。</p>
<p><strong>算法：</strong>每个 step 给一个 token budget（如 2048），先用 decode 请求填（每个 decode 1 token），剩余预算用来跑 prefill chunk；长 prompt 分多个 step 完成 prefill。</p>
<p><strong>收益：</strong>① decode 的 TPOT 抖动从几百毫秒降到几十毫秒；② GPU 利用率提升（prefill chunk 把 decode 的 memory-bound 间隙填上，变成 compute + memory 混合）；代价是单条 prefill 总耗时略涨（多次 kernel launch 和 attention mask 重建）。</p>
<p><strong>开关：</strong>vLLM <code>--enable-chunked-prefill</code>，v0.6 起默认开启；chunk 大小由 <code>max_num_batched_tokens</code> 控制。</p>
</div>

<div class="card card-w">
<h3>关键技术点 3：PD 分离（Disaggregated Prefill-Decode）</h3>
<p>Chunked Prefill 治标不治本：prefill 和 decode 仍共享同一组 GPU，扩缩容耦合。DistServe（OSDI'24）和 Splitwise（ISCA'24）提出物理拆分。</p>
<p><strong>架构：</strong>① Prefill 集群：高算力卡（H100/H200），追求 TTFT，TP 较大、batch 较小。② Decode 集群：可以用算力略低但显存大的卡，追求吞吐和 TPOT，batch 大、KV 多。③ KV 传输：prefill 完后通过 NVLink/RDMA 把整段 KV 传给 decode 节点；H100 NVLink 900GB/s、CX-7 IB 400Gb/s，10k token Llama-70B 的 KV ~1.4GB，传输 &lt; 5ms。</p>
<p><strong>关键工程问题：</strong>① 路由层要根据 prompt 长度和当前两端负载决定走哪个 prefill 节点；② KV layout 跨节点要兼容，常用 NVSHMEM 或自研 RDMA 库；③ decode 节点要能接收 streaming KV，第一块到了就能开始 decode 第一个 token，进一步压低 TTFT。</p>
<p><strong>vLLM/SGLang 实现：</strong>vLLM v0.6+ 实验性支持 disaggregated serving；DeepSeek/月之暗面/Mooncake 都是 PD 分离生产实践。</p>
</div>

<div class="card card-s">
<h3>关键技术点 4：投机解码（Speculative Decoding）</h3>
<p>Decode 是 memory-bound，瓶颈在权重从 HBM 读到 SM。一次 forward 验证多个 token 几乎不增加权重读取，是无损加速的关键洞察。</p>
<p><strong>原理：</strong>用便宜的 draft 模型生成 K 个候选 token，大模型对 K+1 个位置并行做一次 forward，得到大模型在每个位置的真实分布；按拒绝采样接受最长前缀，第一个被拒绝的位置用大模型分布重采样。数学上等价于直接从大模型采样，无损。</p>
<p><strong>变体：</strong></p>
<ul>
<li><strong>Draft model：</strong>用一个小模型（如 Llama-1B 配 Llama-70B），简单但 draft 也要算 forward。</li>
<li><strong>Medusa：</strong>在大模型 last hidden 上接 N 个独立 head 直接预测后 N 个 token，免 draft 模型，但精度依赖 head 训练质量。</li>
<li><strong>EAGLE / EAGLE-2：</strong>把大模型的 hidden state 也喂给 draft，接受率显著高于普通 draft；当前最常用。</li>
<li><strong>Lookahead Decoding：</strong>用 Jacobi 迭代生成 N-gram pool，命中即接受，无需训练。</li>
</ul>
<p><strong>陷阱：</strong>① 接受率低（&lt; 0.5）反而变慢；② batch 越大越没收益（GPU 已 compute-bound）；③ 实现复杂，KV 要支持回滚被拒绝位置。</p>
</div>

<div class="card card-w">
<h3>关键技术点 5：MoE 推理与 EP</h3>
<p>DeepSeek-V3、Qwen2.5-MoE、Mixtral 8x22B 推动 MoE serving 成为 2025-2026 核心战场。</p>
<p><strong>瓶颈：</strong></p>
<ul>
<li><strong>路由不均：</strong>top-k 路由让部分专家成为热点，整 batch 跟着最慢专家走。训练侧用 aux loss 平衡，推理侧用 redundant experts（热门专家放 2 份）。</li>
<li><strong>all-to-all：</strong>每层 2 次 all-to-all（dispatch + combine），跨机 IB 是瓶颈；DeepEP 用 NVLink 做机内、IB 做机间，一次只发非零 token，比 NCCL all-to-all 快 3 倍。</li>
<li><strong>显存：</strong>专家多激活少，纯 TP 把每个专家都切让 GEMM 太小；EP 每个专家完整放在一卡，配 grouped GEMM 一次算多个专家。</li>
</ul>
<p><strong>典型部署：</strong>DeepSeek-V3 671B 用 Attention DP=32 + Expert Parallel=32（一台 8 卡 H800 跑 8 个专家），prefill 节点和 decode 节点各跑独立 EP 集群。</p>
<p><strong>计算与通信 overlap：</strong>每层 attention 算完先发 dispatch all-to-all，同时算下一组的 attention；DeepSeek DualPipe 在训练用，推理也有类似思路。</p>
</div>

<div class="card card-s">
<h3>关键技术点 6：Prefix Cache 与 RadixAttention</h3>
<p>多轮对话、Agent、few-shot prompt 有大量共享前缀。Prefix Cache 把相同前缀的 KV 块跨请求复用。</p>
<p><strong>vLLM Prefix Cache：</strong>对每个完整 block 做 hash（block_size token 内容 + 前一块 hash），相同 hash 的物理块共享；命中时跳过这些 token 的 prefill 计算。开关 <code>enable_prefix_caching</code>。</p>
<p><strong>SGLang RadixAttention：</strong>把所有活跃 KV 块组织成 radix tree（基数树），路径即 token 序列。新请求来时按 token 在树上匹配最长前缀，命中部分直接复用，未命中部分新建子节点。LRU 淘汰叶子；命中粒度比 vLLM 的 block hash 更细，多轮对话场景命中率显著更高。</p>
<p><strong>命中率优化：</strong>路由层按 prompt prefix hash 把请求路由到同一实例，命中率从 30% 拉到 80%+；系统提示词命中后 TTFT 几乎为 0。</p>
</div>

<div class="card card-w">
<h3>关键技术点 7：KV 量化（FP8 / INT8）</h3>
<p>BF16 KV → FP8 KV 显存减半，可翻倍 batch 或上下文。</p>
<p><strong>方案：</strong></p>
<ul>
<li><strong>per-tensor scale：</strong>整个 K 或 V 用一个 scale，简单但动态范围大时精度差。</li>
<li><strong>per-token scale：</strong>每个 token 一个 scale，精度更好，主流方案。</li>
<li><strong>per-channel scale：</strong>对 outlier channel 单独 scale，组合 SmoothQuant 思路。</li>
</ul>
<p><strong>硬件：</strong>FP8 需要 SM89+（Ada L40 / Hopper H100/H800/H200）；A100 没有 FP8 但可以走 INT8。</p>
<p><strong>精度回归：</strong>① 短上下文一般无损；② &gt; 32k 累计误差需要单独评测；③ 数学/代码任务比对话敏感；④ 用业务真实评测集（不是 MMLU）卡 acc/EM/pass@1。</p>
</div>

<div class="card card-m">
<h3>四大引擎深度对比</h3>
<table>
<tr><th>维度</th><th>vLLM</th><th>TensorRT-LLM</th><th>SGLang</th><th>TGI</th></tr>
<tr><td>核心创新</td><td>PagedAttention + continuous batching</td><td>NVIDIA 全栈 kernel + plugin</td><td>RadixAttention + 前端 DSL</td><td>工程化 + HF 生态</td></tr>
<tr><td>调度器</td><td>Python，可读性强，社区活跃</td><td>C++ in-flight batcher，半闭源</td><td>Python，前缀树调度</td><td>Rust router + Python server</td></tr>
<tr><td>KV 管理</td><td>Paged，block_size 可调，prefix cache（hash）</td><td>Paged，FP8 KV，循环 buffer</td><td>Radix tree 自动共享</td><td>Paged（早期版本较弱）</td></tr>
<tr><td>量化</td><td>AWQ/GPTQ/FP8/INT8</td><td>SmoothQuant/FP8/INT4 AWQ 全栈</td><td>AWQ/FP8</td><td>BitsAndBytes/GPTQ</td></tr>
<tr><td>投机解码</td><td>支持（draft / EAGLE / Medusa）</td><td>支持，性能强</td><td>支持 EAGLE</td><td>较弱</td></tr>
<tr><td>MoE</td><td>支持，EP 持续完善</td><td>支持，性能优</td><td>DeepSeek 优化最好</td><td>有限</td></tr>
<tr><td>多模态</td><td>较好</td><td>需要自己接</td><td>较好</td><td>有限</td></tr>
<tr><td>构建复杂度</td><td>低，pip 装</td><td>高，需要 build engine、绑版本</td><td>低</td><td>低</td></tr>
<tr><td>定位</td><td>通用 OSS 默认选项</td><td>NVIDIA 上的极致性能</td><td>复杂 prompt / agent / 结构化生成</td><td>HF 生态快速上线</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q1: 解释 PagedAttention，为什么提升吞吐？block_size 怎么选？</div>
<div class="qa-a">
<p><strong>核心：</strong>把 KV Cache 像 OS 虚拟内存一样按 block 管理。</p>
<div class="qa-section"><div class="qa-section-title">解决什么问题</div><p>传统按 max_seq_len 给每个序列预留连续显存，浪费严重（内部碎片 + 预分配碎片），实际利用率常 &lt; 40%，并发上不去。</p></div>
<div class="qa-section"><div class="qa-section-title">怎么做</div><p>逻辑上按 block_size（如 16）分块，物理上不连续，通过 block table 映射。新 token 满一块再申请下一块。共享前缀用引用计数 + CoW。</p></div>
<div class="qa-section"><div class="qa-section-title">block_size 选型</div><p>太小（1-4）：block table 大、attention kernel 访存不友好、调度开销升高。太大（&gt;64）：内部碎片回到老问题，prefix 共享粒度变粗。vLLM 默认 16，是 kernel 性能与碎片率的折中。</p></div>
<div class="qa-summary">PagedAttention 把显存利用率从 ~40% 提到 &gt;90%，吞吐提升来自更高的 batch size。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q2: Continuous Batching 与 Static Batching 区别？</div>
<div class="qa-a">
<p><strong>核心：</strong>调度粒度从 request 级降到 iteration（token）级。</p>
<div class="qa-section"><div class="qa-section-title">Static</div><p>整批一起进入、一起出去。最长那条没结束全 batch 都得等，GPU 大量空转。</p></div>
<div class="qa-section"><div class="qa-section-title">Continuous（Orca / vLLM）</div><p>每个 forward step 重新组 batch：完成的立即返回，等待的立即加入。配 PagedAttention，无需 padding 到同长。</p></div>
<div class="qa-section"><div class="qa-section-title">瓶颈</div><p>batch 打满 token budget 后再加请求触发 preemption，<code>max_num_batched_tokens</code> 要按显存和 SLA 调。</p></div>
<div class="qa-summary">continuous batching 让 GPU 永远在干活，吞吐通常 5-20 倍提升。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q3: Prefill 和 Decode 一起跑会有什么问题？Chunked Prefill 和 PD 分离怎么解？</div>
<div class="qa-a">
<p><strong>核心：</strong>两阶段计算特性完全不同，混跑互相伤害。</p>
<div class="qa-section"><div class="qa-section-title">冲突</div><p>Prefill compute-bound，单条长 prompt 把 GPU 占满几百毫秒，期间 decode TPOT 卡顿。Decode memory-bound，单独跑 GPU 利用率低。</p></div>
<div class="qa-section"><div class="qa-section-title">Chunked Prefill</div><p>把长 prompt 切 chunk，每个 step 拼一段 prefill + 多个 decode 进同一 batch，TPOT 抖动从几百 ms 降到几十 ms。</p></div>
<div class="qa-section"><div class="qa-section-title">PD 分离</div><p>物理拆两个集群：Prefill 节点专跑首 token，Decode 节点专跑生成；KV 通过 NVLink/RDMA 传输。可独立扩缩容，TTFT 和 TPOT 解耦。</p></div>
<div class="qa-summary">在线服务多用 chunked prefill；超大规模或 SLA 严苛用 PD 分离。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q4: 投机解码原理？为什么能加速且不损精度？</div>
<div class="qa-a">
<p><strong>核心：</strong>用便宜 draft 猜 K 个，大模型一次 forward 验证。</p>
<div class="qa-section"><div class="qa-section-title">原理</div><p>Draft 生成 K 个候选 token，大模型对 K+1 个位置并行 forward，按拒绝采样接受最长前缀，第一个被拒位置用大模型分布重采样。数学上等价于直接采样，无损。</p></div>
<div class="qa-section"><div class="qa-section-title">为何变快</div><p>Decode memory-bound，瓶颈是权重从 HBM 读到 SM。一次 forward 验证 K 个 token 几乎不增权重读取，TPOT 接近降为 1/K（接受率高时）。</p></div>
<div class="qa-section"><div class="qa-section-title">变体</div><p>Draft model（Llama-1B + 70B）；Medusa（多头预测，免 draft）；EAGLE（在 hidden state 上 draft，接受率高）；Lookahead（Jacobi 迭代）。</p></div>
<div class="qa-summary">提升 1.5-3x 不损精度，但接受率低反而变慢，且 batch 越大收益越小。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q5: 设计 1k QPS、p99 TTFT &lt; 500ms 的 70B serving 集群</div>
<div class="qa-a">
<p><strong>核心：</strong>容量估算 + 分层架构 + SLO 拆分。</p>
<div class="qa-section"><div class="qa-section-title">容量</div><p>70B BF16 ≈ 140GB，TP=4 在 4×A100-80G 或 2×H100-80G 跑得动。假设输入 1k、输出 256，单实例 ~30 QPS，需要 ~40 实例 + 余量。</p></div>
<div class="qa-section"><div class="qa-section-title">分层</div><p>① 接入：LB + 鉴权 + 限流；② 路由：按 prefix hash 路由提高 cache 命中；③ 推理：vLLM 池，开 chunked prefill；④ 长 prompt 独立集群走 PD 分离；⑤ 监控 TTFT/TPOT/queue/preempt/cache hit。</p></div>
<div class="qa-section"><div class="qa-section-title">达成 p99 TTFT</div><p>chunked prefill 控 chunk size，限单 step token 预算；超长请求隔离独立队列；预留 20% headroom；prefix cache 命中干掉系统提示词的 prefill。</p></div>
<div class="qa-section"><div class="qa-section-title">容灾</div><p>多 AZ；权重持久化；KV swap 防 OOM；慢节点剔除；金丝雀升级。</p></div>
<div class="qa-summary">设计题给分点：容量、SLO 拆分、瓶颈识别、可观测、容灾，缺一不可。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q6: vLLM、TensorRT-LLM、SGLang 怎么选？</div>
<div class="qa-a">
<p><strong>核心：</strong>workload + 硬件 + 团队能力三维决策。</p>
<div class="qa-section"><div class="qa-section-title">vLLM</div><p>OSS 生态最活、上手最快、模型支持最全，适合大多数在线服务和团队，是默认选项。</p></div>
<div class="qa-section"><div class="qa-section-title">TensorRT-LLM</div><p>纯 NVIDIA GPU、追求极致延迟和吞吐、能接受 build engine 的工程成本，适合大厂自营核心业务。</p></div>
<div class="qa-section"><div class="qa-section-title">SGLang</div><p>有大量共享前缀、做结构化输出、tool calling、Agent 多轮，RadixAttention 命中红利明显；DeepSeek MoE 部署事实标准。</p></div>
<div class="qa-section"><div class="qa-section-title">TGI</div><p>团队深度依赖 HF 生态、追求快速上线、性能要求不极致。</p></div>
<div class="qa-summary">先问场景再选引擎，benchmark 永远要在自己 workload 上跑。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q7: KV Cache 量化收益与风险？</div>
<div class="qa-a">
<p><strong>核心：</strong>显存换精度。</p>
<div class="qa-section"><div class="qa-section-title">收益</div><p>BF16→FP8 KV 显存减半，可翻倍 batch 或上下文长度；H100 attention kernel 原生支持 FP8。</p></div>
<div class="qa-section"><div class="qa-section-title">风险</div><p>长上下文（&gt;32k）累计误差放大；数学/代码任务敏感；动态范围大的层要 per-token / per-channel scale。</p></div>
<div class="qa-section"><div class="qa-section-title">工程要点</div><p>校准集覆盖目标分布；和 weight 量化一起评估；上线前用业务评测集卡精度回归。</p></div>
<div class="qa-summary">FP8 KV 是当前性价比最高的显存优化之一，但要做精度回归。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q8: MoE 推理瓶颈？EP 怎么部署？</div>
<div class="qa-a">
<p><strong>核心：</strong>路由不均 + all-to-all 通信。</p>
<div class="qa-section"><div class="qa-section-title">瓶颈</div><p>① 路由不均，热门专家拖累整 batch；② all-to-all 跨机带宽是上限；③ 显存 — 专家多激活少，纯 TP 让 GEMM 太小。</p></div>
<div class="qa-section"><div class="qa-section-title">部署</div><p>Attention 用 DP+TP，FFN/MoE 用 EP；DeepSeek-V3 671B 用 Attention DP=32 + EP=32。DeepEP 用 NVLink+IB 混合 all-to-all 比 NCCL 快 3x。</p></div>
<div class="qa-section"><div class="qa-section-title">优化</div><p>专家亲和路由、训练时 aux loss 均衡、热点专家冗余副本、计算与通信 overlap。</p></div>
<div class="qa-summary">MoE serving 是 2025-2026 AI Infra 核心战场，DeepSeek/Qwen/Mixtral 推动 EP 成熟。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q9: TTFT 高怎么排查？</div>
<div class="qa-a">
<p><strong>核心：</strong>从入口往后逐层切。</p>
<div class="qa-section"><div class="qa-section-title">路径</div><p>① 网关时延（trace 接入层）；② 队列等待（queue depth、是否 waiting）；③ Prefill 时长（输入长度、是否 chunk、是否被抢占）；④ KV 是否重算（recompute）；⑤ Prefix cache 是否命中；⑥ GPU 是否在做别的请求。</p></div>
<div class="qa-section"><div class="qa-section-title">指标</div><p><code>vllm:time_to_first_token_seconds</code>、<code>vllm:request_queue_time_seconds</code>、<code>vllm:num_preemptions_total</code>、<code>vllm:gpu_prefix_cache_hit_rate</code>。</p></div>
<div class="qa-summary">TTFT 排查 = 队列 + prefill + 抢占 + 缓存命中四件事。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q10: vLLM preempt-by-recompute vs preempt-by-swap？</div>
<div class="qa-a">
<p><strong>核心：</strong>显存不够时怎么腾位置。</p>
<div class="qa-section"><div class="qa-section-title">Recompute</div><p>丢 KV，恢复时重跑 prefill。简单、不占 CPU 内存；长 prompt 重算贵。</p></div>
<div class="qa-section"><div class="qa-section-title">Swap</div><p>KV 拷到 CPU pinned memory，恢复时拷回。长 prompt 友好；PCIe 带宽是瓶颈，CPU 内存要够。</p></div>
<div class="qa-section"><div class="qa-section-title">选择</div><p>短 prompt 高吞吐用 recompute；长 prompt 低抢占率用 swap；vLLM 默认 recompute。</p></div>
<div class="qa-summary">理解状态机就理解了 vLLM 调度器一半。</div>
</div>
</div>

<div class="card card-m">
<h3>面试自查清单</h3>
<p>① PagedAttention 块管理与 CoW；② Continuous batching 状态机；③ Chunked prefill 与 PD 分离的取舍；④ Prefix cache / RadixAttention 命中机制；⑤ 投机解码原理与变体；⑥ TP/PP/EP/SP 切分与通信开销；⑦ KV 量化的精度风险；⑧ MoE 路由与 all-to-all 优化；⑨ vLLM scheduler 状态机与 preemption 策略；⑩ FlashAttention v3 在 H100 上的关键优化（warp specialization、TMA、async）；⑪ CUDA Graphs 在 decode step 的收益；⑫ 服务化指标体系与 SLO 分解；⑬ 千卡集群的请求路由、KV 迁移、容灾。</p>
</div>

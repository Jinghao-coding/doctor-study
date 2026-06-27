## 一句话结论

端到端推理链路要从用户请求进入服务开始，一直讲到 token 流式返回和资源释放。自回归推理是 GPT 类语言模型的基本范式，Transformer 提供 Attention 和 FFN 的计算骨架：先 Prefill 并行读完整 Prompt（compute-bound），再 Decode 逐 token 生成（memory-bound）。

<h3>完整推理链路概览</h3>
<p>一个 prompt 从输入到输出，大体会经历 <strong>6 个阶段</strong>。核心本质是：模型先并行"读懂"整段输入，建立上下文状态和 KV cache，然后再进入自回归生成循环，每次只预测下一个 token。</p>

<img src="../../../resources/images/llm-inference/e2e-inference-pipeline.svg" alt="LLM 端到端推理链路" style="width:100%;max-width:960px;margin:12px 0 20px 0;border-radius:8px;" loading="lazy"/>

```flow
① 请求封装 | 组织 system/user/assistant 消息 + generation params
② Tokenization | BPE/tiktoken 分词 → token IDs + BOS/EOS/chat template
③ 推理调度 | 排队、优先级、Continuous Batching、KV Cache 预算、Chunked Prefill
④ Prefill | 并行处理完整 prompt，建立初始 KV Cache → compute-bound → TTFT
⑤ Decode | 逐 token 自回归循环，持续更新 KV Cache → memory-bound → TPOT
⑥ 采样返回 | greedy/top-k/top-p 采样 → detokenize → SSE/WebSocket 流式输出
```

<div class="card card-m">
<h3>核心定位：为什么推理是"两阶段"而不是"一阶段"？</h3>
<table>
<tr><th>维度</th><th>Prefill</th><th>Decode</th></tr>
<tr><td><strong>输入规模</strong></td><td>N 个 prompt tokens 一次性并行</td><td>每步只有 <strong>1 个</strong>新 token</td></tr>
<tr><td><strong>计算特性</strong></td><td>大矩阵乘法 (GEMM)，GPU SM 利用率高</td><td>小矩阵乘 + 大 KV Cache 读取</td></tr>
<tr><td><strong>瓶颈类型</strong></td><td><strong>Compute-bound</strong>（吃算力）</td><td><strong>Memory-bound</strong>（吃显存带宽）</td></tr>
<tr><td><strong>关键指标</strong></td><td>TTFT（首 token 延迟）</td><td>TPOT（单 token 生成延迟）</td></tr>
<tr><td><strong>算术强度</strong></td><td>高（O(N) 计算 / O(N) 数据）</td><td>低（O(1) 计算 / O(N) 数据读取）</td></tr>
<tr><td><strong>优化重点</strong></td><td>FlashAttention、Tensor Core 利用</td><td>PagedAttention、Continuous Batching、量化</td></tr>
</table>
</div>

<h3>第一阶段：请求封装与 Tokenization</h3>
<p>用户输入的自然语言并不是模型真正看到的内容。服务层会先把 system、user、assistant 等多轮消息按固定模板组织起来，补上特殊标记。随后，文本经过 tokenizer（如 BPE 算法的 tiktoken），被切成 token 序列。对模型来说，一切输入都是 token IDs，不是"句子"。</p>

<h3>第二阶段：推理调度层</h3>
<p>请求到达后不会立刻进入 GPU，而是先进入推理服务框架（如 vLLM、TGI）。它们负责：</p>
<ul>
<li>请求排队与优先级管理</li>
<li>动态 batching（continuous batching）</li>
<li>KV 缓存管理</li>
<li>流式返回</li>
</ul>
<p>从系统视角看：用户输入 → prompt 模板展开 → tokenization → 请求调度/batching → 送入模型。vLLM 架构至少有 1 个 API server 负责 HTTP 和 tokenization，1 个 engine core 负责 scheduler 和 KV cache 管理，N 个 GPU worker 执行前向计算。</p>

<div class="card card-s">
<h3>Continuous Batching（动态批处理/连续批处理）：推理吞吐的核心来源</h3>
<p>传统 <strong>Static Batching</strong>：等一批请求都到齐了才一起推理，这一批中所有请求都生成结束后才接入下一批。问题是"等最慢的请求"——短请求被长请求拖尾，GPU 在等待期间空闲。</p>
<p><strong>Continuous Batching（ORCA 论文提出，vLLM/TensorRT-LLM 标配）</strong>：不以"请求"为粒度确定 batch，而以 <strong>iteration（一次前向步）</strong> 为粒度。每个 iteration 结束后，scheduler 检查：</p>
<ol>
<li>哪些请求刚完成 generation（吐出 EOS 或达到 max_tokens）→ 释放其 KV Cache，从 batch 中移除</li>
<li>队列中是否有新请求在等待 → 可以立即加入下一个 iteration 的 batch（不需要等其他请求完成）</li>
<li>KV Cache 剩余显存是否足够接纳新请求</li>
</ol>
<p><strong>本质</strong>：iteration-level 的"有出有进"，把 batch 组成变成一个动态集合而非一次性冻结集合。这使得 GPU 不需要在请求边界等待，Decode 阶段的 GPU 利用率大幅提升（从 10-30% 提升到 70%+）。</p>
<table>
<tr><th>对比维度</th><th>Static Batching</th><th>Continuous Batching</th></tr>
<tr><td>batch 确定时机</td><td>请求进入时一次性确定</td><td>每个 iteration 后重新调整</td></tr>
<tr><td>新请求插入</td><td>必须等当前 batch 全部完成</td><td>下一个 iteration 即可插入</td></tr>
<tr><td>GPU 利用率</td><td>低（等待 + 尾部效应）</td><td>高（持续填充 batch）</td></tr>
<tr><td>预emption/抢占</td><td>无</td><td>支持（KV Cache 换出/重计算）</td></tr>
<tr><td>实现复杂度</td><td>简单</td><td>需要精细的 KV Cache 管理</td></tr>
</table>
<div class="qa-summary">记忆要点：Static Batching 是"批大小固定，等所有人交卷再换下一批"；Continuous Batching 是"每个 step 后动态调整——做完的走，排队的进"，类似流水线而非批量生产。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Tokenization 属于 Transformer 前向推理的一部分吗？</div>
<div class="qa-a"><p>严格来说，tokenization 不属于 Transformer 前向推理本身——模型只接收 input_ids。但在现代推理服务中，tokenizer 往往和 serving 引擎绑定在一起，工程上看起来像是推理引擎在处理原始字符串。vLLM 同时支持 text prompt 和 pre-tokenized prompt，两种模式都能跑。</p></div>
</div>

<h3>第三阶段：Embedding 与位置编码</h3>
<p>Token IDs 进入模型后，第一步是 <strong>embedding lookup</strong>——每个 token 查一张巨大的 embedding 表，得到高维向量表示。此时模型才真正进入连续空间的数值计算。</p>
<p>仅有 token 向量还不够，模型还需知道"谁在前、谁在后"。现代大模型通常使用 <strong>RoPE（Rotary Position Embedding）</strong>，把位置信息融入 attention 计算，让模型在处理 token 时同时保留相对位置信息。</p>

<h3>第四阶段：Transformer Block 内部计算</h3>
<p>一个典型的 decoder-only LLM，每一层做两件事：</p>
<ol>
<li><strong>Self-Attention</strong>：当前位置的 token 查看上下文中哪些 token 最相关。模型把隐藏状态投影成 Q、K、V 三组向量，通过 Q 和 K 的相似度算出注意力权重，再对 V 加权求和。<strong>Causal mask</strong> 确保当前位置只能看到自己和前面的 token，不能偷看未来——这决定了模型天然是自回归生成的。</li>
<li><strong>FFN / MLP</strong>：对每个 token 的表示单独做非线性变换，进一步提纯和增强特征，不跨位置交互。</li>
</ol>
<p>可以粗略理解：<strong>Attention 负责"从上下文搬运信息"，FFN 负责"对当前位置做进一步加工"</strong>。中间配合残差连接和归一化。</p>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Q、K、V 的直觉理解？</div>
<div class="qa-a"><p>Q = 我现在想找什么；K = 每个词身上的"索引标签"；V = 每个词真正携带的信息。类比图书馆检索：你的问题是 Q，书架上每本书的标签是 K，书里的内容是 V。先拿 Q 和所有 K 比较，相关度高的那些 V 被更多取出来，合成当前步该看的信息。Transformer 论文对 attention 的定义，本质上就是"一个 query 对一组 key-value 对做匹配，输出是 values 的加权和"。</p></div>
</div>

<h3>第五阶段：Prefill——读完 Prompt</h3>
<p>Prefill 阶段把整段 prompt 一次性跑完整个前向过程，为所有 token 计算各层隐藏状态，并生成后续 decode 要用到的 KV cache。这一步可以高度并行，因为整段输入已经完整给定，GPU 能把很多矩阵操作一起做完。Prefill 更像"先整体读题"，吞吐通常更高，属于 <strong>compute-bound</strong> 阶段。</p>

<h3>第六阶段：Decode——逐 token 生成</h3>
<p>Prefill 完成后，模型取最后一个位置的隐藏状态，通过输出层映射成整个词表上的 logits（下一个 token 的打分），再经 softmax 和解码策略决定输出。常见解码策略：</p>
<table>
<tr><th>策略</th><th>方式</th><th>特点</th></tr>
<tr><td>Greedy</td><td>选概率最大的 token</td><td>确定性输出，缺乏多样性</td></tr>
<tr><td>Top-k</td><td>从概率最高的 k 个中采样</td><td>控制候选范围</td></tr>
<tr><td>Top-p（nucleus）</td><td>从累积概率达 p 的最小集合中采样</td><td>动态调整候选数</td></tr>
<tr><td>Temperature</td><td>调整 softmax 温度</td><td>高温更随机，低温更确定</td></tr>
</table>
<p>随后进入循环：把刚生成的 token 接到上下文后面 → 复用 KV cache → 只为新 token 跑一遍前向 → 得到新的 logits → 再生成下一个 token。这就是大模型回答总是一个 token 一个 token 流式吐出来的原因。</p>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么"第一个字慢，后面快"？</div>
<div class="qa-a"><p>Prefill 更偏 compute-bound，可以把整段输入并行做大矩阵乘法，吃满 GPU 算力；Decode 更偏 memory-bound，每步只算一个 token，但强依赖历史 KV cache，频繁访问显存，步骤间有严格顺序依赖。所以工程上需要 FlashAttention、continuous batching、chunked prefill / Paged Attention 等优化来提升推理效率。</p></div>
</div>

<h3>推理引擎与模型本体的职责划分</h3>
<table>
<tr><th>职责方</th><th>负责内容</th></tr>
<tr><td>推理引擎 / serving 系统</td><td>接 HTTP 请求、tokenization / 输入处理、调度 batching、管理 KV cache、协调 GPU worker、流式返回、采样与系统优化</td></tr>
<tr><td>LLM 模型本体</td><td>对 input_ids 做 embedding，经多层 Transformer block 的 self-attention 和 FFN，输出 logits（下一个 token 的分数分布）</td></tr>
</table>
<p><strong>推理引擎决定"怎么高效地跑"，模型决定"到底生成什么"。</strong>前者偏"编排与优化"，后者偏"语义计算与内容生成"。</p>

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

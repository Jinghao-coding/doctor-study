## 一句话结论

端到端推理链路要从用户请求进入服务开始，一直讲到 token 流式返回和资源释放。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | LLM 推理系统 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕请求生命周期、Prefill/Decode、KV Cache、Attention 优化、Serving Engine 和性能瓶颈建立系统化面试答案。 |
| 面试抓手 | 面试时按阶段讲，不要直接跳到 Transformer 公式。 |

<h3>完整推理链路概览</h3>
<p>一个 prompt 从输入到输出，大体会经历 <strong>6 个阶段</strong>。核心本质是：模型先并行"读懂"整段输入，建立上下文状态和 KV cache，然后再进入自回归生成循环，每次只预测下一个 token。</p>

```flow
请求封装 | 组织 system、user、assistant 消息和生成参数
Tokenization | 把自然语言切成模型可读的 token IDs
推理调度 | 排队、优先级、continuous batching、KV Cache 预算
Prefill | 并行处理完整 prompt，建立初始 KV Cache
Decode | 逐 token 自回归生成，并持续更新 KV Cache
反解码返回 | 采样、detokenize，并通过流式接口返回
```

<p>这种"自回归 + 不做本次梯度更新"的推理方式，正是 GPT 类语言模型的基本范式；而 Transformer 则提供了它内部 attention 和前馈网络的计算骨架。</p>

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

## 面试回答

**30 秒版：**

端到端推理链路要从用户请求进入服务开始，一直讲到 token 流式返回和资源释放。 面试时按阶段讲，不要直接跳到 Transformer 公式。

**2 分钟版：**

一个 prompt 从输入到输出大体经历 6 个阶段：请求封装、tokenization、推理调度、prefill、decode、反解码返回。我会按阶段讲：服务层先把 system/user/assistant 消息按模板组织好，经 tokenizer（如 BPE 的 tiktoken）切成 token IDs；请求进推理框架（vLLM/TGI）排队、做 continuous batching、管 KV cache；进模型后先 embedding lookup 加 RoPE，再过多层 Transformer block 的 self-attention（Q/K/V 加 causal mask）和 FFN。prefill 把整段 prompt 并行跑完、建立 KV cache，偏 compute-bound；decode 取最后位置 logits 经采样逐 token 生成、复用 KV cache，偏 memory-bound。这也是"第一个字慢、后面快"的原因，工程上靠 FlashAttention、continuous batching、chunked prefill 优化。职责上推理引擎决定"怎么高效跑"，模型决定"生成什么"。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

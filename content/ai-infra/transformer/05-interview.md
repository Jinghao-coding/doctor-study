## 一句话结论

Transformer 面试要把架构、Attention、复杂度、训练稳定和推理系统连接起来。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Transformer 与大模型基础 |
| 章节类型 | 面试收束类 |
| 解决问题 | 围绕 Transformer 架构、输入表示、Attention、训练稳定性和面试高频题建立大模型基础答案。 |
| 面试抓手 | 用可展开问答和追问表收束。 |

<div class="card card-r">
<h3>Transformer 面试高频题</h3>
<p>把前面知识点压缩成可背诵的问答，点击展开。先盖住答案自己说一遍，再对照。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 介绍一下 Transformer 的整体结构。</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">两大部分</div><p><strong>Encoder</strong> 处理输入序列输出上下文表示，每层 = Multi-Head Self-Attention + Feed Forward，子层都带残差和 Layer Norm。<strong>Decoder</strong> 处理目标序列输出预测，每层 = Masked Self-Attention（防止看未来）+ Encoder-Decoder Cross-Attention（交叉注意力）+ Feed Forward，同样带残差和 Layer Norm。</p></div>
<div class="qa-section"><div class="qa-section-title">额外组件</div><p>最前端是 Tokenizer + Embedding + 位置编码，最末端是 Linear + Softmax 输出层。</p></div>
<div class="qa-summary">核心一句：纯注意力架构，抛弃 RNN/CNN，靠 Self-Attention 做 token 间交互、FFN 做单 token 加工，残差+归一化让深层可训练。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Embedding 是什么，它在什么位置？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">是什么</div><p>文本先由 Tokenizer 切成 token，按词表映射成整数 input_ids。模型维护一个可学习的 Embedding 矩阵 <code>[vocab_size, hidden_size]</code>，<strong>用 token id 查表</strong>取出对应行向量，就得到 token 向量。本质是查表，不是矩阵乘。</p></div>
<div class="qa-section"><div class="qa-section-title">位置</div><p>在模型最前端，紧跟 Tokenizer 之后、第一个 Transformer block 之前，之后还要加上位置编码。</p></div>
<div class="qa-summary">Embedding = 一张可训练的查找表，把离散 token id 翻译成稠密向量。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么要位置编码？好处是什么？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">为什么</div><p>Transformer 不用 RNN 结构，而是一次性看全局、所有 token 并行计算。Attention 本身对顺序不敏感（打乱输入只是结果跟着换位），无法利用单词顺序信息。所以要用位置编码把顺序补回来。</p></div>
<div class="qa-section"><div class="qa-section-title">好处</div><p>保存单词在序列中的<strong>绝对或相对位置</strong>，让模型能区分词序不同导致的语义差异，并建模 token 之间的相对距离。</p></div>
<div class="qa-summary">主流方案：原文正弦余弦、BERT 可学习位置编码、LLaMA 的 RoPE 旋转位置编码（外推性好）。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Tokenizer 是怎么做的？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">流程</div><p>用 BPE / WordPiece 等算法把连续文本切成更小的单元（token），可以是整词、词根、词缀甚至单字。然后在预构建的词表里查每个 token，映射成唯一的整数编号（token id）。一段文本就变成一串 token id，成为模型输入。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么用子词</div><p>整词词表会爆炸且无法处理生词（OOV），单字序列太长语义太碎。子词是折中：常见词当整体、罕见词拆词根词缀，既控制词表大小又能处理生词。</p></div>
<div class="qa-summary">BPE：合并高频字符对；WordPiece：合并最大化似然的字符对；SentencePiece：不依赖空格，适合中文/多语言。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Self-Attention 的计算流程？为什么要除以 √d_k？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">流程</div><p>每个 token 投影出 Q、K、V；用 Q 和所有 K 点积得相关性分数，除以 <code>√d_k</code> 缩放后 softmax 成权重；用权重对所有 V 加权求和。公式 <code>softmax(Q·Kᵀ/√d_k)·V</code>。</p></div>
<div class="qa-section"><div class="qa-section-title">为什么除以 √d_k</div><p>维度大时点积数值会很大，softmax 进入梯度极小的饱和区，会导致梯度消失。除以 √d_k 把方差拉回来，稳定梯度。</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Multi-Head 和 Single-Head 的区别？Multi-Head 好在哪？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">区别</div><p>Single-Head 只在一个空间算一次注意力；Multi-Head 把 hidden_size 拆成多个并行子空间，每个 head 独立算注意力再拼接过输出投影。<strong>总维度不变，所以参数量和计算量基本一样</strong>，只是切开算。</p></div>
<div class="qa-section"><div class="qa-section-title">好处</div><ul><li>多角度建模：每个头关注不同子空间特征（语法、语义、位置）。</li><li>表达能力更强：能同时捕获更丰富的依赖。</li><li>并行性好：多头之间天然并行。</li></ul></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Attention 和 Feed Forward 各自的作用？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">Attention</div><p>在 token 之间做信息交互，捕获序列依赖关系——「谁该关注谁」，做的是<strong>混合/通信</strong>。</p></div>
<div class="qa-section"><div class="qa-section-title">Feed Forward</div><p>对每个 token 独立做非线性变换，提升表达能力，承担<strong>「知识存储」</strong>作用，做的是加工/记忆。</p></div>
<div class="qa-summary">比喻：Attention 是「开会交换信息」，FFN 是「会后各自消化加工」。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 手撕 Multi-Head Attention 时，KV cache 和 causal mask 各起什么作用？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">KV cache</div><p>自回归生成时，前面 token 的 K/V 不变，缓存下来避免重复计算，每步只算新 token 的 Q 和它的 K/V，再 cat 到历史后面。是推理加速的关键。</p></div>
<div class="qa-section"><div class="qa-section-title">causal mask</div><p>给「未来位置」加一个极大负数（<code>mask * -1e9</code>），softmax 后这些位置权重≈0，实现「只能看到自己和左边、不能偷看未来」。</p></div>
<div class="qa-section"><div class="qa-section-title">易错点</div><p>合并多头前必须 <code>contiguous()</code>，因为 transpose 后内存不连续，直接 view 会报错。</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 大模型怎么处理梯度消失和梯度爆炸？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">六个手段</div><ul><li><strong>残差连接：</strong>梯度有直通车直达浅层，最关键。</li><li><strong>LayerNorm / RMSNorm：</strong>稳定每层激活分布。</li><li><strong>合理初始化（Xavier/Kaiming）：</strong>保持各层方差一致。</li><li><strong>梯度裁剪：</strong>梯度范数超阈值就缩小，防爆炸。</li><li><strong>学习率 warmup + decay：</strong>避免训练初期发散。</li><li><strong>混合精度 + Loss Scaling：</strong>解决 FP16 梯度下溢。</li></ul></div>
<div class="qa-summary">金句：残差连接把「乘法传播」变成「加法传播」，<code>y=x+F(x)</code> 的梯度是 <code>1+F'(x)</code>，那个 1 保证梯度不衰减。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 NLP 用 LayerNorm 而不是 BatchNorm？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">原因</div><p>BatchNorm 对 batch 内同一特征归一化，依赖 batch 统计量。NLP 里序列长度可变、batch 可能很小，batch 统计不稳定。LayerNorm 对单个样本的所有特征归一化，<strong>不依赖 batch</strong>，对每个 token 独立做，更适合变长序列。</p></div>
<div class="qa-summary">RMSNorm 是 LayerNorm 的简化版（只做均方根缩放、不减均值），更快、效果相当，LLaMA 等主流大模型在用。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Encoder-only、Decoder-only、Encoder-Decoder 有什么区别？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">三种</div><ul><li><strong>Encoder-only（BERT）：</strong>双向注意力，擅长理解类任务（分类、抽取）。</li><li><strong>Decoder-only（GPT/LLaMA）：</strong>单向因果注意力，擅长生成，当前主流大模型。</li><li><strong>Encoder-Decoder（原始 Transformer / T5）：</strong>两半都有，擅长翻译、摘要等 seq2seq。</li></ul></div>
<div class="qa-summary">现在说「大模型」基本默认 Decoder-only：靠因果掩码自回归地一个一个 token 往外吐。</div>
</div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

<div class="card card-m">
<h3>输入处理三件套：从文字到向量</h3>
<p>模型不能直接吃文字，必须先把文字变成数字向量。整条链路是：</p>
<p><strong>文本 →（Tokenizer）→ token →（查词表）→ input_ids →（Embedding 查表）→ 词向量 →（+ 位置编码）→ 送入第一层</strong></p>
<div class="qa-summary">记住顺序：Tokenizer 切词 → Embedding 查表变向量 → 加位置编码 → 进 Transformer block。</div>
</div>

<div class="card card-s">
<h3>1. Tokenizer：怎么把文本切成 token</h3>
<p>Tokenizer 用特定算法（如 <strong>BPE</strong> 或 <strong>WordPiece</strong>）把连续文本切成更小的单元——token。token 可以是完整单词、词根、词缀，甚至单个字符。然后在预先构建的<strong>词表（vocab）</strong>里查每个 token，映射成唯一的整数编号（token id）。最终一段文本变成一串 token id 序列，这才是模型的真正输入。</p>
<table>
<tr><th>算法</th><th>核心思想</th><th>代表模型</th></tr>
<tr><td>BPE（Byte Pair Encoding）</td><td>从字符开始，反复合并出现频率最高的相邻字符对，直到词表达到设定大小</td><td>GPT 系列</td></tr>
<tr><td>WordPiece</td><td>和 BPE 类似，但合并时选「能最大提升语言模型似然」的字符对</td><td>BERT</td></tr>
<tr><td>SentencePiece</td><td>不依赖空格分词，直接在原始字节流上做，适合中文/多语言</td><td>LLaMA、T5</td></tr>
</table>
<p><strong>为什么不直接用单词或单字？</strong>用整词：词表会爆炸，且遇到没见过的词（OOV）就歇菜；用单字：序列太长、语义颗粒太碎。子词（subword）是折中：常见词当整体，罕见词拆成词根词缀，既控制词表大小又能处理生词。</p>
</div>

<div class="card card-d">
<h3>2. Embedding：是什么、在哪里</h3>
<p>模型维护一个<strong>可学习的 Embedding 矩阵</strong>，形状是 <code>[vocab_size, hidden_size]</code>。每个 token id 对应矩阵的一行。所谓 Embedding 就是<strong>用 token id 去这个矩阵里查表（取出对应那一行向量）</strong>。</p>
<ul>
<li><strong>位置：</strong>在模型最前端，紧跟 Tokenizer 之后、第一个 Transformer block 之前。</li>
<li><strong>本质：</strong>就是一次查表（lookup），不是矩阵乘法。把离散的整数 id 变成稠密的连续向量。</li>
<li><strong>可学习：</strong>这个矩阵是模型参数，训练中会被反向传播更新，语义相近的词向量会逐渐靠近。</li>
</ul>
<div class="qa-summary">Embedding = 一张可训练的查找表，把 token id 翻译成模型能理解的向量。</div>
</div>

<div class="card card-w">
<h3>3. 位置编码：为什么需要、好处是什么</h3>
<p><strong>为什么需要：</strong>Transformer 不像 RNN 那样一个一个按顺序处理，而是<strong>一次性看全局、所有 token 并行计算</strong>。Attention 本身是「无序」的——打乱输入顺序，算出来的结果只是跟着换位置，模型分不清「猫追狗」和「狗追猫」。所以必须额外注入位置信息，让模型知道每个 token 在序列中的<strong>绝对或相对位置</strong>。</p>
<p><strong>好处：</strong></p>
<ul>
<li>保留单词在序列中的<strong>顺序信息</strong>，让模型能区分词序不同导致的语义差异。</li>
<li>让模型有能力建模<strong>相对距离</strong>（谁离谁近、谁在前谁在后）。</li>
</ul>
<table>
<tr><th>方案</th><th>做法</th><th>特点</th></tr>
<tr><td>正弦/余弦（原文）</td><td>用不同频率的 sin/cos 函数算出固定位置向量，和 Embedding 相加</td><td>不用学习、可外推到更长序列</td></tr>
<tr><td>可学习位置编码</td><td>像 Embedding 一样维护一张可训练的位置向量表</td><td>BERT 用，简单但难外推到训练没见过的长度</td></tr>
<tr><td>RoPE（旋转位置编码）</td><td>通过旋转 Q/K 向量来编码相对位置</td><td>LLaMA 等主流大模型在用，外推性好</td></tr>
</table>
<div class="qa-summary">面试答法：因为 Transformer 用全局并行计算、没有 RNN 的天然顺序，Attention 本身对位置不敏感，所以要用位置编码把顺序信息补回来。</div>
</div>

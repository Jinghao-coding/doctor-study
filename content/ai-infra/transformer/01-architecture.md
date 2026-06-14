<div class="card card-m">
<h3>一句话先记住</h3>
<p>Transformer 是 2017 年论文 <strong>《Attention is All You Need》</strong> 提出的序列建模架构。它<strong>抛弃了 RNN/CNN</strong>，完全用 <strong>注意力机制（Attention）</strong> 来建模序列中任意两个位置之间的关系，因此可以<strong>高度并行</strong>、能建模<strong>长距离依赖</strong>。它是现在所有大模型（GPT、BERT、LLaMA）的共同底座。</p>
<div class="qa-summary">面试开场可以这样答：Transformer 是一个基于纯注意力的序列模型，分 Encoder 和 Decoder 两部分，靠 Self-Attention 做 token 之间的信息交互，靠 FFN 做单 token 的非线性变换，配合残差和归一化使深层网络可训练。</div>
</div>

<div class="card card-s">
<h3>整体结构：Encoder + Decoder</h3>
<p>原始 Transformer 是为<strong>机器翻译</strong>设计的，所以有两半：左边 Encoder 读源语言句子，右边 Decoder 生成目标语言句子。</p>
<table>
<tr><th>部分</th><th>作用</th><th>内部结构（每层重复 N 次，原文 N=6）</th></tr>
<tr><td>Encoder</td><td>处理输入序列，输出每个 token 的<strong>上下文表示</strong></td><td>Multi-Head Self-Attention + Feed Forward，每个子层都带 Residual + Layer Norm</td></tr>
<tr><td>Decoder</td><td>处理已生成的目标序列，输出下一个 token 的预测</td><td>Masked Self-Attention + Encoder-Decoder Cross-Attention + Feed Forward，每个子层都带 Residual + Layer Norm</td></tr>
</table>
</div>

<div class="card card-d">
<h3>一层 Encoder Layer 里有什么</h3>
<ol>
<li><strong>Multi-Head Self-Attention</strong>：让每个 token 看其它所有 token，做信息交互。</li>
<li><strong>残差连接 + Layer Norm</strong>：<code>x = LayerNorm(x + Attention(x))</code>。</li>
<li><strong>Feed Forward（FFN）</strong>：两层全连接 + 激活，对每个 token 独立做非线性变换。</li>
<li><strong>残差连接 + Layer Norm</strong>：<code>x = LayerNorm(x + FFN(x))</code>。</li>
</ol>
<p>记忆口诀：<strong>「注意力 → 加&归一 → 前馈 → 加&归一」</strong>，一层就这四步。</p>
</div>

<div class="card card-w">
<h3>一层 Decoder Layer 多了什么</h3>
<p>Decoder 比 Encoder 每层多一个注意力子层，所以是<strong>三个子层</strong>：</p>
<ol>
<li><strong>Masked Multi-Head Self-Attention</strong>：自注意力，但加了 <strong>因果掩码（causal mask）</strong>，保证位置 i 只能看到 i 及之前的 token，<strong>不能偷看未来</strong>（否则训练时就作弊了）。</li>
<li><strong>Encoder-Decoder Cross-Attention（交叉注意力）</strong>：Query 来自 Decoder，Key/Value 来自 Encoder 的输出，让生成时能「参考」源句子。</li>
<li><strong>Feed Forward</strong>：同 Encoder。</li>
</ol>
<div class="qa-summary">关键区别：Encoder 双向（能看全句），Decoder 自注意力是单向（只能看左边），还多一个 Cross-Attention 去对齐源句子。</div>
</div>

<div class="card card-s">
<h3>额外组件（首尾）</h3>
<table>
<tr><th>组件</th><th>位置</th><th>作用</th></tr>
<tr><td>Tokenizer</td><td>最前端</td><td>把文本切成 token，再映射成整数 input_ids</td></tr>
<tr><td>Embedding</td><td>token 之后、第一层之前</td><td>查表把每个 token id 变成稠密向量</td></tr>
<tr><td>Positional Encoding</td><td>和 Embedding 相加</td><td>注入位置信息（因为 Attention 本身无序）</td></tr>
<tr><td>Output Layer（Linear + Softmax）</td><td>最末端</td><td>把最后一层的向量投影到词表大小，输出每个词的概率</td></tr>
</table>
</div>

<div class="card card-d">
<h3>三种主流架构变体（一定要会区分）</h3>
<p>现在大模型很少用完整的 Encoder-Decoder，更多是只取一半：</p>
<table>
<tr><th>类型</th><th>代表模型</th><th>结构</th><th>擅长</th></tr>
<tr><td>Encoder-only</td><td>BERT</td><td>只有 Encoder，双向注意力</td><td>理解类任务：分类、抽取、句子表示</td></tr>
<tr><td>Decoder-only</td><td>GPT、LLaMA</td><td>只有 Decoder，单向（因果）注意力</td><td>生成类任务：对话、续写（当前主流）</td></tr>
<tr><td>Encoder-Decoder</td><td>原始 Transformer、T5</td><td>两半都有</td><td>翻译、摘要等 seq2seq 任务</td></tr>
</table>
<div class="qa-summary">现在说「大模型」基本默认是 <strong>Decoder-only</strong>：输入和输出拼在一起，靠因果掩码自回归地一个一个 token 往外吐。</div>
</div>

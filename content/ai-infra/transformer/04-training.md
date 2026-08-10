<div class="card card-m">
<h3>先搞懂：什么是梯度消失/爆炸</h3>
<p>深层网络靠反向传播更新参数，梯度要从最后一层「逐层相乘」传回最前面。</p>
<ul>
<li><strong>梯度消失：</strong>每层梯度都小于 1，连乘后越传越小，最后趋近 0 → 浅层参数几乎不更新，学不动。</li>
<li><strong>梯度爆炸：</strong>每层梯度都大于 1，连乘后越传越大 → 参数剧烈震荡、loss 变 NaN，训练发散。</li>
</ul>
<p>大模型层数很深（几十上百层），这个问题尤其严重，所以需要一整套技术来稳住训练。</p>
</div>

<div class="card card-s">
<h3>大模型怎么处理（六个手段，按重要性记）</h3>
<table>
<tr><th>手段</th><th>解决什么</th><th>原理</th></tr>
<tr><td>残差连接（Residual）</td><td>梯度消失</td><td><code>y = x + F(x)</code>，梯度有一条「直通车」绕过 F 直达浅层，不会被连乘衰减</td></tr>
<tr><td>LayerNorm / RMSNorm</td><td>激活值不稳定</td><td>对每层激活做归一化，稳定分布，让梯度幅度可控</td></tr>
<tr><td>合理初始化（Xavier/Kaiming）</td><td>初始梯度过大/过小</td><td>让各层输入输出的方差保持一致，避免一开始就消失或爆炸</td></tr>
<tr><td>梯度裁剪（Gradient Clipping）</td><td>梯度爆炸</td><td>梯度范数超过阈值就等比例缩小，硬性封顶</td></tr>
<tr><td>学习率 warmup + decay</td><td>训练初期发散</td><td>先用小学习率慢慢升（warmup），再逐渐衰减，避免一开始步子太大</td></tr>
<tr><td>混合精度 + Loss Scaling</td><td>FP16 梯度下溢</td><td>FP16 表示范围小，小梯度会变 0；把 loss 乘大再算梯度，更新前再除回来</td></tr>
</table>
</div>

<div class="card card-d">
<h3>残差连接为什么最关键</h3>
<p>残差是 Transformer 能堆几十层的<strong>头号功臣</strong>。反向传播时 <code>y = x + F(x)</code> 的梯度是 <code>1 + F'(x)</code>，那个常数 <strong>1</strong> 保证了即使 <code>F'(x)</code> 很小，梯度也不会衰减到 0——相当于给梯度修了一条<strong>高速公路</strong>，可以直通传回浅层。</p>
<div class="qa-summary">面试金句：残差连接把「乘法传播」变成了「加法传播」，从根本上缓解了梯度消失。</div>
</div>

<div class="card card-w">
<h3>LayerNorm vs BatchNorm vs RMSNorm</h3>
<table>
<tr><th>方法</th><th>归一化维度</th><th>为什么用在这</th></tr>
<tr><td>BatchNorm</td><td>对一个 batch 内同一特征归一化</td><td>依赖 batch 统计量，序列长度可变、batch 小的时候不稳定，<strong>NLP 一般不用</strong></td></tr>
<tr><td>LayerNorm</td><td>对单个样本的所有特征归一化</td><td>不依赖 batch，对每个 token 独立做，<strong>原始 Transformer 用</strong></td></tr>
<tr><td>RMSNorm</td><td>只用均方根缩放，不减均值</td><td>比 LayerNorm 少算一步、更快，效果相当，<strong>LLaMA 等主流大模型用</strong></td></tr>
</table>
<p>另外还有 <strong>Pre-Norm vs Post-Norm</strong>：原文是 Post-Norm（先残差后归一），现代大模型多用 <strong>Pre-Norm</strong>（先归一再进子层，<code>x + F(LN(x))</code>），训练更稳定、更容易收敛。</p>
</div>

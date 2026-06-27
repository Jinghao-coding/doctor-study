## 一句话结论

Self-Attention 用 Q/K/V 计算 token 间相关性，Multi-Head 则让不同 head 学不同关系子空间。
<div class="card card-m">
<h3>Self-Attention：核心三步</h3>
<p>注意力的本质是<strong>「加权求和」</strong>：每个 token 输出 = 其它所有 token 的 value 的加权平均，权重由「我和你有多相关」决定。</p>
<ol>
<li>每个 token 投影出三个向量：<strong>Q（Query，我要找什么）、K（Key，我能提供什么）、V（Value，我的实际内容）</strong>。</li>
<li>用 Q 和所有 K 做点积得到相关性分数，除以 <code>√d_k</code> 缩放，再 softmax 归一化成权重。</li>
<li>用权重对所有 V 加权求和，得到这个 token 的新表示。</li>
</ol>
<p>公式：</p>
<div class="formula">$$
\operatorname{Attention}(Q,K,V)
= \operatorname{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right)V
$$</div>
<div class="qa-summary">为什么要除以 √d_k？因为维度大时点积数值会很大，softmax 会进入梯度极小的饱和区，缩放是为了稳定梯度。</div>
</div>

<div class="card card-s">
<h3>Multi-Head vs Single-Head：区别和好处</h3>
<p>Single-Head 只在一个空间里算一次注意力。Multi-Head 把 hidden_size 拆成多个并行的子空间（head），<strong>每个 head 独立算一次注意力，再把结果拼接起来过一个输出投影</strong>。</p>
<table>
<tr><th>维度</th><th>Single-Head</th><th>Multi-Head</th></tr>
<tr><td>建模角度</td><td>只能学一种关注模式</td><td>每个头学不同模式（语法、语义、位置…）</td></tr>
<tr><td>表达能力</td><td>较弱</td><td>能捕获更丰富的依赖关系</td></tr>
<tr><td>计算成本</td><td>差不多（总维度不变，只是拆开算）</td><td>差不多，且天然可并行</td></tr>
</table>
<p><strong>Multi-Head 的好处：</strong></p>
<ul>
<li><strong>多角度建模：</strong>每个头关注不同子空间特征，类似 CNN 里的多个卷积核。</li>
<li><strong>表达能力更强：</strong>相比单头能同时捕获多种依赖。</li>
<li><strong>并行性好：</strong>多个头之间互不依赖，天然并行。</li>
</ul>
<div class="qa-summary">注意：拆成多头不增加总参数量和计算量——总维度 hidden_size 是固定的，只是切成 num_heads 份分别算。</div>
</div>

<h3>手撕 Multi-Head Attention（带 KV Cache）</h3>

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class MultiHeadAttention(nn.Module):
    def __init__(self, hidden_size, num_heads):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.q_linear = nn.Linear(hidden_size, hidden_size)
        self.k_linear = nn.Linear(hidden_size, hidden_size)
        self.v_linear = nn.Linear(hidden_size, hidden_size)
        self.o_linear = nn.Linear(hidden_size, hidden_size)

    def forward(self, hidden_state, causal_mask=None,
                past_key_value=None, use_cache=False):
        batch_size = hidden_state.size(0)
        query = self.q_linear(hidden_state)
        key   = self.k_linear(hidden_state)
        value = self.v_linear(hidden_state)

        # 多头拆分: [B, S, H] -> [B, num_heads, S, head_dim]
        query = query.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        key   = key.view(batch_size,   -1, self.num_heads, self.head_dim).transpose(1, 2)
        value = value.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)

        # 拼接 KV cache: 把历史的 key/value 接到前面
        if past_key_value is not None:
            past_key, past_value = past_key_value
            key   = torch.cat([past_key,   key],   dim=2)
            value = torch.cat([past_value, value], dim=2)

        new_past_key_value = (key, value) if use_cache else None

        # 注意力打分 + 缩放
        attention_scores = torch.matmul(query, key.transpose(-1, -2)) \
                           / torch.sqrt(torch.tensor(self.head_dim, dtype=torch.float32))

        # 因果掩码: 把不能看的位置加上一个极大负数, softmax 后趋近 0
        if causal_mask is not None:
            attention_scores += causal_mask * -1e9

        attention_probs = F.softmax(attention_scores, dim=-1)
        output = torch.matmul(attention_probs, value)

        # 合并多头: [B, num_heads, S, head_dim] -> [B, S, H]
        output = output.transpose(1, 2).contiguous() \
                       .view(batch_size, -1, self.num_heads * self.head_dim)
        output = self.o_linear(output)

        return (output, new_past_key_value) if use_cache else output
```

<div class="card card-w">
<h3>手撕代码逐段讲解（面试要能口述）</h3>
<ul>
<li><strong>四个 Linear：</strong>q/k/v 把输入投影成查询、键、值；o_linear 是多头拼接后的输出投影。</li>
<li><strong>view + transpose：</strong>把 <code>[B, S, hidden]</code> 切成 <code>[B, num_heads, S, head_dim]</code>，让每个头独立算。<code>transpose(1,2)</code> 是为了把 head 维提到前面，方便 batch 矩阵乘。</li>
<li><strong>KV cache：</strong>自回归生成时，前面 token 的 K/V 不变，缓存下来避免重复计算，每步只算新 token 的 Q。这是推理加速的关键。</li>
<li><strong>除以 √head_dim：</strong>缩放点积，防止 softmax 饱和、梯度消失。</li>
<li><strong>causal_mask * -1e9：</strong>给「未来位置」加一个极大负数，softmax 后这些位置权重≈0，实现「不能看未来」。</li>
<li><strong>合并多头：</strong>transpose 回来、contiguous（保证内存连续）、view 拼回 hidden_size，最后过 o_linear。</li>
</ul>
<div class="qa-summary">易错点：<code>contiguous()</code> 不能省——transpose 后内存不连续，直接 view 会报错。</div>
</div>

<div class="card card-d">
<h3>Attention vs Feed Forward：各自的作用</h3>
<table>
<tr><th>模块</th><th>作用</th><th>一句话</th></tr>
<tr><td>Attention</td><td>在 <strong>token 之间</strong>做信息交互，捕获序列依赖关系</td><td>「谁该关注谁」——做<strong>混合/通信</strong></td></tr>
<tr><td>Feed Forward (FFN)</td><td>对<strong>每个 token 独立</strong>做非线性变换，提升表达能力</td><td>承担<strong>「知识存储」</strong>，做<strong>加工/记忆</strong></td></tr>
</table>
<p>形象比喻：Attention 是「开会，大家交换信息」；FFN 是「会后各自回去消化、加工」。一层 Transformer 就是「交流一次 + 各自加工一次」。研究还发现大模型的事实知识大量存储在 FFN 层里。</p>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

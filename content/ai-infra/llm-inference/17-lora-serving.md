## 一句话结论

LoRA 通过低秩矩阵分解 BA（r ≪ d）以 ~0.1%~1% 的参数量高效微调模型；多 LoRA Serving 的核心是让所有请求共享一份 base model 权重，在 GPU 显存中同时驻留多个适配器，用 Batched GEMV/GEMM 高效计算 LoRA 增量 Y = X·B·A，S-LoRA/Punica 通过异构批处理、Tucker 分解、分层存储和专用 BGMV kernel 实现数百个 LoRA 的高效并发服务。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | LLM 推理系统 |
| 章节类型 | 机制+系统设计类 |
| 解决问题 | LoRA 原理、多租户场景下的 LoRA 服务化架构、Punica/S-LoRA 核心设计、LoRA 显存管理、vLLM 多 LoRA 实践 |
| 面试抓手 | 讲清"为什么 LoRA 能 work（低秩本质）"和"多 LoRA serving 怎么高效批处理（BGMV、共享 base、分层存储）" |

<div class="card card-m">
<h3>LoRA 基础：低秩适配的原理</h3>
<p>全参数微调需要更新模型的所有参数，代价高昂。LoRA（Low-Rank Adaptation）基于一个关键假设：<strong>模型微调前后的权重变化是低秩的</strong>——即 ΔW = W_finetuned - W_pretrained 可以用低秩矩阵乘积很好地近似。</p>
<p>具体做法：</p>
<ul>
<li>冻结预训练模型权重 $W \in \mathbb{R}^{d \times d}$（或 $d_{in} \times d_{out}$）</li>
<li>添加两个可训练矩阵 $B \in \mathbb{R}^{d \times r}$，$A \in \mathbb{R}^{r \times d}$，其中秩 $r \ll d$（通常 r=8~64）</li>
<li>前向传播：$h = W x + BAx$（或写成 $h = Wx + \frac{\alpha}{r} BAx$，其中 α 是缩放因子）</li>
<li>训练时只更新 A 和 B，原始 W 保持冻结</li>
</ul>

<div class="pa-fig">
<svg viewBox="0 0 640 220" role="img" aria-label="LoRA 低秩分解示意图：W + BA">
<text x="20" y="28" class="pa-title">LoRA: 冻结原始权重 W，低秩增量 BA 旁路</text>

<rect x="40" y="80" width="160" height="60" class="pa-slot" rx="4"></rect>
<text x="120" y="115" text-anchor="middle" class="pa-mono" fill="var(--sec-h)">W (d×d, 冻结)</text>

<rect x="250" y="60" width="70" height="40" class="pa-blk-a" rx="4"></rect>
<text x="285" y="85" text-anchor="middle" class="pa-mono">B (d×r)</text>
<rect x="330" y="120" width="70" height="40" class="pa-blk-b" rx="4"></rect>
<text x="365" y="145" text-anchor="middle" class="pa-mono">A (r×d)</text>

<text x="200" y="115" text-anchor="middle" class="pa-mono">x →</text>
<path d="M200,110 L250,110" stroke="var(--txt-3)" stroke-width="1.5" fill="none" marker-end="url(#faArrow)"></path>
<path d="M200,110 L250,80" stroke="var(--txt-3)" stroke-width="1.5" fill="none"></path>
<path d="M320,80 L330,120" stroke="var(--txt-3)" stroke-width="1.5" fill="none" marker-end="url(#faArrow)"></path>

<text x="320" y="100" text-anchor="middle" class="pa-sub">α/r</text>

<rect x="450" y="80" width="140" height="60" class="pa-slot-sram" rx="4"></rect>
<text x="520" y="105" text-anchor="middle" class="pa-mono" fill="var(--sec-h)">h = Wx + (α/r)·BAx</text>
<text x="520" y="125" text-anchor="middle" class="pa-sub" fill="var(--sec-h)">（推理时可合并: W' = W + BA·α/r）</text>

<path d="M400,110 L450,110" stroke="var(--txt-3)" stroke-width="1.5" fill="none" marker-end="url(#faArrow)"></path>
<path d="M200,110 L250,140" stroke="var(--txt-3)" stroke-width="1.5" fill="none" opacity="0"></path>

<text x="20" y="190" class="pa-sub">r ≪ d：A 和 B 参数量是 2·d·r，远小于 d²（如 d=4096, r=64 时，只有原始权重的 ~3%）。</text>
<text x="20" y="208" class="pa-sub">推理时可将 BA 合并进 W 消除额外计算，但多 LoRA serving 时通常不合并（保留灵活性）。</text>
</svg>
</div>

<p><strong>Alpha 缩放</strong>：$\frac{\alpha}{r}$ 是一个常数缩放因子，通常固定 α=r（即初始缩放为 1），这样改变 r 时不需要重新调学习率。</p>
<p><strong>应用位置</strong>：LoRA 最常用于 attention 层的 Q、K、V、O 投影矩阵，也有人应用于 MLP 层或所有线性层。通常只对 attention 层加 LoRA 就足够（~0.1% 参数量）。</p>
</div>

<div class="card card-m">
<h3>为什么多 LoRA Serving 是刚需</h3>
<p>在多租户（multi-tenant）LLM 服务场景下：</p>
<ul>
<li><strong>不同客户有不同任务</strong>：客服对话、代码补全、法律摘要、医疗问答、创意写作……每个任务都有自己微调的 LoRA 适配器</li>
<li><strong>不可能为每个 LoRA 单独部署一份模型</strong>：70B 模型 FP16 要 140GB 显存，100 个 LoRA 就需要 14TB 显存，完全不现实</li>
<li><strong>所有 LoRA 共享同一个 base model</strong>：它们只是在同一个基础模型上微调了不同的小适配器，99%+ 的权重是相同的</li>
</ul>
<p>这就催生了多 LoRA serving 的核心设计问题：<strong>如何让一份 base model 同时服务于多个 LoRA 适配器的请求，最大化 GPU 利用率和吞吐？</strong></p>

<div class="qa-summary">核心思路：base model 权重共享驻留 GPU，LoRA 适配器按热度在 GPU/CPU/磁盘间分层存储，批处理时高效计算每个请求对应的 LoRA 增量。</div>
</div>

<div class="card card-s">
<h3>LoRA Serving 架构演进</h3>
<table>
<tr><th>方案</th><th>做法</th><th>优点</th><th>缺点</th></tr>
<tr><td>1. Naive：每个 LoRA 独立部署</td><td>每个 LoRA 各加载一份完整模型</td><td>实现简单，隔离性好</td><td>显存爆炸（N×model_size），资源利用率极低，冷启动慢</td></tr>
<tr><td>2. 合并 LoRA（Merge）</td><td>把 LoRA 权重合并进 base 模型 W' = W + BA/α</td><td>无运行时开销，单模型最优性能</td><td>合并是永久性的（无法快速卸载）；每个活跃 LoRA 一份完整权重，仍然不支持多 LoRA 并发</td></tr>
<tr><td>3. 共享 base + Batched LoRA（Punica/S-LoRA）</td><td>GPU 常驻 base model，多个 LoRA 适配器同时加载，请求按 LoRA 分组批处理</td><td>显存大幅节省（base + N×adapter_size），支持多 LoRA 并发</td><td>需要专用 kernel 支持，批处理调度复杂</td></tr>
<tr><td>4. LoRA Fusion（LoRAX）</td><td>运行时融合多个 LoRA，通过 learned routing 组合多个适配器效果</td><td>支持一次请求组合多个 LoRA 能力</td><td>需要额外训练 routing，研究阶段为主</td></tr>
</table>
<p>现代生产系统（vLLM、TensorRT-LLM、S-LoRA、Punica）都采用方案 3：共享 base model + 多 LoRA 并发。</p>
</div>

<div class="card card-d">
<h3>Punica：Batched GEMV (BGMV) Kernel</h3>
<p>Punica 是第一个系统性解决多 LoRA serving 问题的工作，它的核心贡献是 <strong>BGMV（Batched Gather Matrix-Vector multiplication）kernel</strong>。</p>

<p><strong>问题</strong>：一个 batch 里有多个请求，每个请求对应不同的 LoRA 适配器。普通 GEMM 假设 batch 中所有样本用相同权重，但多 LoRA 场景下每个样本的 B 和 A 矩阵不同。</p>
<p><strong>计算分解</strong>：LoRA 的增量计算可以分解为两步：
$$y_{\text{LoRA}} = x \cdot B_i \cdot A_i$$
其中 $B_i$ 和 $A_i$ 是第 i 个请求对应的 LoRA 矩阵。这等价于：先计算 $x \cdot B_i$（每个请求独立的 GEMV），再乘以 $A_i$（再一次 GEMV）。</p>
<p><strong>BGMV 的核心思想</strong>：</p>
<ul>
<li>把多个 LoRA 的 B 矩阵（和 A 矩阵）在显存中连续排列，形成一个"堆叠"的权重池</li>
<li>对于一个 batch 内的请求，每个 warp 负责一个请求的 LoRA 计算</li>
<li>用 <strong>gather</strong> 操作从堆叠的权重池中<strong>索引</strong>出当前请求对应的 B_i/A_i，而不是所有请求共享同一份权重</li>
<li>避免了"按 LoRA 分组 batch"的限制，不同 LoRA 的请求可以在同一个 CUDA kernel 中高效并行计算</li>
</ul>

```cpp
// BGMV 核心直觉（伪代码）
__global__ void bgmv_kernel(
    float* Y, const float* X,
    const float* stacked_B,  // 所有 LoRA 的 B 矩阵连续存储: [num_loras, d, r]
    const int* lora_indices,  // 每个请求对应的 LoRA ID
    int batch_size, int d, int r)
{
    int req = blockIdx.x;  // 每个 block 处理一个请求
    int lora_id = lora_indices[req];
    const float* B_i = stacked_B + lora_id * d * r;  // gather: 索引到当前请求的 B
    // ... 执行 GEMV: y[req] = X[req] @ B_i @ A_i
}
```

<p>BGMV 的意义：让"一个 batch 混合不同 LoRA 的请求"成为可能，不需要把相同 LoRA 的请求凑在一起才能批处理，大幅提升调度灵活性和 GPU 利用率。</p>
</div>

<div class="card card-m">
<h3>S-LoRA：服务数千 LoRA 的系统设计</h3>
<p>S-LoRA 在 Punica 基础上做了更系统的工程设计，目标是单机服务<strong>数千个</strong> LoRA 适配器。核心设计有四点：</p>

<h4>1. Heterogeneous Batching（异构批处理）</h4>
<p>不同 LoRA 请求的 rank r 可能不同（有的 r=8，有的 r=64），有的请求可能同时挂载多个 LoRA。S-LoRA 不要求 batch 内 homogeneity，而是设计了能处理不同 rank、不同 LoRA 组合的通用 kernel。</p>

<h4>2. Unified Paging for KV Cache</h4>
<p>结合 PagedAttention 的思想，KV cache 的分页管理<strong>不区分 LoRA 归属</strong>——所有 LoRA 请求的 KV cache 共享同一个物理 block pool。这和单模型 serving 的 PagedAttention 一致，确保显存不会因为 LoRA 多样性而碎片化。</p>

<h4>3. Optimized LoRA Kernel（Tucker 分解）</h4>
<p>S-LoRA 观察到 LoRA 计算的主要瓶颈是 $X \cdot B$（因为 X 是 [batch, seq, d]，B 是 [d, r]）。它用 <strong>Tucker 分解</strong>把低秩矩阵乘进一步分解：
$$B \cdot A \approx U \cdot S \cdot V^T$$
并融合多个 kernel，减少访存次数。相比朴素 LoRA 计算，Tucker 分解在高 rank 时能额外减少 20%~40% 的计算。</p>

<h4>4. Hierarchical Adapter Management（分层适配器管理）</h4>
<p>GPU 显存装不下数千个 LoRA 时：</p>
<ul>
<li><strong>Hot adapters（热）</strong>：当前在处理请求的 LoRA，驻留 GPU 显存</li>
<li><strong>Warm adapters（温）</strong>：GPU 显存有余量时预取最近使用过的 LoRA，减少加载延迟</li>
<li><strong>Cold adapters（冷）</strong>：放在 CPU RAM，请求到来时通过 PCIe 异步传输到 GPU（prefetch）</li>
<li><strong>Frigid adapters（冻）</strong>：放在 SSD/磁盘，需要时才加载到 CPU 内存</li>
</ul>
<p>配合<strong>预取</strong>（prefetching）策略：当请求队列中出现某个冷 LoRA 时，提前将其权重从 CPU 传输到 GPU，隐藏 PCIe 传输延迟。</p>
</div>

<div class="card card-s">
<h3>多 LoRA 批处理的计算模型</h3>
<p>在多 LoRA 场景下，一个 transformer 层的计算分为两部分：</p>
<ul>
<li><strong>Base 计算（共享）</strong>：$Y_{\text{base}} = X \cdot W$，所有请求共享同一个 W，可以用标准 GEMM 高效计算，这部分占主要计算量</li>
<li><strong>LoRA 增量（不共享）</strong>：$Y_{\text{lora}}^{(i)} = X^{(i)} \cdot B_i \cdot A_i$，每个请求用自己的 $B_i, A_i$，需要用 BGMV 或类似的 batched kernel</li>
<li><strong>输出</strong>：$Y^{(i)} = Y_{\text{base}}^{(i)} + \frac{\alpha}{r_i} Y_{\text{lora}}^{(i)}$</li>
</ul>
<p>关键洞察：<strong>Base 计算量远大于 LoRA 增量计算量</strong>——即使有几十上百个 LoRA，LoRA 的额外开销（因为 r ≪ d）只有 base 的几个百分点。所以多 LoRA serving 的主要代价不是计算，而是<strong>LoRA 权重加载和调度</strong>。</p>

```python
# 多 LoRA 批处理的伪代码
def forward_batch(batch_requests):
    # 1. 所有请求共享 base model 计算
    X = gather_inputs(batch_requests)  # [total_tokens, d_model]
    Y_base = X @ W_base                # 大 GEMM，共享权重，这是主要计算

    # 2. 按 LoRA 分组，分别计算 LoRA 增量
    Y_lora = zeros_like(Y_base)
    for lora_id, indices in group_by_lora(batch_requests):
        B, A, alpha_r = get_lora_weights(lora_id)
        X_sub = X[indices]
        Y_lora[indices] = X_sub @ B @ A * alpha_r  # BGMV/BGM 处理不同 LoRA

    # 3. 合并输出 + LayerNorm + Attention（base 和 LoRA 增量相加后继续标准计算）
    Y = Y_base + Y_lora
    return Y
```
</div>

<div class="card card-w">
<h3>实际工程问题</h3>
<table>
<tr><th>问题</th><th>说明</th></tr>
<tr><td>Rank 选择</td><td>r 越大表达能力越强但参数量越大；r=8~64 是常见范围，简单任务 r=8 就够，复杂任务 r=64。可以通过奇异值分析选 r。</td></tr>
<tr><td>Alpha/r 比例</td><td>通常设 α=r，让初始化时 LoRA 增量的缩放为 1，避免改变原始输出分布；推理时 α/r 作为常数合并进 B/A 即可。</td></tr>
<tr><td>多 LoRA 混合</td><td>有些场景需要同时叠加多个 LoRA（如一个"代码风格"LoRA + 一个"中文"LoRA），可以做加权和：ΔW = Σ w_i · B_i A_i。vLLM 支持 LoRA 线性组合。</td></tr>
<tr><td>Tokenizer 一致性</td><td>不同 LoRA 必须使用和 base model 相同的 tokenizer。如果某些 LoRA 添加了 special tokens，需要扩展 embedding 层并在加载 LoRA 时一并加载。</td></tr>
<tr><td>Adapter 版本管理</td><td>LoRA 权重依赖特定的 base model 版本（不同 checkpoint 或不同量化方式），版本不匹配会导致精度严重下降。</td></tr>
<tr><td>LoRA 合并时机</td><td>离线合并（W' = W + BA/α）可以消除运行时开销，但失去多 LoRA 灵活性；在线不合并更灵活但需要 BGMV kernel。热 LoRA 可以临时合并进权重矩阵加速（warm merge），冷 LoRA 走 BGMV。</td></tr>
</table>
</div>

<div class="card card-d">
<h3>vLLM 多 LoRA 支持</h3>
<p>vLLM 从 v0.3 开始支持多 LoRA 服务，关键配置和机制：</p>
<ul>
<li><strong>动态 LoRA 加载/卸载</strong>：通过 <code>--enable-lora</code> 开启，请求可以通过 API 指定 LoRA 适配器名称/路径</li>
<li><strong>配置参数</strong>：
  <ul>
    <li><code>--max-lora-rank</code>：支持的最大 LoRA rank（决定预分配的显存空间）</li>
    <li><code>--max-loras</code>：GPU 上同时驻留的最大 LoRA 数量</li>
    <li><code>--max-cpu-loras</code>：CPU 内存中缓存的最大 LoRA 数量</li>
    <li><code>--lora-dtype</code>：LoRA 权重的数据类型（默认 auto，与 base model 一致）</li>
  </ul>
</li>
<li><strong>LoRA Manager</strong>：管理 LoRA 适配器的生命周期，维护 GPU 显存中的 LoRA 权重池，LRU 策略驱逐冷 LoRA，从 CPU 预取温 LoRA</li>
<li><strong>批处理策略</strong>：相同 LoRA 的请求优先聚合成 batch，但也支持混合 LoRA batch（通过 BGMV 风格的 kernel）</li>
</ul>

```python
# vLLM 启动多 LoRA 服务的示例命令
# python -m vllm.entrypoints.openai.api_server \
#     --model meta-llama/Llama-2-7b-hf \
#     --enable-lora \
#     --max-lora-rank 64 \
#     --max-loras 10 \
#     --max-cpu-loras 50
```

```python
# vLLM API 请求中指定 LoRA
import openai
client = openai.Client(base_url="http://localhost:8000/v1")
response = client.chat.completions.create(
    model="meta-llama/Llama-2-7b-hf",
    messages=[{"role": "user", "content": "写一段 Python 排序代码"}],
    extra_body={"lora": "code-lora-v1"}  # 指定 LoRA 适配器
)
```

<p>TensorRT-LLM 也支持多 LoRA 服务，kernel 优化更激进，通常吞吐更高但灵活性略低。</p>
</div>

<div class="card card-r">
<h3>常见误区</h3>
<ul>
<li><strong>误区 1：LoRA 只是微调技巧</strong>——LoRA 不只是训练技术，它在推理服务中也扮演重要角色：低秩增量让"一个 base model 服务多个微调版本"在显存上可行。</li>
<li><strong>误区 2：多 LoRA Serving 就是把多个 LoRA 加起来</strong>——不是简单的权重加法，核心挑战是<strong>系统级的高效批处理、显存管理和调度</strong>，BGMV kernel 和分层存储才是关键。</li>
<li><strong>误区 3：r 越大越好</strong>——r 越大 LoRA 参数量越大、显存开销越大、BGMV 计算越慢；存在收益递减点，多数任务 r=8~16 已足够。</li>
<li><strong>误区 4：用 LoRA 就必须把 BA 合并进 W</strong>——合并是推理优化选项之一，多 LoRA serving 场景下通常不合并，保留 W 不变才能共享 base model。</li>
<li><strong>误区 5：LoRA 只能加在 Q/V 投影</strong>——早期工作只用 Q/V，后来发现加在 Q/K/V/O 和 MLP 上效果更好，但参数量也相应增加。生产中通常根据效果和开销权衡。</li>
</ul>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: LoRA 为什么用低秩矩阵？为什么微调的权重变化是低秩的？</div>
<div class="qa-a"><p>LoRA 的核心假设是：预训练模型在适配下游任务时，权重变化 ΔW = W_finetuned - W_pretrained 本质上是"低秩"的——即模型适配新知识不需要在所有权重方向上都做大幅度调整，只需要在少数几个关键方向上更新。这个假设有几方面支撑：(1) 实证观察：对微调后的权重做 SVD 分解，发现大部分奇异值非常小，只有少数几个方向上有显著变化，top 几个奇异值就能解释大部分变化；(2) 内在维度理论：论文 "Intrinsic Dimensionality" 指出模型适配只需要一个低维子空间；(3) 过度参数化视角：大模型本身参数冗余度极高，下游任务可用远比模型维度低的自由度来适配。因此用两个小矩阵 BA（总参数量 2·d·r ≪ d²）就可以表达这些关键方向的更新，同时保持原始权重冻结，大幅减少训练显存和参数量。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 多 LoRA Serving 怎么高效批处理？</div>
<div class="qa-a"><p>核心是"共享 base，分离 LoRA"：(1) 所有请求共享一次 base model 的 forward pass，即大 GEMM Y_base = X @ W，这是计算的主力，和单 LoRA 或无 LoRA 一样高效；(2) LoRA 增量部分 Y_lora = X @ B_i @ A_i 对每个请求使用不同的 B_i 和 A_i，需要专门的 batched kernel 处理——Punica 提出的 BGMV（Batched Gather Matrix-Vector multiplication）把多个 LoRA 的权重在显存中连续堆叠，每个 block/warp 负责一个请求，通过 gather 索引找到对应权重，在一个 kernel 内高效完成不同 LoRA 的计算；(3) 同 LoRA 的请求可以聚在一起用标准 GEMM 计算（比 BGMV 更高效），不同 LoRA 的请求用 BGMV 混合处理；(4) S-LoRA 进一步用 Tucker 分解优化 LoRA 计算，用异构批处理支持不同 rank 的 LoRA，用统一分页管理 KV cache。最终效果是：一次前向传播中混合多个 LoRA 的请求，base 计算完全共享，LoRA 增量开销只有几个百分点。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Punica 的 BGMV kernel 解决什么问题？</div>
<div class="qa-a"><p>BGMV 解决的核心问题是：当一个 batch 里包含不同 LoRA 的请求时，如何高效计算每个请求各自的 LoRA 增量 X·B_i·A_i。在标准 GEMM/GEMV 中，batch 内所有样本共享同一个权重矩阵，GPU 通过 tiling 和共享内存重用权重来实现高吞吐。但多 LoRA 场景下每个请求的 B_i/A_i 不同，无法直接用标准 GEMM。朴素做法是把相同 LoRA 的请求凑在一起，凑不够 batch size 就浪费算力——这严重限制了调度灵活性和 GPU 利用率。BGMV 的做法：(1) 把所有 LoRA 的 B（和 A）矩阵在显存中连续排列成一个大的权重张量 stack；(2) 每个 CUDA block 处理一个请求，通过请求对应的 LoRA ID 做 gather 索引到自己的 B_i/A_i；(3) 这样不同 LoRA 的请求可以在同一个 kernel 中并行计算，不需要同 LoRA 凑 batch。代价是权重无法在请求间共享（每个请求用不同的 B_i），但因为 r 很小（LoRA 矩阵本身不大），且 base 计算（主要开销）已经共享，整体仍然高效。BGMV 本质是"gather + 多个小 GEMV"的融合 kernel。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: LoRA 和全参数微调的效果差多少？</div>
<div class="qa-a"><p>在大多数下游任务上，经过调优的 LoRA（合适的 rank、目标模块、训练超参）效果可以接近或匹配全参数微调，差距通常在 1%~3% 以内。具体取决于：(1) 任务和 base model 的匹配度——如果下游任务和预训练数据分布差异大（如用通用 base model 微调医疗领域），LoRA 可能略逊于全参数微调；差异小则差距更小；(2) LoRA 的配置——rank 足够大（r=64 或更高）、应用到更多层（包括 MLP）时差距更小；(3) 数据量——数据量少时 LoRA 甚至可能比全参数微调更好（因为参数少，不容易过拟合）；大数据量上全参数微调有更多容量去适应。优势方面，LoRA 训练快 2~4 倍（只算梯度和更新小矩阵），显存占用大幅降低（不需要保存大多数参数的优化器状态），且天然适合多任务服务化（多个 LoRA 共享一个 base model）。生产中绝大多数定制化场景都用 LoRA 而非全参数微调。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: vLLM 怎么管理多个 LoRA 适配器的显存？</div>
<div class="qa-a"><p>vLLM 通过 LoRA Manager 实现分层管理，核心机制：(1) 显存预留：启动时根据 --max-lora-rank 和 --max-loras 在 GPU 上预分配一块 LoRA 权重池（workspace），避免运行时动态分配导致碎片；(2) 热 LoRA 驻留 GPU：当前 batch 中正在使用的 LoRA 权重必须在 GPU 显存中，直接参与 BGMV 计算；(3) 冷 LoRA 在 CPU：不在使用的 LoRA 权重保存在 CPU RAM（--max-cpu-loras 控制数量），使用 LRU 策略驱逐；(4) 预取（Prefetching）：当等待队列中出现某个 CPU 上的 LoRA 请求时，在 GPU 处理当前 batch 的同时通过 PCIe 异步将该 LoRA 传输到 GPU workspace，隐藏传输延迟；(5) LRU 驱逐：GPU workspace 满了之后，驱逐最久未使用的 LoRA 权重释放空间；(6) KV cache 不区分 LoRA：所有 LoRA 请求的 KV cache 统一用 PagedAttention 管理，在同一个 block pool 中分配。这种分层管理让 vLLM 可以在有限 GPU 显存下同时服务数十到上百个不同的 LoRA 适配器。</p></div>
</div>

## 关联模块

- `02-request-lifecycle.md`：请求在推理引擎中的完整生命周期，LoRA 选择发生在请求进入时。
- `05-kv-cache-attention.md`：S-LoRA 的 unified paging 建立在 PagedAttention 之上。
- `08-serving-engines.md`：vLLM、TensorRT-LLM 对多 LoRA 的支持情况。
- `design/10-multi-model-llm-serving.md`：多模型服务是更广义的问题，多 LoRA 是其中多租户的一个子场景。
- `design/11-kv-cache-system.md`：KV cache 管理策略，LoRA 请求共享 KV cache pool。

<div class="card card-m">
<h3>ZeRO / FSDP：把训练状态从“每卡完整保存”变成“分片保存”</h3>
<p>大模型训练的显存不仅被参数占用，还被梯度、优化器状态和激活值占用。ZeRO 和 FSDP 的核心都是将训练状态分片，降低每张 GPU 的显存压力；代价是前向/反向时需要更多通信来取回参数或同步分片。</p>
</div>

<div class="card card-s">
<h3>训练显存组成</h3>
<table>
<tr><th>组成</th><th>常见 dtype</th><th>每参数字节数</th><th>说明</th></tr>
<tr><td>模型参数</td><td>FP16/BF16</td><td>2</td><td>forward/backward 使用</td></tr>
<tr><td>梯度</td><td>FP16/FP32</td><td>2 或 4</td><td>优化器更新需要</td></tr>
<tr><td>Adam 一阶矩</td><td>FP32</td><td>4</td><td>momentum</td></tr>
<tr><td>Adam 二阶矩</td><td>FP32</td><td>4</td><td>variance</td></tr>
<tr><td>Master weights</td><td>FP32</td><td>4</td><td>混合精度训练常见</td></tr>
</table>
<p>常见估算会把 Adam 训练状态近似为：</p>
<div class="formula">Training State ≈ Parameters(2B) + Gradients(4B) + Adam States(12B) = 18 bytes / parameter</div>
</div>

<div class="card card-d">
<h3>ZeRO 阶段对比</h3>
<table>
<tr><th>阶段</th><th>分片对象</th><th>显存节省</th><th>通信变化</th><th>典型选择</th></tr>
<tr><td>ZeRO-1</td><td>优化器状态</td><td>中等</td><td>接近 DP</td><td>低风险节省显存</td></tr>
<tr><td>ZeRO-2</td><td>优化器状态 + 梯度</td><td>较大</td><td>接近 DP</td><td>常用甜点</td></tr>
<tr><td>ZeRO-3</td><td>参数 + 梯度 + 优化器状态</td><td>最大</td><td>额外参数 AllGather</td><td>模型极大时使用</td></tr>
<tr><td>FSDP</td><td>参数 shard + 按需 all-gather</td><td>接近 ZeRO-3</td><td>与 wrapping 策略强相关</td><td>PyTorch 原生生态</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 7B 模型，4 卡，用 ZeRO-1/2/3 每卡训练状态显存怎么估算？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说明每参数字节数，再按分片对象分别计算。</p>
<div class="qa-section"><div class="qa-section-title">1. 无 ZeRO</div><p>按每参数 18 bytes 估算：</p><div class="formula">7B × 18 bytes = 126 GB / GPU</div><p>每卡都保存完整训练状态，A100 80GB 放不下。</p></div>
<div class="qa-section"><div class="qa-section-title">2. ZeRO-1</div><p>只切 Adam 优化器状态，参数和梯度仍完整保存：</p><div class="formula">7B × (12 / 4 + 4 + 2) = 63 GB / GPU</div></div>
<div class="qa-section"><div class="qa-section-title">3. ZeRO-2</div><p>切优化器状态和梯度：</p><div class="formula">7B × (12 / 4 + 4 / 4 + 2) = 42 GB / GPU</div></div>
<div class="qa-section"><div class="qa-section-title">4. ZeRO-3</div><p>参数、梯度、优化器状态都切：</p><div class="formula">7B × (12 / 4 + 4 / 4 + 2 / 4) = 31.5 GB / GPU</div></div>
<div class="qa-summary">面试口径：ZeRO 的本质是分片训练状态，ZeRO-2 常是性价比甜点，ZeRO-3 显存最省但通信更重。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: FSDP 和 ZeRO-3 是什么关系？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先讲共同点，再讲 PyTorch FSDP 的实现特点。</p>
<div class="qa-section"><div class="qa-section-title">1. 共同点</div><p>FSDP 和 ZeRO-3 都会把参数、梯度、优化器状态按 data parallel group 分片，前向/反向前按需 all-gather 完整参数，用完后释放。</p></div>
<div class="qa-section"><div class="qa-section-title">2. FSDP 的关键是 wrapping</div><p>FSDP 按 module 包裹粒度决定 all-gather 和释放范围。包得太粗会峰值显存高，包得太细会通信次数多。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 工程差异</div><p>FSDP 是 PyTorch 原生能力，和 autograd/module 生态结合更紧；DeepSpeed ZeRO 提供更完整的 offload、optimizer、配置生态。</p></div>
<div class="qa-summary">面试口径：FSDP 可以理解为 PyTorch 原生的 ZeRO-3 类方案，差异主要在 wrapping 粒度和生态实现。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ZeRO-3 为什么通信更多？什么时候仍然值得用？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>解释参数被分片后必须按需 gather，再说明适用边界。</p>
<div class="qa-section"><div class="qa-section-title">1. 参数不再完整常驻</div><p>ZeRO-3 下每张卡只保存部分参数。某一层 forward/backward 需要完整参数时，需要先 AllGather。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 通信换显存</div><p>相比 ZeRO-2，ZeRO-3 增加参数 AllGather，但显存进一步下降。它是典型的用通信换显存。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 适用场景</div><p>当 ZeRO-2 仍然放不下模型，或者想扩大 batch/seq_len 时，ZeRO-3/FSDP 值得使用；如果 ZeRO-2 已足够，ZeRO-3 不一定更快。</p></div>
<div class="qa-summary">面试口径：ZeRO-3 不是免费午餐，它通过额外参数 AllGather 换取最大显存节省。</div>
</div>
</div>

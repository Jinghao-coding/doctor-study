## 一句话结论

ZeRO/FSDP 的本质是把参数、梯度和优化器状态从每卡完整保存变成分片保存。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 分布式训练 |
| 章节类型 | 机制类（含公式） |
| 解决问题 | 围绕数据并行、张量并行、流水线并行、ZeRO/FSDP、NCCL 和训练排障建立大模型训练系统答案。 |
| 面试抓手 | 显存公式要按 ZeRO 阶段拆。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

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
<div class="formula">$$\text{Training State} \approx \text{Parameters}(2B) + \text{Gradients}(4B) + \text{Adam States}(12B) = 18 \text{bytes} / parameter$$</div>
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
<div class="qa-section"><div class="qa-section-title">1. 无 ZeRO</div><p>按每参数 18 bytes 估算：</p><div class="formula">$$7B \times 18 \text{bytes} = 126 \text{GB} / \text{GPU}$$</div><p>每卡都保存完整训练状态，A100 80GB 放不下。</p></div>
<div class="qa-section"><div class="qa-section-title">2. ZeRO-1</div><p>只切 Adam 优化器状态，参数和梯度仍完整保存：</p><div class="formula">$$7B \times (12 / 4 + 4 + 2) = 63 \text{GB} / \text{GPU}$$</div></div>
<div class="qa-section"><div class="qa-section-title">3. ZeRO-2</div><p>切优化器状态和梯度：</p><div class="formula">$$7B \times (12 / 4 + 4 / 4 + 2) = 42 \text{GB} / \text{GPU}$$</div></div>
<div class="qa-section"><div class="qa-section-title">4. ZeRO-3</div><p>参数、梯度、优化器状态都切：</p><div class="formula">$$7B \times (12 / 4 + 4 / 4 + 2 / 4) = 31.5 \text{GB} / \text{GPU}$$</div></div>
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

## 面试回答

**30 秒版：**

ZeRO/FSDP 的本质是把参数、梯度和优化器状态从每卡完整保存变成分片保存。 显存公式要按 ZeRO 阶段拆。

**2 分钟版：**

我会先说明这个问题在 分布式训练 里的位置，再拆核心链路：输入是什么、系统如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：吞吐和延迟、显存和计算、隔离和利用率、简单实现和生产稳定性之间如何取舍。最后用观测指标或排障路径收束，说明如何判断方案真的有效。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

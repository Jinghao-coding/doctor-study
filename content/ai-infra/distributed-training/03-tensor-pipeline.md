## 一句话结论

张量并行切层内矩阵，流水线并行切层间 stage，两者解决的瓶颈不同。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 分布式训练 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕数据并行、张量并行、流水线并行、ZeRO/FSDP、NCCL 和训练排障建立大模型训练系统答案。 |
| 面试抓手 | TP 看 NVLink，PP 看 bubble。 |

<div class="card card-m">
<h3>张量并行与流水线并行：一个切层内，一个切层间</h3>
<p>张量并行（TP）解决“单层矩阵太大或单层计算太重”的问题；流水线并行（PP）解决“层数太多、整模型放不进单卡”的问题。二者经常组合：TP 放在节点内 NVLink 域，PP 可以跨节点。</p>
</div>

<div class="card card-d">
<h3>TP vs PP 对比</h3>
<table>
<tr><th>维度</th><th>张量并行 TP</th><th>流水线并行 PP</th></tr>
<tr><td>切分对象</td><td>每层矩阵、attention head、MLP 中间维度</td><td>模型层序列</td></tr>
<tr><td>通信模式</td><td>AllGather、ReduceScatter、AllReduce</td><td>相邻 stage Send/Recv</td></tr>
<tr><td>通信频率</td><td>每层多次，频率极高</td><td>每个 micro-batch 跨 stage 传激活/梯度</td></tr>
<tr><td>拓扑要求</td><td>强，优先 NVLink/NVSwitch</td><td>中等，可以跨节点但要减少跳数</td></tr>
<tr><td>主要风险</td><td>跨节点 TP 会极慢</td><td>pipeline bubble 降低利用率</td></tr>
</table>
</div>

<div class="card card-s">
<h3>TP 的矩阵切分直觉</h3>
<p>以线性层 <code>Y = XW</code> 为例，列并行把 W 按输出维度切成多份：</p>
<div class="formula">$$W = [W_1, W_2, ..., W_t]$$</div>
<div class="formula">$$Y_i = XW_i, Y = \operatorname{concat}(Y_1, Y_2, ..., Y_t)$$</div>
<p>行并行则把输入维度切分，局部结果需要 ReduceScatter 或 AllReduce 合并。</p>
</div>

<div class="card card-w">
<h3>PP 的 Bubble 公式</h3>
<p>流水线并行把 batch 切成 m 个 micro-batch，在 p 个 stage 上流动。1F1B 调度下，理想 bubble 比例可近似为：</p>
<div class="formula">$$\text{Bubble Rate} = (p - 1) / (m + p - 1)$$</div>
<p>所以 stage 越多 bubble 越大，micro-batch 越多 bubble 越小。但 micro-batch 数受 global batch size、显存和收敛约束限制。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 TP 一般要求放在同一台机器内？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说明 TP 通信频率高，再比较 NVLink 和跨节点 IB 的带宽/延迟差异。</p>
<div class="qa-section"><div class="qa-section-title">1. TP 每层都通信</div><p>TP 不是每 step 通信一次，而是每一层 forward/backward 都可能 AllGather 或 ReduceScatter。96 层模型一轮训练可能触发数百次集合通信。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 频率比通信量更致命</div><p>跨节点网络不仅带宽低于 NVLink，还会增加延迟。频繁的小/中等消息会被延迟放大。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 放置原则</div><p>通常 TP 度不超过单节点 GPU 数，例如 8×A100 节点上 TP=8，跨节点部分交给 PP 或 DP。</p></div>
<div class="qa-summary">面试口径：TP 是高频层内通信，必须尽量放在 NVLink/NVSwitch 域内；跨节点 TP 通常是性能灾难。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pipeline Bubble 怎么计算？如何降低？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先给公式，再解释 p 和 m 的影响，最后给工程优化手段。</p>
<div class="qa-section"><div class="qa-section-title">1. Bubble 公式</div><p>1F1B 调度下近似：</p><div class="formula">$$\text{Bubble Rate} = (p - 1) / (m + p - 1)$$</div><p>p 是 stage 数，m 是 micro-batch 数。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 例子</div><p>如果 p=4、m=12：</p><div class="formula">$$\text{Bubble Rate} = 3 / (12 + 4 - 1) = 20%$$</div></div>
<div class="qa-section"><div class="qa-section-title">3. 优化方式</div><p>增加 micro-batch、减少 PP stage、使用 interleaved 1F1B、平衡每个 stage 的层数和计算量。</p></div>
<div class="qa-summary">面试口径：PP 的核心开销是 bubble，stage 越多越差，micro-batch 越多越好，但受 batch size 和显存限制。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 32 张 GPU，TP=8、PP=2，那么 DP 是多少？应该如何放置？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先用公式算 DP，再给拓扑放置原则。</p>
<div class="qa-section"><div class="qa-section-title">1. 计算 DP</div><p>总 GPU 数等于三种并行度乘积：</p><div class="formula">$$\text{Total GPUs} = DP \times TP \times PP$$</div><div class="formula">$$DP = 32 / (8 \times 2) = 2$$</div></div>
<div class="qa-section"><div class="qa-section-title">2. 放置方式</div><p>如果每节点 8 卡，则每个 TP group 正好占一台机器；两个 PP stage 占两台机器；DP=2 表示有两条完全相同的 pipeline 副本，总共 4 台机器。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 面试补充</div><p>TP group 内通信走 NVLink，PP stage 间走 IB，DP 同步梯度频率较低，可以跨 pipeline 副本做 AllReduce。</p></div>
<div class="qa-summary">面试口径：DP=总卡数/(TP×PP)，这个例子是 DP=2；TP 放节点内，PP/DP 才跨节点。</div>
</div>
</div>

## 面试回答

**30 秒版：**

张量并行切层内矩阵，流水线并行切层间 stage，两者解决的瓶颈不同。 TP 看 NVLink，PP 看 bubble。

**2 分钟版：**

张量并行和流水线并行解决的瓶颈不同：TP 切层内矩阵，解决单层矩阵太大或单层计算太重；PP 切层间 stage 序列，解决层数太多、整模型放不进单卡。TP 以 Y=XW 为例，列并行把 W 按输出维度切成 [W1...Wt] 各算 Yi 再 concat，行并行切输入维度后用 ReduceScatter/AllReduce 合并；它每层 forward/backward 都要 AllGather 或 ReduceScatter，96 层模型一轮可能触发数百次集合通信，频率比通信量更致命，所以 TP 必须放在节点内 NVLink/NVSwitch 域，TP 度一般不超过单节点 GPU 数，跨节点 TP 是性能灾难。PP 把 batch 切成 m 个 micro-batch 在 p 个 stage 上流动，相邻 stage 只 Send/Recv 激活和梯度，可跨节点；核心开销是 bubble，1F1B 调度下 bubble rate≈(p-1)/(m+p-1)，stage 越多越差、micro-batch 越多越好，但 m 受 global batch 和显存约束。组合时按总 GPU=DP×TP×PP 算，TP 节点内、PP/DP 跨节点。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

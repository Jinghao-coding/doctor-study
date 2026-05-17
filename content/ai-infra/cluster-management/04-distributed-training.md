<div class="card card-m">
<h3>并行策略</h3>
<table>
<tr><th>策略</th><th>切分维度</th><th>通信模式</th><th>适用场景</th></tr>
<tr><td>数据并行（DP）</td><td>数据 batch</td><td>AllReduce 梯度</td><td>模型能放进单卡</td></tr>
<tr><td>张量并行（TP）</td><td>模型层内矩阵</td><td>AllReduce/AllGather</td><td>大矩阵乘法，需要 NVLink</td></tr>
<tr><td>流水线并行（PP）</td><td>模型层间</td><td>P2P Send/Recv</td><td>模型太大放不进单节点</td></tr>
<tr><td>专家并行（EP）</td><td>MoE 专家</td><td>All-to-All</td><td>MoE 模型（Mixtral）</td></tr>
<tr><td>ZeRO（1/2/3）</td><td>优化器状态/梯度/参数</td><td>AllGather + ReduceScatter</td><td>减少显存占用</td></tr>
</table>

<h3>3D 并行</h3>
<p>大模型训练通常组合使用 DP + TP + PP。典型配置（8 节点 × 8 GPU = 64 GPU 训练 175B 模型）：</p>
<ul>
<li>TP = 8（节点内 8 卡 NVLink 互联，通信量大需要高带宽）</li>
<li>PP = 4（跨 4 个节点做流水线，通信量小，可以走 InfiniBand）</li>
<li>DP = 2（两组流水线做数据并行，每个 micro-batch 结束同步梯度）</li>
</ul>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ZeRO 三个阶段分别做了什么？</div>
<div class="qa-a">
<p>训练一个模型需要存储三类数据：优化器状态（如 Adam 的 momentum + variance，每参数 12 字节）、梯度（每参数 4 字节）、模型参数（FP16 每参数 2 字节）。</p>
<ul>
<li><strong>ZeRO-1</strong>：切分优化器状态。每张卡只存 1/N 的优化器状态。省最多内存的部分</li>
<li><strong>ZeRO-2</strong>：切分优化器状态 + 梯度。梯度 reduce 后只保留对应分片</li>
<li><strong>ZeRO-3</strong>：切分优化器状态 + 梯度 + 参数。前向/反向时按需 AllGather 参数，用完释放。通信量最大但内存最省</li>
</ul>
<p>ZeRO-3 + 64 卡可以训练 1T 参数的模型（每卡只存 1/64 参数）。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 数据并行的梯度同步有什么优化？</div>
<div class="qa-a"><p>(1) <strong>梯度压缩</strong>——只传 top-k 梯度或用低精度传输。(2) <strong>梯度累积</strong>——多个 micro-batch 的梯度在本地累积后再同步，减少通信次数。(3) <strong>通信-计算重叠</strong>——反向传播过程中，已计算完的层立即开始 AllReduce，不等所有层都算完。(4) <strong>Ring AllReduce</strong>——通信量 2(N-1)/N × data_size，线性扩展。</p></div>
</div>
</div>

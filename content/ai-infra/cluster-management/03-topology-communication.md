<div class="card card-s">
<h3>集群拓扑层次</h3>
<table>
<tr><th>层级</th><th>互联</th><th>带宽</th><th>延迟</th></tr>
<tr><td>GPU 内部</td><td>SM ↔ HBM</td><td>2-4.8 TB/s</td><td>ns 级</td></tr>
<tr><td>节点内 GPU 间</td><td>NVLink / NVSwitch</td><td>300-900 GB/s</td><td>μs 级</td></tr>
<tr><td>节点内 CPU-GPU</td><td>PCIe Gen4/5</td><td>32-64 GB/s</td><td>μs 级</td></tr>
<tr><td>节点间</td><td>InfiniBand / RoCE</td><td>200-400 Gbps</td><td>几 μs</td></tr>
<tr><td>机柜间</td><td>交换机</td><td>几百 Gbps</td><td>几十 μs</td></tr>
</table>
<p><strong>调度意义</strong>：分布式训练的通信模式（AllReduce）对带宽敏感。拓扑感知调度把同一任务的 worker 放在 NVLink 可达的 GPU 上，或者至少同一个机柜内，显著减少通信时间。</p>

<h3>集合通信原语</h3>
<table>
<tr><th>原语</th><th>操作</th><th>训练中的用途</th></tr>
<tr><td>AllReduce</td><td>所有节点的数据聚合（如求和），结果广播到所有节点</td><td>数据并行梯度同步</td></tr>
<tr><td>AllGather</td><td>所有节点收集所有节点的数据</td><td>张量并行参数同步</td></tr>
<tr><td>ReduceScatter</td><td>先 Reduce 再 Scatter 分片</td><td>ZeRO 优化</td></tr>
<tr><td>Broadcast</td><td>一个节点广播到所有节点</td><td>参数初始化</td></tr>
<tr><td>P2P Send/Recv</td><td>点对点传输</td><td>流水线并行</td></tr>
</table>
<p>NCCL（NVIDIA Collective Communication Library）自动选择最优通信路径（NVLink &gt; PCIe &gt; InfiniBand）。</p>
</div>

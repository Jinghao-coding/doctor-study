<div class="card card-r">
<h3>GPU 集群常见故障</h3>
<table>
<tr><th>故障类型</th><th>频率</th><th>影响</th><th>应对</th></tr>
<tr><td>GPU ECC 错误</td><td>每周/每月</td><td>单卡不可用</td><td>自动检测 + 标记不可调度</td></tr>
<tr><td>NVLink 降级</td><td>偶发</td><td>通信带宽下降</td><td>重新拓扑发现 + 调整并行策略</td></tr>
<tr><td>节点宕机</td><td>大集群每天</td><td>丢失所有进程</td><td>checkpoint 恢复 + 弹性训练</td></tr>
<tr><td>网络分区</td><td>偶发</td><td>NCCL 超时</td><td>超时检测 + 重连</td></tr>
<tr><td>显存泄漏</td><td>常见</td><td>OOM Kill</td><td>监控 + 自动重启</td></tr>
</table>

<h3>Checkpoint 策略</h3>
<ul>
<li><strong>周期性 checkpoint</strong>：每 N 步保存一次完整状态（模型 + 优化器 + 数据迭代器位置）</li>
<li><strong>异步 checkpoint</strong>：后台线程写入存储，不阻塞训练</li>
<li><strong>增量 checkpoint</strong>：只保存变化部分，减少 I/O</li>
<li><strong>分布式 checkpoint</strong>：每张卡只保存自己的分片，并行写入</li>
</ul>
<p>大模型的 checkpoint 可能上百 GB，存储带宽和频率是 trade-off：太频繁影响训练速度，太稀疏丢失进度多。</p>
</div>

<div class="card card-w">
<h3>资源类型</h3>
<table>
<tr><th>类别</th><th>资源</th><th>特点</th></tr>
<tr><td>原生资源</td><td>cpu, memory</td><td>可压缩（cpu）和不可压缩（memory）。Pod 设 requests/limits</td></tr>
<tr><td>扩展资源（Extended Resource）</td><td>nvidia.com/gpu</td><td>整数分配，<strong>admit 后不可修改</strong></td></tr>
<tr><td>临时存储</td><td>ephemeral-storage</td><td>节点本地磁盘</td></tr>
</table>

<h3>Requests vs Limits</h3>
<table>
<tr><th>维度</th><th>Requests</th><th>Limits</th></tr>
<tr><td>调度依据</td><td>是（调度器只看 requests）</td><td>否</td></tr>
<tr><td>运行时行为</td><td>保障最低资源</td><td>限制最大使用量</td></tr>
<tr><td>超出时</td><td>—</td><td>CPU 被 throttle，内存被 OOM Kill</td></tr>
</table>

<h3>QoS 等级</h3>
<table>
<tr><th>QoS</th><th>条件</th><th>驱逐优先级</th></tr>
<tr><td>Guaranteed</td><td>所有容器的 requests = limits</td><td>最后被驱逐</td></tr>
<tr><td>Burstable</td><td>至少一个容器设了 requests 但 requests ≠ limits</td><td>中间</td></tr>
<tr><td>BestEffort</td><td>没有设任何 requests 和 limits</td><td>最先被驱逐</td></tr>
</table>
</div>

<div class="card card-w">
<h3>InPlacePodVerticalScaling（1.27 alpha）</h3>
<p>传统修改资源需要重建 Pod。InPlace 允许在不重启容器的情况下动态调整 CPU 和 Memory 的 requests/limits。</p>
<p><strong>限制</strong>：只支持 CPU 和 Memory，<strong>不支持 GPU</strong>。GPU 是 Extended Resource，admit 后不可修改。GPU 分配必须在调度时确定，运行时只能通过 MPS 等方式做软共享。</p>
</div>

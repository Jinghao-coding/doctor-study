<div class="card card-d">
<h3>主流框架对比</h3>
<table>
<tr><th>框架</th><th>定位</th><th>核心能力</th><th>局限</th></tr>
<tr><td>Volcano</td><td>批处理调度</td><td>Gang scheduling、Queue 管理、PodGroup、Fair-share</td><td>缺少干扰感知、配额弹性不够灵活</td></tr>
<tr><td>Yunikorn</td><td>多租户资源管理</td><td>层级队列、应用感知调度、跨 K8s/YARN</td><td>GPU 拓扑支持有限</td></tr>
<tr><td>Kueue</td><td>作业排队管理</td><td>ResourceFlavor、ClusterQueue、Workload 抽象</td><td>较新，生态还在发展</td></tr>
<tr><td>Run:ai</td><td>GPU 虚拟化平台</td><td>GPU 分时/共享、配额管理、可视化</td><td>商业产品，闭源</td></tr>
</table>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Volcano 的核心设计？它的局限性？</div>
<div class="qa-a">
<p>Volcano 的核心是 <strong>PodGroup + Queue + Policy</strong>：PodGroup 定义 Gang scheduling 语义（minMember），Queue 管理多租户配额，Policy（Gang/DRF/Priority）定义调度策略。</p>
<p>Volcano 的局限性：(1) 配额是静态的（min/max），不支持连续保障度信号；(2) 没有干扰感知合用能力；(3) 不做运行时间预测；(4) 抢占是简单的优先级抢占，不考虑沉没成本。在需要弹性配额、干扰感知等能力时，需从 Scheduling Framework 原生构建，获得更大的灵活性。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Kueue 的 ResourceFlavor 是什么概念？</div>
<div class="qa-a"><p>ResourceFlavor 抽象了不同类型的资源——比如 A100 GPU 是一种 Flavor，H100 GPU 是另一种。ClusterQueue 可以关联多个 Flavor，每个 Flavor 有独立的配额。Workload 提交时可以指定 Flavor 偏好，Kueue 根据配额和排队情况分配。这对异构 GPU 集群很有用。</p></div>
</div>
</div>

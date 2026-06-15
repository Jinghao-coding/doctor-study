## 一句话结论

Kueue 是 K8s SIG Scheduling 的作业准入与排队系统：它不替换 kube-scheduler，而是在 Pod 真正进入调度前决定 Workload 能不能开始、用哪类资源开始。

<div class="card card-m">
<h3>Kueue 解决什么问题</h3>
<p>Kueue 的核心不是“给 Pod 打分”，而是“作业能不能被准入”。它适合你不想替换默认 scheduler，但需要 LocalQueue、ClusterQueue、ResourceFlavor、borrowing 和公平共享的场景。</p>
<table>
<tr><th>对象</th><th>作用</th><th>面试解释</th></tr>
<tr><td>LocalQueue</td><td>namespace 内用户提交入口</td><td>用户只看到本 namespace 的队列</td></tr>
<tr><td>ClusterQueue</td><td>集群级资源池和配额</td><td>平台管理员配置 quota、borrowing、flavor</td></tr>
<tr><td>ResourceFlavor</td><td>资源类型 / 节点池抽象</td><td>A100、H100、spot、on-demand 等资源口味</td></tr>
<tr><td>Workload</td><td>一个待准入作业的抽象</td><td>包含 PodSet，Kueue 判断它是否可以开始</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Kueue 调度链路</h3>
<ol>
<li>用户提交 Job / PyTorchJob / RayJob。</li>
<li>Kueue webhook 或 controller 生成 Workload。</li>
<li>Workload 进入 LocalQueue，再映射到 ClusterQueue。</li>
<li>Kueue 判断某个 ResourceFlavor 下是否有足够 nominal quota 或可借用额度。</li>
<li>准入后给 PodSet 写入 flavor 相关 nodeSelector / toleration 等信息。</li>
<li>具体 Pod → Node 绑定仍由 kube-scheduler 完成。</li>
</ol>
<div class="qa-summary">一句话：Kueue 像售票系统，决定作业能不能进场和坐哪个区域；kube-scheduler 像领位员，决定具体坐哪个座位。</div>
</div>

<div class="card card-w">
<h3>Kueue vs Volcano</h3>
<table>
<tr><th>维度</th><th>Kueue</th><th>Volcano</th></tr>
<tr><td>架构</td><td>准入/排队层，复用 kube-scheduler</td><td>批调度系统，深度控制调度过程</td></tr>
<tr><td>强项</td><td>队列、配额、ResourceFlavor、渐进式接入</td><td>Gang、Queue、Job 生命周期、调度插件</td></tr>
<tr><td>升级风险</td><td>低，和 scheduler 解耦</td><td>相对高，和调度链路耦合更深</td></tr>
<tr><td>控制粒度</td><td>准入层控制，Pod 绑定交给默认 scheduler</td><td>调度过程内控制，能做更细的 Permit / Reserve</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ResourceFlavor 为什么重要？</div>
<div class="qa-a"><p>异构 GPU 集群里“1 张 GPU”不是等价资源。A100/H100/V100、spot/on-demand、不同拓扑和成本都不同。ResourceFlavor 把资源的质纳入队列配额，让 Workload 在准入阶段就知道自己被分到哪类资源。</p></div>
</div>

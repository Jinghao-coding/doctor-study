<div class="card card-m">
<h3>Kueue 解决什么问题</h3>
<p>Kueue 的核心不是“给 Pod 打分”，而是“作业能不能被准入”。它适合你不想替换默认 scheduler，但需要 LocalQueue、ClusterQueue、ResourceFlavor、borrowing 和公平共享的场景。</p>
<table>
<tr><th>对象</th><th>作用</th><th>面试解释</th></tr>
<tr><td>LocalQueue</td><td>namespace 内用户提交入口</td><td>用户只看到本 namespace 的队列</td></tr>
<tr><td>ClusterQueue</td><td>集群级队列及配额</td><td>平台管理员配置 quota、borrowing、flavor；不是物理资源池本身</td></tr>
<tr><td>ResourceFlavor</td><td>资源类型 / 节点池抽象</td><td>A100、H100、spot、on-demand 等资源口味</td></tr>
<tr><td>Cohort</td><td>多个队列的共享关系</td><td>结合额度、借用与回收规则管理共享</td></tr>
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
<div class="qa-summary">Kueue 像售票系统，决定作业能不能进场和坐哪个区域；kube-scheduler 像领位员，决定具体坐哪个座位。</div>
</div>

<div class="card card-w">
<h3>Kueue vs Volcano</h3>
<table>
<tr><th>维度</th><th>Kueue</th><th>Volcano</th></tr>
<tr><td>架构</td><td>准入/排队层，复用 kube-scheduler</td><td>批调度系统，深度控制调度过程</td></tr>
<tr><td>强项</td><td>队列、配额、ResourceFlavor、渐进式接入</td><td>Gang、Queue、Job 生命周期、调度插件</td></tr>
<tr><td>集成关注点</td><td>工作负载适配、准入状态与配额转换</td><td>调度插件、队列策略和作业控制器</td></tr>
<tr><td>控制粒度</td><td>准入层控制，Pod 绑定由配置的调度器执行</td><td>通过 Session、Action、Plugin 组织分配和抢占回收</td></tr>
</table>
</div>

<div class="card card-d">
<h3>额度准入与设备分配</h3>
<p>Kueue 批准 Workload，表示所配置的额度和准入条件得到满足。Pod 后续仍可能因为设备属性、拓扑、卷、污点或实际容量而 Pending。接入 DRA 时，需要将设备需求映射到队列计账资源；设备选择、节点侧准备和容器注入仍是后续阶段。<a href="https://kueue.sigs.k8s.io/docs/tasks/run/dra/">Kueue DRA 指南</a></p>
<p>共享 GPU 要同时处理卡数、每卡显存及算力限制。例如申请两份设备，每份 4Gi 显存，额度应核算总计 8Gi；不能仅看到一个 gpumem 字段就漏掉卡数，也不能转换后再重复扣账。具体转换配置依集成版本确认。<a href="https://www.lixueduan.com/posts/kubernetes/65-kueue-p4-hami-vgpu/">Kueue 与 HAMi 计账示例</a></p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ResourceFlavor 为什么重要？</div>
<div class="qa-a"><p>异构 GPU 集群里“1 张 GPU”不是等价资源。A100/H100/V100、spot/on-demand、不同拓扑和成本都不同。ResourceFlavor 把资源的质纳入队列配额，让 Workload 在准入阶段就知道自己被分到哪类资源。</p></div>
</div>

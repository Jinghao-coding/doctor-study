<div class="card card-m">
<h3>为什么不能只用 K8S 默认调度器</h3>
<p>K8S 默认调度器适合每个 Pod 独立调度的在线服务。但 GPU 训练任务通常需要一组 Pod 同时启动、长时间运行、拓扑敏感、多租户公平和抢占恢复。默认 scheduler 没有任务级队列、没有作业级配额、没有 Gang 语义，也不能表达“超过 10 张 GPU 后继续提交但排队”。</p>
<table>
<tr><th>需求</th><th>默认 K8s 支持情况</th><th>需要补的能力</th></tr>
<tr><td>任务级排队</td><td>不支持，只是 Pod 调度队列</td><td>Queue / Workload / AIJob 准入队列</td></tr>
<tr><td>租户 GPU 限额</td><td>ResourceQuota 会直接拒绝超额创建</td><td>允许提交，超额任务排队等待</td></tr>
<tr><td>Gang Scheduling</td><td>不支持 job 级 all-or-nothing</td><td>PodGroup / Workload / Permit 等待</td></tr>
<tr><td>异构 GPU</td><td>靠 label / extended resource 粗表达</td><td>ResourceFlavor / DRA / 拓扑画像</td></tr>
<tr><td>公平共享</td><td>默认只按 Pod 优先级和资源匹配</td><td>DRF、proportion、borrowing、reclaim</td></tr>
</table>
</div>

<div class="card card-d">
<h3>框架选型地图</h3>
<table>
<tr><th>框架</th><th>定位</th><th>最适合</th><th>主要代价</th></tr>
<tr><td>Volcano</td><td>K8s 原生批调度系统</td><td>训练/HPC/Spark/Flink 等需要 Gang 和 Queue 的场景</td><td>学习 CRD 和插件体系，和调度器耦合较深</td></tr>
<tr><td>Kueue</td><td>K8s SIG 官方作业准入/排队系统</td><td>不想替换 scheduler，只想做队列和配额准入</td><td>不控制 Pod 级调度细节</td></tr>
<tr><td>YuniKorn</td><td>层级队列资源管理器</td><td>大型组织、多层部门/团队资源治理</td><td>架构和运维复杂度更高</td></tr>
<tr><td>Run:ai</td><td>商业 GPU 虚拟化平台</td><td>快速落地 GPU 共享、配额、可视化和成本治理</td><td>闭源、定制深度受限</td></tr>
<tr><td>自研队列 + Scheduler Plugin</td><td>按业务定制</td><td>已有 K8s 基础但需要 AIJob、预测、干扰、代价抢占</td><td>研发和维护成本最高</td></tr>
</table>
</div>

<div class="card card-w">
<h3>面试回答套路</h3>
<ol>
<li>先说默认 K8s 只能解决 Pod 到 Node 的绑定，不解决任务级队列和 Gang。</li>
<li>再说 Volcano / Kueue / YuniKorn / Run:ai 分别补哪一层能力。</li>
<li>最后根据规模和需求选型：小规模用 Volcano/Kueue，组织层级复杂看 YuniKorn，需要 GPU 共享商业能力看 Run:ai，深度定制走自研。</li>
</ol>
<div class="qa-summary">收束：框架选型不是比谁更先进，而是看你要控制“准入排队、调度过程、队列层级、GPU 共享、业务定制”中的哪一层。</div>
</div>

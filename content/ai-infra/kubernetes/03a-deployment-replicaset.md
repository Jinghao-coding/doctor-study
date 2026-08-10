<div class="card card-m">
<h3>Deployment、ReplicaSet 与 Pod 的控制关系</h3>
<div class="flow" role="list" aria-label="Deployment 控制链路">
<div class="flow-step" role="listitem"><div class="flow-index">01</div><div class="flow-title">Deployment</div><div class="flow-desc">声明副本数、Pod template 与发布策略</div></div>
<div class="flow-step" role="listitem"><div class="flow-index">02</div><div class="flow-title">ReplicaSet</div><div class="flow-desc">每个 Pod template 版本对应一个 RS</div></div>
<div class="flow-step" role="listitem"><div class="flow-index">03</div><div class="flow-title">Pod</div><div class="flow-desc">RS 维持匹配 selector 的副本数</div></div>
</div>
<p>Deployment Controller 管理 ReplicaSet 的版本与伸缩，ReplicaSet Controller 管理 Pod 数量。Pod template 的哈希写入 <code>pod-template-hash</code>，用于区分新旧 ReplicaSet。</p>
<div class="qa-summary">只有 <code>.spec.template</code> 变化才触发新 rollout / revision；单纯修改 <code>.spec.replicas</code> 只做伸缩，不创建新版本。</div>
</div>

<div class="card card-s">
<h3>两种发布策略</h3>
<table>
<tr><th>策略</th><th>行为</th><th>适用边界</th></tr>
<tr><td><code>RollingUpdate</code>（默认）</td><td>逐步扩新 ReplicaSet、缩旧 ReplicaSet</td><td>服务能容忍新旧版本短时并存，通常配 readiness</td></tr>
<tr><td><code>Recreate</code></td><td>更新时先终止旧版本 Pod，再创建新版本 Pod</td><td>新旧版本不能并存；会产生服务中断</td></tr>
</table>
<p><code>Recreate</code> 的“先删后建”只约束 Deployment 发起的升级；如果用户手动删除单个 Pod，ReplicaSet 仍会立即补副本，旧 Pod 终止期间可能短暂重叠。</p>
</div>

<div class="card card-d">
<h3>RollingUpdate 的数量约束</h3>
<table>
<tr><th>字段</th><th>控制什么</th><th>计算边界</th></tr>
<tr><td><code>maxUnavailable</code></td><td>更新期间最多允许多少期望副本不可用</td><td>百分比向下取整；默认 25%</td></tr>
<tr><td><code>maxSurge</code></td><td>最多允许比期望副本数多创建多少 Pod</td><td>百分比向上取整；默认 25%</td></tr>
<tr><td><code>minReadySeconds</code></td><td>Pod Ready 后还需稳定多久才计为 Available</td><td>默认 0；用于避免刚 Ready 就推进发布</td></tr>
<tr><td><code>progressDeadlineSeconds</code></td><td>多久没有进展后报告 <code>ProgressDeadlineExceeded</code></td><td>默认 600 秒；只报告失败进展，Controller 仍会继续重试</td></tr>
</table>
<p><code>maxUnavailable</code> 与 <code>maxSurge</code> 不能同时为 0。Terminating Pod 不计入 availableReplicas，而且可能在宽限期内继续占资源，因此 rollout 期间实际 Pod 数和资源占用可暂时超过 <code>replicas + maxSurge</code>。</p>
</div>

<div class="card card-m">
<h3>一次滚动发布的状态流</h3>
<ol>
<li>修改 Deployment 的 <code>.spec.template</code>，Deployment Controller 生成新的 template hash 和 ReplicaSet。</li>
<li>在 <code>maxSurge</code> 允许范围内扩新 ReplicaSet，在 <code>maxUnavailable</code> 允许范围内缩旧 ReplicaSet。</li>
<li>新 Pod 经过调度、启动和 readiness；Ready 持续达到 <code>minReadySeconds</code> 后才计入 Available。</li>
<li>Controller 继续缩旧扩新，直到所有期望副本均为新版本且可用，旧 ReplicaSet 缩到 0。</li>
<li>旧 ReplicaSet 按 <code>revisionHistoryLimit</code> 保留，供 <code>kubectl rollout undo</code> 回滚 Pod template。</li>
</ol>
</div>

<div class="card card-s">
<h3>status 字段怎么读</h3>
<table>
<tr><th>字段</th><th>含义</th><th>异常提示</th></tr>
<tr><td><code>replicas</code></td><td>当前非终止 Pod 总数</td><td>与期望值长期不等，先看 RS 与 Events</td></tr>
<tr><td><code>updatedReplicas</code></td><td>使用最新 Pod template 的副本数</td><td>不增长通常是新 RS 无法扩容或 Pod 无法创建</td></tr>
<tr><td><code>readyReplicas</code></td><td>Ready 的副本数</td><td>探针、应用启动、依赖或配置问题</td></tr>
<tr><td><code>availableReplicas</code></td><td>Ready 且满足 minReadySeconds 的副本数</td><td>发布是否能继续推进的关键</td></tr>
<tr><td><code>unavailableReplicas</code></td><td>仍缺少的可用副本数</td><td>配合 Progressing / Available conditions 判断</td></tr>
</table>
</div>

<div class="card card-w">
<h3>三个容易答错的边界</h3>
<ul>
<li><strong>Deployment 不等于“不能用持久化存储”。</strong>Pod 可以挂 PVC；Deployment 缺少的是每个副本的稳定身份与稳定 PVC 绑定，不适合把副本当作不可互换成员。</li>
<li><strong>PDB 不控制 Deployment 自己的滚动删除。</strong>PDB 主要约束 Eviction API 等自愿中断；rollout 可用性由 Deployment strategy、readiness 和 minReadySeconds 控制。</li>
<li><strong>不要让多个控制器 selector 重叠。</strong>Deployment selector 创建后不可变；重叠 selector 可能让控制器争抢或误认 Pod。</li>
</ul>
</div>

<div class="card card-r">
<h3>发布卡住的定位顺序</h3>
<pre><code class="language-bash">kubectl rollout status deployment/&lt;name&gt;
kubectl describe deployment &lt;name&gt;
kubectl get rs -l app=&lt;label&gt;
kubectl get pod -l app=&lt;label&gt; -o wide
kubectl describe pod &lt;new-pod&gt;
kubectl logs &lt;new-pod&gt; --all-containers --previous</code></pre>
<table>
<tr><th>现象</th><th>优先检查</th></tr>
<tr><td>新 ReplicaSet 没创建</td><td>template 校验、selector、配额、权限、Deployment condition</td></tr>
<tr><td>新 RS 有但 replicas 不增长</td><td>ResourceQuota、LimitRange、Pod 创建 Events</td></tr>
<tr><td>Pod Pending</td><td>资源、亲和性、taint、PVC、调度 Events</td></tr>
<tr><td>Pod Running 但 not Ready</td><td>readiness、启动日志、依赖、minReadySeconds</td></tr>
<tr><td><code>ProgressDeadlineExceeded</code></td><td>它只表示发布没有按时进展，不会自动回滚</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: maxSurge=1、maxUnavailable=0 表示什么？</div>
<div class="qa-a">
<p>发布期间至少维持全部期望副本可用，同时最多额外创建 1 个新 Pod。它适合优先保证可用性的服务，但要求集群有额外容量；如果新 Pod 永远不 Ready，旧 Pod 不会继续缩容，发布会卡住。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: rollback 会恢复哪些内容？</div>
<div class="qa-a">
<p>Deployment revision 保存的是 Pod template 快照，回滚主要恢复 <code>.spec.template</code>。副本数等不产生 revision 的字段不会因为回滚自动恢复；旧 ReplicaSet 被 revisionHistoryLimit 清理后，也无法再回到对应版本。</p>
</div>
</div>

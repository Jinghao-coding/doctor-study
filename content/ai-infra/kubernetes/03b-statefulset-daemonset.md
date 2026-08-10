<div class="card card-s">
<h3>StatefulSet 与 DaemonSet 的官方定义</h3>
<p><strong>StatefulSet</strong> 用于管理有状态应用的一组 Pod。Pod 可以来自相同模板，但不是可互换副本；每个 Pod 都有稳定标识，这个标识会跨重新调度保留。它还为部署、伸缩和更新提供顺序与唯一性保证。</p>
<p><strong>DaemonSet</strong> 用于提供节点本地能力，确保所有或部分符合条件的 Node 各运行一份 Pod。Node 加入时补建对应 Pod，Node 移除时清理对应 Pod，因此它控制的是“目标节点覆盖”，不是固定副本数。</p>
<p><strong>选择标准：</strong>成员需要稳定网络身份或独立持久卷时考虑 StatefulSet；功能必须贴着每个目标节点运行时使用 DaemonSet。两者都不替代应用自身的数据复制、选主或故障恢复协议。</p>
<p>官方文档：<a href="https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/">StatefulSet</a> · <a href="https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/">DaemonSet</a></p>
</div>

<div class="card card-m">
<h3>StatefulSet 与 DaemonSet 解决不同的“不互换”问题</h3>
<table>
<tr><th>对象</th><th>控制目标</th><th>Pod 为什么不可随意互换</th></tr>
<tr><td>StatefulSet</td><td>维持 N 个有序、身份稳定的副本</td><td>每个 ordinal 可能对应独立网络身份、存储和应用角色</td></tr>
<tr><td>DaemonSet</td><td>让所有或部分符合条件的 Node 各运行一份节点组件</td><td>Pod 与目标 Node 的本地功能绑定，例如日志、网络、存储或设备插件</td></tr>
</table>
</div>

<div class="card card-s">
<h3>StatefulSet 的三类稳定身份</h3>
<table>
<tr><th>身份</th><th>实现</th><th>边界</th></tr>
<tr><td>稳定 ordinal</td><td><code>web-0</code>、<code>web-1</code>；默认从 0 开始，可配置起始 ordinal</td><td>Pod 重建后同一 ordinal 仍代表同一成员</td></tr>
<tr><td>稳定网络身份</td><td><code>serviceName</code> + Headless Service 形成稳定 DNS</td><td>Headless Service 需要用户创建；DNS 仍可能受负缓存影响</td></tr>
<tr><td>稳定存储</td><td><code>volumeClaimTemplates</code> 为每个 Pod 创建独立 PVC</td><td>需要可用 StorageClass/PV；StatefulSet 不负责数据复制、一致性或备份</td></tr>
</table>
<p>StatefulSet 不是“有状态应用自动托管器”。它只稳定对象身份和生命周期；选主、复制、分片、成员变更和数据恢复仍由应用或 Operator 完成。</p>
</div>

<div class="card card-d">
<h3>StatefulSet 创建、伸缩与更新</h3>
<table>
<tr><th>字段/策略</th><th>默认行为</th><th>何时调整</th></tr>
<tr><td><code>podManagementPolicy: OrderedReady</code></td><td>按 ordinal 递增创建，前一个 Ready 后再创建下一个；缩容逆序</td><td>成员存在启动依赖</td></tr>
<tr><td><code>podManagementPolicy: Parallel</code></td><td>伸缩时并行创建/删除，不等待前一个 Ready</td><td>副本无启动顺序依赖、希望加速扩缩容</td></tr>
<tr><td><code>updateStrategy: RollingUpdate</code></td><td>默认从最大 ordinal 向最小 ordinal 逐个重建，并等待 Ready</td><td>常规自动更新</td></tr>
<tr><td><code>rollingUpdate.partition</code></td><td>只更新 ordinal ≥ partition 的 Pod</td><td>金丝雀、分阶段升级、保留低 ordinal 稳定成员</td></tr>
<tr><td><code>updateStrategy: OnDelete</code></td><td>template 更新后不自动重建，手动删 Pod 才应用新模板</td><td>应用需要外部编排成员更新</td></tr>
</table>
<div class="qa-summary">默认有序不是绝对前提：<code>Parallel</code> 会放松扩缩容顺序；StatefulSet 的“稳定身份”与“有序动作”是两组不同保证。</div>
</div>

<div class="card card-w">
<h3>PVC 保留与删除必须显式设计</h3>
<p>默认 <code>persistentVolumeClaimRetentionPolicy</code> 为 <code>Retain</code>：缩容或删除 StatefulSet 不自动删除由 volumeClaimTemplates 创建的 PVC。当前稳定 API 可以分别设置：</p>
<table>
<tr><th>字段</th><th><code>Retain</code></th><th><code>Delete</code></th></tr>
<tr><td><code>whenScaled</code></td><td>缩掉 Pod 后保留对应 PVC，未来同 ordinal 可复用</td><td>Pod 正常终止后删除被缩掉 ordinal 的 PVC</td></tr>
<tr><td><code>whenDeleted</code></td><td>删除 StatefulSet 后保留所有 PVC</td><td>Pod 正常终止后删除模板生成的 PVC</td></tr>
</table>
<p>即便 PVC 被删，底层卷是否删除仍取决于 PV / StorageClass 的 reclaim policy。任何自动删除策略上线前都应验证备份与恢复。</p>
</div>

<div class="card card-r">
<h3>StatefulSet 滚动更新的卡死点</h3>
<p>默认 OrderedReady 下，如果某个新版本 Pod 永远无法 Running + Ready，Controller 会停在该 ordinal。即使把 template 回退到好版本，也可能需要手动删除已经创建的坏 Pod，控制器才会按回退后的模板重建。</p>
<pre><code class="language-bash">kubectl rollout status statefulset/&lt;name&gt;
kubectl get pod -l app=&lt;label&gt; -L controller-revision-hash
kubectl get controllerrevision
kubectl describe pod &lt;blocked-pod&gt;</code></pre>
</div>

<div class="card card-s">
<h3>DaemonSet 如何决定“每个节点一个”</h3>
<ol>
<li>DaemonSet Controller 根据 nodeSelector、原始 nodeAffinity 等条件找出 eligible Nodes。</li>
<li>它为每个目标 Node 创建 Pod，并把 Pod 的 required nodeAffinity 改成精确匹配该 Node。</li>
<li>默认 scheduler 通常负责最终绑定；Pod 调度失败时仍可能涉及资源不足和优先级/抢占。</li>
<li>Node 新增或标签变为匹配时补 Pod；Node 不再匹配或被删除时清理对应 Pod。</li>
</ol>
<p>DaemonSet Controller 会自动加入一组关键 tolerations，例如 not-ready、unreachable、unschedulable；但业务自定义 taint 仍需要显式 toleration。重要节点组件通常还应配置合适的 PriorityClass。</p>
</div>

<div class="card card-d">
<h3>DaemonSet 更新与容量风险</h3>
<table>
<tr><th>策略/字段</th><th>作用</th><th>风险</th></tr>
<tr><td><code>RollingUpdate</code>（默认）</td><td>template 改变后受控替换各节点 Pod</td><td>节点组件升级失败可能影响整批节点功能</td></tr>
<tr><td><code>OnDelete</code></td><td>只有旧 Pod 被手动删除后才使用新模板重建</td><td>需要外部系统确保更新覆盖率</td></tr>
<tr><td><code>maxUnavailable</code></td><td>限制更新期间最多不可用的 daemon Pod</td><td>值过大会同时损失多个节点能力</td></tr>
<tr><td><code>maxSurge</code></td><td>允许先在节点启动新版再删除旧版</td><td>同一节点短时运行两份，CPU/内存/端口/设备可能冲突</td></tr>
<tr><td><code>minReadySeconds</code></td><td>新版 Ready 稳定一段时间后才继续</td><td>探针不代表真实节点功能时仍会误推进</td></tr>
</table>
</div>

<div class="card card-w">
<h3>AI Infra 场景边界</h3>
<table>
<tr><th>场景</th><th>常见对象</th><th>原因</th></tr>
<tr><td>GPU Device Plugin、DCGM exporter、CSI node plugin、CNI node agent</td><td>DaemonSet</td><td>功能必须贴着目标节点运行</td></tr>
<tr><td>etcd、ZooKeeper、Kafka 等成员稳定的服务</td><td>StatefulSet + 应用/Operator</td><td>需要稳定成员身份和存储，但一致性仍由上层处理</td></tr>
<tr><td>普通无状态推理副本</td><td>Deployment</td><td>副本通常可替换，不需要稳定 ordinal</td></tr>
<tr><td>一次性分布式训练</td><td>Job / TrainJob / 训练 Operator</td><td>核心是完成、角色、rank 和失败恢复，不应仅因“有 rank”就套 StatefulSet</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: StatefulSet 删除 Pod 后，名称和存储会怎样？</div>
<div class="qa-a">
<p>Controller 会按同一 ordinal 重建同名 Pod；如果使用 volumeClaimTemplates，通常重新挂载该 ordinal 对应的 PVC。默认 PVC 保留策略是 Retain，但最终还要结合 StatefulSet PVC retention policy 与 PV reclaim policy 判断数据是否删除。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: cordon 后为什么 DaemonSet Pod 仍可能被调度？</div>
<div class="qa-a">
<p>DaemonSet Pod 会自动获得 <code>node.kubernetes.io/unschedulable:NoSchedule</code> toleration，节点级网络、存储等组件需要在不可调度节点上继续存在。cordon 主要阻止普通新 Pod，不等价于停止 DaemonSet。</p>
</div>
</div>

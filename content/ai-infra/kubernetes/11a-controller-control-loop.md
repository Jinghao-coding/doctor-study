<div class="card card-m">
<h3>Kubernetes Controller：让实际状态持续接近期望状态</h3>
<p>Kubernetes 官方把 Controller 描述为持续运行的控制循环：它观察集群状态，并在需要时创建或请求变更，使当前状态逐步接近期望状态。Controller 不直接操作 etcd，也通常不直接命令其他组件，而是读取和写入 API 对象，由其他控制循环继续完成后续工作。</p>
<p>例如用户把 Deployment 的 <code>spec.replicas</code> 从 2 改成 3：Deployment Controller 调整 ReplicaSet，ReplicaSet Controller 创建一个新 Pod，Scheduler 为 Pod 选 Node，目标 kubelet 再启动容器。这些组件通过 API Server 中的对象状态协作，不需要相互同步调用。</p>
<p>官方资料：<a href="https://kubernetes.io/docs/concepts/architecture/controller/">Kubernetes Controllers</a> · <a href="https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/">Control Plane to Node Communication</a></p>
</div>

## 控制循环

```flow
读取期望状态 | 从 spec、metadata 或策略对象得到系统应达到的目标
观察实际状态 | 读取子对象、status、节点状态或外部系统事实
计算差异 | 判断已经收敛、需要创建/更新/删除，还是暂时无法推进
执行修正 | 通过 API Server 写对象，或调用受控的外部系统
重新观察 | 等待相关事件、限速重试或按时间再次 Reconcile
```

<div class="card card-s">
<h3>期望状态、实际状态与 Status</h3>
<table>
<tr><th>状态</th><th>常见来源</th><th>例子</th></tr>
<tr><td>期望状态</td><td>对象的 <code>spec</code>、metadata、策略或配额对象</td><td>Deployment 希望有 3 个副本；TrainingJob 希望使用 8 张 GPU</td></tr>
<tr><td>实际状态</td><td>子对象、Node/Pod 状态、外部云资源、队列或存储系统</td><td>当前只有 2 个 Pod；外部负载均衡器尚未创建</td></tr>
<tr><td>观察结果</td><td>父对象的 <code>status</code> 与 Conditions</td><td><code>observedGeneration</code>、Ready、Progressing、Degraded</td></tr>
</table>
<p><code>status</code> 是 Controller 对实际状态的报告，不等于实际系统本身。它更新失败时，外部资源可能已经成功创建，所以 Controller 必须能在下一轮重新查询并补写状态。</p>
</div>

<div class="card card-d">
<h3>Reconcile 处理的是对象当前状态，不是重放事件</h3>
<pre><code class="language-go">func Reconcile(key NamespacedName) error {
    desired := getDesiredObject(key)
    actual := observeChildrenAndExternalState(desired)

    if desired.IsDeleting() {
        return reconcileFinalizer(desired, actual)
    }
    if diff := calculateDiff(desired, actual); !diff.Empty() {
        return applyIdempotentChange(diff)
    }
    return updateStatusIfChanged(desired, actual)
}</code></pre>
<p>Watch 通知只表达“这个对象可能值得重新检查”。worker 真正执行时应重新读取当前状态，因为事件可能重复、合并、乱序，Controller 也可能在处理过程中崩溃。相同输入执行一次和多次应得到相同结果。</p>
</div>

<div class="card card-w">
<h3>控制器必须面对的失败模型</h3>
<table>
<tr><th>现象</th><th>正确处理</th><th>不能依赖</th></tr>
<tr><td>同一对象多次触发</td><td>幂等 Reconcile、稳定子资源名称、按 UID 去重外部副作用</td><td>事件只出现一次</td></tr>
<tr><td>本地观察稍旧</td><td>再次 Reconcile；关键更新使用 resourceVersion 冲突保护</td><td>Informer Cache 与 API Server 实时完全一致</td></tr>
<tr><td>API 或外部系统暂时失败</td><td>分类错误、限速重试、超时、Condition/Event</td><td>一次调用必定成功或失败结果完全确定</td></tr>
<tr><td>进程重启或切主</td><td>从 API 与外部系统重建当前状态</td><td>内存队列、锁和处理中间变量会持久化</td></tr>
<tr><td>对象正在删除</td><td>OwnerReference 清理 API 内子对象；Finalizer 幂等清理外部资源</td><td>删除事件到达后对象仍可无限读取</td></tr>
</table>
</div>

## 外部副作用与 Status 一致性

Kubernetes API 对象和云 API、训练队列、对象存储等外部系统之间没有分布式事务。一次 Reconcile 可能已经在外部创建资源，却在写回 `status` 前超时或崩溃；下一轮看到的仍是旧 Status，但外部操作并不一定失败。

```flow
持久化操作意图 | 用 CR UID、generation、操作类型生成稳定 operation ID
调用外部系统 | 请求携带幂等键，或给外部资源写 owner UID / tag
结果未知时先查询 | 网络超时不能直接等价为“外部创建失败”
认领或补建资源 | 已存在且配置正确就认领；不存在才创建
写回观察结果 | 更新 external ID、observedGeneration 和 Conditions
后续持续对账 | 外部资源漂移或 Status 丢失都可重新收敛
```

<div class="card card-m">
<h3>外部成功、Status 失败后的重试协议</h3>
<table>
<tr><th>下一轮观察</th><th>Controller 动作</th><th>不能做什么</th></tr>
<tr><td>按稳定 key 找到外部资源，配置也正确</td><td>认领现有资源，只补写 Status</td><td>再次无条件创建</td></tr>
<tr><td>外部资源不存在</td><td>使用同一幂等键创建，再写 Status</td><td>换随机名称绕过去重</td></tr>
<tr><td>请求超时，结果未知</td><td>先按 operation ID 查询；必要时进入异步对账</td><td>把超时直接当成确定失败</td></tr>
<tr><td>外部状态与最新 spec 不一致</td><td>根据最新 generation 计算更新或替换动作</td><td>继续执行旧 generation 的中间步骤</td></tr>
</table>
<p>复杂、长耗时操作可以单独建 Operation CR 或外部任务记录，持久化 intent、operation ID、阶段和最后一次错误。Controller 重启后从这些持久状态恢复，而不是依赖进程内变量。</p>
</div>

## API 更新冲突与字段所有权

<div class="card card-s">
<h3>resourceVersion 提供乐观并发保护</h3>
<p>Controller 基于某一版本对象计算更新时，写请求会携带该对象的 <code>resourceVersion</code>。如果其他客户端已先更新对象，API Server 返回 <code>409 Conflict</code>，防止陈旧副本覆盖新状态。</p>
<ol>
<li>重新 Get 最新对象；不能反复提交原来的旧对象。</li>
<li>基于最新 spec、status 和 generation 重新计算差异。</li>
<li>只更新自己负责的字段；spec 与 status 使用不同子资源。</li>
<li>使用 Patch 或 Server-Side Apply 时明确 field manager，减少多个 Controller 写同一字段。</li>
</ol>
<p><code>resourceVersion</code> 是 API Server 管理的不透明值，不应手工递增，也不应用数值大小推导业务先后关系。</p>
</div>

## OwnerReference、Finalizer 与删除收敛

<div class="card card-d">
<h3>两种清理机制负责不同边界</h3>
<table>
<tr><th>机制</th><th>解决的问题</th><th>删除链路</th></tr>
<tr><td><code>ownerReferences</code></td><td>Kubernetes API 内父子对象的垃圾回收</td><td>父对象删除后，Garbage Collector 按传播策略删除 dependent 对象</td></tr>
<tr><td><code>finalizers</code></td><td>对象最终消失前必须完成的清理协议，尤其是 API 外部资源</td><td>API Server 先写 <code>deletionTimestamp</code>；Controller 清理成功后移除自己的 finalizer；对象才最终删除</td></tr>
</table>
<p>删除分支也必须幂等：外部资源已经不存在应视为清理完成；Controller 只能移除自己负责的 finalizer，不能清空其他组件的 key。</p>
</div>

<div class="card card-w">
<h3>Finalizer 卡死的恢复顺序</h3>
<ol>
<li>检查对象的 <code>deletionTimestamp</code>、剩余 finalizers 和 Conditions/Events，定位负责的 Controller。</li>
<li>检查 Controller 是否存活，以及 RBAC、网络、外部 API、超时和重试是否阻断清理。</li>
<li>修复 Controller 或人工完成等价清理，让它幂等地移除自己的 key。</li>
<li>只有确认清理已完成，或明确接受外部资源泄漏与一致性风险时，才人工 patch 掉对应 finalizer。</li>
</ol>
</div>

## 多副本 Controller 与 Leader Election

<div class="card card-m">
<h3>进程内去重、多副本协调和业务正确性是三层问题</h3>
<table>
<tr><th>层次</th><th>机制</th><th>能力边界</th></tr>
<tr><td>单进程多个 worker</td><td>WorkQueue 的 dirty / processing 集合按 key 合并并发</td><td>只约束当前进程，处理期间再次更新会在 <code>Done</code> 后重新入队</td></tr>
<tr><td>多个 Controller 副本</td><td>各副本拥有独立 Informer Cache 和 WorkQueue</td><td>没有额外协调时，可能同时 Reconcile 同一对象</td></tr>
<tr><td>单活故障切换</td><td>通过 <code>coordination.k8s.io/v1 Lease</code> 选 Leader，通常只有 Leader 启动 worker</td><td>减少常态重复工作并提供故障切换，但不提供 exactly-once</td></tr>
<tr><td>最终正确性</td><td>幂等、resourceVersion、稳定名称、外部幂等键或 fencing token</td><td>在重试、切主或短暂重叠时避免重复创建和陈旧写覆盖并发结果</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Lease 切主时可能发生什么</h3>
<p>Leader 定期续租；续租失败后应停止工作，其他副本在租约可竞争时成为新 Leader。旧 Leader 已完成的 API 写入会由新 Leader 的 Informer 重新观察；只存在内存中的队列、锁和中间状态会丢失，因此必须从 API 对象和外部事实重建。</p>
<p>Leader Election 不是事务和 fencing。网络分区、进程长时间暂停或外部调用已经发出时，旧、新实例的副作用可能在短窗口内重叠。API 对象更新可由 <code>resourceVersion</code> 拒绝陈旧写；外部系统仍需要幂等键、唯一约束或单调递增的 fencing token。</p>
</div>

<div class="card card-s">
<h3>Informer 与 WorkQueue 在控制循环中的位置</h3>
<table>
<tr><th>工程问题</th><th>组件</th><th>提供的能力</th></tr>
<tr><td>怎样持续观察大量 API 对象，又不在每轮全量请求 API Server</td><td>Informer</td><td>List/Watch、本地 Cache、索引与事件通知</td></tr>
<tr><td>怎样把对象变化交给 worker，并处理去重、延迟和失败重试</td><td>WorkQueue</td><td>按 key 排队、dirty/processing 跟踪、AddAfter、AddRateLimited</td></tr>
<tr><td>怎样决定真正要做的业务动作</td><td>Reconcile</td><td>读取当前期望与实际状态，执行一次幂等修正</td></tr>
</table>
<div class="qa-summary">Controller 是业务控制逻辑；Informer 是观察与缓存基础设施；WorkQueue 是触发、并发和重试基础设施。三者不能混成一条事件回调。</div>
</div>

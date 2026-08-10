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

<div class="card card-m">
<h3>Job 的目标是“满足完成条件”，不是“保持 Pod 常驻”</h3>
<div class="flow" role="list" aria-label="Job 控制链路">
<div class="flow-step" role="listitem"><div class="flow-index">01</div><div class="flow-title">Job spec</div><div class="flow-desc">completions、parallelism、失败与成功策略</div></div>
<div class="flow-step" role="listitem"><div class="flow-index">02</div><div class="flow-title">Job Controller</div><div class="flow-desc">创建/替换 Pod，统计成功与失败</div></div>
<div class="flow-step" role="listitem"><div class="flow-index">03</div><div class="flow-title">kubelet</div><div class="flow-desc">按 restartPolicy 在原 Pod 内处理容器</div></div>
<div class="flow-step" role="listitem"><div class="flow-index">04</div><div class="flow-title">Terminal condition</div><div class="flow-desc">Complete 或 Failed</div></div>
</div>
<p>Job Pod 的 <code>restartPolicy</code> 只能是 <code>Never</code> 或 <code>OnFailure</code>。前者让失败更清楚地落成 Failed Pod，后者可能在同一个 Pod 内重启容器。</p>
</div>

<div class="card card-s">
<h3>四种常见并行模式</h3>
<table>
<tr><th>模式</th><th>关键配置</th><th>完成条件</th></tr>
<tr><td>非并行 Job</td><td>默认 <code>parallelism=1</code>、<code>completions=1</code></td><td>一个 Pod 成功</td></tr>
<tr><td>固定完成数</td><td><code>completions=N</code>、<code>parallelism=M</code></td><td>累计 N 个成功 Pod，最多 M 个并发</td></tr>
<tr><td>Indexed Job</td><td><code>completionMode: Indexed</code></td><td>每个 completion index 成功；适合静态分片</td></tr>
<tr><td>工作队列</td><td>通常不显式设置 completions，由多个 Pod 竞争外部队列</td><td>至少一个 Pod 成功后不再创建新 Pod，并等待其余 Pod 完成</td></tr>
</table>
<p>Indexed Job 会向 Pod 暴露 completion index，可配 <code>backoffLimitPerIndex</code> 和 <code>maxFailedIndexes</code>，避免单个坏分片拖垮全部任务。</p>
</div>

<div class="card card-d">
<h3>失败、超时与成功策略</h3>
<table>
<tr><th>字段</th><th>控制什么</th><th>关键边界</th></tr>
<tr><td><code>backoffLimit</code></td><td>Pod/容器失败累计到多少次后 Job 失败</td><td>默认 6；重试带指数退避</td></tr>
<tr><td><code>backoffLimitPerIndex</code></td><td>Indexed Job 每个 index 独立失败预算</td><td>坏 index 不阻止其他 index 继续</td></tr>
<tr><td><code>podFailurePolicy</code></td><td>按 exit code 或 PodCondition 执行 FailJob / Ignore / Count / FailIndex</td><td>要求 Pod template 使用 <code>restartPolicy: Never</code></td></tr>
<tr><td><code>activeDeadlineSeconds</code></td><td>限制 Job 总运行时长</td><td>优先于 backoffLimit；超时后终止活跃 Pod</td></tr>
<tr><td><code>successPolicy</code></td><td>Indexed Job 满足部分成功规则即可成功</td><td>失败终止策略一旦命中，优先于 successPolicy</td></tr>
<tr><td><code>suspend</code></td><td>暂停 Job</td><td>暂停会终止当前活跃 Pod，恢复后重新创建</td></tr>
</table>
</div>

<div class="card card-w">
<h3>Job 必须按“可能重复执行”设计</h3>
<p>即使 <code>parallelism=1</code>、<code>completions=1</code>、<code>restartPolicy=Never</code>，同一程序仍可能被启动两次，例如控制面尚未确认旧 Pod 状态时创建替代 Pod。因此任务应具备：</p>
<ul>
<li>幂等输出或基于唯一业务键的去重；</li>
<li>checkpoint / 临时文件采用原子提交；</li>
<li>外部锁带租约和 fencing，不能只依赖“只有一个 Pod”；</li>
<li>能够识别并清理上一次尝试留下的不完整结果。</li>
</ul>
</div>

<div class="card card-s">
<h3>完成后的对象与清理</h3>
<table>
<tr><th>对象</th><th>默认行为</th><th>清理方式</th></tr>
<tr><td>Job</td><td>保留 Complete / Failed condition，方便查看状态</td><td>手动删除或设置 <code>ttlSecondsAfterFinished</code></td></tr>
<tr><td>Job Pods</td><td>通常保留，便于查看日志和退出码</td><td>删除 Job 时级联清理；TTL Controller 也可处理</td></tr>
<tr><td>CronJob 产生的 Jobs</td><td>按成功/失败历史上限保留</td><td><code>successfulJobsHistoryLimit</code> / <code>failedJobsHistoryLimit</code></td></tr>
</table>
</div>

<div class="card card-m">
<h3>CronJob 只负责按时间创建 Job</h3>
<table>
<tr><th>字段</th><th>语义</th><th>容易忽略的边界</th></tr>
<tr><td><code>schedule</code></td><td>五段 cron 表达式</td><td>调度是近似的，不是精确到秒的实时调度器</td></tr>
<tr><td><code>timeZone</code></td><td>按 IANA 时区解释 schedule</td><td>未设置时使用 kube-controller-manager 的本地时区</td></tr>
<tr><td><code>startingDeadlineSeconds</code></td><td>错过计划时间后允许补建 Job 的窗口</td><td>过短可能因 Controller 检查周期而始终错过</td></tr>
<tr><td><code>concurrencyPolicy</code></td><td>Allow / Forbid / Replace</td><td>只约束同一个 CronJob 创建的 Jobs</td></tr>
<tr><td><code>suspend</code></td><td>暂停后续调度</td><td>不影响已经启动的 Job；恢复时错过的调度可能被补建</td></tr>
<tr><td>历史上限</td><td>成功默认保留 3，失败默认保留 1</td><td>历史不是日志归档，生产日志仍应外送</td></tr>
</table>
<div class="qa-summary">CronJob 可能在一个计划时间创建两个 Job，也可能漏建；任务必须幂等。<code>concurrencyPolicy: Forbid</code> 只能阻止同一 CronJob 的重叠运行，不能提供全局单例锁。</div>
</div>

<div class="card card-d">
<h3>AI 训练任务的对象选择</h3>
<table>
<tr><th>需求</th><th>对象</th><th>原因</th></tr>
<tr><td>单 Pod 或松耦合批处理</td><td>原生 Job / Indexed Job</td><td>完成数、并行度和失败策略已经足够</td></tr>
<tr><td>多角色、rank、gang、拓扑与弹性恢复</td><td>训练 CRD / Operator</td><td>原生 Job 不理解分布式训练角色和协同生命周期</td></tr>
<tr><td>Kubeflow Trainer v2</td><td><code>TrainJob</code> + TrainingRuntime</td><td>统一替代旧版按框架拆分的 CRD</td></tr>
<tr><td>Kubeflow Training Operator v1</td><td><code>PyTorchJob</code> 等</td><td>属于旧版 framework-specific API，新增系统应明确版本</td></tr>
<tr><td>Volcano 批调度</td><td><code>VolcanoJob</code> / PodGroup</td><td>提供 gang、队列与批任务语义</td></tr>
</table>
</div>

<div class="card card-r">
<h3>批任务排障入口</h3>
<pre><code class="language-bash">kubectl describe job &lt;job&gt;
kubectl get pod -l job-name=&lt;job&gt; -o wide
kubectl logs job/&lt;job&gt; --all-containers
kubectl get job &lt;job&gt; -o jsonpath='{.status.conditions}'
kubectl describe cronjob &lt;cronjob&gt;
kubectl get job --sort-by=.metadata.creationTimestamp</code></pre>
<table>
<tr><th>现象</th><th>先看什么</th></tr>
<tr><td>Job 一直 Active</td><td>Pod phase、退出码、未完成 index、外部队列是否耗尽</td></tr>
<tr><td>Job 很快 Failed</td><td>backoffLimit、activeDeadlineSeconds、podFailurePolicy</td></tr>
<tr><td>同一任务执行两次</td><td>CronJob 近似调度、Pod 替换、任务是否幂等</td></tr>
<tr><td>CronJob 没触发</td><td>suspend、schedule/timeZone、startingDeadlineSeconds、错过次数与 Controller 日志</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: restartPolicy=OnFailure 和 backoffLimit 有什么区别？</div>
<div class="qa-a">
<p><code>restartPolicy=OnFailure</code> 由 kubelet 在同一个 Pod 内重启失败容器；<code>backoffLimit</code> 由 Job Controller 统计失败，决定整个 Job 何时永久失败。前者影响单 Pod 行为，后者影响 Job 级终止条件。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CronJob 的 Forbid 能保证任务只执行一次吗？</div>
<div class="qa-a">
<p>不能。Forbid 只是不在前一个 Job 尚未完成时再启动同一 CronJob 的新 Job；控制面故障、状态确认延迟等仍可能导致重复创建或重复执行。业务侧仍要用幂等写入、去重键或带 fencing 的锁。</p>
</div>
</div>

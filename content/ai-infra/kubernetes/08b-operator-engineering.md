<div class="card card-m">
<h4>Kubebuilder 实战：从脚手架到第一个 Operator</h4>
<p>Kubebuilder 把项目骨架、CRD 生成、RBAC、Webhook、部署 YAML 和测试目录标准化；业务对象建模、幂等 Reconcile、状态机、失败重试、升级与可观测性仍由 Operator 实现。</p>
<table>
<tr><th>步骤</th><th>命令 / 产物</th><th>你要真正理解什么</th></tr>
<tr><td>初始化项目</td><td><code>kubebuilder init --domain example.com --repo github.com/xxx/operator</code></td><td><code>domain</code> 会参与 CRD group，例如 <code>training.ai.example.com</code>；<code>repo</code> 是 Go module 路径</td></tr>
<tr><td>创建 API</td><td><code>kubebuilder create api --group core --version v1 --kind Application --namespaced=true</code></td><td>这里本质是在定义一个 GVK：Group、Version、Kind；同时生成 API 类型、CRD 样例、Controller 骨架</td></tr>
<tr><td>完善类型</td><td><code>api/v1/*_types.go</code></td><td>在 Go struct 中定义 <code>Spec</code> 和 <code>Status</code>，再由 controller-gen 生成 CRD schema 和 deepcopy 代码</td></tr>
<tr><td>实现控制器</td><td><code>internal/controller/*_controller.go</code></td><td>核心不是写事件回调，而是在 <code>Reconcile</code> 中反复读取对象、处理删除、创建/更新下游资源、回写 status</td></tr>
<tr><td>生成清单</td><td><code>make manifests</code>、<code>make install</code></td><td>生成 CRD、RBAC、Webhook 等 YAML，并把 CRD 安装到集群</td></tr>
<tr><td>本地运行</td><td><code>make run</code></td><td>Controller 可在本地连远程 kubeconfig 调试，但 Webhook 调试通常需要额外处理证书和访问路径</td></tr>
<tr><td>部署上线</td><td><code>IMG=xxx make docker-buildx</code>、<code>make build-installer</code></td><td>把 Controller 打成镜像，并生成包含 CRD、RBAC、Deployment 的安装包</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">工程要点</div><p>Kubebuilder 把 Kubernetes controller 的标准结构固化下来：API 类型放在 <code>api/</code>，控制循环放在 <code>internal/controller/</code>，部署资源放在 <code>config/</code>。核心能力仍是把业务对象建模成清晰的 spec/status，并写出幂等、可重试、可观测的 reconcile。</p></div>
<div class="qa-section"><div class="qa-section-title">参考来源</div><p>本节实战流程参考了 <a href="https://www.lixueduan.com/posts/kubernetes/35-build-operator-by-kubebuilder/" target="_blank" rel="noopener">K8s Operator 开发 Part1：快速上手 Kubebuilder，构建你的第一个 K8s Operator</a>，并结合 AI 训练任务 Operator 场景做了重新组织和补充。</p></div>
</div>

<div class="card card-s">
<h4>GVK / GVR：写 Operator 前必须分清的两个标识</h4>
<p>CRD 注册进 API Server 之后，会同时涉及“这个对象是什么”和“我通过 REST 路径怎么访问它”。这就是 GVK 和 GVR 的区别。面试时如果能讲清这个点，说明你不是只会套 Kubebuilder 命令。</p>
<table>
<tr><th>概念</th><th>组成</th><th>更常出现在哪里</th><th>例子</th></tr>
<tr><td>GVK</td><td>Group / Version / Kind</td><td>对象类型识别、Scheme 注册、Controller 处理对象</td><td><code>training.ai.example.com / v1 / TrainingJob</code></td></tr>
<tr><td>GVR</td><td>Group / Version / Resource</td><td>REST 访问、dynamic client、kubectl 资源路径</td><td><code>training.ai.example.com / v1 / trainingjobs</code></td></tr>
<tr><td>核心区别</td><td>Kind 是单数类型名，Resource 通常是复数资源名</td><td>GVK 偏“类型系统”，GVR 偏“API 访问路径”</td><td><code>Kind=Pod</code>，<code>Resource=pods</code></td></tr>
</table>
<div class="qa-summary">面试口径：GVK 用来说明“这是什么类型的对象”，GVR 用来说明“通过哪个 API 资源路径操作它”。Controller 代码里经常关心 GVK/Scheme，动态客户端和 RESTMapper 经常关心 GVR。</div>
</div>

<div class="card card-d">
<h4>Reconcile 代码骨架：Application Demo 到 TrainingJob 的迁移</h4>
<p>参考文章中的 Application Demo 很适合入门：用户提交一个 Application CR，里面包含 <code>spec.image</code> 和 <code>spec.enabled</code>；Controller 根据它创建、更新或删除 Deployment，并把 Deployment 是否 ready 写回 <code>status.ready</code>。把这个例子迁移到 AI 训练场景，就是把 Deployment 换成一组 role 化的 worker/master Pod、Service、ConfigMap、PVC、队列对象和状态机。</p>
<pre><code>// 典型 Reconcile 思路，不是完整可运行代码
func Reconcile(ctx, req) {
  // 1. 根据 namespace/name 获取 CR；NotFound 通常说明对象已删除，直接返回
  job := getTrainingJob(req.NamespacedName)

  // 2. 处理 deletionTimestamp：如果正在删除，先跑 finalizer 清理外部资源
  if job.IsDeleting() {
    cleanupQueueQuota(job)
    cleanupTemporaryCheckpoint(job)
    removeFinalizer(job)
    return
  }

  // 3. 确保 finalizer 存在，保证后续删除前有机会清理外部资源
  ensureFinalizer(job)

  // 4. 根据 spec 计算期望资源：Pod/Service/ConfigMap/PVC/PodGroup 或 Workload
  desired := buildDesiredTrainingResources(job.Spec)

  // 5. 对比实际状态，只做必要的 create/update/delete
  syncOwnedResources(desired)

  // 6. 观察下游资源状态，回写 status.conditions
  updateTrainingJobStatus(job)
}</code></pre>
<table>
<tr><th>Application Demo</th><th>TrainingJob Operator</th><th>设计变化</th></tr>
<tr><td><code>spec.image</code></td><td>镜像、启动命令、role、GPU 数、数据路径</td><td>从单应用部署变成分布式训练拓扑</td></tr>
<tr><td><code>spec.enabled</code></td><td>队列准入、暂停/恢复、重试策略</td><td>是否运行不只是布尔值，还要受 quota、Gang、优先级影响</td></tr>
<tr><td>Deployment ready</td><td>Master/Worker ready、Rendezvous、Checkpoint 心跳</td><td>训练任务 ready 需要结合框架语义</td></tr>
<tr><td><code>status.ready</code></td><td><code>status.phase</code> + <code>conditions</code> + replica 统计 + last error</td><td>状态要能支持排障，而不是只有 true/false</td></tr>
</table>
</div>

<div class="card card-m">
<h4>Webhook：把默认值和校验前移到 Admission 阶段</h4>
<p>Operator 里经常有两类逻辑不要放到 Reconcile 里硬兜底：一类是默认值，一类是非法输入校验。Kubebuilder 可以生成 Webhook 骨架，常见命令是 <code>kubebuilder create webhook --group core --version v1 --kind Application --defaulting --programmatic-validation</code>。</p>
<table>
<tr><th>Webhook 类型</th><th>作用</th><th>Application 例子</th><th>TrainingJob 例子</th></tr>
<tr><td>Mutating Admission Webhook</td><td>给对象补默认值或注入字段</td><td>没有写 <code>enabled</code> 时默认设为 true</td><td>默认 restartPolicy、backoffLimit、checkpoint interval、priorityClass</td></tr>
<tr><td>Validating Admission Webhook</td><td>拒绝非法对象</td><td>校验 <code>spec.image</code> 格式</td><td>校验 GPU 数必须大于 0，worker 数和并行策略匹配，队列名合法</td></tr>
<tr><td>Reconcile</td><td>处理运行时状态收敛</td><td>创建或删除 Deployment</td><td>创建训练资源、等待准入、失败恢复、写 status</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">职责分工</div><p>Webhook 负责“对象能不能进入系统、进入前补什么默认值”，Reconcile 负责“对象已经进入系统后，如何让实际状态收敛”。不要依赖 Reconcile 才发现明显非法的 spec，否则用户会看到对象创建成功但长期失败；也不要在 Webhook 里做耗时外部调用，否则会拖慢 API Server 的写路径。</p></div>
</div>

<div class="card card-w">
<h4>生产级 Operator 检查项</h4>
<p>脚手架只能跑通基本控制循环；生产部署还必须覆盖工程化、稳定性、权限、升级和可观测性。</p>
<table>
<tr><th>维度</th><th>入门 Demo 常见做法</th><th>生产级思考</th></tr>
<tr><td>幂等性</td><td>看到事件就创建资源</td><td>每次 reconcile 都先读实际状态，已存在则比较差异，避免重复创建和重复副作用</td></tr>
<tr><td>OwnerReference</td><td>只创建子资源</td><td>给 Pod/Service/ConfigMap 设置 owner，利用 Kubernetes GC 自动清理内部资源</td></tr>
<tr><td>Finalizer</td><td>可能不处理删除</td><td>清理外部队列占用、对象存储临时目录、实验追踪记录；清理逻辑必须可重试、可超时</td></tr>
<tr><td>Status Conflict</td><td>直接 update status</td><td>处理 resourceVersion 冲突，必要时重试；用 <code>observedGeneration</code> 表示 status 对应哪一版 spec</td></tr>
<tr><td>权限</td><td>给较大的 RBAC</td><td>按最小权限生成和审查 RBAC，避免 Controller 具备不必要的集群级权限</td></tr>
<tr><td>可观测性</td><td>只看日志</td><td>补充 events、conditions、metrics、trace id、reconcile latency、queue depth、error rate</td></tr>
<tr><td>升级兼容</td><td>只有一个版本</td><td>考虑 CRD versioning、conversion webhook、字段废弃策略和向后兼容</td></tr>
</table>
<div class="qa-summary">面试口径：Kubebuilder 帮你生成 Operator 的工程骨架，生产级 Operator 的关键是 API 设计、幂等 Reconcile、删除清理、状态可观测、权限最小化和版本演进。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 如果让你现场设计一个 TrainingJob CRD，你会包含哪些字段？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">核心 spec</div><p>至少包括：镜像、启动命令、replica/role 定义、每个 role 的资源请求、队列名、优先级、重试次数、checkpoint 配置、数据输入输出路径、环境变量和 Secret 引用。</p></div>
<div class="qa-section"><div class="qa-section-title">核心 status</div><p>至少包括：phase、conditions、readyReplicas、activeReplicas、failedReplicas、startTime、completionTime、lastCheckpoint、lastFailureReason、observedGeneration。</p></div>
<div class="qa-section"><div class="qa-section-title">设计原则</div><p>spec 表达用户意图，status 表达系统事实；不要把运行时状态塞回 spec，也不要让用户通过改 status 控制系统。</p></div>
<div class="qa-summary">面试口径：TrainingJob CRD 的设计重点是 role 化资源声明、队列准入、容错恢复和可观测状态，而不是简单包一层 PodTemplate。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: TrainingJob Operator 如何处理删除？为什么需要 Finalizer？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">为什么需要</div><p>OwnerReference 只能清理 Kubernetes 内部子资源，但训练任务可能还占着外部系统资源，例如队列占用、临时 checkpoint、对象存储目录、外部 DNS/Service 注册、实验追踪记录。</p></div>
<div class="qa-section"><div class="qa-section-title">删除流程</div><p>用户删除 TrainingJob 后，对象先进入 deletionTimestamp 状态；Operator 看到后执行外部清理；清理成功后移除 finalizer；API Server 最终真正删除对象。</p></div>
<div class="qa-section"><div class="qa-section-title">常见坑</div><p>如果清理逻辑失败但 finalizer 不移除，对象会一直 Terminating；所以 finalizer 逻辑必须幂等、可重试、可超时，并能把失败原因写入 status/events。</p></div>
<div class="qa-summary">面试口径：Finalizer 是删除前的外部资源清理协议，关键是幂等、可重试和失败可观测。</div>
</div>
</div>

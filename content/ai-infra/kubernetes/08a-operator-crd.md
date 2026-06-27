## 一句话结论

Operator = CRD + Controller：CRD 负责把领域对象注册成 Kubernetes API，Operator 通过幂等 Reconcile 把对象的期望状态持续推进到实际状态。
## 阅读路径

1. 先区分 CRD 和 Operator：CRD 是对象，Operator 是行为。
2. 再看 controller-runtime 如何组织 Reconcile、cache、client、watch 和 webhook。
3. 最后用 TrainingJob / AIJob 这类场景说明如何设计领域对象和生命周期。

<div class="card card-m">
<h3>为什么 Operator 应该单独学</h3>
<p>Operator 是 Kubernetes 扩展体系里最常被深挖的一类问题。它不只是"写个 controller"，而是要把领域对象、状态机、失败恢复、升级回滚和可观测性都建模清楚。AI Infra 里的 TrainingJob、AIJob、RayCluster、InferenceService、GPU 资源画像，都很适合用 Operator 表达。</p>
<table>
<tr><th>概念</th><th>一句话</th><th>面试边界</th></tr>
<tr><td>CRD</td><td>给 Kubernetes 增加一种新的 API 对象</td><td>只有数据和 schema，没有行为</td></tr>
<tr><td>Controller</td><td>watch 对象变化并执行 reconcile</td><td>持续让实际状态逼近期望状态</td></tr>
<tr><td>Operator</td><td>CRD + Controller + 运维知识</td><td>把业务生命周期和故障恢复代码化</td></tr>
</table>
</div>

<div class="card card-d">
<h3>CRD：往 K8s 里加一种新的 API 对象</h3>
<p>CRD（CustomResourceDefinition）就是"我想往集群里多加一种 API 对象"。注册之后，<code>kubectl get xxx</code> 立刻可用，对象也走 API Server / etcd 的标准链路。但 CRD 只是<strong>声明 schema</strong>，没有控制器它就只是一份结构化数据。</p>
<table>
<tr><th>关键字段</th><th>作用</th><th>面试关注点</th></tr>
<tr><td><code>group / version / kind</code></td><td>API 路径，例如 <code>training.example.com/v1alpha1, AIJob</code></td><td>避免和已有 group 冲突，前期用 v1alpha1</td></tr>
<tr><td><code>scope</code></td><td>Namespaced 还是 Cluster</td><td>大部分业务对象 Namespaced，节点级 / 集群级才用 Cluster</td></tr>
<tr><td>OpenAPI v3 schema</td><td>校验字段类型、必填、枚举</td><td>没写 schema 字段会被丢弃；要尽量严格</td></tr>
<tr><td><code>subresources.status</code></td><td>分离 spec 和 status 写权限</td><td>controller 只该写 status，用户只该写 spec</td></tr>
<tr><td><code>subresources.scale</code></td><td>支持 <code>kubectl scale</code> 和 HPA</td><td>需要暴露 replicas 字段</td></tr>
<tr><td><code>additionalPrinterColumns</code></td><td>自定义 <code>kubectl get</code> 列</td><td>用户体验细节</td></tr>
<tr><td>多版本 + conversion</td><td>v1alpha1 → v1beta1 → v1 演进</td><td>需要 conversion webhook 或 None 策略</td></tr>
</table>
<table>
<tr><th>对比</th><th>ConfigMap / Annotation</th><th>CRD</th></tr>
<tr><td>类型校验</td><td>无</td><td>OpenAPI schema 校验</td></tr>
<tr><td>RBAC 粒度</td><td>所有 ConfigMap 是一类</td><td>每种 CRD 是独立资源，单独授权</td></tr>
<tr><td>watch 语义</td><td>所有 ConfigMap 在一个 watch</td><td>每个 CR 独立 watch，scale 更好</td></tr>
<tr><td>语义</td><td>"配置"</td><td>"领域对象"，可以建 controller</td></tr>
</table>
<div class="qa-summary">面试口径：CRD 是给 K8s 加新对象，schema + status 子资源 + 多版本 conversion 是工程化要点；CRD 本身只是声明，要靠 Operator 给它注入行为。</div>
</div>

<div class="card card-w">
<h3>CRD 版本演进：v1alpha1 → v1beta1 → v1</h3>
<p>CRD 版本演进不是简单改 <code>apiVersion</code>。面试官问这个点时，通常想看你是否理解 API 兼容性、<code>served</code> / <code>storage</code>、conversion webhook 和存量对象迁移。</p>
<table>
<tr><th>阶段</th><th>语义</th><th>工程承诺</th></tr>
<tr><td><code>v1alpha1</code></td><td>试验版</td><td>字段和语义可能变化，兼容性承诺弱</td></tr>
<tr><td><code>v1beta1</code></td><td>相对稳定版</td><td>字段基本稳定，开始认真处理兼容和迁移</td></tr>
<tr><td><code>v1</code></td><td>稳定版</td><td>强兼容承诺，不能随意删除字段或改变字段语义</td></tr>
</table>
<table>
<tr><th>字段</th><th>含义</th><th>面试重点</th></tr>
<tr><td><code>served</code></td><td>这个版本是否对外提供 API 访问</td><td>老客户端还在用旧版本时要保持 <code>served: true</code></td></tr>
<tr><td><code>storage</code></td><td>etcd 中对象实际存储使用哪个版本</td><td>只能有一个版本 <code>storage: true</code></td></tr>
<tr><td>conversion webhook</td><td>不同版本 schema 不兼容时的转换逻辑</td><td>字段改名、拆分、合并时必须考虑信息是否丢失</td></tr>
</table>
<pre><code class="language-yaml">spec:
  versions:
    - name: v1alpha1
      served: true
      storage: false
    - name: v1beta1
      served: true
      storage: true
    - name: v1
      served: false
      storage: false</code></pre>
<div class="qa-summary">一句话：可以多个版本同时 served，但只能一个版本 storage；字段结构变化时用 conversion webhook 保护老对象和老客户端。</div>
</div>

<div class="card card-s">
<h3>版本升级流程：以 AIJob 为例</h3>
<p>假设 <code>v1alpha1</code> 里是扁平字段，后来 <code>v1beta1</code> 想改成结构化字段：</p>
<pre><code class="language-yaml"># v1alpha1
spec:
  gpuCount: 8
  modelName: resnet50

# v1beta1
spec:
  resources:
    gpu:
      count: 8
  workload:
    model: resnet50</code></pre>
<table>
<tr><th>步骤</th><th>动作</th><th>原因</th></tr>
<tr><td>1</td><td>新增 <code>v1beta1</code>，保留 <code>v1alpha1 served=true</code></td><td>老客户端和老 YAML 还能继续用</td></tr>
<tr><td>2</td><td>选择 <code>v1beta1 storage=true</code></td><td>新写入对象统一存新版本</td></tr>
<tr><td>3</td><td>实现 conversion webhook</td><td>把 <code>gpuCount</code> 映射到 <code>resources.gpu.count</code></td></tr>
<tr><td>4</td><td>controller 内部使用 hub version</td><td>业务逻辑不感知多个外部 API 版本</td></tr>
<tr><td>5</td><td>迁移存量对象</td><td>切 storage version 不会自动重写 etcd 里的所有旧对象</td></tr>
<tr><td>6</td><td>观测旧版本访问量</td><td>确认没有老客户端后再下线旧版本</td></tr>
<tr><td>7</td><td>将 <code>v1alpha1 served=false</code>，最终稳定到 <code>v1</code></td><td>完成兼容窗口后的清理</td></tr>
</table>
<div class="qa-summary">面试口径：先多版本共存，再 conversion，再 storage migration，最后下线旧 served version；不能直接删旧字段。</div>
</div>

<div class="card card-w">
<h3>Operator 模式：把运维知识代码化</h3>
<p>Operator = CRD + Controller。设计 Operator 的本质是回答："给我一份期望状态（spec），我要怎么不断地把世界（status）调成那样？"这就是 Reconcile 循环。</p>
<table>
<tr><th>概念</th><th>作用</th><th>面试关注点</th></tr>
<tr><td>Reconcile 循环</td><td>对每个 CR 反复执行"看现状 → 算差异 → 操作 → 写 status"</td><td>必须幂等，能容忍重复触发</td></tr>
<tr><td>Informer / Workqueue</td><td>List/Watch 缓存 + 限速队列</td><td>避免直接打 API Server</td></tr>
<tr><td>Owner Reference</td><td>子对象指向父 CR</td><td>父 CR 删除时级联删除子对象（GC）</td></tr>
<tr><td>Finalizer</td><td>删除前的 cleanup hook</td><td>常见用法：先回收云资源再让对象真正删除</td></tr>
<tr><td>Status conditions</td><td>多维度状态（Ready / Progressing / Degraded）</td><td>不要把所有状态压成一个 phase 字符串</td></tr>
<tr><td>Leader election</td><td>多副本只让一个 reconcile</td><td>用 Lease 对象</td></tr>
<tr><td>事件 record</td><td>给用户可见的反馈</td><td><code>kubectl describe</code> 能看到</td></tr>
</table>
<table>
<tr><th>层级</th><th>OperatorHub 推荐的成熟度</th></tr>
<tr><td>Level 1 Basic Install</td><td>装得上、跑得起来</td></tr>
<tr><td>Level 2 Seamless Upgrades</td><td>支持升级，不丢数据</td></tr>
<tr><td>Level 3 Full Lifecycle</td><td>备份 / 故障恢复 / 配置变更</td></tr>
<tr><td>Level 4 Deep Insights</td><td>提供监控指标、告警</td></tr>
<tr><td>Level 5 Auto Pilot</td><td>自愈、自动 scale、自动调参</td></tr>
</table>
<div class="qa-summary">面试口径：Operator = CRD + 幂等 Reconcile；从 install 到 auto-pilot 共 5 个成熟度等级，AI 训练平台的目标至少是 Level 3。</div>
</div>

<div class="card card-s">
<h3>controller-runtime：写 Operator 的标准库</h3>
<p>kubebuilder / Operator SDK 都是基于 controller-runtime 的脚手架。它把 Informer、Workqueue、Manager、Webhook 都封装好了，让开发者主要关注 Reconcile 函数。</p>
<table>
<tr><th>组件</th><th>作用</th></tr>
<tr><td><code>Manager</code></td><td>管 leader election、metrics、health、shared cache 和多个 controller 的生命周期</td></tr>
<tr><td><code>Cache</code></td><td>每个 GVK 一个 informer，Reconcile 读缓存而不是直连 API Server</td></tr>
<tr><td><code>Client</code></td><td>读用 cache，写直连 API Server</td></tr>
<tr><td><code>Predicate</code></td><td>过滤事件，避免无意义 reconcile</td></tr>
<tr><td><code>Builder</code></td><td>声明"我要 watch 哪些资源、Owns 哪些子对象"</td></tr>
<tr><td><code>Webhook</code></td><td>同进程跑 admission / conversion / defaulting webhook</td></tr>
</table>
<table>
<tr><th>常见坑</th><th>说明</th></tr>
<tr><td>读到旧缓存</td><td>cache 是异步同步，写完立刻 reconcile 可能读不到自己的写入；要么重新入队，要么用 no-cache client</td></tr>
<tr><td>无限 reconcile</td><td>每次 update 都触发新事件，要在 spec 没变时不更新对象</td></tr>
<tr><td>Status 和 Spec 一起写</td><td>违反 status 子资源语义，建议分两次 update</td></tr>
<tr><td>finalizer 写错</td><td>不能正确退出会让对象永远 Terminating</td></tr>
<tr><td>多 controller 写同一对象</td><td>易冲突，要明确 owner / 字段所有权</td></tr>
</table>
</div>

<div class="card card-m">
<h3>AIJob Operator 设计抓手</h3>
<p>如果面试官让你设计一个 AI 训练 Operator，不要只说"创建 Pod"。要围绕任务语义和生命周期展开。</p>
<table>
<tr><th>设计点</th><th>应该包含什么</th><th>为什么重要</th></tr>
<tr><td>Spec</td><td>framework、role/replica、GPU 资源、队列、minAvailable、checkpoint、容错策略</td><td>表达训练任务，而不是简单包装 PodTemplate</td></tr>
<tr><td>Status</td><td>phase、conditions、ready/failed workers、reason、start/finish time、predictionRef</td><td>用户排查和平台自动化都依赖 status</td></tr>
<tr><td>子对象</td><td>PodGroup / Pods / Service / ConfigMap / PredictionResult</td><td>通过 OwnerReference 做生命周期管理</td></tr>
<tr><td>Finalizer</td><td>删除前清理外部 checkpoint、队列占用、临时资源</td><td>避免外部资源泄漏</td></tr>
<tr><td>Reconcile</td><td>创建缺失对象、修复漂移、处理失败重试、更新 status</td><td>保证最终一致和自愈</td></tr>
</table>
</div>

<div class="card card-m">
<h3>Operator 与 CRD 高频问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CRD 和 ConfigMap 都能存配置，为什么还要 CRD？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从校验、RBAC、watch、语义四个维度比较。</p>
<div class="qa-section"><div class="qa-section-title">1. 类型校验</div><p>ConfigMap 没有 schema，错字段悄悄过；CRD 有 OpenAPI schema，错字段直接被拒。</p></div>
<div class="qa-section"><div class="qa-section-title">2. RBAC 粒度</div><p>所有 ConfigMap 是一种资源，难做"只允许改训练任务但不能改其他配置"；CRD 每种是独立资源，可以单独授权。</p></div>
<div class="qa-section"><div class="qa-section-title">3. watch 与扩展性</div><p>所有 ConfigMap 在同一个 informer，对象多了相互干扰；CRD 每种独立 watch、独立 cache，扩展性更好。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 语义与控制器</div><p>ConfigMap 表达"配置"；CRD 表达"领域对象"，可以挂自己的 Operator 跑 reconcile，业务语义清晰。</p></div>
<div class="qa-summary">面试口径：CRD 不是为了"放得下"，而是为了"管得住"：schema、RBAC、watch、controller 全部独立。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Operator 的 Reconcile 为什么必须幂等？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从触发模型反推。</p>
<div class="qa-section"><div class="qa-section-title">1. 重复触发是常态</div><p>Reconcile 由 watch 事件、resync 周期、自身 update、错误重入队等触发，同一个对象会被反复 reconcile。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 幂等的含义</div><p>同一 spec + 同一现状跑一次和跑十次结果一致；不能"已经创建子对象了再创建一次会冲突"。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 实现要点</div><p>用 GET + 比较 + Update/Patch；创建子对象时用 controllerutil.CreateOrUpdate；写状态前看是否真的变了再写。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 反模式</div><p>每次 reconcile 都改 spec → 触发新事件 → 再次 reconcile → 死循环；要严格区分谁写 spec 谁写 status。</p></div>
<div class="qa-summary">面试口径：K8s 的控制循环是"事件多、可能丢、可能重复"，所以 Reconcile 必须无条件幂等，并且 spec / status 写权严格分离。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么时候不该用 Operator？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>避免"什么都包成 Operator"的过度工程化。</p>
<div class="qa-section"><div class="qa-section-title">1. 一次性脚本</div><p>就是初始化建几个对象，写个 Helm hook 或 Job 即可，不需要长期 reconcile。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 没有持续运维语义</div><p>对象创建后不需要持续守护、不需要根据外部状态调节，CRD 没意义。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 跨集群编排</div><p>跨集群编排是 Fleet / ApplicationSet 的职责，不是单集群 Operator 的舞台。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 替代方案足够</div><p>静态策略用 VAP，资源调度用 scheduler plugin，发布用 GitOps，能不写 controller 就不写。</p></div>
<div class="qa-summary">面试口径：Operator 是为了"持续运维知识代码化"。一次性、无外部状态、跨集群这三类场景，要优先选别的扩展点。</div>
</div>
</div>

</div>

## 关联模块

- `Workload 与 Controller`：理解 controller / reconcile 的基础。
- `Scheduler 插件与扩展`：理解调度逻辑不应该塞进 Operator。
- `AI Infra：GPU / 批调度 / DRA`：理解 AIJob、PodGroup、GPU 资源语义。
- `扩展与工程化`：理解 Operator 如何被 Helm、Kustomize、GitOps 部署和发布。

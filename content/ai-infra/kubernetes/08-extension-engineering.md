<div class="card card-m">
<h3>本 Tab 想说清楚什么</h3>
<p>K8s 真正吸引人的不是"跑容器"，而是它<strong>把自己写成了一个可以被扩展的平台</strong>：你可以加资源类型（CRD）、加控制器（Operator）、加调度策略（Scheduler Plugin）、加准入（VAP / Webhook）、加资源粒度（DRA），还可以把所有 YAML 用 Helm / Kustomize 工程化、用 GitOps 自动同步到集群。这是 AI Infra 工程师真实工作的舞台。</p>
<table>
<tr><th>扩展点</th><th>解决什么问题</th><th>本 Tab 重点</th></tr>
<tr><td>CRD</td><td>定义新的 API 对象</td><td>Schema、版本、conversion、Status/Spec 划分</td></tr>
<tr><td>Operator</td><td>把"运维知识"代码化</td><td>controller-runtime、Reconcile、finalizer、owner reference</td></tr>
<tr><td>API 扩展</td><td>聚合 API、自定义 server</td><td>aggregation layer 简介</td></tr>
<tr><td>Scheduler 插件</td><td>自定义调度逻辑</td><td>已在 Scheduler 内部机制 Tab，本 Tab 仅做衔接</td></tr>
<tr><td>包管理 / 配置工程化</td><td>YAML 太多怎么办</td><td>Helm vs Kustomize</td></tr>
<tr><td>GitOps</td><td>怎么把集群当代码管</td><td>ArgoCD / Flux、Pull vs Push 模型</td></tr>
</table>
</div>

<div class="card card-d">
<h3>CRD：往 K8s 里加一种新的 API 对象</h3>
<p>CRD（CustomResourceDefinition）就是"我想往集群里多加一种 API 对象"。注册之后，<code>kubectl get xxx</code> 立刻可用，对象也走 API Server / etcd 的标准链路。但 CRD 只是<strong>声明 schema</strong>，没有控制器它就只是一坨数据。</p>
<table>
<tr><th>关键字段</th><th>作用</th><th>面试关注点</th></tr>
<tr><td><code>group / version / kind</code></td><td>API 路径，例如 <code>training.example.com/v1alpha1, Job</code></td><td>避免和已有 group 冲突，前期用 v1alpha1</td></tr>
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
<div class="qa-summary">面试口径：CRD 是给 K8s 加新对象，<strong>schema + status 子资源 + 多版本 conversion</strong> 是工程化要点；CRD 本身只是声明，要靠 Operator 给它注入"行为"。</div>
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
<tr><th>层级</th><th>OperatorHub 推荐的"成熟度"</th></tr>
<tr><td>Level 1 Basic Install</td><td>装得上、跑得起来</td></tr>
<tr><td>Level 2 Seamless Upgrades</td><td>支持升级，不丢数据</td></tr>
<tr><td>Level 3 Full Lifecycle</td><td>备份 / 故障恢复 / 配置变更</td></tr>
<tr><td>Level 4 Deep Insights</td><td>提供监控指标、告警</td></tr>
<tr><td>Level 5 Auto Pilot</td><td>自愈、自动 scale、自动调参</td></tr>
</table>
<div class="qa-summary">面试口径：Operator = CRD + 幂等 Reconcile；从 install 到 auto-pilot 共 5 个成熟度等级，AI 训练平台的目标至少是 Level 3（任务全生命周期 + 故障恢复）。</div>
</div>

<div class="card card-s">
<h3>controller-runtime：写 Operator 的标准库</h3>
<p>kubebuilder / Operator SDK 都是基于 controller-runtime 的脚手架。它把 Informer、Workqueue、Manager、Webhook 都封装好了，让开发者只关心 Reconcile 函数。</p>
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
<tr><td>读到旧缓存</td><td>cache 是异步同步，写完立刻 reconcile 可能读不到自己的写入；要么重新入队，要么用 Get with no-cache</td></tr>
<tr><td>无限 reconcile</td><td>每次 update 都触发新事件，要在 spec 没变时不更新对象</td></tr>
<tr><td>Status 和 Spec 一起写</td><td>违反 status 子资源语义，建议分两次 update</td></tr>
<tr><td>finalizer 写错</td><td>不能正确退出会让对象永远 Terminating</td></tr>
<tr><td>多 controller 写同一对象</td><td>易冲突，要明确 owner / 字段所有权</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Helm：包管理与版本化的 release</h3>
<p>Helm 把一组 YAML 模板打包成 Chart，渲染时用 values 注入参数；安装后会在集群里创建一个 release，可以 upgrade / rollback / uninstall。它解决"YAML 反复抄"和"我装的是哪个版本"。</p>
<table>
<tr><th>对象</th><th>作用</th></tr>
<tr><td>Chart</td><td>包含 templates / values.yaml / Chart.yaml</td></tr>
<tr><td>values.yaml</td><td>默认参数，用户可以覆盖</td></tr>
<tr><td>helpers (_helpers.tpl)</td><td>命名前缀、label 标准化等模板片段</td></tr>
<tr><td>release</td><td>一次安装的实例，记录 revision，支持回滚</td></tr>
<tr><td>hooks</td><td>install / upgrade / delete 前后的钩子任务</td></tr>
<tr><td>dependencies</td><td>子 chart，例如装 Operator 时同时装 CRD chart</td></tr>
</table>
<table>
<tr><th>能力</th><th>Helm</th><th>Kustomize</th></tr>
<tr><td>核心思路</td><td>模板 + 参数</td><td>原生 YAML + Overlay 补丁</td></tr>
<tr><td>语法</td><td>Go template，比较"密"</td><td>纯 YAML，结构清晰</td></tr>
<tr><td>版本管理</td><td>有 release / revision</td><td>没有，靠 Git 提交</td></tr>
<tr><td>升级 / 回滚</td><td><code>helm upgrade / rollback</code></td><td>靠 GitOps 工具</td></tr>
<tr><td>条件分支</td><td>强（<code>{{ if }}</code>）</td><td>弱，靠多 overlay</td></tr>
<tr><td>典型场景</td><td>分发可参数化的中间件</td><td>同一份基线，差异化部署到 dev/staging/prod</td></tr>
<tr><td>组合用法</td><td colspan="2">Chart 内部用 Helm 模板，外部环境差异用 Kustomize overlay：<code>helm template ... | kustomize build</code></td></tr>
</table>
</div>

<div class="card card-w">
<h3>Kustomize：base + overlay 的纯 YAML 工程化</h3>
<p>Kustomize 思路是<strong>不引入模板语言</strong>：先有一份纯 YAML（base），各环境用 overlay 描述差异（patch、replicas、image、namespace、labels）。</p>
<table>
<tr><th>原语</th><th>作用</th></tr>
<tr><td><code>resources</code></td><td>本 layer 引用的 YAML 文件 / 子目录</td></tr>
<tr><td><code>namespace / commonLabels / commonAnnotations</code></td><td>批量改本层所有对象</td></tr>
<tr><td><code>images</code></td><td>替换镜像 tag</td></tr>
<tr><td><code>replicas</code></td><td>调整 replica 数</td></tr>
<tr><td><code>patches</code></td><td>strategic merge / JSON patch 改字段</td></tr>
<tr><td><code>configMapGenerator / secretGenerator</code></td><td>从文件 / literal 生成 ConfigMap / Secret，附带 hash 后缀</td></tr>
<tr><td><code>components</code></td><td>可复用的"功能片段"</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">什么时候选谁？</div><p><strong>分发给外部用户的中间件 / Operator</strong>用 Helm（要参数化、要 release 概念）；<strong>自家平台多环境部署</strong>用 Kustomize（要清晰的 diff）；两者也能组合：Helm 渲染出来的 YAML 再用 Kustomize 做环境差异化。</p></div>
</div>

<div class="card card-d">
<h3>GitOps：把"集群状态"也写进 Git</h3>
<p>GitOps 不是工具，是工作模型：<strong>Git 是唯一真相，集群状态由 Git 持续 reconcile 出来</strong>。所有变更都走 PR + Review，不再人肉 <code>kubectl apply</code>。</p>
<table>
<tr><th>原则</th><th>含义</th></tr>
<tr><td>声明式</td><td>所有期望状态用声明式 YAML 表达</td></tr>
<tr><td>版本化 + 不可变</td><td>Git 提交即审计；同一 commit 在不同时间渲染结果一致</td></tr>
<tr><td>自动化拉取</td><td>Agent 在集群里持续 pull / sync</td></tr>
<tr><td>持续 reconcile</td><td>偏离期望状态会被自动纠回（drift detection）</td></tr>
</table>
<table>
<tr><th>对比</th><th>ArgoCD</th><th>Flux</th></tr>
<tr><td>架构</td><td>有 UI server + 多 controller</td><td>多个 controller（source / kustomize / helm / notification）</td></tr>
<tr><td>UI</td><td>原生 Web UI 强</td><td>较轻，常配合 Weave GitOps UI</td></tr>
<tr><td>多集群</td><td>ApplicationSet + cluster generator</td><td>Flux 多 cluster bootstrap</td></tr>
<tr><td>Helm 支持</td><td>支持（渲染或 chart）</td><td>支持（HelmRelease 控制器）</td></tr>
<tr><td>Kustomize 支持</td><td>原生</td><td>原生（Kustomization controller）</td></tr>
<tr><td>渐进交付</td><td>结合 Argo Rollouts</td><td>结合 Flagger</td></tr>
<tr><td>可观测</td><td>UI 直接看 sync 状态、diff</td><td>主要靠 metrics + CLI</td></tr>
</table>
<div class="qa-summary">面试口径：GitOps = "Git 是真相 + 集群里有 agent 持续 sync + 偏离自动纠回"。ArgoCD UI 友好、生态丰富，Flux 更轻量、controller 拼装灵活；选谁看团队偏好和多集群规模。</div>
</div>

<div class="card card-s">
<h3>渐进式发布与 K8s 原生回滚</h3>
<p>真正生产里发布从来不是 <code>kubectl apply</code> 一把梭。要分清"K8s 自带的滚动发布"和"渐进式发布工具（Argo Rollouts / Flagger）"的边界。</p>
<table>
<tr><th>能力</th><th>K8s 原生 Deployment</th><th>Argo Rollouts / Flagger</th></tr>
<tr><td>滚动更新</td><td>maxSurge / maxUnavailable</td><td>支持，且每步可以手动审批</td></tr>
<tr><td>金丝雀 / 蓝绿</td><td>需要拆两个 Service，复杂</td><td>原生 Canary / BlueGreen 策略</td></tr>
<tr><td>自动 metrics 分析</td><td>无</td><td>用 Prometheus / Datadog 做发布门禁</td></tr>
<tr><td>回滚</td><td><code>kubectl rollout undo</code> 回到上一 revision</td><td>失败自动回滚 + 审计</td></tr>
<tr><td>结合 Service Mesh</td><td>需要自己写规则</td><td>原生支持 Istio / Linkerd / SMI</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">面试口径</div><p>普通业务用 Deployment + RollingUpdate 已经够；对外重要服务建议用 Argo Rollouts 做 canary + metrics 门禁，把"判断这次发布健康吗"从人工眼神切换成自动化指标。</p></div>
</div>

<div class="card card-m">
<h3>扩展点全景图：什么需求接哪个扩展点</h3>
<table>
<tr><th>需求</th><th>该用哪个扩展点</th><th>原因</th></tr>
<tr><td>新增一种业务对象（TrainingJob、Tenant）</td><td>CRD + Operator</td><td>声明式建模业务实体</td></tr>
<tr><td>静态准入策略（禁特权、强制 label）</td><td>ValidatingAdmissionPolicy（CEL）</td><td>无需部署 webhook，毫秒级</td></tr>
<tr><td>动态准入（查外部系统）</td><td>Validating / Mutating Webhook</td><td>能跑任意逻辑</td></tr>
<tr><td>调度策略（拓扑、组调度、Backfill）</td><td>Scheduler Plugin（Filter / Score / PreBind）</td><td>调度内核内嵌扩展</td></tr>
<tr><td>新种类设备 / 资源</td><td>DRA（DeviceClass + ResourceClaim）</td><td>替代 Device Plugin，支持复杂 attributes</td></tr>
<tr><td>新存储后端</td><td>CSI Driver</td><td>统一卷接口</td></tr>
<tr><td>新网络方案</td><td>CNI Plugin</td><td>Pod 网络模型扩展</td></tr>
<tr><td>聚合 API（自己提供 K8s 风格 API）</td><td>API Aggregation Layer</td><td>复用 RBAC、kubectl，但服务自管</td></tr>
<tr><td>跨集群同步对象</td><td>Operator + GitOps（ArgoCD ApplicationSet）</td><td>避免一致性靠人</td></tr>
<tr><td>把 YAML 工程化</td><td>Helm + Kustomize</td><td>分别解决参数化和环境 overlay</td></tr>
</table>
<div class="qa-summary">面试口径：选扩展点先问"我是要加一个对象、还是改调度、还是改网络/存储/准入"，然后选最贴合的扩展点。能用内置（VAP、Scheduler Plugin、DRA）就别上独立 webhook / sidecar，控制面稳定性更重要。</div>
</div>

<div class="card card-m">
<h3>扩展与工程化高频问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CRD 和 ConfigMap 都能存配置，为什么还要 CRD？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从校验、RBAC、watch、语义四个维度比较。</p>
<div class="qa-section"><div class="qa-section-title">1. 类型校验</div><p>ConfigMap 没有 schema，错字段悄悄过；CRD 有 OpenAPI schema，错字段直接被拒。</p></div>
<div class="qa-section"><div class="qa-section-title">2. RBAC 粒度</div><p>所有 ConfigMap 是一种资源，难做"只允许改训练任务但不能改其他配置"；CRD 每种是独立资源，可以单独授权。</p></div>
<div class="qa-section"><div class="qa-section-title">3. watch 与扩展性</div><p>所有 ConfigMap 在同一个 informer，对象多了相互干扰；CRD 每种独立 watch、独立 cache，扩展性更好。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 语义与控制器</div><p>ConfigMap 表达"配置"；CRD 表达"领域对象"，可以挂自己的 Operator 跑 reconcile，业务语义清晰。</p></div>
<div class="qa-summary">面试口径：CRD 不是为了"放得下"，而是为了"管得住"——schema、RBAC、watch、controller 全部独立，是建模业务实体的正路。</div>
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
<div class="qa-q">Q: Helm 和 Kustomize 怎么选？能一起用吗？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从分发场景和组合用法回答。</p>
<div class="qa-section"><div class="qa-section-title">1. 各自的强项</div><p>Helm 强在<strong>参数化分发</strong>，适合发布给外部用户的中间件；Kustomize 强在<strong>多环境 overlay</strong>，适合自家平台 dev/staging/prod 差异化部署。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 各自的痛点</div><p>Helm 模板语法重，YAML 一旦复杂就难以审阅；Kustomize 没有 release 概念，回滚要靠 Git。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 组合用法</div><p>常见做法：第三方 Operator 用 Helm 渲染，再用 Kustomize 做环境差异；或者 ArgoCD Application 同时声明 Helm + Kustomize。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 结论</div><p>没有银弹。GitOps 落地里，"Helm 做包，Kustomize 做层"是非常常见的搭配。</p></div>
<div class="qa-summary">面试口径：Helm 解决参数化和分发，Kustomize 解决环境 overlay；生产里两者经常组合，Helm 渲染 + Kustomize 差异化。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 什么是 GitOps？为什么是 pull 模型？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从动机讲到实现，把 pull 的理由说清楚。</p>
<div class="qa-section"><div class="qa-section-title">1. 动机</div><p>"集群状态"必须可审计、可回放、可恢复。Git 是天然的版本化、有 Review 流程的真相。</p></div>
<div class="qa-section"><div class="qa-section-title">2. Pull 模型</div><p>集群里跑 agent（ArgoCD / Flux），定期从 Git 拉最新期望状态并 reconcile。CI 不需要拥有集群凭据，安全边界更小。</p></div>
<div class="qa-section"><div class="qa-section-title">3. Drift 自动纠回</div><p>有人手工 <code>kubectl apply</code> 改了对象，agent 会检测到并恢复成 Git 中的版本，强制变更走 PR。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 配套</div><p>多集群用 ApplicationSet / Flux multi-cluster；渐进式发布配 Argo Rollouts 或 Flagger；Secret 配 SealedSecrets / SOPS / External Secrets。</p></div>
<div class="qa-summary">面试口径：GitOps = Git 是真相 + 集群 agent 持续 pull + drift 自动纠回；pull 模型让 CI 系统不持有集群凭据，更安全。</div>
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

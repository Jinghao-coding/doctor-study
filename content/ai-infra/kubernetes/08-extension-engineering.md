## 一句话结论

K8S 工程化要区分“扩展能力”和“交付能力”：CRD / Operator 负责建模和控制循环，Helm / Kustomize / GitOps / 渐进式发布负责把这些对象安全、可审计地交付到集群。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Kubernetes 核心 |
| 章节类型 | 系统类 |
| 解决问题 | 梳理 Helm、Kustomize、GitOps、ArgoCD/Flux、渐进式发布，以及不同 Kubernetes 扩展点如何选型。 |
| 面试抓手 | Operator 与 CRD 已拆到单独章节；本节重点讲工程化交付、发布回滚和扩展点选型。 |

## 阅读路径

1. 先看 Helm / Kustomize：解决 YAML 参数化和多环境差异。
2. 再看 GitOps：解决集群状态审计、同步和漂移修复。
3. 最后看扩展点选型：不同需求应该接 CRD、Webhook、Scheduler Plugin、DRA、CSI、CNI 还是 GitOps。

<div class="card card-m">
<h3>本 Tab 想说清楚什么</h3>
<p>Kubernetes 平台工程不只是写 YAML，而是要把对象建模、配置渲染、环境差异、发布回滚、审计和漂移修复串起来。<strong>Operator 与 CRD 的设计细节已经拆到“Operator 与 CRD”章节</strong>；本节只保留工程化交付和扩展点选型。</p>
<table>
<tr><th>主题</th><th>解决什么问题</th><th>本节重点</th></tr>
<tr><td>Helm</td><td>如何把一组 YAML 参数化、版本化发布</td><td>Chart、values、release、upgrade / rollback</td></tr>
<tr><td>Kustomize</td><td>如何维护 dev / staging / prod 的环境差异</td><td>base + overlay、patch、images、replicas</td></tr>
<tr><td>GitOps</td><td>如何把集群状态纳入 Git 审计和自动同步</td><td>ArgoCD / Flux、pull 模型、drift correction</td></tr>
<tr><td>渐进式发布</td><td>如何降低发布风险</td><td>Deployment rolling update、Argo Rollouts、Flagger</td></tr>
<tr><td>扩展点选型</td><td>什么需求应该接哪个 Kubernetes 扩展点</td><td>CRD/Operator、Webhook、Scheduler Plugin、DRA、CSI、CNI</td></tr>
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
<tr><td>新增一种业务对象（AIJob、Tenant）</td><td>CRD + Operator</td><td>声明式建模业务实体</td></tr>
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



</div>

## 面试回答

**30 秒版：**

K8S 工程化交付要区分 Helm、Kustomize、GitOps、渐进式发布和不同扩展点选型。Operator 与 CRD 单独成章，本节重点讲如何安全交付和持续同步。

**2 分钟版：**

我会先把问题拆成两层：第一层是扩展点选型，新增业务对象用 CRD + Operator，动态准入用 Webhook，调度策略用 Scheduler Plugin，设备资源用 DRA，网络和存储分别用 CNI / CSI；第二层是交付工程化，Helm 解决参数化分发，Kustomize 解决多环境 overlay，GitOps 让 Git 成为集群期望状态的唯一真相，ArgoCD / Flux 在集群里持续 pull 并修正 drift。发布高风险服务时，再用 Argo Rollouts / Flagger 做 canary、blue-green 和 metrics 门禁。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

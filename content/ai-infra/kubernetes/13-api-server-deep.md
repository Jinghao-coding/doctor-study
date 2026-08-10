## 请求处理全链路

<div class="card card-m">
<h3>请求处理五阶段</h3>
<p>所有发往 API Server 的 REST 请求（kubectl、client-go、controller、kubelet）都经过同一条处理链：</p>
<pre><code>HTTP Request
  │
  ├─ 1. Authentication（认证）
  │     → 你是谁？从请求中提取身份信息（user/group）
  │     → 失败返回 401 Unauthorized
  │
  ├─ 2. Authorization（鉴权）
  │     → 你有权限做这个操作吗？RBAC/ABAC/Node/Webhook
  │     → 失败返回 403 Forbidden
  │
  ├─ 3. Admission Control（准入控制）
  │     → 修改/校验对象，执行语义策略
  │     a. Mutating Webhooks（可修改对象）
  │     b. Object Schema Validation（内置校验）
  │     c. Validating Webhooks（只能批准/拒绝）
  │     → 失败返回 403/422
  │
  ├─ 4. Validation（验证）
  │     → 内置字段校验（格式、必填字段、immutable 字段）
  │     → CRD 有 OpenAPI schema 校验
  │     → 失败返回 422 Unprocessable Entity
  │
  └─ 5. Storage（持久化）
        → 写入 etcd（RESTStorage → etcd3 storage backend）
        → 触发 watch 事件通知所有 watcher
        → 返回结果给客户端
</code></pre>
<p>注意：<strong>读请求（GET/LIST/WATCH）经过认证和鉴权，但跳过 Admission 和 Validation</strong>（Webhook 可以配置对读请求生效，但通常不这么做）。</p>
</div>

## 1. Authentication（认证）

<div class="card card-s">
<h3>认证方式</h3>
<p>API Server 支持多种认证方式，按顺序尝试，任一成功即通过：</p>
<table>
<tr><th>认证方式</th><th>使用场景</th><th>凭证位置</th></tr>
<tr><td>X.509 Client Cert</td><td>管理员 kubeconfig、kubelet/etcd 组件认证</td><td><code>--client-ca-file</code> 指定 CA，证书 CN/O 映射为 user/group</td></tr>
<tr><td>Bearer Token / ServiceAccount</td><td>Pod 内应用访问 API</td><td>ServiceAccount Admission 自动注入 projected volume: <code>/var/run/secrets/kubernetes.io/serviceaccount/token</code></td></tr>
<tr><td>Bootstrap Token</td><td>kubelet TLS bootstrapping</td><td>kube-system 中 bootstrap token secret</td></tr>
<tr><td>OIDC (OpenID Connect)</td><td>集成企业 SSO（如 Okta、Dex）</td><td><code>Authorization: Bearer &lt;id_token&gt;</code></td></tr>
<tr><td>Webhook Token Authenticator</td><td>自定义认证服务（对接内部鉴权系统）</td><td>Bearer token 通过 webhook POST 到外部服务验证</td></tr>
<tr><td>Node Authorizer + Node Restriction</td><td>kubelet 认证（专用）</td><td>kubelet client cert 用户名 <code>system:node:&lt;nodeName&gt;</code></td></tr>
</table>
<pre><code class="language-yaml"># ServiceAccount 自动挂载到 Pod 中的 token（projected volume）
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: my-sa
  containers:
  - name: app
    # /var/run/secrets/kubernetes.io/serviceaccount/ 包含：
    #   token → JWT token（audience-bound, time-limited in K8s 1.21+）
    #   ca.crt → API Server CA 证书
    #   namespace → 当前 namespace
</code></pre>
</div>

<div class="card card-d">
<h3>认证结果：User Info</h3>
<p>认证成功后，请求上下文携带以下信息，后续鉴权使用：</p>
<ul>
<li><strong>User Name</strong>：用户名（X.509 的 CN 字段，如 <code>kubernetes-admin</code>；ServiceAccount 的 <code>system:serviceaccount:&lt;ns&gt;:&lt;sa-name&gt;</code>）</li>
<li><strong>Groups</strong>：组（X.509 的 O 字段，如 <code>system:masters</code>；ServiceAccount 默认组 <code>system:serviceaccounts</code>、<code>system:serviceaccounts:&lt;ns&gt;</code>）</li>
<li><strong>UID</strong>：用户唯一标识</li>
<li><strong>Extra</strong>：额外信息（如 OIDC 中的 claims）</li>
</ul>
<p>关键点：<strong>K8s 不存储 User 对象</strong>——普通用户由外部系统管理（证书/OIDC/webhook），只有 ServiceAccount 是 API 资源对象。</p>
</div>

## 2. Authorization（鉴权）

<div class="card card-m">
<h3>鉴权模式</h3>
<p>API Server 支持多种鉴权模式并行启用（<code>--authorization-mode=...,..</code>），任一通过则放行：</p>
<table>
<tr><th>鉴权模式</th><th>说明</th></tr>
<tr><td>RBAC（Role-Based Access Control）</td><td>基于角色的访问控制，生产环境标准方式。通过 Role/ClusterRole 定义权限，RoleBinding/ClusterRoleBinding 绑定到用户/组/SA</td></tr>
<tr><td>Node</td><td>专用鉴权器，限制 kubelet 只能访问自己节点上的 Pod、Service、Secret 等资源</td></tr>
<tr><td>ABAC（Attribute-Based）</td><td>基于属性的访问控制（静态 JSON 策略文件），已被 RBAC 取代，不推荐</td></tr>
<tr><td>Webhook</td><td>调用外部 HTTP(S) 服务做鉴权决策（如 Open Policy Agent/Gatekeeper 可以通过 webhook 模式接入）</td></tr>
<tr><td>AlwaysAllow / AlwaysDeny</td><td>全部允许/拒绝，仅用于测试</td></tr>
</table>
<p>生产环境推荐：<code>--authorization-mode=Node,RBAC</code></p>
</div>

<div class="card card-s">
<h3>RBAC 核心对象</h3>
<pre><code class="language-yaml"># Role：namespace 级别权限
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]  # core API group
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch"]
  resourceNames: ["my-pod"]  # 可选：限定特定资源实例

# ClusterRole：集群级别权限（或跨 namespace 的通用角色模板）
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]

# RoleBinding：把 Role/ClusterRole 绑定到用户
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: alice          # 普通用户
  apiGroup: rbac.authorization.k8s.io
- kind: ServiceAccount
  name: my-sa          # ServiceAccount
  namespace: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
</code></pre>
<table>
<tr><th>概念</th><th>说明</th></tr>
<tr><td>Verbs</td><td>get, list, watch, create, update, patch, delete, deletecollection（标准）；自定义资源可自定义 verb</td></tr>
<tr><td>API Groups</td><td>""（core group：pods/services/configmaps 等）、apps（deployments/replicasets）、batch（jobs）等</td></tr>
<tr><td>ClusterRole + RoleBinding</td><td>ClusterRole 定义集群级权限，但通过 RoleBinding 绑定到特定 namespace 时，权限只在该 namespace 生效</td></tr>
<tr><td>Aggregated ClusterRoles</td><td>通过 label selector 聚合其他 ClusterRole 的规则（如 admin/edit/view 预置角色）</td></tr>
</table>
</div>

<div class="card card-w">
<h3>鉴权常见错误</h3>
<ul>
<li><strong>403 Forbidden</strong>：认证通过但权限不足。检查 RoleBinding 中的 subject 是否正确、Role 中是否包含所需 verb 和 resource、namespace 是否匹配。</li>
<li><strong>401 Unauthorized</strong>：认证失败。检查 kubeconfig 证书/token 是否有效、是否过期、CA 是否正确。</li>
<li>System 前缀：用户名/组以 <code>system:</code> 开头是保留的，K8s 组件使用（如 <code>system:node:</code>、<code>system:serviceaccount:</code>），普通用户不要使用。</li>
<li>Privilege escalation：创建 ClusterRoleBinding 的权限本身需要 ClusterRole admin 权限，防止提权。</li>
</ul>
</div>

## 3. Admission Control（准入控制）

<div class="card card-m">
<h3>Admission Control 架构</h3>
<p>Admission 是可扩展的策略执行点，在对象持久化到 etcd 之前运行。分为两类：</p>
<ol>
<li><strong>Mutating Admission（变更准入）：</strong>可以修改请求中的对象（添加默认值、注入 sidecar、设置 label 等）。</li>
<li><strong>Validating Admission（验证准入）：</strong>只能批准或拒绝请求，不能修改对象。</li>
</ol>
<pre><code>请求对象 → [Mutating Webhooks 链（按配置顺序）] → 对象可能已被修改
         → [内置 Validating Admission]
         → [Validating Webhooks 链（按配置顺序）] → 通过/拒绝
</code></pre>
<p><strong>重要：Mutating Webhook 在 Validating Webhook 之前执行</strong>。Mutating 修改过的对象会被 Validating 再次校验，防止无效对象通过。K8s 1.15+ 支持 reinvocation：如果后续 Mutating Webhook 修改了对象，已执行过的 Mutating Webhook 可能被重新调用（由 <code>reinvocationPolicy: IfNeeded</code> 控制）。</p>
</div>

<div class="card card-s">
<h3>内置 Admission Controller</h3>
<p>除了 Webhook，API Server 内置了大量 admission plugin，关键的有：</p>
<table>
<tr><th>内置插件</th><th>功能</th></tr>
<tr><td>LimitRanger</td><td>为 Pod/Container 设置默认 request/limit，校验不超过 LimitRange 范围</td></tr>
<tr><td>ResourceQuota</td><td>限制 namespace 资源总量（CPU/内存/Pod 数/ConfigMap 数等）</td></tr>
<tr><td>ServiceAccount</td><td>自动为 Pod 挂载 ServiceAccount token（projected volume）</td></tr>
<tr><td>DefaultStorageClass</td><td>PVC 未指定 storageClassName 时自动设置默认 StorageClass</td></tr>
<tr><td>DefaultTolerationSeconds</td><td>为 Pod 设置默认的 notready:NoExecute  toleration（5 分钟）</td></tr>
<tr><td>MutatingAdmissionWebhook</td><td>执行注册的 MutatingWebhookConfiguration</td></tr>
<tr><td>ValidatingAdmissionWebhook</td><td>执行注册的 ValidatingWebhookConfiguration</td></tr>
<tr><td>NodeRestriction</td><td>限制 kubelet 只能修改自己 Node 上的 Pod/Node 对象</td></tr>
<tr><td>PodSecurity（替代 PSP）</td><td>Pod Security Standards（Privileged/Baseline/Restricted）</td></tr>
<tr><td>NamespaceLifecycle</td><td>防止在 Terminating namespace 创建资源，防止删除系统 namespace</td></tr>
</table>
</div>

<div class="card card-d">
<h3>动态 Admission Webhook 配置</h3>
<pre><code class="language-yaml"># MutatingWebhookConfiguration：注入 sidecar 示例
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: istio-sidecar-injector
webhooks:
- name: sidecar-injector.istio.io
  clientConfig:
    service:
      name: istiod
      namespace: istio-system
      path: "/inject"
      port: 443
    caBundle: &lt;base64-encoded-CA&gt;  # Webhook Server 的 CA 证书
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
    operations: ["CREATE"]       # CREATE/UPDATE/DELETE/CONNECT
    scope: "Namespaced"
  failurePolicy: Fail            # Fail: webhook 不可用时拒绝请求；Ignore: 放行
  sideEffects: None
  reinvocationPolicy: IfNeeded   # 对象被其他 webhook 修改后是否重新调用
  namespaceSelector: {}          # 按 namespace label 过滤
  objectSelector: {}             # 按对象 label 过滤
  admissionReviewVersions: ["v1", "v1beta1"]
</code></pre>
<table>
<tr><th>failurePolicy</th><th>行为</th></tr>
<tr><td>Fail</td><td>Webhook 调用失败（超时/网络错误/5xx）时拒绝请求，保证策略不被绕过</td></tr>
<tr><td>Ignore</td><td>Webhook 失败时放行，可用性优先但策略可能被绕过</td></tr>
</table>
<p>Webhook 超时由 <code>timeoutSeconds</code> 控制（默认 10 秒，建议设为 ≤10 秒）。Webhook 本身如果挂了且 failurePolicy=Fail，会导致对应资源类型无法创建/更新——这是生产故障的常见原因。</p>
</div>

## 4. API Aggregation（API 聚合）

<div class="card card-s">
<h3>APIService 与扩展 API</h3>
<p>除了内置资源（Pod/Service/Deployment）和 CRD，K8s 还支持通过 API Aggregation 层将外部服务注册为 API Server，使自定义 API 看起来像内置 API 一样通过主 API Server 访问：</p>
<ul>
<li><strong>APIService</strong>：注册聚合 API 的资源对象，声明 group/version 和后端 Service。</li>
<li><strong>Extension API Server</strong>：独立部署的 API 服务（如 metrics-server），主 API Server 将匹配路径的请求代理到它。</li>
<li>metrics-server 是最常见的聚合 API 使用者（提供 <code>apis/metrics.k8s.io/v1beta1</code>）。</li>
<li>CRD vs Aggregated API：CRD 简单，直接存储在 etcd 中；Aggregated API 更灵活，可以有自定义存储、自定义业务逻辑，但需要部署独立服务。</li>
</ul>
<pre><code class="language-yaml">apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1beta1.metrics.k8s.io
spec:
  service:
    name: metrics-server
    namespace: kube-system
  group: metrics.k8s.io
  version: v1beta1
  insecureSkipTLSVerify: true
  groupPriorityMinimum: 100
  versionPriority: 100
</code></pre>
</div>

## API Priority and Fairness（APF）

<div class="card card-d">
<h3>请求优先级与公平性</h3>
<p>大规模集群中，一个"吵闹邻居"（如某个 Controller 疯狂 LIST 全量 Pod）可能耗尽 API Server 资源拖垮整个控制面。APF（K8s 1.20+）通过以下机制防止这种情况：</p>
<ol>
<li><strong>Priority Levels（优先级）</strong>：请求分为多个优先级（leader-election、system、workload-high、workload-low、global-default），每个优先级有独立的并发配额（concurrency shares）。</li>
<li><strong>Flow Schema（流模式）</strong>：按请求属性（user、verb、resource、namespace 等）将请求分类到不同 Priority Level。</li>
<li><strong>Fair Queuing（公平排队）</strong>：同一优先级内，按 flow 维度公平分配并发槽，避免同一类请求独占。</li>
<li><strong>排队与丢弃</strong>：队列满时新请求被拒绝（429 Too Many Requests），保护 API Server 不过载。</li>
</ol>
<pre><code class="language-bash"># 查看 PriorityLevelConfiguration 和 FlowSchema
kubectl get prioritylevelconfigurations
kubectl get flowschemas

# 典型优先级配置（系统关键请求优先级最高）
# - leader-election: 控制面选主，配额最高
# - system: 系统组件（kubelet/scheduler/controller-manager）
# - workload-high: 关键 workload controller
# - workload-low: 普通请求
# - global-default: 未匹配的其他请求
</code></pre>
</div>

## Watch 机制与分页

<div class="card card-m">
<h3>Watch 实现细节</h3>
<p>Watch 是 K8s Controller 模式的基础，API Server 对 Watch 请求的处理：</p>
<ul>
<li><strong>HTTP chunked transfer</strong>：Watch 响应是一个长连接 HTTP/1.1 chunked 响应（或 HTTP/2 stream），每个事件作为一个 JSON chunk 发送。</li>
<li><strong>Cacher（API Server 内的 watch cache）</strong>：API Server 为每个资源类型维护一个基于 etcd watch 的环形缓存（watch cache），List 请求默认从缓存读（<code>resourceVersion=0</code>），Watch 请求从缓存中推送事件，减轻 etcd 直接压力。</li>
<li><strong>Bookmark events</strong>：API Server 周期性发送 bookmark 事件（仅包含 resourceVersion），客户端可以用它更新 lastSeenResourceVersion 而无需处理完整对象，加速重连。</li>
<li><strong>resourceVersion 语义</strong>：list 返回 resourceVersion，watch 从该版本开始，支持从历史版本重放（在 watch cache 窗口内）。</li>
</ul>
<pre><code>GET /api/v1/namespaces/default/pods?watch=1&resourceVersion=12345
→ HTTP 200 OK, Content-Type: application/json, Transfer-Encoding: chunked

{"type":"ADDED","object":{...,"metadata":{"resourceVersion":"12350"}}}
{"type":"MODIFIED","object":{...,"metadata":{"resourceVersion":"12351"}}}
{"type":"DELETED","object":{...,"metadata":{"resourceVersion":"12355"}}}
{"type":"BOOKMARK","object":{"metadata":{"resourceVersion":"12399"}}}
...
</code></pre>
</div>

<div class="card card-s">
<h3>LIST 分页（Chunking）</h3>
<p>当集群中有大量对象（如 10 万 Pod）时，一次 LIST 全量返回会占用大量内存和带宽，并可能导致 API Server 超时。K8s 支持分页：</p>
<ul>
<li>客户端 LIST 时指定 <code>limit</code> 参数（每页数量）。</li>
<li>API Server 返回一页数据和 <code>continue</code> token（基于 etcd revision + key 范围的不透明 token）。</li>
<li>客户端用 <code>continue</code> token 获取下一页，直到返回空 continue 表示结束。</li>
<li>分页期间如果资源版本变化（有新对象写入），continue token 会失效，客户端需要重新开始。</li>
</ul>
<pre><code>GET /api/v1/pods?limit=500
→ {items: [...500 pods...], metadata: {continue: "eyJ2IjoibXZS...", resourceVersion: "12345"}}

GET /api/v1/pods?limit=500&continue=eyJ2IjoibXZS...
→ {items: [...next 500...], metadata: {continue: "..."}}
</code></pre>
</div>

## 乐观并发控制

<div class="card card-m">
<h3>resourceVersion 与 CAS</h3>
<p>K8s 使用乐观并发控制（Optimistic Concurrency Control）处理并发更新，避免显式锁：</p>
<ol>
<li>客户端 GET 对象，获取当前的 <code>metadata.resourceVersion</code>。</li>
<li>客户端修改对象，UPDATE/PATCH 请求携带该 resourceVersion。</li>
<li>API Server 解析对象，检查 storage（etcd）中当前对象的 mod_revision 是否匹配客户端的 resourceVersion。</li>
<li>匹配则写入成功，resourceVersion 更新为新的更高值。</li>
<li>不匹配则返回 <strong>409 Conflict</strong>，客户端必须重新 GET、应用变更、重试。</li>
</ol>
<pre><code class="language-go">// 使用 client-go 的 retry.RetryOnConflict 处理乐观冲突
retryErr := retry.RetryOnConflict(retry.DefaultRetry, func() error {
    // 每次重试前重新 GET 最新版本
    deployment, err := clientset.AppsV1().Deployments("default").Get(ctx, "nginx", metav1.GetOptions{})
    if err != nil { return err }
    
    // 应用变更
    deployment.Spec.Replicas = int32Ptr(5)
    
    // 尝试 UPDATE
    _, err = clientset.AppsV1().Deployments("default").Update(ctx, deployment, metav1.UpdateOptions{})
    return err
})
</code></pre>
<p>注意：PATCH（尤其是 strategic merge patch 和 JSON patch）和 UPDATE 的冲突处理不同——PATCH 可以在不指定 resourceVersion 的情况下执行，但有自己的 merge 语义；Server-Side Apply（SSA）通过 managedFields 做字段级别的冲突检测。</p>
</div>

<div class="card card-w">
<h3>PUT vs PATCH 对比</h3>
<table>
<tr><th>操作</th><th>语义</th><th>是否必须 resourceVersion</th><th>适用场景</th></tr>
<tr><td>PUT (Update)</td><td>整体替换对象（除 status 子资源）</td><td>必须（否则返回 400）</td><td>Controller 全量更新对象</td></tr>
<tr><td>JSON Patch (application/json-patch+json)</td><td>RFC 6902 补丁，细粒度 add/remove/replace</td><td>可选（不提供可能覆盖其他变更）</td><td>精确字段修改</td></tr>
<tr><td>Merge Patch (application/merge-patch+json)</td><td>RFC 7386 合并补丁，null = 删除</td><td>可选</td><td>简单更新</td></tr>
<tr><td>Strategic Merge Patch</td><td>K8s 扩展，支持 list 合并策略（如 containers 按 name merge）</td><td>可选</td><td>kubectl apply（旧版）</td></tr>
<tr><td>Server-Side Apply (application/apply-patch+yaml)</td><td>字段归属管理（managedFields），声明式 apply</td><td>不需要（字段级冲突检测）</td><td>kubectl apply（推荐）、GitOps</td></tr>
</table>
</div>

## 高频问答

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Mutating 和 Validating Webhook 执行顺序？</div>
<div class="qa-a">
<p>执行顺序严格为：<strong>所有 Mutating Webhooks（按配置顺序串行执行）→ 对象 Schema 校验 → 所有 Validating Webhooks（按配置顺序串行执行）</strong>。</p>
<div class="qa-section"><div class="qa-section-title">关键细节</div><p>1. Mutating Webhook 可以修改对象（如注入 sidecar 容器、添加 label/annotation、设置默认值），修改后的对象传给后续的 Webhook。</p><p>2. 因为 Mutating 可以修改对象，所以 Validating 必须在所有 Mutating 完成后执行，以校验最终的对象是否合法。</p><p>3. 如果某个 Mutating Webhook 修改了对象，且后续的 Mutating Webhook 配置了 <code>reinvocationPolicy: IfNeeded</code>，前面已经执行过的 Mutating Webhook 可能被再次调用，以确认它们是否需要对新修改的对象再做调整。</p><p>4. Validating Webhook 只能返回 allow/deny，不能修改对象。如果多个 Validating Webhook 中有一个拒绝，请求立即被拒绝。</p><p>5. 内置 Admission Plugin（如 LimitRanger、ResourceQuota）的执行时机在 Mutating 和 Validating 之间，内置插件也可能修改对象（如 LimitRanger 注入默认 request/limit）。</p></div>
<div class="qa-summary">面试口径：Mutating 先执行（可以改对象）→ 内置校验 → Validating 后执行（不能改，只能通过/拒绝）；Mutating 串行、Validating 串行，失败受 failurePolicy 控制。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 一个请求什么时候返回 403？什么时候返回 401？</div>
<div class="qa-a">
<p>这两个状态码分别对应认证和鉴权失败：</p>
<div class="qa-section"><div class="qa-section-title">401 Unauthorized（认证失败）</div><p>API Server 无法验证请求者的身份。常见原因：没有提供认证凭证（cert/token）、凭证无效或过期、证书由不受信任的 CA 签发、token 格式错误或 audience 不匹配。此时 API Server 无法知道"你是谁"，直接拒绝。注意：匿名请求在启用 Anonymous 认证时被认证为 <code>system:anonymous</code> 用户和 <code>system:unauthenticated</code> 组，不会返回 401，但后续鉴权通常会拒绝（返回 403）。</p></div>
<div class="qa-section"><div class="qa-section-title">403 Forbidden（鉴权失败）</div><p>认证通过（API Server 知道你是谁），但你没有执行该操作的权限。常见原因：没有对应的 Role/ClusterRole 和 RoleBinding、Role 中没有所需的 verb（如只有 get 没有 list）、资源类型或 namespace 不匹配、尝试访问集群级资源但只有 namespace 级权限。这是 RBAC 配置错误的典型表现，用 <code>kubectl auth can-i</code> 可以诊断。</p></div>
<div class="qa-summary">面试口径：401 = 不知道你是谁（认证失败），403 = 知道你是谁但你不能这么做（鉴权/RBAC 失败）。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: API Server 怎么处理 list 请求的分页？</div>
<div class="qa-a">
<p>大规模集群中 LIST 全量对象会造成 API Server/etcd 压力和客户端 OOM，API Server 使用 <strong>chunking（分页）</strong>机制：</p>
<div class="qa-section"><div class="qa-section-title">1. 客户端传 limit</div><p>客户端在 LIST 请求中指定 <code>limit=N</code>，表示每页最多返回 N 个对象。kubectl 和 client-go Informer 默认会自动使用分页（<code>--chunk-size=500</code>）。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 服务器返回 continue token</div><p>API Server 从 etcd 读取 N 个对象，同时返回一个不透明的 <code>continue</code> token（编码了当前 etcd revision 和起始 key 位置）。响应中带有当前页的 resourceVersion。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 客户端循环获取</div><p>客户端收到非空 continue 后，带上该 token 请求下一页。API Server 从 token 标记的位置继续读取。continue 为空时表示所有数据已返回。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 一致性保证</div><p>整个分页过程在同一 resourceVersion 下执行，返回的是该时刻的一致快照。如果分页期间有新的写操作导致 etcd 压缩或 revision 前进太多，continue token 会失效（410 Gone），客户端需要从头重新开始 list。</p></div>
<div class="qa-summary">面试口径：LIST 分页 = limit 参数 + continue token，API Server 将大结果集分片返回，整个分页过程在同一 etcd revision 下保证一致性，避免全量加载。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Admission webhook 挂了会怎样？</div>
<div class="qa-a">
<p>取决于 <code>failurePolicy</code> 配置和 webhook 类型：</p>
<div class="qa-section"><div class="qa-section-title">failurePolicy: Fail</div><p>Webhook 调用超时（默认 10s）、网络不可达、返回 5xx 错误时，<strong>请求被拒绝</strong>（返回 500 或 403）。这保证策略不会因为 webhook 故障而被绕过，但也意味着 webhook 单点故障可能导致对应资源类型完全无法创建/更新。例如 istio-sidecar-injector webhook 挂了，所有带注入 label 的 namespace 中都无法创建新 Pod。</p></div>
<div class="qa-section"><div class="qa-section-title">failurePolicy: Ignore</div><p>Webhook 失败时<strong>请求放行</strong>，不执行该 webhook 的校验/变更逻辑。这提高了可用性，但有安全风险——策略被绕过，可能创建不合规对象。</p></div>
<div class="qa-section"><div class="qa-section-title">最佳实践</div><p>1. 生产环境关键策略（安全、配额）用 Fail，非关键策略（如日志注入）可用 Ignore。2. Webhook 服务本身要做高可用（多副本 + PDB）。3. 设置合理的 <code>timeoutSeconds</code>（如 5 秒），避免 webhook 慢导致 API 请求整体超时。4. 使用 <code>namespaceSelector</code>/<code>objectSelector</code> 缩小 webhook 拦截范围。5. Webhook 自身的部署要排除自身拦截（避免鸡生蛋问题：webhook 依赖的 namespace 中创建 Pod 时不拦截），通常通过 <code>namespaceSelector: kubernetes.io/metadata.name!=kube-system</code> 或特定 label 排除。</p></div>
<div class="qa-summary">面试口径：webhook 挂了的行为由 failurePolicy 决定（Fail=拒绝/Ignore=放行）；关键策略 Fail 但要保证 webhook HA，否则 webhook 故障会导致对应资源类型操作全部失败。</div>
</div>
</div>

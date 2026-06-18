## 一句话结论

安全和多租户要从身份、授权、准入、隔离、配额和审计六层看。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Kubernetes 核心 |
| 章节类型 | 系统类 |
| 解决问题 | 围绕控制面、调度资源模型、Workload Controller、网络存储、安全多租户、排障和 AI Infra GPU/DRA 建立平台面试答案。 |
| 面试抓手 | 不要把 RBAC、Admission、Pod Security 混为一谈。 |

<div class="card card-m">
<h3>安全、准入与多租户：请求能不能进入，资源能不能隔离</h3>
<p>Kubernetes 安全链路可以概括为：<strong>Authentication 识别你是谁，Authorization 判断你能做什么，Admission 决定这个请求是否符合集群策略，Persistence 才会写入 etcd。</strong>多租户治理则在此基础上叠加 namespace、RBAC、Quota、LimitRange、Pod Security、PriorityClass 和队列配额。</p>
</div>

<div class="card card-s">
<h3>API Server 请求链路</h3>
<table>
<tr><th>阶段</th><th>作用</th><th>常见机制</th><th>面试重点</th></tr>
<tr><td>Authentication</td><td>确认调用者身份</td><td>证书、Token、OIDC、ServiceAccount</td><td>未认证通常是 anonymous 或直接拒绝</td></tr>
<tr><td>Authorization</td><td>判断是否有权限</td><td>RBAC、Node、Webhook</td><td>RBAC 是 allow-only，没有显式 deny</td></tr>
<tr><td>Mutating Admission</td><td>修改请求对象</td><td>默认值注入、sidecar 注入</td><td>先变更再校验</td></tr>
<tr><td>Validating Admission</td><td>校验请求对象</td><td>Webhook、ValidatingAdmissionPolicy</td><td>策略不通过则拒绝写入</td></tr>
<tr><td>Persistence</td><td>写入 etcd</td><td>storage layer</td><td>写入后其他组件通过 watch 感知</td></tr>
</table>
</div>

<div class="card card-d">
<h3>RBAC 与 ServiceAccount</h3>
<table>
<tr><th>对象</th><th>作用</th><th>注意点</th></tr>
<tr><td>Role</td><td>namespace 级权限集合</td><td>只能授予本 namespace 内资源权限</td></tr>
<tr><td>ClusterRole</td><td>集群级权限集合</td><td>可用于集群资源，也可被 RoleBinding 绑定到 namespace</td></tr>
<tr><td>RoleBinding</td><td>把 Role/ClusterRole 授给主体</td><td>作用域是 namespace</td></tr>
<tr><td>ClusterRoleBinding</td><td>集群范围授权</td><td>权限很大，生产要谨慎</td></tr>
<tr><td>ServiceAccount</td><td>Pod 内访问 API Server 的身份</td><td>配合最小权限原则</td></tr>
</table>
<p>回答 RBAC 时要强调“主体 subject、动作 verb、资源 resource、作用域 namespace/cluster”四个维度。</p>
</div>

<div class="card card-w">
<h3>Admission、Webhook 与策略治理</h3>
<table>
<tr><th>机制</th><th>适合做什么</th><th>风险/注意点</th></tr>
<tr><td>MutatingAdmissionWebhook</td><td>注入 sidecar、默认资源、镜像仓库前缀</td><td>要避免循环变更和高延迟</td></tr>
<tr><td>ValidatingAdmissionWebhook</td><td>拒绝不合规镜像、特权容器、非法标签</td><td>Webhook 故障可能影响 API 写入</td></tr>
<tr><td>ValidatingAdmissionPolicy</td><td>用 CEL 写内置校验策略</td><td>适合轻量规则，减少外部 webhook 依赖</td></tr>
<tr><td>Pod Security</td><td>限制特权、宿主机 namespace、危险能力</td><td>按 namespace enforce/audit/warn 逐步推进</td></tr>
<tr><td>OPA/Gatekeeper/Kyverno</td><td>更完整的策略即代码</td><td>需要治理策略复杂度和误伤</td></tr>
</table>
</div>

<div class="card card-m">
<h3>多租户资源治理</h3>
<table>
<tr><th>机制</th><th>解决的问题</th><th>AI Infra 场景</th></tr>
<tr><td>Namespace</td><td>基础隔离边界</td><td>按团队、项目、环境隔离</td></tr>
<tr><td>ResourceQuota</td><td>限制 namespace 资源总量</td><td>限制 CPU、内存、Pod 数、PVC、GPU 扩展资源</td></tr>
<tr><td>LimitRange</td><td>设置单 Pod/容器默认值和上下限</td><td>防止用户不写 requests 或申请过大</td></tr>
<tr><td>PriorityClass</td><td>定义任务优先级</td><td>线上推理优先于离线训练，关键任务可抢占</td></tr>
<tr><td>Queue</td><td>批任务排队和准入</td><td>Kueue/Volcano 按队列管理训练任务</td></tr>
<tr><td>Quota borrowing</td><td>空闲配额可临时借用</td><td>提升 GPU 利用率</td></tr>
<tr><td>Reclaim</td><td>高优任务需要资源时回收借用资源</td><td>保证关键队列 SLA</td></tr>
</table>
</div>

<div class="card card-s">
<h3>ResourceQuota 与 LimitRange 的区别</h3>
<p>这两个对象经常一起出现，但治理层级不同：<strong>ResourceQuota 管 namespace 总量，LimitRange 管单个 Pod / Container 的范围和默认值。</strong></p>
<table>
<tr><th>维度</th><th>ResourceQuota</th><th>LimitRange</th></tr>
<tr><td>作用范围</td><td>namespace 总量</td><td>单个 Pod / Container / PVC</td></tr>
<tr><td>解决问题</td><td>防止一个租户占光 namespace 资源</td><td>防止单个对象不写 request 或申请过大</td></tr>
<tr><td>典型限制</td><td>CPU/Memory 总 requests、Pod 数、PVC 数、GPU 扩展资源总量</td><td>每个容器 request/limit 的最小、最大、默认值</td></tr>
<tr><td>失败表现</td><td>创建对象时被 admission 拒绝，提示 exceeded quota</td><td>对象字段不满足范围或被自动填默认值</td></tr>
</table>
<div class="qa-summary">面试口径：Quota 控总量，LimitRange 控单体；多租户集群通常两者都要配。</div>
</div>

<div class="card card-d">
<h3>ResourceQuota 基础机制</h3>
<p><code>ResourceQuota</code> 是 namespace 级资源总量约束。它发生在 API Server 的 admission 阶段：当新建或更新对象会导致 namespace 超过配额时，请求会被直接拒绝。</p>
<table>
<tr><th>维度</th><th>说明</th><th>例子</th></tr>
<tr><td>作用范围</td><td>单个 namespace</td><td>team-a namespace 最多 10 张 GPU</td></tr>
<tr><td>统计对象</td><td>对象数量、requests、limits、PVC、Service 等</td><td><code>pods</code>、<code>requests.cpu</code>、<code>limits.memory</code></td></tr>
<tr><td>统计时机</td><td>API 写入前的 admission</td><td>超额时对象不会被创建</td></tr>
<tr><td>统计语义</td><td>看声明值，不看实时使用量</td><td>Pod 实际只用 1 CPU，也按 request 计入 quota</td></tr>
<tr><td>扩展资源</td><td>支持 GPU/NPU 等 extended resource</td><td><code>requests.nvidia.com/gpu: "10"</code></td></tr>
</table>
<pre><code class="language-yaml">apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a-quota
  namespace: team-a
spec:
  hard:
    pods: "100"
    requests.cpu: "200"
    requests.memory: 800Gi
    limits.cpu: "400"
    limits.memory: 1200Gi
    requests.nvidia.com/gpu: "10"
    persistentvolumeclaims: "20"</code></pre>
<div class="qa-summary">关键边界：ResourceQuota 是“拒绝超额创建”的 admission 机制，不是“超过后排队等待”的调度机制。</div>
</div>

<div class="card card-w">
<h3>ResourceQuota 常见坑</h3>
<table>
<tr><th>问题</th><th>原因</th><th>处理方式</th></tr>
<tr><td>用户不写 requests，Pod 创建被拒</td><td>namespace 有 quota 时，缺失 request 可能无法统计</td><td>配合 LimitRange 设置默认 request/limit</td></tr>
<tr><td>超过 GPU 配额后任务直接失败</td><td>ResourceQuota 是 admission 拒绝，不是队列系统</td><td>需要 Kueue / Volcano / AIJob Queue Controller 做排队</td></tr>
<tr><td>Pod 实际使用很低但 quota 满了</td><td>quota 统计 requests，不看实时利用率</td><td>优化 request，或引入借用/回收机制</td></tr>
<tr><td>只限制 CPU/Memory，GPU 被抢光</td><td>没有把 extended resource 纳入 quota</td><td>添加 <code>requests.nvidia.com/gpu</code> 等扩展资源配额</td></tr>
<tr><td>对象数量过多导致控制面压力</td><td>只限制资源量，没限制 object count</td><td>限制 pods、services、secrets、configmaps、PVC 数量</td></tr>
</table>
</div>

<div class="card card-r">
<h3>安全题常见误区</h3>
<ul>
<li>不要把 RBAC 和 NetworkPolicy 混为一谈：RBAC 管 API 权限，NetworkPolicy 管网络流量。</li>
<li>不要认为 namespace 是强安全隔离：它是逻辑隔离，还需要 RBAC、Quota、NetworkPolicy、Pod Security 配合。</li>
<li>不要让 Webhook 无超时、无降级策略：它可能成为 API Server 写路径上的稳定性风险。</li>
<li>不要给默认 ServiceAccount 过大权限：Pod 被攻陷后会扩大影响面。</li>
<li>不要只限制 CPU/内存而忘记扩展资源：GPU 集群要把 <code>nvidia.com/gpu</code>、NPU 等纳入 Quota。</li>
</ul>
</div>

<div class="card card-d">
<h3>Secret 管理：默认不是加密，是 base64</h3>
<p>面试常考的"陷阱题"：Kubernetes 的 Secret 不是加密的，它在 etcd 里默认只是 base64 编码。生产环境要叠加 etcd 加密、外部 Secret 系统、最小化挂载和审计。</p>
<table>
<tr><th>层次</th><th>解决的问题</th><th>典型实现</th><th>面试关注点</th></tr>
<tr><td>默认 Secret</td><td>把敏感数据从 Pod 配置中分离</td><td>base64 + RBAC 控制访问</td><td>不是加密，只是编码；任何能读 Secret 的人都能解码</td></tr>
<tr><td>etcd 加密 at rest</td><td>把 Secret 在 etcd 里加密存储</td><td><code>EncryptionConfiguration</code> + KMS provider</td><td>需要在 API Server 启用 <code>--encryption-provider-config</code></td></tr>
<tr><td>External Secrets Operator</td><td>把外部 KV 系统映射为 K8s Secret</td><td>对接 Vault / AWS SM / GCP SM</td><td>Secret 来源可控，可以做 rotate / audit</td></tr>
<tr><td>CSI Secret Store</td><td>不创建 K8s Secret，直接以卷形式挂载</td><td>Vault CSI、AWS / Azure / GCP provider</td><td>避免 Secret 在 etcd 落盘，也支持自动 rotate</td></tr>
<tr><td>SPIFFE / SPIRE</td><td>给工作负载发短期身份证书（mTLS）</td><td>SPIRE Server + Agent + Workload API</td><td>用 SVID 替代长期 token，减少凭据泄漏</td></tr>
<tr><td>Workload Identity</td><td>把 ServiceAccount 映射为云 IAM 身份</td><td>GKE Workload Identity / IRSA</td><td>Pod 不需要在 Secret 里存云密钥</td></tr>
</table>
<div class="qa-summary">面试口径：Secret 默认不是加密的，生产至少要做"etcd at-rest 加密 + RBAC 最小权限"；进一步通过 External Secrets / CSI Secret Store / Workload Identity 把凭据生命周期交给外部系统。</div>
</div>

<div class="card card-w">
<h3>etcd 加密 at rest 的工作方式</h3>
<p>API Server 通过 <code>EncryptionConfiguration</code> 配置加密 provider，按资源类型决定哪些对象在写 etcd 前被加密。<strong>顺序很重要：第一个 provider 用于加密，所有 provider 用于解密</strong>，所以滚动启用加密时要逐步切换。</p>
<table>
<tr><th>Provider</th><th>说明</th><th>适用场景</th></tr>
<tr><td><code>identity</code></td><td>不加密，明文写 etcd</td><td>默认值，仅用于初始或回退</td></tr>
<tr><td><code>aescbc</code> / <code>aesgcm</code></td><td>用本地密钥做 AES 加密</td><td>简单加密，密钥保存在 API Server 节点</td></tr>
<tr><td><code>secretbox</code></td><td>NaCl secretbox</td><td>类似 aescbc，依赖外部库</td></tr>
<tr><td><code>kms</code></td><td>用外部 KMS 包装 DEK</td><td>生产推荐，密钥不在节点本地</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">面试常追问</div><p><strong>"已经写入 etcd 的旧 Secret 会自动被加密吗？"</strong>不会。需要 <code>kubectl get secrets -A -o yaml | kubectl replace -f -</code> 之类的操作触发重写，或写个 controller 周期性 touch。轮换 KMS 密钥同样要走这个流程。</p></div>
</div>

<div class="card card-s">
<h3>镜像安全：签名、扫描、SBOM、admission</h3>
<p>容器镜像是供应链攻击的高危环节。完整的镜像安全闭环不是单点，而是从构建到准入的链路。</p>
<table>
<tr><th>阶段</th><th>做什么</th><th>典型工具</th><th>面试要点</th></tr>
<tr><td>构建</td><td>固定 base 镜像、最小化层、只装必要依赖</td><td>distroless / chainguard / 多阶段构建</td><td>不要在镜像里内嵌长期凭据</td></tr>
<tr><td>SBOM 生成</td><td>列出镜像内所有组件和版本</td><td>syft、Trivy SBOM</td><td>有 SBOM 才能在 CVE 出现时快速反查影响面</td></tr>
<tr><td>漏洞扫描</td><td>对镜像做 CVE 扫描</td><td>Trivy、Grype、Clair</td><td>CI 阶段拒绝高危 CVE，不要等上线再扫</td></tr>
<tr><td>镜像签名</td><td>给镜像打可验签的签名</td><td>Cosign / Sigstore</td><td>签名 + 透明日志（Rekor），防止中间篡改</td></tr>
<tr><td>准入验证</td><td>集群只接受可信镜像</td><td>Kyverno / Gatekeeper / Connaisseur 验签策略</td><td>在 Validating Admission 阶段拒绝未签名/未扫描镜像</td></tr>
<tr><td>运行时</td><td>对运行中容器做行为检测</td><td>Falco、Tetragon</td><td>补救供应链漏过的部分</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Audit Log：谁在什么时候做了什么</h3>
<p>API Server 审计日志是合规和事故复盘的核心证据。它通过 <code>--audit-policy-file</code> 配置，定义"哪些请求记录到什么级别"。</p>
<table>
<tr><th>级别</th><th>记录什么</th><th>典型用途</th></tr>
<tr><td>None</td><td>不记录</td><td>明确忽略噪声，比如健康检查</td></tr>
<tr><td>Metadata</td><td>请求元数据（who / what / when）</td><td>大部分请求的默认级别，体积小</td></tr>
<tr><td>Request</td><td>元数据 + 请求体</td><td>关注 spec 变更（如 RBAC、Pod 创建）</td></tr>
<tr><td>RequestResponse</td><td>元数据 + 请求体 + 响应体</td><td>合规审计、敏感资源（Secret、token）</td></tr>
</table>
<table>
<tr><th>排障问题</th><th>用 audit log 怎么查</th></tr>
<tr><td>谁删了某个 Pod</td><td>过滤 <code>verb=delete, resource=pods, name=xxx</code></td></tr>
<tr><td>谁绑定了 cluster-admin</td><td>过滤 <code>resource=clusterrolebindings, verb=create/update</code></td></tr>
<tr><td>Token 是否被外部使用</td><td>过滤 <code>user.username=system:serviceaccount:...</code> + 来源 IP</td></tr>
<tr><td>Secret 是否被异常读取</td><td>对 Secret 启用 RequestResponse 级别记录 GET</td></tr>
</table>
<div class="qa-summary">面试口径：Audit Policy 决定"记什么"，sink（File / Webhook）决定"送到哪"，体积大要按级别和 namespace 收敛，敏感资源单独提级。</div>
</div>

<div class="card card-w">
<h3>API Priority and Fairness（APF）：API Server 限流的现代方案</h3>
<p>老版本 K8s 用 <code>--max-requests-inflight</code> 全局限流，单一控制器抖动就能把整个 API Server 打满。1.20+ 默认启用 APF：把请求按 FlowSchema 分流到不同 PriorityLevelConfiguration，再做公平排队和限流。</p>
<table>
<tr><th>对象</th><th>作用</th><th>例子</th></tr>
<tr><td>FlowSchema</td><td>按 user / SA / verb / resource 把请求分到某个 PL</td><td>kube-system 控制器 → 高优先级，普通用户 → 低优先级</td></tr>
<tr><td>PriorityLevelConfiguration</td><td>定义优先级的并发份额、排队策略</td><td><code>system</code>、<code>workload-high</code>、<code>workload-low</code> 等</td></tr>
<tr><td>flow distinguisher</td><td>同一 PL 内做公平区分</td><td>按 user 区分，避免单租户挤占</td></tr>
<tr><td>排队 vs 拒绝</td><td>满了后排队还是直接 429</td><td>关键控制器 PL 通常排队，普通客户端可拒绝</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">面试口径</div><p>大集群里被 429 不一定是 client 写错代码，更常见是某个 controller 把对应 FlowSchema 的 PL 占满。排查路径：看 API Server <code>apiserver_flowcontrol_*</code> 指标，定位是哪个 PriorityLevel 在排队/拒绝，再反查 FlowSchema 找出始作俑者。</p></div>
</div>

<div class="card card-s">
<h3>ValidatingAdmissionPolicy（VAP）：用 CEL 替代 webhook 的轻量策略</h3>
<p>在没有 VAP 之前，做"拒绝特权容器""强制带 owner label"这类校验都得写 ValidatingAdmissionWebhook，运维成本高、还可能成为写路径稳定性风险。VAP 是 1.30 GA 的内置机制，用 CEL 在 API Server 内嵌执行，不需要部署外部 webhook。</p>
<table>
<tr><th>对象</th><th>作用</th></tr>
<tr><td><code>ValidatingAdmissionPolicy</code></td><td>定义策略，用 CEL 表达式判断 <code>object</code> / <code>oldObject</code> / <code>params</code> 是否合法</td></tr>
<tr><td><code>ValidatingAdmissionPolicyBinding</code></td><td>把 policy 绑定到 namespace / 资源 / 参数对象</td></tr>
<tr><td>params</td><td>引用一个配置 CR，让同一策略复用不同参数</td></tr>
<tr><td>actions</td><td>Deny / Warn / Audit，可以分级别处理</td></tr>
</table>
<table>
<tr><th>对比维度</th><th>Webhook</th><th>VAP（内置 CEL）</th></tr>
<tr><td>部署</td><td>需要起 Pod、配置 TLS、维护 SLO</td><td>API Server 内置，零部署</td></tr>
<tr><td>性能</td><td>多一次远程调用，延迟敏感</td><td>本地执行，毫秒级</td></tr>
<tr><td>稳定性风险</td><td>Webhook 挂了可能影响 API 写入</td><td>无外部依赖</td></tr>
<tr><td>表达能力</td><td>任意代码</td><td>CEL，足够覆盖大多数策略</td></tr>
<tr><td>适合场景</td><td>跨集群对接、复杂逻辑、需要外部数据</td><td>静态规则、最小权限基线</td></tr>
</table>
<div class="qa-summary">面试口径：写得清楚的静态准入策略优先用 VAP（CEL），需要动态外部数据或跨系统调用才上 Webhook；这是替代 OPA/Gatekeeper 中相当一部分简单策略的方向。</div>
</div>

<div class="card card-m">

<h3>安全、准入与多租户高频问答</h3>

<p>本模块的问答按“概念 → 作用 → 链路/排查 → 面试口径”组织，避免只背一段结论。</p>

</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: RBAC、Admission、Pod Security 分别解决什么问题？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. RBAC 解决权限问题</div><p>RBAC 判断某个 subject 是否能对某类 resource 执行某个 verb，例如某用户能否在某 namespace create pods。</p></div>
<div class="qa-section"><div class="qa-section-title">2. Admission 解决准入策略问题</div><p>Admission 发生在认证鉴权之后、写入 etcd 之前，可以变更对象或校验对象，例如注入 sidecar、拒绝非法镜像。</p></div>
<div class="qa-section"><div class="qa-section-title">3. Pod Security 解决 Pod 安全基线问题</div><p>Pod Security 限制特权容器、hostNetwork、hostPID、危险 capabilities、root 运行等高风险配置。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 三者关系</div><p>RBAC 管“谁能做”，Admission 管“请求对象是否合规”，Pod Security 是针对 Pod 安全字段的一类准入策略。</p></div>
<div class="qa-summary">面试口径：RBAC 是权限，Admission 是写入前策略，Pod Security 是 Pod 运行安全基线，三者处在 API Server 请求链路不同阶段。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 一个用户说自己没有权限创建 Pod，怎么排查？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 确认身份和范围</div><p>先确认用户、组、ServiceAccount 和 namespace，权限问题必须带着作用域看。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 验证 RBAC</div><p>用 <code>kubectl auth can-i create pods -n xxx --as user</code> 验证，再检查 Role/ClusterRole 和 Binding 是否正确。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 区分非 RBAC 拒绝</div><p>如果 RBAC 允许但仍失败，继续看 Admission Webhook、ResourceQuota、LimitRange、Pod Security、镜像策略等是否拒绝。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 生产建议</div><p>按最小权限原则授权，不要直接给 cluster-admin；默认 ServiceAccount 也不要绑定过大权限。</p></div>
<div class="qa-summary">面试口径：权限排查先确认身份和 namespace，再用 can-i 验证 RBAC，最后排查 Admission、Quota 和 Pod Security。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 多租户 GPU 集群如何做公平性和利用率平衡？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 基础隔离</div><p>用 namespace、RBAC、ResourceQuota、LimitRange 隔离团队和资源，GPU 扩展资源也要纳入 quota。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 队列治理</div><p>用 Kueue、Volcano 或自研队列表达团队配额、优先级、借用和回收策略。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 公平性</div><p>用 PriorityClass、DRF、quota borrowing/reclaim 等机制，让关键任务有保障，普通任务不被长期饿死。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 利用率</div><p>空闲 GPU 可以借用给低优任务；高优任务到来时通过抢占、重排或 checkpoint 恢复释放资源。</p></div>
<div class="qa-summary">面试口径：多租户 GPU 集群要同时做权限隔离、配额公平、空闲借用和高优任务回收，不能只靠 namespace。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ResourceQuota 为什么不能实现“超过 10 张 GPU 后排队”？</div>
<div class="qa-a">
<p>因为 ResourceQuota 是 API Server admission 阶段的硬拒绝机制。对象一旦会导致 namespace 超过 quota，API Server 直接拒绝创建，不会把这个任务保存成“等待中”的对象，也不会让 scheduler 以后自动再试。</p>
<div class="qa-section"><div class="qa-section-title">正确做法</div><p>如果业务语义是“允许继续提交，但超过 10 张 GPU 后排队”，应该引入任务级队列，例如 Kueue、Volcano，或者自研 <code>AIJob + AIQueue + Queue Controller</code>。排队发生在 Pod 创建前，准入后再创建 Pod。</p></div>
<div class="qa-summary">面试口径：ResourceQuota 管硬上限，Queue 管等待；不要用 quota 代替队列。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 ResourceQuota 通常要配合 LimitRange？</div>
<div class="qa-a">
<p>ResourceQuota 统计 namespace 总量，很多统计项依赖 Pod 的 requests / limits。如果用户不写 requests，系统可能无法准确计入 quota，或者对象被拒绝。LimitRange 可以为容器设置默认 request/limit，也可以限制单个容器的最小/最大资源，保证 quota 有可统计的输入。</p>
<div class="qa-summary">面试口径：LimitRange 给单体对象设默认值和上下限，ResourceQuota 再管 namespace 总量，两者配合才完整。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: K8s Secret 是不是加密的？生产怎么管 Secret？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先纠正"Secret 默认加密"这个误解，再讲分层方案。</p>
<div class="qa-section"><div class="qa-section-title">1. 默认行为</div><p>Secret 在 etcd 里默认是 base64 编码，<strong>不是加密</strong>。任何能 read Secret 的人都能解码出明文。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 第一层：etcd 加密 at rest</div><p>API Server 配 <code>EncryptionConfiguration</code>，建议用 KMS provider（密钥不在节点本地）；旧 Secret 不会自动加密，需要重写一遍。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 第二层：外部 Secret 系统</div><p>用 External Secrets Operator 或 CSI Secret Store，把真正的 Secret 留在 Vault / AWS SM 等系统，K8s 只持有引用或挂载，并支持自动 rotate。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 第三层：身份替代</div><p>用 Workload Identity（IRSA / GKE WI）让 Pod 直接用云 IAM 身份，避免在 Secret 里存 access key；用 SPIFFE/SPIRE 给工作负载发短期 mTLS 证书。</p></div>
<div class="qa-summary">面试口径：Secret 默认只是 base64，生产至少做 etcd 加密 + RBAC 最小权限，进阶用外部 Secret 系统和 Workload Identity 把凭据生命周期外置。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 大集群里大家被 429 限流，怎么定位？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>不要直接调大 inflight，要先理解 APF 把请求分到了哪个 PriorityLevel。</p>
<div class="qa-section"><div class="qa-section-title">1. 看是不是 APF 在拒绝</div><p>1.20+ 默认启用 APF，429 通常带 <code>Retry-After</code> 头，对应某个 PriorityLevel 满了。看 API Server <code>apiserver_flowcontrol_request_concurrency_in_use</code>、<code>apiserver_flowcontrol_rejected_requests_total</code> 指标。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 定位 FlowSchema</div><p>用指标里的 <code>flow_schema</code>、<code>priority_level</code> 标签反查：哪个 FlowSchema 命中、哪个 PL 在排队/拒绝。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 找始作俑者</div><p>同一 PL 内通过 flow distinguisher（如 user）看是不是某个 controller / SA 在打高 QPS，常见是写循环、watch 重连风暴或 finalizer 死循环。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 缓解方式</div><p>修客户端（指数退避、合并 update）；调整 FlowSchema 把关键 controller 提到独立 PL；必要时为该 PL 增加 assured concurrency shares。</p></div>
<div class="qa-summary">面试口径：429 不是单纯调大并发就能解决，要按 APF 的 FlowSchema → PriorityLevel → flow distinguisher 链路定位"是谁把哪个优先级队列打满"。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ValidatingAdmissionPolicy 和 OPA/Gatekeeper、Kyverno 怎么选？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从部署成本、表达力、稳定性影响、动态数据需求四个维度比。</p>
<div class="qa-section"><div class="qa-section-title">1. 静态最小权限基线</div><p>"禁止特权容器""强制带 owner label""限制镜像仓库前缀"这类规则，用 VAP 最合适，零部署，毫秒级，写路径无远程调用。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 复杂或动态策略</div><p>需要查外部数据（IAM、CMDB）、跨集群同步、做 mutation 或全量审计的，仍要靠 OPA/Gatekeeper 或 Kyverno，因为它们能跑任意逻辑。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 稳定性</div><p>Webhook 挂了可能阻塞 API Server 写路径，必须配超时和 failurePolicy=Ignore；VAP 没这个问题。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 治理</div><p>真实集群往往是混合：80% 静态规则用 VAP，20% 复杂策略用 Kyverno/Gatekeeper；都要做策略灰度（先 Audit/Warn 再 Deny）。</p></div>
<div class="qa-summary">面试口径：能用 CEL 表达的策略优先 VAP，需要外部数据或复杂逻辑才上 Kyverno/Gatekeeper；新策略上线一律先 Audit/Warn，再切 Deny。</div>
</div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

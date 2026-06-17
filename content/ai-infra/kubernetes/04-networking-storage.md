## 一句话结论

K8S 网络和存储解决 Pod 如何被访问、如何发现服务、如何挂载持久数据。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Kubernetes 核心 |
| 章节类型 | 系统类 |
| 解决问题 | 围绕控制面、调度资源模型、Workload Controller、网络存储、安全多租户、排障和 AI Infra GPU/DRA 建立平台面试答案。 |
| 面试抓手 | 按 CNI、Service、DNS、Ingress、PV/PVC/CSI 讲。 |

<div class="card card-m">
<h3>网络与存储：Pod 能不能被访问，数据能不能挂上</h3>
<p>网络和存储经常一起出现在排障题里。Pod 启动不仅要调度成功，还要 CNI 分配网络、CSI 挂载卷；服务访问不仅要 Pod Running，还要 readiness、EndpointSlice、Service 转发和 DNS 都正常。</p>
</div>

<div class="card card-s">
<h3>Kubernetes 网络模型</h3>
<table>
<tr><th>对象/机制</th><th>作用</th><th>面试重点</th></tr>
<tr><td>Pod IP</td><td>每个 Pod 一个可路由 IP</td><td>同集群 Pod 可直接通信，具体由 CNI 实现</td></tr>
<tr><td>CNI</td><td>为 Pod 配网、分配 IP、配置路由/隧道/策略</td><td>Calico、Cilium、Flannel 等实现差异</td></tr>
<tr><td>Service</td><td>为一组 Pod 提供稳定访问入口</td><td>通过 selector 关联 endpoints</td></tr>
<tr><td>EndpointSlice</td><td>保存 Service 后端 Pod 地址</td><td>替代老 Endpoints，更适合大规模</td></tr>
<tr><td>kube-proxy</td><td>实现 Service VIP 到后端 Pod 的转发</td><td>iptables、IPVS 模式</td></tr>
<tr><td>eBPF datapath</td><td>替代或增强 kube-proxy 的数据面</td><td>性能、可观测性、网络策略</td></tr>
<tr><td>CoreDNS</td><td>集群 DNS 解析</td><td>Service DNS、Headless DNS、外部解析</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Service 类型与访问路径</h3>
<table>
<tr><th>类型</th><th>作用</th><th>典型场景</th><th>追问点</th></tr>
<tr><td>ClusterIP</td><td>集群内虚拟 IP</td><td>内部服务访问</td><td>VIP 如何转发到 Pod</td></tr>
<tr><td>NodePort</td><td>在每个节点暴露端口</td><td>简单外部访问或 LB 后端</td><td>端口范围、流量路径</td></tr>
<tr><td>LoadBalancer</td><td>对接云厂商/负载均衡器</td><td>生产外部入口</td><td>云控制器如何创建 LB</td></tr>
<tr><td>ExternalName</td><td>返回外部 DNS CNAME</td><td>集群内引用外部服务</td><td>不创建 ClusterIP 和 endpoints</td></tr>
<tr><td>Headless</td><td><code>clusterIP: None</code>，直接返回后端 Pod DNS</td><td>StatefulSet、服务发现、自定义负载均衡</td><td>和 ClusterIP 的核心区别</td></tr>
</table>
</div>

<div class="card card-w">
<h3>Service 不通排查链路</h3>
<ol>
<li>看客户端访问的是 DNS、ClusterIP、NodePort 还是外部 LB。</li>
<li>检查 Service selector 是否匹配 Pod label。</li>
<li>检查 EndpointSlice 是否有 ready endpoints。</li>
<li>检查 Pod readinessProbe 是否失败。</li>
<li>进入 Pod 直接访问目标 Pod IP 和端口，区分应用问题与 Service 问题。</li>
<li>检查 NetworkPolicy、CNI、kube-proxy/eBPF 数据面、节点路由和安全组。</li>
<li>检查 CoreDNS 解析是否正常。</li>
</ol>
</div>

<div class="card card-s">
<h3>PV / PVC / StorageClass / CSI</h3>
<table>
<tr><th>对象/组件</th><th>职责</th><th>面试重点</th></tr>
<tr><td>PV</td><td>集群中的实际存储资源</td><td>容量、访问模式、回收策略</td></tr>
<tr><td>PVC</td><td>用户对存储的声明</td><td>像 Pod 申请 CPU 一样申请存储</td></tr>
<tr><td>StorageClass</td><td>动态供给模板</td><td>provisioner、parameters、reclaimPolicy、volumeBindingMode</td></tr>
<tr><td>CSI Controller</td><td>创建/删除/扩容卷、Attach/Detach</td><td>通常在控制面或独立 Deployment</td></tr>
<tr><td>CSI Node</td><td>节点侧 mount/unmount</td><td>通常是 DaemonSet</td></tr>
<tr><td>kubelet Volume Manager</td><td>在 Pod 启动前准备 volume</td><td>Pod 卡 ContainerCreating 常看这里</td></tr>
</table>
</div>

<div class="card card-m">
<h3>PV/PVC 绑定与 WaitForFirstConsumer</h3>
<p>普通动态供给可能在 Pod 调度前就创建卷，但对本地盘、可用区相关云盘等存储，提前创建可能导致卷所在拓扑和 Pod 调度节点不一致。<code>WaitForFirstConsumer</code> 会延迟卷绑定和创建，等 scheduler 结合 Pod 约束和存储拓扑一起决策。</p>
<table>
<tr><th>模式</th><th>行为</th><th>适合场景</th></tr>
<tr><td>Immediate</td><td>PVC 创建后立即绑定/供给 PV</td><td>无拓扑限制或共享存储</td></tr>
<tr><td>WaitForFirstConsumer</td><td>等第一个 Pod 使用 PVC 时再结合调度创建/绑定</td><td>本地盘、云盘可用区、拓扑敏感存储</td></tr>
<tr><td>StatefulSet volumeClaimTemplates</td><td>为每个 Pod 自动创建独立 PVC</td><td>数据库、消息队列、有状态训练组件</td></tr>
</table>
</div>

<div class="card card-w">
<h3>Ingress / Gateway API：南北向流量入口的两代演进</h3>
<p>Service 解决“集群内部怎么访问 Pod”，Ingress / Gateway API 解决“集群外部怎么进来”。Ingress 是 v1 时代的入口对象，能力相对单一（HTTP host/path 路由）；Gateway API 是社区推出的新一代标准，把入口拆成 GatewayClass / Gateway / *Route 三层，把基础设施权限和应用路由权限分开。</p>
<table>
<tr><th>对象</th><th>作用</th><th>谁来管</th><th>面试关注点</th></tr>
<tr><td>IngressClass</td><td>声明集群里有哪种 Ingress 控制器</td><td>平台/集群管理员</td><td>支持多套 Ingress 共存（Nginx、Traefik、云厂商 LB）</td></tr>
<tr><td>Ingress</td><td>HTTP/HTTPS host + path 路由 → Service</td><td>应用方</td><td>能力有限，rewrite/auth/重试常靠 annotation 扩展</td></tr>
<tr><td>GatewayClass</td><td>声明一类 Gateway 实现</td><td>实现方/平台</td><td>类似 StorageClass，定义“某种网关”的能力</td></tr>
<tr><td>Gateway</td><td>实际监听的入口（IP、端口、TLS）</td><td>平台</td><td>把基础设施配置和路由配置解耦</td></tr>
<tr><td>HTTPRoute / TCPRoute / GRPCRoute</td><td>路由规则</td><td>应用方</td><td>支持 host、path、header、weight、mirror、timeout、retry</td></tr>
<tr><td>ReferenceGrant</td><td>跨 namespace 引用授权</td><td>资源所有者</td><td>解决多租户下 Route 引用别 namespace 的 Service 问题</td></tr>
</table>
<div class="qa-summary">面试口径：Ingress 是入口对象的“第一代”，Gateway API 把网关基础设施和应用路由解耦，更适合多租户和复杂流量治理。生产上常见的入口实现有 Nginx Ingress、Traefik、Istio Gateway、Envoy Gateway、云厂商 ALB。</div>
</div>

<div class="card card-d">
<h3>NetworkPolicy：默认全通，加策略变隔离</h3>
<p>Kubernetes 默认网络是<strong>“同 Pod、同 Namespace、跨 Namespace 全部互通”</strong>。NetworkPolicy 是 namespace 级的网络策略对象，用于定义“哪些 Pod 可以访问哪些 Pod、哪些端口”。它由 CNI 实现真正落地，CNI 不支持就形同虚设。</p>
<table>
<tr><th>关键字段</th><th>作用</th><th>常见坑</th></tr>
<tr><td><code>podSelector</code></td><td>选中要被保护的目标 Pod</td><td>空 selector 表示选中 namespace 全部 Pod</td></tr>
<tr><td><code>policyTypes: [Ingress, Egress]</code></td><td>声明这条策略管入向、出向，还是两个都管</td><td>没列出的方向就不会被这条策略限制</td></tr>
<tr><td><code>ingress.from / egress.to</code></td><td>允许的来源/目标</td><td>支持 podSelector、namespaceSelector、ipBlock</td></tr>
<tr><td><code>ports</code></td><td>允许的端口和协议</td><td>不写代表所有端口都放行</td></tr>
<tr><td>“默认拒绝”模式</td><td>用一条空规则的策略实现 deny-all</td><td>常见做法：先 deny-all，再按需开放</td></tr>
</table>
<table>
<tr><th>能力</th><th>NetworkPolicy v1</th><th>AdminNetworkPolicy（社区演进）</th></tr>
<tr><td>作用域</td><td>单 namespace</td><td>集群级，平台管理员视角</td></tr>
<tr><td>动作</td><td>仅 allow</td><td>支持 allow / deny / pass，有优先级</td></tr>
<tr><td>表达 L7</td><td>不支持</td><td>需要 CNI（如 Cilium）扩展</td></tr>
<tr><td>典型用途</td><td>业务 namespace 自治</td><td>平台基线（例如禁止访问元数据服务）</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">面试常追问</div><p><strong>“写了 NetworkPolicy 但不生效？”</strong>九成是 CNI 没启用 NetworkPolicy 实现（Flannel 默认没有）；剩下情况是 selector 写错、policyTypes 没写 Egress 导致出向没限制、或者忘了 DNS（CoreDNS 53/UDP）也要放行。</p></div>
</div>

<div class="card card-s">
<h3>CNI 实现对比：Flannel / Calico / Cilium</h3>
<p>CNI 是 Pod 网络的实现层，决定 Pod IP 怎么分、跨节点流量怎么走、NetworkPolicy 怎么落地。面试不要只说“我们用了 Calico”，要能说清三种主流实现的差异。</p>
<table>
<tr><th>维度</th><th>Flannel</th><th>Calico</th><th>Cilium</th></tr>
<tr><td>跨节点数据面</td><td>VXLAN / host-gw（默认 overlay）</td><td>BGP（underlay 路由）或 VXLAN/IPIP</td><td>VXLAN / Geneve / native routing，可走 eBPF</td></tr>
<tr><td>NetworkPolicy</td><td>不原生支持，需要外挂</td><td>原生支持 + GlobalNetworkPolicy</td><td>原生支持 + L7（HTTP/gRPC/Kafka）</td></tr>
<tr><td>kube-proxy 替代</td><td>否</td><td>否（可选 eBPF 模式）</td><td>可完全替代 kube-proxy</td></tr>
<tr><td>可观测性</td><td>弱</td><td>中</td><td>强（Hubble，eBPF 流量级可视化）</td></tr>
<tr><td>典型适用</td><td>简单集群、入门</td><td>多租户、企业生产</td><td>大规模、需要 L7 策略和深度可观测</td></tr>
</table>
<div class="qa-summary">面试口径：Flannel 简单但策略弱；Calico 偏路由协议（BGP）+ 原生 NetworkPolicy；Cilium 走 eBPF，能替换 kube-proxy 并提供 L7 策略和 Hubble 可观测性。</div>
</div>

<div class="card card-d">
<h3>kube-proxy 三种模式：iptables / IPVS / eBPF</h3>
<p>Service VIP 到后端 Pod 的转发由 kube-proxy（或 CNI 替代实现）完成。三种模式在性能、规则规模和可观测性上差异明显。</p>
<table>
<tr><th>维度</th><th>iptables</th><th>IPVS</th><th>eBPF（Cilium / Calico）</th></tr>
<tr><td>转发原理</td><td>通过 NAT 链做 DNAT/SNAT</td><td>内核 IPVS 模块做四层负载均衡</td><td>eBPF 程序挂在 socket / tc / XDP</td></tr>
<tr><td>规则数量</td><td>O(N)，Service 多了 iptables 规则线性膨胀</td><td>哈希表 O(1) 查找</td><td>map O(1)，且不依赖 iptables</td></tr>
<tr><td>大集群表现</td><td>10k+ Service 时同步慢、CPU 高</td><td>明显优于 iptables</td><td>最佳，且支持精细可观测</td></tr>
<tr><td>负载均衡算法</td><td>随机/轮询有限</td><td>rr / lc / sh / dh 等多种</td><td>由 eBPF 程序定义</td></tr>
<tr><td>排查工具</td><td><code>iptables -t nat -L</code></td><td><code>ipvsadm -ln</code></td><td><code>cilium service list</code> / Hubble</td></tr>
<tr><td>conntrack 依赖</td><td>强依赖</td><td>仍依赖</td><td>可绕过 conntrack（提升性能）</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">面试口径</div><p>大集群（数千 Service / 数万 Pod）必须放弃 iptables 模式，要么 IPVS，要么 eBPF。eBPF 还能解决 conntrack 表打满的稳定性问题，并提供 L7 可观测能力。</p></div>
</div>

<div class="card card-m">
<h3>CoreDNS 与集群 DNS 解析链路</h3>
<p>Pod 里 <code>nslookup my-svc</code> 能拿到 IP，背后是 kubelet → /etc/resolv.conf → CoreDNS → API Server endpoint 缓存这条链。面试常考 <code>ndots</code>、search domain 和 NodeLocal DNSCache。</p>
<table>
<tr><th>机制</th><th>作用</th><th>面试要点</th></tr>
<tr><td>ClusterFirst DNS 策略</td><td>Pod 默认把 CoreDNS 作为上游</td><td>kubelet 把 CoreDNS Service IP 写进 <code>/etc/resolv.conf</code></td></tr>
<tr><td><code>ndots: 5</code></td><td>少于 5 个点的域名会先按 search 列表补全</td><td>访问外网域名性能差时，降低 ndots 或写 FQDN（结尾加点）</td></tr>
<tr><td>search domain</td><td>例如 <code>&lt;ns&gt;.svc.cluster.local svc.cluster.local cluster.local</code></td><td>解释为什么 <code>my-svc</code> 能被解析为 <code>my-svc.&lt;ns&gt;.svc.cluster.local</code></td></tr>
<tr><td>Headless DNS</td><td>返回 A 记录列表，每个 Pod 一条</td><td>StatefulSet <code>pod-0.svc.ns.svc.cluster.local</code> 也是这个机制</td></tr>
<tr><td>NodeLocal DNSCache</td><td>每个节点起一个本地缓存代理</td><td>避免 conntrack 表泄漏、CoreDNS 抖动放大；大集群必备</td></tr>
<tr><td>CoreDNS plugin chain</td><td>kubernetes / forward / cache / log / autopath</td><td>解析慢通常先看 forward 上游和 cache 命中率</td></tr>
</table>
</div>

<div class="card card-s">
<h3>ConfigMap / Secret 挂载到 Pod</h3>
<p>ConfigMap 和 Secret 是 Pod 拿配置的标准方式。挂载方式决定它们是只读还是支持热更新，也决定排障路径。</p>
<table>
<tr><th>挂载方式</th><th>是否热更新</th><th>使用场景</th></tr>
<tr><td>environment variables</td><td>否（Pod 重建才变）</td><td>启动参数、简单配置</td></tr>
<tr><td>volumeMount（projected / configMap / secret 卷）</td><td>是，kubelet 周期同步（默认约 60s）</td><td>大段配置文件，希望支持热更新</td></tr>
<tr><td>subPath 单文件挂载</td><td><strong>否</strong>，subPath 不会更新</td><td>挂某一个文件到固定路径</td></tr>
<tr><td>immutable: true</td><td>不可变</td><td>大规模集群减少 watch 开销，避免误改</td></tr>
</table>
<div class="qa-summary">面试口径：env 不热更，volume 挂载会热更（除 subPath），Secret 默认只是 base64 不是加密，真正加密要靠 etcd encryption at rest 或外部 Secret 系统。</div>
</div>

<div class="card card-w">
<h3>AI 训练场景的网络扩展：RDMA / Multus / SR-IOV / hostNetwork</h3>
<p>大模型训练对网络带宽和延迟非常敏感（AllReduce、参数同步），仅靠默认 CNI 的 overlay 网络往往不够。AI Infra 集群常见的扩展方式：</p>
<table>
<tr><th>方案</th><th>解决什么问题</th><th>典型用法</th><th>面试关注点</th></tr>
<tr><td>hostNetwork</td><td>Pod 直接用宿主机网络栈，零开销</td><td>NCCL 直连场景、节点级 agent</td><td>端口冲突、不安全、不能再走 Service 网格</td></tr>
<tr><td>Multus</td><td>给一个 Pod 接多张网卡</td><td>主网卡走默认 CNI，副网卡走 RDMA / 存储网</td><td>NetworkAttachmentDefinition 是它的核心 CRD</td></tr>
<tr><td>SR-IOV CNI</td><td>把物理网卡的 VF 直通给 Pod</td><td>RDMA、低延迟交易、NFV</td><td>每个 VF 是独立的网卡，绕过软件交换</td></tr>
<tr><td>RDMA shared device plugin</td><td>把 RDMA 设备暴露成扩展资源</td><td><code>rdma/hca: 1</code></td><td>调度时按 RDMA 设备亲和（同 NIC、同 NUMA）</td></tr>
<tr><td>InfiniBand / RoCE</td><td>低延迟集合通信链路</td><td>NCCL over IB、GPUDirect RDMA</td><td>需要拓扑感知调度，避免跨 leaf/spine 通信</td></tr>
</table>
<div class="qa-section"><div class="qa-section-title">面试口径</div><p>训练 Pod 通常长这样：用 Multus 同时挂主 CNI 网卡（控制面、Service 访问）和一张 RDMA 网卡（GPU 间集合通信）；调度器还要保证同一训练任务的 Pod 落在同一 leaf switch 下，否则 AllReduce 会跨 spine，性能腰斩。</p></div>
</div>

<div class="card card-m">

<h3>网络与存储高频问答</h3>

<p>本模块的问答按“概念 → 作用 → 链路/排查 → 面试口径”组织，避免只背一段结论。</p>

</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Service 不通怎么排查？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 确认访问入口</div><p>先确认客户端访问的是 DNS、ClusterIP、NodePort、LoadBalancer 还是 Ingress，不同入口对应不同链路。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 检查 Service 到 Pod 的映射</div><p>看 Service selector 是否匹配 Pod labels，再看 EndpointSlice 是否生成 ready endpoints。没有 endpoints 通常是 selector、readiness 或 Pod 状态问题。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 区分应用和 Service 问题</div><p>直接访问 Pod IP:Port，如果 Pod IP 不通，多半是应用、端口、容器或 CNI 问题；如果 Pod IP 通但 Service 不通，再看 kube-proxy/eBPF。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 检查网络基础设施</div><p>继续排查 CoreDNS、NetworkPolicy、CNI、kube-proxy/IPVS/iptables/eBPF、节点路由、安全组和云 LB。</p></div>
<div class="qa-summary">面试口径：Service 不通按“入口 → selector/endpoints → Pod 直连 → DNS/策略/数据面”逐层缩小范围。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Headless Service 和 ClusterIP Service 的区别？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. ClusterIP 的概念</div><p>ClusterIP Service 会分配一个虚拟 IP，客户端访问 VIP 后由 kube-proxy、IPVS 或 eBPF 转发到后端 Pod。</p></div>
<div class="qa-section"><div class="qa-section-title">2. Headless 的概念</div><p>Headless Service 设置 <code>clusterIP: None</code>，不提供 VIP，DNS 直接返回后端 Pod IP 或稳定域名。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 作用差异</div><p>ClusterIP 适合普通服务负载均衡；Headless 适合客户端自己做负载均衡、服务发现或需要感知每个副本身份的场景。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 典型场景</div><p>StatefulSet 常配 Headless Service，让 <code>pod-0.service.namespace.svc</code> 这类稳定域名指向固定副本。</p></div>
<div class="qa-summary">面试口径：ClusterIP 提供稳定 VIP 和服务转发，Headless 不提供 VIP，而是通过 DNS 暴露后端 Pod 地址。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Ingress 和 Gateway API 有什么区别？什么时候选哪个？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说能力差异，再讲谁来管，最后给场景建议。</p>
<div class="qa-section"><div class="qa-section-title">1. 模型差异</div><p>Ingress 把入口 IP、TLS、host/path 路由全塞在一个对象里；Gateway API 拆成 GatewayClass / Gateway / *Route 三层，平台管 Gateway，应用管 Route。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 能力差异</div><p>Ingress 主要支持 HTTP host/path，复杂能力（rewrite、auth、重试、流量切分）多靠 annotation 扩展，跨实现不通用。Gateway API 把 header 匹配、加权切分、mirror、timeout、retry 写进了标准字段。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 多协议</div><p>Gateway API 同时定义了 HTTPRoute / TCPRoute / TLSRoute / GRPCRoute，原生支持四层转发，Ingress 一般只管七层。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 选型建议</div><p>新建集群、需要多租户和精细流量治理优先 Gateway API；已有大量 Ingress 的存量集群，迁移要看 Ingress 控制器是否同时支持 Gateway API。</p></div>
<div class="qa-summary">面试口径：Ingress 是入口对象第一代，Gateway API 是把基础设施和应用路由解耦的新一代标准，多租户和复杂流量治理场景更适合 Gateway API。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Ingress Controller 和 Service Mesh 有什么区别？</div>
<div class="qa-a">
<p>Ingress Controller 主要解决南北向入口流量：外部 HTTP/HTTPS 请求如何根据 host/path 进入集群并路由到 Service。Service Mesh 主要解决东西向服务间通信治理：mTLS、重试、超时、熔断、流量拆分、可观测性和零信任。</p>
<table>
<tr><th>维度</th><th>Ingress Controller</th><th>Service Mesh</th></tr>
<tr><td>主要流量方向</td><td>外部 → 集群</td><td>服务 ↔ 服务</td></tr>
<tr><td>核心能力</td><td>入口路由、TLS 终止、host/path 转发</td><td>mTLS、流量治理、熔断、重试、可观测性</td></tr>
<tr><td>典型实现</td><td>Nginx、Traefik、HAProxy、Envoy Gateway</td><td>Istio、Linkerd、Consul Connect</td></tr>
</table>
<div class="qa-summary">面试口径：Ingress 管入口，Service Mesh 管服务间治理；两者可以共存，不是简单替代关系。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 写了 NetworkPolicy 但没生效，怎么排查？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从 CNI 是否支持开始往下找，依次看 selector、方向、DNS。</p>
<div class="qa-section"><div class="qa-section-title">1. 先确认 CNI 支持</div><p>NetworkPolicy 是规范，由 CNI 落地。Flannel 默认没有实现，需要换 Calico / Cilium 或加上 NetworkPolicy 控制器。<code>kubectl get networkpolicy</code> 能创建不代表能生效。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 检查 selector</div><p>看 <code>podSelector</code> 是否真的匹配目标 Pod 的 label，再看 <code>ingress.from</code> / <code>egress.to</code> 是否正确选中了允许的来源/目标。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 检查 policyTypes</div><p>没显式列出 Egress，出向就不会被这条策略限制。要拒绝出向必须把 <code>Egress</code> 写进 policyTypes。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 不要忘了 DNS</div><p>限制出向时常见坑：忘了放行 CoreDNS 53/UDP，导致业务起来直接解析失败，看起来像“NetworkPolicy 把所有访问都断了”。</p></div>
<div class="qa-summary">面试口径：NetworkPolicy 不生效先看 CNI、selector、policyTypes，再看 DNS 是否被一起切断。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 大集群（10k+ Service）为什么必须放弃 iptables 模式？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从 iptables 的复杂度问题讲起，再讲 IPVS / eBPF 的优势。</p>
<div class="qa-section"><div class="qa-section-title">1. iptables 的本质问题</div><p>每个 Service 在 iptables 里都是 O(N) 条规则，规则之间是线性匹配，链长后查找慢；同步全量 iptables 也是 O(N²) 规模操作。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 表现症状</div><p>Service 数量上万后，kube-proxy 单次 sync 数秒到数十秒，CPU 高，新 Service 生效慢，节点 iptables 大到影响内核报文路径性能。</p></div>
<div class="qa-section"><div class="qa-section-title">3. IPVS</div><p>用内核 IPVS 做四层 LB，O(1) 哈希查找，规则数量与 Service 数解耦，并提供更多负载均衡算法。</p></div>
<div class="qa-section"><div class="qa-section-title">4. eBPF</div><p>Cilium / Calico eBPF 模式可完全替代 kube-proxy，绕开 iptables/conntrack，提供 L7 可观测和更低延迟，更适合超大规模和高性能场景。</p></div>
<div class="qa-summary">面试口径：大集群必须切到 IPVS 或 eBPF，iptables 的线性规则在 Service 上万后会同时拖慢控制面（同步）和数据面（查找）。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ConfigMap / Secret 改了之后 Pod 为什么没更新？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先区分挂载方式，再讲热更新机制和延迟。</p>
<div class="qa-section"><div class="qa-section-title">1. 看挂载方式</div><p>用 env 注入的不会热更，必须重启 Pod；用 volume 挂载的（projected / configMap / secret 卷）会热更。</p></div>
<div class="qa-section"><div class="qa-section-title">2. subPath 是个大坑</div><p>subPath 单文件挂载不支持热更新，用了 subPath 就只能重建 Pod 才能拿到新内容。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 同步周期</div><p>kubelet 默认每 ~60s 同步一次（受 <code>configMapAndSecretChangeDetectionStrategy</code> 影响），所以热更新不是即时，可能有分钟级延迟。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 应用是否监听文件变化</div><p>就算 kubelet 把文件刷新了，应用本身不重读配置也没用，常见做法是 SIGHUP、inotify 或定期 reload。</p></div>
<div class="qa-summary">面试口径：env 注入不热更，volume 挂载会热更但有分钟级延迟，subPath 不会热更，最终生效还要看应用是否重新读取配置。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 训练任务用 hostNetwork 还是 Multus + RDMA？怎么权衡？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先讲两种方案各自的能力，再讲它们的代价。</p>
<div class="qa-section"><div class="qa-section-title">1. hostNetwork 的优势</div><p>Pod 直接用宿主机网络栈，没有 overlay 开销，最低延迟，最简单；NCCL 跨节点通信、节点级 agent 经常这样用。</p></div>
<div class="qa-section"><div class="qa-section-title">2. hostNetwork 的代价</div><p>同节点端口冲突、不能再走 Service 网格 / NetworkPolicy / Sidecar 注入，安全性差，多租户场景几乎不可用。</p></div>
<div class="qa-section"><div class="qa-section-title">3. Multus + RDMA / SR-IOV</div><p>Pod 主网卡走默认 CNI（控制面 / Service 访问），副网卡接入 RDMA / 存储网，AllReduce 走专用低延迟网络，控制面安全模型保留。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 还要看拓扑</div><p>不管哪种方案，调度器都要保证训练 Pod 落在同一 leaf 下，否则 AllReduce 跨 spine 会让带宽腰斩；这是 Topology-aware 调度和 DRA attributes 要解决的问题。</p></div>
<div class="qa-summary">面试口径：单机训练 / 节点级 agent 可以 hostNetwork；多租户 + 大规模训练用 Multus 给 Pod 接 RDMA 副网卡，并配合拓扑感知调度。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: PVC 一直 Pending 怎么排查？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先说概念和作用，再按链路或排查维度展开，最后给一句面试总结。</p>
<div class="qa-section"><div class="qa-section-title">1. 先看 PVC 事件</div><p>用 <code>kubectl describe pvc</code> 看 Events，确认是 StorageClass 不存在、provisioner 异常、容量不足还是访问模式不匹配。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 检查 StorageClass</div><p>看 provisioner、parameters、reclaimPolicy、allowVolumeExpansion 和 <code>volumeBindingMode</code>。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 理解 WaitForFirstConsumer</div><p>如果是 <code>WaitForFirstConsumer</code>，PVC 可能会等使用它的 Pod 参与调度后才绑定或创建 PV。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 检查底层和拓扑</div><p>云盘、本地盘要看可用区、节点拓扑、配额、权限、CSI Controller/Node 组件和底层存储状态。</p></div>
<div class="qa-summary">面试口径：PVC Pending 按“PVC Events → StorageClass/CSI → WaitForFirstConsumer → Pod 调度拓扑 → 底层存储”排查。</div>
</div>
</div>

## 面试回答

**30 秒版：**

K8S 网络和存储解决 Pod 如何被访问、如何发现服务、如何挂载持久数据。 按 CNI、Service、DNS、Ingress、PV/PVC/CSI 讲。

**2 分钟版：**

网络和存储解决 Pod 怎么被访问、怎么发现服务、怎么挂持久数据。网络侧每个 Pod 一个可路由 IP，由 CNI 分配并配路由（Flannel 简单但策略弱，Calico 走 BGP 加原生 NetworkPolicy，Cilium 走 eBPF 可替代 kube-proxy 并提供 L7 和 Hubble 可观测）；Service 通过 selector 关联 EndpointSlice，kube-proxy 把 VIP 转发到后端 Pod，iptables 是 O(N) 规则，大集群上万 Service 必须切 IPVS 或 eBPF；Headless Service 不给 VIP，直接用 DNS 暴露 Pod，配合 StatefulSet 稳定域名；南北向入口从 Ingress 演进到 Gateway API，把 GatewayClass/Gateway/Route 三层解耦。存储侧 PVC 是声明、PV 是实际资源、StorageClass 做动态供给，WaitForFirstConsumer 会延迟绑定让 scheduler 结合 Pod 约束和存储拓扑一起决策。排障 Service 不通按"入口→selector/endpoints→Pod 直连→DNS/NetworkPolicy/数据面"逐层缩小，PVC Pending 按"Events→StorageClass/CSI→拓扑"排查。AI 训练对带宽延迟敏感，常用 hostNetwork 或 Multus 给 Pod 接 RDMA 副网卡走 NCCL 集合通信，并配合拓扑感知调度保证 Pod 落在同一 leaf，避免 AllReduce 跨 spine 带宽腰斩。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

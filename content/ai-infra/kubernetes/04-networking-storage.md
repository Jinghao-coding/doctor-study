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

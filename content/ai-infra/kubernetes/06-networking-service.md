<div class="card card-m">
<h3>Kubernetes 网络模型</h3>
<p>Kubernetes 网络面试的核心不是背 CNI 名字，而是讲清楚三个基本要求：Pod 之间可以直接通信、Node 可以和 Pod 通信、Service 为动态 Pod 集合提供稳定访问入口。</p>
<table>
<tr><th>对象</th><th>网络语义</th><th>实现依赖</th><th>面试重点</th></tr>
<tr><td>Pod IP</td><td>每个 Pod 有独立 IP，Pod 内容器共享网络命名空间</td><td>CNI 插件分配 IP、配置路由和 veth</td><td>同 Pod 内容器通过 localhost 通信，不同 Pod 通过 Pod IP 通信</td></tr>
<tr><td>Node 网络</td><td>节点之间可路由，承载跨节点 Pod 通信</td><td>Overlay、BGP、云厂商 VPC 或 underlay</td><td>跨节点通信是否封装取决于 CNI 实现</td></tr>
<tr><td>Service IP</td><td>为一组 Pod 提供稳定虚拟入口</td><td>kube-proxy 或 eBPF 数据面</td><td>Service 不等于反向代理进程，通常是节点上的转发规则</td></tr>
<tr><td>DNS</td><td>把 service name 解析为 ClusterIP 或 Pod IP</td><td>CoreDNS + kube-dns service</td><td>DNS 故障会表现为服务名不通但 IP 直连可能正常</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Pod 跨节点通信链路</h3>
<p>一个 Pod 访问另一个节点上的 Pod 时，流量通常从容器网络命名空间出发，经 veth 到宿主机，再由 CNI 配置的路由、隧道或 eBPF 程序转发到目标节点，最后进入目标 Pod。</p>
<ol>
<li>源容器发包到目标 Pod IP。</li>
<li>数据包从容器 eth0 进入 veth pair 的宿主机端。</li>
<li>宿主机根据 CNI 配置的路由或 eBPF 逻辑决定下一跳。</li>
<li>如果是 overlay CNI，可能封装 VXLAN/Geneve 后跨节点传输。</li>
<li>目标节点解封装或路由转发到目标 Pod 的 veth。</li>
<li>目标容器收到数据包。</li>
</ol>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CNI 到底负责什么？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">创建时</div><p>kubelet 创建 Pod sandbox 后调用 CNI 插件，为 Pod 分配 IP、创建 veth、配置路由、配置网络命名空间。</p></div>
<div class="qa-section"><div class="qa-section-title">删除时</div><p>Pod 删除时 kubelet 调用 CNI DEL，释放 IP、清理网络设备和相关规则。</p></div>
<div class="qa-summary">CNI 解决 Pod 网络接入问题，Service 转发通常由 kube-proxy 或 eBPF 数据面解决。</div>
</div>
</div>
</div>

<div class="card card-m">
<h3>Service 类型对比</h3>
<table>
<tr><th>Service 类型</th><th>作用</th><th>访问范围</th><th>典型场景</th></tr>
<tr><td>ClusterIP</td><td>集群内部虚拟 IP</td><td>集群内</td><td>微服务内部访问，默认类型</td></tr>
<tr><td>NodePort</td><td>每个节点开放固定端口，转发到 Service</td><td>集群外可通过任意节点 IP + 端口访问</td><td>简单暴露、测试环境，不适合复杂生产入口</td></tr>
<tr><td>LoadBalancer</td><td>创建云厂商负载均衡器并转发到 Service</td><td>集群外</td><td>云上生产入口</td></tr>
<tr><td>ExternalName</td><td>把 Service 名称映射到外部 DNS 名称</td><td>依赖外部 DNS</td><td>集群内用统一 service name 访问外部服务</td></tr>
<tr><td>Headless Service</td><td>clusterIP: None，不分配虚拟 IP</td><td>DNS 直接返回后端 Pod IP</td><td>StatefulSet、数据库、分布式训练 worker 直连</td></tr>
</table>
</div>

<div class="card card-w">
<h3>kube-proxy：iptables、IPVS 与 eBPF</h3>
<p>Service 的转发能力传统上由 kube-proxy 维护节点规则实现。面试中经常问 iptables 和 IPVS 的区别，近年来也会追问 eBPF 数据面。</p>
<table>
<tr><th>模式</th><th>实现方式</th><th>优点</th><th>不足</th></tr>
<tr><td>iptables</td><td>生成大量 iptables 规则，用随机概率做负载均衡</td><td>成熟、依赖少、兼容性强</td><td>规则多时更新和匹配成本高，可观测性一般</td></tr>
<tr><td>IPVS</td><td>利用 Linux IPVS 内核负载均衡能力</td><td>性能更好，支持更多调度算法</td><td>依赖 IPVS 模块，问题排查需要理解 ipvsadm</td></tr>
<tr><td>eBPF</td><td>在内核 hook 点运行 eBPF 程序转发</td><td>性能高、可观测性强、可绕过部分 iptables 路径</td><td>依赖 CNI/内核能力，排查方式不同</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Service 是不是一个真正的代理进程？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">传统实现</div><p>不是。ClusterIP 通常不是某个进程监听的真实 IP，而是 kube-proxy 在每个节点维护的转发规则。</p></div>
<div class="qa-section"><div class="qa-section-title">流量路径</div><p>访问 ClusterIP 时，内核网络栈命中 iptables/IPVS/eBPF 规则，把流量转发到某个 Endpoint Pod。</p></div>
<div class="qa-summary">Service 是抽象，kube-proxy/eBPF 是数据面实现。</div>
</div>
</div>
</div>

<div class="card card-s">
<h3>CoreDNS 与服务发现</h3>
<p>Kubernetes 中服务名解析通常由 CoreDNS 提供。Pod 的 DNS 配置会指向 kube-dns Service，CoreDNS 根据 Service、EndpointSlice、Pod 等对象生成解析结果。</p>
<table>
<tr><th>查询形式</th><th>含义</th><th>返回结果</th></tr>
<tr><td>svc-name</td><td>同 namespace 下服务</td><td>ClusterIP 或 headless 后端 Pod IP</td></tr>
<tr><td>svc-name.namespace</td><td>指定 namespace 下服务</td><td>对应 Service 解析结果</td></tr>
<tr><td>svc-name.namespace.svc.cluster.local</td><td>完整集群域名</td><td>最明确，排查 DNS 时常用</td></tr>
<tr><td>headless service</td><td>clusterIP: None</td><td>直接返回后端 Pod IP 列表</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Service 不通怎么区分 DNS 问题和网络问题？</div>
<div class="qa-a">
<div class="qa-grid"><div class="qa-mini"><strong>先测 DNS</strong>nslookup service-name，确认是否能解析。</div><div class="qa-mini"><strong>再测 ClusterIP</strong>直接 curl ClusterIP:port，绕过服务名。</div><div class="qa-mini"><strong>再测 Endpoint</strong>直接访问 Pod IP:containerPort，绕过 Service 转发。</div><div class="qa-mini"><strong>最后看规则</strong>检查 endpoints、EndpointSlice、kube-proxy、NetworkPolicy。</div></div>
</div>
</div>
</div>

<div class="card card-d">
<h3>NetworkPolicy</h3>
<p>NetworkPolicy 用于限制 Pod 间东西向流量。它本身只是 Kubernetes API 对象，是否真正生效取决于 CNI 是否支持 NetworkPolicy。</p>
<table>
<tr><th>概念</th><th>说明</th><th>高频误区</th></tr>
<tr><td>默认允许</td><td>没有 NetworkPolicy 时，Pod 通信默认全允许</td><td>创建一个 policy 后，被选中的 Pod 会进入默认拒绝模型</td></tr>
<tr><td>podSelector</td><td>选择被保护的 Pod</td><td>不是选择访问来源，而是选择策略作用对象</td></tr>
<tr><td>ingress / egress</td><td>分别控制入站和出站</td><td>只写 ingress 不会自动限制 egress</td></tr>
<tr><td>CNI 支持</td><td>Calico、Cilium 等支持策略</td><td>如果 CNI 不支持，创建 policy 也不生效</td></tr>
</table>
</div>

<div class="card card-d">
<h3>官方参考</h3>
<div class="resource-grid">
<a class="resource-card" href="https://kubernetes.io/docs/concepts/services-networking/"><div class="resource-type">official</div><div class="resource-title">Services, Load Balancing, and Networking</div><div class="resource-desc">Kubernetes 网络与 Service 总入口。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/services-networking/service/"><div class="resource-type">official</div><div class="resource-title">Service</div><div class="resource-desc">ClusterIP、NodePort、LoadBalancer、Headless Service 等。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/"><div class="resource-type">official</div><div class="resource-title">DNS for Services and Pods</div><div class="resource-desc">服务发现、DNS 名称规则、Headless Service 解析。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/"><div class="resource-type">official</div><div class="resource-title">Network Plugins</div><div class="resource-desc">CNI 网络插件与 Pod 网络接入机制。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/concepts/services-networking/network-policies/"><div class="resource-type">official</div><div class="resource-title">Network Policies</div><div class="resource-desc">Pod 间访问控制和网络隔离。</div></a>
</div>
</div>

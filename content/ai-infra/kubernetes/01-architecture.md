<div class="card card-s">
<h3>控制面组件</h3>
<table>
<tr><th>组件</th><th>职责</th><th>关键细节</th></tr>
<tr><td>kube-apiserver</td><td>集群 API 入口，所有操作的网关</td><td>无状态，支持水平扩展。所有组件通过它通信</td></tr>
<tr><td>etcd</td><td>分布式键值存储，集群唯一的持久化状态</td><td>Raft 共识，建议 3 或 5 节点。性能瓶颈往往在 etcd</td></tr>
<tr><td>kube-scheduler</td><td>为未绑定的 Pod 选择合适节点</td><td>可插件化扩展（Scheduling Framework）</td></tr>
<tr><td>kube-controller-manager</td><td>运行控制循环：Deployment、ReplicaSet、Node 等</td><td>声明式 API 的执行者，负责将实际状态收敛到期望状态</td></tr>
</table>

<h3>数据面组件</h3>
<table>
<tr><th>组件</th><th>职责</th></tr>
<tr><td>kubelet</td><td>节点代理，管理 Pod 生命周期。通过 CRI 调用容器运行时</td></tr>
<tr><td>kube-proxy</td><td>维护网络规则（iptables/IPVS），实现 Service 负载均衡</td></tr>
<tr><td>容器运行时</td><td>containerd / CRI-O，负责拉镜像和运行容器</td></tr>
</table>
</div>

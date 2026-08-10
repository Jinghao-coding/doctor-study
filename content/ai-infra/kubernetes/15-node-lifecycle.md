## Node 注册与 Bootstrap

<div class="card card-m">
<h3>kubelet 启动与节点注册</h3>
<p>新节点加入集群的完整流程：</p>
<ol>
<li><strong>kubelet 启动</strong>：读取 kubeconfig（或 bootstrap kubeconfig），有有效证书则直接加入；没有则进入 TLS Bootstrap 流程。</li>
<li><strong>TLS Bootstrap</strong>：kubelet 使用 bootstrap token（在 kube-system namespace 的 bootstrap token secret 中）创建 CertificateSigningRequest（CSR）。</li>
<li><strong>CSR 审批</strong>：管理员手动审批（<code>kubectl certificate approve</code>）或配置 controller 自动审批（需要正确的 Group 权限）。</li>
<li><strong>证书签发</strong>：API Server 签发 kubelet client 证书，kubelet 将证书和 key 存储到 <code>--cert-dir</code>（默认 /var/lib/kubelet/pki/）。</li>
<li><strong>创建 Node 对象</strong>：kubelet 使用自己的证书向 API Server 创建 Node 对象（或更新已有），Node 对象的 metadata.name 默认是主机名（<code>--hostname-override</code> 可覆盖）。</li>
<li><strong>Node Authorization</strong>：Node authorizer 限制每个 kubelet 只能修改自己的 Node 对象、只能读写自己节点上的 Pod/Service/Secret/PV 等资源，防止 kubelet 越权。</li>
</ol>
<pre><code class="language-bash"># Bootstrap kubeconfig 示例
apiVersion: v1
clusters:
- cluster:
    certificate-authority: /etc/kubernetes/pki/ca.crt
    server: https://api-server:6443
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: tls-bootstrap-token-user
  name: tls-bootstrap
current-context: tls-bootstrap
users:
- name: tls-bootstrap-token-user
  user:
    token: 07401b.f395accd246ae52d  # bootstrap token: <token-id>.<secret>
</code></pre>
</div>

<div class="card card-s">
<h3>kubelet 关键启动参数</h3>
<table>
<tr><th>参数</th><th>作用</th></tr>
<tr><td><code>--kubeconfig</code></td><td>kubelet 访问 API Server 的 kubeconfig 路径</td></tr>
<tr><td><code>--bootstrap-kubeconfig</code></td><td>首次启动时的 bootstrap kubeconfig（用于获取正式证书）</td></tr>
<tr><td><code>--config</code></td><td>KubeletConfiguration 文件（K8s 1.10+ 推荐使用配置文件）</td></tr>
<tr><td><code>--container-runtime-endpoint</code></td><td>CRI endpoint（如 unix:///run/containerd/containerd.sock）</td></tr>
<tr><td><code>--node-ip</code></td><td>节点 IP（多网卡时需要指定）</td></tr>
<tr><td><code>--pod-cidr</code></td><td>该节点 Pod CIDR（某些网络插件要求）</td></tr>
<tr><td><code>--register-node</code></td><td>是否自动注册 Node 对象（默认 true）</td></tr>
</table>
</div>

## Node 状态与健康检测

<div class="card card-m">
<h3>Node Conditions</h3>
<p>Node 对象的 status.conditions 描述节点健康状态：</p>
<table>
<tr><th>Condition</th><th>True 含义</th><th>False 含义</th></tr>
<tr><td>Ready</td><td>节点健康，可以接收 Pod</td><td>节点不健康（kubelet 未上报状态或节点有问题）</td></tr>
<tr><td>MemoryPressure</td><td>节点内存压力大（可用内存低于阈值）</td><td>内存正常</td></tr>
<tr><td>DiskPressure</td><td>节点磁盘压力大（磁盘可用空间或 inode 不足）</td><td>磁盘正常</td></tr>
<tr><td>PIDPressure</td><td>进程数过多（接近内核 pid_max）</td><td>PID 数量正常</td></tr>
<tr><td>NetworkUnavailable</td><td>网络配置不正确（CNI 未就绪）</td><td>网络正常</td></tr>
</table>
<pre><code class="language-yaml"># Node status 片段
status:
  conditions:
  - type: Ready
    status: "True"
    lastHeartbeatTime: "2024-01-15T10:30:00Z"
    lastTransitionTime: "2024-01-01T00:00:00Z"
    reason: "KubeletReady"
    message: "kubelet is posting ready status"
  - type: MemoryPressure
    status: "False"
  - type: DiskPressure
    status: "False"
  addresses:
  - type: InternalIP
    address: 10.0.1.5
  - type: Hostname
    address: node-1
  capacity:
    cpu: "16"
    memory: 64Gi
    pods: "110"
    nvidia.com/gpu: "4"
</code></pre>
</div>

<div class="card card-d">
<h3>Node Lease：快速失败检测</h3>
<p>在 K8s 1.17 之前，kubelet 通过 NodeStatus 更新上报心跳，NodeStatus 更新开销大（包含 Pod/Volume/Image 等完整状态，可能几十 KB）。1.17 引入 <strong>Lease 对象</strong>（在 <code>kube-node-lease</code> namespace 中）实现轻量级心跳：</p>
<ul>
<li>每个 Node 对应一个 Lease 对象（同名）。</li>
<li>kubelet 默认每 10 秒（<code>--node-lease-duration-seconds=40</code>）更新 Lease（仅更新 renewTime，几十字节）。</li>
<li>NodeStatus 上报间隔降低（默认 5 分钟，或状态变化时上报）。</li>
<li>Node Controller 检查 Lease 的 renewTime 判断节点是否存活：如果超过 <code>--node-monitor-grace-period</code>（默认 40 秒）没更新，将 Node 标记为 NotReady。</li>
</ul>
<pre><code class="language-bash"># 查看 Lease
kubectl get lease -n kube-node-lease
kubectl describe lease node-1 -n kube-node-lease

# Node Controller 关键参数（kube-controller-manager）
# --node-monitor-grace-period=40s   # Node NotReady 判定时间
# --pod-eviction-timeout=5m0s       # NotReady 后多久驱逐 Pod
# --node-eviction-rate=0.1          # 每秒驱逐节点速率
# --node-startup-grace-period=1m0s  # 节点启动宽限期
</code></pre>
</div>

<div class="card card-r">
<h3>Node NotReady 之后发生什么？</h3>
<pre><code>T=0s: kubelet 停止上报 Lease（节点故障/网络分区/kubelet 挂了）
T=10s: Node Controller 检测到 Lease 未更新
T=40s: Node Controller 将 Node Ready 标记为 False (Unknown/NotReady)
       → kube-proxy 停止向该节点转发 Service 流量
       → Endpoint Controller 从 Endpoints/EndpointSlice 中移除该节点 Pod
       → 但 Pod 暂时还在节点上，API Server 中 Pod 状态不变
T=5m0s (pod-eviction-timeout):
       Node Controller 开始驱逐该节点上的 Pod
       → Pod 被标记为 Terminating
       → API Server 在其他节点上创建替代 Pod（如果被 Deployment/StatefulSet 管理）
       → 但如果节点真的挂了，kubelet 无法执行优雅终止
       → Pod 会一直 Terminating 直到 Pod 被强制删除（或者节点恢复后 kubelet 清理）
</code></pre>
<p>注意：网络分区场景下，被分区的 kubelet 不知道自己被判定 NotReady，仍然在节点上运行 Pod，但这些 Pod 无法被访问（Endpoint 已移除）。分区恢复后，kubelet 会上报最新状态，可能删除已被 API Server 标记删除的 Pod。</p>
</div>

## Node 维护：Cordon 与 Drain

<div class="card card-m">
<h3>Cordon vs Drain</h3>
<table>
<tr><th>操作</th><th>命令</th><th>效果</th><th>是否驱逐 Pod</th></tr>
<tr><td>Cordon</td><td><code>kubectl cordon &lt;node&gt;</code></td><td>给 Node 打 <code>node.kubernetes.io/unschedulable:NoSchedule</code> taint，新 Pod 不会调度上来</td><td>不驱逐，现有 Pod 继续运行</td></tr>
<tr><td>Uncordon</td><td><code>kubectl uncordon &lt;node&gt;</code></td><td>移除 unschedulable taint，恢复可调度</td><td>-</td></tr>
<tr><td>Drain</td><td><code>kubectl drain &lt;node&gt;</code></td><td>cordon + 驱逐所有非 DaemonSet Pod，用于节点维护/升级/下线</td><td>驱逐</td></tr>
</table>
<pre><code class="language-bash"># 安全 drain 节点（生产常用参数）
kubectl drain node-1 \
  --ignore-daemonsets \           # 忽略 DaemonSet Pod（无法驱逐，它们随节点走）
  --delete-emptydir-data \        # 允许删除使用 emptyDir 的 Pod（否则 drain 失败）
  --timeout=300s \                # 驱逐超时
  --grace-period=60               # Pod 优雅终止宽限期

# drain 过程：
# 1. cordon 节点（打 SchedulingDisabled）
# 2. 逐个驱逐 Pod：
#    a. 发送 Eviction 请求到 API Server
#    b. API Server 检查 PDB 是否允许驱逐
#    c. 如果 PDB 阻止，等待并重试
#    d. Pod 收到 SIGTERM，执行 preStop hook
#    e. 等待 grace period
#    f. kubelet 强制 kill 容器
# 3. 等待所有 Pod 被驱逐（或超时）
</code></pre>
</div>

<div class="card card-w">
<h3>Drain 常见问题</h3>
<ul>
<li><strong>DaemonSet 阻止 drain</strong>：必须加 <code>--ignore-daemonsets</code>，因为 DaemonSet Pod 必须在每个节点运行（包括被 drain 的节点）。drain 不会删除 DaemonSet Pod，它们会留在节点上。</li>
<li><strong>emptyDir 阻止 drain</strong>：使用 emptyDir 的 Pod 被驱逐会丢失数据，drain 默认拒绝。加 <code>--delete-emptydir-data</code> 确认允许。</li>
<li><strong>PDB 阻止 drain</strong>：如果 Pod 被 PDB 保护且当前不可驱逐，drain 会等待。这是正常行为，不要强制删除 Pod（<code>--force</code> 会绕过 PDB，可能导致服务中断）。</li>
<li><strong>local storage Pod</strong>：使用本地存储的 Pod（如 StatefulSet 挂 local PV）无法被自动驱逐到其他节点，需要特殊处理。</li>
<li><strong>裸 Pod（无 controller）</strong>：drain 会删除裸 Pod 且不会重建，加 <code>--force</code> 才允许。生产环境避免裸 Pod。</li>
</ul>
</div>

## Node Problem Detector（NPD）

<div class="card card-s">
<h3>NPD 功能</h3>
<p>Node Problem Detector 是 K8s 社区工具，作为 DaemonSet 运行在每个节点上，检测节点侧的各种问题并上报为 Node Condition 或 Event：</p>
<table>
<tr><th>检测项</th><th>问题类型</th></tr>
<tr><td>Kernel deadlock（内核死锁）</td><td>检测 kernel 日志中的 "blocked for more than" 消息</td></tr>
<tr><td>Filesystem corruption（文件系统损坏）</td><td>检测 EXT4/XFS 文件系统错误</td></tr>
<tr><td>kubelet/cni/containerd 问题</td><td>检测关键系统服务异常</td></tr>
<tr><td>Hardware error（硬件错误）</td><td>MCE（Machine Check Exception）日志</td></tr>
<tr><td>OOM Kill</td><td>内核 OOM 事件</td></tr>
<tr><td>Disk bad sector</td><td>磁盘坏道</td></tr>
</table>
<p>NPD 上报的问题可以被 Node Controller 或外部运维系统消费，实现自动隔离故障节点（如自动 cordon）。</p>
</div>

## Taints 与 Tolerations

<div class="card card-m">
<h3>Taint/Toleration 模型</h3>
<p>Taint（污点）打在 Node 上，排斥不能容忍该 taint 的 Pod；Toleration（容忍）加在 Pod 上，允许 Pod 被调度到有对应 taint 的 Node。</p>
<pre><code class="language-yaml"># 给节点打 taint
kubectl taint nodes node-1 dedicated=gpu:NoSchedule

# Pod 加 toleration
tolerations:
- key: "dedicated"
  operator: "Equal"
  value: "gpu"
  effect: "NoSchedule"
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300   # NotReady 后容忍 300 秒，之后被驱逐
</code></pre>
<table>
<tr><th>Effect</th><th>行为</th></tr>
<tr><td>NoSchedule</td><td>新 Pod 不能调度上来，不影响已运行的 Pod</td></tr>
<tr><td>PreferNoSchedule</td><td>尽量不调度（软约束，scheduler 优先选没有 taint 的节点）</td></tr>
<tr><td>NoExecute</td><td>新 Pod 不能调度，且已运行的不容忍 Pod 会被立即驱逐</td></tr>
</table>
</div>

<div class="card card-d">
<h3>常见系统 Taint</h3>
<table>
<tr><th>Taint</th><th>含义</th><th>Effect</th></tr>
<tr><td><code>node.kubernetes.io/unschedulable</code></td><td>节点被 cordon</td><td>NoSchedule</td></tr>
<tr><td><code>node-role.kubernetes.io/control-plane</code></td><td>控制面节点</td><td>NoSchedule（默认，防止业务 Pod 跑到 master）</td></tr>
<tr><td><code>node.kubernetes.io/not-ready</code></td><td>节点 NotReady</td><td>NoExecute（配合 tolerationSeconds 延迟驱逐）</td></tr>
<tr><td><code>node.kubernetes.io/unreachable</code></td><td>节点不可达</td><td>NoExecute</td></tr>
<tr><td><code>node.kubernetes.io/disk-pressure</code></td><td>磁盘压力</td><td>NoSchedule（不驱逐已有 Pod，但不调度新 Pod）</td></tr>
<tr><td><code>node.kubernetes.io/memory-pressure</code></td><td>内存压力</td><td>NoSchedule</td></tr>
<tr><td><code>node.kubernetes.io/pid-pressure</code></td><td>PID 压力</td><td>NoSchedule</td></tr>
<tr><td><code>node.kubernetes.io/network-unavailable</code></td><td>网络不可用</td><td>NoSchedule</td></tr>
<tr><td><code>nvidia.com/gpu</code></td><td>GPU 节点（自定义）</td><td>NoSchedule（防止 CPU Pod 占用）</td></tr>
</table>
</div>

## Node Pressure 与 Eviction

<div class="card card-m">
<h3>kubelet 驱逐策略</h3>
<p>当节点资源紧张时，kubelet 会主动终止 Pod 以回收资源（节点级 OOM 保护）：</p>
<table>
<tr><th>驱逐类型</th><th>行为</th><th>配置</th></tr>
<tr><td>Hard Eviction</td><td>达到阈值立即驱逐</td><td><code>evictionHard: memory.available<"100Mi", nodefs.available<"10%"</code></td></tr>
<tr><td>Soft Eviction</td><td>达到阈值且持续 grace period 后才驱逐</td><td><code>evictionSoft: memory.available<"200Mi"</code> + <code>eviction-soft-grace-period: 1m30s</code></td></tr>
</table>
<p>kubelet 不直接按 QoS 类别做固定排序，而是针对发生压力的资源依次比较：是否超过 request、Pod Priority、使用量相对 request 的程度。对 CPU/内存这类有 request 的资源，结果通常表现为：</p>
<ol>
<li>使用量超过 request 的 BestEffort 或 Burstable Pod 先进入候选，再按 Priority 和超过 request 的相对程度排序。</li>
<li>Guaranteed Pod，以及使用量低于 request 的 Burstable Pod 最后考虑，主要按 Priority 排序；系统进程挤占预留资源时它们仍可能被驱逐。</li>
<li>inode/PID 没有 request，DiskPressure 的统计口径也不同，因此不能把“BestEffort → Burstable → Guaranteed”套到所有节点压力场景。</li>
</ol>
<p>节点压力驱逐与内核 OOM Killer 也不是同一条链路。发生节点 OOM 时，kubelet 设置的 <code>oom_score_adj</code> 会影响内核选择：BestEffort 通常为 1000，Guaranteed 通常为 -997，Burstable 根据 request 占节点内存比例计算。</p>
</div>

## Container 与 Pod 生命周期

<div class="card card-m">
<h3>Pod 内容器启动顺序</h3>
<p>一个 Pod 中容器的启动有明确顺序：</p>
<ol>
<li><strong>Init Containers</strong>：按定义顺序<strong>串行</strong>执行，每个必须成功退出才执行下一个。任何 Init Container 失败，Pod 重启（restartPolicy 决定）。用于初始化配置、等待依赖服务、数据库迁移等。</li>
<li><strong>postStart Hook</strong>：主容器启动后<strong>异步</strong>执行（容器 entrypoint 启动同时触发），执行失败会重启容器。不要用 postStart 做必须在容器接受流量前完成的初始化——它和 entrypoint 是并行的，没有顺序保证。</li>
<li><strong>Main Containers</strong>：在所有 Init Container 成功后<strong>并行</strong>启动。</li>
</ol>
<pre><code class="language-yaml">apiVersion: v1
kind: Pod
spec:
  initContainers:
  - name: init-config
    image: busybox:1.35
    command: ['sh', '-c', 'cp /config/* /etc/app/']
    volumeMounts:
    - name: config
      mountPath: /etc/app
  - name: wait-for-db
    image: busybox:1.35
    command: ['sh', '-c', 'until nc -z db 5432; do sleep 2; done;']
  containers:
  - name: app
    image: myapp:v1
    lifecycle:
      postStart:
        exec:
          command: ["/bin/sh", "-c", "sleep 3 && warmup-cache.sh"]
      preStop:
        exec:
          command: ["/bin/sh", "-c", "sleep 10 && kill -TERM 1"]  # 等待 envoy sidecar 处理完
    ports:
    - containerPort: 8080
</code></pre>
</div>

<div class="card card-m">
<h3>Pod 优雅终止完整过程</h3>
<p>当 Pod 被删除（kubectl delete、drain、滚动更新、驱逐）时，经历以下步骤：</p>
<pre><code>T=0s: API Server 收到删除请求，设置 Pod metadata.deletionTimestamp
       → Pod 被标记为 Terminating
       → Endpoint Controller 开始从 Endpoints 中移除该 Pod（摘流）
       → kube-proxy 更新 iptables/IPVS 规则，停止转发新请求到该 Pod

T=0s+: kubelet 看到 Pod Terminating：
       1. 执行 preStop hook（如果定义）
          - preStop 是同步执行的，必须退出才进入下一步
          - 用于优雅摘流：sleep 几秒让旧请求处理完（等待 iptables 规则传播）、通知注册中心下线、保存 checkpoint
       2. preStop 完成后（或没有 preStop），向容器主进程（PID 1）发送 SIGTERM

T=0s → T=terminationGracePeriodSeconds（默认 30s）:
       - 容器进程收到 SIGTERM，应该开始优雅关闭
         （完成在途请求、关闭连接、flush 数据、释放锁）
       - 如果进程在 grace period 内退出，终止完成
       - Sidecar 容器问题：如果有 istio-proxy/envoy sidecar，
         它可能在主容器退出前先被 kill 导致主容器网络中断。
         解决方案：
         a. preStop 中 sleep 等待 sidecar 完成转发
         b. K8s 1.28+ Sidecar Containers（restartPolicy: Always + restartPolicy 标记为 sidecar）

T=grace period 到期:
       - kubelet 发送 SIGKILL 强制杀死仍在运行的容器
       - 容器被清理，Pod 从 API Server 中删除

注意：如果节点故障（NotReady 超时被驱逐），kubelet 无法执行上述流程，
Pod 会卡在 Terminating 状态，需要等节点恢复或强制删除（--force --grace-period=0）。
</code></pre>
</div>

<div class="card card-d">
<h3>Probes：探针机制</h3>
<table>
<tr><th>探针</th><th>作用</th><th>失败后果</th><th>典型场景</th></tr>
<tr><td>livenessProbe</td><td>检测容器是否活着（死锁、僵死）</td><td>重启容器（kubelet 杀容器并重启）</td><td>检测死锁、无限循环、应用崩溃但进程还在的情况</td></tr>
<tr><td>readinessProbe</td><td>检测容器是否准备好接收流量</td><td>从 Endpoints/Service 摘除，不重启</td><td>应用启动加载大模型时不接收流量、依赖数据库不可用时摘流</td></tr>
<tr><td>startupProbe</td><td>检测应用是否启动完成（K8s 1.16+）</td><td>重启容器；在 startupProbe 成功前关闭 liveness 检查</td><td>慢启动应用（AI 模型加载需要几分钟），避免 liveness 在启动期间误杀</td></tr>
</table>
<pre><code class="language-yaml">livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 30   # 启动后等多久开始探测
  periodSeconds: 10         # 探测间隔
  timeoutSeconds: 5         # 探测超时
  failureThreshold: 3       # 连续失败多少次标记为失败
  successThreshold: 1       # 成功一次即认为正常
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  periodSeconds: 5
  failureThreshold: 2
startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  periodSeconds: 10
  failureThreshold: 30      # 最多等 30*10=300 秒启动
</code></pre>
<p>关键实践：</p>
<ul>
<li>livenessProbe 失败会重启容器，不要把依赖检查（如数据库连通）放进 liveness，否则依赖故障会导致容器不断重启。</li>
<li>readinessProbe 失败只摘流不重启，适合依赖检查。</li>
<li>慢启动应用（如 vLLM 加载大模型、Java 应用）必须配 startupProbe，否则 livenessProbe 会在启动期间超时导致反复重启。</li>
<li>readiness 一旦失败会被摘除 Service，恢复后重新加入；liveness 失败直接重启容器。</li>
</ul>
</div>

## Pod Sandbox（Pause 容器）

<div class="card card-s">
<h3>Pause 容器的作用</h3>
<p>每个 Pod 中第一个启动的是 pause 容器（gcr.io/google_containers/pause-amd64），它的作用：</p>
<ol>
<li><strong>持有 Linux Namespace</strong>：pause 容器创建并持有 Pod 的 network namespace、UTS namespace（hostname）、IPC namespace。业务容器加入这些共享 namespace。</li>
<li><strong>Pod IP 稳定性</strong>：Pod IP 分配在 pause 容器上，业务容器重启不需要重新分配 IP 和重建网络栈。</li>
<li><strong>共享网络</strong>：Pod 内所有容器共享同一个 network namespace（同一个 IP、同一个 localhost），通过 localhost 互相通信，端口不冲突。</li>
<li><strong>僵尸进程回收</strong>：pause 容器运行一个极简进程（编译为静态二进制，只调用 pause() 系统调用），作为 PID namespace 的 init 进程，回收业务容器的孤儿进程。</li>
</ol>
<p>注意：PID namespace 默认不共享（每个容器有独立 PID namespace），除非设置 <code>shareProcessNamespace: true</code>。</p>
</div>

## 高频问答

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Node NotReady 了会怎样？</div>
<div class="qa-a">
<p>Node NotReady 后，K8s 按时间线执行以下动作：</p>
<div class="qa-section"><div class="qa-section-title">立即（秒级）</div><p>1. Node Controller 将 Node Ready condition 标记为 False/Unknown。2. Endpoint Controller/EndpointSlice Controller 将该节点上所有 Pod IP 从 Service Endpoints 中移除，kube-proxy 更新 iptables/IPVS 规则，新请求不再路由到这些 Pod。3. 节点上的 Pod 如果是 Deployment/StatefulSet 管理的，此时控制面尚未创建替代 Pod，因为还在等待 pod-eviction-timeout。</p></div>
<div class="qa-section"><div class="qa-section-title">5 分钟（pod-eviction-timeout 默认）后</div><p>Node Controller 开始驱逐该节点上的 Pod：将 Pod 标记为 Terminating（设置 deletionTimestamp），在其他健康节点上创建新的替代 Pod。但由于目标节点上的 kubelet 无法通信，它无法执行 Pod 的优雅终止流程（preStop、SIGTERM）。</p></div>
<div class="qa-section"><div class="qa-section-title">对 StatefulSet/有状态应用</div><p>StatefulSet 因为有 Pod 名称和 PV 绑定，驱逐会更谨慎——只有旧 Pod 被确认删除后才会在其他节点创建同名 Pod。RWO 类型的 PV 需要 Attach/Detach 过程。</p></div>
<div class="qa-section"><div class="qa-section-title">节点恢复</div><p>如果节点恢复（kubelet 重新连接），kubelet 会上报最新 Pod 状态，删除 Terminating 状态但其实仍在运行的 Pod（或重新同步状态）。网络分区恢复后需要注意"双写"问题：被驱逐的旧 Pod 和新创建的 Pod 如果都在运行（旧 Pod 在分区恢复前没被终止），可能导致数据不一致。</p></div>
<div class="qa-summary">面试口径：NotReady → 立即摘流（从 Endpoints 移除）→ 等待 pod-eviction-timeout（默认 5 分钟）→ 驱逐 Pod 并在其他节点重建；节点上 Pod 无法优雅终止，有状态应用需要额外处理。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Pod 被删除的完整过程？</div>
<div class="qa-a">
<p>Pod 优雅终止是一个多组件协作的过程，时间线如下：</p>
<div class="qa-section"><div class="qa-section-title">1. API Server 收到删除请求</div><p>设置 Pod 的 metadata.deletionTimestamp 和 metadata.deletionGracePeriodSeconds（默认 30 秒），将 Pod 标记为 Terminating 状态。此时 Pod 仍在节点上运行。</p></div>
<div class="qa-section"><div class="qa-section-title">2. Endpoint Controller 摘流</div><p>几乎立即，Endpoint Controller 观察到 Pod Terminating，将该 Pod IP 从所有 Endpoints/EndpointSlices 中移除。kube-proxy 更新 iptables/IPVS/eBPF 规则，停止将新流量转发给这个 Pod。注意：iptables/IPVS 规则更新有传播延迟（秒级），所以 preStop 中 sleep 几秒很重要。</p></div>
<div class="qa-section"><div class="qa-section-title">3. kubelet 执行 preStop hook</div><p>kubelet 看到 Pod 进入 Terminating，先执行 preStop hook（如果配置了）。preStop 是阻塞的，通常用来：sleep 等待流量规则生效、调用服务注册接口注销、保存 checkpoint、通知 sidecar 准备关闭。preStop 超时或执行完毕后继续下一步。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 发送 SIGTERM</div><p>preStop 完成后，kubelet 向容器 PID 1 发送 SIGTERM 信号。应用收到 SIGTERM 应该停止接受新连接、完成在途请求、关闭数据库连接、flush 日志等。注意：SIGTERM 默认不会传递给 shell 脚本启动的子进程（需要 exec 形式启动或 trap 处理）。</p></div>
<div class="qa-section"><div class="qa-section-title">5. Grace Period</div><p>等待 terminationGracePeriodSeconds（默认 30 秒，可在 Pod spec 和 delete 请求中指定）。如果容器在此期间主动退出（进程退出码 0），终止流程提前完成。</p></div>
<div class="qa-section"><div class="qa-section-title">6. SIGKILL 强制清理</div><p>grace period 到期后，kubelet 发送 SIGKILL 强制杀死仍在运行的容器（包括 sidecar）。容器被清理，Pod sandbox (pause) 也被删除，Volume 被卸载。</p></div>
<div class="qa-section"><div class="qa-section-title">7. Finalizer</div><p>如果 Pod 有 finalizer（如 storage-protection、namespace cleanup），kubelet 完成容器终止后 API Server 还需等待 finalizer 被移除，Pod 才会从 etcd 中彻底删除。</p></div>
<div class="qa-summary">面试口径：删除请求 → deletionTimestamp → Endpoint 摘流 → preStop → SIGTERM → 等待 grace period → SIGKILL → 清理 sandbox/volume；关键点是 preStop sleep 处理流量延迟，应用要正确处理 SIGTERM。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: readinessProbe 和 livenessProbe 区别？</div>
<div class="qa-a">
<p>两者目标完全不同，面试中常被混淆：</p>
<div class="qa-section"><div class="qa-section-title">livenessProbe：存活性探测</div><p>目的是检测容器是否"卡死"——进程还在但无法正常工作（如死锁、无限循环、内部状态损坏）。失败后果：kubelet 杀掉容器并根据 restartPolicy 重启。配置建议：检查应用内部健康（如 /healthz 返回进程是否正常），<strong>不要</strong>检查外部依赖（数据库、Redis、下游服务），否则依赖故障会导致容器不断重启形成 crash loop。</p></div>
<div class="qa-section"><div class="qa-section-title">readinessProbe：就绪性探测</div><p>目的是检测容器是否"准备好接收流量"。失败后果：不重启容器，只是将 Pod IP 从 Service Endpoints 中移除（kube-proxy 更新规则），不分配新流量到该 Pod，但已有连接不受影响（TCP 连接不断）。配置建议：可以检查外部依赖、预热状态（大模型是否加载完、缓存是否 warm）、初始化是否完成。</p></div>
<div class="qa-section"><div class="qa-section-title">startupProbe：启动探针</div><p>K8s 1.16+ 引入，专门解决慢启动应用的问题。在 startupProbe 成功之前，liveness 和 readiness 探测都被禁用（不会执行）。startupProbe 失败会重启容器；成功后切换到正常的 liveness/readiness 检查。适合加载大模型（需要几分钟）、Java 应用（JVM warmup）等场景。</p></div>
<div class="qa-section"><div class="qa-section-title">常见错误</div><p>1. livenessProbe 检查依赖服务 → 依赖挂了导致所有 Pod crash loop，雪崩。2. 慢启动应用没配 startupProbe → liveness 在启动期间超时误杀。3. 只有 liveness 没有 readiness → 启动中的 Pod 就接收流量，导致请求失败。4. readiness 检查过于严格（偶发抖动就失败）→ 频繁摘流加流。</p></div>
<div class="qa-summary">面试口径：liveness 失败→重启（管死活），readiness 失败→摘流不重启（管流量），startup 保护慢启动期间 liveness 不杀容器。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: cordon 和 drain 区别？</div>
<div class="qa-a">
<p>cordon 和 drain 都是节点维护操作，但力度完全不同：</p>
<div class="qa-section"><div class="qa-section-title">cordon = 标记不可调度（软隔离）</div><p><code>kubectl cordon &lt;node&gt;</code> 给节点打上 <code>node.kubernetes.io/unschedulable:NoSchedule</code> taint。效果：新 Pod 不会被调度到这个节点，但节点上已运行的所有 Pod 完全不受影响，继续正常运行和提供服务。相当于把节点"标记"为维护中，但还没开始维护。uncordon 移除 taint 即可恢复。</p></div>
<div class="qa-section"><div class="qa-section-title">drain = cordon + 驱逐所有 Pod（硬隔离）</div><p><code>kubectl drain &lt;node&gt;</code> 首先执行 cordon（防止新 Pod 调度），然后逐个驱逐节点上的 Pod：通过 Eviction API 请求删除每个 Pod（受 PDB 保护），Pod 经历 preStop→SIGTERM→grace period 优雅终止，被 Deployment/StatefulSet 管理的 Pod 会在其他节点重建。drain 后节点上基本没有业务 Pod（除了 DaemonSet），可以安全关机/升级/更换硬件。</p></div>
<div class="qa-section"><div class="qa-section-title">使用场景</div><p>1. 先 cordon 观察节点问题（不想让新 Pod 上来但不影响现有业务）。2. 节点维护/升级/下线：drain → 维护 → uncordon。3. 节点故障：如果节点 NotReady 且需要人工修复，可以先 drain 把流量引走再处理。</p></div>
<div class="qa-summary">面试口径：cordon = 只挡新 Pod（打 NoSchedule taint），现有 Pod 不动；drain = cordon + 驱逐所有 Pod（节点清空，可以安全维护）。</div>
</div>
</div>

<div class="card card-m">
<h3>AI Infra 视角下的 K8s 高频问题</h3>
<p>AI Infra 面试不会只问 Kubernetes 基础，还会把 K8s 和 GPU、训练任务、推理服务、多租户资源治理结合起来。下面这些内容需要和前面的调度、资源模型、网络、存储一起理解。</p>
<table>
<tr><th>方向</th><th>核心问题</th><th>为什么高频</th></tr>
<tr><td>GPU Device Plugin</td><td>K8s 如何识别和分配 GPU</td><td>原生 K8s 不知道 GPU 细节，需要 device plugin 上报扩展资源</td></tr>
<tr><td>GPU 共享</td><td>MIG、MPS、time-slicing 的差异</td><td>推理和训练资源利用率优化的基础</td></tr>
<tr><td>Topology</td><td>CPU、NUMA、GPU、NIC 拓扑如何影响性能</td><td>大模型训练通信和数据加载对拓扑敏感</td></tr>
<tr><td>Gang Scheduling</td><td>分布式训练为什么要整体调度</td><td>单个 worker 先启动没有意义，还会占资源</td></tr>
<tr><td>Kueue / Volcano</td><td>队列、配额、公平性、PodGroup</td><td>原生 scheduler 更偏逐 Pod 调度，批任务需要更强队列语义</td></tr>
<tr><td>多租户治理</td><td>资源配额、优先级、抢占、借用和回收</td><td>平台要在利用率、公平性、稳定性之间平衡</td></tr>
</table>
</div>

<div class="card card-s">
<h3>GPU Device Plugin</h3>
<p>Device Plugin 是 kubelet 的插件机制，用于把 GPU 这种非标准资源接入 Kubernetes。NVIDIA GPU 通常通过 NVIDIA device plugin 上报为 <code>nvidia.com/gpu</code> 扩展资源。</p>
<ol>
<li>NVIDIA device plugin 以 DaemonSet 形式运行在 GPU 节点上。</li>
<li>插件发现本机 GPU 设备，并通过 gRPC 向 kubelet 注册资源名，例如 <code>nvidia.com/gpu</code>。</li>
<li>kubelet 把 GPU 数量写入 Node 的 allocatable/capacity。</li>
<li>用户在 Pod requests/limits 中声明 <code>nvidia.com/gpu: 1</code>。</li>
<li>scheduler 根据节点 allocatable 和已分配 requests 选择节点。</li>
<li>Pod 落到节点后，kubelet 调用 device plugin Allocate，拿到设备路径、环境变量、mount 信息。</li>
<li>容器运行时把对应 GPU 注入容器。</li>
</ol>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 nvidia.com/gpu 通常只能整数分配？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">Extended Resource 语义</div><p>Kubernetes 扩展资源按离散资源计数，调度器只做 requests 级别的整数扣减。</p></div>
<div class="qa-section"><div class="qa-section-title">设备隔离语义</div><p>一张物理 GPU 作为一个设备分配给容器时，默认是整卡语义；调度器并不知道卡内显存、SM、带宽如何切分。</p></div>
<div class="qa-section"><div class="qa-section-title">共享方案</div><p>如果要细粒度共享，需要 MIG、MPS、time-slicing 或厂商/平台自定义方案把资源抽象成新的可调度单元。</p></div>
</div>
</div>
</div>

<div class="card card-w">
<h3>MIG、MPS、time-slicing 对比</h3>
<table>
<tr><th>方案</th><th>隔离粒度</th><th>适合场景</th><th>优点</th><th>不足</th></tr>
<tr><td>MIG</td><td>硬件级切分 GPU 实例</td><td>A100/H100 等支持 MIG 的推理、多租户隔离</td><td>隔离更强，资源边界清晰，可作为离散设备上报</td><td>切分规格固定，重配置成本高，不适合所有训练场景</td></tr>
<tr><td>MPS</td><td>多个进程共享同一 GPU 上下文</td><td>小模型推理、提高并发利用率</td><td>减少上下文切换，提高小任务吞吐</td><td>隔离弱，显存和错误隔离需要额外治理</td></tr>
<tr><td>time-slicing</td><td>时间片共享 GPU</td><td>低优先级任务、开发测试、小推理任务</td><td>接入简单，提高卡利用率</td><td>性能抖动明显，不是强隔离，显存仍可能互相影响</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试中如何比较 MIG、MPS、time-slicing？</div>
<div class="qa-a">
<div class="qa-grid"><div class="qa-mini"><strong>MIG</strong>硬件隔离更强，适合多租户推理和明确规格切分。</div><div class="qa-mini"><strong>MPS</strong>偏运行时共享，提高小 kernel 或小推理任务并发。</div><div class="qa-mini"><strong>time-slicing</strong>偏调度共享，简单但抖动更大。</div><div class="qa-mini"><strong>选择原则</strong>强隔离选 MIG，吞吐共享看 MPS，开发测试可用 time-slicing。</div></div>
</div>
</div>
</div>

<div class="card card-m">
<h3>Topology Manager 与拓扑感知调度</h3>
<p>AI 训练对拓扑敏感：GPU 与 GPU 之间是否有 NVLink，GPU 与 NIC 是否同 NUMA，CPU 与 GPU 是否跨 socket，都会影响数据加载和通信效率。</p>
<table>
<tr><th>机制</th><th>工作位置</th><th>解决什么</th><th>局限</th></tr>
<tr><td>Topology Manager</td><td>kubelet 节点侧</td><td>协调 CPU Manager、Device Manager、Memory Manager 的 NUMA 对齐</td><td>发生在节点内资源分配阶段，不负责跨节点选择</td></tr>
<tr><td>CPU Manager</td><td>kubelet 节点侧</td><td>为 Guaranteed Pod 分配独占 CPU core</td><td>主要解决 CPU 绑定，不理解 GPU 通信拓扑</td></tr>
<tr><td>Device Manager</td><td>kubelet 节点侧</td><td>管理 device plugin 上报设备并调用 Allocate</td><td>默认调度器只看到资源数量，不知道具体 GPU 拓扑</td></tr>
<tr><td>自定义调度插件</td><td>scheduler 控制面</td><td>跨节点选择拓扑更优的节点</td><td>需要维护拓扑元数据和调度器缓存一致性</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Topology Manager 和自定义调度插件分别解决什么？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">Topology Manager</div><p>节点内做资源对齐，例如 CPU、内存、设备尽量在同一个 NUMA node，避免 kubelet 分配阶段产生差拓扑。</p></div>
<div class="qa-section"><div class="qa-section-title">自定义调度插件</div><p>调度阶段选择哪个节点更好，例如优先选择 NVLink 完整、GPU/NIC 拓扑更适合训练任务的节点。</p></div>
<div class="qa-summary">一句话：调度插件选节点，Topology Manager 在节点内分配资源。</div>
</div>
</div>
</div>

<div class="card card-s">
<h3>Gang Scheduling 与分布式训练</h3>
<p>分布式训练通常需要一组 Pod 同时运行。例如 8 个 worker 中只有 2 个启动，训练无法有效开始，却已经占用了 GPU。Gang Scheduling 的目标是“要么一起运行，要么都不占资源”。</p>
<table>
<tr><th>概念</th><th>含义</th><th>为什么重要</th></tr>
<tr><td>PodGroup</td><td>一组需要整体调度的 Pod</td><td>表达分布式任务的整体性</td></tr>
<tr><td>minAvailable</td><td>最小可运行 Pod 数</td><td>不足则不放行，避免部分 worker 空占资源</td></tr>
<tr><td>Queue</td><td>任务队列</td><td>支持租户、公平性和资源配额管理</td></tr>
<tr><td>Preemption / Reclaim</td><td>抢占或回收资源</td><td>高优先级训练任务或配额回收需要</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 原生 kube-scheduler 能不能做 Gang Scheduling？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">理论上</div><p>可以通过 Permit、Reserve 等插件实现部分整体准入逻辑。</p></div>
<div class="qa-section"><div class="qa-section-title">生产上</div><p>Gang Scheduling 还需要 PodGroup、队列、公平性、配额、资源回收、任务生命周期等能力，因此通常使用 Volcano、Kueue 或平台自研调度系统。</p></div>
<div class="qa-summary">面试回答：原生框架能扩展，但完整批调度语义通常交给 Volcano/Kueue。</div>
</div>
</div>
</div>

<div class="card card-m">
<h3>Kueue 与 Volcano</h3>
<table>
<tr><th>系统</th><th>定位</th><th>核心能力</th><th>适用场景</th></tr>
<tr><td>Kueue</td><td>Kubernetes 原生批任务队列管理</td><td>ClusterQueue、LocalQueue、ResourceFlavor、admission、quota borrowing</td><td>批任务准入控制、配额、公平共享，与 Job、RayJob、MPIJob 等集成</td></tr>
<tr><td>Volcano</td><td>批计算调度系统</td><td>PodGroup、Queue、Gang、Fair Share、Preemption、多种调度插件</td><td>AI、大数据、HPC 等批任务调度</td></tr>
<tr><td>原生 scheduler</td><td>通用 Pod 调度器</td><td>Filter、Score、Bind、Preemption、插件框架</td><td>在线服务、通用 workload、基础调度</td></tr>
</table>
<p>面试时不要简单说“Volcano 更强”。更准确的表述是：原生 scheduler 是逐 Pod 通用调度器，Kueue/Volcano 提供批任务层面的队列、准入和整体调度语义。</p>
</div>

<div class="card card-w">
<h3>分布式训练部署模式</h3>
<table>
<tr><th>模式</th><th>K8s 对象</th><th>关键点</th><th>风险</th></tr>
<tr><td>StatefulSet + Headless Service</td><td>StatefulSet、Headless Service</td><td>稳定 DNS，Pod ordinal 可推导 rank</td><td>弹性和失败恢复需要额外逻辑</td></tr>
<tr><td>Job + 自定义启动脚本</td><td>Job、ConfigMap、Service</td><td>适合一次性训练，脚本生成 master addr、rank、world size</td><td>原生 Job 不提供强 Gang Scheduling</td></tr>
<tr><td>Kubeflow Training Operator</td><td>PyTorchJob、MPIJob、TFJob</td><td>领域化 CRD，封装训练角色</td><td>需要理解 operator 和底层 Pod/Service 的映射</td></tr>
<tr><td>Ray on K8s</td><td>RayCluster、RayJob</td><td>适合 Ray 分布式训练和推理</td><td>资源调度有 K8s 和 Ray 双层调度</td></tr>
</table>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Headless Service 为什么适合分布式训练？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">直连需求</div><p>NCCL、Parameter Server、MPI 等训练通信需要 worker 之间直接连接，而不是通过 Service 负载均衡随机转发。</p></div>
<div class="qa-section"><div class="qa-section-title">稳定发现</div><p>Headless Service 配合 StatefulSet 会返回每个 Pod 的稳定 DNS，worker 可以解析其他 worker 地址。</p></div>
<div class="qa-summary">一句话：Headless Service 用于成员发现，不用于负载均衡。</div>
</div>
</div>
</div>

<div class="card card-d">
<h3>多租户 GPU 资源治理</h3>
<p>AI 平台要同时考虑资源利用率、公平性、隔离性和任务优先级。单纯 ResourceQuota 只能限制上限，不足以表达队列、公平共享、借用、抢占和回收。</p>
<table>
<tr><th>机制</th><th>解决什么</th><th>局限/注意</th></tr>
<tr><td>Namespace ResourceQuota</td><td>限制租户最大资源占用</td><td>静态，不擅长表达资源借用和队列公平性</td></tr>
<tr><td>PriorityClass + Preemption</td><td>高优先级任务抢占低优先级任务</td><td>会造成被抢占任务中断，训练场景要结合 checkpoint</td></tr>
<tr><td>Queue</td><td>按团队或业务线排队</td><td>需要调度系统支持公平性和准入控制</td></tr>
<tr><td>Quota borrowing</td><td>空闲资源可被其他队列临时借用</td><td>需要资源回收策略，避免被借用方回来后无资源</td></tr>
<tr><td>Preemption/Reclaim</td><td>回收被借用资源或保障高优任务</td><td>要平衡效率和稳定性</td></tr>
<tr><td>Checkpoint</td><td>降低抢占损失</td><td>训练框架和平台需要支持保存/恢复</td></tr>
</table>
</div>

<div class="card card-s">
<h3>大规模集群稳定性</h3>
<p>大规模 AI 集群中，瓶颈不只在 GPU。API Server、etcd、scheduler、controller、kubelet、日志和监控都会成为稳定性风险。</p>
<table>
<tr><th>组件</th><th>风险</th><th>优化方向</th></tr>
<tr><td>etcd</td><td>写入延迟、数据库膨胀、watch 压力</td><td>SSD、compaction、defrag、event 分离、控制对象 churn</td></tr>
<tr><td>API Server</td><td>QPS 高、LIST/WATCH 压力、Webhook 延迟</td><td>watch cache、APF、限流、减少全量 list、优化 webhook</td></tr>
<tr><td>scheduler</td><td>调度吞吐不足、Filter/Score 插件耗时</td><td>减少候选节点、优化插件、缓存预计算、profile 拆分</td></tr>
<tr><td>controller</td><td>reconcile 风暴、队列积压</td><td>限速队列、指数退避、减少无意义更新</td></tr>
<tr><td>kubelet</td><td>节点上 Pod 过多、镜像/日志/磁盘压力</td><td>控制节点密度、镜像 GC、日志轮转、资源预留</td></tr>
<tr><td>监控日志</td><td>高基数指标和日志风暴</td><td>控制 label cardinality、采样、分级采集</td></tr>
</table>
</div>

<div class="card card-d">
<h3>官方与扩展参考</h3>
<div class="resource-grid">
<a class="resource-card" href="https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/"><div class="resource-type">official</div><div class="resource-title">Device Plugins</div><div class="resource-desc">GPU 等硬件资源接入 Kubernetes 的官方机制。</div></a>
<a class="resource-card" href="https://kubernetes.io/docs/tasks/administer-cluster/topology-manager/"><div class="resource-type">official</div><div class="resource-title">Topology Manager</div><div class="resource-desc">节点侧 CPU、内存、设备 NUMA 对齐策略。</div></a>
<a class="resource-card" href="https://github.com/NVIDIA/k8s-device-plugin"><div class="resource-type">github</div><div class="resource-title">NVIDIA k8s-device-plugin</div><div class="resource-desc">NVIDIA GPU device plugin 官方实现。</div></a>
<a class="resource-card" href="https://kueue.sigs.k8s.io/"><div class="resource-type">project</div><div class="resource-title">Kueue</div><div class="resource-desc">Kubernetes 原生批任务队列、配额和准入控制。</div></a>
<a class="resource-card" href="https://volcano.sh/"><div class="resource-type">project</div><div class="resource-title">Volcano</div><div class="resource-desc">批计算、AI、HPC 场景的调度系统。</div></a>
<a class="resource-card" href="https://www.kubeflow.org/docs/components/training/"><div class="resource-type">project</div><div class="resource-title">Kubeflow Training Operator</div><div class="resource-desc">PyTorchJob、MPIJob、TFJob 等训练任务 CRD。</div></a>
</div>
</div>

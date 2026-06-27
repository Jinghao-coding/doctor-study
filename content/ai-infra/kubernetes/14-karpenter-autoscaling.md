## 一句话结论

K8s 弹性伸缩分为节点层（Cluster Autoscaler 扩节点组、Karpenter 直接按需配实例）和 Pod 层（HPA 水平扩副本、VPA 垂直调资源、KEDA 事件驱动）；AI/GPU 场景下 Karpenter 凭借 Pod 级装箱、快速供给和 consolidation 相比 CA 更适合异构 GPU 和突发推理负载，PDB 保护自愿中断下的分布式训练/推理服务可用性。
## Cluster Autoscaler（CA）

<div class="card card-m">
<h3>CA 工作原理</h3>
<p>Cluster Autoscaler 是 K8s 社区标准节点自动扩缩容组件，工作在<strong>节点组（Node Group/ASG）</strong>级别：</p>
<ol>
<li><strong>Scale-up 触发：</strong>每 10 秒扫描一次，检查是否有 Pending Pod（因资源不足无法调度）。对每个 Pending Pod，CA 模拟调度：假设增加节点组中的一个节点，是否能放得下这个 Pod？如果能，且该节点组没有正在 scale-up，则将 ASG 扩容 +1 节点。</li>
<li><strong>Scale-down 判断：</strong>每 10 秒扫描节点，判断节点是否"低利用率"（CPU/内存 request 利用率 &lt; scale-down-utilization-threshold，默认 0.5）且其上 Pod 可以被调度到其他节点。节点满足条件后进入冷却期（默认 10 分钟不缩），冷却期后仍低利用率则驱逐 Pod 并删除节点。</li>
<li><strong>不可驱逐 Pod：</strong>Kube-system Pod（非 DaemonSet/PodPriority）、PDB 阻止的 Pod、有 local storage 的 Pod、没有 controller 的 Pod 默认阻止节点缩容。</li>
</ol>
<pre><code class="language-text">CA Scale-up 决策路径：
Pending Pod 存在?
  → 模拟调度: 现有节点能放吗? → 能则不扩
  → 不能: 增加 ASG 的一个节点能放吗?
     → 有多个 ASG 可选: 选 expansion policy (least-waste/most-pods/price)
     → 触发 ASG scale-up (+1)
  → 等待新节点 join 集群，kubelet 注册，调度器调度 Pending Pod
</code></pre>
</div>

<div class="card card-w">
<h3>CA 的局限性</h3>
<table>
<tr><th>局限</th><th>说明</th></tr>
<tr><td>慢</td><td>从 Pending Pod 到节点可用通常 2-5 分钟（云厂商实例启动 + kubelet 注册 + 镜像拉取），对突发负载响应慢</td></tr>
<tr><td>节点组粒度</td><td>只能在预定义的 ASG 内扩缩，无法为 Pod 选择最合适的实例类型</td></tr>
<tr><td>装箱不优</td><td>不知道 Pod 具体需要什么，只是模拟"多一个节点够不够"，可能导致资源浪费</td></tr>
<tr><td>多实例类型</td><td>需要手动创建多个节点组覆盖不同实例类型，管理复杂</td></tr>
<tr><td>缩容保守</td><td>低利用率判断只看 request 不看实际使用率，且冷却期长；不会主动合并 Pod 到更少节点</td></tr>
<tr><td>不感知价格</td><td>Spot/抢占式实例的成本优化需要额外工具（如 Karpenter 或 CA priority expander）</td></tr>
</table>
</div>

## Karpenter

<div class="card card-m">
<h3>Karpenter 设计理念</h3>
<p>Karpenter 是 AWS 开源（现在 CNCF 沙箱）的节点自动伸缩组件，设计目标是<strong>直接按需供给最合适的计算资源</strong>，跳过 ASG 抽象，直接调用云厂商 API 创建 EC2 实例（或其他云资源）：</p>
<table>
<tr><th>特性</th><th>说明</th></tr>
<tr><td>Pod 级装箱</td><td>直接观察 Pending Pod 的 resource request（CPU/内存/GPU/arch/zone/label），选择最优实例类型组合</td></tr>
<tr><td>快速供给</td><td>不经过 ASG，直接调用云 API 创建实例，&lt;1 分钟可用（配合 EKS 优化 AMI）</td></tr>
<tr><td>异构实例</td><td>自动从数百种实例类型中选择满足 Pod 需求的最便宜/最合适的组合</td></tr>
<tr><td>Consolidation（整合）</td><td>持续扫描集群，主动将 Pod 重新调度到更少/更便宜的节点上，删除空节点</td></tr>
<tr><td>Drift 检测</td><td>当 NodePool/EC2NodeClass 配置变化或 AMI 更新时，自动替换旧节点</td></tr>
<tr><td>多节点合并</td><td>可以同时替换多个节点，将 Pod 整合到更少节点上（multi-node consolidation）</td></tr>
<tr><td>Spot/OD 混部</td><td>自动混部 Spot 和 On-Demand 实例，优先使用便宜的 Spot</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Karpenter 核心概念</h3>
<pre><code class="language-yaml"># NodePool（原 Provisioner）：定义节点供给约束
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-pool
spec:
  template:
    spec:
      requirements:
        - key: "karpenter.sh/capacity-type"
          operator: In
          values: ["on-demand", "spot"]
        - key: "nvidia.com/gpu.product"
          operator: In
          values: ["A10G", "A100", "L4"]       # GPU 类型约束
        - key: "topology.kubernetes.io/zone"
          operator: In
          values: ["us-east-1a", "us-east-1b"] # 可用区
        - key: karpenter.sh/instance-category
          operator: In
          values: ["g"]                        # GPU 实例族
      taints:
        - key: "nvidia.com/gpu"
          effect: NoSchedule
      startupTaints:
        - key: "karpenter.sh/registering"
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenUnderutilized     # 或 WhenEmpty
    consolidateAfter: 1m                       # 低利用率持续多久后整合
    budgets:
    - nodes: 10%                               # 每轮最多同时中断 10% 节点
  limits:
    cpu: 1000                                  # 整个 NodePool 的资源上限
    nvidia.com/gpu: 64
---
# EC2NodeClass：定义云厂商实例配置
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: AL2
  amiSelectorTerms:
  - id: ami-xxx          # GPU 驱动预装的 AMI
  role: "KarpenterNodeRole-xxx"
  securityGroupSelectorTerms:
  - tags: {karpenter.sh/discovery: my-cluster}
  subnetSelectorTerms:
  - tags: {karpenter.sh/discovery: my-cluster}
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs: {volumeSize: 100Gi, volumeType: gp3}
  userData: |
    #!/bin/bash
    # 安装 NVIDIA device plugin / 配置 GPU 运行时
</code></pre>
<table>
<tr><th>概念</th><th>对应 CA</th><th>说明</th></tr>
<tr><td>NodePool</td><td>Node Group / ASG</td><td>节点供给约束（实例类型、zone、taint、labels）</td></tr>
<tr><td>NodeClass（EC2NodeClass）</td><td>Launch Template</td><td>云厂商层面的配置（AMI、security group、subnet、role）</td></tr>
<tr><td>Consolidation</td><td>Scale-down（弱）</td><td>主动整合：删除低利用率节点，重新调度 Pod</td></tr>
<tr><td>Disruption Budget</td><td>-</td><td>控制同时中断多少节点，配合 PDB 使用</td></tr>
</table>
</div>

<div class="card card-d">
<h3>Consolidation 机制详解</h3>
<p>Karpenter 的 consolidation 不是简单的"空节点就删"，而是主动做 Pod 重调度决策：</p>
<table>
<tr><th>Consolidation Policy</th><th>行为</th></tr>
<tr><td>WhenEmpty</td><td>只有节点上没有非 DaemonSet Pod 时才删除（类似 CA 缩容）</td></tr>
<tr><td>WhenUnderutilized</td><td>持续评估节点利用率，如果能将节点上所有 Pod 调度到其他现有节点（或更少/更便宜的新节点），则驱逐 Pod 并删除原节点</td></tr>
<tr><td>Never</td><td>不做 consolidation，只做空节点清理</td></tr>
</table>
<p>决策流程：</p>
<ol>
<li>找出所有可中断节点（没有 do-not-disrupt annotation、PDB 允许、不在关键时间窗口）。</li>
<li>对每个节点（或多个节点组合），检查其上 Pod 是否能被重新放置到其他节点或更便宜的实例。</li>
<li>选择"最大成本节省"的动作执行（cordon → 驱逐 → 终止节点）。</li>
<li>受 disruption budget 限制每轮最多中断 N 个节点。</li>
</ol>
<p>Pod 可以通过 <code>karpenter.sh/do-not-disrupt: "true"</code> annotation 阻止被驱逐（重要 workload 如正在训练的 Job、长连接推理服务）。</p>
</div>

<div class="card card-r">
<h3>CA vs Karpenter 深度对比</h3>
<table>
<tr><th>维度</th><th>Cluster Autoscaler</th><th>Karpenter</th></tr>
<tr><td>抽象层级</td><td>通过 ASG/Node Group 间接操作</td><td>直接调用 Cloud API 创建实例</td></tr>
<tr><td>供给速度</td><td>2-5 分钟</td><td>&lt;1 分钟（绕过 ASG，直接 provision）</td></tr>
<tr><td>实例选择</td><td>ASG 内的固定实例类型</td><td>按 Pod 需求从所有实例类型中选择最优</td></tr>
<tr><td>装箱粒度</td><td>节点组级：多一个节点够不够？</td><td>Pod 级：精确计算每个 Pod 需要什么资源</td></tr>
<tr><td>缩容/整合</td><td>空节点 + 低利用率 → 删（保守）</td><td>主动 consolidation：可以驱逐 Pod 合并节点</td></tr>
<tr><td>异构调度</td><td>需多个 node group，配置复杂</td><td>原生支持多 arch/多 GPU 类型混部</td></tr>
<tr><td>成本优化</td><td>需配合 priority expander</td><td>内置 Spot/OD 混部 + 最便宜实例选择</td></tr>
<tr><td>Drift 修复</td><td>不支持</td><td>自动检测 AMI/SG 配置变化，替换节点</td></tr>
<tr><td>多云支持</td><td>所有主流云厂商</td><td>AWS 最成熟，Azure/GCP 快速跟进</td></tr>
<tr><td>适用场景</td><td>固定节点组、严格节点管理</td><td>弹性需求大、异构资源、AI/Serverless 场景</td></tr>
</table>
</div>

## GPU 场景的弹性伸缩

<div class="card card-m">
<h3>GPU 伸缩特殊考虑</h3>
<p>GPU 节点弹性伸缩相比 CPU 场景有额外复杂性：</p>
<ol>
<li><strong>GPU 实例类型特殊</strong>：GPU 实例（AWS p5/p4d/g5/g6、GCP a3/a2、NC 系列）价格高、供给紧张，scale-up 失败率高（InsufficientInstanceCapacity 常见）。需要配置备选实例类型和多 AZ 分散。</li>
<li><strong>拓扑感知调度</strong>：多 GPU 训练（如 8x A100）要求同一实例内有 NVLink/NVSwitch 连接；多机分布式训练要求同一 placement group 内低延迟网络。Karpenter 通过 <code>topology.kubernetes.io/zone</code>、<code>karpenter.sh/instance-size</code>、weight 机制处理。</li>
<li><strong>NVIDIA Device Plugin</strong><code>nvidia.com/gpu</code> resource 必须在 Node Ready 后才能被调度，kubelet 启动后需要 device plugin 分配 GPU 资源并上报。这导致节点 Ready 到真正可调度有延迟。</li>
<li><strong>GPU 节点 taints/tolerations</strong>：GPU 节点应该打 taint（如 <code>nvidia.com/gpu:NoSchedule</code>），需要 GPU 的 Pod 加对应的 toleration，避免 CPU Pod 占了昂贵的 GPU 节点。</li>
<li><strong>启动开销</strong>：GPU 节点需要预装 NVIDIA 驱动、CUDA、容器运行时（nvidia-container-runtime）、device plugin daemonset，启动后还需要拉取大型 AI 镜像（数 GB 到数十 GB），实际可用时间比 CPU 节点长。</li>
<li><strong>Consolidation 风险</strong>：GPU 训练/推理任务对中断敏感，必须用 <code>do-not-disrupt</code>、PDB 阻止 consolidation 驱逐正在运行的 GPU Pod，避免训练中断。</li>
</ol>
<pre><code class="language-yaml"># GPU Pod 示例（正确配置）
apiVersion: v1
kind: Pod
metadata:
  name: llm-inference
  annotations:
    karpenter.sh/do-not-disrupt: "true"  # 防止 consolidation 驱逐
spec:
  tolerations:
  - key: "nvidia.com/gpu"
    operator: "Exists"
    effect: "NoSchedule"
  nodeSelector:
    nvidia.com/gpu.product: "A10G"
  containers:
  - name: vllm
    image: vllm/vllm-openai:latest
    resources:
      limits:
        nvidia.com/gpu: 1
        cpu: "8"
        memory: "32Gi"
</code></pre>
</div>

<div class="card card-s">
<h3>Karpenter vs CA 对 AI 工作负载的影响</h3>
<table>
<tr><th>场景</th><th>CA</th><th>Karpenter</th></tr>
<tr><td>突发推理扩容</td><td>慢（2-5 分钟），排队请求堆积</td><td>快（&lt;1 分钟），快速响应流量</td></tr>
<tr><td>多 GPU 类型混部</td><td>需要配置多个 node group，手动管理</td><td>NodePool 内自动选择最合适 GPU 类型</td></tr>
<tr><td>训练任务排队</td><td>按 node group 扩容，可能选到不合适实例</td><td>按 Pod 的 GPU/CPU/内存/网络需求精确供给</td></tr>
<tr><td>成本优化</td><td>需要手动选 Spot 节点组</td><td>自动优先 Spot，consolidation 释放闲置 GPU 节点</td></tr>
<tr><td>AMI/驱动更新</td><td>需要滚动 ASG，操作复杂</td><td>drift detection 自动替换旧节点</td></tr>
<tr><td>固定节点池</td><td>适合稳定、长期运行的训练集群</td><td>适合弹性强、负载波动大的场景</td></tr>
</table>
</div>

## HPA / VPA / PDB

<div class="card card-m">
<h3>HPA（Horizontal Pod Autoscaler）</h3>
<p>HPA 自动调整 Deployment/StatefulSet 的副本数，基于 metrics 驱动：</p>
<ul>
<li><strong>CPU/Memory 利用率</strong>：通过 metrics-server 获取 Pod resource metrics，计算 <code>targetAverageUtilization</code>。</li>
<li><strong>自定义指标</strong>：通过 Prometheus Adapter 暴露自定义指标（如 QPS、Kafka lag、GPU 利用率）。</li>
<li><strong>外部指标</strong>：对接外部系统指标（如 SQS queue length、ALB request count）。</li>
</ul>
<pre><code class="language-yaml">apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-inference
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-inference
  minReplicas: 2
  maxReplicas: 20
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0      # 扩容不等待
      policies:
      - type: Percent
        value: 100                       # 每次最多翻倍
        periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 300   # 缩容稳定窗口 5 分钟
      policies:
      - type: Pods
        value: 1                         # 每次最多缩 1 个
        periodSeconds: 60
  metrics:
  - type: Resource
    resource:
      name: nvidia.com/gpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric: {name: vllm_num_requests_waiting}
      target: {type: AverageValue, averageValue: "10"}
</code></pre>
<p>HPA 公式：<code>desiredReplicas = ceil[currentReplicas * (currentMetric / targetMetric)]</code></p>
</div>

<div class="card card-s">
<h3>VPA（Vertical Pod Autoscaler）</h3>
<p>VPA 自动调整 Pod 的 CPU/内存 request/limit：</p>
<ul>
<li><strong>四种模式</strong>：<code>Off</code>（只推荐不应用）、<code>Initial</code>（只在创建时设置）、<code>Auto</code>（创建时设置 + 运行时更新）、<code>Recreate</code>（需要重启 Pod）。</li>
<li><strong>In-place Pod Resize</strong>：K8s 1.27+（beta in 1.31）支持不重启 Pod 调整 CPU/内存 request/limit，但不是所有 runtime/CRI 都完全支持；GPU 资源目前不支持 in-place resize。</li>
<li><strong>和 HPA 冲突</strong>：VPA 不要和基于 CPU/内存的 HPA 同时启用（会互相打架：HPA 看高 CPU 扩副本，VPA 看高 CPU 加 request，循环放大）。但可以和基于自定义/外部指标的 HPA 配合。</li>
<li><strong>Admission Controller</strong>：VPA 的 webhook 在 Pod 创建时注入推荐的 request/limit。</li>
</ul>
</div>

<div class="card card-d">
<h3>PDB（Pod Disruption Budget）</h3>
<p>PDB 保护自愿中断（voluntary disruption）场景下的应用可用性：</p>
<ul>
<li><strong>自愿中断</strong>：kubectl drain、节点升级、cluster autoscaler 缩容、Karpenter consolidation 等主动驱逐。<strong>不包括</strong>节点故障、OOM kill、硬件故障等非自愿中断。</li>
<li>PDB 限制同一时间内可以被驱逐的 Pod 数量，保证 minAvailable 个 Pod 或最多 maxUnavailable 个 Pod 不可用。</li>
<li>驱逐操作（Eviction API）在 PDB 预算不足时会被 API Server 拒绝（429 Too Many Requests），驱逐方（drain/CA/Karpenter）必须等待并重试。</li>
</ul>
<pre><code class="language-yaml"># 分布式训练 PDB：保证最多 1 个 Pod 不可用
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: training-workers
spec:
  maxUnavailable: 1       # 或 minAvailable: 7
  selector:
    matchLabels:
      job-name: megatron-training
---
# 推理服务 PDB：保证至少 2 个副本可用
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: inference-min-available
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: vllm-inference
</code></pre>
<p><strong>PDB 不能防止节点故障</strong>——节点宕机时 Pod 直接消失，PDB 无法阻止。它只在 API Server 收到 Eviction 请求时检查预算。对训练任务，还需要应用层 checkpoint 和容错；对推理服务，需要多副本 + 反亲和。</p>
</div>

## KEDA：事件驱动伸缩

<div class="card card-s">
<h3>KEDA（Kubernetes Event-Driven Autoscaling）</h3>
<p>KEDA 扩展 HPA，支持基于外部事件源驱动伸缩，特别适合 AI 推理（请求队列长度）、消息处理（Kafka/RabbitMQ 积压）等场景：</p>
<ul>
<li>提供 50+ scaler：Kafka、RabbitMQ、Redis、Prometheus、AWS SQS/SQS、CPU/Memory、自定义。</li>
<li>可以伸缩到 0 副本（HPA 本身 minReplicas ≥1，KEDA 的 ScaledObject 支持 minReplicaCount=0）。</li>
<li>和 HPA 共存，KEDA 管理 HPA 对象，通过 custom metrics 驱动。</li>
</ul>
<pre><code class="language-yaml">apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: kafka-consumer
spec:
  scaleTargetRef:
    name: my-consumer
  minReplicaCount: 0
  maxReplicaCount: 30
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka:9092
      consumerGroup: my-group
      topic: inference-requests
      lagThreshold: "100"   # Kafka lag 超过 100 开始扩容
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: gpu_utilization
      threshold: "80"
      query: avg(nvidia_gpu_utilization{pod=~"my-consumer.*"})
</code></pre>
</div>

## 高频问答

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Karpenter 和 Cluster Autoscaler 怎么选？</div>
<div class="qa-a">
<p>选择依据主要看集群弹性需求和工作负载特征：</p>
<div class="qa-section"><div class="qa-section-title">选 Karpenter 的场景</div><p>1. AI/ML 工作负载：GPU 类型多样（A100/A10/L4 等）、突发扩容需求大（推理流量）、需要快速供给；2. Serverless/弹性场景：Job 类型 workload 多、Pod 生命周期短、需要 scale-to-0 和快速扩容；3. 成本敏感：希望自动选择最便宜实例（Spot/OD 混部）、主动 consolidation 减少浪费；4. 多云/异构：需要支持多架构（x86/ARM）混合部署。</p></div>
<div class="qa-section"><div class="qa-section-title">选 CA 的场景</div><p>1. 严格的节点组管理要求：安全合规要求节点在预定义 ASG 内、需要使用自定义 Launch Template 配置；2. 多云/混合云一致性：在所有云厂商/本地环境保持相同扩缩容体验；3. 稳定长期运行的集群：workload 变化不大、scale-up 延迟可以接受；4. 对 consolidation 敏感：不希望 Pod 被主动驱逐（如严格的 stateful workload）。</p></div>
<div class="qa-section"><div class="qa-section-title">可以一起用吗</div><p>可以。Karpenter 和 CA 可以共存于同一集群，分别管理不同的 node group/NodePool。例如用 CA 管理稳定的系统节点组（kube-system、监控），用 Karpenter 管理弹性 GPU/Spot 节点池。通过 taints/tolerations 和 nodeSelector 让不同 workload 调度到对应的池。</p></div>
<div class="qa-summary">面试口径：快速弹性 + 异构资源 + 成本优化选 Karpenter；稳定可预测 + 严格节点管理 + 多云一致性选 CA；AI/GPU 场景 Karpenter 优势明显。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: HPA 和 VPA 可以同时用吗？</div>
<div class="qa-a">
<p><strong>不建议 HPA（基于 CPU/内存）和 VPA 同时使用</strong>，但具体要看指标类型：</p>
<div class="qa-section"><div class="qa-section-title">冲突场景</div><p>当 HPA 使用 CPU 或内存利用率作为伸缩指标时，和 VPA 会产生冲突循环：CPU 利用率高 → HPA 扩副本 → VPA 观察到单 Pod CPU 使用高，建议增加 request → request 变大导致利用率下降 → HPA 缩副本 → request 又可能被调，循环往复导致抖动。</p></div>
<div class="qa-section"><div class="qa-section-title">可以共存的场景</div><p>HPA 使用自定义指标或外部指标（如 QPS、Kafka lag、GPU 利用率、队列长度）时，可以和 VPA 配合。因为这些指标不受 Pod 资源 request 的直接影响：VPA 调整 CPU/内存 request，HPA 基于业务指标扩缩副本，两者不打架。</p></div>
<div class="qa-section"><div class="qa-section-title">推荐实践</div><p>1. 大多数情况下只选其一：CPU/内存密集型无状态服务用 HPA；资源配置需要优化的服务用 VPA（Off/Auto 模式）。2. 需要同时用时，HPA 用自定义/外部指标，VPA 用 Initial 模式（只在 Pod 创建时设置 request）。3. VPA 的 in-place resize（未来稳定后）可以让 VPA 在不重启的情况下调整资源，减少和 HPA 的冲突。</p></div>
<div class="qa-summary">面试口径：HPA(CPU/内存) 和 VPA 冲突（会打架），不要同时开；HPA(自定义指标) + VPA(Initial/Off) 可以共存。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: PDB 能防止节点故障吗？</div>
<div class="qa-a">
<p><strong>不能。</strong>PDB 只保护<strong>自愿中断（voluntary disruption）</strong>，不能防止非自愿中断。</p>
<div class="qa-section"><div class="qa-section-title">PDB 能保护的场景</div><p>kubectl drain 驱逐 Pod、Cluster Autoscaler 缩容删除节点、Karpenter consolidation/Drift 替换节点、节点升级（kubectl drain + cordon）、手动 kubectl delete pod。这些操作通过 Eviction API 请求驱逐，API Server 检查 PDB 预算，预算不足时返回 429 拒绝驱逐。</p></div>
<div class="qa-section"><div class="qa-section-title">PDB 不能保护的场景</div><p>节点硬件故障/断电、节点网络分区导致 NodeNotReady（超过 pod-eviction-timeout 后 Node Controller 直接删除 Pod）、OOM Killer 杀容器、容器进程 crash、磁盘故障、云厂商实例被意外回收。这些场景下 Pod 直接消失或被 kubelet 标记终止，不经过 Eviction API，PDB 无法拦截。</p></div>
<div class="qa-section"><div class="qa-section-title">真正的高可用策略</div><p>1. PDB + 多副本 + Pod anti-affinity（跨节点/跨 AZ 分布）。2. 应用层容错：分布式训练要做 checkpoint 和自动 resume；推理服务要多副本 + 优雅终止（preStop + readiness 摘流）。3. Node 层面：跨 AZ 部署、节点健康检查、NPD 快速检测问题。4. Pod 层面：proper terminationGracePeriodSeconds、preStop hook 做流量摘除和状态保存。5. 对非自愿中断，需要应用层自己处理（如 leader election、session affinity、checkpoint）。</p></div>
<div class="qa-summary">面试口径：PDB 只防自愿中断（drain/升级/缩容），不防节点故障/宕机；真正高可用需要多副本反亲和 + 应用层容错 + PDB 三者结合。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 节点弹性伸缩有什么特殊考虑？</div>
<div class="qa-a">
<p>GPU 节点伸缩相比 CPU 场景有以下关键差异：</p>
<div class="qa-section"><div class="qa-section-title">1. 实例供给不确定性</div><p>GPU 实例（特别是高端如 p5/p4de/H100）云厂商库存有限，scale-up 可能遇到 InsufficientInstanceCapacity。需要配置多实例类型 fallback（Karpenter 的 requirements 允许多种 GPU 类型）、多 AZ 分散、Spot+OD 混部。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 拓扑感知</div><p>多 GPU 训练要求 NVLink/NVSwitch 拓扑（同一实例内 8 GPU 直连）；多机训练要求低延迟网络（EFA/RDMA）和 placement group。NodePool 需要约束实例大小和网络能力。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 节点启动后就绪延迟</div><p>GPU 节点需要 NVIDIA 驱动、nvidia-container-runtime、device plugin DaemonSet 就绪后才能分配 GPU 资源。kubelet Ready 不等于 GPU 可调度；还要等 nvidia-device-plugin 上报 <code>nvidia.com/gpu</code> 资源。镜像预热（image caching）对大型 AI 镜像（10GB+）至关重要，否则 Pod Pending 会卡在 ContainerCreating。</p></div>
<div class="qa-section"><div class="qa-section-title">4. Taints/Tolerations 隔离</div><p>GPU 节点成本极高（单实例 $20-80+/小时），必须打 NoSchedule taint，GPU Pod 通过 toleration 调度上去，防止 CPU Pod 误占 GPU 节点导致资源浪费。</p></div>
<div class="qa-section"><div class="qa-section-title">5. Consolidation 和中断保护</div><p>GPU 训练任务不能被意外中断（几小时的训练会白费），必须配置 do-not-disrupt annotation、PDB、合理的 disruption budget；推理服务要配 preStop hook 做优雅摘流。Karpenter 的 consolidationPolicy 对 GPU 节点池建议 WhenEmpty 而非 WhenUnderutilized（避免频繁驱逐）。</p></div>
<div class="qa-section"><div class="qa-section-title">6. 资源模型</div><p>GPU 是整数资源（不能分配 0.5 GPU，除非用 MIG/MPS/Time-Slicing），Pod requests/limits 必须声明整数个 nvidia.com/gpu。节点可分配 GPU 数等于实例 GPU 数减去 system 预留。</p></div>
<div class="qa-summary">面试口径：GPU 伸缩要关注实例供给风险、拓扑约束、启动后就绪延迟（驱动+device plugin+镜像）、taint 隔离防 CPU Pod 抢占、consolidation 保护训练任务不中断。</div>
</div>
</div>

## 关联模块

- `02-scheduling-resource-model`：资源模型（requests/limits）是 HPA 和 Karpenter 调度决策的基础。
- `07-ai-infra-gpu-dra`：GPU 共享（MIG/MPS）、DRA 动态资源分配影响 GPU 节点伸缩策略。
- `15-node-lifecycle`：Node 注册、NotReady 处理、drain 流程和 PDB 紧密相关。
- `05-fault-tolerance`：分布式训练容错、checkpoint、PDB 对训练任务保护。

## 一句话结论

GPU 调度场景题不要只背“队列、打分、抢占”这些概念。面试官通常在考三件事：你能不能把业务场景讲具体，能不能把 GPU 从“几张卡”拆成显存、算力、拓扑、成本、租户配额等可调度条件，能不能说明方案落到 Kubernetes 节点标签、资源池、准入层和调度器扩展时到底做哪些动作。

回答时建议按这个顺序展开：**先澄清任务类型和约束 -> 解释资源和任务画像 -> 说调度链路怎么改 -> 说异常和回退 -> 说指标如何证明有效**。这样每个场景都能讲到 8-10 分钟，而不是只报几个名词。

## 常用术语先解释

| 术语 | 白话解释 | 在回答里怎么用 |
|---|---|---|
| 资源规格 / 卡型资源池 | 把同样叫 GPU 的资源按型号、显存、网络、成本、节点池区分开 | H100 80GB、A100 40GB、A10 24GB 是不同资源规格，不能只当成 `nvidia.com/gpu=1` |
| node pool | 一批同质或用途相近的节点池 | 在线推理池、离线训练池、H100 高端池、A10 低成本池 |
| 作业画像 | 调度器对任务需求的结构化描述 | 需要多少显存、是否多机、是否需要 NVLink、预计时长、是否可抢占 |
| Gang / 组调度 | 一组 Pod 必须一起启动，否则训练跑不起来 | 8 卡分布式训练不能先启动 7 个 worker 占着资源空等 |
| Backfill | 在不影响大任务预约启动的前提下，让短任务填资源空洞 | 64 卡任务还差 16 卡时，用 1-2 卡短任务临时填空 |
| 抢占代价 | 抢掉一个任务带来的进度损失和恢复成本 | GPU 训练抢占要看 checkpoint 新鲜度、运行时长、模型加载成本 |
| 拓扑感知 | 调度时考虑 GPU 与 GPU、GPU 与 NIC 的物理连接关系 | TP 更想放同节点 NVSwitch，跨节点会被 RDMA 和交换机瓶颈限制 |

## 场景题总览

| 场景 | 面试官真正想看 | 关键词 |
|---|---|---|
| 异构 GPU 调度 | 你是否能把 GPU 从“数量”升级成卡型 / 显存 / 性能 / 拓扑资源 | 节点标签、资源池、型号匹配、性能归一 |
| 多租户配额 | 你是否理解公平和利用率冲突 | quota、fairshare、cohort、借用、回收 |
| Gang / 组调度 | 你是否知道分布式训练 All-or-Nothing 语义 | PodGroup、minAvailable、准入、死锁 |
| Backfill | 你是否能处理大任务等资源时的小任务填空 | 短作业、预计时长、reservation |
| 抢占 | 你是否知道 GPU 训练抢占代价很高 | priority、checkpoint、victim cost |
| 碎片治理 | 你是否能解释 GPU 利用率低的结构性原因 | bin packing、defrag、reservation |
| 拓扑感知 | 你是否知道同样 GPU 数量性能可能差很多 | NVLink、NVSwitch、RDMA、NUMA、NIC affinity |
| 训练/推理混部 | 你是否能保护在线 SLO | MIG、MPS、time-slicing、priority、isolation |
| 海量小 GPU 作业 | 你是否能考虑调度器吞吐和显存切分 | fractional GPU、best-fit、batch scheduling |
| 弹性训练 | 你是否能把调度和训练框架语义结合 | min/max workers、elastic quota、world size |
| 故障恢复 | 你是否能把调度和稳定性闭环 | DCGM、Xid、drain、reschedule、checkpoint |

## 通用回答骨架

```flow
澄清场景 | 训练/推理/评测/小作业，单 Pod 还是多 Pod，在线还是离线
定义资源 | GPU 型号、显存、CPU、内存、网络、存储、拓扑、故障域
确定硬约束 | 显存够、型号兼容、Gang 满足、SLO 不破、租户 quota 不越界
选择目标 | 吞吐、等待时间、JCT、公平性、SLO、利用率、成本
设计策略 | 队列排序、准入、Filter/Score、Backfill、抢占、弹性
工程落地 | GPU 插件、节点标签、准入控制、调度扩展、资源看板和监控指标
验证效果 | queue time、JCT、GPU util、fragmentation、SLO violation、preemption cost
```

## 1. 异构 GPU 调度

### 典型题目

公司有一个共享训练集群：老节点是 A10 24GB，主力节点是 A100 40GB / 80GB，新采购了一批 H100 80GB。现在用户提交任务只写 `gpu: 4`，结果出现三类问题：

- BERT 微调、图片离线推理这类轻任务占了 H100，成本很高。
- 70B 模型 SFT 被调到 A10，显存根本不够，反复 OOM。
- 需要 8 卡 NVLink 的张量并行任务，被拆到多台普通 A100 节点，训练速度很差。

面试官问：你会怎么改造调度系统？

### 先把题目讲清楚

这里的核心矛盾不是“调度器认不认识 GPU 型号”，而是 `nvidia.com/gpu=1` 这个资源太粗了。对 CPU 任务来说，1 核 CPU 之间差异相对小；但对 AI 任务来说，1 张 A10、1 张 A100、1 张 H100 完全不是同一种资源。它们的显存、算力、精度能力、互联、价格都不同。

所以要把 GPU 从“数量”升级成“资源画像”。可以把资源规格理解成更有语义的卡型标签：比如 `a10-24g`、`a100-40g`、`a100-80g-nvlink`、`h100-80g-nvswitch`。面试里不需要绑定某个具体系统名，直接说平台维护一张“GPU 资源规格表”或“卡型资源池”即可。

### 10 分钟回答展开

1. **资源侧建模**

先在集群侧维护 GPU 资源目录，而不是只看 Kubernetes 的 extended resource。每个节点或节点池记录：

| 字段 | 例子 | 为什么重要 |
|---|---|---|
| 型号 | A10 / A100 / H100 | 决定算力、支持精度和成本 |
| 显存 | 24GB / 40GB / 80GB | 决定模型能不能放下 |
| 互联 | PCIe / NVLink / NVSwitch | 决定 TP、MoE、AllReduce 性能 |
| 网络 | 普通以太网 / IB / RDMA | 决定跨节点训练性能 |
| 成本 | 每小时价格或内部成本权重 | 避免小任务浪费高端卡 |
| 健康状态 | 正常 / Xid 频发 / ECC 风险 | 避免把任务调到坏卡 |

这里最容易混的是“发现卡型”和“改资源名”。可以先拆成三个问题：

| 问题 | 谁负责 | 结果是什么 |
|---|---|---|
| K8S 知道有几张 GPU | NVIDIA device plugin | 节点 `allocatable` 里出现 `nvidia.com/gpu: 8` |
| K8S 知道是什么卡型 | GPU Feature Discovery + Node Feature Discovery | 节点 label 里出现 `nvidia.com/gpu.product`、`nvidia.com/gpu.memory` |
| 是否把资源改名 / 切成共享份额 | device plugin 的 ConfigMap | 例如把 `nvidia.com/gpu` 暴露成 `nvidia.com/gpu.shared`，或者把一张卡切成多个 time-slicing 副本 |

所以，ConfigMap 确实存在，但它主要配置 device plugin “怎么暴露资源”，不是凭空告诉集群“这台机器是 H100”。卡型信息仍然来自节点上的发现组件读取真实硬件，然后写 Node label。平台再根据这些 label 把节点归入 A10、A100、H100 等资源池；健康状态由 DCGM / Xid 监控实时回写，坏卡自动从可调度资源池里摘掉。

管理员视角可以这样讲：

```flow
安装 NVIDIA 驱动和容器运行时 | 节点上的容器能访问 GPU
部署 NVIDIA device plugin | kubelet 看到 nvidia.com/gpu 这种可分配资源
配置 device plugin ConfigMap | 配 MIG、time-slicing、renameByDefault 等资源暴露方式
部署 Node Feature Discovery | 集群具备给 Node 写硬件特征 label 的能力
启用 GPU Feature Discovery | 读取 GPU 型号、显存、架构、MIG 状态并生成 nvidia.com/* label
检查节点标签和资源名 | 看 allocatable 里的 nvidia.com/gpu / nvidia.com/gpu.shared，以及 label 里的 gpu.product / gpu.memory
配置资源池/准入规则 | 调度层用这些标签区分 A10/A100/H100，而不是让用户直接写复杂 label
```

这里的“发现”不是 Kubernetes 自带能力，也不是装完集群就天然知道卡型；它依赖管理员部署和配置这些组件。所谓自动，是指组件启动后会从节点真实硬件读取信息并持续更新 label，而不是管理员手工维护每台机器的卡型表。

典型 ConfigMap 只解决“资源怎么暴露”的问题，例如 time-slicing：

```yaml
version: v1
sharing:
  timeSlicing:
    renameByDefault: true
    failRequestsGreaterThanOne: true
    resources:
    - name: nvidia.com/gpu
      replicas: 4
```

这表示一张物理 GPU 可以被暴露成 4 个 time-slicing 份额；如果 `renameByDefault: true`，资源名会从 `nvidia.com/gpu` 变成类似 `nvidia.com/gpu.shared`。但它并不负责判断这张物理卡是 A10 还是 H100，卡型仍然看节点 label。

2. **任务侧画像**

用户不能只填“几张 GPU”。平台要提供更结构化的提交入口，例如：

| 任务字段 | 示例 | 调度含义 |
|---|---|---|
| 最低显存 | `>=40GB` | 低于这个值直接过滤 |
| 可接受卡型 | `A100-80G, H100-80G` | A10 不进入候选 |
| 首选卡型 | `H100` | 有 H100 优先，没有再降级 |
| 是否需要高速互联 | `need_nvlink=true` | 多卡任务优先同节点 NVLink / NVSwitch |
| 精度要求 | `fp8_required=false` | FP8 必须 H100，BF16 可用 A100 |
| 任务类型 | 训练 / 推理 / 评测 / Notebook | 决定抢占、SLO 和队列策略 |

3. **调度链路**

可以分成准入、过滤、打分三步：

```flow
准入阶段 | 先判断租户 quota 和对应卡型资源池是否允许进入队列
过滤阶段 | 过滤掉显存不够、型号不兼容、拓扑不满足、健康异常的节点
打分阶段 | 在候选节点中按成本、等待时间、碎片程度、拓扑质量综合打分
绑定阶段 | 绑定具体节点或资源池，并记录这次任务用了哪个卡型
反馈阶段 | 采集 OOM、运行时长、GPU 利用率，用于修正任务画像
```

过滤和打分里最容易被追问的是拓扑：`need_nvlink=true` 的多卡任务，过滤阶段要求候选节点（或同一 NVSwitch / superpod 域）能一次放下整个 Gang，打分阶段再对“同节点 > 同 superpod > 跨节点”做梯度加分。这一步必须和组调度联动——先按拓扑选定一组满足 `minAvailable` 的节点再整体绑定，否则会出现 8 卡任务被拆到多台普通节点、训练带宽打不满的情况。

4. **降级策略**

降级不能由调度器偷偷决定，要让用户或平台模板显式表达。例如一个 LoRA 微调任务可以写：

```text
preferred: h100-80g
acceptable: [a100-80g, a100-40g]
forbidden: [a10-24g]
```

如果 H100 紧张，就可以降到 A100；但 70B 推理如果最低显存 80GB，就不能降到 A10。这里体现的是“硬约束”和“偏好”的区别：显存够不够是硬约束，H100 还是 A100 是偏好或成本选择。

5. **指标验证**

落地后不能只说“更智能”。要看：

| 指标 | 说明 |
|---|---|
| 高端卡错配率 | H100 被低需求任务占用的比例是否下降 |
| OOM 重试率 | 因显存不匹配导致的失败是否下降 |
| 各卡型资源池等待时间 | A10/A100/H100 是否出现单个池子严重拥塞 |
| 单位任务成本 | 同类任务平均 GPU 成本是否下降 |
| 性能归一吞吐 | 同任务在不同卡型上的吞吐是否符合预期 |

6. **性能归一与跨型号配额**

异构集群的配额和公平不能只数“卡数”，因为 1 张 H100 ≠ 1 张 A10。常见做法是给每种卡型一个等价系数（compute-equivalent unit），例如以 A100 为基准，H100 记 2.x、A10 记 0.3，配额、计费、fairshare 都按归一后的 GPU 当量计算。要点是：归一系数和 workload 相关（训练、推理、FP8 任务的相对加速比不同），所以系数应按任务类型分档或定期用真实 benchmark 校准，不能写死一个常数。面试时强调一句：“归一是为了让不同型号可比较和可计费，不是物理真值。”

### 面试追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 只用 node label 能不能解决？</div>
<div class="qa-a"><p>label 能表达“节点是什么”，但它不是完整方案。完整方案还需要任务画像、队列配额、准入控制、Filter/Score 策略、降级规则和指标闭环。否则只是把 <code>gpu=true</code> 换成 <code>gpu=h100</code>，仍然解决不了谁能用、什么时候降级、如何避免浪费高端卡的问题。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 卡型资源池分得越细越好吗？</div>
<div class="qa-a"><p>不是。分太粗会错配，分太细会导致资源池碎片化。一般按“影响调度决策的维度”分：型号、显存、互联、成本和故障域是常见维度；驱动小版本、非关键标签不应该随便变成独立资源池。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 存量任务还是只写 gpu: 4，怎么平滑迁移？</div>
<div class="qa-a"><p>不要求用户一次性改全部提交脚本。用准入 webhook 给没有画像的任务注入默认卡型偏好（按队列 / 命名空间 / 镜像推断），同时根据历史运行数据（显存峰值、是否多机、是否用到 NVLink）回填任务画像；再用看板告诉用户“你这个任务其实只要 A100，却占了 H100”，用成本和排队数据推动用户主动填写。先保证不破坏存量，再逐步收紧默认值。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 管理员到底怎么让集群知道这是 A100 还是 H100？</div>
<div class="qa-a"><p>先装 GPU 驱动、容器运行时和 NVIDIA device plugin，让 kubelet 能看到 <code>nvidia.com/gpu</code>；如果要 GPU 共享或改资源名，再配 device plugin 的 ConfigMap，例如 <code>renameByDefault</code> 把共享 GPU 暴露成 <code>nvidia.com/gpu.shared</code>。但卡型识别靠 Node Feature Discovery + GPU Feature Discovery：它们读取本机 GPU 信息并写入 Node label，例如 <code>nvidia.com/gpu.product</code>、<code>nvidia.com/gpu.memory</code>。最后调度层用这些 label 建 A100/H100 资源池。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 把 H100 只留给大任务，结果 H100 经常空着怎么办？</div>
<div class="qa-a"><p>这是“高端卡保护”和“利用率”的经典冲突。纯预留会浪费，纯抢占又伤大任务。常见折中是：H100 池允许低优先级、可抢占、带 checkpoint 的短任务借用，一旦大任务来了用抢占快速回收；同时给借用任务设较短的最大运行时间或要求支持弹性缩容，让回收代价可控。判断标准是 H100 空闲率和大任务排队时间这两个指标同时不恶化。</p></div>
</div>

<div class="qa-summary">面试金句：异构 GPU 调度的核心不是“识别型号”，而是把型号、显存、性能和成本变成可调度语义。</div>

## 2. 多租户配额与弹性借用

### 典型题目

一个 GPU 集群给搜索、广告、推荐、算法平台四个团队共用。每个团队买了固定配额，比如推荐 200 卡、广告 100 卡、搜索 80 卡。问题是：

- 白天推荐团队任务少，100 多张卡空着。
- 广告团队临时做大促实验，排队 300 个任务。
- 如果完全按硬配额，整体利用率低。
- 如果谁有任务谁先用，推荐团队晚上提交任务时又拿不回自己的卡。

面试官问：你怎么设计多租户 GPU 配额系统？

### 先把公平说具体

公平不是“大家平均分”。工业里更常见的是三层语义：

| 语义 | 白话解释 | 例子 |
|---|---|---|
| guarantee / deserved quota | 这个团队应该被保障的资源 | 推荐团队至少应有 200 卡 |
| borrowing / over-quota | 别人不用时，我可以临时多用 | 广告临时借推荐空闲的 80 卡 |
| reclaim / preemption | 原主人要用时，借用者要归还 | 推荐晚上提交任务，广告 over-quota 任务被回收 |

### 10 分钟回答展开

1. **队列模型**

每个团队对应一个队列，队列上配置保障配额、最大可借额度、权重和优先级。不要只在 Namespace 上做限制，因为 Namespace 更偏权限边界，Queue 才是调度资源治理边界。

```flow
Team Namespace | 控制谁能提交、权限和隔离
Team Queue | 控制能用多少 GPU、能借多少、如何回收
Resource Pool | 管一组真实 GPU 资源池，比如 A100 池或 H100 池
Borrowing Group | 多个队列之间允许互相借用的一组共享池
```

2. **准入策略**

任务进入队列时先判断它属于哪个团队、请求哪个卡型资源池、当前队列是否在保障额度内。如果在保障额度内，优先准入；如果超过保障额度，要看共享池是否有空闲，以及该队列是否允许借用。

3. **公平排序**

当多个队列都想借资源时，不按简单 FIFO，而按 fairshare 或 quota debt 排序。可以这样解释：

| 场景 | 排序倾向 |
|---|---|
| 队列长期低于保障配额 | 应优先补齐 |
| 队列已经大量 over-quota | 借用优先级降低 |
| 高优先级线上修复任务 | 可以临时插队，但要有审计 |
| 低优先级实验任务 | 可以使用空闲资源，但可抢占 |

4. **回收策略**

回收是这题的重点。不能说“直接抢占”。GPU 训练抢占很贵，所以要分层：

| 回收方式 | 适用情况 |
|---|---|
| 等待自然结束 | 原队列不急，借用任务很快结束 |
| 禁止新借用 | 先停止 over-quota 队列继续扩大占用 |
| 优雅抢占 | 通知任务 checkpoint，给宽限期 |
| 强制抢占 | 高优任务、SLO 或配额严重违约时使用 |

5. **观测和解释**

多租户系统最怕“团队觉得不公平”。所以要能解释：某个任务为什么排队、为什么被抢占、当前队列在保障内还是借用中、预计多久能获得资源。

### 面试追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Hard quota 和 Elastic quota 怎么选？</div>
<div class="qa-a"><p>Hard quota 简单可解释，但利用率低；Elastic quota 利用率高，但必须配套回收和审计。GPU 集群通常用 elastic quota：保障配额保证底线，空闲借用提升利用率，回收策略保证原队列回来时拿得回资源。</p></div>
</div>

<div class="qa-summary">面试金句：多租户 GPU 调度不是“平均分卡”，而是“保障配额 + 空闲借用 + 可解释回收”。</div>

## 3. Gang / 组调度

### 典型题目

用户提交一个 PyTorch DDP 训练任务，需要 8 个 worker，每个 worker 1 张 GPU。默认 Kubernetes 一个 Pod 一个 Pod 调度，结果先起来 7 个 Pod，最后 1 个因为没有 GPU 一直 Pending。已经起来的 7 个 Pod 也不能训练，因为 rendezvous 等不到完整 world size，GPU 被白白占住。

面试官问：如何解决这种“部分启动导致资源浪费”的问题？

### 先解释为什么普通调度不够

普通 Kubernetes 调度器以 Pod 为单位，只关心“这个 Pod 能不能放到某个节点”。但分布式训练的语义是 Job 级别的：8 个 worker 要么一起达到最小可运行规模，要么都不要占资源。这就是 Gang Scheduling，也叫组调度或 All-or-Nothing 调度。

### 10 分钟回答展开

1. **把 Pod 组建模成一个整体**

平台需要引入 `PodGroup`、`Workload` 或 Job 级抽象，记录：

| 字段 | 示例 | 含义 |
|---|---|---|
| minAvailable | 8 | 至少 8 个 worker 到齐才启动 |
| totalReplicas | 8 | 目标 worker 数 |
| resource per replica | 1 GPU + CPU + memory | 单 worker 资源需求 |
| queue | team-a-training | 所属队列 |
| priority | high / normal / low | 抢占和排序依据 |

2. **准入阶段先判断整组是否可满足**

不要让 Pod 先进入默认调度再卡住，而是在准入阶段判断：当前队列和资源池是否能同时满足 8 张 GPU、CPU、内存和拓扑要求。满足才放行，不满足就留在队列里。

3. **预留和超时**

如果资源是逐步释放的，可以为这个 gang 做 reservation。但 reservation 不能无限占着资源，所以需要超时和回滚：

```flow
发现资源即将凑齐 | 为 PodGroup 预留候选节点
超过等待时间仍不满足 | 释放 reservation
有更高优任务进入 | 重新评估 reservation 是否需要被抢占
资源满足 | 整组 Pod 同时进入绑定流程
```

4. **和 Backfill 结合**

Gang 会带来队头阻塞。比如 64 卡任务暂时凑不齐，不能让空闲 48 卡一直空着。可以允许短任务 backfill，但前提是不破坏大 gang 的预约启动时间。

5. **异常处理**

启动后如果某个 worker 失败，要看训练框架是否支持弹性：

| 情况 | 处理 |
|---|---|
| 不支持弹性 world size | 整个 Job 重启或从 checkpoint 恢复 |
| 支持 min/max worker | 缩到 min 继续跑，后续再扩容 |
| 单节点故障 | 标记坏节点，重新调度缺失 worker |
| rendezvous 超时 | 清理半启动 Pod，避免资源泄漏 |

### 常见追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Gang Scheduling 的缺点是什么？</div>
<div class="qa-a"><p>主要是 head-of-line blocking 和资源空等。大任务需要整组资源，如果一直凑不齐，会堵住队列。解决方式是分队列、reservation timeout、backfill、elastic gang、aging，以及把 min/max worker 语义暴露给训练框架。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Gang 和普通优先级抢占怎么结合？</div>
<div class="qa-a"><p>抢占必须 gang-aware。不能只抢一个 Pod，而要判断抢占后是否能让整个 incoming gang 成功启动；victim 也最好按 Job/Gang 粒度选择，避免把别人的分布式训练打残。</p></div>
</div>

## 4. Backfill：大任务等资源，小任务如何填空

### 典型题目

训练平台队首是一个 64 卡预训练任务，需要 8 台 8 卡 A100 节点同时空出来。现在集群只有 48 张 A100 空闲，预计 30 分钟后会有两台机器释放。队列后面有很多 1-2 卡的评测、LoRA 微调、小模型推理任务，很多 10 分钟内能跑完。

如果严格 FIFO，48 张 GPU 要空等 30 分钟；如果小任务随便插队，64 卡任务可能永远凑不齐。你怎么设计？

### 先解释 Backfill 的边界

Backfill 不是“让小任务插队”。它的定义是：**在不延迟队首大任务预计启动时间的前提下，用短任务填补暂时用不上的资源空洞**。所以关键是有 reservation 和预计运行时长。

### 10 分钟回答展开

1. **为队首大任务做预约**

调度器先估计 64 卡任务最早什么时候能启动。估计依据包括：当前空闲资源、运行中任务预计结束时间、队列配额、可抢占任务、节点拓扑。

2. **选择可回填任务**

小任务能不能 backfill，不只看卡数，还要看它是否会破坏预约：

| 条件 | 说明 |
|---|---|
| 预计运行时间短 | 必须能在大任务预约时间前结束 |
| 可抢占或可重试 | 估计错误时可以快速让出资源 |
| 资源形状匹配碎片 | 适合填 1-2 卡、小显存、零散 CPU/内存 |
| 不占关键拓扑块 | 不拆掉即将给 64 卡任务用的完整节点组 |

3. **运行时长如何估计**

工业里用户填的时长经常不准，可以用多路信息：

| 来源 | 用法 |
|---|---|
| 用户声明 | 作为初始上限，但不完全相信 |
| 历史同类任务 | 按镜像、入口命令、数据集、模型大小预测 |
| 在线进度 | 任务跑起来后修正剩余时间 |
| 超时策略 | 超过声明时长后降低优先级或标为不可 backfill |

4. **防止大任务饿死**

要给队首任务 aging 和 reservation。也可以设置 backfill 窗口，比如距离预约启动只剩 5 分钟时，不再放新的小任务进去。

5. **指标验证**

看 GPU idle time 是否下降、大任务 queue time 是否没有显著增加、reservation miss 是否可控、backfill 任务的超时率是否过高。

<div class="qa-summary">面试金句：Backfill 不是让小任务随便插队，而是在不破坏大任务 reservation 的前提下填碎片。</div>

## 5. 抢占与代价感知

### 典型题目

线上推荐模型出现质量问题，需要立即启动一个 16 卡紧急修复训练任务。但 A100 池已经满了，里面有低优先级预训练、学生实验、评测任务，还有一些正在借用别人配额的任务。你会不会抢占？如果抢，占谁？

### 先解释立场

GPU 抢占可以做，但不能像 CPU 短任务那样粗暴。训练任务被 kill 以后可能损失几个小时进度，还要重新拉镜像、加载数据、初始化 NCCL、恢复 checkpoint。所以抢占策略应该是“代价感知的资源回收”，不是简单按优先级杀 Pod。

### 10 分钟回答展开

victim 选择要考虑：

| 维度 | 含义 |
|---|---|
| 优先级 | 低优任务优先被抢 |
| 是否借用资源 | over-quota / borrowed 任务优先被回收 |
| checkpoint 新鲜度 | checkpoint 越新，进度损失越小 |
| 已运行时间 | 刚运行不久的任务沉没成本低 |
| 释放资源匹配度 | 释放的 GPU 型号、数量、拓扑是否正好满足 incoming |
| 重启成本 | 镜像、数据、NCCL 初始化、模型加载成本 |
| 是否 gang | 避免只杀分布式任务的一部分 |

```flow
找候选 victim | 低优先级、借用资源、可抢占
估算收益 | 释放 GPU 数量、型号、拓扑、CPU/内存
估算代价 | checkpoint age、运行时长、重启成本、SLO 影响
选择集合 | 最小代价满足 incoming gang
优雅终止 | 通知 checkpoint，超时强杀
```

落地时可以分三层：

| 层次 | 策略 |
|---|---|
| 候选过滤 | 不抢线上推理、不抢保障配额内高优训练，优先找 over-quota 和低优任务 |
| 代价打分 | checkpoint 越新、已运行越短、释放资源越匹配，越适合作 victim |
| 执行协议 | 先发 preempt notice，给任务保存 checkpoint 的宽限期，超时后强杀 |

### 面试追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不能只按 PriorityClass 抢？</div>
<div class="qa-a"><p>PriorityClass 只能表达重要性，不能表达抢占代价。两个低优任务里，一个刚启动 5 分钟且有 checkpoint，另一个跑了 20 小时还没有保存，如果只看优先级会做出很差的 victim 选择。</p></div>
</div>

<div class="qa-summary">面试金句：GPU 抢占不是 kill 低优 Pod，而是用最小进度损失换足够可用资源。</div>

## 6. GPU 碎片治理

### 典型题目

监控显示 A100 集群还有 120 张 GPU 空闲，但一个 8 卡单机训练任务一直排队。排查发现每台 8 卡机器都被零散占了 6-7 张卡，只剩 1-2 张。总量够，但凑不出一台完整 8 卡机器。你怎么治理这种碎片？

### 先解释碎片不是一种

GPU 碎片不是只有“卡数碎片”。AI 任务常见的是多维碎片：GPU 数量、显存、CPU、内存、NVLink 拓扑、队列配额任何一个维度不连续，都会让大任务跑不起来。

### 10 分钟回答展开

| 碎片类型 | 例子 | 治理方式 |
|---|---|---|
| 卡数碎片 | 每节点剩 1 卡，8 卡任务跑不了 | bin packing、reservation、defrag |
| 显存碎片 | 同卡剩余显存零散，小显存作业能跑，大显存作业不能跑 | best-fit、fractional GPU 分桶 |
| 多维碎片 | GPU 有剩余但 CPU/内存不够 | 多维打分、CPU/GPU 配比感知 |
| 拓扑碎片 | 卡数够但 NVLink 域被拆散 | 保留完整 clique / node group |
| 队列碎片 | 某队列有资源但无任务，另队列排队 | elastic quota / borrowing |

回答时先说碎片的类型，再说策略组合：放置阶段用 bin packing 保留大块；队列阶段用 backfill 填小洞；资源池阶段按卡型 / topology 分池；长期用 defrag 或迁移低优任务整理资源。

更具体地说，可以分成四个动作：

1. **调度时尽量紧凑放置**：小任务优先 best-fit 到已经被使用的节点，保留完整空节点给大任务。
2. **按拓扑保留大块资源**：8 卡 NVSwitch 节点不要随便拆给零散任务；可以维护 full-node pool。
3. **用 Backfill 填短洞**：短任务可以填碎片，但不能破坏大任务 reservation。
4. **低峰期整理资源**：对可抢占、checkpoint 新鲜的低优任务做迁移或重启，整理出连续节点。

### 面试追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: bin packing 和 spread 该选哪个？</div>
<div class="qa-a"><p>离线训练更常用 bin packing，因为要保留完整节点和拓扑块；在线推理可能需要 spread 来降低单点故障和热点风险。不能脱离任务类型说固定答案。</p></div>
</div>

## 7. 拓扑感知调度

### 典型题目

一个 8 卡张量并行任务，放在单台 H100 NVSwitch 机器上吞吐很高；但如果调度到 4 台机器、每台 2 卡，训练速度掉了一大截。用户说“我明明也拿到了 8 张 GPU”，你怎么解释？调度器怎么避免这种放置？

### 先解释性能差在哪里

GPU 训练不是只消耗计算，还大量消耗通信。张量并行 TP 的通信频率很高，几乎每层都有 AllReduce / AllGather。如果 8 张卡在同一 NVSwitch 域，通信走节点内高速互联；如果跨多机，就要走 NIC、RDMA、交换机，延迟和带宽都差很多。

### 10 分钟回答展开

| 并行策略 | 通信特征 | 放置偏好 |
|---|---|---|
| TP | 每层高频 AllReduce/AllGather | 同节点 NVLink/NVSwitch |
| PP | 相邻 stage 传 activation | 相邻 stage 尽量近 |
| DP | 每步梯度 AllReduce | 可跨节点，但需要 RDMA |
| EP/MoE | All-to-All | 避免跨拥塞域 |

落地方式：

- 短期：node label + scheduler plugin + GPU/NIC/NUMA 拓扑缓存。
- 中期：device plugin 上报拓扑信息，调度器自定义 Score。
- 长期：DRA / ResourceSlice 表达设备级属性和拓扑。

更具体的调度链路可以这样说：

```flow
任务声明并行策略 | TP/PP/DP/EP，不同策略通信图不同
构建设备拓扑图 | GPU-GPU、GPU-NIC、NUMA、节点、机架
Filter | 过滤掉不满足最低拓扑要求的候选
Score | 给同 NVSwitch、同节点、同机架、跨机架不同代价
Bind | 同时绑定 GPU 和 rank 映射，避免 rank 随机落位
Observe | 采集 NCCL 带宽、step time、重传、IB 拥塞验证效果
```

### 面试追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: DP 任务也必须同节点吗？</div>
<div class="qa-a"><p>不一定。DP 主要每个 step 做梯度同步，通信频率低于 TP，可以跨节点，只要 RDMA 和网络收敛比足够。TP 更强依赖节点内 NVLink/NVSwitch，PP 关注相邻 stage 的链路，MoE/EP 关注 All-to-All 和拥塞域。</p></div>
</div>

<div class="qa-summary">面试金句：拓扑感知调度优化的是 rank 通信图到硬件拓扑图的映射代价。</div>

## 8. 训练和推理混部

### 典型题目

线上推理服务白天高峰需要稳定 P99，夜间低峰 GPU 利用率只有 25%。离线训练团队希望复用这些 GPU 跑低优先级训练和评测。但一旦混部，推理 P99 抖动、显存被挤占、模型加载变慢。你怎么设计训练和推理混部？

### 先定原则

在线推理的 SLO 是硬约束，离线训练是可让步任务。混部的目标不是“所有任务都尽量塞满”，而是在不破坏 P99 / TTFT / TPOT 的前提下吃掉低峰资源。

### 10 分钟回答展开

| 隔离方式 | 隔离强度 | 适用场景 |
|---|---|---|
| 物理节点隔离 | 最强 | 核心在线推理，严格 SLO |
| MIG | 强 | A100/H100 上推理 + 小任务混部 |
| MPS | 中 | 可接受一定干扰的多进程共享 |
| Time slicing | 弱 | 离线推理、实验任务 |
| 只按优先级抢占 | 弱 | 可重试低优训练任务 |

回答要点：

1. 推理 SLO 是硬约束，训练是可让步任务。
2. 先用节点池或 MIG 保护强 SLO 推理。
3. 对可混部场景，用限额、优先级、监控和自动驱逐保护推理。
4. 观测 P99、TPOT、GPU memory、SM/HBM、context switch 和训练吞吐。

可以把方案拆成三档：

| 档位 | 场景 | 方案 |
|---|---|---|
| 核心在线服务 | 搜索、广告、支付风控等强 SLO | 物理隔离或独占 MIG，不和训练混 |
| 普通在线推理 | P99 有要求但低峰明显 | 低峰允许可抢占离线任务进入，指标异常自动驱逐 |
| 离线推理/评测 | SLO 弱，吞吐优先 | MPS / time slicing / fractional GPU 提高利用率 |

混部还需要运行时控制：训练任务必须带低优先级、可抢占、显存上限；推理服务指标异常时，调度器或控制器触发驱逐；被驱逐训练任务从 checkpoint 或任务队列重试。

### 面试追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MIG、MPS、time slicing 有什么区别？</div>
<div class="qa-a"><p>MIG 是硬件级切分，隔离强，适合保护推理；MPS 是多个进程共享 GPU 执行上下文，利用率高但隔离弱；time slicing 是时间片轮转，适合低优实验或离线任务，不适合强 SLO 推理。</p></div>
</div>

## 9. 海量小 GPU 作业调度

### 典型题目

平台每天有几千万个 C++ / Python 小作业，单个作业只用 2-6GB 显存，运行几十秒到几分钟。它们如果每个独占一张 24GB 或 80GB GPU，利用率非常低；但如果同卡多进程，又容易 OOM、CPU/内存不够、调度器吞吐扛不住。

这个场景已经在“海量小显存作业”子页单独展开，核心是：**显存主导的在线多维装箱 + 高吞吐批量调度**。

### 10 分钟回答展开

```flow
资源画像 | actual gpu_mem/cpu/mem/duration
GPU 卡型分池 | 型号和显存容量隔离
候选索引 | remaining memory buckets + machine residual CPU/mem
Best-fit | 减少显存碎片，保留大块资源
Batch scheduling | 支撑几千万作业规模
反馈预测 | 修正用户申报，降低 OOM 和过度预留
```

展开时要补充三点：

| 问题 | 具体回答 |
|---|---|
| 为什么不能一作业一 GPU | 小作业只用几 GB 显存，独占会造成显存和 SM 浪费 |
| 为什么不能简单超卖 | 用户申报不准，同卡 OOM 会互相影响，还会挤占 CPU/内存 |
| 调度器怎么扛吞吐 | 候选节点索引、批量调度、增量缓存、按剩余显存 bucket 做 best-fit |

## 10. 弹性训练调度

### 典型题目

一个推荐模型训练任务最好用 8 个 worker，但 4 个 worker 也能先跑，只是速度慢一点。用户希望资源紧张时先用 4 卡启动，夜间资源多了扩到 8 卡；如果某个节点故障，也希望先缩到 6 卡继续，而不是整个任务失败。

面试官问：调度器如何支持弹性训练？

### 先说明弹性不是调度器单独能做

弹性训练需要三方配合：调度器负责资源变化，训练框架负责 world size 变化后的 rendezvous 和数据切分，任务代码负责 batch size、学习率、checkpoint 等语义一致性。只说“调度器扩缩容 Pod”是不完整的。

### 10 分钟回答展开

| 问题 | 方案 |
|---|---|
| 如何表达弹性 | `min/target/max` workers，或 elastic workload |
| 如何准入 | 至少满足 min 才启动，target/max 作为扩容目标 |
| 如何扩容 | 有空闲资源时增加 worker，训练框架重建 rendezvous |
| 如何缩容 | 节点故障或抢占时减少 worker，继续训练 |
| 一致性风险 | world size 变化影响 batch size、学习率、BN、数据切分 |
| 调度风险 | 扩容不能无限抢占别人，要受 quota/fairshare 约束 |

具体链路：

```flow
提交任务 | 声明 min=4 target=8 max=8
准入启动 | 资源达到 min 后先启动
运行监控 | 观察训练吞吐、队列资源、故障事件
扩容 | 空闲资源满足 fairshare 时增加 worker，并触发 rendezvous
缩容 | 节点故障或配额回收时减少 worker，训练框架重建通信组
语义修正 | 调整 global batch、学习率、数据 shard、checkpoint 元信息
```

### 面试追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 所有分布式训练都适合弹性吗？</div>
<div class="qa-a"><p>不是。DP 维度通常更容易弹性，因为多几个或少几个 data parallel worker 比较自然；TP/PP 改 world size 会改变模型切分，代价很高。所以大模型训练常见做法是固定 TP/PP，优先弹性 DP。</p></div>
</div>

<div class="qa-summary">面试金句：弹性训练不是单纯调度问题，它要求调度器、训练框架和 checkpoint/rendezvous 协同。</div>

## 11. 故障感知调度

### 典型题目

GPU 集群里经常出现这些问题：某张卡频繁 Xid 错误，某台机器 ECC error 增多，某个机架 IB 丢包，节点偶发 NotReady。用户抱怨任务刚调度上去就失败，或者 NCCL hang 很久才超时。你怎么让调度系统具备故障感知能力？

### 先解释调度和故障的关系

故障感知调度不是只在任务失败后重试。更好的系统要做到三件事：坏资源不要再被分配，运行中故障能快速隔离，恢复后资源能有审计地重新加入集群。

### 10 分钟回答展开

```flow
健康采集 | DCGM / node exporter / kubelet condition / IB metrics
资源标记 | node taint、GPU device health、unschedulable
调度过滤 | Filter 阶段排除坏卡、坏节点、拥塞域
任务恢复 | 重调度、弹性缩容、checkpoint 重启
闭环治理 | 故障统计、自动隔离、维修后恢复、容量扣减
```

指标：

- GPU Xid / ECC / temperature / power。
- NVLink error、PCIe replay、IB symbol error。
- Node condition、kubelet/runtime health。
- 任务失败率、重试率、checkpoint 恢复时间。

落地动作可以更具体：

| 阶段 | 动作 |
|---|---|
| 采集 | DCGM 采集 Xid/ECC/温度/功耗，网络侧采集 IB 错误和丢包 |
| 判定 | 区分临时抖动、可恢复错误、需要隔离的硬故障 |
| 标记 | 对坏卡、坏节点、坏拓扑域打 taint 或标记 unschedulable |
| 调度 | Filter 阶段排除坏资源，Score 阶段降低风险节点权重 |
| 运行中恢复 | 触发重调度、弹性缩容或 checkpoint 恢复 |
| 闭环 | 维修后通过 burn-in 测试，再自动或人工恢复调度 |

### 面试追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不能所有失败都直接重试？</div>
<div class="qa-a"><p>如果根因是坏卡或坏网络，直接重试可能又调回同一类资源，形成失败风暴。故障感知调度要先隔离异常资源，再决定任务是重试、缩容、迁移还是从 checkpoint 恢复。</p></div>
</div>

## 工业落地层次

| 层次 | 适合回答的点 |
|---|---|
| Kubernetes 基础层 | Device plugin 注册 GPU 数量，Node label 表达卡型和硬件特征，scheduler 做 Filter/Score/Preemption |
| 批调度层 | Job / PodGroup / Queue / Reservation 表达分布式训练、队列公平和大任务预约 |
| 平台准入层 | 根据租户、任务画像、卡型资源池、配额和优先级决定任务能不能进入调度 |
| 调度扩展层 | 深度定制拓扑、干扰预测、显存切分、抢占代价和训练框架语义 |
| 监控闭环层 | DCGM、Xid、NCCL、队列等待、GPU 利用率和成本指标反向修正策略 |

## 参考资料

- Kubernetes docs: scheduler framework、PriorityClass、preemption、node affinity。
- NVIDIA k8s-device-plugin docs: device plugin、MIG strategy、time-slicing。
- NVIDIA GPU Feature Discovery docs: GPU feature labels、NFD integration。
- NVIDIA GPU Operator docs: device plugin、Node Feature Discovery、GPU Feature Discovery、MIG Manager、DCGM Exporter。
- Volcano docs: Gang Scheduling、Queue Resource Management、Binpack、Preempt / Reclaim。

## 关联模块

- `多资源公平调度`：DRF、Elastic Quota、借用和回收。
- `批调度、Gang 与 Backfill`：组调度、回填、抢占和 checkpoint。
- `拓扑感知调度`：GPU/NIC/NUMA/NVLink/RDMA 放置。
- `海量小显存 GPU 作业调度`：短作业高吞吐和 fractional GPU 装箱。

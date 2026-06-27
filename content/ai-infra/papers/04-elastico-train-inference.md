## 一句话结论

ElastiCo 面向训练与离线 LLM 推理在同一 GPU 上的安全共置，提出资源形态变换、弹性影子定价与干扰感知共置三项机制，以 Kubernetes 原生中间件实现、无需改用户代码，在 64 卡实测中 JCT 降低 2.94×、GPU 利用率从 25% 提升至 46%。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 论文工作 |
| 章节类型 | 论文项目类 |
| 解决问题 | 训练任务和离线推理任务如何安全共置在同一 GPU 上，同时保证训练不被推理 SLO 违约拖慢、推理不因训练抢占而崩溃。 |
| 面试抓手 | 和 DeepShare 形成互补——DeepShare 解决多租户配额管理，ElastiCo 解决同一租户内训推混部的资源形态与定价问题。 |

<div class="card card-s" style="margin-top:0.8rem">
<p><strong>📄 论文原文：</strong><a href="../../../resources/papers/PE_Journal2026_ElastiCo.pdf" target="_blank">Performance Evaluation 2026 — ElastiCo PDF</a></p>
</div>

<div class="card card-m">
<h3>问题背景</h3>
<p>GPU 集群中同时存在两类负载：</p>
<ul>
<li><strong>训练任务</strong>：长时运行（几小时到几天），资源需求波动大（前向/反向/通信阶段 GPU 利用率交替高低），对延迟不敏感但不能被随便杀（checkpoint 周期长，重启代价大）。</li>
<li><strong>离线 LLM 推理</strong>：相对短时（几分钟到几十分钟），对延迟有一定 SLO 要求，资源需求在 prefill 阶段高、decode 阶段低。</li>
</ul>
<p>核心矛盾：</p>
<ol>
<li><strong>资源互补</strong>：训练在通信/数据加载阶段 GPU 空闲，decode 阶段 SM 利用率低，可以互相填补空隙。</li>
<li><strong>干扰风险</strong>：如果直接放一起，两者争用 SM、显存带宽，可能导致训练 JCT 暴增或推理 SLO 违约。</li>
<li><strong>缺乏隔离机制</strong>：NVIDIA MPS 能做算力划分，但不能动态调整、不能处理显存竞争；MIG 是静态划分，灵活性不够。</li>
</ol>
<p>ElastiCo 的核心问题：<span class="hl">如何让训练和推理安全共置，且推理可弹性进出（原主要求资源时推理能退），不需要修改用户代码。</span></p>
</div>

<div class="card card-m">
<h3>三项核心机制</h3>

<div class="comp">
<div class="comp-t">机制一：资源形态变换（Resource Morphing）</div>
<p>训练和推理对 GPU 资源的使用模式不同：</p>
<ul>
<li><strong>训练</strong>：主要消耗 SM 算力 + 显存（存权重、梯度、优化器状态），对 SM 比例敏感但可容忍一定的 SM 缩减。</li>
<li><strong>推理</strong>：主要消耗显存（权重 + KV Cache），prefill 阶段突发算力，decode 阶段算力需求低。</li>
</ul>
<p>资源形态变换的核心思想是：<strong>根据两个任务当前阶段动态调整资源分配比例</strong>，而不是固定切分。具体来说：</p>
<ul>
<li>利用 CUDA MPS 的 per-client SM 限制做<strong>算力比例动态调整</strong>（通过 CUDA_MPS_ACTIVE_THREAD_PERCENTAGE 环境变量动态设置）。</li>
<li>利用 CUDA VMM 的显存预留/提交机制做<strong>显存弹性管理</strong>——推理权重和 KV Cache 按需映射，训练需要时可回收。</li>
<li>当训练进入 I/O 或通信阶段（GPU 空闲窗口），主动增加推理的 SM 配额；训练进入计算阶段时，收缩推理 SM 配额。</li>
</ul>
<p>和静态 MIG 切分的区别：MIG 是物理分区，切完后算力和显存比例固定；MPS + VMM 是逻辑隔离，可以毫秒级调整。</p>
</div>

<div class="comp">
<div class="comp-t">机制二：弹性影子定价（Elastic Shadow Pricing）</div>
<p>影子定价借鉴经济学中的影子价格概念——给每个资源（GPU 上的 SM、显存）定一个动态"价格"，反映该资源在当前时刻的稀缺程度。</p>
<p>定价模型：</p>
<ul>
<li><strong>价格信号</strong>：基于训练任务的当前 GPU 利用率和显存使用量计算——利用率越高、显存越紧张，SM 和显存的影子价格越高。</li>
<li><strong>弹性调整</strong>：当影子价格低（训练空闲）时，允许推理使用更多资源，定价低；当影子价格高（训练繁忙）时，推理缩容，定价高。</li>
<li><strong>准入控制</strong>：推理任务的"价值"（SLO 优先级 × 剩余工作量）必须大于当前影子价格才能启动共置，否则等待或放到空闲 GPU。</li>
</ul>
<p>本质上是把<strong>资源分配问题转化为一个基于动态价格的市场清算问题</strong>：价格随供需变化，供需平衡时实现最优共置。比固定阈值更灵活——高优推理在价格高时仍可进入，低优推理在价格低时才进入。</p>
</div>

<div class="comp">
<div class="comp-t">机制三：干扰感知共置（Interference-Aware Colocation）</div>
<p>和 DeepShare 的干扰感知有相似之处，但针对训推共置场景做了特殊优化：</p>
<ul>
<li><strong>特征工程</strong>：不仅采集硬件计数器（SM activity、mem bandwidth、L2 hit rate），还采集训练任务的阶段信号（forward/backward/communication 阶段），用阶段信息辅助干扰预测。</li>
<li><strong>干扰模型</strong>：训练一个轻量级性能模型，预测"训练任务在阶段 S、推理任务在阶段 T、SM 比例为 x"时，两者的 slowdown。</li>
<li><strong>动态准入与驱逐</strong>：实时监控实际 slowdown，超过训练容忍阈值（如 10%）时暂停/驱逐推理；低于阈值时继续运行。</li>
<li><strong>推理保护</strong>：推理任务有自己的 SLO 预算（如 TTFT < 500ms），当干扰导致推理 SLO 有违约风险时主动缩容推理的 batch size 而非杀掉。</li>
</ul>
<p>关键区别：DeepShare 的合用主要是<strong>训练+训练</strong>共置，两个任务地位对等；ElastiCo 是<strong>训练+推理</strong>，训练是"主"、推理是"客"，主客之间有优先级不对称性——推理可以被暂停/驱逐/缩容，但训练不应该被杀。</p>
</div>

<h3>核心结果</h3>
<div class="grid">
<div class="gi"><div class="gv g">2.94×</div><div class="gl">JCT 最高降低</div></div>
<div class="gi"><div class="gv g">2.02×</div><div class="gl">集群吞吐提升</div></div>
<div class="gi"><div class="gv g">25% → 46%</div><div class="gl">GPU 利用率提升</div></div>
<div class="gi"><div class="gv g">64 GPU</div><div class="gl">实测验证</div></div>
</div>
</div>

<div class="card card-s">
<h3>Kubernetes 实现</h3>
<p>ElastiCo 实现为 <strong>Kubernetes 原生中间件</strong>，核心组件：</p>
<ul>
<li><strong>ElastiCo Controller</strong>：管理共置对（co-location pair）的生命周期、影子定价计算、准入决策。监听 Pod 事件，识别训练 Pod 和推理 Pod。</li>
<li><strong>Node Agent（DaemonSet）</strong>：部署在每个 GPU 节点上，负责：(1) 通过 DCGM 采集 GPU 硬件指标；(2) 动态调整 MPS SM 比例；(3) 通过 CUDA VMM ioctl 管理显存映射；(4) 监控实际 slowdown 并上报 Controller。</li>
<li><strong>Scheduler Plugin</strong>：扩展 Score 插件，优先把推理 Pod 调度到有空闲窗口的训练 GPU 节点上；Filter 插件检查节点是否满足推理的最小资源需求。</li>
</ul>
<p><strong>零侵入</strong>：用户不需要修改训练或推理代码。通过 MPS 环境变量 + CUDA VMM API + cgroup 限制在运行时层面实现隔离和弹性。</p>
</div>

<div class="card card-w">
<h3>和 DeepShare 的关系</h3>
<table>
<tr><th>维度</th><th>DeepShare</th><th>ElastiCo</th></tr>
<tr><td>解决场景</td><td>多租户之间的配额管理与资源借用</td><td>同一 GPU 上训练与推理的共置</td></tr>
<tr><td>核心信号</td><td>QAD（配额保障度）</td><td>影子定价（资源稀缺度）</td></tr>
<tr><td>合用对象</td><td>训练 + 训练</td><td>训练 + 推理</td></tr>
<tr><td>优先级</td><td>Guaranteed > Best-effort，对等租户之间</td><td>训练为主、推理为客，不对称优先级</td></tr>
<tr><td>资源隔离</td><td>MPS 静态 SM 限制</td><td>MPS 动态 SM + VMM 弹性显存</td></tr>
<tr><td>驱逐策略</td><td>杀 Best-effort Pod</td><td>推理可暂停/缩容/驱逐，训练不杀</td></tr>
</table>
<p>两者可以组合使用：DeepShare 在集群层面做多租户配额治理，ElastiCo 在节点层面做训推共置优化。</p>
</div>

<div class="card card-m">
<h3>ElastiCo 高频问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: "资源形态变换"具体是怎么变换的？为什么叫"形态"而不是"分配"？</div>
<div class="qa-a"><p>"形态"强调的不是简单地把 GPU 切成固定比例，而是<strong>根据不同类型任务的资源使用特征，动态改变资源的"形状"——即 SM 算力和显存的分配比例</strong>。训练任务在计算阶段需要更多 SM、在 IO 阶段不需要；推理在 prefill 需要突发 SM、decode 阶段 SM 空闲。固定切分（如 MIG 50/50）无法利用这些互补窗口。ElastiCo 通过 MPS 动态调整 active thread percentage 实现 SM 弹性，通过 CUDA VMM 按需映射/取消映射物理页实现显存弹性，组合起来就是资源形态随负载动态变化。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 影子定价和 DeepShare 的 QAD 有什么本质区别？</div>
<div class="qa-a"><p>QAD 是<strong>租户级保障指标</strong>，回答"这个租户被欠服务了多少"，用于跨租户优先级排序；影子定价是<strong>节点级资源价格信号</strong>，回答"当前这张 GPU 的资源有多稀缺"，用于推理任务的共置准入决策。QAD 驱动"谁先调度"，影子定价驱动"能不能共置、共置多少"。两者在不同层级运作。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 训练的 checkpoint 怎么处理？驱逐推理会不会导致训练崩？</div>
<div class="qa-a"><p>ElastiCo <strong>不会驱逐训练任务</strong>。训练是"主"角色，在 GPU 上有常驻权。被驱逐/缩容的始终是推理任务。推理任务因为是离线推理（非在线服务），SLO 是分钟级而非毫秒级，被驱逐后可以：(1) 暂停（保留 KV Cache 在 CPU 内存），等训练空闲再恢复；(2) 迁移到其他 GPU；(3) 如果推理支持增量 checkpoint，从断点继续。实测中推理暂停/恢复开销约 2-5 秒，对离线推理可接受。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 怎么做到"无需修改用户代码"？</div>
<div class="qa-a"><p>三层透明注入：(1) <strong>容器层</strong>：通过 admission webhook 自动注入 MPS 环境变量、VMM 配置和必要的 LD_PRELOAD 库；(2) <strong>运行时层</strong>：Node Agent 通过 CUDA Driver API（cuMemCreate/cuMemMap/cuMemUnmap）管理显存，不需要训练/推理框架感知；(3) <strong>调度层</strong>：Scheduler Plugin 在调度阶段就做好放置决策，用户只需要提交标准 Pod（带 elastico.sh/class: training 或 inference 标签）。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 GPU 利用率只有 46%？DeepShare 不是 70% 吗？</div>
<div class="qa-a"><p>两个系统的基线利用率不同。ElastiCo 的场景是<strong>训推共存集群</strong>，训练任务本身有大量 IO/通信空窗，纯训练集群的平均利用率通常只有 20-30%；而 DeepShare 的场景是纯训练多租户集群，基线利用率约 40%。而且 ElastiCo 的 46% 是<strong>训推安全共置</strong>下的利用率，有 SLO 约束（不能让训练 slowdown 超过阈值），而 DeepShare 是训练间共享，干扰容忍度更高。两者不可直接比较数字。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: MPS 动态调整 SM 比例的延迟是多少？会不会影响推理实时性？</div>
<div class="qa-a"><p>MPS SM 比例调整通过设置 CUDA_MPS_ACTIVE_THREAD_PERCENTAGE 并重启 MPS control daemon 实现，切换延迟约 50-200ms。ElastiCo 不会在 prefill 阶段调整 SM 比例（那是推理的关键路径），而是在 decode 阶段或训练通信阶段做调整。对离线推理来说，200ms 级别的波动完全可接受。</p></div>
</div>
</div>

## 关联模块

- `论文工作 / DeepShare`：多租户层面的配额治理，可与 ElastiCo 组合。
- `GPU 硬件与资源共享 / MIG/MPS`：GPU 共享的硬件基础。
- `Kubernetes 核心 / Scheduler 插件`：K8S 调度框架扩展点落地。
- `LLM 推理系统`：推理侧 prefill/decode 资源特征。

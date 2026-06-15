## 一句话结论

面试版完整回答（背诵展开版） 这一节要服务项目深挖：先说明问题背景和核心贡献，再讲系统设计、实现证据、实验结果和面试追问。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 论文工作 |
| 章节类型 | 论文项目类 |
| 解决问题 | 围绕 Maestro 与 DeepShare 的问题背景、系统设计、实现细节、实验结果和高频追问建立项目叙事。 |
| 面试抓手 | 按背景、方案、实现、结果、局限回答。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心概念、系统链路或关键机制，把知识点映射到工程场景。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-w">
<h3>面试版完整回答（背诵展开版）</h3>
<p>如果先不考虑 Gang Scheduling，我会把 DeepShare 在 Kubernetes 里的实现拆成 Controller 和 Scheduler Plugin 两部分。<strong>Controller 负责租户级资源治理，Scheduler Plugin 负责 Pod 级调度。</strong></p>
<p>Controller 维护每个租户的 Guaranteed 队列和 Best-effort 队列，也就是论文里的 <code>Q_i^G</code> 和 <code>Q_i^B</code>。它 watch 用户提交的 GPU Job 或 Pod，读取 tenant、class、GPU request 和预测运行时间，然后放入对应租户队列。Controller 还会周期性统计每个租户的 quota 使用量，计算 QAD，并维护 TenantQuota 的 status。</p>
<p>Controller 还负责准入。对于 Guaranteed 作业，只有满足 <code>U_i^G + R_j ≤ q_i</code> 时才允许进入调度候选集；对于 Best-effort 作业，只有在没有可放置的 Guaranteed 作业，并且 <code>U_i^B + R_j ≤ η·q_i</code> 时才允许进入候选集。被准入的 Pod 通过移除 schedulingGate，或打上 admitted annotation 进入 kube-scheduler。</p>
<p>第二级集群队列由 Scheduler Plugin 的 QueueSort 实现：Controller 负责生成 admitted Pod 集合，QueueSort 在 kube-scheduler 内部按 DeepShare 规则排序——Guaranteed 优先于 Best-effort；同一类中 QAD 低的租户优先；QAD 接近时预测运行时间短的作业优先；最后用提交时间作为 tie-breaker。</p>
<p>后续 Scheduler Plugin 负责真正的节点决策。PreFilter 解析 tenant、class、GPU 需求和预测时间；Filter 检查节点 GPU 是否足够、是否满足共享和干扰约束；Score 做 bin packing、碎片控制和干扰感知打分；Reserve/Unreserve 维护 DeepShare 自己的资源账本；PostFilter 在 Guaranteed 作业调度失败且租户 QAD 很低时，选择低代价 Best-effort Pod 进行抢占。</p>
<p><strong>两个队列的实现总结：</strong>第一级租户队列在 Controller 中显式维护；第二级全局队列不一定是单独物理队列，而是<strong>由 Controller 准入后的 Pod 集合 + Scheduler Plugin 的 QAD-aware QueueSort 共同实现</strong>。这样既保留 Kubernetes-native 的调度框架，又能实现 DeepShare 的 QAD 驱动资源管理。</p>
</div>

<div class="card card-d">
<h3>面试版 60 秒背诵版</h3>
<p>不考虑 Gang Scheduling 时，Controller + Scheduler Plugin 的分工是：<strong>Controller 管 tenant/job 级逻辑，Scheduler Plugin 管 Pod/node 级逻辑。</strong></p>
<p>Controller 维护每个租户的 Guaranteed / Best-effort 队列，计算 QAD，做 quota admission 和 Best-effort cap 控制。通过准入的 Pod 才进入 scheduler。</p>
<p>Scheduler Plugin 通过 QueueSort 实现全局排序：<em>Guaranteed first，QAD low first，runtime short first</em>。然后用 Filter/Score 做节点选择和 colocation 判断，用 Reserve/Unreserve 更新资源账本，用 PostFilter 做 Best-effort 抢占。</p>
<p><span class="hl">第一级队列在 Controller 里，第二级队列由 admitted Pod 集合 + QueueSort 逻辑实现。</span></p>
</div>

## 面试回答

**30 秒版：**

02f-talk 这一节要服务项目深挖：说明问题背景、核心贡献、系统设计、实验或证据，以及面试追问怎么回答。 按背景、方案、实现、结果、局限回答。

**2 分钟版：**

我会先说明这个知识点在 论文工作 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

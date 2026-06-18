## 一句话结论

多模型 LLM 推理服务的设计主线是「在有限 GPU 上让尽可能多的模型既低延迟又高利用率」：靠层级化模型驻留（Running/Sleeping/CPU/Disk）解决放不下，靠显存超配和准入控制守住 OOM，靠适应度路由 + 分队列 + SRTF 排队解决调度，靠输出长度预测把这些串起来。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 系统设计题 |
| 章节类型 | 系统设计类 |
| 解决问题 | 围绕多模型推理、多租户调度、分布式训练平台和 KV Cache 管理形成可复述设计题框架。 |
| 面试抓手 | 回答时先定范围，再讲核心链路，最后落到工程风险和面试追问。 |

<div class="card card-m">
<h3>题目</h3>
<p>设计一个支持多模型的 LLM 推理服务，要求低延迟高利用率，多个 agent 组成工作流协作。</p>

<h3>设计要点</h3>
<ol>
<li><strong>模型驻留管理</strong>
  <ul>
  <li>层级化 LRU：Running → Sleeping → CPU → Disk → Remote</li>
  <li>Sleeping 状态保留 CUDA Graph + JIT 缓存，加速重新激活</li>
  <li>热门模型常驻 GPU，冷门模型逐级退出</li>
  </ul>
</li>
<li><strong>内存管理</strong>
  <ul>
  <li>核算约束：M_kv + M_res ≤ M_total</li>
  <li>CUDA VMM 超配：虚拟地址池 3× 物理显存，按需映射</li>
  <li>准入控制：每个请求进来先检查资源是否够</li>
  </ul>
</li>
<li><strong>请求路由</strong>
  <ul>
  <li>适应度评分综合就绪延迟、KV 适配度、降级代价</li>
  <li>交互和批处理分队列，避免 HoL blocking</li>
  </ul>
</li>
<li><strong>排队策略</strong>
  <ul>
  <li>SRTF 基于预测剩余时间排序</li>
  <li>Stage 边界抢占，不打断解码中的请求</li>
  </ul>
</li>
<li><strong>预测驱动</strong>
  <ul>
  <li>输出长度预测 → KV 需求 → 准入控制 + 内存预分配</li>
  <li>安全裕度偏向高估，防止 OOM</li>
  </ul>
</li>
</ol>

<h3>追问方向</h3>
<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">追问：如何处理突发流量？</div>
<div class="qa-a"><p>(1) 排队 + 准入控制：超出容量的请求排队等待，不是直接拒绝。(2) 降级策略：用更小的模型替代、减少最大输出长度、增大 batch。(3) 弹性扩缩：基于排队深度自动启动新实例（但模型加载需要时间，所以要预热）。(4) 优先级分级：VIP 请求优先，普通请求可延迟。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">追问：模型更新（A/B 测试）怎么做？</div>
<div class="qa-a"><p>(1) 金丝雀部署：新模型先加载到少量节点，小比例流量路由过去。(2) 适应度评分中加入模型版本权重。(3) Sleeping 状态帮助快速回滚——旧模型保留在 CPU，回滚只需重新激活。(4) KV 缓存不兼容不同模型版本，新模型需要重新 prefill。</p></div>
</div>
</div>

<hr class="div">

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

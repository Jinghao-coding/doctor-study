## 预测收益如何验证

预测误差和调度收益回答不同问题。运行时间平均误差降低，不一定改变队列顺序；显存平均误差很小，也可能在少数请求上严重低估。完整验证要同时报告预测精度、显存覆盖率、加载偏差、端到端延迟和系统资源成本。

<div class="table-scroll">

| 追问 | 可验证的回答 |
|---|---|
| GNN 比解析模型强在哪里？ | 在相同数据与预算下比较目标误差、低估尾部和实际决策收益 |
| 融合带来多少收益？ | 固定其余配置，只关闭融合，观察准入次数、重加载和完成时间 |
| 预取是否有效？ | 固定其余配置，统计加载与前驱执行的重叠，以及额外驻留成本 |
| 跨工作流共享有何作用？ | 改变需求合并范围，检查加载排序、复用和资源争用 |
| 是否真在端到端用到 GNN？ | 核对运行命令、资源表来源和运行记录，而不是只看方法名称 |

</div>

## 当前实验材料的口径

2026-09-06 核对到的材料有以下限制，不能把它们混成一组实测结论：

- `data/evaluation_12gpu_counterfactual/manifest.json` 明确标记为 12 GPU 反事实模拟，且未建模跨 GPU 网络、存储、PCIe 与并发加载干扰。这不是 12 卡端到端实测。
- `run_serve_0728.sh` 的 `sagepilot` 分支读取 `cache/profile_v2/predictions.yaml`。该运行配置不能直接支持“收益由 GNN 带来”的归因；需要独立确认使用 GNN 表的实验。
- `serve_0728_reference.md` 说明 Parrot / Kairos 参照仅借用了请求排序规则，没有完整实现各系统的其他机制，因此不能表述为完整系统复现。
- 旧资料中的数据集规模、跨 H100 泛化和“零 profiling”等说法，缺少本次核对所需的完整证据，不作为已验证成果列出。

## 工程追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 两个请求同时看到空闲显存怎么办？</div>
<div class="qa-a"><p>把检查、预留、发 grant 放在同一个资源所有者的原子状态转换中。当前调度器核心通过命令队列串行更新状态，并在异步加载前登记 LOADING 归属。解释并发正确性必须指出状态所有者和原子边界，仅说“异步执行”不足以证明不会超卖。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 取消和完成消息同时到达，如何避免重复释放？</div>
<div class="qa-a"><p>作为工程扩展，应按 request / attempt 标识实现幂等状态转换，让资源只释放一次，并用 generation / epoch 隔离旧尝试。超时不等于 worker 已停止，重新分配前需要取消确认、核对或隔离。这些是需要通过故障测试验证的设计要求，不代表当前系统已经具备完整高可用保证。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GPU 利用率低，怎么找到瓶颈？</div>
<div class="qa-a"><p>先拆请求时间：arrival、ready、acquire、加载起止、生成起止、工具起止与 completion，再关联 session、node、replica、device。分清排队、加载、生成还是工具占主导，再深入对应时间线。显存占用、GPU 忙碌比例和有效生成吞吐不是同一指标，不能仅凭一个利用率百分比下结论。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 从十几张卡扩到万卡，如何设计？</div>
<div class="qa-a"><p>当前材料没有验证万卡。扩展可采用全局路由与局部准入：全局维护容量、模型位置摘要，资源域内部做精确预留。摘要过期时，局部仍拒绝不安全准入；还需处理热模型复制、跨域代价和故障隔离。验证应覆盖控制面事件吞吐、p99 决策延迟、数据面吞吐与恢复时间。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 提高吞吐却让 p95 延迟变差怎么办？</div>
<div class="qa-a"><p>明确负载和目标，例如在满足延迟 SLO 条件下最大化可接受吞吐。长链租约、驻留优先与更大 batch 都可能改变等待分布，需要同时测尾延迟、SLO 违反比例和公平性。当前启发式不能被描述为严格 SLO 保证。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 哪种负载下收益可能变小？</div>
<div class="qa-a"><p>所有模型都能常驻、加载已经完全被隐藏、工作流缺少可融合链，或大部分时间花在生成和工具执行时，生命周期优化的空间可能缩小。相反，频繁换模也不保证一定受益：若预取和重加载争抢 I/O，可能引入新瓶颈，需要受控对照验证。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 简历里的个人贡献该如何具体表达？</div>
<div class="qa-a"><p>把真实负责的组件、一个可复现的问题、做出的代码或策略改变，以及有运行记录支撑的结果连起来。团队成果、当前实现和未来扩展分别陈述。未确认的个人职责、投稿状态与实验提升不填成既成事实。</p></div>
</div>

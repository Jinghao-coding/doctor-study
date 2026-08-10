<div class="card card-d">
<h3>论文原文延伸问答（基于 IEEE Cluster 2026 原稿）</h3>
<p>下面这组问题对应面试官真正会按论文细节追问的角度：参数选取、消融、敏感性、对比 baseline、工程边界。回答全部出自论文正文与 §V 实验。</p>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 论文里 EMA 系数 <code>λ=0.3</code>、调度周期 50ms，物理意义是什么？</div>
<div class="qa-a"><p>论文 §III-A 给的解析：在 50ms 调度周期下，<strong>持续偏差在大约 350ms 内累积到稳态值的 90%</strong>，几何收敛速率为 \((1-\lambda)\)。这个区间能 <strong>过滤亚秒级抖动</strong>（短任务结束、突发请求），同时让真正的"持续 under-service"快速被发现。λ 再调大会被短任务完成的抖动带飞，调小则恢复信号迟滞。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 当租户暂时没有 Guaranteed 需求时 QAD 怎么定？为什么不直接定 0？</div>
<div class="qa-a"><p>论文 Eq.1 显式规定 \(Q_i(t)=1\) 当 \(D_i^G(t)=0\)。这是为了 <strong>"暂时不用 quota ≠ 被亏待"</strong>：定 0 会让空闲租户被错误识别为最受损者并抢回资源；同时分母用 <code>min(q_i, D_i^G(t))</code> 又防止租户通过虚报巨大 \(D_i^G\) 压低 QAD、抬高恢复优先级。这两条共同实现"既不奖励虚假 demand，也不惩罚临时空闲"。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 干扰预测为什么选 Random Forest？论文给的理由是什么？</div>
<div class="qa-a"><p>这里问的是<strong>干扰预测器</strong>，不要和运行时间预测混在一起。论文 §III-C 的考虑包括：(1) <strong>sub-millisecond 推理</strong>，可以放在 Kubernetes scheduler 关键路径上；(2) RFE 选出的主特征是 <strong>SM Active (44.5%)、co-run SM Active (20.6%)、mem copy util (12.3%)</strong>，与干扰来源相符且可解释；(3) 输入是 DCGM 硬件计数器，跨 framework / model 更容易泛化。它预测共享吞吐保持率，\(R^2=0.902\)。<strong>31.84% MAPE 和 \(R^2=0.7286\) 属于另一个 per-tenant gradient boosting 运行时间预测器</strong>，不能拿来证明 Random Forest 的准确率。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 抢占效率 \(E_j\) 的物理含义？为什么用贪心？</div>
<div class="qa-a"><p>定义：</p>
<div class="formula">$$E_j = \frac{R_j \cdot \hat{T}(j)}{1 + \alpha \cdot C_p(j)}$$</div>
<p>分子 <code>R_j·T̂(j)</code> 是"如果抢占这个 victim，能回收多少 <strong>GPU-时</strong>"；分母 <code>1+α·C_p(j)</code> 惩罚<strong>已经被抢占过多次的 Pod</strong>，避免同一作业被反复打断。SelectVictims 按 \(E_j\) 降序贪心选取直到释放约束 Eq.3 满足，复杂度 O(n log n)。这是对原 NP-hard 选 victim 子问题的近似。论文 sensitivity 给默认 <strong>α=0.5</strong>、<strong>β=0.3</strong>，区间 α∈[0.3,0.8]、β∈[0.1,0.6] 都接近最优。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 共享时光靠 RF 准入会不会被打脸？运行时怎么兜底？</div>
<div class="qa-a"><p>会，所以论文叠了一层在线检测：DCGM 周期采样实际 retention \(\hat{\rho}=t_{shared}/t_{excl}\)，<strong>连续 3 个采样窗口 \(\hat\rho<\rho_{tol}\)</strong> 就把这一对标 degraded，下一周期把 Best-effort 伙伴抢占。固定窗口规则相比 CUSUM 等顺序检测的好处：<strong>检测延迟有界 + 每对只维护一组计数器</strong>，落到调度器里行为更可预测。一对 GPU 上发生干扰漂移时不会拖到 Guaranteed 任务才被发现。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 动态容忍 \(\rho_{tol}\) 里的压力 \(P\) 和 \(\gamma\) 是怎么调的？</div>
<div class="qa-a"><p>论文公式：</p>
<div class="formula">$$P = \left(\frac{G_p}{G_f+\epsilon}\right)^{\gamma},\quad \rho_{tol} = \min\!\big(1,\;[\rho_{min} + P(1-\rho_{min})] \cdot \max(k-\tilde{Q}_i,\, k-\tilde{Q}_{ie})\big)$$</div>
<p>\(\gamma=0.5\) 让压力<strong>亚线性增长</strong>，短促 demand burst 不会立刻把所有 colocation 一刀切关掉；最大值再被任一租户的"欠服务度" <code>k - Q̃</code> 放大，<strong>欠服务越严重门槛越高</strong>。Sensitivity 显示 \(\rho_{min}=0.7\) 是甜点：0.5 时 GPU 利用 71.2% 但平均放慢 18%，反而 JCT 倒挂；0.9 时干净但只剩 55.3% 利用率。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 31.84% MAPE 是怎么得到的？冷启动用户怎么办？</div>
<div class="qa-a"><p>Venus 23,859 jobs 上采用<strong>按租户训练的 gradient boosting regressor</strong>。总体 MAPE 为 31.84%，\(R^2=0.7286\)；历史提交 ≥50 的老租户 MAPE&lt;25，新租户落到<strong>集群级 fallback 模型，MAPE&lt;60</strong>。冷启动不会阻断调度，只是时间排序不那么准。Figure 4 在随机 2000 jobs 上对照 real vs prediction；即使长尾作业误差较大，也不会覆盖 QAD 主排序，因为 \(\hat{T}(j)\) 只是 secondary key。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: <code>nvidia.com/gpu</code> 是 K8s Extended Resource，论文怎么绕开"准入后不可修改"？</div>
<div class="qa-a"><p>论文 §IV-B 明确：GPU 数确实改不了，所以 DeepShare <strong>不动 GPU 数</strong>；要释放资源时走两条路。<br/>(1) <strong>CPU/Memory 走 Pod resize subresource</strong>：control plane 必须启用 <code>InPlacePodVerticalScaling</code>，VPA 推荐基础上额外保留 <code>max(10%, 0.5 core)</code> CPU 和 <code>max(10%, 256 MB)</code> memory headroom，避免压缩后 OOM。<br/>(2) <strong>GPU 抢占走删 Pod / 重建</strong>：通过 PostFilter 选 victim 后由 API server 删除 Pod，新 Pod 重新进入 scheduler。这是为什么论文必须在 §IV 里强调依赖 K8s v1.35 的新 subresource。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 集群过载（\(\sum \min(q_i, D_i^G) > G_{tot}\)）时 DeepShare 怎么降级？数据多少？</div>
<div class="qa-a"><p>论文 §V-D 给出量化：Venus peak-hour 中约 <strong>8% 周期</strong>会进入过载。Algorithm 1 按 \(\tilde{Q}_i(t)\) 升序排队，近似 <strong>max-min fair recovery</strong>。可观测后果：<br/>· 单租户最差 \(\tilde{Q}_i=0.72\)；<br/>· spike 之后 <strong>3.2 个 cycle (~160ms)</strong> 恢复到 \(\tilde{Q}_i\ge 0.95\)；<br/>· Best-effort 排队延迟 <strong>2.1×</strong>，Guaranteed 仅 <strong>+14%</strong>——这就是"服务差异化"在论文里的实际兑现。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Ablation 里"DRA 单独"和"DRA + colocation"分别贡献多少？</div>
<div class="qa-a"><p>物理 16-GPU testbed（§V-E Figure 11）：<br/>· <strong>DRA 单独</strong> vs Hard：makespan −23%、JCT −18.5%、queue −36%；<br/>· <strong>DRA + Colocate</strong> vs Hard+Colocate：makespan −32%、JCT −34%、queue −66%；<br/>· DRA + Colocate vs DRA-only 再省 <strong>31% 排队</strong>（Figure 10），整体 throughput <strong>1.48×</strong>。<br/>仿真消融（Figure 7）：去掉 runtime prediction 排队 +18.4%，去掉 interference awareness 排队 +30.1%——结论是 <strong>colocation 的贡献 > runtime prediction</strong>，但两者必须由 QAD 兜住才不会反过来伤害 SLA。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么平均 JCT 只比 Lucid 好 6.3%，但论文还是把 JCT 当卖点？</div>
<div class="qa-a"><p>论文 §V-C 直接解释了：JCT = queueing + execution，<strong>execution 部分各策略基本一样</strong>，所以平均 JCT 改善被稀释。真正能差异化的是排队侧——论文给出 <strong>queueing −46%（1067s vs 1976s）</strong>、<strong>P95/P99 tail JCT −23%</strong>、<strong>idle GPU time −71%（vs Lucid）/ −96.8%（vs FIFO）</strong>。面试时讲"为什么 JCT 看起来涨幅有限"是高频反向追问，要答：DeepShare 主战场是 <strong>排队公平性 + tail-latency</strong>，平均 JCT 不是核心指标。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 论文承认哪些局限？（部署前你会注意什么）</div>
<div class="qa-a"><p>§V-G 明文承认四条：<br/>(1) 干扰预测器在 <strong>16 个 DL 模型族（CV/NLP/RL/recommender）</strong> 上训练，未见架构（如新型 MoE）可能要重训；硬件计数器为输入提供一定泛化。<br/>(2) 物理 testbed 只有 <strong>16 GPU</strong>，结论稳妥外推到 <strong>部门级集群（数十至低三位数 GPU）</strong>，更大规模需要重新评估。<br/>(3) <strong>异构加速器</strong>（如 H100、TPU、国产卡）需要重新 profiling 并重训 RF 干扰模型。<br/>(4) 论文未覆盖 <strong>多 node 分布式训练 / Gang Scheduling</strong> 场景，generalize 到 LLM 大集群训练需要补 PodGroup + Permit 扩展点（可主动补充作为面试加分）。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 跟 Lucid、Tiresias、Gavel、HiveD 这些 prior art 的本质差异点是什么？</div>
<div class="qa-a"><p>论文 §VI Related Work 总结：<br/>· <strong>Tiresias</strong>：MLFQ 排序但无 runtime knowledge；DeepShare 加了运行时间预测和 QAD。<br/>· <strong>Lucid</strong>：最强非侵入式 sharing baseline，但干扰模型简单（DeepShare 干扰 \(R^2=0.902\) 显著更准）+ 静态阈值（DeepShare 用 \(\rho_{tol}\) 动态调）。<br/>· <strong>Gavel</strong>：max-min fair throughput 但<strong>假设 GPU 独占</strong>，没法 colocate。<br/>· <strong>HiveD</strong>：静态 cell 分区给保证，<strong>不弹性</strong>，恰好是 DRA 要解的问题。<br/>· <strong>Optimus / ElasticFlow</strong>：在线 runtime prediction 但<strong>无 QAD</strong>，会让短任务覆盖租户公平性。<br/>论文卖点是<strong>把 quota assurance + interference colocation + runtime prediction 三者用单一 \(\tilde{Q}_i(t)\) 信号闭环</strong>，前述任何一篇都只解决其中一两块。</p></div>
</div>
</div>

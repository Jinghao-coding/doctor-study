## 一句话结论

线上预测系统必须处理概念漂移、冷启动、长尾误差和安全裕度。
<div class="card card-r">
<h3>四层防御机制</h3>
<table>
<tr><th>层次</th><th>推理场景</th><th>训练场景</th></tr>
<tr><td>安全裕度</td><td>ρ ∈ [0.1, 0.3]，偏向高估</td><td>—</td></tr>
<tr><td>在线校准</td><td>EWMA 跟踪误差分位数，误差增大自动扩大裕度</td><td>EMA 平滑 QAD，过滤瞬时噪声</td></tr>
<tr><td>Fallback</td><td>per-role 数据不足 → 全局模型</td><td>新作业无历史 → 集群级中位数</td></tr>
<tr><td>增量更新</td><td>post-execution profiling 持续收集真实数据</td><td>周期性再训练（如每天/每周）</td></tr>
</table>
</div>

<div class="card card-s">
<h3>Concept Drift 应对</h3>
<p>模型部署后，数据分布会随时间变化——新 agent 上线、用户行为变化、模型版本升级。应对策略：</p>
<ol>
<li><strong>滑动窗口训练</strong>：只用最近 N 天的数据重训，自动遗忘过时模式</li>
<li><strong>置信度监控</strong>：EWMA 跟踪预测误差，误差持续增大说明 drift 发生</li>
<li><strong>异常检测</strong>：误差突增超过阈值 → 告警通知人工检查</li>
<li><strong>模型热加载</strong>：新模型训练好后在线替换，不停服更新</li>
</ol>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 预测模型本身会不会成为系统瓶颈？</div>
<div class="qa-a"><p>需要从两个维度评估：(1) <strong>延迟</strong>——推理场景预测约 10ms，对比 LLM 推理本身几百毫秒到几秒，可忽略；训练场景预测 &lt; 1ms，调度总预算 50ms 中占比极小。(2) <strong>吞吐</strong>——树模型推理是纯 CPU 计算，单核每秒可做上万次预测，不会成为瓶颈。如果未来需要更复杂的模型，可以考虑异步预测 + 缓存结果。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 MAPE ~30% 的预测精度能接受？</div>
<div class="qa-a"><p>三个原因：(1) 预测用于<strong>排序</strong>而非精确计时——只要排序大致正确，SJF 效果就好。(2) 实际作业运行时间跨度大（分钟到小时），30% 的误差在排序上影响有限。(3) 有退化保护——预测完全不准时退化为 FIFO，不会比基线差。类似的，Backfill scheduling 中 SLURM 的运行时间估计误差常超过 100%，但依然有效。</p></div>
</div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

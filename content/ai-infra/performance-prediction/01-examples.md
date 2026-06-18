## 一句话结论

性能预测例子要说明预测目标是什么、输入特征是什么、结果如何服务调度或容量规划。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 性能预测与建模 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕树模型与深度模型选择、特征工程、评价指标、鲁棒性和在线校准建立 ML-for-Systems 答案。 |
| 面试抓手 | 不要只讲模型，要讲系统决策如何使用预测。 |

<div class="card card-s">
<table>
<tr><th>维度</th><th>推理场景</th><th>训练场景</th></tr>
<tr><td>预测目标</td><td>输出 token 长度</td><td>作业执行时间</td></tr>
<tr><td>模型</td><td>LightGBM（两阶段）</td><td>Random Forest</td></tr>
<tr><td>特征来源</td><td>结构化（角色、位置）+ 语义（MiniLM → PCA）</td><td>硬件计数器 + 历史统计</td></tr>
<tr><td>精度</td><td>分类 AUC 0.96，回归 R² 0.78</td><td>MAPE ~30%, R² 0.73</td></tr>
<tr><td>推理延迟</td><td>~10ms</td><td>&lt; 1ms</td></tr>
<tr><td>冷启动</td><td>per-role → 全局 fallback</td><td>≥ 50 历史样本后有效</td></tr>
<tr><td>更新策略</td><td>post-execution profiling + EWMA</td><td>周期性再训练 + EMA 平滑</td></tr>
</table>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

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

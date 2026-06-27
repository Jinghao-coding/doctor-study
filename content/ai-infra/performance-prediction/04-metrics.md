## 一句话结论

预测评估要区分回归和分类指标，MAPE/MAE/RMSE/R2/AUC/F1 各有适用边界。
<div class="card card-s">
<h3>回归评估指标</h3>
<table>
<tr><th>指标</th><th>公式/含义</th><th>适用场景</th></tr>
<tr><td>MAE</td><td>平均绝对误差，对异常值不敏感</td><td>输出长度预测</td></tr>
<tr><td>MAPE</td><td>平均绝对百分比误差，无量纲，跨尺度可比</td><td>运行时间预测</td></tr>
<tr><td>R²</td><td>决定系数，1 为完美预测，0 为均值基线</td><td>衡量整体拟合</td></tr>
<tr><td>RMSE</td><td>均方根误差，对大误差敏感</td><td>关注极端情况时使用</td></tr>
</table>

<h3>分类评估指标</h3>
<table>
<tr><th>指标</th><th>含义</th><th>使用</th></tr>
<tr><td>AUC</td><td>ROC 曲线下面积，阈值无关的整体判别力</td><td>工具调用分类等二分类任务</td></tr>
<tr><td>Precision</td><td>预测为正的里面实际为正的比例</td><td>避免假阳性</td></tr>
<tr><td>Recall</td><td>实际为正的里面被预测为正的比例</td><td>避免假阴性</td></tr>
<tr><td>F1</td><td>Precision 和 Recall 的调和平均</td><td>不均衡分类</td></tr>
</table>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

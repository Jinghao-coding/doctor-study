<div class="card card-w">
<h3>推理输出长度预测特征</h3>
<table>
<tr><th>类别</th><th>特征</th><th>信号</th></tr>
<tr><td rowspan="4">结构化特征</td><td>agent 角色 ID</td><td>不同角色输出模式不同</td></tr>
<tr><td>工作流位置（DAG 深度）</td><td>初始 stage 倾向短输出，终端 stage 倾向长输出</td></tr>
<tr><td>当前调用索引</td><td>对话中越后面的调用越可能是总结</td></tr>
<tr><td>工具可用性标记</td><td>有工具的 stage 更可能做工具调用</td></tr>
<tr><td rowspan="2">语义特征</td><td>MiniLM prompt 嵌入</td><td>捕捉语义内容信号</td></tr>
<tr><td>PCA 384→32 维</td><td>降维减少过拟合和推理时间</td></tr>
<tr><td>交叉特征</td><td>分类器预测概率 p̂_tool</td><td>告诉回归器当前处于哪个分布模式</td></tr>
</table>

<h3>训练运行时间预测特征</h3>
<table>
<tr><th>类别</th><th>特征</th><th>来源</th></tr>
<tr><td rowspan="3">硬件计数器</td><td>SM activity（%）</td><td>DCGM</td></tr>
<tr><td>Memory bandwidth 利用率</td><td>DCGM</td></tr>
<tr><td>PCIe 吞吐</td><td>DCGM</td></tr>
<tr><td rowspan="3">历史统计</td><td>同类作业历史运行时间</td><td>调度器数据库</td></tr>
<tr><td>请求资源量（GPU 数、CPU、内存）</td><td>Pod spec</td></tr>
<tr><td>数据集大小</td><td>作业元数据</td></tr>
</table>
</div>

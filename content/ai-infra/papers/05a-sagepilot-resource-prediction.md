## 预测对象与查表接口

预测对象是一种请求配置在某类 GPU 上的资源代价。例如 `Qwen3-8B / decode / V100 / batch=2 / 输入=2048 / 输出=512` 对应运行时间、显存点估计、显存准入上界和加载时间。调度在线查表；离线可以用 GNN 或实测 profiling 生成同一接口的数据。

**GNN 读取模型算子图，SageGraph 处理 Agent 工作流图。** 前者的节点是矩阵乘、Attention 等算子；后者的节点是完整模型调用或工具调用。

<div class="table-scroll">

| 特征层次 | 具体输入 | 提供的信息 |
|---|---|---|
| 节点 | 算子类型、MACs、参数量、内存量、张量形状、入度和出度 | 每个算子的计算与访存规模 |
| 边 | 张量字节数、元素数、维度、两端节点连接信息 | 算子之间的数据依赖 |
| 全局 | 阶段、batch、输出长度、GPU 算力/容量/带宽、整图统计 | 请求配置与设备条件 |

</div>

## 原始预测如何训练出来

当前路径从 PyTorch 导出的计算图构造特征。decode 图先建立长度为 `输入长度 + 输出长度 - 1` 的 KV 上下文，再捕获一步 decode，并把输出长度作为全局特征。因此输出 512 tokens 的配置不需要把 512 步全部展开成图。

```flow
算子类型 embedding | 与节点数值特征拼接
节点、边、全局特征编码 | 映射到隐藏向量
TransformerConv 图层 | 沿依赖边聚合，并更新边与全局状态
mean / sum / max pooling | 汇总整图表示
独立回归头 | 输出各目标标量，按对应缩放规则恢复量纲
```

核对的训练配置使用 128 维隐藏表示、2 层图网络、8 个 attention heads、九个预测目标。训练以实测标签做监督，使用加权 Smooth L1 损失和 AdamW。运行时间、显存和部署时间对应 `run_duration_sec_avg`、`gpu_mem_used_mb_max`、`deployment_duration_sec_avg`；其他目标包括 CPU、主机内存、GPU 活跃度与功率。

## 运行时间：用近期长度选择预测桶

资源表按模型、GPU、batch、输入长度和输出长度索引。在线时间估计可使用同一节点近期输出 token 数的 p90 选择覆盖桶；没有历史则使用配置的输出上限。

例如输出上限为 1024，近期 p90 为 300，时间估计可查询覆盖 300 的桶。p90 描述过去样本的长度分布，不能保证下一次一定不超过它。

当前等预算评估读取已标定的运行时间缓存；冻结缓存最初的完整标定入口在原问答中尚未追清。因此不把未经核实的线性校准公式写成运行时间的既定实现。

## 显存：点估计、校正值与准入上界

显存低估可能导致 OOM，所以点预测不能直接等同准入预算。当前后处理先拟合线性去偏项，其中 I、B、O 分别是输入长度、batch 和输出长度：

\[
M_{corr}=\max\{1, w^\top[\hat M,\log_2 I,\log_2 B,\log_2 O,1]\}
\]

这里的 1 是代码使用的最小正值，单位沿用资源表的 MB。再根据校准集的正向残差分位数加入余量，并至少保留 10%：

\[
M_{upper}=\max(M_{corr}+q_{0.95},\ 1.1M_{corr})
\]

最终准入条件还包括固定余量与该配置的 OOM 惩罚：

\[
M_{upper}+\epsilon_{mem}+penalty_{OOM}\le M_{GPU}
\]

**显存按配置的输出上限检查，不因近期输出较短而缩小准入容量。** 例如时间按 300 tokens 的覆盖桶估计，显存仍按 1024 上限的覆盖桶检查。两者分别服务于完成时间估计与容量安全。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 95% 分位数加 10% 余量，能保证零 OOM 吗？</div>
<div class="qa-a"><p>这是经验上界。运行分布变化、后端额外开销和未建模状态都可能使实际占用超出校准范围。分位数必须用独立数据验证覆盖率，并监测低估尾部与 OOM；它不能作为绝对安全证明。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不用参数量、FLOPs 或 GBDT？</div>
<div class="qa-a"><p>图特征能表达算子类型、形状和依赖的差异，但有图结构不等于必须用 GNN。应比较解析公式、表格模型和 GNN 的误差、数据成本与下游调度收益，尤其检查显存低估尾部。简单公式在某些目标上可能更有效。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 换成 H100 的设备属性就能保证泛化吗？</div>
<div class="qa-a"><p>设备属性提供条件输入，不构成泛化保证。新架构、kernel、精度与后端版本都可能改变映射。需要留出 GPU 或模型族的测试，并根据目标设备实测做校准。采图与训练本身也有成本，不能把系统表述为完全零 profiling。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 算子图会遗漏哪些运行信息？</div>
<div class="qa-a"><p>模型级图不自动等同真实 serving 的 kernel 执行图，后端融合、kernel 选择、动态 batching 和资源争用都可能造成偏差。要用匹配后端与负载的标签和独立验证检查误差；新增运行特征或 trace 校准属于需要验证的补偿方法。</p></div>
</div>

核对依据：关联实现的 `src/gnn_model/data/causal_lm_graph.py`、`data/constants.py`、`models/predictor.py`、训练配置 `scaled_training_v2_20260607.yaml`，以及 `src/experiment/workflow/cache_postprocess.py`。

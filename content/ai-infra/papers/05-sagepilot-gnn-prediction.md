## 一句话结论

SagePilot 面向深度学习负载资源预测和 Agentic 工作流编排问题：通过 ONNX 计算图表征 + GNN 多目标预测，在不实际运行的情况下预测模型的时延/显存/GPU利用率，并将预测信号用于 Agent 工作流的模型冷启动预部署、OOM 风险选卡和显存复用，解决 profiling 成本高和 Agent 冷启动慢的问题。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 论文工作 |
| 章节类型 | 论文项目类（在投/撰写中） |
| 解决问题 | 如何在不运行模型的前提下预测其资源画像，并将预测信号用于 Agentic 工作流的资源编排。 |
| 面试抓手 | 重点讲 GNN 为什么适合计算图建模、多目标预测如何设计、以及预测如何指导实际调度决策。 |

<div class="card card-m">
<h3>问题背景</h3>
<p>两个实际痛点：</p>
<ol>
<li><strong>Profiling 成本高</strong>：深度学习模型上线前，往往需要在各种 GPU 型号、batch size、序列长度下反复试跑才能估计资源需求（需要多少显存、跑多快）。对于大模型，一次 profiling 可能需要多张 A100 跑几十分钟，成本高、周期长，拖慢上线节奏。</li>
<li><strong>Agentic 工作流冷启动慢</strong>：LLM Agent 系统中，不同工具调用会触发不同模型（搜索用小模型、代码生成用代码模型、总结用通用模型），模型频繁加载/卸载导致冷启动延迟（模型权重从 CPU 加载到 GPU 需要几秒到几十秒），同时固定显存预留要么 OOM 要么浪费。</li>
</ol>
<p><strong>核心洞察</strong>：模型的计算图（ONNX 格式）天然是一个图结构——节点是算子（matmul、conv、layer_norm 等），边是张量（带 shape、dtype 信息）。计算图的拓扑结构、算子类型和张量形状共同决定了模型的运行时性能。这和 GNN 的图结构建模能力天然匹配。</p>
</div>

<div class="card card-m">
<h3>系统设计</h3>

<div class="comp">
<div class="comp-t">模块一：计算图表征（Graph Representation）</div>
<p><strong>图构建</strong>：将 PyTorch/TF 模型导出为 ONNX，然后将 ONNX 计算图转化为图样本：</p>
<ul>
<li><strong>节点特征</strong>：算子类型（embedding 为 one-hot + 可学习 embedding）、算子属性（kernel size、stride、groups 等卷积参数）、输入输出张量数量。</li>
<li><strong>边特征</strong>：张量 shape（如 [B, 1024, 768] → 维度数值 + dtype + 总元素数）、tensor size（bytes）。</li>
<li><strong>全局特征</strong>：batch size、序列长度、GPU 型号 embedding（不同 GPU 的 SM 数、显存带宽、算力作为 global feature）。</li>
</ul>
<p><strong>图预处理</strong>：ONNX 计算图可能有冗余节点（identity、constant），需要做常量折叠和节点融合预处理；过大的计算图做子图采样，控制图规模在可处理范围内。</p>
</div>

<div class="comp">
<div class="comp-t">模块二：GNN 多目标预测器</div>
<p><strong>为什么用 GNN</strong>：</p>
<ul>
<li>计算图是天然的图结构，CNN/MLP 无法直接处理变长拓扑；</li>
<li>GNN 的消息传递机制模拟了张量数据在算子间流动的过程——算子节点的特征聚合其输入张量的信息，类似实际执行时算子读入输入张量进行计算；</li>
<li>不同模型的计算图大小差异大（从几百到几万节点），GNN 可以处理变长图。</li>
</ul>
<p><strong>模型架构</strong>：</p>
<ul>
<li><strong>GNN Backbone</strong>：使用 GIN（Graph Isomorphism Network）或 GAT（Graph Attention Network）做 4-6 层消息传递，因为算子间主要是 1-hop 依赖，但多层可以捕捉多跳数据流。</li>
<li><strong>Graph-level Readout</strong>：使用 global add/mean pooling 加上 attention pooling（重要算子如 matmul 赋更高权重），得到图级 embedding。</li>
<li><strong>多任务输出头</strong>：共享 GNN backbone，接三个 MLP 输出头分别预测：(1) 运行时延（ms），(2) 显存峰值（GB），(3) GPU 利用率（%）。</li>
</ul>
<p><strong>训练策略</strong>：</p>
<ul>
<li>loss = w₁ · MSE(latency) + w₂ · MSE(memory) + w₃ · MSE(utilization)，用 uncertainty weighting 自动平衡多任务 loss；</li>
<li>标签做 log 变换处理长尾（有些超大模型时延和显存是极端值）；</li>
<li>显存预测偏向高估（安全裕度），OOM 的代价比浪费大。</li>
</ul>
</div>

<div class="comp">
<div class="comp-t">模块三：Benchmark 数据集自动构建</div>
<p>通过<strong>运行时程序分析</strong>自动采集 (计算图, 性能指标) 对：</p>
<ul>
<li>插桩 PyTorch/ONNX Runtime，运行模型时自动记录每个算子的输入 shape、执行时间、显存分配。</li>
<li>覆盖 CNN（ResNet、EfficientNet）、Transformer（BERT、GPT、LLaMA 系列）、推荐模型（DLRM、Wide&Deep）等多模型族。</li>
<li>跨多个 batch size、序列长度、GPU 型号采集。</li>
<li>数据集规模 10W+ 条（图样本 × 配置组合）。</li>
</ul>
</div>

<div class="comp">
<div class="comp-t">模块四：Agentic 工作流编排</div>
<p>将预测信号用于 LLM Agent 系统的模型调度：</p>
<ul>
<li><strong>冷启动预部署</strong>：根据 Agent 的当前对话上下文和下一步可能调用的工具，提前预测需要的模型，将其权重从 CPU/NVMe 预加载到 GPU，避免用户等待模型加载。</li>
<li><strong>OOM 风险感知选卡</strong>：预测模型峰值显存，如果当前 GPU 剩余显存不够（加上安全裕度），选择更大的 GPU 或驱逐低优先级模型，避免运行时 OOM。</li>
<li><strong>显存复用与驱逐</strong>：根据预测的模型执行时长和显存需求，决定哪些模型可以常驻 GPU、哪些可以换出到 CPU，类似 Maestro 的分级缓存但用 GNN 预测替代启发式估计。</li>
</ul>
</div>

<h3>预期结果</h3>
<div class="grid">
<div class="gi"><div class="gv">10W+</div><div class="gl">Benchmark 数据规模</div></div>
<div class="gi"><div class="gv">GNN</div><div class="gl">一次前向预测多指标</div></div>
<div class="gi"><div class="gv">0 profiling</div><div class="gl">无需实际运行即可预测</div></div>
<div class="gi"><div class="gv">Agent</div><div class="gl">工作流编排应用</div></div>
</div>
<p class="text-muted" style="margin-top:0.8rem">（具体实验数据以论文最终版为准）</p>
</div>

<div class="card card-w">
<h3>SagePilot 高频问答</h3>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么用 GNN 而不是直接用模型参数量/FLOPs 做预测？参数量不够吗？</div>
<div class="qa-a"><p>参数量和 FLOPs 是<strong>粗粒度指标</strong>，无法捕捉关键的性能影响因素：(1) 算子类型差异——同样是 1GFLOP，matmul 是 compute-bound 且 GPU 利用率高，element-wise 是 memory-bound 且利用率低；(2) 内存访问模式——同样参数量的模型，访存密集型（如小算子多）和计算密集型（如大 matmul）性能差异巨大；(3) 模型结构影响——Attention 有不规则的 memory access pattern，和同等 FLOPs 的 conv 不可比。GNN 通过建模图结构和算子类型，能捕捉这些细粒度差异。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: ONNX 计算图丢失了哪些信息？怎么补偿？</div>
<div class="qa-a"><p>ONNX 静态图确实丢失了一些信息：(1) <strong>算子融合</strong>：推理引擎（TensorRT/TVM）会做 kernel fusion，但 ONNX 里是分开的节点，导致预测的 kernel launch 数不准。补偿方式：加入 fusion pattern 匹配特征或用实际执行的 kernel trace 做训练标签。(2) <strong>动态 shape</strong>：ONNX 的动态维度（如 batch size、seq_len）是符号化的，需要通过全局特征传入。(3) <strong>CUDA kernel 选择</strong>：cuBLAS/cutlass 会根据 shape 选择不同 kernel，同样的 matmul 在不同 shape 下效率差异大。补偿：把具体 shape 数值作为边特征，让模型学习 shape→kernel 性能的映射。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: GNN 怎么做跨 GPU 泛化？在 A100 上训的能用到 H100 上吗？</div>
<div class="qa-a"><p>GPU 型号通过 global feature 传入（SM 数、显存带宽、FP16 算力、L2 cache 大小等）。GNN 的消息传递是<strong>GPU 无关</strong>的——它学习的是算子之间的数据流和算子类型的影响，而 GPU 特征只影响最终输出头的 scale。所以在 A100 上训练的模型，只需要更换 global feature 中的 GPU 参数，就可以 zero-shot 迁移到 H100 上预测。如果在 H100 上有少量 profiling 数据，可以 few-shot fine-tune 校准输出头。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 多目标预测怎么平衡三个目标的 loss？显存预测的高估和低估怎么处理？</div>
<div class="qa-a"><p>使用 uncertainty weighting（Kendall 2018）自动学习每个任务的噪声参数 σ，动态调整 loss 权重。对于显存预测，使用<strong>非对称 loss（MSE + 不对称惩罚）</strong>：低估的惩罚是高估的 3 倍——因为低估导致 OOM（请求失败），高估只是浪费显存（可接受）。时延预测用对称 MSE，GPU 利用率预测用 Huber loss（对异常值鲁棒）。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 和 Maestro 的预测器有什么关系？</div>
<div class="qa-a"><p>Maestro 的预测是<strong>请求级</strong>的——给定 agent 角色和 prompt 上下文，预测单次 LLM 推理的输出 token 数和 KV 显存需求，用的是 LightGBM（表格数据、结构化+语义特征）。SagePilot 的预测是<strong>模型级</strong>的——给定 ONNX 计算图和部署配置，预测模型本身的运行时延和显存峰值，用的是 GNN（图结构数据）。两者粒度不同：Maestro 管的是"这次请求需要多少 KV"，SagePilot 管的是"这个模型跑起来需要多少资源"。SagePilot 的模型级预测可以为 Maestro 提供模型权重显存的基础估计，两者互补。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 和现有性能预测工作（Habitat、Daydream、Paleo）的区别？</div>
<div class="qa-a"><p>几个区别：(1) <strong>Paleo</strong>用解析模型（FLOPs/带宽）估算，需要手动建模每个算子，泛化差；(2) <strong>Habitat</strong>基于协同过滤，用同 GPU 上已有模型的性能做迁移，但冷启动需要至少一个 profiling；(3) <strong>Daydream</strong>用白盒模拟器，需要获取完整的 kernel 执行 profile，部署复杂。SagePilot 的优势：(a) 只需要 ONNX 计算图（导出即可，不需要实际执行）；(b) GNN 自动学习算子→性能的映射，不需要手动写算子模型；(c) 一次推理同时输出多个指标（时延/显存/利用率）；(d) 跨 GPU 泛化。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 10W+ 数据怎么采集的？覆盖了哪些模型？</div>
<div class="qa-a"><p>自动化采集 pipeline：(1) 从 HuggingFace 和 ONNX Model Zoo 拉取开源模型（约 500 个不同架构）；(2) 在多个 GPU（V100/A100/H100）上用 ONNX Runtime 插桩运行，记录每个配置（batch size、seq_len、precision）的真实性能；(3) 每个模型跑多个配置组合，生成约 10W+ 条 (graph, config) → (latency, memory, util) 样本。覆盖 CNN（ResNet/EfficientNet/MobileNet）、Transformer（BERT/GPT-2/BART/LLaMA）、推荐（DLRM/Wide&Deep）、RNN（LSTM/GRU）等主流模型族。</p></div>
</div>
</div>

## 关联模块

- `性能预测与建模`：树模型、特征工程、回归指标基础。
- `GPU 硬件与资源共享`：GPU 硬件指标（SM、带宽、显存）用于 global feature。
- `论文工作 / Maestro`：请求级预测，与 SagePilot 的模型级预测互补。
- `AI Agent`：Agentic 工作流编排的应用场景。

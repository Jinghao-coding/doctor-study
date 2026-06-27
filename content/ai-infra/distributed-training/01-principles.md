## 一句话结论

分布式训练并行策略的总公式是总 GPU 数由 DP、TP、PP 等维度相乘决定。
<div class="foundation-brief">
<h3>先把分布式训练看成四个问题</h3>
<p>分布式训练不是“卡越多越快”，而是在多张 GPU 之间拆分数据、模型、训练状态和通信。读这一页时先建立地图：模型放不下看显存拆分，单层太大看张量并行，层数太多看流水线并行，吞吐不够再扩大数据并行。</p>
<div class="foundation-map">
<div class="foundation-node"><strong>数据怎么拆</strong><span>DP/DDP 让每张卡处理不同 batch，通过 AllReduce 同步梯度。</span></div>
<div class="foundation-node"><strong>模型怎么拆</strong><span>TP 切层内矩阵，PP 切层间 stage，EP 切 MoE 专家。</span></div>
<div class="foundation-node"><strong>状态怎么拆</strong><span>ZeRO/FSDP 把参数、梯度、优化器状态从“每卡完整保存”变成“分片保存”。</span></div>
<div class="foundation-node"><strong>通信怎么放</strong><span>TP 优先节点内 NVLink，PP/DP 更适合跨节点，NCCL 决定通信效率。</span></div>
</div>
</div>

<div class="card card-m">
<h3>一张表先看清每种并行</h3>
<table>
<tr><th>策略</th><th>解决什么问题</th><th>核心通信</th><th>放置直觉</th><th>细节位置</th></tr>
<tr><td>DP / DDP</td><td>扩大吞吐，吃更多数据</td><td>每步 AllReduce 梯度</td><td>拓扑要求相对低，可跨节点</td><td>数据并行与梯度同步</td></tr>
<tr><td>TP</td><td>单层矩阵太大或单层计算太重</td><td>每层 AllGather / ReduceScatter</td><td>尽量放在同节点 NVLink/NVSwitch 内</td><td>张量并行与流水线并行</td></tr>
<tr><td>PP</td><td>模型层数太多，整模型放不进单卡</td><td>相邻 stage 传激活和梯度</td><td>可以跨节点，但要减少 stage 间跳数</td><td>张量并行与流水线并行</td></tr>
<tr><td>EP</td><td>MoE 专家分布在不同 GPU</td><td>All-to-All</td><td>需要高 bisection bandwidth</td><td>NCCL 与通信优化</td></tr>
<tr><td>ZeRO / FSDP</td><td>参数、梯度、优化器状态占显存太多</td><td>AllGather / ReduceScatter</td><td>通常作为 DP 的显存优化层</td><td>ZeRO / FSDP</td></tr>
</table>
</div>

<div class="card card-d">
<h3>选型路径</h3>
<p>分布式训练选型可以按“先能放下，再跑得快，再排得好”的顺序判断，不要一开始就堆所有并行策略。</p>
<div class="foundation-flow"><span>单卡能放下模型状态吗</span><span>不能就上 ZeRO/FSDP</span><span>单层仍太大就上 TP</span><span>层数太多就上 PP</span><span>吞吐不足再扩大 DP</span></div>
<table>
<tr><th>判断问题</th><th>优先方案</th><th>原因</th></tr>
<tr><td>模型状态放不下</td><td>ZeRO-2 / ZeRO-3 / FSDP</td><td>先减少每卡必须常驻的训练状态</td></tr>
<tr><td>单层参数或 attention 太大</td><td>TP</td><td>把层内矩阵切到多张卡上计算</td></tr>
<tr><td>层数太多、激活峰值高</td><td>PP + activation checkpointing</td><td>把不同层放到不同 stage，降低单卡常驻压力</td></tr>
<tr><td>模型能放下但吞吐不够</td><td>DP / DDP</td><td>复制模型副本，吃更多数据</td></tr>
<tr><td>MoE 专家很多</td><td>EP</td><td>专家分布式放置，按 token routing 通信</td></tr>
</table>
</div>

<div class="card card-s">
<h3>3D 并行的拓扑放置</h3>
<p>大模型训练常见组合是 TP × PP × DP。总 GPU 数满足：</p>
<div class="formula">$$\text{Total GPUs} = TP \times PP \times DP$$</div>
<p>放置原则比公式更重要：TP 的通信最频繁，优先限制在单节点高速互联内；PP 只在相邻 stage 传激活，通常可以跨节点；DP 每步同步梯度，频率低于 TP，可以放在最外层扩吞吐。</p>
<table>
<tr><th>并行维度</th><th>推荐位置</th><th>为什么</th></tr>
<tr><td>TP</td><td>节点内 4/8 卡</td><td>每层多次通信，跨节点延迟和带宽都容易成为瓶颈</td></tr>
<tr><td>PP</td><td>跨节点 stage</td><td>通信量主要是激活和梯度，低于 TP</td></tr>
<tr><td>DP</td><td>多条 pipeline 副本之间</td><td>每步同步一次梯度，适合做吞吐扩展</td></tr>
</table>
</div>

<div class="card card-w">
<h3>读这个模块的顺序</h3>
<p>先读本页总览，理解每种并行策略解决的问题；再读数据并行，掌握 AllReduce 和梯度同步；然后读 TP/PP，理解层内和层间切分；最后读 ZeRO/FSDP 与 NCCL，把显存和通信问题串起来。</p>
<ol>
<li><strong>只想建立框架</strong>：读本页总览和选型路径。</li>
<li><strong>要算通信量</strong>：读数据并行与 NCCL 两个 Tab。</li>
<li><strong>要讲大模型训练配置</strong>：读 TP/PP 和 ZeRO/FSDP。</li>
<li><strong>要准备面试排障</strong>：读排障与面试计算题。</li>
</ol>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

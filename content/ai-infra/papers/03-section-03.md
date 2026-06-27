## 一句话结论

Maestro 与 DeepShare 互补——前者解决推理侧多 agent 调度、后者解决训练侧多租户管理，两者共享预测驱动调度、代价感知抢占、弹性资源管理和分层架构四个理念，可串成"用轻量预测为调度器提供前瞻信号"的统一研究叙事。
<div class="card card-s">
<h3>互补关系</h3>
<p>Maestro 解决<strong>推理侧</strong>的多 agent 调度，DeepShare 解决<strong>训练侧</strong>的多租户管理。一个完整的 GPU 集群需要同时支持训练和推理。</p>

<h3>共通设计理念</h3>
<table>
<tr><th>理念</th><th>Maestro</th><th>DeepShare</th></tr>
<tr><td>预测驱动调度</td><td>预测输出长度 → 内存管理 + 排队</td><td>预测运行时间 → 排序 + 抢占</td></tr>
<tr><td>代价感知抢占</td><td>量化降级代价 C_deg 选最小影响路径</td><td>量化抢占效率 E_j 考虑进度损失</td></tr>
<tr><td>弹性资源管理</td><td>CUDA VMM 3× 超配</td><td>DRA 弹性配额借用</td></tr>
<tr><td>分层架构</td><td>全局调度器 + 节点运行时</td><td>全局调度器 + 节点 DaemonSet</td></tr>
</table>

<h3>自我介绍中的论文定位</h3>
<div class="comp">
<p>我的研究聚焦于 <strong>GPU 集群的资源调度与性能预测</strong>，在训练和推理两个互补场景下展开：</p>
<p><strong>DeepShare</strong>（IEEE Cluster 2026）解决多租户 GPU 集群中训练作业的调度。核心创新是配额保障度 QAD，统一驱动弹性配额管理、预测性调度和干扰感知合用，在 219 GPU 的 K8s 集群上实现 70.58% GPU 利用率和 93% QoS 合规率。</p>
<p><strong>Maestro</strong>（ICDCS 2026）面向 LLM 多智能体系统的推理调度。核心挑战是输出长度不确定性和多模型内存压力。设计了两阶段预测器加 CUDA VMM 超配加 SRTF 调度，在 64 块 A100 上将 SLO 达成率提升 23.6 个百分点。</p>
<p>贯穿核心能力：<strong>用轻量预测模型为调度器提供前瞻性信号，再设计弹性资源管理和抢占策略来利用这些信号。</strong></p>
</div>

<h3>与工业界系统的区别</h3>
<table>
<tr><th>对比对象</th><th>区别</th></tr>
<tr><td>vLLM / SGLang</td><td>它们是单节点推理引擎，Maestro 在其之上做多模型管理和跨节点调度</td></tr>
<tr><td>Volcano</td><td>面向 Gang scheduling，DeepShare 在配额弹性、干扰感知、运行时间预测方面做了增强</td></tr>
<tr><td>Orca / FastServe</td><td>它们关注单模型的迭代级调度，Maestro 关注多模型多 agent 的工作流级调度</td></tr>
</table>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

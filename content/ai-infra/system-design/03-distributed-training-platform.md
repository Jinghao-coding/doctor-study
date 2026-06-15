## 一句话结论

系统设计题这一节需要服务面试复习：先给结论，再把链路、机制、权衡和回答模板讲清楚。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 系统设计题 |
| 章节类型 | 系统设计类 |
| 解决问题 | 围绕多模型推理、多租户调度、分布式训练平台和 KV Cache 管理形成可复述设计题框架。 |
| 面试抓手 | 回答时先定范围，再讲核心链路，最后落到工程风险和面试追问。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心链路或关键机制，把概念映射到系统组件和资源消耗。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-s">
<h3>题目</h3>
<p>设计一个端到端的分布式训练平台，支持从提交任务到训练完成的全流程。</p>

<h3>设计要点</h3>
<ol>
<li><strong>任务抽象</strong>
  <ul>
  <li>用户提交训练配置：模型代码、数据路径、并行策略、资源需求</li>
  <li>平台生成 PodGroup + 配置 ConfigMap + Headless Service</li>
  </ul>
</li>
<li><strong>资源调度</strong>
  <ul>
  <li>Gang scheduling 保证所有 worker 同时启动</li>
  <li>拓扑感知：优先同节点（NVLink）→ 同机柜（高速交换）→ 跨机柜</li>
  </ul>
</li>
<li><strong>训练生命周期</strong>
  <ul>
  <li>初始化：参数同步 + NCCL 通信组建立</li>
  <li>训练循环：数据加载 → 前向 → 反向 → AllReduce → 更新</li>
  <li>Checkpoint：周期性异步保存到分布式存储</li>
  </ul>
</li>
<li><strong>容错机制</strong>
  <ul>
  <li>Worker 故障检测（心跳超时）</li>
  <li>弹性恢复：从最近 checkpoint 重启，支持 worker 数量变化</li>
  <li>GPU 健康检查：ECC 错误检测 + 自动标记不可用</li>
  </ul>
</li>
<li><strong>可观测性</strong>
  <ul>
  <li>训练指标：loss、throughput、GPU 利用率</li>
  <li>系统指标：网络吞吐、存储 IOPS、调度延迟</li>
  <li>日志和事件：统一收集到日志平台</li>
  </ul>
</li>
</ol>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">追问：如何优化大模型训练的启动时间？</div>
<div class="qa-a"><p>(1) <strong>镜像预热</strong>：在目标节点预拉取训练镜像（几十 GB），避免冷启动拉镜像。(2) <strong>模型缓存</strong>：预训练 checkpoint 缓存在节点本地 NVMe，不用每次从分布式存储下载。(3) <strong>NCCL 初始化优化</strong>：减少初始化时的全互联探测时间。(4) <strong>数据预加载</strong>：提前将训练数据加载到内存或本地 SSD。</p></div>
</div>
</div>

<hr class="div">

## 面试回答

**30 秒版：**

系统设计题这一节需要先定范围，再把机制和工程边界讲清楚。 按结论、链路、权衡、风险回答。

**2 分钟版：**

我会先说明这个问题在 系统设计题 里的位置，再拆核心链路：输入是什么、系统如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：吞吐和延迟、显存和计算、隔离和利用率、简单实现和生产稳定性之间如何取舍。最后用观测指标或排障路径收束，说明如何判断方案真的有效。

## 关联模块

- `GPU 硬件与资源共享`：提供 SM、HBM、NVLink、MIG/MPS、利用率诊断等底层直觉。
- `LLM 推理系统`：提供 Prefill/Decode、KV Cache、Serving Engine 和推理优化语境。
- `Kubernetes 核心`：提供调度、资源模型、控制器和扩展机制。
- `分布式训练 / 调度与集群`：提供多卡通信、队列、公平性、拓扑和容错背景。

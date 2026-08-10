## 一条生产决策链

```flow
给 workload 分类 | 在线推理、离线推理、训练、Notebook、系统任务
定义不可妥协约束 | P99、故障隔离、显存上限、吞吐、可抢占性
建立单任务画像 | 显存峰值、SM Active、HBM、PCIe、CPU/IO、运行时间
选择虚拟化机制 | 整卡 / MIG / MPS / Time-Slicing / HAMi
选择调度策略 | 独占、binpack、spread、干扰感知、拓扑感知
设置运行时保护 | 显存/算力上限、共享密度、在线降级与抢占
灰度与复测 | 单任务基线 -> 两任务共置 -> 压力/异常 -> 扩大范围
```

## 场景选型表

<table>
<thead><tr><th>场景</th><th>首选</th><th>原因</th><th>不建议</th></tr></thead>
<tbody>
<tr><td>核心在线推理，严格 P99</td><td>整卡或 MIG</td><td>性能和故障边界最可预测</td><td>直接 Time-Slicing；无监控的 MPS</td></tr>
<tr><td>同团队多个小模型推理</td><td>MPS</td><td>kernel 可并发，能限制显存和执行资源</td><td>把 MPS 当硬隔离卖给不可信租户</td></tr>
<tr><td>Notebook / 开发实验</td><td>Time-Slicing</td><td>配置简单，提高共享访问密度</td><td>承诺固定 1/N 性能</td></tr>
<tr><td>多团队细粒度显存/算力</td><td>HAMi</td><td>支持 MiB/百分比声明和设备感知放置</td><td>忽略 HAMi-Core 兼容性与插件冲突</td></tr>
<tr><td>大训练或通信密集训练</td><td>整卡、拓扑感知分配</td><td>需要稳定 SM/HBM/NVLink，减少同卡干扰</td><td>为了表面利用率强行切碎</td></tr>
<tr><td>KV Cache / 权重弹性</td><td>CUDA VMM + 运行时准入</td><td>解决虚拟地址和物理显存页弹性</td><td>把 VMM 当算力虚拟化</td></tr>
</tbody>
</table>

## 生产架构怎么分层

<table>
<thead><tr><th>层次</th><th>组件</th><th>需要维护的状态</th></tr></thead>
<tbody>
<tr><td>设备发现</td><td>GPU Feature Discovery、DCGM、HAMi Device Plugin</td><td>型号、显存、MIG 状态、健康、拓扑</td></tr>
<tr><td>资源表达</td><td>NVIDIA Device Plugin、MIG profile、HAMi resources、DRA</td><td>资源名、容量、共享关系、设备属性</td></tr>
<tr><td>准入与调度</td><td>kube-scheduler、Scheduler Plugin、HAMi Scheduler</td><td>quota、剩余显存/算力、优先级、干扰画像</td></tr>
<tr><td>运行时执行</td><td>MIG、MPS server、CUDA driver、HAMi-Core、CUDA VMM</td><td>硬件实例、client 限制、内存映射</td></tr>
<tr><td>监控与回退</td><td>DCGM Exporter、业务指标、告警、抢占/迁移</td><td>P99、吞吐、SM/HBM、OOM、Xid、降级状态</td></tr>
</tbody>
</table>

面试时可以说：**Device Plugin 解决“怎么把设备交给 Pod”，不等于解决“共享后性能是否安全”；虚拟化方案必须和调度、监控、回退形成闭环。**

## 上线前验证矩阵

| 验证项 | 要证明什么 | 失败时怎么处理 |
|---|---|---|
| 单任务基线 | 虚拟化本身的固定开销 | 检查 context、driver、MPS/HAMi 注入 |
| 两任务共置 | SM/HBM/显存是否互补 | 调低共享密度或改 spread |
| 显存超限 | 限制是否真的生效 | 检查 MPS/HAMi runtime，必要时改 MIG |
| 延迟压力 | P95/P99 是否可接受 | 在线 workload 改整卡/MIG |
| 异常退出 | 是否共享故障域 | 加自动摘卡、重建 daemon、隔离节点池 |
| 节点重启 | MIG geometry/共享配置能否恢复 | 用 Operator/controller 声明式重建 |
| 监控归因 | 能否定位到 Pod/MIG/client | 补 DCGM、Pod annotation 和业务标签 |

## 论文项目怎么映射

论文部分只回答“为什么需要在基础机制上再加系统策略”。详细背景、算法和实验仍放在<a href="../papers/index.html">论文工作</a>页面。

<table>
<thead><tr><th>项目</th><th>使用的基础机制</th><th>机制本身缺什么</th><th>论文补了什么</th></tr></thead>
<tbody>
<tr><td><strong>DeepShare</strong></td><td>NVIDIA MPS + DCGM</td><td>MPS 能并发，但不知道哪两个作业适合共置，也不知道何时该保护欠保障租户</td><td>QAD、Random Forest 干扰预测、动态准入阈值、连续窗口在线降级</td></tr>
<tr><td><strong>ElastiCo</strong></td><td>MPS 执行资源限制 + CUDA VMM</td><td>固定 SM/显存比例无法追随训练和推理阶段变化</td><td>资源形态变换、影子定价、训推阶段感知的动态调整</td></tr>
<tr><td><strong>Maestro</strong></td><td>CUDA VMM</td><td>VMM 只提供映射能力，不知道每个 Agent stage 应预留多少 KV Cache</td><td>输出长度预测、准入控制、按需物理页映射和降级策略</td></tr>
</tbody>
</table>

这里不要混淆：

- DeepShare 的 GPU 共置依赖 MPS，但贡献不是“发明 MPS”，而是让共置服从租户保障和干扰闭环。
- ElastiCo 组合了算力和显存弹性，但 MPS/VMM 只是执行原语，策略来自资源形态与价格信号。
- Maestro 使用 CUDA VMM 管 KV Cache，不是把一张 GPU 虚拟成多个 Kubernetes GPU。
- HAMi 是可落地的开源平台方案，和论文里的自研策略可以互补，但当前项目没有宣称论文原型直接基于 HAMi。

## 面试设计题答法

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 让 10 个团队共享 100 张 GPU，你会怎么设计虚拟化方案？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">先分池</div><p>核心在线推理和大训练保留整卡/MIG 池；Notebook、离线推理进入共享池；不要让所有 workload 共用一种策略。</p></div>
<div class="qa-section"><div class="qa-section-title">再选机制</div><p>强 SLA 用 MIG；可信小 workload 用 MPS；低优研发用 Time-Slicing；需要任意显存/算力配比和异构统一管理时评估 HAMi。</p></div>
<div class="qa-section"><div class="qa-section-title">最后闭环</div><p>调度器维护 quota、拓扑和共享密度，DCGM 与业务指标检测干扰，超过阈值自动迁移、降级到独占或抢占低优任务。</p></div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不全部使用 HAMi 或全部使用 MIG？</div>
<div class="qa-a"><p>因为它们优化的目标不同。MIG 用固定硬件边界换稳定性，但会产生 profile 碎片；HAMi 用软件调度和运行时控制换细粒度与灵活性，但系统复杂度和隔离边界不同。生产平台通常按 workload 分池组合使用，而不是追求单一方案统一全部场景。</p></div>
</div>

## 常见误区

| 误区 | 正确理解 |
|---|---|
| 利用率最高的方案就是最好方案 | 还要同时看有效吞吐、P99、JCT、OOM、故障域和运维成本。 |
| 一个集群只能选一种 GPU 虚拟化 | 可以按节点池组合，但同一节点/设备的管理插件和 sharing method 要避免冲突。 |
| 论文机制可以替代底层 GPU 共享 | 论文策略建立在 MIG/MPS/VMM 等执行原语上，解决的是准入、调度和保障。 |
| 有显存配额就不会干扰 | SM、HBM、cache、PCIe、CPU/IO 仍可能竞争。 |

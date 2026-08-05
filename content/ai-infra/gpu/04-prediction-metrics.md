## 一句话结论

GPU 专题负责解释指标的物理含义和诊断价值；“性能预测与建模”专题负责把指标组织成特征与标签，训练模型、评估误差并做在线校准。两者连接但不重复。

## 指标归属边界

| 内容 | GPU 专题 | 性能预测专题 |
|---|---:|---:|
| GPU-Util、SM Active、Occupancy、Warp Stall 定义 | 负责 | 引用 |
| HBM、PCIe、NVLink、功耗与温度的诊断语义 | 负责 | 引用 |
| 哪些指标能说明 Compute/Memory/Communication Bound | 负责 | 引用 |
| 特征 X、标签 Y、训练集采样与数据清洗 | 简述 | 负责 |
| 解析模型、树模型、跨硬件泛化 | 链接 | 负责 |
| MAE/MAPE/P95、置信区间、安全裕度、Concept Drift | 链接 | 负责 |

## 从 GPU 指标到预测模型

```flow
工作负载静态特征 | Shape、Batch、Sequence、FLOPs、显存需求
硬件静态特征 | Peak FLOPS、HBM、SM 数、互联拓扑
运行时观测 | SM Active、HBM 吞吐、NCCL 时间、功耗
预测标签 | Step Time、Token/s、Peak Active Memory、MFU
模型治理 | 误差评估、校准、漂移检测、安全裕度
```

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不能只用 GPU-Util 预测性能？</div>
<div class="qa-a"><p>GPU-Util 主要表示采样窗口内是否有 Kernel 活动，缺少空间利用率、算术强度、显存带宽和通信信息。两个任务都可能是 100% GPU-Util，但一个吃满 Tensor Core，另一个只是在持续执行低效访存 Kernel，因此吞吐差异很大。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 指标和特征有什么区别？</div>
<div class="qa-a"><p>指标是对系统状态的度量；特征是经过定义、对齐和处理后提供给预测模型的输入。一个指标是否适合作为特征，还取决于采样窗口、是否泄漏未来信息、跨硬件是否可比以及线上是否稳定可得。</p></div>
</div>

## 关联模块

- 本专题的“性能指标体系”“利用率诊断与瓶颈分析”负责指标解释。
- `性能预测与建模`负责 X/Y 设计、模型训练、误差、泛化与在线校准。
- `论文项目`负责说明性能预测如何服务调度、合用和资源决策。

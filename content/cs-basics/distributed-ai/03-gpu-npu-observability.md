## 通用观测维度

| 维度 | 通用问题 | NVIDIA 示例 | 其他加速器需要映射的概念 |
|---|---|---|---|
| 身份 | 有几张卡、UUID/逻辑 ID 是什么 | `nvidia-smi -L` | 设备枚举、逻辑卡与物理卡关系 |
| 容量 | 显存/HBM 使用和峰值是多少 | memory used/free | HBM/Device Memory 容量 |
| 计算 | 计算单元是否持续执行有效工作 | SM Active、Tensor Core | AI Core/Vector Core 活跃度 |
| 带宽 | HBM、Host-Device 是否成为瓶颈 | HBM、PCIe Throughput | HBM 与互联吞吐 |
| 拓扑 | 卡、CPU、NIC 的距离如何 | `nvidia-smi topo -m` | PCIe/片间互联/NUMA 映射 |
| 通信 | Collective 时间和错误如何 | NCCL 时间、RDMA counters | 对应 Collective Library 与网络指标 |
| 健康 | 温度、功耗、错误和降频 | Xid、ECC、clock | 供应商错误码、健康状态、频率 |

## 观测原则

- 先看业务吞吐、延迟和任务进度，再解释硬件指标。
- 区分“设备忙”“计算单元吃满”“有效模型计算高效”三个概念。
- 跨厂商对比使用物理语义，不直接比较名称相似但口径不同的百分比。
- 工具输出必须记录采样窗口、设备 ID、驱动/固件版本和工作负载阶段。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么不能把不同厂商的 Utilization 直接比较？</div>
<div class="qa-a"><p>不同工具可能测量“任意 Kernel 活跃时间”“计算核心忙碌比例”或“某类矩阵单元使用率”，采样周期和聚合方式也不同。跨设备比较应回到 Token/s、Step Time、有效 FLOPs、HBM 吞吐和功耗等可解释量，并核对指标定义。</p></div>
</div>

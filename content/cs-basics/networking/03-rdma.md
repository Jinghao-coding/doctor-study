## 一句话结论

RDMA：绕过内核协议栈的内存访问 是 网络基础 的核心知识点，面试回答要先给结论，再说明机制边界、工程场景和常见误区。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 网络基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕 TCP/UDP、HTTP/gRPC/RPC、RDMA 和 GPUDirect 建立 AI Infra 网络答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心概念、系统链路或关键机制，把知识点映射到工程场景。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m"><h3>RDMA：绕过内核协议栈的内存访问</h3><p>RDMA 允许网卡直接读写远端主机内存，减少 CPU 参与、系统调用和数据拷贝，适合高吞吐、低延迟通信。AI 训练里的 NCCL、参数同步和高速存储访问都会受 RDMA 能力影响。</p></div>
<div class="card card-d"><h3>TCP RPC vs RDMA</h3><table><tr><th>维度</th><th>TCP RPC</th><th>RDMA</th></tr><tr><td>目标</td><td>可靠请求/响应、服务治理</td><td>低延迟、低 CPU、高吞吐内存搬运</td></tr><tr><td>CPU 参与</td><td>序列化、系统调用、协议栈</td><td>注册内存后由 NIC DMA</td></tr><tr><td>工程难点</td><td>超时、重试、负载均衡</td><td>QP、内存注册、驱动、拥塞控制</td></tr></table></div>
<div class="card card-s"><h3>RC / UC / UD</h3><table><tr><th>模式</th><th>含义</th><th>特点</th><th>场景</th></tr><tr><td>RC</td><td>Reliable Connected</td><td>可靠、有序、连接态</td><td>分布式训练、存储</td></tr><tr><td>UC</td><td>Unreliable Connected</td><td>连接态但不可靠</td><td>少见，上层自处理可靠性</td></tr><tr><td>UD</td><td>Unreliable Datagram</td><td>无连接、不可靠、开销低</td><td>控制消息、发现、广播</td></tr></table></div>
<div class="card card-m">
<h3>GPUDirect RDMA 数据路径</h3>
<p>AI 训练里最理想的跨机路径不是 GPU 先拷贝到 CPU 内存再发网络，而是 NIC 直接读写 GPU HBM。这样可以减少 host staging、CPU 内存带宽占用和额外拷贝。</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">源 GPU HBM</div><div class="flow-desc">梯度、参数分片或激活值在 GPU 显存中</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">本机 PCIe 路径</div><div class="flow-desc">GPU 到同 NUMA/同 PCIe root 下的 RDMA NIC</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">RDMA NIC</div><div class="flow-desc">网卡直接从 GPU memory 发起 DMA</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">IB/RoCE 网络</div><div class="flow-desc">经过交换机、拥塞控制和路由</div></div>
<div class="flow-step"><div class="flow-index">05</div><div class="flow-title">远端 GPU HBM</div><div class="flow-desc">远端 NIC 直接写入目标 GPU 显存</div></div>
</div>
<p>如果 GPU 和 NIC 跨 Socket，或者 GDR 不可用，路径可能退化成 GPU → CPU pinned memory → NIC → 网络 → CPU pinned memory → GPU。这会增加延迟、占用 CPU 内存带宽，并降低 NCCL 有效吞吐。</p>
</div>

## 面试回答

**30 秒版：**

03 rdma 是 网络基础 中的一个基础知识点，面试回答要先给结论，再说明机制、边界和工程场景。 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。

**2 分钟版：**

我会先说明这个知识点在 网络基础 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

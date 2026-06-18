## 一句话结论

网络基础要能从 socket API 讲到 TCP 状态机，再落到连接池、超时、反压和 RDMA/NCCL 为什么存在。三次握手确认双方收发能力和初始序列号，TIME_WAIT 保证可靠关闭。AI Infra 里分布式训练通信慢要分应用、GPU 拓扑、网络和系统四层排查；RDMA/InfiniBand/NCCL 的存在就是为了绕过传统 TCP/IP 的内核协议栈、CPU copy 和延迟瓶颈。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 操作系统基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕进程线程、调度、虚拟内存、IO、多路复用、死锁、观测和 AI Infra OS 问题建立系统基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## AI Infra 面试模块：网络基础与系统调用

网络基础连接分布式训练、推理服务、RPC、存储访问和控制面组件。面试回答要能从 socket API 讲到 TCP 状态，再扩展到连接池、超时、重试、反压和 RDMA/NCCL 为什么存在。

### 需要掌握

- TCP/IP 基础：三次握手、四次挥手、拥塞控制、流量控制。
- socket 编程流程：socket、bind、listen、accept、connect、read/write、close。
- listen backlog、SYN queue、accept queue：半连接和全连接队列过小会导致连接失败或延迟升高。
- TIME_WAIT、CLOSE_WAIT：TIME_WAIT 用于可靠关闭和旧报文消散；CLOSE_WAIT 常说明应用未 close。
- TCP keepalive、Nagle、reuseaddr/reuseport：分别影响连接保活、小包聚合和端口复用。
- 网络收发包路径：网卡、DMA、硬中断/软中断、协议栈、socket buffer、用户态。
- epoll 在网络服务中的使用。

### AI Infra 相关关注点

- 分布式训练通信瓶颈可能来自带宽、延迟、拥塞、丢包、网卡队列、PCIe/NUMA 拓扑、NCCL 算法选择。
- RDMA、InfiniBand、RoCE、NCCL 解决的是传统 TCP/IP 在内核协议栈、CPU copy、延迟和吞吐上的瓶颈。
- 推理服务要关注连接数、长连接、连接池、超时、重试、限流和熔断。
- 大模型服务中的流式输出需要处理慢客户端、发送缓冲区、反压和请求取消。

### 高频问题

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: TCP 三次握手和四次挥手过程是什么？</div>
<div class="qa-a"><p>三次握手是客户端 SYN、服务端 SYN+ACK、客户端 ACK，用于确认双方收发能力和初始序列号。四次挥手是主动关闭方 FIN、被动方 ACK，被动方处理完剩余数据后 FIN，主动方 ACK 并进入 TIME_WAIT。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: TIME_WAIT 为什么存在？过多怎么办？</div>
<div class="qa-a"><p>TIME_WAIT 用于确保最后一个 ACK 能被对端收到，并让旧连接残留报文自然消失。过多时先判断是否短连接过多，可通过连接池、长连接、HTTP keepalive、端口范围调整和合理复用缓解，不能简单粗暴关闭安全机制。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: epoll 的 LT 和 ET 模式有什么区别？</div>
<div class="qa-a"><p>LT 是水平触发，只要 fd 仍然可读/可写就会反复通知；ET 是边缘触发，只在状态变化时通知，要求非阻塞 fd 并一次读到 EAGAIN，否则可能遗漏事件。ET 通知少但编程要求更高。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 分布式训练通信慢，可能从哪些层面排查？</div>
<div class="qa-a"><p>从应用看 batch、梯度大小、通信算法、NCCL 日志；从 GPU 拓扑看 NVLink/PCIe、跨 NUMA、GPU affinity；从网络看带宽、丢包、拥塞、RoCE PFC/ECN、网卡错误；从系统看 CPU 辅助线程、软中断、IRQ 亲和和容器资源限制。</p></div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

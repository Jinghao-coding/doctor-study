## 一句话结论

RPC 是远程调用的「语义抽象」（方法、参数、返回值、超时、重试、负载均衡），HTTP/gRPC 只是它的「承载方式」，两者不在一个层面；理解 RPC 要看清它的 CPU 开销分布——序列化、系统调用、协议栈、重试，每一块都有对应优化（Protobuf/零拷贝、batch/io_uring、内核调优/RDMA、deadline+幂等+退避）。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 网络基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕 TCP/UDP、HTTP/gRPC/RPC、RDMA 和 GPUDirect 建立 AI Infra 网络答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>HTTP、gRPC 与 RPC</h3><p>RPC 是远程调用抽象，HTTP/gRPC 是常见承载方式。面试要区分“调用语义”和“网络协议”：RPC 关心方法、参数、返回值、超时、重试、负载均衡；底层可能走 HTTP/1.1、HTTP/2、TCP 或其他协议。</p></div>
<div class="card card-d"><h3>RPC 链路 CPU 开销</h3><table><tr><th>阶段</th><th>开销</th><th>优化</th></tr><tr><td>序列化/反序列化</td><td>CPU 与内存分配</td><td>Protobuf、对象复用、零拷贝 buffer</td></tr><tr><td>系统调用</td><td>用户态/内核态切换</td><td>batch、io_uring、连接复用</td></tr><tr><td>协议栈</td><td>TCP/IP 处理、中断</td><td>内核调优、RSS/RPS、RDMA</td></tr><tr><td>重试</td><td>放大流量</td><td>deadline、幂等、退避、熔断</td></tr></table></div>
<div class="qa" onclick="this.classList.toggle('open')"><div class="qa-q">Q: RPC 超时和重试怎么设计？</div><div class="qa-a"><p>先设置端到端 deadline，再把预算分配给下游调用；重试必须要求幂等或有去重机制，并使用指数退避和 jitter，避免在故障时形成重试风暴。</p></div></div>

## 面试回答

**30 秒版：**

RPC 是远程调用的语义抽象，关心方法、参数、返回值、超时、重试、负载均衡；HTTP/1.1、HTTP/2、gRPC 只是它的承载方式。面试要分清「调用语义」和「网络协议」两层。落到性能，RPC 的 CPU 开销主要在序列化反序列化、系统调用、协议栈处理和重试放大，每块都有对应优化手段。

**2 分钟版：**

RPC 是远程调用抽象，把跨网络调一个远端方法包装成像调本地函数一样，它关心的是方法、参数、返回值、超时、重试、负载均衡这些调用语义；而 HTTP/1.1、HTTP/2、TCP 是底层承载协议，gRPC 就是跑在 HTTP/2 上的一种 RPC 实现。所以回答要把这两层分开，不能混。从性能视角拆 RPC 链路的 CPU 开销：序列化/反序列化耗 CPU 和内存分配，优化用 Protobuf、对象复用、零拷贝 buffer；系统调用带来用户态内核态切换，优化靠 batch、io_uring、连接复用；协议栈本身有 TCP/IP 处理和中断开销，可以做内核调优、RSS/RPS 甚至上 RDMA；重试会放大流量，必须配 deadline、幂等或去重、指数退避加 jitter，否则故障时形成重试风暴。超时重试的设计原则是先定端到端 deadline，再把预算分配给各下游调用，重试前提是幂等。这些在 AI Infra 里直接对应推理服务和参数同步的 RPC 链路，序列化和协议栈开销往往是吞吐瓶颈，高性能场景会用 RDMA 绕开内核协议栈。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

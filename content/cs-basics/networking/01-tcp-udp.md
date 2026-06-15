## 一句话结论

TCP 与 UDP 的核心区别 是 网络基础 的核心知识点，面试回答要先给结论，再说明机制边界、工程场景和常见误区。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 网络基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕 TCP/UDP、HTTP/gRPC/RPC、RDMA 和 GPUDirect 建立 AI Infra 网络答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心概念、系统链路或关键机制，把知识点映射到工程场景。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m"><h3>TCP 与 UDP 的核心区别</h3><table><tr><th>维度</th><th>TCP</th><th>UDP</th></tr><tr><td>连接</td><td>面向连接</td><td>无连接</td></tr><tr><td>可靠性</td><td>重传、有序、流控、拥塞控制</td><td>不保证可靠和有序</td></tr><tr><td>延迟/开销</td><td>开销更高</td><td>开销更低</td></tr><tr><td>场景</td><td>HTTP/gRPC、数据库、可靠 RPC</td><td>DNS、实时音视频、QUIC 底层</td></tr></table></div>
<div class="card card-s"><h3>面试重点</h3><p>TCP 不是“永远可靠”，而是通过确认、重传、窗口、拥塞控制尽力提供可靠字节流。真实系统还要处理超时、半开连接、队头阻塞、连接池和重试风暴。</p></div>

<div class="card card-m">
<h3>三次握手：建立连接</h3>
<p>三次握手的本质是<strong>双方各确认一次对方的收发能力</strong>，并同步初始序列号（ISN）。少一次就无法保证双向通道都可用。</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">SYN</div><div class="flow-desc">客户端发 SYN，seq=x，进入 SYN_SENT</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">SYN+ACK</div><div class="flow-desc">服务端回 SYN+ACK，seq=y, ack=x+1，进入 SYN_RCVD</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">ACK</div><div class="flow-desc">客户端回 ACK，ack=y+1，双方进入 ESTABLISHED</div></div>
</div>
<div class="qa-summary">为什么不是两次：两次握手无法确认客户端的接收能力，且历史失效的 SYN 重复到达会导致服务端建立无效连接。</div>
</div>

<div class="card card-d">
<h3>四次挥手与 TIME_WAIT</h3>
<p>关闭连接需要四次，是因为 TCP 全双工，每个方向都要单独关闭：一方 FIN 只表示“我没有数据要发了”，但对端可能还有数据，所以 ACK 和对端 FIN 通常不能合并。</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">FIN</div><div class="flow-desc">主动方发 FIN，进入 FIN_WAIT_1</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">ACK</div><div class="flow-desc">被动方回 ACK，主动方进入 FIN_WAIT_2</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">FIN</div><div class="flow-desc">被动方数据发完后发 FIN，进入 LAST_ACK</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">ACK</div><div class="flow-desc">主动方回 ACK，进入 TIME_WAIT（2MSL）后关闭</div></div>
</div>
</div>
<div class="card card-w"><h3>TIME_WAIT 为什么存在 / 为什么有时危险</h3><p>主动关闭方停留在 TIME_WAIT（默认 2MSL）有两个目的：<strong>① 保证最后一个 ACK 能可靠到达</strong>（丢了可重发）；<strong>② 让本连接的旧报文在网络中自然消亡</strong>，避免污染新连接。</p><p>风险：短连接高并发场景（如压测、未用连接池的 RPC 客户端）会堆积大量 TIME_WAIT，耗尽本地端口。工程上优先<strong>用长连接/连接池</strong>，而不是无脑开 <code>tcp_tw_reuse</code>。</p></div>

<div class="card card-s">
<h3>可靠性与流量/拥塞控制</h3>
<table>
<tr><th>机制</th><th>解决什么</th><th>关键点</th></tr>
<tr><td>序列号 + ACK + 重传</td><td>丢包、乱序</td><td>超时重传 RTO、快速重传（3 个重复 ACK）</td></tr>
<tr><td>滑动窗口（流控）</td><td>接收方处理不过来</td><td>由接收方 rwnd 通告，防止打爆对端缓冲</td></tr>
<tr><td>拥塞控制</td><td>网络链路拥塞</td><td>由发送方 cwnd 控制，防止打爆网络</td></tr>
</table>
<p>经典拥塞控制四阶段：<strong>慢启动</strong>（cwnd 指数增长）→ <strong>拥塞避免</strong>（线性增长）→ <strong>快速重传</strong> → <strong>快速恢复</strong>。现代内核默认多用 <code>CUBIC</code>，高带宽长肥管道（数据中心、跨洋）常用 <code>BBR</code>（基于带宽和 RTT 建模，而非纯丢包驱动）。</p>
</div>

<div class="card card-r">
<h3>队头阻塞（HoL Blocking）</h3>
<table>
<tr><th>层次</th><th>队头阻塞原因</th><th>缓解</th></tr>
<tr><td>TCP 层</td><td>字节流有序交付，一个包丢了后续包都得等重传</td><td>无法在 TCP 内根治</td></tr>
<tr><td>HTTP/1.1</td><td>一条连接同一时刻只能处理一个请求</td><td>多连接、pipelining（受限）</td></tr>
<tr><td>HTTP/2</td><td>应用层多路复用，但仍跑在单条 TCP 上，丢包仍触发 TCP HoL</td><td>换底层传输</td></tr>
<tr><td>HTTP/3 (QUIC)</td><td>基于 UDP，流之间相互独立，单流丢包不阻塞其他流</td><td>根治应用层 HoL</td></tr>
</table>
</div>

<div class="card card-m">
<h3>HTTP 协议演进</h3>
<table>
<tr><th>版本</th><th>底层</th><th>关键改进</th><th>遗留问题</th></tr>
<tr><td>HTTP/1.1</td><td>TCP</td><td>长连接 keep-alive、分块传输</td><td>队头阻塞、并发靠多连接</td></tr>
<tr><td>HTTP/2</td><td>TCP + TLS</td><td>二进制分帧、多路复用、头部压缩(HPACK)、Server Push</td><td>TCP 层队头阻塞仍在</td></tr>
<tr><td>HTTP/3</td><td>QUIC(UDP) + TLS1.3</td><td>无 TCP HoL、0-RTT 连接、连接迁移</td><td>UDP 被中间设备限速/拦截</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 TCP 是三次握手、四次挥手？</div>
<div class="qa-a"><p><strong>三次握手：</strong>建立连接要双向确认收发能力并同步序列号。客户端 SYN → 服务端 SYN+ACK（一次合并）→ 客户端 ACK，共三次。两次无法确认客户端接收能力，且可能被历史重复 SYN 误导。</p><p><strong>四次挥手：</strong>TCP 是全双工，关闭需要双向各自关闭。被动方收到 FIN 后通常还有数据要发，所以 ACK 和它自己的 FIN 不能合并，因此比握手多一次。</p><div class="qa-summary">面试口径：握手次数由“双向同步序列号 + 确认收发能力”决定；挥手多一次是因为全双工要分别关闭两个方向。</div></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 流量控制和拥塞控制有什么区别？</div>
<div class="qa-a"><p>流量控制（rwnd）由<strong>接收方</strong>主导，防止发送方发太快撑爆接收缓冲区，是端到端问题；拥塞控制（cwnd）由<strong>发送方</strong>主导，防止打爆中间网络链路，是全网共享资源问题。实际发送窗口取 <code>min(rwnd, cwnd)</code>。</p></div>
</div>

## 面试回答

**30 秒版：**

01 tcp udp 是 网络基础 中的一个基础知识点，面试回答要先给结论，再说明机制、边界和工程场景。 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。

**2 分钟版：**

我会先说明这个知识点在 网络基础 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

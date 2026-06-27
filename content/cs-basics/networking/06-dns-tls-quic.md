## 一句话结论

DNS 解析是网络请求第一步，K8s 中 ndots:5 触发 search domain 扩展是常见性能坑；TLS 1.3 将握手从 2-RTT 降到 1-RTT 并支持 0-RTT 恢复（但 0-RTT 有重放风险）；QUIC 基于 UDP 实现，解决了 TCP 队头阻塞问题，原生支持连接迁移和内置 TLS 1.3，是 HTTP/3 的底层协议。
<div class="card card-m">
<h3>DNS：域名系统</h3>
<p>DNS（Domain Name System）是互联网的电话簿：将域名翻译为 IP 地址。DNS 是一个分层的分布式数据库系统。</p>
<table>
<tr><th>概念</th><th>说明</th></tr>
<tr><td>层级结构</td><td>根域（.）→ 顶级域（TLD，如 .com/.cn/.org）→ 二级域（如 bytedance.com）→ 子域（如 www.bytedance.com）</td></tr>
<tr><td>递归查询</td><td>客户端 → Local DNS（如 8.8.8.8、运营商 DNS），要求返回最终答案（或报错）</td></tr>
<tr><td>迭代查询</td><td>Local DNS → 根 → TLD → 权威 DNS，每级返回下一级地址，Local DNS 自己一步步问</td></tr>
<tr><td>缓存机制</td><td>DNS 记录有 TTL（Time To Live），各级 DNS 缓存记录直到 TTL 过期，减少重复查询</td></tr>
</table>
<p><strong>常见 DNS 记录类型：</strong></p>
<table>
<tr><th>类型</th><th>用途</th></tr>
<tr><td>A</td><td>域名 → IPv4 地址</td></tr>
<tr><td>AAAA</td><td>域名 → IPv6 地址</td></tr>
<tr><td>CNAME</td><td>域名别名（指向另一个域名）</td></tr>
<tr><td>MX</td><td>邮件服务器地址</td></tr>
<tr><td>TXT</td><td>任意文本记录（SPF/DKIM/域名验证等）</td></tr>
<tr><td>SRV</td><td>服务定位（服务发现，如 LDAP/K8s headless service）</td></tr>
<tr><td>PTR</td><td>反向解析：IP → 域名</td></tr>
</table>
</div>

<div class="card card-w">
<h3>DNS 传输协议：UDP vs TCP</h3>
<p>DNS 主要使用 UDP 53 端口：简单、快速、无连接开销。但当响应报文超过 512 字节（原始 DNS 限制）时会被截断（TC 标志位 = 1），客户端需要改用 TCP 53 端口重新查询。现代 DNS 支持 EDNS0（Extension Mechanisms for DNS）将 UDP 响应大小提升到 4096 字节或更高。</p>
<p><strong>加密 DNS：</strong></p>
<table>
<tr><th>协议</th><th>端口</th><th>特点</th></tr>
<tr><td>DNS over HTTPS (DoH)</td><td>443 (HTTPS)</td><td>DNS 查询包装在 HTTPS 中，和普通 Web 流量混在一起，防 ISP 窃听/篡改，但也可能被企业防火墙阻拦</td></tr>
<tr><td>DNS over TLS (DoT)</td><td>853 (专用端口)</td><td>TLS 加密 DNS，专用端口容易被识别和封锁</td></tr>
</table>
<div class="qa-summary">传统 DNS 明文传输（UDP 53）容易被窃听和篡改（DNS 劫持/污染）；DoH/DoT 加密 DNS 保证隐私，但 DoH 因为跑在 443 端口更难被封锁。</div>
</div>

<div class="card card-r">
<h3>K8s 中 DNS 常见问题</h3>
<p>Kubernetes 集群中 CoreDNS 是最常见的性能瓶颈之一，面试常考。</p>
<p><strong>ndots:5 导致的 search domain 扩展问题：</strong></p>
<p>Pod 的 <code>/etc/resolv.conf</code> 默认配置：</p>
<pre><code class="language-text">nameserver 10.96.0.10
search default.svc.cluster.local svc.cluster.local cluster.local
options ndots:5</code></pre>
<p><code>ndots:5</code> 含义：域名中点（.）的数量少于 5 个时，会依次拼接 search domain 列表中的后缀尝试解析（最多 5-1=4 个？实际是 search 列表长度次），最后才用绝对域名（加末尾点）查询。例如查询 <code>my-service</code>：</p>
<ol><li><code>my-service.default.svc.cluster.local</code></li><li><code>my-service.svc.cluster.local</code></li><li><code>my-service.cluster.local</code></li><li><code>my-service</code>（绝对域名）</li></ol>
<p><strong>问题：</strong>每个外部域名（如 <code>api.example.com</code> 只有 2 个点）都会先触发 3-4 次无效的内部查询，再查外部域名。DNS 超时默认 5s，这些无效查询会显著增加延迟。</p>
<p><strong>解决方案：</strong></p>
<ul><li>使用 FQDN（全限定域名），末尾加 <code>.</code>（如 <code>api.example.com.</code>），跳过多余 search</li><li>调小 <code>ndots</code>（如 <code>ndots:2</code>）</li><li>使用 NodeLocal DNSCache（DaemonSet 节点级 DNS 缓存）减少到 CoreDNS 的跳数</li><li>优化 CoreDNS 配置和副本数</li></ul>
</div>

<div class="card card-m">
<h3>TLS 1.2 握手：2-RTT</h3>
<p>TLS（Transport Layer Security）是 HTTPS 的加密层，在 TCP 连接建立后进行握手协商密钥。TLS 1.2 需要 2-RTT 才能完成握手开始加密通信。</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">ClientHello</div><div class="flow-desc">客户端发：支持的 TLS 版本、密码套件列表、随机数 Client Random、可选 Session ID</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">ServerHello + 证书</div><div class="flow-desc">服务端回：选定密码套件、随机数 Server Random、证书（Certificate）、ServerKeyExchange（密钥交换参数，如 ECDHE）、ServerHelloDone</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">ClientKeyExchange + 切换密钥</div><div class="flow-desc">客户端：验证证书 → 生成 Pre-Master Secret（用服务端公钥加密或 ECDHE 计算）→ 发 ClientKeyExchange → ChangeCipherSpec（之后用协商密钥加密）→ Finished（握手完整性验证）</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">服务端切换密钥</div><div class="flow-desc">服务端：ChangeCipherSpec → Finished。握手完成，开始加密通信</div></div>
</div>
<p><strong>密钥计算：</strong>Client Random + Server Random + Pre-Master Secret → Master Secret → 对称加密密钥。RSA 密钥交换中 Pre-Master Secret 用服务端公钥加密（不支持前向保密）；ECDHE 中双方通过椭圆曲线 Diffie-Hellman 交换临时公钥，各自计算出相同的共享密钥（支持前向保密 PFS）。</p>
<div class="qa-summary">TLS 1.2 总共 2-RTT（TCP 三次握手后再加 2 个 TLS RTT = 总共 3-RTT 才能发加密请求）。RSA 密钥交换不支持 PFS，ECDHE 支持 PFS（即使服务端私钥泄露也不能解密历史流量）。</div>
</div>

<div class="card card-d">
<h3>TLS 1.3 握手：1-RTT 与 0-RTT</h3>
<p>TLS 1.3（RFC 8446，2018）是重大改进，将握手延迟减半，并大幅简化密码套件。</p>
<p><strong>1-RTT 握手（新连接）：</strong></p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">ClientHello + key_share</div><div class="flow-desc">客户端一次性发送：ClientHello + 猜测的密钥共享参数（key_share，支持的 ECDHE 组的临时公钥）+ 支持的密码套件。不需要等 ServerHello 就能发密钥材料</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">ServerHello + 证书 + Finished</div><div class="flow-desc">服务端：选择 key_share → 自己的 key_share + 证书 + CertificateVerify + Finished（全部加密！）。客户端收到后可以直接发应用数据</div></div>
</div>
<p><strong>关键改进：</strong></p>
<ul><li><strong>1-RTT 完成握手：</strong>客户端在第一条消息就带上密钥猜测，省去了 TLS 1.2 的 ServerKeyExchange/ClientKeyExchange 来回</li><li><strong>删除不安全的算法：</strong>移除 RSA 密钥交换（无 PFS）、移除 RC4/3DES/SHA-1 等弱密码套件，只支持 ECDHE/DHE 密钥交换 + AEAD 加密（AES-GCM/ChaCha20-Poly1305）</li><li><strong>Server 端消息加密：</strong>ServerHello 之后的所有消息（证书等）都是加密的，TLS 1.2 中证书是明文</li></ul>
<p><strong>0-RTT（PSK 恢复）：</strong></p>
<p>如果客户端之前连接过服务器并持有 PSK（Pre-Shared Key，通过 Session Ticket 或 PSK 建立），可以在第一个 ClientHello 中<strong>直接携带应用数据</strong>，不需要等握手完成，实现 0-RTT 数据发送。</p>
<div class="qa-summary">TLS 1.3 将新连接握手从 2-RTT 降到 1-RTT（总延迟从 TCP 3-RTT + TLS 2-RTT = 5-RTT → TCP 3-RTT + TLS 1-RTT = 4-RTT），重连 0-RTT 可以立即发数据。删除了所有不支持前向保密的密钥交换。</div>
</div>

<div class="card card-w">
<h3>0-RTT 的安全风险：重放攻击</h3>
<p>0-RTT 数据虽然快，但有重要安全缺陷：<strong>不提供重放保护（non-replayability）</strong>。</p>
<p>原因：0-RTT 数据是用 PSK 加密的，同一个 PSK 可以被重复使用；攻击者如果截获了 0-RTT 数据包，可以重放它，服务器可能重复执行操作（如重复转账、重复下单）。</p>
<p><strong>缓解措施：</strong></p>
<ul><li>0-RTT 数据只用于<strong>幂等请求</strong>（如 GET/HEAD），绝对不能用于 POST/PUT/DELETE 等非幂等操作</li><li>服务端记录 anti-replay token/nonce，拒绝重复的 0-RTT 数据</li><li>正常 1-RTT 握手完成后的流量是完全安全的，只有 0-RTT 早期数据有风险</li></ul>
</div>

<div class="card card-s">
<h3>TLS 会话恢复与终止</h3>
<p><strong>会话恢复（Session Resumption）：</strong></p>
<table>
<tr><th>机制</th><th>TLS 版本</th><th>原理</th></tr>
<tr><td>Session ID</td><td>TLS 1.2</td><td>服务端存储会话状态（Session ID → Master Secret），客户端复用 Session ID，服务端查缓存恢复</td></tr>
<tr><td>Session Ticket</td><td>TLS 1.2</td><td>服务端将会话状态加密成 blob（Session Ticket）发给客户端，客户端下次带回，服务端解密恢复。服务端无状态（类似 HTTP Cookie）</td></tr>
<tr><td>PSK (Pre-Shared Key)</td><td>TLS 1.3</td><td>统一的 PSK 机制，可以通过 Session Ticket 或外部建立（如 out-of-band），支持 0-RTT</td></tr>
</table>
<p><strong>TLS 终止位置：</strong></p>
<ul><li><strong>LB 层终止（SSL Offload）：</strong>最常见。负载均衡器做 TLS 解密，证书集中管理，后端用明文 HTTP（性能好但内网无加密）</li><li><strong>Sidecar 终止：</strong>Service Mesh（Istio/Linkerd）中，Envoy sidecar 做 mTLS，服务间通信加密</li><li><strong>应用层终止：</strong>应用自己处理 TLS，最安全但消耗应用 CPU</li></ul>
<p><strong>mTLS（双向 TLS）：</strong>不仅服务端出示证书，客户端也要出示证书，用于服务间身份认证。Service Mesh 中 Istio 通过 mTLS 实现服务到服务的零信任安全。</p>
</div>

<div class="card card-m">
<h3>QUIC：基于 UDP 的新一代传输协议</h3>
<p>QUIC（Quick UDP Internet Connections）由 Google 设计，IETF 标准化，运行在 UDP 之上，HTTP/3 就是 HTTP/2 over QUIC。</p>
<div class="qa-section"><div class="qa-section-title">为什么基于 UDP 而不是新协议或 SCTP？</div><ul><li><strong>中间盒兼容性：</strong>互联网上的 NAT/防火墙只普遍放行 TCP 和 UDP，新 IP 协议号会被大量设备丢弃</li><li><strong>用户空间实现：</strong>QUIC 在用户空间实现（不需要内核修改），可以快速迭代升级；TCP 实现在操作系统内核，升级极慢（设备换内核/系统要几年）</li><li><strong>UDP 就是最小特性的传输层：</strong>UDP 只提供端口复用，QUIC 在其上实现自己需要的可靠性、拥塞控制、流控、多路复用</li><li><strong>SCTP 虽然解决了队头阻塞，但不被 NAT/防火墙广泛支持，且同样在内核中难以迭代</strong></li></ul></div>
</div>

<div class="card card-d">
<h3>QUIC 核心特性</h3>
<table>
<tr><th>特性</th><th>说明</th></tr>
<tr><td>多路复用 Streams</td><td>一个 QUIC 连接包含多个独立的 byte stream，每个 stream 独立可靠、独立流量控制。单个 stream 丢包只重传该 stream，不阻塞其他 stream——<strong>从根本上解决了 TCP 层队头阻塞</strong></td></tr>
<tr><td>连接迁移</td><td>连接由 Connection ID 标识（不是传统的四元组 src_ip:src_port-dst_ip:dst_port）。客户端从 WiFi 切换到 4G（IP 变化）时，Connection ID 不变，连接可以继续不中断（对移动设备极其友好）</td></tr>
<tr><td>内置 TLS 1.3</td><td>QUIC 将 TLS 1.3 集成在握手层（不跑在 QUIC 之上），1-RTT 握手建立加密连接；支持 0-RTT 数据。QUIC 始终加密，没有明文版本</td></tr>
<tr><td>自建可靠性层</td><td>QUIC 在 UDP 上自己实现重传、拥塞控制（可插拔，默认 CUBIC 或 BBR）、流量控制</td></tr>
<tr><td>两级流控</td><td>per-stream 流控（每个 stream 有独立窗口）+ connection-level 流控（整个连接总窗口），比 TCP 单窗口更精细</td></tr>
<tr><td>改进的握手</td><td>QUIC 握手同时完成传输层和加密层握手，1-RTT 完成；0-RTT 支持重连时直接发数据。相比 TCP + TLS 1.2（3+2=5 RTT）快很多</td></tr>
</table>
</div>

<div class="card card-s">
<h3>HTTP/1.1 vs HTTP/2 vs HTTP/3 对比</h3>
<table>
<tr><th>维度</th><th>HTTP/1.1</th><th>HTTP/2</th><th>HTTP/3</th></tr>
<tr><td>底层传输</td><td>TCP</td><td>TCP + TLS</td><td>QUIC (UDP) + TLS 1.3</td></tr>
<tr><td>多路复用</td><td>无（一个连接同一时刻一个请求，靠多连接并发）</td><td>有（binary framing，多请求共享 TCP 连接）</td><td>有（QUIC streams）</td></tr>
<tr><td>队头阻塞</td><td>应用层 HoL（一个请求阻塞同连接其他请求）</td><td>TCP 层 HoL（丢包阻塞所有 stream）</td><td>无传输层 HoL（stream 独立丢包重传）</td></tr>
<tr><td>握手 RTT</td><td>TCP 3-RTT + TLS 1.2 2-RTT = 5-RTT</td><td>同 HTTP/1.1（HTTP/2 在 TLS 之上）</td><td>QUIC+TLS 1-RTT（总共 1-RTT，因为传输和加密握手合并）</td></tr>
<tr><td>连接迁移</td><td>不支持（四元组变了连接就断）</td><td>不支持（同 TCP）</td><td>支持（Connection ID）</td></tr>
<tr><td>加密</td><td>可选（HTTPS 才有）</td><td>实际生产中必需 TLS</td><td>始终加密（强制）</td></tr>
<tr><td>头部压缩</td><td>无（每次重复发完整 headers）</td><td>HPACK</td><td>QPACK（适配 QUIC 流）</td></tr>
</table>
<div class="qa-summary">HTTP/2 解决了 HTTP/1.1 的应用层队头阻塞（多路复用），但仍跑在 TCP 上，TCP 层队头阻塞无法解决；HTTP/3 基于 QUIC，彻底解决队头阻塞（每个 stream 独立）+ 更快握手 + 连接迁移。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: TLS 1.3 相比 1.2 改进了什么？</div>
<div class="qa-a">
<p><strong>1. 握手延迟减半：2-RTT → 1-RTT</strong></p>
<p>TLS 1.2 需要 ServerHello → ClientKeyExchange 两轮协商密钥材料；TLS 1.3 客户端在第一个 ClientHello 就带上 key_share（ECDHE 临时公钥），服务端直接回复自己的 key_share 并完成密钥协商，省去一个 RTT。加上 TCP 三次握手，完整建连从 5-RTT 降到 4-RTT。</p>
<p><strong>2. 0-RTT 恢复</strong></p>
<p>持有 PSK（会话票据）的重连客户端可以在第一个包里直接发送加密的应用数据，无需等待握手完成。</p>
<p><strong>3. 强制前向保密（PFS）</strong></p>
<p>删除了 RSA 静态密钥交换（不支持 PFS，如果服务端私钥泄露，历史流量都能解密），只保留 ECDHE/DHE 临时密钥交换。即使服务端长期私钥泄露，每次会话的临时密钥独立，无法解密历史流量。</p>
<p><strong>4. 删除不安全算法</strong></p>
<p>移除了 RC4、3DES、SHA-1、MD5、CBC 模式等弱算法，只保留 AEAD 加密套件（AES-GCM、ChaCha20-Poly1305）。</p>
<p><strong>5. 握手加密</strong></p>
<p>TLS 1.2 中 ServerHello 之后的证书等信息仍是明文传输（被动监听者可以看到你访问了哪个网站）；TLS 1.3 中 ServerHello 之后的所有消息都是加密的（但 SNI 仍然明文，ESNI/ECH 正在解决这个问题）。</p>
<p><strong>6. 密码套件大幅简化</strong></p>
<p>TLS 1.2 有数百种密码套件组合（密钥交换+加密+MAC+PRF 各选），TLS 1.3 简化到只有几个套件，减少协商复杂度和实现 bug。</p>
<div class="qa-summary">TLS 1.3 核心改进：1-RTT 握手（快一倍）+ 0-RTT 恢复 + 强制前向保密 + 删除弱算法 + 握手加密；代价是 0-RTT 有重放风险，需要服务端做幂等性保障。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: QUIC 为什么基于 UDP 而不是 SCTP 或新协议？</div>
<div class="qa-a">
<p>核心原因是<strong>互联网中间盒（middlebox）的现实约束</strong>和<strong>可部署性</strong>：</p>
<p><strong>1. 中间盒兼容性</strong></p>
<p>互联网上有大量 NAT 设备、防火墙、负载均衡器，它们大多只识别 TCP 和 UDP。一个新的 IP 协议号（如 SCTP 是 132）会被大量中间设备直接丢弃。UDP 端口普遍开放，几乎 100% 能通过。</p>
<p><strong>2. 用户空间可演进性</strong></p>
<p>TCP 实现在操作系统内核中，升级 TCP 意味着升级操作系统——从 Windows/Linux 内核补丁到终端用户更新，周期长达数年。QUIC 在用户空间实现（浏览器、CDN、客户端库），协议迭代只需要更新应用，不需要等待内核更新。这也是为什么 QUIC 能快速部署而 TCP 改进（如 Multipath TCP）推广很慢。</p>
<p><strong>3. SCTP 的问题</strong></p>
<p>SCTP（Stream Control Transmission Protocol，RFC 4960）确实原生支持多流和不队头阻塞，但：</p>
<ul><li>同样在内核中实现，部署和升级慢</li><li>NAT/防火墙穿透性差（协议号 132 不被普遍支持）</li><li>没有 TLS 集成，加密仍需在其上叠加</li><li>连接迁移等 QUIC 的移动性特性 SCTP 没有</li></ul>
<p><strong>4. UDP 足够「瘦」</strong></p>
<p>UDP 只提供端口复用和 best-effort 数据报，QUIC 需要的所有特性（可靠、有序、拥塞控制、流控、多路复用、加密、连接迁移）都可以在用户空间 UDP 上实现，不需要内核支持。</p>
<div class="qa-summary">QUIC 选 UDP 主要因为中间盒兼容性（UDP 普遍放行，新 IP 协议被丢弃）和用户空间可演进（不需要内核升级，快速迭代）；SCTP 虽然有多流但同样在内核、穿透性差、推广难。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: HTTP/3 解决了什么 HTTP/2 解决不了的问题？</div>
<div class="qa-a">
<p><strong>最核心：TCP 层队头阻塞（HoL Blocking）</strong></p>
<p>HTTP/2 虽然在应用层做了多路复用（一个 TCP 连接上跑多个请求/响应），但底层是 TCP 字节流。TCP 要求有序交付，一个包丢了，所有后续包（即使属于其他 HTTP/2 stream）都要等重传——这就是<strong>传输层队头阻塞</strong>。在丢包率高的网络（如 WiFi、蜂窝网络）中，HTTP/2 多路复用的效果甚至可能比 HTTP/1.1 多连接还差。</p>
<p>HTTP/3 (QUIC) 中每个 stream 是独立的，一个 stream 丢包只影响该 stream 的重传和排序，其他 stream 可以继续传输。</p>
<p><strong>其他 HTTP/2 无法解决的问题：</strong></p>
<p><strong>1. 连接建立慢：</strong>HTTP/2 跑在 TCP + TLS 上，需要 TCP 三次握手（1.5-RTT）+ TLS 握手（TLS 1.2 是 2-RTT，1.3 是 1-RTT），总共 3-4 RTT 才能发请求。QUIC 将传输握手和 TLS 握手合并，新连接 1-RTT 即可（0-RTT 恢复可立即发数据）。</p>
<p><strong>2. 连接迁移：</strong>HTTP/2 over TCP 连接由四元组标识，IP 变化（WiFi 切 4G）连接就断了；QUIC 用 Connection ID 标识连接，网络切换不中断，对移动设备用户体验提升显著。</p>
<p><strong>3. 连接迁移对 NAT 重绑定更鲁棒：</strong>NAT 设备可能重新映射端口（NAT rebinding），TCP 连接因此中断，QUIC 的 Connection ID 机制不受影响。</p>
<div class="qa-summary">HTTP/3（QUIC）解决 HTTP/2 的 TCP 层队头阻塞（QUIC stream 独立丢包不阻塞其他流）、握手慢（合并传输+TLS握手 1-RTT/0-RTT）、无连接迁移（Connection ID 支持网络切换不断连）三个根本问题。这三个问题 HTTP/2 因为依赖 TCP 无法在不换传输协议的情况下解决。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: DNS 在 K8s 中为什么慢？怎么优化？</div>
<div class="qa-a">
<p><strong>K8s DNS 慢的主要原因：</strong></p>
<p><strong>1. ndots:5 导致 search domain 扩展</strong></p>
<p>默认 ndots:5 意味着任何域名中点数少于 5 的查询都会先拼上 search domain 列表（<code>svc.cluster.local</code> 等）依次尝试，最后才查原始域名。访问外部域名时会产生多次无效查询，每次查询超时默认 5 秒。</p>
<p><strong>2. CoreDNS 单点/性能瓶颈</strong></p>
<p>所有 Pod 的 DNS 查询都发往 CoreDNS Service（ClusterIP），CoreDNS 副本不足或配置不当会成为瓶颈。conntrack 表满也会导致 DNS 丢包。</p>
<p><strong>3. 到 CoreDNS 多跳网络</strong></p>
<p>Pod → iptables/IPVS → CoreDNS Pod，每一跳都有延迟。</p>
<p><strong>优化方案：</strong></p>
<p><strong>1. 使用 FQDN 或调小 ndots</strong></p>
<pre><code class="language-yaml">dnsConfig:
  options:
    - name: ndots
      value: "2"</code></pre><p>访问外部服务用完整域名加末尾点（<code>api.example.com.</code>）跳过多余 search。</p>
<p><strong>2. NodeLocal DNSCache</strong></p>
<p>以 DaemonSet 在每个节点运行 DNS 缓存，Pod 的 DNS 查询先到节点本地缓存（169.254.x.x），命中直接返回，未命中才转发给 CoreDNS。减少到 CoreDNS 的跳数和压力。</p>
<p><strong>3. CoreDNS 扩容与优化</strong></p>
<ul><li>增加 CoreDNS 副本数（根据集群规模）</li><li>开启 CoreDNS cache 插件</li><li>配置 NodeLocal + CoreDNS 二级缓存架构</li></ul>
<p><strong>4. 应用侧连接池/DNS 缓存</strong></p>
<ul><li>应用层缓存 DNS 结果（JVM TTL、Go resolver 缓存、连接池复用长连接）</li><li>减少 DNS 查询频率</li></ul>
<p><strong>5. 检查 conntrack 表</strong></p>
<p>高并发下 nf_conntrack 表满会丢包，导致 DNS 超时：<code>sysctl net.netfilter.nf_conntrack_max</code> 调大。</p>
<div class="qa-summary">K8s DNS 慢的主因是 ndots:5 触发多余 search domain 查询 + CoreDNS 集中式瓶颈；优化：调小 ndots 或用 FQDN + NodeLocal DNSCache 本地缓存 + CoreDNS 扩容 + 应用层 DNS 缓存。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 0-RTT 有什么安全风险？</div>
<div class="qa-a">
<p>0-RTT 的安全风险核心是<strong>重放攻击（Replay Attack）</strong>。</p>
<p><strong>为什么会有重放风险：</strong></p>
<ul><li>0-RTT 数据使用 PSK（Pre-Shared Key）加密，PSK 来自之前的会话（Session Ticket）</li><li>与 1-RTT 握手不同，0-RTT 数据不包含双方新生成的随机 Nonce 交换，缺乏防重放的上下文</li><li>攻击者捕获了 0-RTT 数据包后，可以在另一个连接中重放（resend）同一个加密数据包，服务器用同一个 PSK 能解密并处理</li><li>这可能导致非幂等操作被重复执行：重复转账、重复下单、重复提交表单</li></ul>
<p><strong>1-RTT 之后的数据为什么安全：</strong>1-RTT 握手完成后，双方通过 (Client Hello + Server Hello) 交换了新的随机数，会话密钥是新鲜的，重放旧数据包密钥不对。0-RTT 数据是在握手中途发送的，没有这个新鲜度保证。</p>
<p><strong>缓解措施：</strong></p>
<ol><li><strong>0-RTT 只用于幂等请求：</strong>客户端只在 GET/HEAD/OPTIONS 等幂等方法使用 0-RTT 发送数据；POST/PUT/DELETE 等非幂等请求等 1-RTT 握手完成后再发</li><li><strong>服务端 anti-replay 机制：</strong>服务端记录 0-RTT 数据的唯一标识（nonce/timestamp），在窗口内拒绝重复的 0-RTT 数据。TLS 1.3 规范中服务端可以通过单飘带（single-use）ticket 或时间窗口来防重放</li><li><strong>客户端控制：</strong>应用层可以决定是否启用 0-RTT（不是必须），敏感操作禁用 0-RTT</li></ol>
<div class="qa-summary">0-RTT 的安全风险是重放攻击：攻击者可以重放捕获的 0-RTT 数据导致非幂等操作重复执行（因为没有双方新鲜随机数交换）。缓解：0-RTT 只发幂等请求（GET）+ 服务端 anti-replay 机制（记录 nonce 拒绝重复）。</div>
</div>
</div>

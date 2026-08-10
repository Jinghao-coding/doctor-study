<div class="card card-m">
<h3>HTTP/1.1 核心要点</h3>
<table><tr><th>特性</th><th>说明</th></tr>
<tr><td>持久连接</td><td>默认 Connection: keep-alive，一个 TCP 连接承载多个请求</td></tr>
<tr><td>管道化（Pipelining）</td><td>客户端可连续发多个请求不等响应，但服务端必须按序返回，仍有 HOL</td></tr>
<tr><td>队头阻塞（HOL）</td><td>一个请求的响应未返回前，同连接后续请求被阻塞（应用层 HOL）</td></tr>
<tr><td>并发方式</td><td>浏览器开 6 个 TCP 连接并发请求同一域名</td></tr>
<tr><td>头部冗余</td><td>每次请求重复发送大量相同 headers（User-Agent、Cookie 等），无压缩</td></tr>
<tr><td>请求模型</td><td>文本协议，明文可读，请求-响应模型，Server 不能主动推送</td></tr>
</table>
</div>

<div class="card card-d">
<h3>HTTP/2 核心改进</h3>
<ul>
<li><strong>二进制分帧（Binary Framing）：</strong>所有消息切成 binary frame（HEADERS/DATA/SETTINGS/WINDOW_UPDATE 等），不再是文本</li>
<li><strong>多路复用（Multiplexing）：</strong>一个 TCP 连接上并发交错多个 stream（请求/响应），stream 独立</li>
<li><strong>头部压缩（HPACK）：</strong>静态表+动态表+Huffman 编码压缩 headers，减少冗余</li>
<li><strong>Server Push：</strong>服务端可以主动推资源给客户端（实际使用较少，浏览器支持受限）</li>
<li><strong>流控（Flow Control）：</strong>per-stream 流量控制窗口（WINDOW_UPDATE frame）</li>
</ul>
<p><strong>仍然存在 TCP 层队头阻塞：</strong>一个 TCP 包丢失 → 所有 stream 等待重传，HTTP/2 解决了应用层 HOL 但传输层 HOL 还在（HTTP/3 解决）。</p>
</div>

<div class="card card-s">
<h3>gRPC：基于 HTTP/2 + Protobuf 的 RPC 框架</h3>
<table><tr><th>特性</th><th>说明</th></tr>
<tr><td>序列化</td><td>Protobuf（二进制，比 JSON 小 3-10 倍，快 20-100 倍）</td></tr>
<tr><td>传输层</td><td>HTTP/2，原生支持多路复用、双向流、头部压缩</td></tr>
<tr><td>调用模式</td><td>Unary（普通 RPC）、Server Streaming、Client Streaming、Bidirectional Streaming</td></tr>
<tr><td>IDL</td><td>.proto 文件定义接口，自动生成客户端/服务端代码</td></tr>
<tr><td>生态</td><td>拦截器（middleware）、deadline、负载均衡、健康检查、反射</td></tr>
<tr><td>K8s 生态</td><td>gRPC 原生支持，Envoy/Istio 做 L7 负载均衡（gRPC 需要 L7 因为多路复用）</td></tr>
</table>
<p><strong>gRPC vs REST：</strong></p>
<ul>
<li>gRPC 强类型、契约驱动（.proto 文件就是接口文档），Protobuf 高效，支持 streaming</li>
<li>REST 基于 HTTP 语义（GET/POST/PUT/DELETE），JSON 可读，工具链成熟，浏览器原生支持</li>
<li>AI Infra 中：模型服务推理 API（Triton、vLLM OpenAI-compatible API）常用 REST + JSON；服务间控制面/数据面通信常用 gRPC</li>
</ul>
</div>

<div class="card card-w">
<h3>RPC 链路开销与优化</h3>
<table><tr><th>阶段</th><th>开销来源</th><th>优化方向</th></tr>
<tr><td>序列化/反序列化</td><td>CPU + 内存分配（JSON 解析尤其重）</td><td>Protobuf/FlatBuffers、对象复用、零拷贝 buffer</td></tr>
<tr><td>系统调用</td><td>用户态/内核态切换（read/write/sendmsg）</td><td>batch、io_uring、连接复用、DPDK</td></tr>
<tr><td>协议栈</td><td>TCP/IP 内核处理 + 中断</td><td>内核调优、RSS/RPS/RFS、busy poll、RDMA</td></tr>
<tr><td>连接建立</td><td>TCP+TLS 握手 RTT</td><td>连接池、长连接、TLS 会话恢复、QUIC 0-RTT</td></tr>
<tr><td>重试/超时</td><td>故障时重试风暴放大流量</td><td>deadline 传播、幂等性、指数退避+jitter、熔断</td></tr>
</table>
</div>

<div class="card card-r">
<h3>常见状态码</h3>
<table><tr><th>状态码</th><th>含义</th><th>面试考点</th></tr>
<tr><td>200 OK</td><td>请求成功</td><td>—</td></tr>
<tr><td>301/302</td><td>永久/临时重定向</td><td>301 浏览器会缓存；302 不缓存</td></tr>
<tr><td>304 Not Modified</td><td>协商缓存命中</td><td>If-Modified-Since / ETag</td></tr>
<tr><td>400 Bad Request</td><td>请求参数错误</td><td>—</td></tr>
<tr><td>401 Unauthorized</td><td>未认证</td><td>缺少/无效身份凭证</td></tr>
<tr><td>403 Forbidden</td><td>无权限</td><td>认证通过但无权访问</td></tr>
<tr><td>404 Not Found</td><td>资源不存在</td><td>—</td></tr>
<tr><td>429 Too Many Requests</td><td>限流</td><td>Rate Limiting，Retry-After</td></tr>
<tr><td>500 Internal Server Error</td><td>服务端异常</td><td>未捕获异常</td></tr>
<tr><td>502 Bad Gateway</td><td>网关收到无效响应</td><td>后端挂了或返回异常</td></tr>
<tr><td>503 Service Unavailable</td><td>服务不可用</td><td>过载/维护，Retry-After</td></tr>
<tr><td>504 Gateway Timeout</td><td>网关超时</td><td>后端处理超时</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: REST 和 RPC 怎么选？</div>
<div class="qa-a"><p><strong>REST 适合：</strong>公开 API、面向浏览器/第三方、资源 CRUD 操作为主、需要人类可读调试。<strong>RPC（gRPC）适合：</strong>内部服务间通信、高性能要求、复杂调用模式（streaming、双向流）、强类型契约、多语言支持。AI Infra 场景：控制面（服务注册发现、配置下发、调度）常用 gRPC；推理 API（OpenAI-compatible）对外常用 REST/HTTP + JSON，对内也有 gRPC（如 Triton gRPC endpoint 性能更高）。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: HTTP/2 多路复用为什么还会被阻塞？</div>
<div class="qa-a"><p>HTTP/2 解决了<strong>应用层队头阻塞</strong>（不再需要等前一个请求响应完再发下一个），但底层还是 TCP，TCP 是字节流协议，要求有序交付。当一个 TCP 包丢失时，接收方 TCP 栈必须缓存后续到达的 out-of-order 包，等待重传后才能按序交给应用层——这个等待对 HTTP/2 的所有 stream 都生效，哪怕丢的那个包属于其他 stream。丢包率 1% 时 HTTP/2 性能可能比 HTTP/1.1 多连接还差。HTTP/3 基于 QUIC（UDP），每个 stream 独立，丢包不影响其他 stream，彻底解决传输层 HOL。</p></div>
</div>

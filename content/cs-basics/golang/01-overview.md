<div class="card card-m">
<h3>Go 的设计哲学</h3>
<p>Go 的设计目标是解决 Google 内部大规模软件工程的痛点：编译慢、依赖混乱、并发编程复杂、工程师水平参差不齐。它刻意放弃了很多语言特性，追求「足够好」的工程效率。</p>
<table>
<tr><th>设计原则</th><th>具体体现</th><th>解决的问题</th></tr>
<tr><td>简单少即是多</td><td>25 个关键字、没有继承、没有泛型（1.18 前）、没有异常</td><td>降低学习成本，代码风格统一，新人一周可上手</td></tr>
<tr><td>组合优于继承</td><td>struct embedding、interface 鸭式类型</td><td>避免继承层次过深，代码更易重构</td></tr>
<tr><td>并发是一等公民</td><td>goroutine + channel、CSP 模型</td><td>语言层面支持高并发，不用回调地狱</td></tr>
<tr><td>快速编译</td><td>依赖分析清晰、禁止循环依赖、包级别编译</td><td>大型项目编译速度快，开发体验好</td></tr>
<tr><td>内置工具链</td><td>gofmt、go test、go vet、go mod、pprof</td><td>统一工程规范，不用纠结选什么工具</td></tr>
</table>
<div class="qa-summary">Go 不是追求语言特性最多的语言，而是追求团队协作效率最高、大规模工程最稳的语言。</div>
</div>

<div class="card card-d">
<h3>Go 适用场景</h3>
<table>
<tr><th>场景</th><th>为什么选 Go</th><th>代表项目</th></tr>
<tr><td>云原生基础设施</td><td>单二进制部署、并发强、资源占用低、容器友好</td><td>Docker、Kubernetes、Etcd、Prometheus</td></tr>
<tr><td>微服务/API 网关</td><td>HTTP/RPC 性能好、goroutine 处理高并发连接</td><td>Go-kit、Kratos、Gin、Hertz</td></tr>
<tr><td>CLI/DevOps 工具</td><td>交叉编译简单、跨平台、无依赖</td><td>Hugo、Terraform、GitHub CLI、kubectl</td></tr>
<tr><td>分布式中间件</td><td>网络库成熟、并发模型适合代理/存储</td><td>TiDB、InfluxDB、CockroachDB、NSQ</td></tr>
<tr><td>高并发网络代理</td><td>goroutine-per-connection 模型简单高效</td><td>Traefik、Envoy（部分）、FRP</td></tr>
</table>
</div>

<div class="card card-w">
<h3>Go 不适合的场景</h3>
<table>
<tr><th>场景</th><th>为什么不选 Go</th><th>替代语言</th></tr>
<tr><td>HPC/数值计算</td><td>GC 停顿、编译器优化不如 C++/Fortran、SIMD 支持弱</td><td>C++、Fortran、Julia</td></tr>
<tr><td>GPU 计算/CUDA</td><td>没有官方 CUDA 绑定、生态薄弱</td><td>CUDA C++、Python</td></tr>
<tr><td>低延迟实时交易</td><td>GC 虽然低延迟但仍有 STW，不能保证亚微秒级</td><td>C++、Rust</td></tr>
<tr><td>GUI 桌面应用</td><td>原生 GUI 框架不成熟</td><td>C++、Rust、Electron</td></tr>
<tr><td>前端 Web 开发</td><td>WASM 生态尚在发展，不如 JS/TS 成熟</td><td>TypeScript、Rust（WASM）</td></tr>
</table>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Go vs Python 做 AI 后端怎么选？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从性能、生态、部署、团队三个维度对比，结论是「分层选型」而不是二选一。</p>
<div class="qa-section">
<div class="qa-section-title">选 Python 的场景</div>
<p>模型推理封装、数据处理 pipeline、Notebook 实验、快速原型验证。Python 有 PyTorch/TensorRT 完整生态，算法团队效率最高。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">选 Go 的场景</div>
<p>高并发 API 网关、请求调度、服务编排、缓存代理、日志采集、分布式训练的控制面。Go 处理 10k QPS 只用几个 goroutine，内存占用是 Python 的 1/10，单二进制部署到 K8s 极其方便。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">典型架构</div>
<p>Go 做入口层（鉴权、限流、路由、batch 合并）→ Python/C++ 做推理层（TensorRT/vLLM）→ Go 做监控日志层。这是目前大多数 AI 公司的标准架构。</p>
</div>
<div class="qa-summary">面试口径：AI 后端不是二选一，Go 做基础设施和高并发入口，Python 做模型推理，各司其职。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Go 的值类型和 Java 的引用类型有什么本质区别？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>核心是「传递的到底是什么」以及「修改是否会影响原对象」。</p>
<div class="qa-section">
<div class="qa-section-title">Go 的值语义</div>
<p>Go 中所有赋值和参数传递默认都是<strong>值拷贝</strong>：int、string、struct、array 是值类型，传参会复制整个对象；slice、map、channel、interface、pointer 看起来像引用，本质是「包含指向底层数据指针的结构体」，拷贝的是这个 header 结构体，所以通过它们能修改底层数据。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">Java 的引用语义</div>
<p>Java 中除了基本类型（int、long 等），所有对象都是引用传递，赋值只是拷贝引用地址，方法内修改对象字段会影响原对象；但如果是<code>obj = newObj</code>这种重新赋值，不会影响外部引用。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">关键区别举例</div>
<pre><code class="language-go">// Go
type User struct{ Name string }
func f(u User) { u.Name = "changed" }  // 修改的是拷贝，外部不变
func f(u *User) { u.Name = "changed" } // 传指针，外部变

// Java
void f(User u) { u.name = "changed"; } // 修改对象字段，外部变
void f(User u) { u = new User(); }    // 重新赋值，外部不变
</code></pre>
</div>
<div class="qa-summary">面试口径：Go 默认值传递，想修改原对象必须显式传指针；Java 对象默认引用传递，这是两种语言最重要的语义差异之一。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么很多云原生项目（Docker/K8s/Etcd）都用 Go 写？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>不是因为 Go 性能最高，而是综合工程效率、部署、并发、生态的最优解。</p>
<div class="qa-section">
<div class="qa-section-title">部署优势</div>
<p>静态编译成单二进制，<code>FROM scratch</code> 就能做镜像，没有 JVM/Python 依赖，镜像大小几 MB vs Java 的几百 MB，冷启动快。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">并发模型适合云原生</div>
<p>云原生组件大多是 I/O 密集型（watch API、处理 HTTP 请求、代理转发），goroutine 模型让每个连接一个 goroutine 成为可能，代码写起来像同步但性能是异步的。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">工程文化契合</div>
<p>gofmt 统一代码风格、内置 test/bench/pprof、社区推崇简单透明，K8s 生态早期就是 Google 内部 Borg/Omega 的 Go 实现延伸。</p>
</div>
<div class="qa-summary">面试口径：云原生选 Go 是「部署简单 + 并发够用 + 工程效率高 + 社区生态」的综合选择，不是单纯看性能。</div>
</div>
</div>

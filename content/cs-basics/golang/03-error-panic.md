## 一句话结论

Go 错误处理哲学是**error as value（错误是值）**：用普通值返回错误，调用者必须显式处理；panic 只用于真正不可恢复的程序错误，defer 在函数返回前按 LIFO 执行；面试必考点是 `fmt.Errorf %w` 错误包装、`errors.Is/As`、defer 与 return 的执行顺序。

<div class="card card-m">
<h3>error 是一个接口</h3>
<p>Go 内置的 error 就是一个只包含 Error() 方法的 interface，这是最朴素的错误处理设计：</p>
<pre><code class="language-go">type error interface {
    Error() string
}
</code></pre>
<p>创建错误最常用的方式：</p>
<pre><code class="language-go">// 1. 简单字符串错误（最常用）
err := errors.New("something went wrong")

// 2. 格式化错误信息
err := fmt.Errorf("failed to read file %s: %w", filename, err)

// 3. 自定义错误类型（需要携带额外信息时）
type MyError struct {
    Code    int
    Message string
    Cause   error
}
func (e *MyError) Error() string {
    return fmt.Sprintf("code=%d msg=%s: %v", e.Code, e.Message, e.Cause)
}
</code></pre>
</div>

<div class="card card-s">
<h3>错误包装与 errors.Is/As/Unwrap</h3>
<p>Go 1.13 引入了错误包装（error wrapping），用 <code>%w</code> 格式化动词可以把底层错误包装到新错误中，形成错误链。</p>
<table>
<tr><th>函数</th><th>作用</th><th>示例</th></tr>
<tr><td><code>fmt.Errorf("...: %w", err)</code></td><td>包装错误，保留原始错误链</td><td><code>return fmt.Errorf("query db: %w", err)</code></td></tr>
<tr><td><code>errors.Is(err, target)</code></td><td>判断错误链中是否包含 target 错误（包括哨兵错误）</td><td><code>if errors.Is(err, os.ErrNotExist) { ... }</code></td></tr>
<tr><td><code>errors.As(err, &target)</code></td><td>把错误链中第一个匹配的类型提取到 target</td><td><code>var myErr *MyError; if errors.As(err, &myErr) { ... }</code></td></tr>
<tr><td><code>errors.Unwrap(err)</code></td><td>返回被包装的下一层错误</td><td>手动遍历错误链时用</td></tr>
</table>
<div class="card-w">
<h4>⚠️ Sentinel Error vs 自定义错误</h4>
<table>
<tr><th></th><th>Sentinel Error（哨兵错误）</th><th>自定义错误类型</th></tr>
<tr><td>定义</td><td><code>var ErrNotFound = errors.New("not found")</code></td><td>实现 error 接口的 struct</td></tr>
<tr><td>判断方式</td><td><code>errors.Is(err, ErrNotFound)</code></td><td><code>errors.As(err, &myErr)</code></td></tr>
<tr><td>优点</td><td>简单、标准库大量使用</td><td>可以携带上下文信息（Code、字段等）</td></tr>
<tr><td>缺点</td><td>不能携带额外信息，API 暴露内部实现</td><td>需要定义类型，略复杂</td></tr>
<tr><td>适用</td><td>标准错误：EOF、NotExist、AlreadyClosed</td><td>业务错误：ErrorCode、请求ID、用户信息</td></tr>
</table>
</div>
</div>

<div class="card card-d">
<h3>Go 错误处理最佳实践</h3>
<ul>
<li>✅ 错误要么处理，要么返回，不要忽略（<code>_ = err</code> 除外）</li>
<li>✅ 错误信息要描述「做什么失败了」，不要只说「出错了」</li>
<li>✅ 用 <code>%w</code> 包装错误保留根因，不要用 <code>%v</code> 吞掉错误链</li>
<li>✅ 业务错误用自定义类型携带错误码，上层用 <code>errors.As</code> 判断</li>
<li>❌ 不要到处 <code>if err != nil { return err }</code> 裸传，至少加一层上下文</li>
<li>❌ 不要用 panic 处理普通业务错误（比如参数校验失败）</li>
</ul>
<pre><code class="language-go">// ❌ 不好：裸传错误，没有上下文
func GetUser(id int) (*User, error) {
    return db.Query("SELECT ...", id)
}

// ✅ 好：包装错误，说明是哪个操作失败
func GetUser(id int) (*User, error) {
    user, err := db.Query("SELECT ...", id)
    if err != nil {
        return nil, fmt.Errorf("get user %d from db: %w", id, err)
    }
    return user, nil
}
</code></pre>
</div>

<div class="card card-m">
<h3>Panic 与 Recover</h3>
<p>panic 用于报告**真正意外的、程序无法继续运行**的错误，会立刻停止当前函数执行，沿调用栈向上执行所有 defer，然后程序崩溃并打印栈信息。</p>
<div class="card-w">
<h4>什么时候用 panic，什么时候不用</h4>
<table>
<tr><th>✅ 应该用 panic</th><th>❌ 不应该用 panic</th></tr>
<tr><td>程序启动时配置解析失败（服务没法启动）</td><td>HTTP 请求参数校验失败（应该返回 400）</td></tr>
<tr><td>不可能发生的情况（程序员错误）</td><td>数据库查询没找到记录（应该返回 ErrNotFound）</td></tr>
<tr><td>map 并发写、nil 指针解引用等 runtime 错误</td><td>网络超时、文件不存在（可预期的错误）</td></tr>
<tr><td>init() 函数中依赖初始化失败</td><td>任何业务逻辑错误</td></tr>
</table>
</div>
<p>recover 用于捕获 panic，阻止程序崩溃，**只能在 defer 中调用**，通常用于 HTTP 服务的中间件，避免单个请求 panic 导致整个服务挂掉。</p>
<pre><code class="language-go">func RecoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if err := recover(); err != nil {
                log.Printf("panic: %v\n%s", err, debug.Stack())
                http.Error(w, "Internal Server Error", 500)
            }
        }()
        next.ServeHTTP(w, r)
    })
}
</code></pre>
</div>

<div class="card card-s">
<h3>Defer 执行顺序：LIFO + 在 return 之前</h3>
<p>defer 语句会把函数调用压入栈，<strong>后进先出（LIFO）</strong>顺序执行；defer 执行时机是「函数返回之前」，也就是 return 语句赋值返回值之后、真正返回给调用者之前。</p>
<pre><code class="language-go">func example() {
    defer fmt.Println("1")
    defer fmt.Println("2")
    defer fmt.Println("3")
    fmt.Println("函数体")
}
// 输出：
// 函数体
// 3
// 2
// 1
</code></pre>
<p>经典面试题：defer 修改命名返回值：</p>
<pre><code class="language-go">func f() (result int) {
    defer func() {
        result++  // ✅ 可以修改命名返回值
    }()
    return 0  // 1. 先给 result 赋值 0；2. 执行 defer（result 变成 1）；3. 返回 result=1
}

func g() int {
    result := 0
    defer func() {
        result++  // ❌ 修改的是局部变量，不影响返回值
    }()
    return result  // 返回值已经确定是 0，defer 改的是局部变量
}

fmt.Println(f()) // 1
fmt.Println(g()) // 0
</code></pre>
<div class="qa-summary">一句话：defer 在 return 赋值后、真正返回前执行；如果是命名返回值，defer 可以修改最终返回值；如果是匿名返回值，defer 修改的是局部副本。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Go 为什么用 error 返回值而不用 exception 异常机制？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>这是 Go 设计哲学的体现，核心是「显式优于隐式」和「控制流清晰」。</p>
<div class="qa-section">
<div class="qa-section-title">exception 的问题</div>
<p>exception 会隐式改变控制流，throw 可以从很深的调用栈直接跳转到上层 catch，代码路径不清晰；容易被滥用，什么错误都抛异常；程序员容易忽略异常（或者写空 catch 吞掉）；资源清理依赖 try-with-resources/finally，容易出错。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">error as value 的优势</div>
<p>错误是普通值，必须显式处理，<code>if err != nil</code> 强迫你面对错误；控制流完全在代码里可见，不会有看不见的跳转；资源清理用 defer 更可靠；没有额外的异常栈展开开销，性能更好。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">Go 也承认的代价</div>
<p>代价是代码里 <code>if err != nil</code> 看起来很啰嗦，但 Rob Pike 说「这不是问题，这是我们的设计选择——显式处理每个错误，让错误成为代码的一等公民」。Go 1.13 之后 errors.Is/As 和 %w 包装已经很大程度缓解了错误处理的繁琐。</p>
</div>
<div class="qa-summary">面试口径：Go 不用 exception 是为了控制流清晰、错误处理显式；代价是 err != nil 多，但这是有意识的设计取舍，不是缺陷。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: defer 的执行顺序是怎样的？defer 在 return 之前还是之后执行？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>分两部分回答：多个 defer 的顺序，以及 defer 和 return 的先后关系。</p>
<div class="qa-section">
<div class="qa-section-title">多个 defer 的顺序</div>
<p>后进先出（LIFO，栈结构）：先 defer 的后执行，后 defer 的先执行。这和栈释放资源的语义一致——先申请的后释放（比如打开文件 A 再打开文件 B，先关 B 再关 A）。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">defer 和 return 的执行时序</div>
<p>return 不是一个原子操作，编译器把它拆成三步：<br>
1. 给返回值赋值<br>
2. 执行所有 defer 函数<br>
3. 函数真正返回（RET 指令）</p>
<p>所以 defer 是在 return 赋值之后、真正返回之前执行的。如果函数用命名返回值，defer 可以修改最终返回值；如果是匿名返回值，return 时已经把值存到返回位置了，defer 修改局部变量不影响。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">defer 参数什么时候求值？</div>
<p>defer 语句执行时（不是 defer 函数调用时）就会对参数求值，比如 <code>defer fmt.Println(i)</code> 中 i 的值在 defer 那一刻就确定了；如果 defer 的是闭包，闭包引用的变量是在执行时才取值。</p>
<pre><code class="language-go">for i := 0; i < 3; i++ {
    defer fmt.Println("a:", i)  // 输出 a:2, a:1, a:0（参数立即求值）
    defer func() { fmt.Println("b:", i) }() // 输出 b:3, b:3, b:3（闭包引用外部 i）
}
</code></pre>
</div>
<div class="qa-summary">面试口径：defer 是 LIFO 执行顺序；return 先赋值返回值，再跑 defer，最后真正返回；defer 参数立即求值，闭包变量延迟绑定。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: errors.Is 和 errors.As 有什么区别？什么时候用哪个？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先讲二者解决的问题，再给对比和示例。</p>
<div class="qa-section">
<div class="qa-section-title">errors.Is —— 判断是什么错误</div>
<p>沿着错误链 Unwrap，逐层比较是否等于 target 错误（用 == 比较，或者类型实现 Is(error) bool 方法）。用于判断「这个错误是不是某个预定义的哨兵错误」，比如 <code>os.ErrNotExist</code>、<code>io.EOF</code>、<code>context.Canceled</code>。</p>
<pre><code class="language-go">if errors.Is(err, context.DeadlineExceeded) {
    return "超时"
}
</code></pre>
</div>
<div class="qa-section">
<div class="qa-section-title">errors.As —— 提取特定类型的错误</div>
<p>沿着错误链 Unwrap，找到第一个类型匹配的错误，把它赋值给 target（target 必须是指针）。用于提取自定义错误类型，拿到 Code、Metadata 等额外信息。</p>
<pre><code class="language-go">var apiErr *APIError
if errors.As(err, &apiErr) {
    log.Printf("API 错误码: %d, 请求ID: %s", apiErr.Code, apiErr.RequestID)
}
</code></pre>
</div>
<div class="qa-section">
<div class="qa-section-title">记忆口诀</div>
<p>Is 问「是不是这个错误」（比较值），As 问「有没有这种类型的错误」（提取类型）。</p>
</div>
<div class="qa-summary">面试口径：判断是不是某个哨兵错误用 Is；提取自定义错误类型的字段用 As；它们都会沿着 %w 包装的错误链查找，不会因为包装就丢了根因。</div>
</div>
</div>

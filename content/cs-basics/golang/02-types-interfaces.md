## 一句话结论

Go 类型系统核心是**值语义 + 组合 + 隐式 interface**：没有继承只用 struct embedding 组合，interface 是鸭式类型（实现方法即满足接口），面试高频坑是**nil pointer 赋值给 interface 后 interface != nil**。

<div class="card card-m">
<h3>值类型 vs 引用类型</h3>
<p>Go 中所有赋值和参数传递默认都是值拷贝，但有些类型内部持有指针，表现得像引用。理解这点是写对 Go 代码的基础。</p>
<table>
<tr><th>分类</th><th>类型</th><th>拷贝行为</th><th>修改是否影响原值</th></tr>
<tr><td rowspan="4">值类型</td><td>int、float、bool、string</td><td>完整拷贝数据</td><td>不影响</td></tr>
<tr><td>array（固定长度数组）</td><td>拷贝整个数组</td><td>不影响</td></tr>
<tr><td>struct</td><td>拷贝所有字段</td><td>不影响（字段是指针除外）</td></tr>
<tr><td>pointer（*T）</td><td>拷贝地址（8字节）</td><td>通过指针修改会影响</td></tr>
<tr><td rowspan="4">引用语义类型</td><td>slice</td><td>拷贝 header（ptr+len+cap）</td><td>修改元素会影响底层数组</td></tr>
<tr><td>map</td><td>拷贝 header（指向哈希表指针）</td><td>修改会影响</td></tr>
<tr><td>channel</td><td>拷贝 header（指向队列指针）</td><td>修改会影响</td></tr>
<tr><td>interface</td><td>拷贝（tab+data 两字）</td><td>如果 data 是指针则可能影响</td></tr>
</table>
<div class="qa-summary">一句话：Go 没有「引用类型」这个语法概念，但 slice/map/channel/interface 内部持有指针，有引用语义；想修改 struct 本身必须传 *T。</div>
</div>

<div class="card card-s">
<h3>Struct Embedding：组合替代继承</h3>
<p>Go 没有 extends 关键字，不支持类继承，而是通过 struct embedding 实现组合。嵌入的字段称为「匿名字段」，外层 struct 可以直接访问嵌入字段的方法和字段。</p>
<pre><code class="language-go">type Animal struct{ Name string }
func (a Animal) Speak() string { return "..." }

type Dog struct {
    Animal  // 嵌入 Animal，不是继承
    Breed string
}

d := Dog{Animal: Animal{Name: "旺财"}, Breed: "柯基"}
fmt.Println(d.Name)    // 直接访问：旺财（提升字段）
fmt.Println(d.Speak()) // 直接调用方法：...
</code></pre>
<table>
<tr><th>特性</th><th>Go Embedding</th><th>Java/C++ 继承</th></tr>
<tr><td>关系</td><td>has-a（组合）</td><td>is-a（继承）</td></tr>
<tr><td>多态</td><td>通过 interface 实现</td><td>通过虚函数/override 实现</td></tr>
<tr><td>方法覆盖</td><td>外层同名方法会遮蔽嵌入方法，可显式调用 d.Animal.Speak()</td><td>子类 override 父类方法，多态调用</td></tr>
<tr><td>多继承问题</td><td>可以嵌入多个 struct，编译器处理冲突</td><td>菱形继承问题，需要虚继承</td></tr>
<tr><td>构造</td><td>必须显式初始化嵌入字段</td><td>自动调用父类构造</td></tr>
</table>
</div>

<div class="card card-m">
<h3>Interface：隐式鸭式类型</h3>
<p>Go 的 interface 是一组方法签名的集合，类型不需要显式声明「implements XxxInterface」，只要实现了 interface 的所有方法，就自动满足这个 interface。这就是「鸭子类型」：如果它走起来像鸭子、叫起来像鸭子，那它就是鸭子。</p>
<pre><code class="language-go">type Speaker interface {
    Speak() string
}

type Dog struct{}
func (d Dog) Speak() string { return "汪！" }  // Dog 自动满足 Speaker

type Cat struct{}
func (c Cat) Speak() string { return "喵～" } // Cat 自动满足 Speaker

func MakeSound(s Speaker) { fmt.Println(s.Speak()) }

MakeSound(Dog{}) // 汪！
MakeSound(Cat{}) // 喵～
</code></pre>
<div class="card-d">
<h4>空 interface interface{}</h4>
<p><code>interface{}</code>（Go 1.18+ 写作 <code>any</code>）不包含任何方法，所以所有类型都满足它。但不要滥用空 interface，它会让你失去类型检查：</p>
<ul>
<li>✅ 用在 fmt.Print、json.Marshal 这种真正需要处理任意类型的地方</li>
<li>❌ 不要为了省事用 <code>map[string]interface{}</code> 传业务参数，应该定义 struct</li>
</ul>
</div>
</div>

<div class="card card-s">
<h3>类型断言与 Type Switch</h3>
<p>从 interface 取出具体类型用类型断言 <code>x.(T)</code>，推荐用 comma-ok 形式避免 panic。</p>
<pre><code class="language-go">var s Speaker = Dog{}

// 不安全：如果 s 不是 Dog 会 panic
d := s.(Dog)

// 安全：ok 为 false 时 d 是 Dog 的零值
d, ok := s.(Dog)
if ok {
    fmt.Println("是 Dog", d.Breed)
}

// Type Switch：判断多种类型
switch v := s.(type) {
case Dog:
    fmt.Println("Dog:", v.Breed)
case Cat:
    fmt.Println("Cat:", v.Name)
case nil:
    fmt.Println("nil interface")
default:
    fmt.Printf("未知类型 %T\n", v)
}
</code></pre>
</div>

<div class="card card-r">
<h3>⚠️ 经典坑：nil interface vs nil pointer</h3>
<p>这是 Go 面试最高频的坑之一：interface 在内部是两字结构（<code>(type, data)</code>），只有当 <strong>type 和 data 都为 nil</strong> 时，interface 才等于 nil。</p>
<pre><code class="language-go">type MyError struct{}
func (e *MyError) Error() string { return "error" }

func returnsError() error {
    var e *MyError = nil  // e 是 nil pointer
    return e             // 但返回的 interface 是 (*MyError, nil)
}

func main() {
    err := returnsError()
    fmt.Println(err == nil) // false！面试必问
    fmt.Println(err)        // <nil>  （打印看起来是 nil 但实际不是）
}
</code></pre>
<div class="qa-summary">一句话总结：nil pointer 赋值给 interface 后，interface 的 type 字段不为 nil，所以 <code>interface != nil</code>。返回错误时，如果真的没有错误，必须显式返回 <code>nil</code>，而不是返回值为 nil 的指针。</div>
<div class="card-d">
<h4>正确写法</h4>
<pre><code class="language-go">func returnsError() error {
    var e *MyError = nil
    if 出错条件 {
        return e
    }
    return nil // ✅ 正确：无错误时直接返回 nil
}
</code></pre>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Go 为什么没有继承？组合比继承好在哪里？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>从 Go 设计哲学「简单、可维护」出发，说继承的问题和组合的优势。</p>
<div class="qa-section">
<div class="qa-section-title">继承的问题</div>
<p>继承是 is-a 关系，容易形成过深的继承层次（继承金字塔），父类修改会影响所有子类，耦合度高；多继承带来菱形继承问题；子类继承了不需要的方法，违反里氏替换原则。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">组合的优势</div>
<p>组合是 has-a 关系，耦合度低，可以嵌入多个 struct，方法查找简单直接，不会有继承的脆弱基类问题；Go 通过 interface 实现多态，通过 embedding 实现代码复用，职责更清晰。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">面向对象三要素在 Go 中的实现</div>
<p>封装（首字母大小写控制可见性）、继承（struct embedding 组合）、多态（interface 鸭式类型）——Go 没有放弃 OOP，而是用更简单的方式实现。</p>
</div>
<div class="qa-summary">面试口径：Go 不是没有 OOP，而是认为继承带来的耦合比复用价值更大，用组合+interface 能写出更易维护的代码，这是「简单优于复杂」设计哲学的体现。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: nil interface 和 nil pointer 到底有什么区别？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>先讲 interface 的内部结构，再给代码示例，最后说正确的返回方式。</p>
<div class="qa-section">
<div class="qa-section-title">interface 的内存布局</div>
<p>interface 在运行时是两个指针大小的结构体：第一个指针指向 itab（类型信息+方法表），第二个指针指向实际数据。<strong>只有 itab 和 data 都为 nil 时，interface 才 == nil</strong>。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">为什么会出现「看起来是 nil 实际不是」</div>
<p>当你把一个 nil 的 *T 赋值给 interface 时，itab 被设置为 *T 的类型信息，data 是 nil，但 interface 本身不是 nil。<code>fmt.Println(err)</code> 会打印 <code>&lt;nil&gt;</code> 是因为 Error() 方法在 receiver 为 nil 时返回的，但 <code>err == nil</code> 比较的是整个 interface 结构。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">避坑指南</div>
<p>函数返回 error 时，如果确定没有错误，一定要 return nil，不要 return 一个类型化的 nil 指针；接收 error 时不要用 <code>err != (*MyError)(nil)</code> 这种判断，用 errors.As 来做类型断言。</p>
</div>
<div class="qa-summary">面试口径：记住 interface 是两字结构（type, data），只有两者都 nil 才等于 nil；返回 error 永远显式 return nil。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Go 的 interface 和 Java 的 interface、C++ 的抽象类有什么区别？</div>
<div class="qa-a">
<p><strong>回答思路：</strong>核心区别是「是否需要显式声明实现」以及「是否可以有数据」。</p>
<div class="qa-section">
<div class="qa-section-title">Go interface</div>
<p>隐式实现，不需要 implements 关键字；interface 不能有字段（Go 1.18 前），只有方法；可以给任意类型（包括基本类型、非 struct 类型）实现方法来满足接口；支持空 interface any。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">Java interface</div>
<p>显式声明 implements；Java 8+ 可以有 default 方法、static 方法、常量；只能被 class 实现；一个类可以实现多个 interface。</p>
</div>
<div class="qa-section">
<div class="qa-section-title">C++ 抽象类</div>
<p>包含纯虚函数就是抽象类，可以有成员变量、构造函数、普通虚函数；通过 public 继承来「实现」接口；支持多继承，但有菱形继承风险。</p>
</div>
<div class="qa-summary">面试口径：Go interface 最大特点是隐式实现和值语义，这让接口和实现完全解耦——你可以为别人写的类型实现你的接口，不需要修改原有代码。</div>
</div>
</div>

## 关联模块

- `错误处理与 Panic`：error 本身就是一个 interface
- `Go 工程实践`：interface 在单元测试 mock 中的应用
- `内存管理与 GC`：eface/iface 内部结构和 GC 的关系

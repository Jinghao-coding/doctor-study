## 一句话结论

面向对象三大特性：封装、继承、多态 是 编程与系统工程基础 的核心知识点，面试回答要先给结论，再说明机制边界、工程场景和常见误区。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 编程与系统工程基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕编译链接、C++、内存、智能指针、调试和工程排障建立系统编程答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心概念、系统链路或关键机制，把知识点映射到工程场景。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m">
<h3>面向对象三大特性：封装、继承、多态</h3>
<table>
<tr><th>特性</th><th>含义</th><th>一句话</th></tr>
<tr><td>封装</td><td>隐藏实现细节，把数据和操作数据的函数包在一起，对外只暴露接口</td><td>对不可信的调用方做信息隐藏，使代码模块化</td></tr>
<tr><td>继承</td><td>子类派生自父类，复用父类属性和方法，也可以重写父类方法</td><td>实现代码复用和扩展</td></tr>
<tr><td>多态</td><td>同一个函数名有多种实现形式</td><td>覆盖（重写虚函数）+ 重载（同名不同参）</td></tr>
</table>
<div class="qa-summary">面试口径：封装管"隐藏"，继承管"复用"，多态管"同名不同行为"。多态在 C++ 里又分编译期多态（重载/模板）和运行期多态（虚函数）。</div>
</div>

<div class="card card-s">
<h3>public / protected / private 访问范围</h3>
<table>
<tr><th>修饰符</th><th>本类成员函数 / 友元</th><th>子类成员函数</th><th>类的对象（外部）</th></tr>
<tr><td>private</td><td>可访问</td><td>不可访问</td><td>不可访问</td></tr>
<tr><td>protected</td><td>可访问</td><td>可访问</td><td>不可访问</td></tr>
<tr><td>public</td><td>可访问</td><td>可访问</td><td>可访问</td></tr>
</table>
<p>注意 private 即使是该类自己的对象也不能直接访问（只能通过成员函数/友元）。</p>
</div>

<div class="card card-d">
<h3>三种继承方式与属性变化</h3>
<table>
<tr><th>继承方式</th><th>父类成员在子类中的属性变化</th></tr>
<tr><td>private 继承</td><td>父类的所有方法在子类中变为 private</td></tr>
<tr><td>protected 继承</td><td>父类的 protected 和 public 方法在子类中变为 protected，private 不变</td></tr>
<tr><td>public 继承</td><td>父类中的方法属性不发生改变（最常用，表达 "is-a" 关系）</td></tr>
</table>
</div>

<div class="card card-w">
<h3>虚函数与虚函数表</h3>
<p><strong>虚函数</strong>：C++ 中虚函数的作用主要是实现运行期多态。用父类型别的指针指向其子类实例，然后通过父类指针调用，实际会调用子类重写的成员函数。</p>
<p><strong>虚函数表（vtable）</strong>：每个包含虚函数的类都存在一个函数地址数组。当用父类指针操作子类对象时，这张虚函数表指明实际应调用的函数。C++ 编译器保证<strong>虚函数表指针（vptr）位于对象实例最前面的位置</strong>，这样通过对象地址就能拿到 vtable，遍历其中函数指针并调用相应函数。</p>
<pre><code class="language-cpp">class Base {
public:
  virtual void run() { /* ... */ }   // 虚函数
  virtual ~Base() {}                  // 基类析构通常要声明 virtual
};

class Derived : public Base {
public:
  void run() override { /* 子类实现 */ }
};

Base* p = new Derived();
p-&gt;run();        // 运行期通过 vtable 调用 Derived::run
delete p;        // 因为 ~Base 是 virtual，能正确调用 Derived 析构</code></pre>
<div class="qa-summary">面试常追问：vptr 在对象内存布局最前面；每个类一张 vtable，对象实例只存一个 vptr 指向它；基类析构不声明 virtual，用基类指针 delete 子类对象会导致子类析构不被调用，造成资源泄漏。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 虚函数调用是怎么在运行期确定实际函数的？</div>
<div class="qa-a"><p>编译器为每个含虚函数的类生成一张虚函数表（vtable），表里是该类各虚函数的实际地址。每个对象实例最前面存一个虚指针（vptr）指向所属类的 vtable。通过基类指针调用虚函数时，编译器生成的代码会先取对象的 vptr，再到 vtable 中按固定偏移找到函数地址间接调用，从而在运行期分派到正确的实现。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 重载（overload）和重写（override）的区别？</div>
<div class="qa-a"><p>重载是同一作用域内多个同名函数，参数表不同，编译期根据实参类型静态决议，属于编译期多态。重写是子类重新定义父类的虚函数，函数签名相同，运行期通过 vtable 动态分派，属于运行期多态。还有一个 hiding（隐藏）：子类定义了同名非虚函数会隐藏父类同名函数，与重写不同。</p></div>
</div>

## 面试回答

**30 秒版：**

03 cpp oop 是 编程与系统工程基础 中的一个基础知识点，面试回答要先给结论，再说明机制、边界和工程场景。 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。

**2 分钟版：**

我会先说明这个知识点在 编程与系统工程基础 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

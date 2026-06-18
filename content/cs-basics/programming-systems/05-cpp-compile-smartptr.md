## 一句话结论

编译四阶段是预处理、编译、汇编、链接，分别产出 .i/.s/.o 和可执行文件；配套要记三件事——静态库整体复制进可执行文件、动态库运行时加载且多进程共享，智能指针 unique/shared/weak 分别对应独占/共享/打破循环引用，多线程卡死用 gdb attach 后 info threads + bt 看各线程卡在哪个锁。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 编程与系统工程基础 |
| 章节类型 | 机制类 |
| 解决问题 | 围绕编译链接、C++、内存、智能指针、调试和工程排障建立系统编程答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m">
<h3>源码到可执行文件：编译四阶段</h3>
<table>
<tr><th>阶段</th><th>做什么</th><th>命令</th><th>产物</th></tr>
<tr><td>预处理</td><td>宏替换、头文件展开、条件编译、移除注释</td><td><code>g++ -E source.cpp -o source.i</code></td><td>.i</td></tr>
<tr><td>编译</td><td>语法分析（生成 AST）、语义分析、中间代码生成、优化、生成汇编</td><td><code>g++ -S source.i -o source.s</code></td><td>.s</td></tr>
<tr><td>汇编</td><td>把汇编指令转成机器指令，生成目标文件（代码+数据的二进制）</td><td><code>g++ -c source.s -o source.o</code></td><td>.o</td></tr>
<tr><td>链接</td><td>符号解析（引用关联到定义）、重定位（符号引用替换为实际地址）</td><td><code>g++ source.o -o source</code></td><td>可执行文件 / 库</td></tr>
</table>
<p>打包静态库：<code>ar rcs libxxx.a a.o b.o</code>；生成动态库：<code>g++ -shared -o libxxx.so a.o b.o</code>。</p>
</div>

<div class="card card-d">
<h3>静态库 vs 动态库</h3>
<table>
<tr><th>维度</th><th>静态库 .a</th><th>动态库 .so</th></tr>
<tr><td>链接时机</td><td>编译链接时整体复制进可执行文件</td><td>运行时动态加载</td></tr>
<tr><td>可执行文件体积</td><td>变大（含库代码）</td><td>较小（不含库代码）</td></tr>
<tr><td>运行依赖</td><td>不依赖外部库</td><td>运行时需要找到对应 .so</td></tr>
<tr><td>更新维护</td><td>库更新要重新编译链接</td><td>替换 .so 即可，多进程共享一份</td></tr>
</table>
<div class="qa-summary">AI Infra 场景：CUDA / cuDNN / NCCL 多以动态库分发，常见报错是运行时找不到 .so 或版本不匹配，用 <code>ldd</code> 排查依赖、检查 <code>LD_LIBRARY_PATH</code>。</div>
</div>

<div class="card card-s">
<h3>智能指针需要包含哪些要素</h3>
<table>
<tr><th>类型</th><th>语义</th><th>用途</th></tr>
<tr><td>unique_ptr</td><td>独占式，同一时间只有一个指针指向对象</td><td>明确单一所有权，零开销</td></tr>
<tr><td>shared_ptr</td><td>共享式，多个指针共享同一对象，引用计数</td><td>共享所有权</td></tr>
<tr><td>weak_ptr</td><td>弱引用，不增加引用计数</td><td>解决 shared_ptr 循环引用导致的内存无法释放</td></tr>
</table>
<p>自己实现一个引用计数智能指针，要包含的要素：</p>
<ul>
<li><strong>原始指针</strong>：指向被管理对象。</li>
<li><strong>计数器</strong>：跟踪引用计数。</li>
<li><strong>拷贝构造函数</strong>：增加引用计数。</li>
<li><strong>赋值运算符重载</strong>：增加新对象引用计数，并减少旧指针的引用计数。</li>
<li><strong>析构函数</strong>：引用计数减到 0 时释放资源。</li>
</ul>
</div>

<div class="card card-w">
<h3>gdb 调试多线程卡死 / 死锁</h3>
<p>一个 C++ 多线程程序执行到中间卡住，定位流程：</p>
<table>
<tr><th>步骤</th><th>命令</th><th>作用</th></tr>
<tr><td>1</td><td><code>gdb attach &lt;pid&gt;</code></td><td>关联到发生死锁/卡死的进程</td></tr>
<tr><td>2</td><td><code>info threads</code></td><td>查看所有线程信息和部分堆栈，找出可疑线程</td></tr>
<tr><td>3</td><td><code>thread &lt;id&gt;</code></td><td>切换到具体线程</td></tr>
<tr><td>4</td><td><code>bt</code></td><td>查看该线程堆栈，看卡在哪个锁/调用</td></tr>
</table>
<div class="qa-summary">典型死锁特征：多个线程的 bt 都停在 <code>lock</code> / <code>pthread_mutex_lock</code> 且互相等待。Python 侧大模型训练 hang 常用 <code>py-spy dump</code> 看各线程/各 rank 卡点。</div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

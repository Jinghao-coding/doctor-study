## 一句话结论

STL 容器各有底层实现：vector 是连续动态数组按 1.5x/2x 倍增扩容、string 有 SSO 小字符串栈上优化、deque 是分段连续数组、list 是双向链表、set/map 基于红黑树有序 O(log n)、unordered_map 是哈希表平均 O(1)；vector 迭代器在 reallocation 后全部失效，list 只失效被删元素，unordered_map rehash 后全部失效；容器选择按"是否需要有序/是否需要随机访问/是否频繁中间插入"三维度决策。
<div class="card card-m">
<h3>vector：连续动态数组</h3>
<p>vector 在堆上分配一块连续内存，用三个指针管理：<code>start</code>（起始）、<code>finish</code>（已用末尾）、<code>end_of_storage</code>（容量末尾）。</p>
<table>
<tr><th>操作</th><th>复杂度</th><th>说明</th></tr>
<tr><td>随机访问 [] / at</td><td>O(1)</td><td>连续内存，直接指针偏移</td></tr>
<tr><td>push_back</td><td>摊还 O(1)</td><td>有容量时直接构造；不够时扩容</td></tr>
<tr><td>pop_back</td><td>O(1)</td><td>只析构末尾元素，不释放内存</td></tr>
<tr><td>insert / erase（中间）</td><td>O(n)</td><td>需要搬移后面所有元素</td></tr>
</table>
<p><strong>扩容策略</strong>：capacity 不足时分配新的更大内存（MSVC 是 1.5 倍，GCC 是 2 倍），把旧元素搬过去（移动构造优先，拷贝兜底），释放旧内存。</p>
<pre><code class="language-cpp">vector&lt;int&gt; v;
v.reserve(1000);  // 提前预留容量，避免多次扩容
for (int i = 0; i &lt; 1000; ++i) {
    v.push_back(i);  // 不会触发 reallocation
}

cout &lt;&lt; v.size() &lt;&lt; " / " &lt;&lt; v.capacity() &lt;&lt; endl;  // 1000 / 1000
v.clear();
cout &lt;&lt; v.size() &lt;&lt; " / " &lt;&lt; v.capacity() &lt;&lt; endl;  // 0 / 1000（内存不释放！）
// 真正释放内存：swap 空 vector
vector&lt;int&gt;().swap(v);
// C++11：v.shrink_to_fit();</code></pre>
</div>

<div class="card card-d">
<h3>string 的 SSO（Small String Optimization）</h3>
<p>std::string 几乎所有主流实现（libstdc++、libc++、MSVC STL）都用 SSO：短字符串直接存在 string 对象内部的栈上 buffer，不分配堆内存；长度超过阈值才在堆上分配。</p>
<table>
<tr><th>实现</th><th>SSO 阈值（含 '\0'）</th><th>说明</th></tr>
<tr><td>libstdc++ (GCC)</td><td>16 字节（15 字符 + '\0'）</td><td>典型 64 位平台</td></tr>
<tr><td>libc++ (Clang/Mac)</td><td>23 字节（22 字符 + '\0'）</td><td>利用了 union 里的 padding</td></tr>
<tr><td>MSVC STL</td><td>16 字节（15 字符 + '\0'）</td><td>Debug 模式下更少</td></tr>
</table>
<div class="qa-summary">面试口径：string s = "hello"; 大概率不触发堆分配；但 string s(100, 'x'); 一定在堆上。写性能敏感代码时要意识到这一点。</div>
</div>

<div class="card card-s">
<h3>deque：分段连续数组</h3>
<p>deque 表面上支持随机访问和两端 O(1) 插入，但底层<strong>不是真正连续的</strong>。它维护一个"中控数组"（map），每个元素指向一块固定大小的连续内存段（通常 512 字节）。</p>
<ul>
<li><strong>push_front / push_back</strong>：O(1)，当前段不够时分配新段挂到 map 上，不需要搬移已有元素（这是和 vector 最大的区别）。</li>
<li><strong>随机访问 []</strong>：O(1) 但比 vector 慢——要先算段号 + 段内偏移，多一次指针跳转。</li>
<li><strong>中间 insert/erase</strong>：O(n)，因为需要搬移元素。</li>
<li><strong>没有 reserve()</strong>，因为 deque 的内存本来就是分段增长的。</li>
</ul>
</div>

<div class="card card-w">
<h3>list / forward_list：链表</h3>
<ul>
<li><strong>list</strong>：双向链表，每个节点有 prev/next 指针 + 数据。不支持随机访问，但任意位置 insert/erase 是 O(1)（前提是你已经有那个位置的迭代器）。</li>
<li><strong>forward_list</strong>：单向链表，更省内存（少一个指针），只支持前向遍历。</li>
</ul>
<p><strong>重要</strong>：由于链表节点分散在堆上，<strong>list 的缓存局部性极差</strong>（cache miss 多），遍历比 vector 慢很多倍。在 C++ 中除非确实有"在中间频繁插入/删除且不搬迁元素"的需求，否则优先用 vector。</p>
<p><code>list::sort()</code> 提供了链表专用的归并排序（O(n log n)），不需要随机访问，比通用的 <code>std::sort</code>（需要 random access iterator）更适合 list。</p>
</div>

<div class="card card-m">
<h3>set / map：红黑树有序</h3>
<p>set、map、multiset、multimap 底层通常是<strong>红黑树</strong>（一种近似平衡的二叉搜索树）：</p>
<ul>
<li>所有操作（insert / erase / count / find）都是 O(log n)。</li>
<li>元素<strong>有序</strong>，按 key 排序，可以做范围查询（<code>lower_bound</code> / <code>upper_bound</code>）。</li>
<li>map 的 value_type 是 <code>pair&lt;const Key, T&gt;</code>，key 不可修改（修改会破坏 BST 性质）。</li>
<li>迭代器是双向迭代器（bidirectional），不是随机访问，<code>it + 5</code> 不行。</li>
</ul>
</div>

<div class="card card-r">
<h3>unordered_map / unordered_set：哈希表</h3>
<p>底层是哈希表，标准只规定接口不规定实现。常见实现：</p>
<ul>
<li><strong>libstdc++</strong>：开链法（separate chaining），每个 bucket 是一个单向链表，挂 hash 冲突的元素。</li>
<li><strong>libc++</strong>：开链法 + 短期优化（bucket 里前几个元素直接存在 bucket 数组里，超过再链表）。</li>
<li><strong>MSVC</strong>：也曾用过开放寻址（open addressing），但新版本也偏向开链。</li>
</ul>
<table>
<tr><th>操作</th><th>平均</th><th>最坏</th><th>说明</th></tr>
<tr><td>insert / find / erase</td><td>O(1)</td><td>O(n)</td><td>所有 hash 冲突退化成链表时</td></tr>
<tr><td>rehash</td><td>—</td><td>O(n)</td><td>bucket 扩容时重新算 hash 搬移所有元素</td></tr>
</table>
<p><strong>load factor</strong>（装载因子）= size / bucket_count。超过 <code>max_load_factor()</code>（默认 1.0）时触发 rehash，bucket 数大约翻倍，所有元素重新分配位置。rehash 会导致所有迭代器失效。</p>
<pre><code class="language-cpp">unordered_map&lt;string, int&gt; m;
m.reserve(10000);  // 提前预留 bucket，避免插入过程中多次 rehash
for (int i = 0; i &lt; 10000; ++i) {
    m[to_string(i)] = i;
}</code></pre>
</div>

<div class="card card-d">
<h3>容器适配器：stack / queue / priority_queue</h3>
<p>它们不是独立容器，而是对底层容器的封装：</p>
<table>
<tr><th>适配器</th><th>默认底层容器</th><th>底层操作</th><th>可替换为</th></tr>
<tr><td>stack</td><td>deque</td><td>push_back / pop_back / back</td><td>vector / list</td></tr>
<tr><td>queue</td><td>deque</td><td>push_back / pop_front / front / back</td><td>list（不能用 vector，因为没有 pop_front）</td></tr>
<tr><td>priority_queue</td><td>vector</td><td>push_back + pop_heap（堆调整）</td><td>deque</td></tr>
</table>
<p><code>priority_queue</code> 是大顶堆（默认），top() 是最大值，push/pop 都是 O(log n)。要小顶堆用 <code>priority_queue&lt;int, vector&lt;int&gt;, greater&lt;int&gt;&gt;</code>。</p>
</div>

<div class="card card-w">
<h3>迭代器失效（Iterator Invalidation）规则</h3>
<table>
<tr><th>容器</th><th>操作</th><th>哪些迭代器失效</th></tr>
<tr><td rowspan="3">vector</td><td>reallocation（push_back 等导致扩容）</td><td><strong>全部</strong>迭代器/引用/指针失效</td></tr>
<tr><td>insert / push_back（不扩容）</td><td>插入点<strong>之后</strong>的迭代器失效</td></tr>
<tr><td>erase / pop_back</td><td>删除点<strong>及之后</strong>的迭代器失效（erase 返回下一个有效迭代器）</td></tr>
<tr><td rowspan="2">deque</td><td>push_front / push_back</td><td><strong>全部</strong>迭代器失效（但引用/指针仍有效，因为不搬移元素）</td></tr>
<tr><td>insert / erase 中间</td><td><strong>全部</strong>迭代器/引用/指针失效</td></tr>
<tr><td rowspan="2">list / forward_list</td><td>insert / push</td><td>无失效</td></tr>
<tr><td>erase</td><td>仅<strong>被删元素</strong>的迭代器失效，其余不受影响</td></tr>
<tr><td>set / map</td><td>insert / erase</td><td>仅<strong>被删元素</strong>的迭代器失效</td></tr>
<tr><td rowspan="2">unordered_map</td><td>insert（不触发 rehash）</td><td>无失效</td></tr>
<tr><td>insert 触发 rehash</td><td><strong>全部</strong>迭代器失效</td></tr>
</table>
<div class="qa-summary">面试高频坑：<code>for (auto it = v.begin(); it != v.end(); ++it) { if (...) v.erase(it); }</code> 是 UB，因为 erase 后 it 已失效。正确写法：<code>it = v.erase(it);</code> 或 <code>v.erase(it++);</code>。</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: vector 扩容为什么是 1.5 倍或 2 倍？为什么不是 3 倍或固定大小？</div>
<div class="qa-a"><p>核心是<strong>摊还复杂度</strong>和<strong>内存复用</strong>的平衡：①任何大于 1 的常数倍增长，push_back 的摊还时间都是 O(1)——每个元素最多被搬移常数次（2 倍时每个元素被搬 1 次左右）。②倍数不能太大（如 3 倍）：扩容太激进导致内存浪费，而且每次分配的新大小总是大于之前所有已释放块的总和，无法复用刚释放的内存（buddy allocator 场景下）。③倍数不能太小（如 1.1 倍）：扩容太频繁，insert/erase 摊还时间会退化成 O(n)。④1.5 倍 vs 2 倍：2 倍在数学上摊还分析更干净（每个元素恰好被搬一次），1.5 倍（MSVC 选择）能更好地复用之前释放的内存块。固定步长扩容会导致 O(n²) 的 push_back，所以必须是指数级增长。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: unordered_map 和 map 怎么选？</div>
<div class="qa-a"><p>三个维度决策：<strong>①是否需要有序</strong>——需要范围查询、按序遍历、lower_bound/upper_bound 选 map（红黑树）。<strong>②性能要求</strong>——平均性能 unordered_map O(1) 优于 map O(log n)，但 unordered_map 最坏 O(n)（hash 冲突严重时），且 rehash 时抖动明显；map 性能稳定可预测。<strong>③key 类型</strong>——unordered_map 需要 key 支持 hash（自定义类型要提供 std::hash 特化），map 需要 key 支持 &lt; 比较（自定义类型提供 operator&lt;）。经验法则：默认选 unordered_map 追求性能；需要有序或稳定延迟选 map；int/string 做 key 两者都行，小数据量（&lt;1000 元素）两者差异可以忽略。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么 vector 的 clear() 不释放内存？怎么真正释放？</div>
<div class="qa-a"><p>clear() 只做<strong>两件事</strong>：调用所有元素的析构函数，把 size 设为 0；<strong>capacity 不变，内存不还给操作系统/分配器</strong>。这是设计选择——clear() 常见用法是"清空后再填新元素"，保持 capacity 可以避免重新分配，提升性能。真正释放内存有两种方式：①<code>vector&lt;T&gt;().swap(v);</code>（swap 一个临时空 vector，临时对象析构时带走旧内存）；②C++11 的 <code>v.shrink_to_fit()</code>（非强制，请求释放多余容量，但编译器可能不执行）。这是 C++ "不花不需要的开销"哲学的体现。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: emplace_back 和 push_back 到底有什么区别？</div>
<div class="qa-a"><p><code>push_back(obj)</code> 接收一个已经构造好的对象（或隐式转换构造临时对象），然后把它<strong>拷贝/移动</strong>进容器。<code>emplace_back(args...)</code> 接收构造函数参数，直接在 vector 的内存位置上<strong>原地构造</strong>（in-place construction，通过 placement new 和完美转发），省去一次临时对象的构造 + 移动/拷贝。关键区别：①对已有左值对象，两者一样，都会拷贝。②对"需要多个构造参数"的对象，emplace_back 明显更高效（如 <code>v.emplace_back(42, "hello")</code> 直接构造 pair）。③对单参数隐式转换场景，push_back(T&&) 本身也会触发移动，差异不大。④小心 emplace_back 隐式转换带来的可读性问题：<code>v.emplace_back(10)</code> 在 vector&lt;int&gt; 可以，但如果是 vector&lt;bool&gt; 会有有趣的陷阱。总结：<strong>用参数包直接构造时用 emplace_back，传已有对象时两者等价</strong>。</p></div>
</div>

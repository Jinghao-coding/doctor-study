<div class="card card-m">
<h3>指令集基础</h3>
<table><tr><th>维度</th><th>CISC（x86）</th><th>RISC（ARM/RISC-V）</th></tr>
<tr><td>设计理念</td><td>复杂指令，一条指令做更多事</td><td>简单定长指令，硬件高效执行</td></tr>
<tr><td>指令长度</td><td>变长（1–15 字节）</td><td>定长（ARM 32bit / Thumb 16bit）</td></tr>
<tr><td>寄存器数量</td><td>16 个 GPR（x86-64）</td><td>32 个 GPR（ARM64/RISC-V）</td></tr>
<tr><td>代表</td><td>Intel/AMD 服务器/桌面</td><td>手机/嵌入式/Apple M系列/昇腾</td></tr>
<tr><td>AI Infra 场景</td><td>主流训练/推理服务器</td><td>边缘推理、Apple Silicon、自研芯片</td></tr>
</table>
</div>

<div class="card card-s">
<h3>流水线（Pipelining）</h3>
<ul>
<li><strong>经典 5 级流水线：</strong>取指（IF）→ 译码（ID）→ 执行（EX）→ 访存（MEM）→ 写回（WB）</li>
<li><strong>理想 CPI = 1：</strong>每个 cycle 完成一条指令（但实际被冒险打断）</li>
<li><strong>三类冒险：</strong>
  <ul>
    <li><strong>结构冒险：</strong>硬件资源冲突（如同一周期争用 ALU）→ 增加硬件资源/流水线停顿</li>
    <li><strong>数据冒险：</strong>指令间依赖（RAW/WAR/WAW）→ 旁路（forwarding/bypass）、流水线停顿</li>
    <li><strong>控制冒险：</strong>分支/跳转目标不确定 → 分支预测、延迟槽、预取</li>
  </ul>
</li>
<li><strong>超流水线：</strong>级数更深（如 Pentium 4 有 31 级），提升频率但分支误判代价更高</li>
<li><strong>超标量（Superscalar）：</strong>每 cycle 发射多条指令到多个执行单元，现代 x86 可 4–6 发射</li>
<li><strong>乱序执行（OoO）：</strong>不按程序序发射，按数据就绪顺序执行，隐藏延迟（ROB、保留站）</li>
</ul>
</div>

<div class="card card-d">
<h3>分支预测（Branch Prediction）</h3>
<ul>
<li><strong>为什么重要：</strong>误判一次分支意味着清空流水线，代价 10–20 cycles</li>
<li><strong>静态预测：</strong>编译器提示（如 __builtin_expect）、总是向后跳转（循环）</li>
<li><strong>动态预测：</strong>
  <ul>
    <li>1-bit / 2-bit 饱和计数器：记录分支历史方向</li>
    <li>（GShare/Perceptron）：结合全局/局部历史，现代预测准确率 &gt;95%</li>
    <li>BTB（Branch Target Buffer）：预测跳转目标地址</li>
    <li>RAS（Return Address Stack）：预测函数返回地址</li>
  </ul>
</li>
<li><strong>AI Infra 启发：</strong>写 if-else 时让高频路径走进分支（如常见输入走 then），减少误判；unlikely/likely 宏提示编译器</li>
</ul>
</div>

<div class="card card-w">
<h3>SIMD：单指令多数据</h3>
<p>一条指令同时处理多个数据元素，是 CPU 上向量化计算的基础。</p>
<table><tr><th>指令集</th><td>架构</td><td>宽度</td><td>典型用途</td></tr>
<tr><td>SSE / SSE2/3/4</td><td>x86</td><td>128 bit（4×float 或 2×double）</td><td>早期向量化</td></tr>
<tr><td>AVX / AVX2</td><td>x86</td><td>256 bit（8×float）</td><td>主流 CPU GEMM 内核</td></tr>
<tr><td>AVX-512</td><td>x86（Xeon）</td><td>512 bit（16×float）</td><td>HPC、部分推理场景</td></tr>
<tr><td>NEON</td><td>ARM/ARM64</td><td>128 bit</td><td>移动端/边缘推理</td></tr>
<tr><td>SVE / SVE2</td><td>ARMv8/v9</td><td>可变长度（128–2048 bit）</td><td>HPC、富岳/AWS Graviton</td></tr>
<tr><td>AMX（Advanced Matrix Extensions）</td><td>Intel Sapphire Rapids+</td><td>tile 矩阵运算</td><td>CPU 上的矩阵乘加速</td></tr>
</table>
<p><strong>GPU 对应：</strong>CUDA 的 warp 单指令多线程（SIMT）本质是 SIMD 的扩展；Tensor Core 做的是矩阵 tile 运算，和 CPU AMX 同类。</p>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么循环展开（loop unrolling）能加速？</div>
<div class="qa-a"><p>三个原因：(1) 减少循环控制指令（比较+跳转）的比例，分支预测压力小；(2) 展开后指令调度器能看到更多独立指令，填充流水线发射槽，提升 IPC；(3) 给编译器更多机会做 SIMD 向量化。但过度展开会增加代码 size，导致 I-cache 压力。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 分支误判（branch misprediction）代价有多大？怎么优化？</div>
<div class="qa-a"><p>现代 OoO 处理器流水线深 10–20 级，误判需清空流水线重新取指，代价约 10–20 cycles。高频 if-else 中误判率 20% 就会让 IPC 大幅下降。优化方法：</p><ul><li><strong>减少分支：</strong>用条件移动（CMOV）替代短 if-else</li><li><strong>排序数据：</strong>先按条件排序让同一分支集中（如 partition 数据）</li><li><strong>likely/unlikely 宏：</strong>给编译器静态预测提示</li><li><strong>查表/分支表：</strong>switch 跳转表替代多分支</li><li><strong>向量化：</strong>SIMD 用 blend/mask 指令无分支处理</li></ul></div>
</div>

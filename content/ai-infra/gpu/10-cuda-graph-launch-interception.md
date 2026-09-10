## 从 PyTorch 到 GPU 的提交链路

```flow
Python 模型代码 | nn.Module、autograd、torch.compile
PyTorch Dispatcher / ATen | 选择 CPU、CUDA 或自定义算子实现
CUDA 库与自定义 Kernel | cuBLAS、cuDNN、Triton、C++/CUDA Extension
CUDA Runtime API | cudaLaunchKernel、stream、event、memcpy
CUDA Driver API | cuLaunchKernel、context、module、virtual memory
GPU | block 分配到 SM，warp 发射指令
```

“编排 kernel launch”必须先说明控制的是哪一层。替换某个算子的算法，适合在 PyTorch 算子或编译器层做；控制多个 kernel 的提交次序，可以在框架执行器或 CUDA API 边界做；改变已经提交到 GPU 后的 block/warp 调度，则需要硬件或驱动支持，普通用户态拦截库做不到。

## 三种改造位置

<div class="table-scroll">

| 位置 | 做法 | 用户代码改动 | 能控制什么 | 主要限制 |
|---|---|---:|---|---|
| PyTorch 算子层 | C++/CUDA Extension、注册自定义算子、替换 module | 显式调用时需要少量修改 | kernel 算法、线程组织、数据布局、融合 | 只覆盖被替换的算子 |
| 框架/编译执行层 | graph rewrite、fusion、运行时队列 | 可以很少 | 连续的算子图、融合、静态子图重放 | 需要理解框架 dispatcher、autograd 和动态 shape |
| CUDA API 边界 | 包装 Runtime/Driver API，在真正 launch 前排队 | 通常只改启动方式 | 尚未提交 kernel 的顺序、优先级、准入 | 难覆盖所有路径，必须维护完整异步语义 |

</div>

对普通 PyTorch 训练，如果目标是不改模型逻辑而协调多个进程的 kernel 提交，可以尝试在动态库边界包装 `cudaLaunchKernel` 或 `cuLaunchKernel`，进程间再由调度器发放提交许可。CUDA Runtime 构建在 Driver API 之上，但实际程序可能通过 Runtime、Driver、第三方库或 CUDA Graph 提交工作，因此只 hook 一个符号不等于覆盖全部 GPU 工作。

`LD_PRELOAD` 只是 ELF 动态链接环境下的一种注入办法。静态链接、符号版本、直接加载 driver symbol、子进程、容器挂载和框架升级都会影响覆盖率。上线前必须用 trace 验证实际命中的 API，而不能根据设计图假设已经拦截完整。

## 延迟 kernel launch 的正确性约束

拦截函数如果立即调用真实 launch，只需转发参数；如果先返回、稍后再提交，就改变了原 API 的时间语义，必须保存足够的信息并维护依赖。

<div class="table-scroll">

| 约束 | 为什么会出错 | 需要维护的状态 |
|---|---|---|
| Kernel 参数 | `kernelParams` 常是指向主机参数存储的指针数组；原调用返回后，这些地址未必仍有效 | 参数值、大小、对齐和函数签名；或按 ABI 保存 packed buffer |
| Stream 顺序 | 同一 stream 内操作应按提交顺序执行 | 每个 stream 的逻辑队列和序号 |
| Event 依赖 | `record`/`wait` 表达跨 stream 的 happens-before | event 的生产者、消费者和完成状态 |
| 同步 API | `stream/device synchronize` 不能在对应工作尚未真实提交时错误返回 | 先冲刷依赖队列，再等待真实完成 |
| 异步内存操作 | memcpy、memset、malloc/free 可能与 kernel 存在顺序关系 | 指针生命周期、所在 stream 和释放时机 |
| 错误传播 | CUDA 错误可能异步暴露 | launch 错误、异步错误与调用方可见时机 |

</div>

仅延迟 kernel 而不处理 event、同步和内存生命周期，会出现“消费者先于生产者执行”“内存先释放后使用”或者同步调用提前返回等错误。多线程进程中还要维护每线程状态，并避免调度器本身成为全局锁瓶颈。

## 能优化什么，不能优化什么

kernel 级编排可以根据优先级、预计时长或资源互补性，决定尚未提交的 kernel 何时进入某个 stream。例如暂缓后台训练 kernel，为延迟敏感请求留下提交窗口，或者交错计算型和访存型 kernel。

但 launch 拦截通常不能终止一个已经运行的长 kernel。当前台请求到来时，后台长 kernel 可能继续占用 GPU，形成 blocking time。因此实际系统还需要控制 kernel 粒度、使用 stream priority，并评估 GPU 架构支持的抢占边界。stream priority 也只是调度提示，不是任意时刻的强制抢占保证。

调度收益至少要覆盖以下成本：

$$
T_{benefit} > T_{intercept}+T_{queue}+T_{coordination}+T_{extra\ launch}
$$

对于大量短 kernel，CPU launch 开销和协调开销都更敏感；对于少量长 kernel，细粒度编排机会又会减少。

## CUDA Graph：一次提交重复执行的依赖图

CUDA Graph 把 kernel、memcpy 等操作及依赖先定义成图，经过实例化得到 executable graph，之后通过 `cudaGraphLaunch` 重复执行。相比每次逐个提交 kernel，它提前完成大量准备工作，主要减少 CPU launch 和 driver dispatch 开销。

```flow
Definition / Stream Capture | 记录操作与依赖
Instantiation | 校验并生成 cudaGraphExec_t
Replay | 一次 cudaGraphLaunch 提交整张图
Update / Re-record | 参数或拓扑变化时更新、重新捕获
```

Graph 适合操作序列重复、shape 集合有限、CPU 提交成为瓶颈的 workload。重放时的 kernel、参数和内存地址受到约束；动态控制流、频繁变化的 shape 和依赖 CPU 的逻辑会增加重录或 graph break。参数小改动有机会更新 executable graph，拓扑或 node 类型发生较大变化时通常需要重新实例化。

Graph replay 只出现一次 `cudaGraphLaunch`，不会在重放时重新经过每个普通 `cudaLaunchKernel`。因此，若调度器只拦截普通 kernel launch，它对 graph 内部每个 kernel 不再拥有同样的提交控制。设计时需要明确选择：

- 把整张 Graph 作为调度单元；
- 在捕获或建图阶段改写 node 和依赖；
- 对需要细粒度控制的区域不用 Graph；
- 按有限 shape 建立多个 graph，并把重录成本和显存占用计入策略。

CUDA Graph 的创建、实例化和重放语义见 [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cuda-graphs.html)；PyTorch 对静态地址、动态 shape 和 graph-safe 代码的限制见 [PyTorch CUDA semantics](https://docs.pytorch.org/docs/stable/notes/cuda.html)。

## PyTorch 自定义 CUDA 算子的开发闭环

如果目标是优化一个确定的算子，更直接的路径是写 C++/CUDA Extension，而不是拦截所有 launch：

1. 用 PyTorch reference 实现定义语义，准备连续、非连续、空 tensor、不同 shape/dtype 的测试。
2. 注册算子 schema、CPU/CUDA 实现、FakeTensor/meta kernel，并处理 autograd。
3. 先保证边界检查、stream 使用、错误检查和数值结果正确。
4. 用 profiler 判断瓶颈属于访存、计算、同步还是 launch，而不是先猜优化点。
5. 依次检查内存合并访问、tile 与 shared memory 复用、register 压力、occupancy、warp divergence、融合和 Tensor Core 对齐。
6. 与 PyTorch 原实现比较延迟、吞吐、数值误差和不同 shape 下的稳定性。

PyTorch 官方的扩展流程见 [Custom C++ and CUDA Operators](https://docs.pytorch.org/tutorials/advanced/cpp_custom_ops.html)。成熟的 GEMM 或 Attention kernel 还涉及更复杂的 tiling、异步搬运、流水线和架构特化，不能把“会写基础 kernel”表述成已经具备成熟库级优化经验。

## 高频追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 给一个普通 PyTorch 训练脚本，编排 kernel launch 应该改哪里？</div>
<div class="qa-a">
<p>先看目标。如果是替换某个低效算子，我会在 PyTorch C++/CUDA 扩展或编译器层实现；如果希望用户模型代码基本不变，并在多个训练进程之间协调尚未提交的 kernel，可以考虑在 CUDA Runtime/Driver API 边界包装 launch，再交给独立调度器决定提交时机。后一种方案不能只拦截一个函数，还必须维护 stream、event、同步、异步内存操作和参数生命周期，并验证 CUDA Graph 和第三方库走的实际提交路径。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CUDA Graph 和 kernel launch 拦截是什么关系？</div>
<div class="qa-a">
<p>普通执行每个 kernel 都有一次 launch，拦截器可以在真实提交前排队。CUDA Graph 先记录整段操作，重放时通过一次 <code>cudaGraphLaunch</code> 提交，所以普通 launch hook 看不到每个 node 的再次提交。此时可以把整张 graph 当作调度单位，或者在建图阶段处理 node；如果仍要逐 kernel 控制，就需要放弃这部分 graph 化，同时承担更高的 CPU 提交开销。</p>
</div>
</div>

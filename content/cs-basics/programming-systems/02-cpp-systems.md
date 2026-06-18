## 一句话结论

C++ 在 AI Infra 里占据 Python 之下的性能关键路径——训练框架、推理引擎、通信库、算子 runtime 都靠它扛吞吐，所以面试 C++ 的考点也都围绕这条路径：RAII/智能指针管资源、move/allocator 抠内存性能、mutex/atomic 做并发、动态库/ABI 处理链接加载、perf/gdb/sanitizer 做性能排障。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 编程与系统工程基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕编译链接、C++、内存、智能指针、调试和工程排障建立系统编程答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>C++ 在 AI Infra 中为什么重要</h3><p>训练框架、推理引擎、通信库、算子 runtime 和高性能服务里，C++ 常处在 Python 之下的性能关键路径。</p></div>
<div class="card card-d"><h3>高频考点</h3><table><tr><th>方向</th><th>基础概念</th><th>AI Infra 场景</th></tr><tr><td>资源管理</td><td>RAII、析构、智能指针</td><td>CUDA stream、buffer、socket 自动释放</td></tr><tr><td>内存性能</td><td>move、拷贝、省略、allocator</td><td>减少 tensor metadata 拷贝</td></tr><tr><td>并发同步</td><td>mutex、atomic、condition_variable</td><td>调度队列、异步回调</td></tr><tr><td>链接加载</td><td>动态库、符号、ABI</td><td>CUDA/NCCL 插件加载失败</td></tr><tr><td>性能排查</td><td>perf、gdb、sanitizer</td><td>CPU hotspot、死锁、越界、泄漏</td></tr></table></div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

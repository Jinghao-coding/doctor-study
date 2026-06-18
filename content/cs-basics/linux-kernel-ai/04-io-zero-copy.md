## 一句话结论

大模型权重加载是典型系统瓶颈：权重几十到几百 GB 要穿过磁盘、page cache、用户态 buffer、反序列化、CPU 内存、pinned memory 再到 GPU HBM，路径不合理 GPU 就一直空等。优化围绕减少拷贝展开——mmap 省掉 page cache 到用户态的拷贝、Direct I/O 绕过 page cache 避免污染、sendfile 做文件到网络的零拷贝，落地还要叠加并行 shard、pinned memory 和 NUMA-aware 加载。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Linux Kernel for AI Infra |
| 章节类型 | 机制类 |
| 解决问题 | 围绕 NUMA、cgroup、hugepage、THP、IO、zero-copy 等内核机制建立 AI Infra 系统答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 大模型权重加载为什么是系统瓶颈？

大模型权重可能是几十 GB、几百 GB，甚至 TB 级分片。加载路径涉及：

```text
磁盘 / 网络存储
文件系统
page cache
用户态 buffer
反序列化
CPU 内存
pinned memory
GPU HBM
```

如果路径不合理，GPU 会一直等待权重或 batch 数据。典型问题包括：

- page cache 抖动；
- CPU 拷贝过多；
- 上下文切换频繁；
- 小 I/O 太多；
- 反序列化慢；
- NUMA 不匹配；
- PCIe 拷贝慢。

## 传统 read/write 路径

以从磁盘读取权重到用户态为例：

```cpp
read(fd, user_buffer, size);
```

典型路径是：

```flow
磁盘 / SSD | 权重或数据集 shard
DMA | 存储设备把数据搬到内核
Kernel Page Cache | 内核页缓存
CPU copy | 从 page cache 拷贝到用户态
User Buffer | 应用自己的 buffer
```

至少涉及：

```text
1 次 DMA：磁盘 → 内核 page cache
1 次 CPU copy：page cache → 用户态 buffer
```

如果之后还要拷贝到 GPU：

```flow
User Buffer | CPU 内存中的 tensor buffer
cudaMemcpyAsync | H2D 拷贝
GPU HBM | 进入 GPU 显存
```

整体可以理解为：

```text
磁盘 → page cache → user buffer → GPU HBM
```

其中：

- 磁盘 → page cache：DMA。
- page cache → user buffer：CPU 拷贝。
- user buffer → GPU HBM：DMA，经 PCIe/NVLink 相关路径。

## read/write 的上下文切换

以阻塞 `read()` 为例，典型过程是：

```flow
用户态调用 read() | 应用进入 syscall
陷入内核态 | 内核检查 fd、page cache、权限等
发起 I/O 或拷贝 | cache miss 时发起磁盘 I/O
进程 sleep | 数据未就绪时被调度出去
I/O 完成唤醒 | 中断或 completion 唤醒进程
返回用户态 | read 返回给应用
```

从用户进程视角，至少有：

```text
用户态 → 内核态
内核态 → 用户态
```

如果 I/O 阻塞，还会有：

```text
进程调度出去
I/O 完成后再调度回来
```

对于大量小文件、小 read，系统调用和上下文切换开销会非常明显。

传统 `write()` 类似：

```flow
User Buffer | 应用待写数据
CPU copy | 拷贝进入内核
Kernel Page Cache | 写入页缓存
DMA | 后台刷盘
Disk / SSD | 持久化存储
```

如果写网络 socket：

```text
User Buffer → Kernel Socket Buffer → NIC DMA → Network
```

传统路径的主要问题是用户态和内核态之间多次拷贝、系统调用次数多、上下文切换多、page cache 可能污染。

## mmap：把文件映射到地址空间

`mmap` 可以把文件映射到进程虚拟地址空间。

传统 read：

```text
read(fd, user_buffer, size)
```

mmap：

```text
ptr = mmap(file)
直接访问 ptr[i]
```

访问路径变成：

```flow
文件 | 权重文件或 shard
Page Cache | 内核缓存文件页
用户虚拟地址映射 | 应用像访问内存一样访问文件内容
```

相比 `read()` 的：

```text
磁盘 → page cache → user buffer
```

`mmap()` 可以避免：

```text
page cache → user buffer 的显式 CPU 拷贝
```

因为用户态虚拟地址直接映射到 page cache 对应的物理页。

这对大权重文件有价值：

- 不用一次性 read 到用户 buffer。
- 可以按需 page fault 加载。
- 多个进程可以共享同一份 page cache。
- 减少用户态额外内存副本。

### mmap 的代价

mmap 不是万能的，它的问题包括：

1. **page fault 开销**：第一次访问页面时，如果页面不在内存中，会触发 page fault。
2. **随机访问可能导致大量缺页**：访问模式很随机时可能造成 page fault 风暴。
3. **预取策略需要调优**：可以配合 `madvise`。
4. **仍然要拷贝到 GPU**：mmap 优化文件到 CPU 地址空间，不代表权重自动进入 GPU HBM。

加载模型时仍然可能需要：

```text
mmap file
  → CPU 解析 tensor metadata
  → cudaMemcpyAsync
  → GPU HBM
```

### mmap 适合什么？

适合：

- 大文件；
- 只读权重；
- 多个 worker / 进程共享；
- 按需加载；
- 随机访问部分权重；
- 减少用户态 buffer 副本。

不适合：

- 极端顺序大吞吐且希望绕过 page cache；
- 对 page fault 抖动极敏感；
- 访问模式不可预测；
- 文件生命周期很短。

## Direct I/O：绕过 page cache

Direct I/O 通常指使用 `O_DIRECT` 绕过 page cache。

传统 buffered I/O：

```text
Disk → Page Cache → User Buffer
```

Direct I/O：

```text
Disk → User Buffer
```

它主要优化三点：

1. **避免 page cache 污染**：大模型权重文件巨大，一次加载可能把 page cache 塞满，挤掉其他服务热数据。
2. **减少一层缓存管理**：不经过 page cache，可以减少内核缓存管理开销。
3. **让应用自己控制缓存**：高性能推理引擎或存储系统可以自己管理 buffer、预取、对齐和生命周期。

Direct I/O 的代价是要求更严格：

- buffer 地址对齐；
- I/O size 对齐；
- file offset 对齐；
- 通常需要较大的 I/O 粒度；
- 绕过 page cache 后重复读取不会自动命中缓存；
- 应用自己要做缓存；
- 小 I/O 性能可能更差。

适合：

- 大文件顺序读取；
- 应用自己做缓存；
- 不希望污染 page cache；
- 权重只加载一次；
- 存储吞吐很高。

不适合：

- 大量小随机 I/O；
- 希望依赖 page cache 加速重复访问；
- 应用不想处理对齐和 buffer 管理。

## sendfile 与零拷贝

`sendfile()` 用于在两个文件描述符之间传输数据，典型是：

```text
文件 fd → socket fd
```

传统用户态转发：

```text
read(file_fd, user_buffer)
write(socket_fd, user_buffer)
```

路径是：

```flow
Disk | 文件数据
Kernel Page Cache | 内核缓存
User Buffer | 进入用户态
Kernel Socket Buffer | 再回内核 socket buffer
NIC | 发送网络
```

`sendfile()` 优化后，路径可以接近：

```flow
Disk | 文件数据
Kernel Page Cache | 内核页缓存
Socket Buffer / NIC | 直接进入网络发送路径
Network | 发给远端节点
```

它主要减少：

- 内核态 → 用户态的数据拷贝；
- 用户态 → 内核态的数据拷贝；
- 系统调用次数；
- 上下文切换；
- CPU cache 污染。

适合：

- 文件服务器；
- 模型权重分发服务；
- HTTP 静态文件下载；
- 节点间传输 checkpoint / shard。

sendfile 对 GPU 加载的最终一步不是主要路径。GPU 加载通常是：

```text
Disk → CPU memory/page cache → GPU HBM
```

而 sendfile 更适合：

```text
Disk/File → Network Socket
```

所以它更适合模型分发链路，而不是单机内权重进入 GPU HBM 的最终一步。

## 四种 I/O 方式对比

| 方式 | 数据路径 | 优点 | 缺点 | 适合场景 |
|---|---|---|---|---|
| read/write | Disk → Page Cache → User Buffer | 简单、通用、兼容性好 | 多一次用户态拷贝，syscall 开销明显 | 普通文件读取、小中型文件 |
| mmap | Disk → Page Cache → 用户虚拟地址映射 | 少一次用户态拷贝，按需加载，多进程共享 page cache | page fault 抖动，访问模式影响大 | 大权重文件、只读模型、按需访问 |
| Direct I/O | Disk → User Buffer | 绕过 page cache，避免缓存污染，应用可控 | 对齐要求高，小 I/O 不友好，需自管缓存 | 大文件顺序读、高性能存储、一次性加载 |
| sendfile | Disk/Page Cache → Socket/NIC | 避免数据进用户态，减少拷贝和 syscall | 主要用于文件到网络，不适合复杂解析 | 模型分发、文件服务、checkpoint 传输 |

## 大模型权重加载优化思路

以推理服务加载大模型为例，典型链路是：

```flow
NVMe / Network Storage | 本地盘、远端盘、对象存储或分布式文件系统
File System | 文件系统和内核 I/O 路径
Page Cache 或 Direct I/O Buffer | buffered I/O 或 O_DIRECT
User-space Runtime | 推理框架或模型加载器
Tensor Metadata Parsing | 解析 safetensors / checkpoint metadata
CPU Tensor Buffer / Pinned Memory | 准备 H2D 的 CPU 侧 buffer
GPU HBM | 最终进入 GPU 显存
```

优化目标是：

- 减少拷贝；
- 减少 page fault 抖动；
- 提高 I/O 并行度；
- 匹配 NUMA；
- 避免 page cache 污染；
- 让 GPU 尽早拿到可用权重。

常见手段：

1. **使用 safetensors 等更易 mmap 的格式**。
   相比复杂 pickle 反序列化，结构化、连续、可 mmap 的权重格式更容易做按需加载和并行加载。

2. **并行加载 shard**。
   大模型通常有多个 shard，可以多线程并行读取，但不要超过磁盘队列和 CPU 解码能力，不要造成 page cache 抖动，不要跨 NUMA 搬运数据。

3. **使用 pinned memory 加速 H2D**。
   CPU 到 GPU 拷贝建议使用 pinned memory，这样 DMA 更高效，也更容易与计算 overlap。

4. **做 NUMA-aware loading**。
   GPU 0-3 挂 Socket 0，GPU 4-7 挂 Socket 1 时，权重加载线程也应该分组，避免 Socket 1 读入内存再跨 Socket 给 GPU 0。

5. **控制 page cache**。
   权重只加载一次，可以考虑 Direct I/O、`posix_fadvise(DONTNEED)`、`madvise(DONTNEED)`；权重会反复加载或多个进程共享，则 mmap + page cache 可能更合适。

## 面试综合回答模板

I/O 方面，传统 `read` 路径通常是磁盘 DMA 到 page cache，再 CPU copy 到用户 buffer，如果再加载到 GPU，还要从 CPU buffer 拷贝到 GPU HBM。`mmap` 可以把文件映射到进程地址空间，减少 page cache 到 user buffer 的一次拷贝，但可能引入 page fault 抖动。Direct I/O 绕过 page cache，适合大文件顺序读和不希望污染 page cache 的场景，但需要处理对齐和缓存管理。`sendfile` 则适合文件到网络 socket 的零拷贝传输，例如模型权重分发，减少数据进入用户态带来的拷贝和上下文切换。对于大模型权重加载，实际优化要结合 mmap/Direct I/O、并行 shard 加载、pinned memory、NUMA-aware loading 和 page cache 控制综合设计。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: mmap、Direct I/O、sendfile 在大模型系统中分别适合哪里？</div>
<div class="qa-a"><p><code>mmap</code> 适合只读大权重文件、按需加载和多进程共享 page cache；Direct I/O 适合大文件顺序读取、应用自己做缓存且不希望污染 page cache 的场景；<code>sendfile</code> 适合模型权重分发、checkpoint 文件传输或静态文件服务，因为它优化的是文件到 socket 的路径。真正把权重加载进 GPU HBM 时，通常还需要 CPU 侧解析和 H2D 拷贝，sendfile 不是最终一步的主要优化。</p><div class="qa-summary">面试口径：mmap 优化文件到地址空间，Direct I/O 优化缓存控制，sendfile 优化文件到网络。</div></div>
</div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

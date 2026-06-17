## 一句话结论

虚拟内存给每个进程独立地址空间，MMU 把虚拟地址翻译成物理地址，TLB 缓存翻译结果；普通页 4KB，大页 2MB/1GB 能减少页表项、扩大 TLB 覆盖、降低 TLB miss 和 page table walk 开销。THP 是内核自动把普通页合并成大页的透明大页机制，用着方便但透明不等于免费——page fault 分配大页、khugepaged 合并、compaction 碎片整理和大页拆分都可能引入延迟抖动。所以大页是吞吐和延迟稳定性的权衡：稳定吞吐型任务可能受益，在线推理等 P99 敏感服务通常设为 never 或 madvise，到底开不开要 benchmark。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Linux Kernel for AI Infra |
| 章节类型 | 机制类 |
| 解决问题 | 围绕 NUMA、cgroup、hugepage、THP、IO、zero-copy 等内核机制建立 AI Infra 系统答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 虚拟内存、物理内存和 MMU

**虚拟内存** 是操作系统给每个进程提供的独立地址空间。进程看到的是虚拟地址，不是直接的物理 DRAM 地址。

虚拟内存带来的好处包括：

1. **隔离性**：进程 A 不能随便访问进程 B 的内存。
2. **地址空间连续**：进程以为自己拥有连续地址，但底层物理页可以是离散的。
3. **按需分配**：`malloc` 后不一定马上分配物理内存，可能等第一次访问时触发 page fault。
4. **支持 mmap、共享内存、文件映射**：文件可以映射到进程地址空间。

**物理内存** 就是真实 DRAM。操作系统把物理内存切成页，常见页大小是：

```text
4KB
```

虚拟地址到物理地址的映射关系由页表维护。

**MMU** 是 **Memory Management Unit，内存管理单元**。它负责把 CPU 发出的虚拟地址转换成物理地址：

```flow
Virtual Address | CPU 发出的虚拟地址
MMU | 内存管理单元处理地址翻译
Page Table Walk | 查询页表，找到映射关系
Physical Address | 得到真实 DRAM 地址
```

为了加速地址转换，CPU 里有 **TLB**，即 Translation Lookaside Buffer，可以理解为页表转换缓存。

| 情况 | 代价 |
|---|---|
| TLB hit | 虚拟地址到物理地址转换很快 |
| TLB miss | 需要 page table walk，开销更高 |

## Huge Pages 为什么有用？

普通页通常是 4KB。Huge Page 可以是：

```text
2MB
1GB
```

使用大页的好处是：

- 同样大小的内存，需要更少页表项。
- TLB 覆盖范围更大。
- TLB miss 更少。
- page table walk 开销更低。

例如映射 1GB 内存：

| 页大小 | 需要页数量 |
|---|---:|
| 4KB page | 262144 个页 |
| 2MB huge page | 512 个页 |
| 1GB huge page | 1 个页 |

对大模型训练/推理，动辄几十 GB 到几百 GB 的 host memory、KV cache staging、权重加载缓存、数据集缓存，大页可能减少 TLB 压力。

## THP：透明大页

**Transparent Huge Pages，THP** 是 Linux 的透明大页机制。它的目标是：

```text
应用程序不显式申请 huge page
内核自动尝试把普通 4KB 页合并成 2MB 大页
```

THP 的优点是使用方便，应用无需修改代码。但它的问题是：**透明不等于免费**。

内核可能在运行时做：

- page fault 时分配大页；
- 后台 `khugepaged` 合并页面；
- 内存碎片整理 compaction；
- 页面拆分 split。

这些操作可能引入延迟抖动。

## 为什么深度学习系统中经常建议关闭 THP？

很多在线服务、数据库、低延迟推理系统会建议关闭 THP，原因不是“大页一定不好”，而是 THP 的自动行为可能不稳定。

### THP 可能导致延迟尖刺

当内核尝试分配 2MB 连续物理内存时，如果内存碎片严重，可能触发 compaction。

这会导致：

- 请求延迟突然升高；
- DataLoader 卡顿；
- 推理 P99/P999 抖动。

### THP 的收益不稳定

深度学习系统里有大量内存分配模式：

- 小对象；
- 临时 buffer；
- pinned memory；
- DataLoader batch；
- mmap 权重；
- CUDA runtime 内存；
- 通信 buffer。

不一定都适合自动大页。

### 可能影响内存回收

大页拆分、合并、回收比普通 4KB 页复杂，内存压力大时可能加剧抖动。

### 可能影响 fork / copy-on-write

某些数据加载或服务启动模式中，如果进程使用 fork，THP 可能让 copy-on-write 的粒度变大，造成额外内存开销。

## THP 一定要关闭吗？

不是。更准确的说法是：

> **吞吐型、长时间运行、内存访问模式稳定的任务可能从大页受益；低延迟、强稳定性、容易受内存碎片影响的在线服务通常倾向关闭 THP 或设为 madvise。**

常见策略：

```text
always   ：尽量对所有匿名内存使用 THP
madvise  ：只有应用显式 madvise 时才使用 THP
never    ：禁用 THP
```

在深度学习系统中，可以这样理解：

| 场景 | 常见策略 | 原因 |
|---|---|---|
| 在线推理服务 | `never` 或 `madvise` | 更关注 P99/P999 稳定性 |
| 离线训练任务 | benchmark 后决定 | 可能收益来自 TLB miss 降低，也可能收益不明显 |
| 数据库/参数服务 | 通常 `never` 或 `madvise` | 避免 compaction 和回收抖动 |
| 大规模 CPU 内存扫描 | 可能受益 | 访问模式稳定、TLB 压力大 |

如果某个训练任务主要瓶颈是 TLB miss 或大规模 CPU 内存扫描，THP 可能有收益；如果主要瓶颈是 GPU 计算或 I/O，THP 收益可能不明显，反而可能带来抖动。

## 显式 HugeTLB 与 THP

还有一种方式是显式 HugeTLB：

```text
提前预留 huge pages
应用显式使用
行为更可控
```

| 机制 | 使用方式 | 优点 | 缺点 |
|---|---|---|---|
| 普通 4KB 页 | 默认 | 稳定、灵活 | TLB 覆盖范围小 |
| THP | 内核自动 | 应用无感，可能提升吞吐 | 可能引入延迟抖动 |
| HugeTLB | 显式预留/使用 | 可控、稳定 | 配置复杂，灵活性差 |

## 和大模型训练/推理的关系

大模型系统里，Linux 内存管理会影响：

- 权重加载时的 page cache 行为；
- mmap 权重文件的 page fault；
- DataLoader worker 的内存分配；
- pinned memory 是否能稳定分配；
- 容器 memory limit 下的 reclaim；
- THP compaction 对 P99 的影响；
- NUMA node 本地内存是否足够；
- fork + copy-on-write 的额外内存开销。

```flow
模型权重 / batch 数据 | 文件、网络或对象存储进入 CPU 侧
虚拟内存映射 | malloc / mmap / page cache
MMU + TLB | 地址翻译影响 CPU 侧访问效率
THP / HugeTLB | 可能降低 TLB miss，也可能引入抖动
Pinned Memory | H2D DMA 前的关键缓冲区
GPU HBM | 最终进入模型计算路径
```

## 面试回答模板

虚拟内存是操作系统给每个进程提供的独立地址空间，物理内存是真实 DRAM，MMU 负责把虚拟地址翻译成物理地址，TLB 用来缓存地址翻译结果。普通页通常是 4KB，大页可以是 2MB 或 1GB，可以减少页表项数量、扩大 TLB 覆盖范围、降低 TLB miss。THP 是 Linux 的透明大页机制，内核自动尝试把普通页合并为大页。它可能提升大内存顺序访问吞吐，但也可能因为 page fault、内存碎片整理、`khugepaged` 合并和大页拆分引入延迟抖动。在深度学习系统里，离线训练是否开启 THP 要 benchmark；在线推理或对 P99 敏感的服务通常更倾向关闭 THP 或设置为 `madvise`。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么在线推理服务常建议关闭 THP？</div>
<div class="qa-a"><p>因为在线推理更关注 P99/P999 稳定性，而 THP 可能在 page fault、内存碎片整理、页面合并或拆分时引入延迟尖刺。THP 对大内存顺序访问可能有吞吐收益，但这种收益不一定能覆盖推理服务对低抖动的要求。因此生产上常设为 <code>never</code> 或 <code>madvise</code>，具体还要 benchmark。</p><div class="qa-summary">面试口径：THP 是吞吐和延迟稳定性的权衡，不是绝对开或关。</div></div>
</div>

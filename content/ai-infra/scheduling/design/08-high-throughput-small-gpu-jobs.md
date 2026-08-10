## 题目描述

已有一个 GPU 集群调度平台，现在要在这个平台基础上优化调度策略。集群由一批机器组成，每台机器有若干张 GPU 卡；GPU 型号不同，显存容量不同；每台机器的 CPU、内存和 GPU 配比也不固定，也就是“一张卡对应多少 CPU / host memory”并不一致。

作业侧的特点是：每天有几千万个作业，每个作业本质上是一个 C++ 进程；每个作业只占几 GB GPU 显存，通常打不满一张卡，同时还会消耗一定 CPU 和 host memory；单个作业运行几分钟到几十分钟，运行完成后释放资源。题目目标是在平台已经存在的前提下，把这些海量短作业更高效地调度到 GPU 卡和机器上，提高整体资源利用率，并最大化作业吞吐量。

## 输入、输出与约束

| 类别 | 内容 | 需要澄清的点 |
|---|---|---|
| 输入资源 | 机器、GPU 型号、GPU 显存、CPU、host memory、当前占用 | 是否能拿到每张卡剩余显存和每台机器剩余 CPU/内存 |
| 输入作业 | C++ 进程、GPU 显存需求、CPU/内存需求、预计运行时长、优先级 | 作业资源是用户申报、历史画像，还是平台可预测 |
| 输出决策 | 作业放到哪台机器、哪张 GPU、同卡并发多少 | 需要原子 reserve，避免并发调度重复分配 |
| 硬约束 | 显存必须够，CPU/内存必须够，GPU 型号必须兼容 | 显存是主瓶颈，但不是唯一约束 |
| 优化目标 | GPU 显存利用率、作业吞吐、队列等待时间、失败率 | 不能只看平均 GPU-Util |
| 规模约束 | 每天几千万作业 | 调度器自身吞吐和候选召回效率非常关键 |

## 非目标

| 非目标 | 为什么先不做 |
|---|---|
| 从零设计调度平台 | 题设说平台已经存在，重点是改造调度策略和观测闭环 |
| 大模型训练 Gang Scheduling | 本题作业是单进程短作业，不是多 worker 同起同停 |
| 复杂拓扑感知训练调度 | 每个作业只占几 GB 显存，核心矛盾先是同卡装箱和机器多维配比 |
| 只追求单作业性能最优 | 目标是整体吞吐和利用率，允许在可控范围内做同卡并发 |

## 题目边界

| 维度 | 题设信息 | 调度含义 |
|---|---|---|
| 集群 | 多台机器，每台若干 GPU，GPU 型号和显存不同 | 需要按 GPU flavor / memory capacity 分池 |
| 配比 | 每台机器 CPU/内存/GPU 配比不固定 | 不能只看 GPU 显存，还要防 CPU/内存成为残余瓶颈 |
| 作业 | 每天几千万个 C++ 进程，几分钟到几十分钟 | 高 QPS 在线调度，调度器吞吐和队列系统本身是关键 |
| 资源 | 每个作业用几 GB 显存，同时消耗 CPU/内存 | 显存是主瓶颈，但必须做多维约束过滤 |
| 目标 | 提高整体资源利用效率、最大化吞吐 | 优先减少 GPU 显存碎片和机器残余资源浪费 |
| 前提 | 平台已经存在 | 不是从零造平台，而是分阶段改造调度策略和观测闭环 |

## 总体思路

```flow
先建画像 | 作业资源需求、运行时长、GPU 型号、机器 CPU/内存/GPU 配比
再分资源池 | 按 GPU 型号/显存容量/机器配比拆池，避免强弱卡混用
做快速匹配 | 维护每张卡剩余显存和机器剩余 CPU/内存的索引
在线装箱 | 显存主导 best-fit，CPU/内存做硬约束，减少碎片
短作业回填 | 用预计时长短的作业填碎片，避免大块资源空等
反馈校准 | 采集实际显存峰值、CPU/内存、运行时长，修正画像
```

## 先做什么

<div class="card card-m">
<h3>第一步：把问题量化，而不是先改算法</h3>
<p>已有平台上最先做的是观测和画像。没有资源画像，调度器只能按用户申报或静态规则调度，很容易出现显存碎片、CPU/内存残余无法利用、某些 GPU 型号过热、队列延迟变长等问题。</p>
</div>

| 要采集什么 | 为什么 |
|---|---|
| 每个作业 requested / actual GPU memory peak | 判断申报是否保守，建立显存预测或修正系数 |
| CPU cores、RSS memory、I/O、运行时长分布 | 做多维约束和短作业 backfill |
| GPU 型号、总显存、当前剩余显存、显存碎片 | 做 flavor 分池和 best-fit |
| 机器 CPU/内存/GPU 配比 | 找出“GPU 有剩余但 CPU/内存不够”的结构性碎片 |
| 队列等待时间、调度耗时、失败/重试原因 | 判断瓶颈在资源不足、匹配算法还是调度器吞吐 |

## 资源建模

<div class="card card-s">
<h3>资源向量</h3>
<p>每个作业可以抽象成 <code>(gpu_mem, cpu, host_mem, duration, gpu_flavor_constraint)</code>，每张 GPU / 每台机器维护剩余向量。匹配时 GPU 显存是主排序维度，CPU 和 host memory 是硬约束。</p>
</div>

| 模型 | 作用 | 注意点 |
|---|---|---|
| GPU flavor | 区分 A10/A100/H100 等不同显存和性能 | 不同卡性能不同，吞吐目标不能只看作业数 |
| GPU memory slice | 每个作业几 GB 显存，可在同卡放多个进程 | 需要 runtime 隔离和显存上限，否则 OOM 会互相影响 |
| CPU / host memory | C++ 进程也吃 CPU 和内存 | 机器配比异构时，CPU/内存会造成“剩余显存不可用” |
| duration | 几分钟到几十分钟 | 可用于短作业优先、backfill 和释放时间预测 |
| interference | 同卡多进程可能有 SM/HBM/PCIe 干扰 | 不能只按显存装满，还要监控性能退化 |

## 调度算法

```flow
入队 | 校验资源画像，按 GPU flavor / 优先级 / 时长分队列
候选召回 | 从索引里找剩余显存足够且 CPU/内存足够的机器和 GPU
硬约束过滤 | GPU 型号、显存、CPU、host memory、租户/故障域
打分排序 | best-fit 显存、减少机器残余碎片、保持负载均衡
绑定启动 | 原子扣减资源，启动 C++ 进程，设置显存/CPU/内存限制
运行反馈 | 采集峰值和时长，完成后释放资源并更新预测
```

<div class="card card-d">
<h3>主策略：显存主导的 Best-Fit Decreasing</h3>
<p>把等待队列中可调度的一批作业按显存需求从大到小处理；每个作业优先放到“刚好能容纳它”的 GPU 上，减少大卡被小作业打散。CPU/内存作为机器级硬约束，防止显存够但进程跑不起来。</p>
</div>

<div class="card card-w">
<h3>为什么不是简单 first-fit</h3>
<p>first-fit 容易把小显存作业随机塞到大显存卡上，造成大作业找不到连续剩余显存。best-fit 会优先消耗最贴近需求的碎片，保留大块显存给后续大作业。</p>
</div>

| 策略 | 适合点 | 风险 |
|---|---|---|
| First Fit | 实现简单、调度快 | 碎片大，异构资源浪费明显 |
| Best Fit | 减少显存碎片 | 需要维护高效索引，局部最优 |
| Best Fit Decreasing | 批量调度时更稳定 | 等待成批会增加一点调度延迟 |
| Backfill | 利用短作业填碎片 | 需要运行时长估计，估错会影响后续作业 |
| Load Balancing | 避免热点机器 | 可能牺牲装箱效率 |

## 高吞吐工程实现

这个题有“每天几千万作业”的量级，回答时必须提调度器自身吞吐。

| 模块 | 做法 |
|---|---|
| 资源索引 | 按 GPU flavor 建池；每个池维护按剩余显存排序的 GPU set；机器维度维护 CPU/内存剩余 |
| 批量调度 | 每轮取一批 pending jobs，批内排序和匹配，减少锁和数据库/API 往返 |
| 乐观扣减 | scheduler cache 里先 reserve，启动失败再 rollback，避免并发重复分配 |
| 分片调度器 | 按资源池、租户或队列 shard，多实例并行调度 |
| 热路径缓存 | 避免每个作业全量扫描所有机器，候选召回只查相关 flavor / memory bucket |
| 限流与降级 | 高峰期先用近似 best-fit，观测恢复后再做更精细 defrag |

## 后做什么

```flow
阶段 1 | 资源画像、峰值采集、队列等待和碎片指标
阶段 2 | GPU flavor 分池、显存 best-fit、多维硬约束过滤
阶段 3 | 批量调度、短作业 backfill、运行时长估计
阶段 4 | 预测 requested memory/duration，自动修正用户申报
阶段 5 | 干扰感知、碎片整理、跨池迁移或重启策略
```

| 阶段 | 目标 | 产出 |
|---|---|---|
| 1. Baseline | 先知道浪费在哪里 | GPU memory utilization、CPU/memory residual、queue time、失败原因 |
| 2. 装箱 | 提高显存利用率 | flavor pool、best-fit、candidate index |
| 3. 吞吐 | 支撑几千万作业规模 | batch scheduling、scheduler shard、cache reserve |
| 4. 预测 | 降低过度申报和 OOM | memory peak estimator、duration estimator、安全余量 |
| 5. 治理 | 长期稳定运行 | defrag、干扰检测、SLO/告警、容量规划 |

## 关键权衡

| 权衡 | 回答口径 |
|---|---|
| 利用率 vs 隔离 | 同卡多进程能提高显存利用率，但要限制显存、CPU 和监控干扰 |
| 装箱效率 vs 调度延迟 | 几千万作业不能每次全局最优，必须用索引和近似算法 |
| 显存利用 vs CPU/内存残余 | 主维度是显存，但 CPU/内存配比异构会让剩余显存不可用 |
| 大作业 vs 小作业 | 大显存作业优先保留大块，小作业用 backfill 填碎片 |
| 预测激进 vs OOM | 预测可减少保守申报，但必须加安全余量和失败回退 |

## 图形化回答

```flow
作业队列 | job=(gpu_mem,cpu,mem,duration,flavor)
画像修正 | actual peak + runtime feedback
资源池索引 | flavor -> remaining gpu memory buckets
多维过滤 | GPU memory + machine CPU/memory + policy
Best-Fit 打分 | 最小剩余显存 + 最少机器残余碎片
绑定执行 | reserve -> launch process -> monitor -> release
```

## 回答结构

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 面试里如何回答这个场景题？</div>
<div class="qa-a">
<div class="qa-section"><div class="qa-section-title">1. 先复述本质</div><p>这是海量短作业在异构 GPU 集群上的在线多维装箱问题。主瓶颈是 GPU 显存，但 CPU/内存配比异构会影响可用性，目标是在调度延迟可控的前提下提高显存利用率和作业吞吐。</p></div>
<div class="qa-section"><div class="qa-section-title">2. 先做观测和画像</div><p>我不会一上来改算法，而是先采集 requested/actual GPU memory、CPU、host memory、运行时长、队列等待、调度耗时、失败原因和碎片指标，建立 baseline。</p></div>
<div class="qa-section"><div class="qa-section-title">3. 再做资源池和索引</div><p>按 GPU 型号和显存容量分池，维护每张 GPU 的剩余显存、每台机器的剩余 CPU/内存，用 memory bucket 或有序结构快速找候选，避免全量扫描。</p></div>
<div class="qa-section"><div class="qa-section-title">4. 调度策略</div><p>核心用显存主导的 best-fit/bin packing：优先把作业放到刚好能容纳的 GPU 上，CPU/内存做硬约束；批量调度时按显存需求从大到小，短作业可以 backfill 碎片窗口。</p></div>
<div class="qa-section"><div class="qa-section-title">5. 工程化和迭代</div><p>为了支撑几千万作业，需要 batch scheduling、scheduler cache reserve、分片调度器和失败 rollback。后续再引入显存/时长预测、干扰检测、defrag 和容量规划。</p></div>
<div class="qa-summary">先量化浪费，再按 GPU flavor 分池，用显存 best-fit 做在线多维装箱，靠批量调度和反馈预测把吞吐做上去。</div>
</div>
</div>

## 高频追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 为什么主维度是显存，不是 GPU 利用率？</div>
<div class="qa-a"><p>题设里每个 C++ 作业只用几 GB 显存，显然打不满一张卡，卡住的是一张 GPU 上能同时放多少进程。GPU-Util / SM 利用率当然也要看，但调度入口首先要保证显存可容纳且不 OOM；后续才用利用率和干扰指标决定是否继续提高同卡并发。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: CPU/内存配比异构怎么处理？</div>
<div class="qa-a"><p>把机器看成 GPU 显存 + CPU + host memory 的多维资源。候选 GPU 显存够只是第一步，还要检查所在机器剩余 CPU/内存是否足够。打分时惩罚会造成残余资源不可用的放置，例如剩很多显存但 CPU 被打满，或者 CPU 剩很多但显存碎掉。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 几千万作业下调度器怎么不成为瓶颈？</div>
<div class="qa-a"><p>避免每个作业扫描全集群。按 GPU flavor 分 shard，维护剩余显存 bucket / 有序索引；每轮批量取 pending jobs，批内排序后匹配；scheduler cache 里乐观 reserve，启动失败 rollback；高峰期可用近似 best-fit，牺牲一点最优性换调度吞吐。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 怎么衡量优化有效？</div>
<div class="qa-a"><p>看四类指标：GPU 显存利用率和碎片率、作业吞吐和 queue time、CPU/内存残余资源浪费、失败率/OOM/重试率。不能只看平均 GPU-Util，因为这个场景主瓶颈是显存装箱和作业调度吞吐。</p></div>
</div>

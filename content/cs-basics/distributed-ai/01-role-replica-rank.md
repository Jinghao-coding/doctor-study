## 一句话结论

Role、Replica、Rank 是分布式训练里三套不同的身份坐标：role 是「干什么活」（worker/ps/chief），replica 是「同一角色的第几个副本」，rank 是「通信世界里的全局编号」。三者不是一回事，把 Pod 名、rank 和业务角色混在一起是排查 hang 和通信错误时最常见的坑。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | 分布式 AI 基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕 role/replica/rank、通信存储、GPU/NPU 可观测性建立分布式训练和推理基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>Role、Replica、Rank</h3><p>分布式训练里，role 描述职责，replica 描述副本编号，rank 描述通信世界中的全局身份。不要把 Pod 名称、rank 和业务角色混为一谈。</p></div>
<table><tr><th>概念</th><th>含义</th><th>例子</th></tr><tr><td>Role</td><td>任务角色</td><td>worker、ps、chief、evaluator</td></tr><tr><td>Replica</td><td>同一角色下的副本</td><td>worker-0、worker-1</td></tr><tr><td>Global Rank</td><td>通信全局编号</td><td>DDP world 中 rank 0..N-1</td></tr><tr><td>Local Rank</td><td>节点内编号</td><td>一台 8 卡机器 local_rank 0..7</td></tr></table>

## 面试回答

**30 秒版：**

role 描述职责（worker/ps/chief/evaluator），replica 是同一角色下的副本编号，global rank 是整个通信 world 里的唯一身份、local rank 是节点内的卡号。NCCL 通信、checkpoint 写主、日志定位都依赖 rank，所以这套编号必须和实际卡、Pod 对应清楚。

**2 分钟版：**

我会先把三层坐标讲清楚：role 是任务角色，replica 是该角色的第几个副本，global rank 是通信组里 0..N-1 的全局编号，local rank 是单机内 0..7 的卡号。然后讲它们各自的用途：rank 0 通常承担 checkpoint 写盘、日志汇总、broadcast 源；local rank 用来绑定 CUDA_VISIBLE_DEVICES 选定本机 GPU；role 则决定进程跑训练还是评估。接着讲坑：Pod 名（worker-3）不等于 rank 3，rank 由 launcher 或 rendezvous 分配；如果 rank 和卡映射错乱，会出现某些 rank 卡住等不到、AllReduce hang。最后收束：排查分布式 hang 时，我会先确认每个 rank 的 local_rank、所在节点和 GPU 是否一一对应，再看 NCCL 日志里是哪个 rank 没进 collective。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

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

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

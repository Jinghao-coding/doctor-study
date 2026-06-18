## 一句话结论

Docker/runtime 解决「单机怎么把一个容器跑起来、限住资源」，Kubernetes 解决「一堆容器怎么调度、恢复、发现、治理」。面试里别把两者职责混在一起：镜像和 cgroup 是 runtime 层，requests/limits、QoS、controller、Service 是 K8s 层。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Linux 与容器基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕运行环境、namespace、cgroup、rootfs、Docker/K8S 资源模型建立容器基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

<div class="card card-m"><h3>Docker 与 Kubernetes 的分工</h3><table><tr><th>问题</th><th>Docker/Runtime</th><th>Kubernetes</th></tr><tr><td>环境复现</td><td>镜像、rootfs</td><td>镜像版本、拉取策略</td></tr><tr><td>资源限制</td><td>写 cgroup</td><td>requests/limits、QoS、调度</td></tr><tr><td>失败恢复</td><td>单机重启策略</td><td>Deployment/Job/StatefulSet controller</td></tr><tr><td>服务发现</td><td>基本不解决</td><td>Service、DNS、EndpointSlice</td></tr></table></div>
<div class="card card-w"><h3>QoS、RSS 和 Usage</h3><p>RSS 是进程实际驻留物理内存；cgroup usage 是容器级内存统计，包括匿名页、page cache、部分内核内存等。Pod QoS 根据 requests/limits 分为 Guaranteed、Burstable、BestEffort，影响 OOM 和驱逐优先级。</p></div>

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `专题综合题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

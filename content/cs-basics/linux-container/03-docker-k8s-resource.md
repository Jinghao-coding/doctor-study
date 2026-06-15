## 一句话结论

Docker 与 Kubernetes 的分工 是 Linux 与容器基础 的核心知识点，面试回答要先给结论，再说明机制边界、工程场景和常见误区。

## 复习定位

| 维度 | 内容 |
|---|---|
| 所属模块 | Linux 与容器基础 |
| 章节类型 | 概念类 |
| 解决问题 | 围绕运行环境、namespace、cgroup、rootfs、Docker/K8S 资源模型建立容器基础答案。 |
| 面试抓手 | 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。 |

## 阅读路径

1. 先记住本节的一句话结论，避免从细节开始散。
2. 再看核心概念、系统链路或关键机制，把知识点映射到工程场景。
3. 最后用“面试回答”收束成 30 秒版和 2 分钟版。

<div class="card card-m"><h3>Docker 与 Kubernetes 的分工</h3><table><tr><th>问题</th><th>Docker/Runtime</th><th>Kubernetes</th></tr><tr><td>环境复现</td><td>镜像、rootfs</td><td>镜像版本、拉取策略</td></tr><tr><td>资源限制</td><td>写 cgroup</td><td>requests/limits、QoS、调度</td></tr><tr><td>失败恢复</td><td>单机重启策略</td><td>Deployment/Job/StatefulSet controller</td></tr><tr><td>服务发现</td><td>基本不解决</td><td>Service、DNS、EndpointSlice</td></tr></table></div>
<div class="card card-w"><h3>QoS、RSS 和 Usage</h3><p>RSS 是进程实际驻留物理内存；cgroup usage 是容器级内存统计，包括匿名页、page cache、部分内核内存等。Pod QoS 根据 requests/limits 分为 Guaranteed、Burstable、BestEffort，影响 OOM 和驱逐优先级。</p></div>

## 面试回答

**30 秒版：**

03 docker k8s resource 是 Linux 与容器基础 中的一个基础知识点，面试回答要先给结论，再说明机制、边界和工程场景。 先讲定义，再讲链路，最后讲 AI Infra 中如何使用或排障。

**2 分钟版：**

我会先说明这个知识点在 Linux 与容器基础 里的位置，再拆核心链路：输入是什么、系统或机制如何处理、消耗哪些资源、输出什么结果。随后补充关键权衡：性能、稳定性、复杂度、可观测性和生产边界。最后用一个典型场景收束，说明如何在 AI Infra 面试里把它和 GPU、Kubernetes、调度、训练或推理系统连接起来。

## 关联模块

- `GPU 硬件与资源共享`：提供硬件、显存、互联和利用率诊断基础。
- `LLM 推理系统 / 分布式训练`：提供大模型系统中的实际落点。
- `Kubernetes / 调度与集群`：提供平台、资源和多租户治理语境。
- `系统设计题 / 论文工作`：把基础知识组织成可复述的方案和项目叙事。

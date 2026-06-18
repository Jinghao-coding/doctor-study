## 一句话结论

AI Infra 的生产链路不是“代码提交后跑一个 Job”，而是把数据集、训练配置、checkpoint、模型权重、镜像、推理配置和评测结果都变成可追踪、可回滚、可审计的制品。面试回答要强调**版本、血缘、准入和回滚**四件事。

## 核心概念

| 制品 | 解决什么问题 | 关键元数据 |
|---|---|---|
| Dataset | 训练、评测和回放的数据来源 | 版本、schema、样本量、来源、权限、质量报告 |
| Training Config | 复现实验和训练任务 | 代码 commit、镜像、超参、并行策略、资源规格 |
| Checkpoint | 训练恢复、模型导出和回滚 | step、metric、optimizer state、并行切分方式、存储路径 |
| Model Artifact | 推理部署的模型权重和 tokenizer | base model、finetune 方法、精度、量化方式、签名 |
| Container Image | 运行环境一致性 | digest、CUDA/driver 兼容、依赖版本、安全扫描结果 |
| Serving Config | 推理服务行为 | engine、tensor parallel、max tokens、batch 策略、限流策略 |
| Evaluation Report | 模型准入依据 | benchmark、线上回放、红线 case、回归结果、审批人 |

## 系统链路

```flow
数据进入 | 数据集版本、schema、权限、质量检查
训练提交 | 代码、镜像、配置、资源和数据版本绑定
运行产出 | checkpoint、日志、metrics、profile、失败事件沉淀
模型注册 | 权重、tokenizer、配置、评测报告和血缘写入 registry
部署准入 | 评测达标、安全扫描、容量预估、灰度策略确认
线上回滚 | 按模型版本、镜像 digest 和 serving config 一起回滚
```

## 关键机制

<div class="card card-s">
<h3>血缘不是文档，是平台状态</h3>
<p>模型注册时必须能回答：这个模型来自哪个 base model、哪个数据集版本、哪次训练任务、哪个 checkpoint、哪份评测报告、哪个镜像和哪份 serving config。否则线上出问题时只能靠人工猜。</p>
</div>

<div class="card card-m">
<h3>Checkpoint 与 Model Artifact 的边界</h3>
<p>Checkpoint 服务训练恢复，通常包含 optimizer state、scheduler state、随机数状态和并行切分信息；Model Artifact 服务推理部署，通常只保留权重、tokenizer、模型结构、量化参数和推理配置。两者不能混为一谈。</p>
</div>

<div class="card card-w">
<h3>镜像用 tag 不够，要用 digest</h3>
<p>生产发布不能只记录 <code>latest</code> 或普通 tag，因为 tag 可变。准入、回滚和审计应记录 image digest、构建流水线、依赖 SBOM 和安全扫描结果。</p>
</div>

## 常见误区

| 误区 | 正确说法 |
|---|---|
| 只要保存模型权重就能复现 | 还需要数据版本、代码 commit、镜像、配置、随机种子和评测结果 |
| checkpoint 就是线上模型 | checkpoint 偏训练恢复，线上模型要经过导出、转换、量化、评测和注册 |
| 模型 registry 只是文件目录 | registry 应保存元数据、血缘、权限、准入状态和版本生命周期 |
| 回滚只回滚权重 | 需要一起回滚镜像、engine 参数、tokenizer、prompt/config 和路由策略 |
| 数据质量是算法问题 | 数据 schema、缺失、重复、脏样本、权限和合规都是平台问题 |

## 关联模块

- `分布式训练平台`：训练任务产出 checkpoint 和模型制品。
- `LLM 推理系统`：模型制品进入 serving engine 后变成线上服务。
- `Kubernetes 核心`：镜像、ConfigMap、Secret、Service 和 Deployment 承载运行环境。
- `系统设计题`：资产血缘和回滚是综合设计题里的加分点。

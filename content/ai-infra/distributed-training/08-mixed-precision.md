## 常见数值格式

<div class="table-scroll">

| 格式 | 符号位 | 指数位 | 尾数位 | 训练中的特点 |
|---|---:|---:|---:|---|
| FP32 | 1 | 8 | 23 | 范围和精度较高，吞吐和显存成本也高 |
| FP16 | 1 | 5 | 10 | 精度高于 BF16，但动态范围明显小，容易溢出或下溢 |
| BF16 | 1 | 8 | 7 | 动态范围接近 FP32，精度低于 FP16，通常更易稳定训练 |

</div>

FP16 和 BF16 都占 16 bit，但“16 位”不代表数值性质相同。FP16 把更多位给尾数，局部表示更细；BF16 保留与 FP32 相同数量的指数位，因此能表示更大和更小的数量级。

TF32 不是另一种 16 位存储格式。它是 NVIDIA Tensor Core 针对 FP32 输入的一条计算路径，保留 FP32 的指数范围、降低有效尾数精度，并通常以 FP32 累加和输出。FP8 则有 E4M3、E5M2 等布局，需要更积极的缩放与校准，不能与 FP16/BF16 的训练稳定性直接等同。

## 混合精度训练链路

混合精度不是把所有 tensor 统一改成 16 位，而是根据算子的数值特性选择计算精度：

```flow
FP32 模型与优化器状态 | 保留稳定更新所需状态
autocast 前向 | GEMM/Conv 等进入 FP16 或 BF16 路径
Loss | 必要时放大
Backward | 产生低精度或 FP32 梯度
Unscale + 溢出检测 | 检查 inf/nan，再裁剪梯度
Optimizer step | 无溢出才更新参数
Scale 调整 | 根据近期溢出动态变化
```

`autocast` 负责为不同算子选择合适 dtype。矩阵乘和卷积通常适合低精度 Tensor Core；reduction、Softmax、归一化、loss 等对范围或累积误差敏感的部分，框架可能保留或提升到 FP32。具体算子策略由设备和框架实现决定。

## FP16 为什么需要 Loss Scaling

反向传播中的小梯度可能低于 FP16 的可表示范围并变成 0。设缩放因子为 $s$，先计算：

$$
L'=sL,\qquad \nabla L'=s\nabla L
$$

反向后再执行：

$$
\nabla L=\frac{\nabla L'}{s}
$$

如果出现 `inf` 或 `nan`，跳过本次参数更新并减小 scale；连续若干步没有溢出，可以增大 scale。这种动态策略在尽量保留小梯度的同时避免无限放大。

梯度裁剪必须作用在 unscale 之后，否则裁剪阈值面对的是被放大的梯度。梯度累积时也要保证同一次有效 batch 内 scale 语义一致，避免在尚未完成累积时错误地 unscale 或更新。

BF16 因为指数范围接近 FP32，通常不依赖 loss scaling 来解决范围问题，但仍可能发生数值不稳定。更大的动态范围不代表更高精度，也不保证所有模型都可以无条件切换。

PyTorch 的自动混合精度由 `torch.autocast` 和 `torch.amp.GradScaler` 提供，参见 [Automatic Mixed Precision](https://docs.pytorch.org/docs/stable/amp.html)。

## 显存和吞吐并不是简单减半

低精度可以减少参数副本、激活、梯度和通信张量中部分对象的字节数，并让适合的矩阵算子使用 Tensor Core。但 Adam 训练还可能保存 FP32 master weight、FP32 一阶和二阶动量；临时 workspace、通信 buffer、allocator 碎片也不会自动按相同比例下降。

因此显存应该拆项估算：

$$
M_{total}=M_{param}+M_{grad}+M_{optimizer}+M_{activation}+M_{workspace}+M_{communication}
$$

混合精度影响其中若干项，并不等价于 $M_{total}$ 固定减半。吞吐能否提升还取决于 shape 是否满足 Tensor Core 高效路径、是否仍受 HBM 或通信限制，以及 cast 和 scale 的额外成本。

## 调度系统如何使用精度配置

在训推混部系统中，同一个训练任务可以预先形成若干可行配置，例如：

$$
c=(precision,\ microbatch,\ checkpointing)
$$

每个配置对应一组观测或预测：

$$
profile(c)=(memory,\ throughput,\ sm,\ bandwidth,\ quality\ constraint)
$$

调度器可以在任务明确支持的配置集合内选择：低精度可能降低显存并提高吞吐，使任务更容易共置；但也可能提高 SM 或 HBM 带宽竞争。调度决策必须同时考虑单任务性能、共置干扰和收敛/精度约束。

精度通常不是可以在任意训练 step 无损切换的调度旋钮。优化器状态、loss scale、checkpoint 兼容性和收敛行为都可能受影响。更稳妥的做法是让用户或离线验证确定可接受配置，调度器只在这个集合内选择，并把切换时机和恢复语义定义清楚。

## 高频追问

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: FP16 和 BF16 都是 16 位，区别是什么？</div>
<div class="qa-a">
<p>FP16 是 1 位符号、5 位指数、10 位尾数，局部精度更细但动态范围小；BF16 是 1 位符号、8 位指数、7 位尾数，范围接近 FP32，但精度更粗。FP16 训练通常配合 loss scaling 缓解小梯度下溢；BF16 通常不依赖它解决范围问题，但仍需检查模型的数值稳定性。</p>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 混合精度如何进入任务调度？</div>
<div class="qa-a">
<p>我会把精度和 micro-batch、激活检查点一起看作经过验证的运行配置。每个配置有显存、吞吐和 SM/带宽需求，调度器在满足收敛与精度约束的候选中选择，并评估共置干扰。不能只因为 FP16 占用更小就判断它一定更适合混部，也不能假设训练过程中可以任意无损切换。</p>
</div>
</div>


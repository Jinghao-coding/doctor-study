## 同部署链如何找到

给定工作流 `P → A(Q8) → B(Q8) → C(Q8) → D(Q14)`，编译器沿拓扑顺序检查相邻边，满足下列条件才合并：

1. 前后节点都是可融合的 Agent 节点。
2. 前节点只有该后继，后节点只有该前驱，链内部没有分叉或汇合。
3. 两者部署的 `model_key` 相同，涵盖模型路径、dtype 与 serving 配置等身份。
4. 其余执行配置相同，允许每阶段 `max_new_tokens` 不同。

链首仍可以接收多个外部前驱，链尾仍可以连向多个外部后继。约束针对链内相邻边，不能误解成整条链两端也必须一对一。

```text
输入：P → A(Q8) → B(Q8) → C(Q8) → D(Q14)
输出：P → Fused[A, B, C] → D(Q14)
```

编译器延长至最大的合法链，生成 `FusedAgentNode`，重接外部边、移除链内部边，并保留各阶段的 prompt、system prompt 和输出上限。这里是确定性的合法性扫描，不是枚举所有物理图并搜索全局最优。

## 执行时究竟省了什么

以下是概念伪代码，用于说明准入边界：

```python
grant = acquire(chain_resource_budget)
try:
    for stage in stages:
        prompt = render(stage.prompt, context)
        result = backend.invoke(prompt, stage.max_new_tokens)
        context = update(context, result)
finally:
    complete(grant)
```

同一后端依次执行原有的三次生成，整链只申请和释放一次资源。租约覆盖中间阶段，因此正常回收策略不能在阶段切换处移走该活跃副本。伪代码的异常收尾不代表已验证所有失败情形；生产实现还必须区分成功、失败和取消。

<div class="table-scroll">

| 对象 | 融合后的变化 |
|---|---|
| acquire / complete | 多次变成一次 |
| 后端副本租约 | 覆盖整条链 |
| 生成调用 | 仍按原有阶段顺序执行 |
| 提示词与结果传递 | 保留各阶段语义 |
| token 计算量 | 不因链融合自动减少 |
| kernel / KV 共享 | 不能仅由调用链融合推导出自动共享 |

</div>

## 时间和显存预算

没有历史时，链运行时间按各阶段估计求和。显存容量需要覆盖后续阶段可能增长的上下文。

当前 worker 使用的输入长度近似为“首段实际输入长度 + 前序阶段最大的输出上限”。如果后续固定提示词更长，或模板累计保留多段输出，这个近似需要扩展。它不能无条件覆盖任意提示词模板。整链预留还可能比逐阶段准入更保守，长租约会影响其他请求的等待。

## 跨工作流共享

两个工作流需要相同部署时，可以共用该部署的副本组。开启跨工作流生命周期机制后，需求按 `model_key` 合并；关闭时按 `(workflow, model_key)` 分别统计。合并后的需求会进入加载收益排序，也影响保留模型、预取与回收判断。

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: SageGraph 是把多个 prompt 拼成一个大 prompt 吗？</div>
<div class="qa-a"><p>不是。当前链融合仍逐阶段渲染提示词、调用模型、传递结果。合并的是资源准入与副本租约边界，不是把多次推理替换为一次推理。</p></div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Agent 分支还没确定，怎么提前知道该加载什么？</div>
<div class="qa-a"><p>利用已确定路径和部署身份的 near-ready 节点。未解析的动态分支不能当成确定需求。提前准备依赖工作流可见性，而不是凭对话内容任意猜测未来工具。</p></div>
</div>

核对依据：`src/workflow/fusion.py` 的 `find_fusable_chains`、`_same_deployment`、`_build_fused_node`，以及 `src/workflow/worker.py` 的融合执行路径。

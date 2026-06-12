## AI Agent 在 AI Infra 中的定位

AI Agent 是把大模型从"对话"升级为"能规划、能调工具、能完成任务"的**应用层范式**。它在 AI Infra 的最上层，决定了底层推理系统要承接什么样的负载（多轮、长上下文、工具调用、并发 Agent）。

面试考 Agent，本质是确认：你是否理解 ReAct 这类推理-行动循环的工作原理，以及记忆、工具调用、规划这些核心组件的工程取舍。

<div class="card card-d">
<h3>一句话定位</h3>
<p>Agent = <strong>LLM（大脑） + 规划（ReAct/Plan-Execute） + 记忆 + 工具调用</strong>。它把"一次问答"变成"观察-思考-行动"的循环，对底层推理系统提出了长上下文和高并发的要求。</p>
</div>

## 与其他模块的关系

| 关联模块 | 关系 | 关键连接点 |
|---|---|---|
| LLM 推理系统 | Agent 负载落到推理引擎 | 多轮上下文、KV cache、并发请求 |
| 论文工作（Maestro） | 多 Agent 调度是论文背景 | 工作负载感知、输出长度预测 |
| 系统设计题 | Agent 平台是设计题方向 | 工具编排、记忆存储、并发治理 |

## 本模块包含哪些内容

| 板块 | 覆盖内容 | 典型面试问题 |
|---|---|---|
| 原理 | Agent 定义、ReAct、Plan-Execute、CoT/ToT、记忆、工具调用、多 Agent | ReAct 怎么工作？记忆系统怎么设计？ |
| 工程与面试 | LangChain/LangGraph、Function Calling、RAG、评估、部署 | Function Calling 原理？RAG 和长上下文怎么选？ |

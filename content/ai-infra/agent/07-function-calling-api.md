## 一句话结论

Function Calling 是 LLM 原生支持的结构化工具调用能力：模型根据用户查询自主决定是否/何时调用哪些工具，输出符合 JSON Schema 的参数，开发者执行后将结果作为 tool message 返回，模型基于结果继续推理。关键参数是 tool_choice 和 parallel_tool_calls，最佳实践是写好工具描述、优雅处理错误、防止无限循环。
<div class="card card-m">
<h3>Function Calling 是什么</h3>
<p>Function Calling（Tool Calling）是 LLM 的一种能力：模型在对话过程中<strong>自主判断是否需要调用外部工具/函数</strong>，并输出结构化的 JSON 参数。开发者负责执行函数，将结果返回给模型，模型再基于工具结果继续推理或生成最终回答。</p>
<div class="flow">
<div class="flow-step"><div class="flow-index">01</div><div class="flow-title">定义工具</div><div class="flow-desc">开发者向 API 注册工具列表（name, description, parameters JSON Schema）</div></div>
<div class="flow-step"><div class="flow-index">02</div><div class="flow-title">用户查询</div><div class="flow-desc">发送用户消息，模型判断是否需要调用工具</div></div>
<div class="flow-step"><div class="flow-index">03</div><div class="flow-title">模型决策</div><div class="flow-desc">模型决定调用哪个工具、传入什么参数，输出 tool_calls</div></div>
<div class="flow-step"><div class="flow-index">04</div><div class="flow-title">执行函数</div><div class="flow-desc">开发者解析参数，执行本地/远程函数，获取结果</div></div>
<div class="flow-step"><div class="flow-index">05</div><div class="flow-title">返回结果</div><div class="flow-desc">将执行结果作为 role="tool" 的消息发回模型</div></div>
<div class="flow-step"><div class="flow-index">06</div><div class="flow-title">继续推理</div><div class="flow-desc">模型读取结果，决定回答用户或继续调用其他工具</div></div>
</div>
</div>

<div class="card card-s">
<h3>消息格式详解（OpenAI 风格）</h3>
<p>Function Calling 涉及四种角色的消息，面试要能写出完整的消息流转。</p>
<p><strong>1. System Message — 工具定义</strong></p>
<pre><code class="language-json">{
  "role": "system",
  "content": "你是一个助手，可以使用工具获取信息。"
}
// tools 参数单独传入：
"tools": [{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "获取指定城市的当前天气",
    "parameters": {
      "type": "object",
      "properties": {
        "city": {
          "type": "string",
          "description": "城市名称，如 Beijing、Shanghai"
        },
        "unit": {
          "type": "string",
          "enum": ["celsius", "fahrenheit"],
          "description": "温度单位"
        }
      },
      "required": ["city"]
    }
  }
}]</code></pre>
<p><strong>2. Assistant Message — 模型决定调用工具</strong></p>
<pre><code class="language-json">{
  "role": "assistant",
  "content": null,
  "tool_calls": [{
    "id": "call_abc123",
    "type": "function",
    "function": {
      "name": "get_weather",
      "arguments": "{\"city\": \"Beijing\", \"unit\": \"celsius\"}"
    }
  }]
}</code></pre>
<p><strong>3. Tool Message — 开发者返回工具结果</strong></p>
<pre><code class="language-json">{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "{\"temperature\": 25, \"condition\": \"sunny\", \"humidity\": 40}"
}</code></pre>
<p><strong>4. 后续 Assistant Message — 模型基于结果回答</strong></p>
<pre><code class="language-json">{
  "role": "assistant",
  "content": "北京今天天气晴朗，气温 25°C，湿度 40%，适合户外活动。"
}</code></pre>
<div class="qa-summary">关键约束：tool message 必须通过 tool_call_id 关联到对应的 tool_call，不能凭空发送；arguments 是 JSON 字符串（需要解析），content 也是字符串（建议 JSON 序列化）。</div>
</div>

<div class="card card-d">
<h3>Parallel Tool Calls（并行工具调用）</h3>
<p>模型可以在一个 assistant 消息中同时调用多个工具——在 <code>tool_calls</code> 数组中放多个条目，每个有独立的 id。开发者应<strong>并行执行</strong>所有工具，然后一次性返回所有 tool message。</p>
<pre><code class="language-json">{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "call_001",
      "type": "function",
      "function": {"name": "get_weather", "arguments": "{\"city\": \"Beijing\"}"}
    },
    {
      "id": "call_002",
      "type": "function",
      "function": {"name": "get_weather", "arguments": "{\"city\": \"Shanghai\"}"}
    }
  ]
}
// 返回时发两条 tool message，对应各自的 id</code></pre>
<div class="qa-summary">并行调用的好处是减少 RTT（多工具不需要一轮轮串行调用），但前提是工具之间没有依赖关系。如果 tool B 需要 tool A 的结果，模型自然会分轮次调用。</div>
</div>

<div class="card card-m">
<h3>Structured Outputs vs Function Calling</h3>
<p>这是两个相关但不同的概念，面试常问区别。</p>
<table>
<tr><th>维度</th><th>Structured Outputs</th><th>Function Calling</th></tr>
<tr><td>目的</td><td>约束模型输出符合 JSON Schema 的结构化文本</td><td>让模型决定是否/何时调用外部工具</td></tr>
<tr><td>是否执行</td><td>不执行任何操作，只是输出格式约束</td><td>开发者需要执行函数并返回结果</td></tr>
<tr><td>输出位置</td><td>assistant.content 是符合 schema 的 JSON</td><td>assistant.tool_calls 包含调用信息</td></tr>
<tr><td>典型场景</td><td>信息抽取、分类、生成结构化数据</td><td>搜索、API 调用、数据库查询、代码执行</td></tr>
<tr><td>工具调用</td><td>无</td><td>有，需要 tool message 响应</td></tr>
</table>
<div class="qa-summary">关系：Structured Output = "输出格式约束（JSON mode 的升级版，保证 schema 合规）"；Function Calling = "决策 + 格式约束（决定调工具 + 输出参数）"。Function Calling 内部其实用了 Structured Output 能力来保证 arguments 合规。</div>
</div>

<div class="card card-s">
<h3>关键参数控制</h3>
<table>
<tr><th>参数</th><th>取值</th><th>作用</th></tr>
<tr><td rowspan="4"><code>tool_choice</code></td><td><code>"auto"</code></td><td>（默认）模型自主决定是否调用工具、调哪个</td></tr>
<tr><td><code>"required"</code></td><td>模型必须至少调用一个工具（禁止纯文本回答）</td></tr>
<tr><td><code>"none"</code></td><td>模型不调用任何工具，只生成文本（禁用工具）</td></tr>
<tr><td><code>{"type": "function", "function": {"name": "xxx"}}</code></td><td>强制模型调用指定工具（如强制输出结构化数据）</td></tr>
<tr><td><code>parallel_tool_calls</code></td><td><code>true</code>/<code>false</code></td><td>是否允许一次 assistant 消息中并行调用多个工具（默认 true）</td></tr>
</table>
<div class="qa-summary"><code>tool_choice</code> 是最常用的控制参数：当模型应该调工具却没调时（如需要查实时数据却凭记忆回答），用 <code>"required"</code> 强制调用；当工具描述模糊模型乱调时，用具体 function 名强制指定。</div>
</div>

<div class="card card-d">
<h3>最佳实践</h3>
<table>
<tr><th>实践</th><th>说明</th></tr>
<tr><td>Tool 描述质量 > Prompt 工程</td><td>工具的 description 是模型选择工具的核心依据。要写清楚：什么时候用、参数含义、enum 值说明、什么时候不要用。描述模糊 = 工具乱调。</td></tr>
<tr><td>少而精 > 多而模糊</td><td>10 个描述清晰的工具 >> 50 个描述模糊的工具。工具太多增加选择难度，模型容易选错。</td></tr>
<tr><td>优雅处理错误</td><td>工具执行失败时，不要抛异常结束循环；把错误信息作为 tool message 返回（如 <code>"error": "City not found, please check city name"</code>），模型会自动修正参数重试。</td></tr>
<tr><td>流式工具调用</td><td>开启 stream 时，arguments 是逐 token 流式输出的，需要累积拼接完整 JSON 后再执行。OpenAI API 通过 deltas 增量返回。</td></tr>
<tr><td>工具链（Tool Chaining）</td><td>模型自然支持链式调用：调 tool A → 读结果 → 调 tool B → ... → 最终回答。不需要特殊处理，只需持续循环直到没有 tool_calls。</td></tr>
<tr><td>JSON Mode vs 原生 Function Calling</td><td>JSON mode 只保证输出合法 JSON，但不保证符合 schema；Structured Outputs / 原生 function calling 能严格保证 schema 合规（字段、类型、enum）。</td></tr>
</table>
</div>

<div class="card card-w">
<h3>常见问题与陷阱</h3>
<table>
<tr><th>问题</th><th>原因</th><th>解决方案</th></tr>
<tr><td>幻觉参数（hallucinated parameters）</td><td>模型编造 schema 中不存在的参数值或枚举</td><td>用 Structured Outputs 模式（strict schema）；description 中明确列出合法值；错误信息作为 tool message 返回让模型重试</td></tr>
<tr><td>该调工具不调</td><td>模型自信地凭记忆回答，不知道信息过时/不可用</td><td><code>tool_choice: "required"</code>；system prompt 中强调「需要实时数据必须调用工具」</td></tr>
<tr><td>选错工具</td><td>工具描述不清晰，多个工具功能重叠</td><td>精简工具数量，每个工具 description 明确区分适用场景</td></tr>
<tr><td>无限工具调用循环</td><td>工具返回结果触发模型再次调用同一工具，无终止条件</td><td>设置最大迭代次数（如 max 10 轮）；检测重复调用并终止；在 tool 结果中明确「无更多信息」</td></tr>
<tr><td>工具参数注入攻击</td><td>恶意用户输入诱导模型把 prompt 注入内容作为工具参数执行（如让 shell 工具执行 rm -rf）</td><td>所有工具参数严格校验（类型、范围、白名单）；高风险操作需要人工确认；永远不要直接把模型输出拼接到 shell/SQL 中</td></tr>
</table>
</div>

<div class="card card-s">
<h3>代码示例：Python SDK 完整流程</h3>
<pre><code class="language-python">from openai import OpenAI
import json

client = OpenAI()
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的当前天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名称"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
            },
            "required": ["city"]
        }
    }
}]

def execute_function(name, args):
    if name == "get_weather":
        return {"temperature": 25, "condition": "sunny"}
    return {"error": f"Unknown function {name}"}

messages = [{"role": "user", "content": "北京今天天气怎么样？"}]
max_iterations = 5

for i in range(max_iterations):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    msg = response.choices[0].message
    messages.append(msg)

    if not msg.tool_calls:
        print("最终回答:", msg.content)
        break

    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)
        result = execute_function(tc.function.name, args)
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result, ensure_ascii=False)
        })</code></pre>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Function Calling 是模型训练出来的还是后处理的？</div>
<div class="qa-a">
<p>现代模型（GPT-4、Claude 3、Gemini 等）的 Function Calling 能力是<strong>通过 SFT（监督微调）训练出来的</strong>，不是简单的后处理解析。</p>
<p>训练过程大致是：</p>
<ol><li>收集大量（用户查询，工具定义，正确 tool_call）的标注数据</li><li>用这些数据做 SFT，教模型在什么场景下输出什么格式的 tool_calls</li><li>部分模型还经过 RLHF 阶段，进一步提升工具选择和参数生成的准确率</li></ol>
<p>模型内部生成的是特殊的 token 序列来标记 tool call 的起止和结构，API 层再解析为结构化 JSON 返回。早期的 function calling（如 gpt-3.5-turbo-0613 刚推出时）确实更像 prompt engineering 的结果，但现在主流模型都把它作为原生训练目标。</p>
<div class="qa-summary">主流模型的 Function Calling 是 SFT 训练出来的原生能力，不是后处理正则匹配；模型学会了在对话流中何时输出工具调用标记、如何组织参数结构。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 怎么让模型一定调用某个工具？</div>
<div class="qa-a">
<p>使用 <code>tool_choice</code> 参数强制控制：</p>
<p><strong>方式 1：强制必须调至少一个工具（不允许纯文本回答）：</strong></p>
<pre><code class="language-python">tool_choice="required"</code></pre>
<p><strong>方式 2：强制调用指定的某个工具（精确控制）：</strong></p>
<pre><code class="language-python">tool_choice={"type": "function", "function": {"name": "extract_entities"}}</code></pre>
<p><strong>补充手段：</strong></p>
<ul><li>System prompt 中明确指示：「要回答这个问题，你必须先调用 search 工具获取最新信息」</li><li>确保工具 description 写清楚什么时候用，不给模型「凭记忆回答」的理由</li><li>如果模型该调不调，检查是否工具描述太泛（模型认为自己知道答案），可以加上「该信息可能过时，必须调用工具确认」</li></ul>
<p><strong>反面：</strong>不要用 <code>tool_choice="none"</code>，那会禁用所有工具调用。</p>
<div class="qa-summary">用 tool_choice 参数控制："required" 强制至少调一个，传入具体 function 名强制调指定工具；配合 system prompt 明确指示。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: 并行 tool call 怎么处理？</div>
<div class="qa-a">
<p>当一个 assistant 消息的 <code>tool_calls</code> 数组包含多个条目时，就是并行工具调用。处理步骤：</p>
<ol><li><strong>不要串行等待：</strong>解析出所有 tool_calls，每个有独立的 <code>id</code>、<code>name</code>、<code>arguments</code></li><li><strong>并行执行：</strong>用线程池/asyncio.gather 同时执行所有工具函数（如果它们之间没有依赖）</li><li><strong>分别返回：</strong>每个工具结果作为单独的 <code>role: "tool"</code> 消息，通过 <code>tool_call_id</code> 关联到对应调用，一次性全部追加到 messages</li><li><strong>继续循环：</strong>发回模型，让模型基于所有结果继续推理</li></ol>
<p><strong>示例：</strong></p>
<pre><code class="language-python">if msg.tool_calls:
    # 并行执行所有工具
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        futures = {
            pool.submit(execute_function, tc.function.name, json.loads(tc.function.arguments)): tc
            for tc in msg.tool_calls
        }
        for future in concurrent.futures.as_completed(futures):
            tc = futures[future]
            result = future.result()
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False)
            })</code></pre>
<p><strong>注意：</strong>tool messages 的顺序不重要，关键是 <code>tool_call_id</code> 正确匹配。</p>
<div class="qa-summary">并行 tool call 即 tool_calls 数组有多个条目；应并行执行所有无依赖的工具，每个结果对应独立 tool message（通过 tool_call_id 关联），一次性发回模型。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: tool message 格式是怎样的？</div>
<div class="qa-a">
<p>Tool message 必须满足以下格式要求：</p>
<pre><code class="language-json">{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "{\"result\": \"工具返回的结果字符串\"}"
}</code></pre>
<p><strong>关键字段：</strong></p>
<ul><li><code>role</code>：必须是字符串 <code>"tool"</code></li><li><code>tool_call_id</code>：必须精确匹配 assistant tool_call 中的 <code>id</code> 字段（如 <code>"call_abc123"</code>），<strong>不能省略、不能写错</strong>——这是关联请求和响应的唯一依据</li><li><code>content</code>：字符串类型，建议 JSON 序列化（因为模型是文本模型，结构化内容要序列化为字符串）；也可以是纯文本错误信息</li></ul>
<p><strong>常见错误：</strong></p>
<ul><li>忘记传 <code>tool_call_id</code> → API 报错</li><li><code>tool_call_id</code> 不匹配 → 模型不知道这个结果对应哪个调用</li><li>content 传 dict 而不是字符串 → 序列化错误</li><li>多个工具调用只返回一个 tool message → 其他 tool_call 没有响应对</li></ul>
<div class="qa-summary">Tool message 三要素：role="tool"、tool_call_id 精确匹配对应调用、content 是字符串（建议 JSON）；每个 tool_call 必须有对应的 tool message 响应。</div>
</div>
</div>

<div class="qa" onclick="this.classList.toggle('open')">
<div class="qa-q">Q: Structured Output 和 Function Calling 区别？</div>
<div class="qa-a">
<table><tr><th>维度</th><th>Structured Outputs</th><th>Function Calling</th></tr><tr><td>本质</td><td>输出格式约束（保证 schema 合规）</td><td>决策能力 + 格式约束（是否调工具 + 参数格式）</td></tr><tr><td>输出在哪里</td><td><code>assistant.content</code>（JSON 文本）</td><td><code>assistant.tool_calls</code>（结构化调用信息）</td></tr><tr><td>需要开发者执行吗</td><td>不需要，直接拿结构化内容用</td><td>需要解析参数执行函数，返回结果</td></tr><tr><td>需要 tool message 吗</td><td>不需要</td><td>必须，否则对话无法继续</td></tr><tr><td>典型场景</td><td>信息抽取、分类打标、提取实体、数据解析</td><td>查天气、搜文档、调 API、查数据库、执行代码</td></tr><tr><td>类比</td><td>「让模型填表」</td><td>「让模型发号施令」</td></tr></table>
<p><strong>联系：</strong>Function Calling 的 arguments 生成内部使用了 Structured Outputs 能力（保证参数 JSON 符合 schema）。可以把 Structured Outputs 看作 Function Calling 的「只输出不执行」特例。</p>
<p>如果用 <code>tool_choice</code> 强制调用某个工具，本质上就是用 Function Calling 机制做 Structured Output——模型会输出一个 tool_call，你不需要真的执行函数，直接解析 arguments 当结构化输出用即可。</p>
<div class="qa-summary">Structured Output 是格式约束（输出合规 JSON 到 content，不执行），Function Calling 是决策+执行（模型决定调工具，输出到 tool_calls，开发者执行后返回 tool message）。</div>
</div>
</div>

## 关联模块

- `01-agent-concepts.md`：Agent 基础概念与 ReAct
- `02-agent-components.md`：Agent 工具系统组件
- `05-agent-paradigms-deep.md`：高级 Agent 范式（ReAct/Reflexion 依赖 tool calling）
- `03-agent-engineering.md`：Agent 工程化与错误处理

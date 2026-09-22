# 智扫通机器人智能客服

基于 **LangChain ReAct 智能体** 的扫地机器人领域智能客服。

用户在前端网页提问，Agent 自主决定调用哪些工具（知识库检索 / 天气 / 用户信息 / 使用记录），结合检索到的资料生成回答；识别到报告需求时自动切换为「报告写手」模式，输出 Markdown 格式的个性化使用报告。

> **项目定位：Agent 编排与运行时干预。**
> 本项目关注的不是检索本身，而是 **Agent 怎么被组织、怎么被介入**——工具如何自主调度、
> 如何在不修改业务代码的前提下挂钩 Agent 循环、如何用同一个 Agent 支撑两种业务模式。
>
> 检索质量与量化评测体系在另一个项目中专项探索：
> [电商智能客服问答系统](https://github.com/ahh818/ecommerce-rag-agent)（30 题评测集 + 实验驱动调参）。

## 它能做什么

| 场景 | 用户输入 | Agent 自主完成 |
|---|---|---|
| 知识问答 | 「清扫后地面还有灰尘、碎屑」 | 检索知识库 → 仅基于资料总结答案 |
| 多工具编排 | 「我这边气温下该怎么保养机器人」 | 依次调用 取位置 → 查天气 → 检索知识库，综合三者回答 |
| 使用报告 | 「生成我的使用报告」 | 取用户 ID → 取月份 → 触发模式切换 → 取使用记录 → 输出 Markdown 报告 |

三个场景的调用顺序**完全由模型现场判断**，没有一行硬编码的流程控制。

## 架构

```
app.py  (Streamlit 前端 + 流式展示)
  └── ReactAgent
       ├── create_agent(model, system_prompt, tools, middleware)
       ├── tools ──→ rag_summarize ──→ RagSummarizeService
       │                                  ├── VectorStoreService (Chroma 检索)
       │                                  └── PromptTemplate | chat_model | StrOutputParser
       ├── tools ──→ fetch_external_data ──→ 用户使用记录
       └── middleware ──→ 日志监控 / 上下文裁剪 / 信号检测 / 动态提示词切换
```

**依赖方向单向：** `app.py → agent → rag → model → utils`，下层永远不知道上层存在。

## 技术栈

| 组件 | 选型 | 作用 |
|---|---|---|
| Agent 框架 | LangChain 1.x（底层 LangGraph） | `create_agent` 组装、ReAct 循环、中间件 |
| 对话模型 | DeepSeek `deepseek-v4-flash` | 思考、决策、生成回答 |
| 向量模型 | 阿里 DashScope `text-embedding-v4` | 文字 → 1024 维向量 |
| 向量库 | Chroma（本地持久化） | 知识库向量存储与相似度检索 |
| Web 前端 | Streamlit | 页面 + 流式输出 |
| 环境管理 | uv | 虚拟环境 + 依赖锁（`uv.lock`） |

## 快速开始

```bash
# 1. 安装依赖
uv sync

# 2. 配置密钥
cp .env.example .env
# 编辑 .env，填入 DeepSeek 和 DashScope 的 API Key

# 3. 知识库入库（首次运行；已入库的文件会按 MD5 指纹自动跳过）
uv run python -m rag.vector_store

# 3.5 初始化演示数据库（可选：CSV 变更后重跑）
uv run python -m agent.tools.external_data

# 4. 启动
uv run streamlit run app.py
```

浏览器打开 `http://localhost:8501` 即可对话。

> **移动或重命名项目目录后必须重建虚拟环境**：`.venv/Scripts/` 下的命令行工具启动器内嵌绝对路径，
> 目录一变就全部失效，报 `uv trampoline failed to canonicalize script path`。
> 执行 `rm -rf .venv && uv sync` 即可修复（若暂时不便重建，`uv run python -m streamlit run app.py` 可绕过）。

## 实现亮点

### 1. 用中间件实现 Agent 运行时干预

四个钩子挂在 ReAct 循环的关键节点上，**不侵入任何业务代码**：

| 中间件 | 挂载点 | 作用 |
|---|---|---|
| `@wrap_tool_call` | 每次工具调用 | 日志监控 + 信号检测 |
| `@before_model` | 每次模型调用前 | 记录消息条数与最新消息类型 |
| `@dynamic_prompt` | 每轮生成提示词前 | **组装**本轮提示词（业务模式 + 思考可见性） |
| `@before_model`（trim_history） | 每次模型调用前 | 消息数超上限时裁剪最早的部分 |

日志、监控这类需求「横穿」所有工具——直接改代码就要在每个工具里各写一遍。中间件一处编写、全局生效，是横切关注点的标准解法。

其中 `@dynamic_prompt` 承担的是「**按运行时状态组装本轮提示词**」，它同时管两个**正交**的维度：

| 维度 | 取值来源 | 效果 |
|---|---|---|
| 业务模式 | `runtime.context["report"]`（由信号工具翻转） | 客服提示词 ↔ 报告写手提示词 |
| 思考可见性 | `config/agent.yml` 的 `show_thinking` | 是否输出推理过程 |

一个中间件管两个互不相关的运行时开关，它作为「提示词组装层」的定位才立得住——加第三个维度只需再拼一段，不用动任何业务代码。

> `show_thinking` 默认开启：本项目定位是展示 **Agent 编排**，如果只输出最终答案，看的人无法判断背后是真在跑 ReAct 循环还是普通 RAG 链——推理过程就是 Agent 自主性的可见证据。若要作为客服产品上线，把它设为 `false` 即可获得干净输出。

### 2. 信号工具 + 运行时上下文 → 零硬编码的业务模式切换

这是本项目最有意思的设计。`fill_context_for_report` 工具本身**什么都不做**，只返回一句确认——它的作用是「信号弹」：

1. **发信号** — 系统提示词规定：判断为报告需求时，必须先调用该工具
2. **接信号** — `@wrap_tool_call` 监听到这个工具名被调用，在 `runtime.context` 里写入 `report = True`
3. **换装** — `@dynamic_prompt` 每轮读取这块上下文，一旦为真，把系统提示词从「客服」换成「报告写手」

整个过程**没有 `if 是报告模式: 切换()` 这样的分支**——模型自主打信号弹，基础设施负责接应。同一套工具链支撑两种业务模式，扩展第三种模式只需加一份提示词。

### 3. 长对话上下文自动裁剪

多轮对话会让消息持续累积，最终超出模型上下文。裁剪放在 `@before_model`
中间件里，在每次模型调用前统一处理。实现上有两个不显然的点：

- **删除要用 `RemoveMessage`，不能直接返回裁剪后的列表。** LangGraph 的
  `messages` 字段用的是 `add_messages` reducer——**追加语义**。直接返回列表
  不是"替换"而是"追加"，消息反而越删越多。`RemoveMessage(id=...)` 是 reducer
  认识的特殊指令，语义是"删掉这条"。
- **裁剪边界不能落在工具消息上。** ReAct 的消息是成对的 `AIMessage(tool_calls)`
  → `ToolMessage(结果)`。若裁剪后剩下的部分以 `ToolMessage` 开头，它的父消息
  已被裁走，形成"孤儿 ToolMessage"，模型 API 会直接返回 400。所以要把开头
  连续的 `ToolMessage` 一并裁掉。

### 4. MD5 指纹增量入库

每个知识文件入库前先算 MD5 指纹并查账本（`md5.txt`），已入库的跳过。重复运行零成本，修改过的文件因指纹变化会被识别为新文件。

## 已知限制

- **外部数据为模拟实现** — `agent/tools/agent_tools.py` 中的天气、用户位置、使用记录是占位数据。工具层是薄壳，替换成真实 API / 数据库不影响 Agent 的编排逻辑。
- **检索策略单一** — 目前是纯向量检索 + 固定 top-k，未做混合检索与 rerank。


## 文档

- [开发文档.md](开发文档.md) — 四条核心链路的完整时序、参数总表、排查手册

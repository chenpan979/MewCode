# 第一阶段：多协议 LLM 终端对话客户端 Plan

> 所有实现路径均从 MewCode 仓库根目录起算。

## 技术栈

- Python 3.12+，`src/` 包布局，Hatchling 构建。
- Textual + Rich：全屏异步 TUI、滚动对话区、流式状态和 Markdown。
- PyYAML：配置解析。
- 官方 `anthropic`、`openai` 异步 SDK：协议和 SSE 处理。
- pytest、pytest-asyncio、Ruff：测试、格式化和 lint。

OpenAI Chat Completions 不是官方新项目的首选接口，但它是本阶段“OpenAI 协议兼容端点”
覆盖面最广的共同接口，因此本阶段使用它。两个 SDK 客户端都设置 `max_retries=0`，满足
spec 的无自动重试边界。

## 架构概览

1. `mewcode_cli.config`：读取和严格校验项目根目录的 YAML，不创建 SDK 客户端。
2. `mewcode_cli.conversation`：只保存成功回合，为待发送回合构造临时消息快照。
3. `mewcode_cli.llm`：定义 `Message`、统一 `Provider` Protocol 和工厂；两个适配器把协议事件
   统一为 `AsyncIterator[str]`，失败直接抛异常。
4. `mewcode_cli.prompt`：system prompt、猫咪 banner 和 Rich renderable。
5. `mewcode_cli.tui`：自定义输入框、provider 选择、对话日志、流式动态区、计时和状态栏。
6. `mewcode_cli.cli`：装配配置并启动应用，配置期错误在进入 raw mode 前处理。

## 核心接口

```python
@dataclass(frozen=True, slots=True)
class ProviderConfig:
    name: str
    protocol: Literal["anthropic", "openai"]
    api_key: str
    model: str
    base_url: str | None = None
    thinking: bool = False

@dataclass(frozen=True, slots=True)
class Message:
    role: Literal["user", "assistant"]
    content: str

class Provider(Protocol):
    name: str
    model: str
    def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]: ...

class Conversation:
    def pending(self, user_text: str) -> tuple[Message, ...]: ...
    def commit(self, user_text: str, assistant_text: str) -> None: ...
    def messages(self) -> tuple[Message, ...]: ...
```

`Conversation.pending()` 不修改已提交历史；流正常完成且正文非空后才调用 `commit()`。

## 协议适配

### Anthropic

- 构造 `AsyncAnthropic(api_key=..., base_url=..., max_retries=0)`。
- 调用 `client.messages.stream(model, max_tokens, system, messages, ...)`。
- `content_block_delta/text_delta` 产生正文；thinking、签名和控制事件忽略。
- `thinking: true` 时发送 `{"type": "enabled", "budget_tokens": 2048}`，并保证
  `max_tokens` 大于 budget。不支持该模式的模型按普通请求错误显示。
- `async with` 保证正常、异常和任务取消时关闭响应流。

### OpenAI

- 构造 `AsyncOpenAI(api_key=..., base_url=..., max_retries=0)`。
- 使用 `chat.completions.create(..., stream=True)`，首条消息注入 `system`。
- 只读取 `choices[0].delta.content`，空 choices/content 安全跳过。
- `thinking` 不发送给 OpenAI 兼容端点。

两适配器不吞异常；TUI 统一格式化错误，并把活动 provider 的 API key 替换为 `***`。

## TUI 设计

- `PromptTextArea(TextArea)` 注册高优先级 Enter/Alt+Enter binding，保留原多行输入体验。
- Windows 使用 `WindowsImeDriver`：Textual 继续绘制全屏界面，`ConsoleInputReader` 仅负责把
  Win32 Unicode、Paste、Mouse 和 Resize 事件翻译回 Textual，且关闭 VT input。
- App compose provider picker 与 chat 容器，通过 display 切换，保留原布局与状态栏。
- `RichLog(wrap=True, markup=False, min_width=1)` 接收 Rich renderable，并支持应用内滚动。
- 提交后禁用输入框，记录 `monotonic()` 起点，启动 Textual worker，由 timer 刷新计时。
- 成功：写入 `Markdown(reply)` + 总耗时，提交 Conversation，恢复输入。
- 失败：写入红色脱敏错误 + 总耗时，不提交 Conversation，恢复输入。
- Ctrl+C 是 App 级高优先级 binding；退出取消 worker、停止 timer 并恢复控制台模式。

## 文件组织

```text
MewCode/
├── .gitignore
├── .mewcode/config.yaml.example
├── README.md
├── pyproject.toml
├── docs/phases/phase-01-chat/
│   ├── spec.md
│   ├── plan.md
│   ├── task.md
│   └── checklist.md
├── src/mewcode_cli/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── conversation.py
│   ├── prompt.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── anthropic_provider.py
│   │   └── openai_provider.py
│   └── tui/
│       ├── __init__.py
│       ├── app.py
│       ├── input.py
│       └── view.py
└── tests/
    ├── test_config.py
    ├── test_conversation.py
    ├── test_providers.py
    └── test_tui.py
```

不拆 `stream.py` / `select.py`：两者强依赖 App 状态，第一阶段拆开会增加循环引用。输入行为
和纯渲染 helper 独立，边界清晰且便于测试。

## 一轮数据流

```text
输入 → Conversation.pending(user) → Provider.stream(snapshot)
    → text delta → 动态纯文本区
    → 正常结束 → Rich Markdown + elapsed → Conversation.commit(user, assistant)
    → 异常     → 脱敏错误 + elapsed        → 历史不变
```

## 关键决策

| 决策 | 选择 | 理由 |
|---|---|---|
| 项目结构 | MewCode 为唯一根项目 | 后续阶段直接扩展同一包 |
| 阶段命名 | `docs/phases/phase-01-chat` | 阶段顺序清晰，目录只承载文档 |
| OpenAI 接口 | Chat Completions | 最大化兼容端点支持 |
| 流接口 | `AsyncIterator[str]` + 异常 | 避免 `done/err` 事件非法组合 |
| 历史提交 | 成功后原子提交 | 失败请求不破坏后续上下文 |
| TUI 并发 | Textual worker + timer | 生命周期和 UI 更新留在同一事件循环 |
| 重试 | SDK `max_retries=0` | 失败立即可见，符合阶段边界 |
| 测试注入 | App 接受 provider factory | 无真实密钥也可覆盖选择、中文输入和流式状态机 |

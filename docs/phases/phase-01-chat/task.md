# 第一阶段：多协议 LLM 终端对话客户端 Tasks

> 工作目录是 MewCode 仓库根目录，共享虚拟环境为 `.venv/`。

## T1 根项目骨架

**文件：** `pyproject.toml`、`.gitignore`、`README.md`、`src/mewcode_cli/__init__.py`、
`src/mewcode_cli/__main__.py`

**步骤：** 配置 Python 3.12+、Hatchling、CLI 入口、运行/dev 依赖；设置版本 `0.1.0`；
忽略根 `.venv`、真实配置和缓存。

**验证：** `.\.venv\Scripts\python -m pip install -e ".[dev]"` 成功。

## T2 配置层和模板

**文件：** `src/mewcode_cli/config.py`、`.mewcode/config.yaml.example`、`tests/test_config.py`

**依赖：** T1

**步骤：** 实现不可变配置类型、`ConfigError`、安全 YAML 加载、字段/类型校验和具体错误路径；
提供双协议示例且不含真实密钥。

**验证：** `.\.venv\Scripts\python -m pytest tests/test_config.py -q`。

## T3 会话事务

**文件：** `src/mewcode_cli/conversation.py`、`tests/test_conversation.py`

**依赖：** T1

**步骤：** 定义 `Message`、`pending`、`commit`、`messages`；拒绝空文本；返回不可变快照；
验证失败轮不提交的调用方式。

**验证：** `.\.venv\Scripts\python -m pytest tests/test_conversation.py -q`。

## T4 Prompt 与统一 Provider 接口

**文件：** `src/mewcode_cli/prompt.py`、`src/mewcode_cli/llm/__init__.py`

**依赖：** T2、T3

**步骤：** 添加 system prompt、猫 banner；定义 Provider Protocol、工厂和错误脱敏 helper；
工厂按 protocol 延迟导入适配器。

**验证：** 模块导入和未知 protocol 单测通过。

## T5 双协议适配器

**文件：** `src/mewcode_cli/llm/anthropic_provider.py`、`src/mewcode_cli/llm/openai_provider.py`、
`tests/test_providers.py`

**依赖：** T4

**步骤：** 实现客户端、`base_url`、`max_retries=0`、system prompt 注入和增量解析；
Anthropic 丢弃 thinking；用 fake SDK 流验证参数与输出。

**验证：** `.\.venv\Scripts\python -m pytest tests/test_providers.py -q`。

## T6 输入组件与渲染 helper

**文件：** `src/mewcode_cli/tui/input.py`、`src/mewcode_cli/tui/view.py`

**依赖：** T1、T4

**步骤：** 自定义 TextArea 的 Enter 提交和 Alt+Enter 换行；实现 WindowsImeDriver，将
Win32 Unicode 事件送回 Textual；实现 user、assistant、error、banner 和状态栏 renderable。

**验证：** Pilot 覆盖中文字符；驱动单测覆盖 ConsoleMode、Unicode、Paste 和 Mouse 翻译。

## T7 TUI 状态机

**文件：** `src/mewcode_cli/tui/app.py`、`src/mewcode_cli/tui/__init__.py`、`tests/test_tui.py`

**依赖：** T2–T6

**步骤：** 实现 picker/chat 视图、provider 选择、提交、worker 流消费、计时、成功提交、
失败恢复、输入禁用、`/exit` 与 Ctrl+C；允许注入 fake provider factory。

**验证：** Textual Pilot 覆盖单 provider、多 provider、中文输入、成功流和失败流。

## T8 CLI 装配

**文件：** `src/mewcode_cli/cli.py`

**依赖：** T2、T7

**步骤：** 加载根目录 `.mewcode/config.yaml`；配置错误输出可读消息并返回非零；合法配置
启动 `MewCodeApp`。

**验证：** 缺配置无 traceback 且退出码非零；合法示例能启动 TUI。

## T9 全量质量检查

**依赖：** T1–T8

```powershell
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m pytest -q
```

## T10 真实端点验收

**依赖：** T9；需要用户本地未提交的真实配置。

**步骤：** 按 checklist 分别验证 Anthropic、OpenAI/兼容端点、多轮、thinking、错误恢复、
计时、Markdown、provider 选择和退出，不把真实 key 写入测试或记录。

## 执行顺序

```text
T1 → T2 ─┬→ T4 → T5 ─┐
    └→ T3 ┘           ├→ T7 → T8 → T9 → T10
             T6 ──────┘
```

# MewCode

MewCode 是一个从零构建的终端 AI Agent。当前正在开发第一阶段: 支持 Anthropic 与
OpenAI 兼容协议的全屏流式多轮对话。

## 项目结构

```text
MewCode/
├── .venv/                         # 所有阶段共用的本地虚拟环境
├── .mewcode/
│   └── config.yaml.example        # 本地运行配置模板
├── docs/phases/phase-01-chat/     # 第一阶段的 spec / plan / task / checklist
├── src/mewcode_cli/               # 持续演进的 MewCode Python 包
├── tests/                         # 自动测试
├── pyproject.toml
└── 前置准备.md
```

后续阶段直接扩展根目录的 `src/mewcode_cli/` 和 `tests/`, 不会再建立嵌套 Python 项目。

## 安装

在仓库根目录执行:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .\.mewcode\config.yaml.example .\.mewcode\config.yaml
```

编辑 `.mewcode/config.yaml`, 填入自己的 provider、模型和密钥。真实配置已被 `.gitignore`
忽略。

## 运行

```powershell
.\.venv\Scripts\python -m mewcode
```

- Enter: 提交
- Alt+Enter: 插入换行
- `/exit`: 空闲时退出
- Ctrl+C: 任意时刻退出

界面保持 Textual 全屏布局、滚动对话区、流式回复和状态栏。Windows 下按照系统设置使用
`Ctrl+Shift`、`Win+Space` 等方式直接切换输入法: 输入中文就是中文, 输入英文就是英文,
不需要 MewCode 专用快捷键。

模型默认使用简体中文回答; 只有在你明确要求其他语言时才会切换。

## 验证

```powershell
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m pytest -q
```

真实端点验收见 `docs/phases/phase-01-chat/checklist.md`。

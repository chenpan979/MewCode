# MewCode

一个运行在终端中的 Python AI 编程助手，支持工具调用、权限与沙箱、MCP、Skills、长期记忆、子 Agent、多 Agent Team、Git Worktree、非交互执行和安全的浏览器 Remote UI。

## 快速开始

```powershell
python -m pip install uv
uv sync --frozen
Copy-Item .mewcode\config.yaml.example .mewcode\config.yaml
uv run mewcode
```

需要 Python 3.11+。配置 Provider 和 API Key、权限模式、Remote 安全、MCP、Hooks、Skills、Team、项目架构及开发测试的完整说明，请阅读 [MEWCODE.md](MEWCODE.md)。

## 验证状态

```text
576 passed, 2 skipped
```

条件式 E2E 测试在没有真实模型凭据时会自动跳过。

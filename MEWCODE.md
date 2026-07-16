# MewCode

MewCode 是一个运行在终端中的 AI 编程助手。它可以读取和修改项目文件、执行命令、调用 MCP 工具，并通过会话记忆、Skills、子 Agent、Team 和 Git Worktree 处理较长或可并行的开发任务。

当前版本：`0.2.0`；要求 Python `3.11+`。

## 主要能力

- Textual 终端交互界面
- `-p` 非交互执行与 NDJSON 流式输出
- 本机浏览器 Remote UI
- Anthropic、OpenAI 和 OpenAI-compatible Provider
- 文件、搜索、Shell、Diff 等内置工具
- 分层权限、危险命令检测、路径限制与 OS 沙箱
- Hooks、MCP、Skills 和自定义 Agent
- Session、长期记忆、上下文压缩与恢复
- 子 Agent、后台任务、多 Agent Team 和 Coordinator 模式
- Git Worktree 创建、切换和回收

## 快速开始

### 1. 安装环境

项目使用 `uv.lock` 锁定依赖。推荐在项目根目录执行：

```powershell
python -m pip install uv
uv sync --frozen
```

`uv sync` 会创建项目本地 `.venv` 并安装运行与开发依赖，不需要修改系统 Python 环境。

也可以激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS：

```bash
source .venv/bin/activate
```

### 2. 创建配置

复制配置示例：

```powershell
Copy-Item .mewcode\config.yaml.example .mewcode\config.yaml
```

Linux/macOS：

```bash
cp .mewcode/config.yaml.example .mewcode/config.yaml
```

最小 Anthropic 配置：

```yaml
providers:
  - name: anthropic-official
    protocol: anthropic
    base_url: https://api.anthropic.com
    api_key: ""
    model: claude-sonnet-4-20250514
    thinking: true

permission_mode: default
```

当 `api_key` 留空时，MewCode 会按协议读取环境变量：

- `anthropic`：`ANTHROPIC_API_KEY`
- `openai`、`openai-compat`：`OPENAI_API_KEY`

PowerShell 示例：

```powershell
$env:ANTHROPIC_API_KEY = "your-api-key"
```

不要把真实密钥提交到仓库。项目目录下的真实配置和运行数据已被 `.gitignore` 忽略，仅提交无密钥的配置示例；仍建议优先使用环境变量。

### 3. 启动

```powershell
uv run mewcode
```

也可以直接使用虚拟环境入口：

```powershell
.\.venv\Scripts\mewcode.exe
```

## 配置加载顺序

未显式传入配置路径时，MewCode 会依次加载并合并：

1. `~/.mewcode/config.yaml`
2. `<项目>/.mewcode/config.yaml`
3. `<项目>/.mewcode/config.local.yaml`

后面的项目级配置覆盖或扩展前面的用户级配置。Provider 可在项目级替换；MCP Server 按名称合并；Hooks 会追加。

## Provider 配置

支持三种协议：

```yaml
providers:
  - name: anthropic
    protocol: anthropic
    base_url: https://api.anthropic.com
    api_key: ""
    model: claude-sonnet-4-20250514
    thinking: true
    context_window: 200000       # 可选；0 表示自动解析
    max_output_tokens: 8192      # 可选；0 表示使用默认值

  - name: openai
    protocol: openai
    base_url: https://api.openai.com/v1
    api_key: ""
    model: gpt-4o

  - name: compatible
    protocol: openai-compat
    base_url: https://your-provider.example/v1
    api_key: "your-provider-key"
    model: your-model
```

配置多个 Provider 时，终端界面会提供选择。

## 权限模式

可以在配置中设置 `permission_mode`，也可以通过 `--mode` 临时覆盖。

| 模式 | 读取 | 写入 | 命令 | 适用场景 |
| --- | --- | --- | --- | --- |
| `default` | 自动允许 | 询问 | 询问 | 日常交互，推荐默认使用 |
| `acceptEdits` | 自动允许 | 自动允许 | 询问 | 已确认可以修改项目文件 |
| `plan` | 自动允许 | 仅计划文件 | 询问/拒绝 | 只分析和制定实施方案 |
| `bypassPermissions` | 自动允许 | 自动允许 | 自动允许 | 受控自动化环境 |

危险命令黑名单、显式 deny 规则和已启用的沙箱仍可能优先拒绝操作。`bypassPermissions` 风险较高，不要在不可信项目或开放远程服务中使用。

权限规则可放在：

- `~/.mewcode/permissions.yaml`
- `<项目>/.mewcode/permissions.yaml`
- `<项目>/.mewcode/permissions.local.yaml`

交互界面中可用 `/permission` 查看和管理当前模式及规则。

## 非交互模式

执行一次任务并把最终结果写到标准输出：

```powershell
uv run mewcode -p "分析这个项目的测试失败原因"
```

非交互模式默认拒绝需要人工确认的写入或命令操作。只有明确授权时才使用 `--yes`：

```powershell
uv run mewcode -p "修复测试" --yes
```

输出 NDJSON 事件流：

```powershell
uv run mewcode -p "运行测试并总结" --output-format stream-json
```

`--yes` 只处理原本需要确认的请求，不会绕过危险命令检测和显式 deny 规则。

## Remote 浏览器模式

### 仅本机访问

Remote 默认只监听 `127.0.0.1:18888`：

```powershell
uv run mewcode --remote
```

浏览器打开：

```text
http://localhost:18888/
```

可以通过 `--remote-port` 修改端口。

### 局域网或外部监听

监听非本机地址时必须配置 token，否则 MewCode 会拒绝启动。推荐用环境变量，避免 token 出现在进程参数中：

```powershell
$env:MEWCODE_REMOTE_TOKEN = "replace-with-a-long-random-token"
uv run mewcode --remote --remote-host 0.0.0.0
```

程序会打印带 token 的访问地址。内置页面会把查询参数中的 token 传给 WebSocket 握手；服务端还会检查浏览器 Origin。

外部访问时还应：

- 使用系统防火墙限制来源地址
- 通过 HTTPS/WSS 反向代理提供 TLS
- 不要复用短 token 或把访问 URL 发到公开渠道
- 不要在不可信网络中启用 `bypassPermissions`

## MCP

stdio MCP Server：

```yaml
mcp_servers:
  - name: context7
    command: npx
    args: ["-y", "@upstash/context7-mcp"]
```

HTTP MCP Server：

```yaml
mcp_servers:
  - name: internal-tools
    url: https://example.com/mcp
    transport: http
    headers:
      Authorization: "Bearer ${MY_TOKEN}"
```

MCP 子进程只继承必要的 `PATH` 和配置中显式声明的 `env`。在终端中使用 `/mcp` 查看连接状态。

## Hooks

Hooks 可在生命周期事件发生时执行命令、注入 Prompt 或调用 HTTP。示例：阻止 Bash 中的递归删除命令：

```yaml
hooks:
  - id: block-recursive-delete
    event: pre_tool_use
    if: 'tool == "Bash" && args.command =~ /rm\s+-rf/'
    reject: true
    action:
      type: command
      command: echo blocked by project policy
```

常用事件包括：

- `session_start`、`session_end`
- `turn_start`、`turn_end`
- `pre_send`、`post_receive`
- `pre_tool_use`、`post_tool_use`
- `compact`、`permission_request`、`file_change`

`reject: true` 只能用于同步 `pre_tool_use` Hook。拒绝规则会在流式、顺序和非交互工具执行路径中统一生效。

## 沙箱

配置示例：

```yaml
sandbox:
  enabled: true
  auto_allow: false
  network_enabled: false
```

- `enabled`：启用操作系统级隔离
- `auto_allow`：沙箱兜底时自动放行命令
- `network_enabled`：允许沙箱内网络访问

沙箱实现与平台相关。即使启用了 OS 沙箱，也建议保留最小权限规则并审查危险操作。

## Skills、Agent 与 Team

项目级 Skills 放在 `.mewcode/skills/<skill-name>/SKILL.md`。MewCode 会加载 Skill 元数据，并在需要时再加载完整说明。

相关配置：

```yaml
enable_fork: true
enable_verification_agent: true
teammate_mode: in-process
enable_coordinator_mode: false
```

Coordinator 模式启用后，Team Lead 主要负责研究、拆分、调度和汇总，写入类工具会受到限制。

Worktree 配置示例：

```yaml
worktree:
  symlink_directories: [node_modules, .venv, vendor]
  stale_cleanup_interval: 3600
  stale_cutoff_hours: 24
```

## 常用终端命令

| 命令 | 作用 |
| --- | --- |
| `/help [命令]` | 查看帮助 |
| `/status` | 查看模型、权限和 token 状态 |
| `/clear` | 清除当前对话 |
| `/plan [任务]` | 进入 Plan 模式 |
| `/compact [重点]` | 压缩当前上下文 |
| `/permission ...` | 查看或修改权限模式与规则 |
| `/sandbox ...` | 查看或切换沙箱状态 |
| `/session ...` | 新建、恢复、列出或删除会话 |
| `/memory ...` | 查看、编辑或清理长期记忆 |
| `/skill ...` | 列出、查看或重新加载 Skills |
| `/mcp` | 查看 MCP Server 状态 |
| `/tasks` | 查看和管理后台任务 |
| `/trace` | 查看 Agent 父子追踪树 |
| `/worktree ...` | 管理 Git Worktree |
| `/review [关注点]` | 审查当前代码变更 |
| `/rewind ...` | 回退到文件历史检查点 |

在界面内输入 `/help` 可查看当前运行环境中实际注册的全部命令。

## 项目结构

```text
mewcode/
├── __main__.py          # CLI、非交互和 Remote 入口
├── app.py               # Textual 终端 UI
├── agent.py             # Agent 主循环与工具调度
├── client.py            # Anthropic/OpenAI 客户端
├── config.py            # 分层配置加载
├── permissions/         # 权限矩阵、规则和路径限制
├── sandbox/             # Seatbelt/Bubblewrap OS 沙箱
├── tools/               # 内置工具
├── hooks/               # Hook 模型、加载与执行
├── mcp/                 # MCP 客户端和工具包装
├── skills/              # Skill 加载、安装和执行
├── memory/              # Session、长期记忆和整理
├── context/             # 上下文预算、持久化和恢复
├── agents/              # 子 Agent、任务和追踪
├── teams/               # Team、Mailbox 和协调器
├── worktree/            # Git Worktree 生命周期
└── commands/            # 斜杠命令系统

tests/                   # 单元、集成和条件式 E2E 测试
```

## 开发与测试

同步锁定依赖：

```powershell
uv sync --frozen
```

运行完整测试：

```powershell
uv run pytest -q
```

语法检查：

```powershell
uv run python -m compileall -q mewcode tests
```

检查依赖一致性：

```powershell
uv lock --check
uv run python -m pip check
```

部分 E2E 测试需要真实模型配置，未提供时会自动跳过：

```powershell
$env:MEWCODE_TEST_API_KEY = "..."
$env:MEWCODE_TEST_BASE_URL = "https://provider.example/v1"
$env:MEWCODE_TEST_MODEL = "model-name"
uv run pytest tests\test_consolidation.py -v -s
```

## 日志与运行数据

项目运行数据默认写在 `.mewcode/`：

- `debug.log`：运行日志
- `history`：输入历史
- `sessions/`：会话记录
- `memory/`：长期记忆
- `plans/`：Plan 模式计划文件
- `permissions.local.yaml`：项目本地权限规则

遇到启动、Provider、MCP 或 Hook 问题时，优先查看 `.mewcode/debug.log`。

## 代码规范

- Python 变量与函数使用 `snake_case`
- 类名使用现有的 `PascalCase` 命名
- commit message 使用英文
- 修复工具执行链路时，必须同时覆盖流式、顺序和非交互路径
- 新增平台相关逻辑时，至少覆盖 Windows 与 POSIX 行为

# 第一阶段自动验收记录

验收日期：2026-07-15

## 已通过

- Python：`3.12.0`。
- 项目以 editable 模式安装到根目录共享 `.venv/` 成功。
- 依赖一致性：`.venv\Scripts\python -m pip check` → `No broken requirements found.`
- 格式：`.venv\Scripts\python -m ruff format --check .` → `18 files already formatted`。
- Lint：`.venv\Scripts\python -m ruff check .` → `All checks passed!`。
- 自动测试：`.venv\Scripts\python -m pytest -q` → `22 passed in 5.29s`。
- 缺少 `.mewcode/config.yaml` 时，CLI 输出单行可读配置错误，不输出 traceback。
- 复制残留扫描未发现旧 `phase1_chat` 工程路径、旧 `src/mewcode/` 包路径、外层 Markdown
  围栏或粘连标题。文档中对 `tmux` / `lipgloss` 的出现仅用于明确排除复制残留和依赖。

## 自动测试覆盖

- YAML 合法/非法配置与精确错误定位。
- 成功回合原子提交、失败回合不污染历史。
- Anthropic text delta 提取、thinking delta 丢弃、system/history/thinking 参数。
- OpenAI system/history 注入、空 chunk 跳过与正文增量。
- 两家 SDK 的 `base_url` 和 `max_retries=0`。
- API key 错误文本脱敏。
- Textual 单 provider、多 provider、中文输入、成功流、失败恢复、Enter 和 Alt+Enter。

## 待真实凭据验证

- Anthropic 实际端点的多轮、thinking 和 Markdown 流式体验。
- OpenAI 官方或兼容端点的流式体验与自定义 `base_url`。
- 真实慢响应计时、Windows 输入法直接中英文切换、Alt+Enter、窗口缩放和 Ctrl+C 恢复。

这些项目需要用户在未提交的 `.mewcode/config.yaml` 中提供真实配置后手工执行；当前不将其
标记为已通过。

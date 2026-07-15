# 第一阶段：多协议 LLM 终端对话客户端 Checklist

> 自动项由测试或命令验证；真实端点项需要本地私密配置，不能记录 key 或完整错误响应。

## 文档与目录

- [ ] MewCode 是唯一项目根；阶段目录只位于 `docs/phases/phase-01-chat/`。
- [ ] 四份文档没有外层代码围栏、标题粘连、`lipgloss`、`tmux` 或复制目录残留。
- [ ] `.venv/` 与 `.mewcode/config.yaml` 被根 `.gitignore` 忽略。

## 自动验证

- [ ] 合法配置可加载，缺文件、坏 YAML、空列表、字段/类型错误产生具体 `ConfigError`。
- [ ] `pending()` 不改变历史，`commit()` 原子追加 user/assistant，快照不可变。
- [ ] Anthropic 注入 system、历史、`base_url` 和可选 thinking，只输出 text delta。
- [ ] OpenAI 在 messages 首项注入 system，只输出非空 content delta。
- [ ] 两家 SDK 客户端均关闭默认自动重试。
- [ ] API key 在 provider 错误字符串中替换为 `***`。
- [ ] 单 provider 直进 chat；多 provider 显示 OptionList 并采用所选项。
- [ ] fake provider 成功流最终提交历史；错误流恢复输入且历史不变。
- [ ] `ruff format --check .`、`ruff check .`、`pytest -q` 全部通过。

## 手工界面验证

- [ ] 启动含猫咪、版本、cwd、就绪提示、带 `❯` 的输入区和 provider/model 状态栏。
- [ ] Enter 提交；Alt+Enter 换行；Ctrl+Shift 可切换输入法；中英文混合输入保持原文。
- [ ] 首 token 前显示 `Imagining… (Ns)`；秒数递增；完成块保留总耗时。
- [ ] 流式正文即时出现，完成后代码块、列表和强调按 Markdown 渲染。
- [ ] 长回复期间对话区可滚动，改变窗口宽度后正常软换行。
- [ ] `/exit` 和 Ctrl+C 退出后，终端输入与回显正常。

## 真实端点验证

- [ ] Anthropic：两轮对话中第二轮能引用第一轮成功历史。
- [ ] Anthropic thinking：支持参数的模型开启后正常回复，界面无 thinking 文本。
- [ ] OpenAI：至少一轮流式 Markdown 回复正常。
- [ ] OpenAI 兼容端点：设置 `base_url` 后正常收发。
- [ ] 多 provider：选择第二项后，状态栏和请求都使用第二项。
- [ ] 错误恢复：错误 key/模型显示红色脱敏信息，下一次请求不携带失败轮次。
- [ ] 重启应用后历史为空。

## 阶段完成条件

- [ ] 所有自动项通过。
- [ ] 至少一个真实端点完成端到端对话；另一协议若无凭据，明确标记“待凭据验证”。
- [ ] 无真实密钥、缓存、虚拟环境或本地配置进入 Git 跟踪列表。

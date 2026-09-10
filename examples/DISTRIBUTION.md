# 公开分发文档验证（2026-09-10）

基线：从 GitHub main 提交 8fcb39a 独立克隆；修改前 46 项离线测试通过。
本轮只修改文档，不合并其他工作区未提交代码，不导入开发者 .local。

主要问题：README 将开发机卡片与公开包混写；缺少无上下文加载和无工具降级说明；
“尚无 OCR”与质量工具冲突；维护历史中的未发布状态容易被当成当前状态。

修改后验证：
- 46 项离线测试通过；宿主提供的 quick_validate 判定 Skill is valid。
- 所有 Markdown 相对文件链接存在；git diff --check 通过。
- 临时空 --home 中实际运行 build、search theory（返回 3 条）、doctor、project new/show，全部成功。
- 人工文档走查：新模型可从 START_HERE 找到 SKILL、来源规则和画像；只有聊天附件时有明确替代流程；
  项目恢复不声称自动记忆；已回答内容不重复询问；关联、冷门、DSR 与材料指令的原有规则未被改写。

这是软件与文档走查，没有新增独立模型冷启动测试或教师评分。
未测试原生 Windows 保存、WSL 接入 Zotero、各宿主原生安装、网络依赖安装或 OCR 语言数据配置。
修改保存在 codex/documentation-onboarding；本记录不意味着已经推送或合并 GitHub。

## 按 skill 仓库习惯重写（同日后续）

实际读取以下仓库 README、目录列表和 Agent Skills 格式规范后，再次调整入口。
GitHub API 查询时的 stars 仅为选样依据，不是质量或兼容性的证明：

| 参考 | Stars 快照 | 采用的组织方式 |
|---|---:|---|
| [anthropics/skills](https://github.com/anthropics/skills) | 175480 | SKILL 元数据与正文、完整目录加载、资源按需读 |
| [obra/superpowers](https://github.com/obra/superpowers) | 284200 | 先讲实际工作方式，再讲安装、用法和目录 |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | 31020 | 明确使用场景，简短安装，自然语言触发例子 |
| [Agent Skills specification](https://agentskills.io/specification) | — | 目录名匹配 name，入口与资源分层，允许额外目录 |

不复制其他项目的插件商店、安装命令或自动触发承诺：本仓库没有相同的插件清单和发布设施。
保留 tools 而不改名 scripts：后者是推荐惯例，额外目录为规范允许，迁移会影响现有命令。
README 移除 ZIP 和 Python 操作主线；克隆目标命名 misq-reviewer；SKILL 为唯一正式入口，
START_HERE 降为兼容转向。已修正上一轮“目录名称可以不同”的安装指引。
文档格式统一标题层级、代码语言、表格表头和相对路径。没有为增加目录数量创建多 skill 嵌套。

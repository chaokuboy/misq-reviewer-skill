# MISQ 研究助手入口

论文、研究想法和投稿任务：先读 `SKILL.md`，按其路由与证据规则执行。
明确要求追问/诊断时直接进入；意图不明才选择功能。普通编程任务不进入论文模式。

优化、修复、扩展本技能：先完整读 `ARCHITECTURE.md`。维护前记录基线，维护后运行
`python3 -m unittest discover -s tests -v` 与 skill frontmatter 校验，并按 `examples/README.md`
执行行为走查。区分脚本测试、人工走查与独立模型盲测，不虚报。

全文、索引、项目记录、凭据只在本地；不修改 Zotero 原文件，不自动发布 GitHub。

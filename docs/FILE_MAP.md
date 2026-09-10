# 文件导航

不需要一次读完整个仓库。按用途选择入口；路径均相对于仓库根。

| 文件或目录 | 作用 | 谁在何时读 |
|---|---|---|
| README.md | 能力、快速开始、公开包边界 | 首次访问的人 |
| START_HERE.md | 旧链接兼容，转向 SKILL.md | 曾引用此路径的对话 |
| SKILL.md | 无上下文正式入口、路由、判断纪律与六段诊断 | 首次加载及执行研究任务的模型 |
| AGENTS.md | 仓库助手入口 | 支持该约定的宿主 |
| docs/GETTING_STARTED.md | 静态加载、工具安装、迁移 | 首次安装或换机器 |
| docs/FAQ.md | 常见误解和排错 | 使用遇到问题时 |
| references/evidence.md | 来源、时效、知识卡与核验 | 所有实质判断前 |
| profiles/misq.md | 维度 0–8、D8 稳定审计项 | MISQ 研究判断 |
| references/dialogue.md | 追问推进与恢复 | 多轮研究讨论 |
| references/research-pipeline.md | 资源到研究路线的主线 | 比较可执行研究方向 |
| references/research-workflows.md | 文献、方法、模拟审稿与修改等流程 | 对应专项任务 |
| references/local-tools.md | 本地检索、同步、项目命令 | 有终端且需要工具时 |
| references/quality-lab.md | 来源质量、PDF、更新检查和评测 | 来源复核或评测时 |
| profiles/misq_submission_guide.md | 历史投稿阅读摘要 | 投稿任务按需读，当前规则需另核验 |
| profiles/knowledge/ | 九份历史蒸馏 | 相关主题的来源线索，不是全部已核验原文 |
| profiles/editorial_list.md、editorial_to_add.md | 历史文献索引和补抓建议 | 维护资料时，不代表当前完整覆盖 |
| evaluations/ | 评测场景、协议、检索开发集 | 准备评测；不是教师标准答案 |
| examples/ | 合成用例与各轮历史验证报告 | 学习用法、核对验证范围 |
| tests/ | 可复现离线软件测试 | 维护与安装检查 |
| ARCHITECTURE.md | 实现、数据流、联动约束与历史记录 | 开发前完整阅读 |
| CONTRIBUTING.md | 文档、代码、来源贡献约定 | 提交修改前 |
| LICENSE | MIT 许可 | 分发或复用时 |
| .local/ | 用户全文索引、卡片、项目和评测原件 | 本机生成，公开包不含 |

## 脚本选择

| 工具 | 用途 |
|---|---|
| research_assistant.py | 主 CLI：构建、搜索、Zotero 同步、项目 |
| research_workflows.py | 主 CLI 调用的证据包、审计、分支等实现 |
| research_planning.py | 研究路线显式资源依赖检查 |
| quality_lab.py | 来源审核、目录对账、PDF 和公开 DOI 通知 |
| blind_eval.py | 真实输出匿名化与真实评分汇总，不调用模型 |
| behavior_run.py | 开发行为运行冻结与收集；依赖本地导入案例 |
| import_deepseek_eval.py | 外部 DeepSeek 合成包输入隔离；外部包不随仓库提供 |
| distill_prompt.md | 原文到候选知识卡的整理协议 |
| requirements-pdf.txt、requirements-quality.txt | 可选 PDF 依赖 |

`fetch_misq.py`、`analyze_corpus.py`、`extract_pdf_text.py`、`download_fulltext.py` 和
`download_fulltext_guide.md` 是历史数据处理路线；不是新用户必跑步骤，也不是通用全文下载服务。
不要根据历史路径或机构配置直接运行下载脚本。

# MISQ 研究助手

用 MIS Quarterly 文献档案引导研究想法，或诊断投稿契合度与研究成熟度。
核心是有来源、适用条件和稿件证据的追问；不预测录用概率。

## 使用

在仓库中让支持 AGENTS.md 的工具读取入口；支持 skills 的工具需把整个目录作为
`misq-reviewer` 技能加载，不能只复制 SKILL.md。具体发现路径以宿主说明为准。

- “帮我梳理这个研究想法” → 一次一个关键问题，根据回答推进。
- “诊断这份方案能否投 MISQ” → 六段诊断：契合度/成熟度、创新、缺口/待确认、下一步、证据审计、开放问题。
- 需求不明确时介绍两种功能；“怎么补”直接给建议，不强制重新选模式。

不要求每次读完全部论文。静态画像可直接用；本地检索与项目记忆按需启用：

```bash
python3 tools/research_assistant.py build
python3 tools/research_assistant.py search '机制 竞争解释 mediation'
python3 tools/research_assistant.py project new my-study
python3 tools/research_assistant.py project show my-study
```

每个项目固定知识版本，保存用修订号检查，换聊天后恢复已问问题与下一步。
完整命令见 [本地工具](references/local-tools.md)。

## 连接本地 Zotero

打开 Zotero 并启用本地 API 后运行：

```bash
python3 tools/research_assistant.py collections
python3 tools/research_assistant.py sync-zotero <实际合集键>
python3 tools/research_assistant.py build
```

只读选定合集的题录与已索引 PDF 文本，不需要 Web API key，不修改附件。
连接不可用时不会更新；未索引/不可读附件进入失败清单。可用 `--extract-pdfs` 从本地 PDF 后备提取并保留物理页码（需安装 pypdf，见本地工具）；尚无 OCR。
数据只写 `.local/`，不提交 GitHub。宿主若使用云端模型，读入的证据片段仍进入模型上下文。

## 知识与限制

- 画像维度 0–8、投稿指南、九份旧蒸馏提供检索入口；本轮未逐页核验原文，不能当已证实政策。
- 稳定审计 ID D8-01 至 D8-15，四态：已有支持、待确认、存在缺口、不适用。
- 2020–2026 的 519 条历史题录统计是标题＋摘要关键词命中、多标签，并非方法偏好或录用率。
- 标准、案例和综合推断分开；日期比评估时点晚才用“当代镜头”；资料未提供不等于研究未做。
- 本地检索是 SQLite FTS5 词项搜索，不是向量 RAG。知识卡由模型辅助整理、人工核验。
- 本地已有 6 张标准候选卡和 4 张案例卡，带片段/hash/适用性/局限及模型复核；仍待人工核验。没有自动训练或自动更新计划。

## 扩展工作台

现在还支持：文献对照、创新路径比较、主张证据检查、按范式审查方法、审稿模拟、
修改回复、两版比较、导师会前摘要和研究方向分支。模型按需执行，不要求每次跑完整套。

```bash
python3 tools/research_assistant.py search '患者自主性' --expand --year-from 2022 --year-to 2026 --kind pdf_fulltext --per-source 1
python3 tools/research_assistant.py packet '患者自主性' --year-from 2022 --year-to 2026
python3 tools/research_assistant.py doctor
python3 tools/research_assistant.py cards-audit
python3 tools/research_assistant.py project-list
```

支持文档上下文读取、知识版本差异、项目分支/导出和 PDF 提取缓存，详见 [操作文档](references/local-tools.md)。
[详细审查](examples/REVIEW_V2.md) 区分已实现能力与剩余不足；小词表扩展不是完整语义检索，
原文提取不等于完成知识核验，审稿模拟不代表真实编辑意见。

## 证据质量与评测

新增 [质量工作台](references/quality-lab.md)：知识卡语义复核记录、8 场景教师盲评工具、
多查询融合、检索回归、PDF 表格/页图/OCR、19 期目录对账、Crossref 更新通知检查。
教师评分尚未开展；没有将模型自评或源码测试当成效果证据。
本轮真实结果与剩余边界见 [第三轮验证记录](examples/QUALITY_V3.md)。

当前版本已运行6案双条件和两组五轮对话，另做3案修订后复测；独立模型评审发现并复核了
审计ID出处错配。详见 [行为评测记录](examples/BEHAVIOR_R1.md)。这是合成开发案例的
行为观察，不是教师校准或优于普通助手的证明。加入研究路线检查后，当前自动测试46项通过。

## 维护与验证

研究想法与资源可按 [研究推进主线](references/research-pipeline.md) 完成最近邻对照、
设计路线比较和判断修订。新增 `plan-check` 检查声明的资源依赖；不将口头承诺视为已获得数据。
候选A的本地试跑和验证边界见 [试跑记录](examples/PILOT_PIPELINE.md)。

先读 [ARCHITECTURE.md](ARCHITECTURE.md)。来源纪律见 [evidence.md](references/evidence.md)，
对话流程见 [dialogue.md](references/dialogue.md)。旧版方案与文件保存在 Git 历史。

```bash
python3 -m unittest discover -s tests -v
```

[examples](examples/README.md) 包含多轮行为协议。脚本测试、人工走查与独立模型盲测分开报告，
不以“已发表所以应该通过”校准答案。

本项目与 MISQ 无隶属关系，输出不代表编辑决定。代码与原创凝练按 [MIT](LICENSE) 分发；
第三方原文权利不因本项目许可证改变，公开包不含期刊全文。

### 证据闭环补丁（2026-09-10）
证据包固定单一知识版本，接入版本绑定的语义审核与 evidence_use 状态；出版通知报告保留
按内容去重的历史，防止后续无命中覆盖旧警报。详见 [质量工作台](references/quality-lab.md)
及 [本轮验证](examples/QUALITY_V4.md)。33 项软件测试通过，不代表追问效果已获教师验证。

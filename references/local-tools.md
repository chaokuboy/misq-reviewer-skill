# 本地工具操作

Python 3.9+，索引与检索只需标准库（SQLite FTS5）。项目并发锁使用 fcntl，当前支持 macOS/Linux。
在仓库根运行；或给脚本绝对路径。默认数据落在仓库 `.local/`，已忽略提交。

```bash
python3 tools/research_assistant.py build
python3 tools/research_assistant.py search '机制 竞争解释 mediation' --limit 3
python3 tools/research_assistant.py project new patient-autonomy
python3 tools/research_assistant.py project show patient-autonomy
```

保存：读出状态，修改后写 `.local/draft.json`，再运行：

```bash
python3 tools/research_assistant.py project save patient-autonomy --file .local/draft.json --expected-revision 1
```

revision 冲突先重新读取并合并，不能强行覆盖。每次保存保留上一版；new 不覆盖同名项目。
检索固定版本：`search 'query' --version <项目中的 knowledge_version>`。
新 build 不会修改项目；要升级版本，显式修改项目并在 decisions 中记录原因和影响。

## Zotero（只读接入）

打开 Zotero 并启用本地 API 后：

```bash
python3 tools/research_assistant.py collections
python3 tools/research_assistant.py sync-zotero <实际合集键>
python3 tools/research_assistant.py coverage
python3 tools/research_assistant.py build
```

`coverage` 汇总现有快照的年份、可读条目、缺文本条目及失败类型；不等于期刊收全证明。

只连接 127.0.0.1，不用 Web API key，不改 Zotero 条目/附件/设置。
sync 读取选定合集的直接成员（子分类需分别同步）及 PDF 的 Zotero 已索引文本。
读取全部成员确保发现旧条目变更；本版尚未用版本游标减少请求。
扫描件、未索引 PDF、断链文件可能无文本：查看 failures，再在 Zotero 检查附件和索引。
可选本地 PDF 后备提取（首次安装依赖，之后只运行同步）：

```bash
python3 -m venv .local/venv
.local/venv/bin/python -m pip install -r tools/requirements-pdf.txt
.local/venv/bin/python tools/research_assistant.py sync-zotero <实际合集键> --extract-pdfs
python3 tools/research_assistant.py build
```

缓存不可用时只读附件的本地路径，用 pypdf 按页提取，不修改源 PDF。
定位为 PDF 物理页序号（从 1 起），不是期刊印刷页码。空白/扫描页列入 failures；不自动 OCR。
默认缓存路径仍使用文本 offset。提取成功不等于语义核验，全文片段一律 verified=false。
合集条目列表/附件列表失败时不发布该次快照；某 PDF 全文不可读则记录失败且不沿用其旧文本。
再次同步完整合集会移除该合集已删除条目；同条目仍属于其他已同步合集则保留。
API 不可用时保留旧快照，不声称“已更新”。

## 知识卡与版本

按 evidence.md 格式创建 `.local/cards/*.json`；build 校验最小结构并与静态档案/快照一起索引。
`verified: true` 是人工核验声明，脚本只能检查字段齐备，不能验证原文是否支持。
本版不自动蒸馏、不自动提升核验状态，也不自动修改公开画像。
每次内容变化创建不可变 SQLite 快照，current.json 原子切换；旧项目继续使用旧版。
回退可把 `.local/current.json` 的 version 指向已有快照；不要删除仍被项目引用的版本。
检索为词项搜索（中文双字切分＋英文 token），不是语义向量搜索；排名只是候选相关度。

全文和私人项目不上 Git；如另设 `--home`，自行放到非公开数据目录。
不配置云端 embedding 服务。宿主模型读取检索结果时，片段仍可能进入云端模型上下文。

## 扩展检索与证据阅读

```bash
python3 tools/research_assistant.py search '患者自主性' --expand --year-from 2022 --year-to 2026 --kind pdf_fulltext --per-source 1
python3 tools/research_assistant.py search 'causal mechanism' --match all --limit 10
python3 tools/research_assistant.py search '研究动机' --verified-only
python3 tools/research_assistant.py read '实际命中的文档ID' --version <知识版本> --context 1
python3 tools/research_assistant.py packet '患者自主性' --project patient-autonomy --year-from 2022 --year-to 2026
```

`--kind` 可重复，类型见 evidence.md，另有 metadata/pdf_fulltext/indexed_fulltext/legacy_distillation。
`--expand` 是公开小词表辅助，不是自动翻译；结果列出扩展词和匹配词。可手写英文查询补召回。
`--match all` 要求全部切分词出现，不与扩展并用。`--per-source 1` 按规范化 DOI/条目键限额。
未知日期不进入指定年份范围；不筛年份时保留。`--verified-only` 只筛核验声明，不能替代卡片审计。
`read` 的上下文仅对有 PDF 物理页码的片段提供；不把拼接重叠片段当独立证据。
`packet` 读取项目固定版本，分别给标准卡与原文候选；检索没有核验结论，也不自动生成新颖性判断。

## 健康、来源和版本

```bash
python3 tools/research_assistant.py doctor
python3 tools/research_assistant.py cards-audit
python3 tools/research_assistant.py versions
python3 tools/research_assistant.py versions --before <旧版本> --after <新版本>
```

doctor 检查 SQLite、项目固定版本是否存在、重复 DOI、覆盖与卡片引用，不修复或删除数据。
版本差异给出新增/移除/改变的文档 ID，不自动迁移项目。卡片审计只能检查结构和字面摘录，
不能判断观点成立、自动识别语义冲突，或判断已发表论文是否撤稿。

## 项目分支与交接

```bash
python3 tools/research_assistant.py project-list
python3 tools/research_assistant.py project-fork patient-autonomy patient-process
python3 tools/research_assistant.py project-export patient-process
```

fork 复制项目状态并记录来源，拒绝覆盖已有目标。不是创建聊天，也不是模型训练。
export 写到 `.local/exports/` 下的独立 Markdown 文件，保留已答问题/审计/下一步与版本。
导出可能包含私人研究内容；本命令不会发送给其他人。

## 资源约束检查

`python3 tools/research_assistant.py plan-check <计划或项目.json>` 检查显式方法禁用、
时间预算、资源可得性与研究用途许可，返回 blocked / conditional / ready_for_planning。
格式与边界见 [研究推进主线](research-pipeline.md)。可选 research_plan 随项目保存、
历史修订、分支和导出保留；检查本身不修改项目，也不评价创新或录用可能。

## 提取缓存与合集重叠

启用 `--extract-pdfs` 后，以 PDF 文件内容 SHA256＋提取器版本作为缓存键，写 `.local/pdf-cache/`。
第一次仍需解析，后续文件内容不变可复用；每次仍读文件哈希，附件丢失不能靠旧缓存冒充可用。
`--refresh-pdfs` 绕过缓存读取，适合排查提取质量，不自动 OCR。
多合集重叠按最近 synced_at 的整条记录选取，同步时刻相同以合集键稳定排序；
这避免混合片段，但不等于跨合集事务快照。不同 Zotero 条目键的重复文献仍保留，doctor 报告 DOI 重复。

## 质量工具

完整命令与状态边界见 [quality-lab.md](quality-lab.md)：semantic-queue/semantic-submit、
多查询融合/检索回归、PDF 版面和 OCR 候选、逐期对账、DOI 更新通知、教师盲评打包与汇总。
可选 PyMuPDF 在独立质量工具中使用，原有标准库检索和 pypdf 同步仍可单独运行。

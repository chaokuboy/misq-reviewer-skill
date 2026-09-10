# MISQ 研究助手：实现与维护

更新：2026-09-09。当前是静态档案＋本地词项检索＋项目状态；不是模型微调，未接入向量模型。
旧架构与决策保留在 Git 历史（47aafdc），本文件描述实际实现，避免沿用过期说明。

## 1. 入口与分工

- SKILL.md：模式路由、判断纪律、六段诊断。
- AGENTS.md：仓库使用与维护入口。
- references/evidence.md：来源类型、时效、知识卡结构与核验纪律。
- references/dialogue.md：四阶段推进/回退、逐轮提问和项目状态。
- references/local-tools.md：可执行命令、限制、恢复流程。
- profiles/misq.md：期刊画像与 D8-01 至 D8-15 稳定审计入口。
- profiles/misq_submission_guide.md、knowledge/ 九份蒸馏：历史阅读成果，尚未本轮原文复核。
- profiles/editorial_list.md：历史文献索引；editorial_to_add.md 是旧补抓建议，不等于现有覆盖。
- tools/research_workflows.py：上下文、证据包、卡片审计、健康检查、版本比较与项目分支/导出。
- references/research-workflows.md：9 类按需研究任务协议。
- tools/research_assistant.py：本地检索/状态/覆盖工具（标准库、FTS5；PDF 后备依赖 pypdf）。
- tools/fetch_misq.py、analyze_corpus.py：旧 Crossref 获取和关键词统计。
- tools/extract_pdf_text.py：旧正则/压缩流提取器，不是 PyMuPDF，不保证 CID/扫描件可读。
- tools/download_fulltext.py、download_fulltext_guide.md：旧 EBSCO 路线，绑定原机构项目，非通用下载器。
- tools/distill_prompt.md：原文→候选知识卡的整理协议。
- tests/：离线工具测试。examples/：人工/模型行为协议与本轮走查记录。

## 2. 数据边界

全文、索引、私有卡片、项目状态、cookie/API key 不进入公开仓库。
保留原 .gitignore 红线，新增 `.local/`。本轮不移动或修改 Zotero 文件，不使用 Web API key。
旧交接记载数百份 PDF、120 条 Editorial 和 linked_file 附件；这些是历史记录，
本轮打开 Zotero 后 API 已连通，并读取“近五年MISQ”合集 345 条记录。
缓存文本请求返回 404，已增加本地 PDF 后备提取；实际提取覆盖另见 examples/VALIDATION.md。
不能把历史数量作为当前完整覆盖证明。

## 3. 可执行数据流

`build` 读取画像、指南和九份蒸馏；按文本块索引，并标 `legacy_distillation/verified=false`。
有 `.local/cards/*.json` 时校验卡片最小字段；有 Zotero 快照时加入题录和已索引 PDF 文本。
采用中文双字切分＋英文 token，SQLite FTS5 排序；支持显式中英词表扩展、来源/年份筛选、同篇限额。检索命中不代表原文支持主张。

`collections` / `sync-zotero` 只读 127.0.0.1:23119 本地 API，绕过系统代理且不跟随重定向。
按实际合集键分页枚举直接成员和 PDF 附件，优先读取 Zotero 已索引文本；`--extract-pdfs` 在缓存失败时用可选 pypdf 只读本地 PDF。
后备定位保存 PDF 物理页序号，不等同印刷页码；空文本页报告，不自动 OCR。
未分页文本的 locator 只标 offset，不能当 PDF 页码。列表读取失败则不发布快照；
单附件失败写 failures 并去除该次不可用文本。同步删除体现在新快照，旧知识版本仍保留。
当前每次扫描整个选定合集，尚非版本游标式增量同步；不遍历子分类。

`build` 对文档内容哈希生成不可变 SQLite 文件，提交后原子更新 current.json。
项目固定知识版本，新 build 不影响已有项目。快照仅在 build 时发布；同步本身只更新本地候选数据。

## 4. 对话与判断

四阶段是推进目标，不是固定问卷。根据回答选择一个最关键不确定性，避免重复、允许暂缓。
固定六段诊断，分开期刊契合度与研究成熟度；资料不全可暂无法判断。
审计四态：已有支持、待确认、存在缺口、不适用。已发表案例不推导录用概率。
按来源真实日期与评估日期比较；同年且日期不清则时序待确认。
旧蒸馏可提示追问，但硬性政策或严重结论需原文与稿件证据支持。

## 5. 项目状态

`.local/projects/<slug>.json` 是当前状态；history 保留旧修订。
保存要求 expected-revision，文件锁防同时覆盖；原子替换避免半写入。支持 macOS/Linux。
记录事实/主张/未知/决定/已问问题/审计与下一步；每项来源定位由宿主填写。
project-list/fork/export 支持本地研究状态分支与交接，不自动创建聊天。
工具检查字段与基本证据存在，不判断论证是否成立，也不自动判断阶段和生成问题。
不存在独立聊天服务：宿主模型执行 SKILL，工具负责检索和状态。

## 6. 核验与更新 SOP

1. 打开 Zotero，确认本地 API 可用，枚举分类；选定相关合集同步。
2. 查看 failures，核对覆盖，必要时在 Zotero 重建索引或人工阅读 PDF。
3. 依据 distill_prompt 生成本地候选卡；默认 unverified。
4. 人工比对 claim、原文定位、限定条件与例外后改变 verified，不能只因字段齐备自动核验。
5. build 建立新版；运行测试与行为走查。旧项目保持旧版，升级时记录判断变化。
6. 公开画像仅纳入核验后的凝练结论；新增审计 ID 不复用旧 ID。

## 7. 联动与验证

模式/报告改动同步 SKILL、dialogue、README、examples。
证据规则改动同步 evidence、画像前言/维度8、distill_prompt、工具验证和测试。
工具/数据格式改动同步 local-tools、本文件、tests。

维护前按 examples 记录基线；维护后执行 unittest、quick_validate 与人工 A/B 走查。
不同测试要如实区分：静态结构不证明模型行为；历史发表不作答案；盲测不提供评分说明。
本轮未做独立模型盲测，也未逐篇原文核验。

## 8. 剩余工作

- 已按19期目录做标题级对账，剩余未匹配项需 DOI/作者/页码复核；OCR与表格候选仍需版面核对。
- 从真实原文生成并核验标准卡/案例卡（现有6张editorial候选卡、4张案例卡；已作助手语义复核，未人工核验）。
- 完整卡 schema、跨卡冲突审查、版本游标增量和多合集一致快照。
- 语义检索是否有必要，要通过关键词检索召回测试决定。
- 教师盲评多轮提问质量；其他期刊建立独立证据包，不直接复制 MISQ 门槛。
- 旧数据脚本的分页终止、窗口、覆盖率与下载指引另行修复，未在此轮宣称完成。

## 9. 发布

开发在 codex/evidence-guided-review。修改前后核对 git diff，确认没有本地数据。
本轮只本地实现，没有 push。用户要求发布时可用正常 git；网络失败再用官方 API，
不在脚本里硬编码凭据。回退从 Git 恢复公开文件、从已有 SQLite 快照恢复知识版本，
项目旧状态通过 history 取出后以新 revision 保存，避免覆盖并发新进展。

## 10. 第二轮实现

详见 examples/REVIEW_V2.md。新检索兼容旧快照；卡片新增来源日期/DOI/条目键索引字段需 build。
本地 PDF 缓存以文件内容和提取器版本哈希寻址，旧快照保留，刷新不改变项目固定版本。
多合集按最近同步的整条记录选择，doctor 报告不同条目键的 DOI 重复；不自动删文献。
cards-audit 是字面引用检查，不自动提高核验状态。versions 比较原始文档 payload，
元数据改变也计 changed，不能直接解释成学术观点改变。
17 项测试与真实本地 CLI 冒烟结果见 examples/REVIEW_V2.md；仍无独立模型盲测。

## 11. 第三轮质量工作台（2026-09-10）

quality_lab.py 提供目录对账、Crossref 更新通知、语义复核队列/提交、多查询RRF与检索回归、
PyMuPDF 坐标/表格/页图/OCR候选。blind_eval.py 只处理真实回答和真实评分，不生成模型答案。
evaluations/ 存放8场景盲评协议及3目标检索开发集，不包含真实教师评分。
目录缓存、全部真实卡片和评分资料只在 .local。代码测试使用合成临时数据，和教师评测分开报告。
质量工具不自动覆盖全文索引；卡片字段更新后 build 发布新知识版本，旧项目不自动升级。
当前自动测试29项；真实接入和剩余边界见 examples/QUALITY_V3.md。

### 证据闭环补丁（2026-09-10）
证据包固定单一知识版本，接入版本绑定的语义审核与 evidence_use 状态；出版通知报告保留
按内容去重的历史，防止后续无命中覆盖旧警报。详见 [质量工作台](references/quality-lab.md)
及 [本轮验证](examples/QUALITY_V4.md)。33 项软件测试通过，不代表追问效果已获教师验证。

### 盲评输入与覆盖补丁（2026-09-10）
未完成评分也校验已填值和重复身份，缺理由暂不计分；汇总列出零评分案例与每案例评分数。
无效回答输入不创建评测目录。36 项软件测试通过，案例等权统计新增回归；
验证范围和复现结果见 [第五轮记录](examples/QUALITY_V5.md)。

### 外部合成测试材料接入（2026-09-10）
`tools/import_deepseek_eval.py` 从 DeepSeek 包抽取纯输入，匿名化案例 ID，记录文件哈希并检查
历史两版输入是否一致。原始期望值、模拟教师评分与旧技能规则不自动合并；产物只在 `.local`。
新增导入隔离和错误输入测试，完整测试现为 38 项。见 [接入核查](examples/DEEPSEEK_INTAKE.md)。

### 当前版本行为评测（2026-09-10）
已实际运行6案双条件、双条件五轮对话（第5轮新上下文摘要恢复），并保存匿名模型评审。
修订前2案出现5处稳定ID来源归属错配；修复出处与范式补充的区分，并澄清gap spotting
应对照完整论证。修订后执行3案开发复测。报告、限制及原件索引见
[行为评测记录](examples/BEHAVIOR_R1.md)。上文“未做独立模型运行”描述此前轮次，
现已有独立执行与模型评审；真实教师评分、原文语义核验和工具联动效果评测仍未完成。
新增behavior_run冻结/收集工具，自动测试现41项。没有在线检索、修改Zotero或发布。

### 研究推进主线试跑（2026-09-10）
references/research-pipeline.md 串联资源、最近邻、契合度/成熟度、证据缺口、路线与修订。
tools/research_planning.py 提供显式依赖检查；research_plan 为可选项目字段，经保存校验，
沿用原修订锁、history、fork 和 export。工具不推断研究创新或识别因果有效性。
候选A按合成情境运行，实际阅读6篇本地PDF的相关章节，保存两版判断及路线检查。
实际运行与验证范围见 [主线试跑](examples/PILOT_PIPELINE.md)，不将合成资源当真实准入。

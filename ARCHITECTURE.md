# MISQ 投稿小助手 · 实现方案与项目交接（给 Codex 的完整文档）

> 交接人：chaokuboy（深圳大学 · IS 研究者）｜ 最后更新：2026-09-08
>
> **本文是开发者视角的完整实现文档**：数据从哪来、怎么凝练成画像、模型运行时如何执行本包、
> 有哪些纪律与红线、以及以后如何安全地优化。**如果你是 Codex 且任务包含"优化 / 修改 /
> 重构 / 扩展 / 修复本技能"——先读完全文再动手；如果只是用本技能评估论文，读 `SKILL.md` 即可。**

---

## 0. 三十秒看懂这个项目

一句话：把 MIS Quarterly 的"隐性审稿标准"从主编 Editorial 与方法论评论中蒸馏成**一份可溯源的
静态档案**（期刊画像 + 审稿人视角审计清单），做成能在 Claude Code / Cursor / Codex 等任意
AI 编码工具中加载的技能包；模型判断论文时**只能对照档案条目并标注来源**，禁止凭印象扮演审稿人。

| 项 | 值 |
|---|---|
| 领域 | IS 学术出版（MIS Quarterly） |
| 形态 | GitHub 仓库 `chaokuboy/misq-reviewer-skill`（27 个公开文件）+ 大量**仅本地**数据（版权/凭据红线） |
| 双功能 | ① **苏格拉底追问**（梳理模糊的研究想法）② **投稿可行性诊断**（"能不能投 MISQ / 创新够不够 / 还缺什么 / 补什么实验"） |
| 运行载体 | `SKILL.md`（Claude Code/Cursor 等 skills 规范）＋ `AGENTS.md`（Codex 入口）＋ `profiles/` 档案 ＋ `examples/` 冒烟测试 |
| 语言 | 界面与报告中文，术语保留英文 |

**设计哲学（最重要的原则）**：本项目的一切价值都建立在"档案化（archival）"之上——
* 判断依据 = 从真实 Editorial/方法论评论中**凝练出的条目**（每条可溯源到哪篇 editorial、哪条评论）；
* 模型角色 = **审计员**（把稿件特征对照档案条目，命中即报＋附证据），**不是**扮演审稿人自由发挥；
* 因此判断质量不依赖宿主模型的"是否恰好背过 MISQ 知识"，且档案可随新 editorial 持续更新。

### 迭代历史（本项目怎么长成今天这样的）

| 阶段 | 时间 | 做了什么 |
|---|---|---|
| ① 骨架期 | 2026-09-06 | 深圳大学 EBSCO proxy 批量下载近五年 MISQ 全文（约 350 篇，本地 `corpus/`）；Crossref 拉元数据 → `analyze_corpus.py` 做 519 篇摘要的方法/主题统计 → 画像 `misq.md` 维度 3（方法）、6（热点） |
| ② 主编回填期 | 2026-09-06 | 精读 2021–2024 六篇 Editorial（DEI/CITC/因果/Tuum Est/SB×2）→ `misq_submission_guide.md`；回填画像维度 0/1/2/4/5/7，形成"追问＋诊断"双模式 |
| ③ 档案化审计期 | 2026-09-08 | 用户反馈："skill 不是让你扮演审稿人，而是基于审稿人视角判断不足" → 画像新增**维度 8 审计清单**（15 行，逐行带档案来源）；诊断第 5 步改为档案锚定审计；输出模板加 ⑤不足审计＋⑥开放问题 |
| ④ 多宿主与交付期 | 2026-09-08 | 补 2025/2026 editorial 蒸馏（49:1–49:4、50 年综述）至 9 份；新增 `AGENTS.md`（Codex 入口）；双模式"入口先选功能"；README 对齐；`examples/` 冒烟测试；本交接文档 |

---

## 1. 仓库结构（公开，27 文件）

```
misq-reviewer-skill/
├── SKILL.md                      ★ 核心指令（模型每次运行必读）：frontmatter + 双模式 + 铁律 + 输出模板
├── AGENTS.md                     Codex 入口：克隆后目录内启动自动加载；含"使用"与"优化"两套指引
├── ARCHITECTURE.md               本文档（开发者/优化者必读）
├── README.md                     给人类的说明：用途/安装（Claude Code、Cursor、Codex、其他）/使用边界
├── LICENSE                       MIT
├── .gitignore                    红线清单（见 §3）
├── profiles/
│   ├── misq.md                   ★ 期刊画像（核心锚点）：维度 0–8
│   ├── misq_submission_guide.md  ★ 主编投稿指南：SB 投稿 20 条 / 拒稿信号 / 各类型要求 / 方法论红线 / 审稿人视角
│   ├── knowledge/                9 份精读提炼 _distill_*.md（溯源材料，供维度 8 引用）
│   ├── editorial_list.md         2010–2026 Editorial/Commentary 索引（120 篇，含 DOI）
│   └── editorial_to_add.md       可选补抓清单（Rai 2017a/2018、Burton-Jones 2023 等）
├── examples/                     冒烟测试
│   ├── README.md                 测试协议、通过标准、故障排查表
│   ├── case_a_misq_diagnosis.md  模式②用例 + 档案审计参考答案（Adamopoulos, MISQ 46(1) 2022 真实发表案例）
│   └── case_b_socratic.md        模式①用例 + 行为检查表
└── tools/                        （可选）数据更新/下载脚本（无凭据部分公开）
    ├── analyze_corpus.py         对摘要 JSONL 做方法/主题词频统计（重跑画像维度 3/6 的数字）
    ├── fetch_misq.py             从 Crossref 增量拉取 MISQ 元数据（产出 *.ris / *.jsonl，本地）
    ├── extract_pdf_text.py       本地 PDF → 文本（含 pymupdf 处理 CID 型 editorial）
    ├── download_fulltext.py      EBSCO 全文批量下载（需 tools/cookies.txt，见 §4）
    ├── download_fulltext_guide.md 抓取指引（步骤文档）
    └── distill_prompt.md         精读蒸馏提示词规范（模型蒸馏 editorial 时的固定 prompt）
```

模型运行时的**读取优先级**：`SKILL.md`（必读）→ `profiles/misq.md`（必读）→
`profiles/misq_submission_guide.md`（按需）→ `profiles/knowledge/*.md`（按需溯源）。

---

## 2. 本地资产（不进 GitHub）与版权红线

以下内容**只在作者机器上**，绝不上传（`.gitignore` 已逐项排除）：

| 资产 | 内容 | 排除原因 |
|---|---|---|
| `corpus/` | 约 350 篇 MISQ 全文 PDF（含 `corpus/editorial2025/` 4 篇 2025 editorial） | **版权**：期刊论文全文归 MISQ 及作者 |
| `editorial_texts/` | 13 份 2021–2026 editorial 提取文本 | 同上（提取自受版权全文） |
| `profiles/knowledge/_raw/` | 10 篇方法论评论全文 txt（2021–2025，蒸馏原料） | 同上 |
| `*.ris` / `*.jsonl` | Crossref/机构库元数据批量文件 | 体积大 + 冗余（DOI 都在 editorial_list.md） |
| `tools/cookies.txt` | EBSCO 机构代理 cookie | 凭据 |
| `tools/zotero_import.py` / `zotero_fix_linked.py` / `zotero_sync_new.py` | 内含 **Zotero API key** 的导入/修链/同步脚本 | 凭据（key 可撤销，务必保密） |

`.gitignore` 现有规则（注释即语义，勿把注释写进规则行内）：

```
tools/cookies.txt
tools/zotero_import.py
tools/zotero_fix_linked.py
tools/zotero_sync_new.py
corpus/
editorial_texts/
profiles/knowledge/_raw/
*.ris
*.jsonl
.DS_Store
__pycache__/
*.pyc
node_modules/
```

**红线铁律（优化时不得触碰）**：任何把全文、提取文本、cookie、API key 提交进公开仓库的改动都是
事故。若误推：立即在 GitHub 撤销对应 token / 删除文件历史，不"删文件了事"。

---

## 3. 数据资产盘点与获取路径（若需扩容时照此操作）

| 资产 | 现状 | 来源与路径 |
|---|---|---|
| 摘要元数据 | 519 篇（2020–2026 窗口） | `fetch_misq.py` 从 **Crossref API**（`api.crossref.org`）按卷期拉取 → 本地 `misq_recent5y.jsonl/.ris` |
| 全文 PDF | 约 350 篇（本地 corpus/） | **EBSCO**（深圳大学 accproxy：`research-ebsco-com.accproxy.lib.szu.edu.cn`，需 cookie）→ `download_fulltext.py`（项目 items API 定位 → 2-step 全文 URL 下载），详见 `download_fulltext_guide.md` |
| Editorial 元数据 | 120 条（2010–2026：Editor's Comments 64 / Guest Editorial 9 / Research Commentary 47） | 逐条按 DOI（见 `profiles/editorial_list.md`）；AIS eLibrary Editor's Comments 通常免费 |
| Editorial 全文 | 关键篇 PDF 在 corpus/editorial2025 等；文本在 editorial_texts/ | 2021–2026 现行主编观点为主（**决策：不下载 2010–2020 editorial 全文**，见 §10 D1） |
| Zotero 文献库 | 用户 **20962168**；合集「近五年MISQ」=5TGSVJKZ（345 篇研究论文）；「MISQ Editorial 文献库」=VJID6Z9W（120 journalArticle + 附件） | Zotero Web API v3（key 仅在本地脚本） |
| Zotero 附件 | 免费配额 300MB 已尽 → 改用 **linked_file**（`path` 指向本地 corpus 绝对路径） | **路径依赖警告**：corpus 目录一旦移动，全部附件链接失效，需重跑 `zotero_fix_linked.py` |

---

## 4. 画像体系 `profiles/misq.md` 详解（核心资产，模型判断的唯一锚点）

画像头部写死了纪律："每次追问/诊断，判断锚点必须取自本文件，禁止模型临时发挥。"
单文件、维度 0–8。各维度 = 内容 + 数据来源 + 更新方式：

| 维度 | 一句话内容 | 数据来源 |
|---|---|---|
| 0 | 一句话定位（MISQ 到底要什么 / 拒绝什么） | 综合凝练 |
| 1 | 期刊使命与边界（Aims、身份标准、big tent、与 ISR 差异、比较优势、DEI/可持续背书） | SB-2024/2026、BJ-2023、49:2/49:4、Benbasat & Zmud 2003 等 |
| 2 | 理论贡献标准（贡献类型清单、四路径、Motivate-Create-Mobilize、"贡献不足"危险信号） | NG/FL/CO、CITC-2022、SB-2024 |
| 3 | 方法偏好与门槛（519 篇方法占比、50 年演变、各方法合格线：DSR/因果/质性/定量行为） | `analyze_corpus.py` 统计 + 方法评论 2022–2025 |
| 4 | 高频拒稿理由 Top 10（含审稿人问法） | SB-2024 拒稿信号 + 综合 |
| 5 | 创新类型地图（高价值 vs 伪创新、借用贡献谱系、范式判定、novelty–rigor–relevance） | 49:3、TB-2022、King/Ram & Goes-2021 |
| 6 | 领域热点问题地图（Top10 占比、上升主题、50 年三阶段/AI 三波） | `analyze_corpus.py` 统计 + 50 年综述 |
| 7 | 追问/诊断锚点速查表（四阶段 ↔ 取哪几维 ↔ 输出什么） | 自设计 |
| **8** | **审稿人视角不足审计清单（deficiency audit）**：15 行审计项，每行带档案来源代码；诊断"还缺什么"只准用本表 | 全部 distill 的"扣分/审稿"条目合并 |

### 4.1 维度 8 的机制（最关键的一维，2026-09-08 新增）

* **目的**：把"审稿人视角"从模型的主观扮演变成**记录在案的档案对照**。
* 15 行审计项覆盖：gap spotting、so-what 不清、开强尾弱、模式未入理论话语、面包箱测试、
  工作化借用/IT 外生、伪创新/事后理论化、因果声明与证据不匹配、机制证据层级、
  稳健性堆叠、测量效度、披露可复现、泛化越界、方法过时、for whom/at what cost。
* 来源代码（文档内通用于此）：`SB`=Susan Brown 2024（20 条/审稿视角）｜`M22C`=2022 CITC｜
  `M22Q`=2022 因果｜`NG/FL/CO`=2021–22 理论三评论｜`TB`=Theory Borrowing 2022｜
  `Q22`=2022 质性｜`C25/D25`=2025 因果图/DSR 效度｜`491/492/493/494`=MISQ 49:1–49:4 (2025)｜`50Y`=50 年综述 (2026)。
* **时效标注规则**：评估 2021–2022 时点稿件时，2022 及以前来源≈"当年标准"；2024–2026 来源
  必须标注**"当代镜头"**（提示性，不计当年硬伤）。这防止拿 2025 年的新标准冤枉 2021 年的稿。
* **与维度 4 的分工**：维度 4（拒稿 Top10）= 会不会被拒（门槛）；维度 8 = 审稿人每轮 R&R
  会追问的不足。诊断报告 ⑤ 列命中项，⑥ 列"档案无依据但重要"的开放问题。

### 4.2 画像内一致性

维度 7 速查表把"追问四阶段 / 诊断五步"映射到各维度；维度 8 行号被 `examples/case_a` 的
参考答案引用（如"维度 8 行 7"）。**改动维度 8 行号或增删行时，必须同步更新 case_a 引用与
SKILL.md 措辞**（见 §11.3 一致性 checklist）。

---

## 5. 知识蒸馏管线（editorial → `_distill_*.md` → 画像）

```
① 获取 editorial 全文（官网/EBSCO/AIS eLibrary，作者合法渠道）
② 提取文本：tools/extract_pdf_text.py（pymupdf；对图表型/CID 编码 editorial 也能抽文本）
   → editorial_texts/*.txt（仅本地）
③ 精读蒸馏：按 tools/distill_prompt.md 的固定 prompt 让模型逐篇产出 _distill_*.md
   → 每份 distill 顶部注明出处（如〔49:2〕= MISQ 49(2) 2025 Carter & Brown）
   → 只写"凝练条目＋出处"，不转载原文长句
④ 回填画像：把 distill 的要点并入 misq.md 相应维度（新增事实→新条目；与现有条目冲突→
   标注出处后并列或裁决）以及 misq_submission_guide.md
⑤ （可选）若有新审计类扣分模式 → 在维度 8 增行，并同步 case_a 与 SKILL.md 措辞
```

### 5.1 现有 9 份 distill 的来源与覆盖（溯源表）

| 文件 | 覆盖的来源 | 主要喂给 |
|---|---|---|
| `_distill_burtonjones.md` | DEI Position Statement (2021, BJ & Sarker)；Tuum Est (2023, BJ) | 维度 1/6；指南六（期刊运作） |
| `_distill_susanbrown.md` | 2024 两篇：Maximizing Chances…；Virtuous Reviewing | 指南一~五（20 条、拒稿信号、审稿人视角）→ 维度 2/4 及维度 8 多行 |
| `_distill_method2022.md` | CITC (Miranda et al. 2022)；Causality Meets Diversity (2022) | M22C/M22Q → 维度 3/8（行 4/8/10/11/13） |
| `_distill_theory.md` | NG (2021)；FL (2021)；CO (2022) | 维度 2/8（行 2/13/11） |
| `_distill_innovation.md` | King 2021；Ram & Goes 2021；Theory Borrowing (Jiang et al. 2022) | 维度 5/8（行 6/7） |
| `_distill_method.md` | DSR Validity (2025)；Design Echelons (2024)；Causal Diagrams (2025)；Qualitative (2022) | 维度 3/8（行 8/12） |
| `_distill_evolution50.md` | MISQ 50 周年综述 (Susan Brown, MISQ 50(2) 2026) | 维度 1/3/6（50 年趋势、方法演变、比较优势） |
| `_distill_2025_innovation_quant.md` | 49:3 Rebalancing Novelty…(2025)；49:1 Quantitative Behavioral (2025) | 维度 5/8（行 7/9 等）+ 维度 3 行为研究要求 |
| `_distill_2025_dei_green.md` | 49:2 Global by Design (Carter & Brown 2025)；49:4 Beyond Green IT (Brown 2025) | 维度 1 背书/立场；维度 8 行 15（for whom/at what cost） |

### 5.2 统计管线（画像中的客观数字）

`fetch_misq.py`（Crossref，按卷期）→ 元数据 JSONL → `analyze_corpus.py`（方法/主题词频，
产出如"实验 24.1%、平台经济 28.3%"）→ 手工回填 misq.md 维度 3/6 顶部。
**数字有"统计窗口"**：换窗口（如扩到 2026 全年）须整表重算并更新 misq.md 头部的数据来源说明，
避免新旧混用。

---

## 6. 运行时设计（模型如何执行本包）

### 6.1 `SKILL.md` 解剖

1. **frontmatter**（兼容 Claude Code Skills）：`name: misq-reviewer`；`description: >-` 折叠块，
   需 ≤1024 字符，写明"两种用途＋触发词"。注意：Claude Code 要求**目录名 = frontmatter name**。
2. **一、身份与工作原则**：定位 = 档案审计员（非审稿人）；**铁律 3 条**：
   ① 不足判断＝逐条对照维度 8，命中即报＋论文证据；② 禁"若我是审稿人会打…"自创观点，
   档案无据 → ⑥ 开放问题；③ 结论须注来源，标准年份晚于评估时点标"当代镜头"。
3. **二、启动加载**：misq.md 必读 → 指南按需 → knowledge 溯源。
4. **三、双模式（入口先选功能）**：**第 0 步**——会话开始/意图不明时，先展示 ①追问/②诊断
   请用户选，选定后执行对应模式的**完整流程**；触发词表命中可跳过介绍直达。
5. **模式 ① 苏格拉底追问**：Clarity(维1)→Prompt(维6)→Challenge(维2+4+8)→Evaluate(维5+2+8)；
   一次一问，只指差距不否定、不代写。
6. **模式 ② 投稿可行性诊断**：五步（边界→问题→贡献→方法→不足审计）→ 输出报告 **①–⑥**：
   ①可行性判断｜②创新点评估｜③缺口清单｜④补充建议｜**⑤不足审计（只列维度 8 命中项，
   每条＝不足|档案来源|论文证据|严重度）**｜**⑥开放问题（不计入可发表性判定）**。
7. **通用规范**：中文交流、保留英文术语、画像随新数据更新无需重训。

### 6.2 `AGENTS.md`（Codex）与宿主加载差异

| 宿主 | 加载机制 | 本包适配 |
|---|---|---|
| Claude Code | `~/.claude/skills/<name>/SKILL.md` 或项目 `.claude/skills/` | README 给出 `cp -r` 命令；整目录（含 profiles）复制 |
| Cursor | `.cursor/skills/misq-reviewer/`（或全局） | 同上 |
| **Codex (OpenAI)** | 自动读**仓库根 `AGENTS.md`**（不读 .claude/skills） | 克隆后在目录内 `codex` 即进入角色 |
| 其他（DeepSeek、Windsurf、Gemini CLI…） | 支持 AGENTS.md 则同 Codex；支持 skills 则同 Claude | 都不支持 → 系统提示词一行引导读 SKILL.md |

`AGENTS.md` 内含两条路径：**使用路径**（论文相关请求：先展示两功能让用户选→执行对应模式；
判断铁律同 SKILL.md；普通编程任务不受约束）与**优化路径**（先读本文档 ARCHITECTURE.md）。

### 6.3 防跑偏机制（都是"为什么这样设计"）

* 第 0 步选功能 → 防止模型自作主张挑模式、跳过用户真实意图；
* ⑤⑥ 分离 → 有档案依据的不足 vs 模型自认为重要但无据的点**分账**，避免把"我的偏好"说成"MISQ 标准"；
* "当代镜头"标注 → 防止时代错置的误判（拿 2025 编辑标准审 2021 稿）；
* 维度 8 表外禁新增 → 审计清单是封闭集合，扩展只能走"改档案"流程，不能运行时临时加。

---

## 7. 冒烟测试 `examples/`（克隆者验收 + 回归基线）

* `examples/README.md`：测试协议与**通过标准**。
  * 用例 A（模式②）：7 条检查——六段报告齐全、⑤逐条带档案来源、无"若我是审稿人"自创观点、
    2025 源标当代镜头、关键判定方向一致（IS 台前/因果匹配/方法创新必要/可冲 MISQ）、命中与放行项分类方向一致。
  * 用例 B（模式①）：5 条行为检查——先选功能、一次一问、锚定维度、四阶段推进、不代写。
* `examples/case_a_misq_diagnosis.md` 用**真实发表案例**校准方向：
  Adamopoulos, Ghose & Tuzhilin，MIS Quarterly **46(1), 2022, pp. 101–150**（DOI
  `10.25300/misq/2021/15611`，arXiv 2021 预印本即当年投稿版）。参考答案是"档案审计"在真实过刊
  上的演示：命中项全 ≤"中"、放行项覆盖致命几条 → 判"可以冲 MISQ"，与历史事实一致。
  **参考答案不是让模型抄答案**——文件明确注明"措辞可随档案演进，结构纪律不能丢"。

---

## 8. 已知边界（诚实清单，改需求前先看）

1. **档案时间覆盖 2021–2026**：方法论评论最早 2021/2022。评历史时点稿件 → 2022 前源≈当年标准，
   2024–2026 源标"当代镜头"；评 2021 前稿件（如经典复制类问题）档案几乎无直接依据 → 交 ⑥ 开放问题。
2. **统计窗口漂移**：维度 3/6 的百分比基于 2020–2026 摘要窗口，窗口滚动后数字会变（须整表重算）。
3. **全文仅本地**：GitHub 无全文 → 克隆者无法复现统计，只能信任画像数字（README 已声明数据来源）。
4. **Zotero 附件 = linked_file**：依赖 corpus 本地绝对路径，移动即断链。
5. **作者网络 github.com 被墙**：发布用 Contents API（§11.6）；克隆者一般无此问题。
6. **无全文 RAG**：当前是静态画像（人读 editorial→精炼条目）；本地全文向量检索是 roadmap（§13 R4），
   且只能本地用（版权）。
7. **宿主模型纪律依赖 prompt**：铁律无法硬性约束任何 LLM；examples 冒烟测试是唯一校验手段。
8. **非官方工具**：判断与 MISQ 编委真实决策无关，README 已声明免责。

---

## 9. 决策记录（Decision Log——每一条"为什么这么干"）

| # | 决策 | 理由 / 备注 |
|---|---|---|
| D1 | **不下载 2010–2020 editorial 全文** | 过时；现任 EIC 观点 2021–2026 已完整覆盖。可选补：Rai 2017a、Rai 2018、Burton-Jones 2023（见 editorial_to_add.md） |
| D2 | Editorial **元数据全收 120 篇**进 Zotero 当文献库（2010–2026 三类），PDF 只下关键篇 | 文献库用于溯源与未来按需蒸馏；PDF 下载成本高 |
| D3 | 全文/提取文本/凭据**一律不上 GitHub** | 版权（MISQ/作者）＋凭据安全；`.gitignore` 执行 |
| D4 | Zotero 附件用 **linked_file** | 免费配额 300MB 已尽；代价 = 路径依赖（corpus 移动会断链） |
| D5 | 发布通道 = **GitHub REST Contents API**（PUT contents，逐文件、带 sha） | 作者网络 github.com git 协议被墙（SSL_ERROR_SYSCALL），api.github.com 可达 |
| D6 | **2025 editorial 作者修正** | 并非 4 篇都出自 Susan Brown：仅 49:2（Carter & Brown）与 49:4（Brown）；49:1/49:3 是其他 senior editors——蒸馏与引用时不得张冠李戴 |
| D7 | 诊断机制从"扮演审稿人"改为"**档案审计**" | 用户反馈（2026-09-08）：skill 不是模型扮演审稿人，而是基于审稿人审稿视角（档案）判断不足 → 维度 8 诞生 |
| D8 | 双模式**入口先选功能** | 用户反馈：多数人用 Codex 克隆即用，启动时应先告知两种功能、让用户选择，再执行对应流程 |
| D9 | 增加 `examples/` 冒烟测试 | 克隆者此前无法自证"装对没装对" |
| D10 | 画像用**中文**、术语英文 | 主要用户为中文投稿人 |
| D11 | 单文件画像（misq.md） | 减少模型漏读风险（多文件易被跳过）；代价是文件变大、需维护引用一致性（§12） |

---

## 10. 优化手册（Codex 可直接执行的 SOP）

> 通用前置：改任何"运行时文件"（SKILL.md/misq.md/指南/distill/examples/README）前，
> 先跑一遍对应冒烟测试建立基线；改完再跑一次对照。改完按 §11 检查联动，按 §11.6 发布。

### 10.1 新增/更新一篇 Editorial 并入库
1. 拿到合法全文（AIS eLibrary / EBSCO / 官网），PDF 入 `corpus/` 对应子目录（本地）。
2. `extract_pdf_text.py` 提文本 → `editorial_texts/<年份>_<slug>.txt`（本地）。
3. 按 `tools/distill_prompt.md` 蒸馏 → `profiles/knowledge/_distill_<slug>.md`，顶部注明出处
   （作者、卷期、年份，如〔49:3〕）。
4. 更新 `profiles/editorial_list.md`（若该条不在清单中）与 `misq_submission_guide.md`（若属投稿建议类）。
5. 将凝练要点并入 `profiles/misq.md` 对应维度；若出现新的"审稿扣分类模式" → 维度 8 增行。
6. **联动**：维度 8 增行 → 更新 `examples/case_a`（行号引用）与 SKILL.md 措辞（如模板里提到清单范围）。
7. 更新 misq.md 头部"数据来源/最后更新"，更新本文件 §5.1 溯源表。
8. 跑冒烟测试回归 → 发布。

### 10.2 重跑摘要统计（换数据窗口）
`fetch_misq.py` → 新 JSONL → `analyze_corpus.py` → 得到新方法/主题占比 → 整表替换 misq.md
维度 3/6 顶部数字 → 更新头部窗口说明 → 若占比结论变了，检查维度 0/1 定性文字是否仍自洽 → 回归。

### 10.3 增删维度 8 审计行（一致性 checklist）
- [ ] misq.md 维度 8 表格增删行，**不要复用行号**（行号漂移是大忌）→ 建议改用稳定 ID（如 D8-07）后统一迁移一次
- [ ] `examples/case_a_misq_diagnosis.md` 中所有"维度 8 行 N"引用同步
- [ ] SKILL.md / AGENTS.md 中凡提到审计清单范围的措辞同步
- [ ] README"使用边界"如有对应描述同步
- [ ] 冒烟测试回归

### 10.4 修改模式流程或输出模板（三处联动）
输出报告 ①–⑥ 或追问四阶段若改 → **必须同步**：`SKILL.md` 模板 ＋ `README.md` 用法示例 ＋
`examples/README.md` 通过标准（第 2 条写明六段结构）＋ `examples/case_a` 参考答案结构。

### 10.5 新增宿主适配
- 走 SKILL.md 规范的宿主：无需改文件，改 README 安装段即可。
- 走 AGENTS.md 的宿主：AGENTS.md 已通用；如需定制在该宿主行为，另建说明并链回 AGENTS.md。
- 更新 README"其他 Agent"段与宿主矩阵（§6.2）。

### 10.6 发布到 GitHub（Contents API，作者网络专用）
```bash
export GITHUB_TOKEN=...   # 只从环境/本地读取，绝不写进仓库任何文件
# 1) 取当前 sha
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/chaokuboy/misq-reviewer-skill/contents/<path> | jq -r .sha
# 2) PUT 新内容（base64 + sha）
curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" -H "Content-Type: application/json" \
  --data '{"message":"...","content":"<base64>","sha":"<sha>"}' \
  https://api.github.com/repos/chaokuboy/misq-reviewer-skill/contents/<path>
```
新增文件不带 sha；已有文件必须带当前 sha（否则 409）。**作者网络无法 git push github.com**，
但克隆者/其他网络可用常规 git。若在非墙网络环境，直接 `git add/commit/push` 更省事——
保持 Contents API 与 git 两种通道的**内容一致**（每次发布二选一，不要双写造成分叉）。
发布后立即用 tree API 核验文件齐全（本会话惯例：`git/trees/HEAD?recursive=1`）。

### 10.7 本地环境重建（换机器时）
- Python PDF 库：pymupdf（本会话曾装到 `/tmp/pdflib`，`sys.path.insert` 引用；正式环境请 pip 安装）。
- EBSCO cookie：`tools/cookies.txt`（深圳大学 accproxy 会话，会过期）。
- Zotero key：本地 `tools/zotero_*.py` 常量；泄漏即撤销重建。
- corpus 路径：Zotero linked_file 指向的绝对路径；移动后跑 `zotero_fix_linked.py`。

### 10.8 常见事故与回退
- 误推敏感文件 → 立即撤销对应 GitHub token / Zotero key；用 `git filter-repo` 或 GitHub 支持清理历史。
- 维度 8 行号漂移 → 全面 grep "维度 8 行" 修正。
- distill 与 editorial 作者张冠李戴 → 以 editorial_list.md DOI 与原文首页为准复核（参考 D6）。

---

## 11. 一致性约束总表（动一处，查五处）

| 你改了 ↓ / 需同步 → | SKILL.md | AGENTS.md | misq.md | guide | distill | README | examples | 本文档 |
|---|---|---|---|---|---|---|---|---|
| misq.md 维度内容/数字 | 引用措辞 | — | — | 交叉引用 | — | 数据来源描述 | 判定方向 | §5/§8 |
| 维度 8 行号/增删行 | 措辞 | — | — | — | — | — | **case_a 引用** | §4.1/§10.3 |
| 输出模板 ①–⑥ / 四阶段 | —(源头) | 摘要提及 | 维 7 表 | — | — | 用法示例 | 通过标准/参考答案 | §6 |
| distill 增删 | 加载清单 | 读取清单 | 溯源引用 | — | — | 文件树 | — | §5.1 |
| 新增宿主 | — | 可选 | — | — | — | 安装段 | 测试段 | §6.2 |
| 数据窗口/统计 | — | — | 头部+维3/6 | — | — | 数据源表 | — | §10.2 |
| editorial_list 增删 | — | — | 数据来源 | — | 溯源 | — | — | §10.1 |

原则：**misq.md 是唯一事实源；SKILL.md 是执行入口；examples 是回归基线；README 是给人类的宣传（不能与前三者矛盾）；本文档记录"为什么"（不能与现状脱节）。**

---

## 12. Roadmap 建议（给后续 Codex 优化的选题池，按性价比排序）

| # | 建议 | 价值 | 备注 |
|---|---|---|---|
| R1 | **维度 8 行号 → 稳定 ID**（D8-01…） | 防漂移，目前行号被 case_a 硬引用 | 迁移后全仓 grep 替换 |
| R2 | examples **半自动回归**（golden 输出关键特征比对脚本） | 目前靠人眼对照 | 可做 `tools/smoke_check.py` |
| R3 | 画像**窗口版本化**（数字带窗口标注，如"2020–2026"） | 防旧数字误用 | 配合 §10.2 |
| R4 | **本地全文 RAG**（corpus 向量化，仅供作者本地问答/检索） | 把 350 篇全文用起来 | 版权红线：永不发布索引外的全文 |
| R5 | 画像 schema **模板化** → 复用到其他期刊（ISR/JMIS/ISJ…） | 扩大工具面 | 维度 0–8 是通用骨架 |
| R6 | 蒸馏**半自动流水线**（editorial 入 corpus → 自动提文本 → distill_prompt 调用 → 人工确认 → 回填画像） | 降低每次更新成本 | 需模型按 §10.1 执行 |
| R7 | 英文输出模式（英文投稿人场景） | 扩大用户 | 模板加语言开关 |
| R8 | 仓库级**链接完整性自检**（SKILL.md/AGENTS/README/examples 互引文件都在、维度 8 引用不悬空） | 防回归 | 可做成 CI 或脚本 |
| R9 | 2026+ 新 editorial 持续跟进（每年 4 期 Editor's Comments + 方法评论） | 档案保鲜 | 触发词：每季度 check editorial_list |

---

## 附录 A：来源代码速查

| 代码 | 全称/出处 | 年份 | 何时可作"当年标准" |
|---|---|---|---|
| SB | Susan Brown：投稿 20 条 / 拒稿信号 / Virtuous Reviewing | 2024 | 审 2024+ 稿；更早稿作参考 |
| M22C / M22Q | CITC / Causality Meets Diversity（方法论评论） | 2022 | 2021–22 及以后（≈当年） |
| NG / FL | Next-Gen Theorizing / Theories in Flux | 2021 | 2021+（当年） |
| CO | When Constructs Become Obsolete | 2022 | 2022+ |
| TB | Theory Borrowing for the Digital Age | 2022 | 2022+ |
| Q22 | Qualitative Research Methods in IS | 2022 | 2022+ |
| C25 / D25 | Causal Diagrams / DSR Validity | 2025 | 当代镜头 |
| 491–494 | MISQ 49:1 定量行为 / 49:2 Global by Design / 49:3 Novelty / 49:4 Green IT | 2025 | 当代镜头 |
| 50Y | 50 周年综述 | 2026 | 当代镜头（视角性，非扣分标准） |
| BJ | Burton-Jones（DEI 2021 / Tuum Est 2023） | 2021/23 | 视角与运作事实，非扣分标准 |

## 附录 B：术语表

| 术语 | 含义 |
|---|---|
| 画像（profile） | `profiles/misq.md`：凝练自真实数据的期刊标准档案，模型判断的唯一锚点 |
| 维度 8 审计清单 | 15 行"审稿人视角不足"条目，逐行带档案来源；诊断"还缺什么"只准用此表 |
| 档案来源 / 来源代码 | 每条判断依据指向的 editorial/评论（SB、M22C…），报告须标注 |
| 当代镜头 | 用 2024–2026 标准评估更早稿时的标注，表示"非当年硬伤" |
| ⑥ 开放问题 | 档案无直接依据但重要的点；不计入可发表性判定，需向 SE/AE 确认 |
| 冒烟测试 | `examples/`：克隆者验证安装是否生效、回归是否破坏的两组用例 |
| linked_file | Zotero 附件模式：只记录本地绝对路径（配额用尽后的替代方案） |
| Contents API 发布 | 作者网络（github.com 被墙）下，用 api.github.com REST 逐文件推送 |

# MISQ Reviewer Skill 🎯

**MIS Quarterly 期刊投稿小助手** —— 以 MISQ 主编 & 资深审稿人的视角，帮你：

- **🤔 苏格拉底式追问**：梳理你的研究想法，把问题问到"能过 MISQ 审稿人那关"的程度
- **🔬 投稿可行性诊断**：把你的论文方案贴进来，判断能否投 MISQ、创新点够不够、缺什么、该补哪些创新与实验

> 无需联网订阅、无需每次重读文献——本包内置一份**凝练自真实数据的期刊画像**（519 篇论文摘要统计 + 6 篇主编 Editorial 全文精读提炼），让 AI 的判断有据可依，而不是凭印象发挥。

---

## ✨ 两种用法

### 1. 苏格拉底追问（梳理研究想法）

> "帮我梳理一下这个研究想法……"

助手会依次用 **Clarity（澄清）→ Prompt（引导）→ Challenge（质疑）→ Evaluate（评价）** 四阶段提问，每个问题都锚定 MISQ 的真实审稿标准（如"去掉 IS 结论还成立吗？""这是 gap spotting 吗？"）。

### 2. 投稿可行性诊断（评估论文方案）

贴入你的方案（题目、研究问题、理论、方法/算法、数据、创新点表述），助手输出：

```
① 投稿可行性判断 → 可以冲 MISQ / 补 X 后可以 / 更像 CS 顶会或他刊
② 创新点评估     → 够不够、属于哪类贡献
③ 缺口清单       → 对照主编投稿指南逐条列出
④ 补充建议       → 创新角度 + 实验/方法 + 理论表述（每条标注依据）
⑤ 风险预警       → 审稿人会挑的硬伤
```

---

## 🚀 安装（克隆后放入你的 AI 工具）

```bash
git clone https://github.com/<你的用户名>/misq-reviewer-skill.git
```

### Claude Code

```bash
# 放到全局 skills 目录
mkdir -p ~/.claude/skills
cp -r misq-reviewer-skill ~/.claude/skills/misq-reviewer
# 或项目级：cp -r 到 <项目>/.claude/skills/misq-reviewer
```

### Cursor

复制到 `.cursor/skills/misq-reviewer/`（项目级）或全局 skills 目录，Cursor 会自动加载。

### 其他 Agent / Coding 工具（DeepSeek、Codex、Windsurf 等）

大多数兼容 `SKILL.md` 规范的 agent 只需把整个目录放进其 skills/rules 目录。
若你的工具不支持 skills 目录，可在系统提示词里加入一句话：
"启动时先读取 `SKILL.md`，并按其中定义扮演 MISQ 投稿小助手。"

---

## 📁 文件结构

```
misq-reviewer-skill/
├── SKILL.md                      ★ 助手定义（双模式指令，frontmatter 标准格式）
├── profiles/
│   ├── misq.md                   ★ 期刊画像（核心锚点：定位/边界/贡献标准/拒稿Top10/创新地图/热点）
│   ├── misq_submission_guide.md  ★ 主编投稿指南（6 篇 Editorial 凝练的 20 条建议等）
│   ├── knowledge/                editorial 三篇精读提炼
│   │   ├── _distill_burtonjones.md
│   │   ├── _distill_susanbrown.md
│   │   └── _distill_method2022.md
│   ├── editorial_list.md         Editorial/Commentary 索引（120 篇，含 DOI）
│   └── editorial_to_add.md       建议补充清单与抓取指引
└── tools/                        （可选）数据更新脚本
    ├── analyze_corpus.py         对摘要做方法/热点统计（重跑画像数据）
    ├── extract_pdf_text.py       PDF → 文本（本地使用）
    ├── fetch_misq.py             从 Crossref 增量拉 MISQ 元数据
    └── download_fulltext.py      批量下全文（需自备 EBSCO 机构 cookie）
```

---

## 🔍 画像怎么来的（方法透明）

| 数据源 | 处理 |
|---|---|
| MISQ 2020–2026 论文元数据（Crossref 官方） | 519 篇摘要 → 方法/主题词频统计（`analyze_corpus.py`） |
| 主编 Editorial 全文（合理阅读） | 精读 6 篇 → 提炼投稿指南、理论贡献标准、拒稿理由、审稿人视角 |
| 期刊运作信息 | 卸任主编总结、DEI 声明、主编问答 → 定位与边界 |

画像更新：有新 Editorial / 新数据时，重跑 `tools/` 并修订 `profiles/misq.md` 即可，助手无需"重新训练"。

---

## ⚖️ 版权与免责

- **本仓库只含凝练知识与分析成果**（原创），不含任何 MISQ 论文全文 PDF —— 全文版权归 MIS Quarterly 与作者。
- Editorial 内容以**引用/提炼**形式呈现，属于合理使用范畴；如需引用原文请标注出处（DOI 见 `editorial_list.md`）。
- 诊断结果仅供参考，不构成投稿录用承诺。
- 本人与 MIS Quarterly 无隶属关系；本工具为独立学术辅助项目。

---

## 📄 License

MIT © 2026 —— 详见 [LICENSE](LICENSE)。

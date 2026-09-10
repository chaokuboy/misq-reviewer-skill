# 克隆与加载 skill

先选最少依赖的方式。公开包自身即可进行静态追问与方案诊断；全文检索和项目保存为可选能力。

## 有文件读取能力的模型

按 README 将完整仓库克隆为 `misq-reviewer` 目录，保留 SKILL、profiles、references 的相对位置。
在新对话让 Agent 读取根目录的 `SKILL.md`，并提供研究任务。
首次回答应利用你已提供的内容，并说明当前依据的资料范围；无需强制填写完整问卷。

原生 skill 宿主按其当前文档安装整个目录，入口为 `SKILL.md`，名称为 `misq-reviewer`。
支持 AGENTS.md 的仓库助手还有该文件作为入口；其他宿主不会自动识别它，需显式读取 SKILL.md。
不同模型的指令遵循和文件能力有差异，本仓库没有验证“所有模型效果相同”。

## 仅支持聊天附件

先附上 `SKILL.md`、`references/evidence.md`、`profiles/misq.md`，并说明每份文件的相对路径。
追问再附 `references/dialogue.md`；研究路线比较再附 `references/research-pipeline.md`；
其他任务按 SKILL 的链接补充。附件通常不会保留目录，模型打不开链接时需提供对应文件。
这些是必要的流程资料，期刊论文只在当前问题需要时补充，不必一次上传全部全文。

可以发送：

> 请按附件中的 SKILL 执行，其他附件是对应路径的支持资料。我的任务是：【任务】。
> 当前没有终端或本地检索权限；缺少的来源请说明，不要声称已经检索或保存。

## 可选：本地工具环境

以下是需要全文检索或项目落盘时的进阶操作，不属于 skill 安装步骤。

以下命令在仓库根执行，适用于 macOS/Linux。Python 3.9+ 的 SQLite 需支持 FTS5。
静态档案索引只用标准库；不需要 API key、付费模型接口或 PDF 库。

```bash
python3 --version
python3 tools/research_assistant.py --help
python3 tools/research_assistant.py build
python3 tools/research_assistant.py search 'theory' --limit 3
python3 tools/research_assistant.py doctor
```

验收：build 返回 version 和 documents，search 返回候选 JSON，doctor 能读取索引。
没有 Zotero 数据时 coverage 为空属于正常情况，不能解释为期刊没有论文。
`packet` 主要查标准卡及论文候选，只有旧蒸馏的干净安装可能返回空结果；静态档案用 search 查。

项目保存前需 build。项目 ID 使用 `my-study` 这类短英文、数字与连字符名称。
工具只保存传入状态；模型必须实际调用 save，聊天才会落盘，详见[本地工具](../references/local-tools.md)。

## 可选 PDF 与 Zotero

打开自己的 Zotero，确认本地 API 可用，然后执行：

```bash
python3 tools/research_assistant.py collections
```

从返回结果中选择实际合集键，再按本地工具文档执行 sync-zotero。不要照抄历史报告里的合集键。
本地 API 地址为 `127.0.0.1:23119`；脚本不自动更改 Zotero 设置，不使用 Web API key。
无此能力时仍可用静态模式，或提供自己有权使用的论文附件。

需从 PDF 后备提取文本时，在仓库根执行：

```bash
python3 -m venv .local/venv
.local/venv/bin/python -m pip install -r tools/requirements-pdf.txt
```

之后用 `.local/venv/bin/python` 执行带 `--extract-pdfs` 的同步。
额外的表格/页图工具安装 `tools/requirements-quality.txt`；OCR 还需要相应语言数据，
并非安装 Python 依赖就一定可用。具体命令、页码含义和限制见[质量工作台](../references/quality-lab.md)。

原生 Windows 的项目保存依赖尚不兼容。静态模式可用；WSL 中的 localhost 与 Windows Zotero
不一定互通，本项目未验证该跨环境接入，不将 WSL 视为一键修复。

## 更新与迁移

没有本地代码修改时，在原克隆目录使用 `git pull --ff-only` 更新公开文件。
存在修改时先检查 git status 并保留自己的改动，避免覆盖；其他副本应先备份再更新。

`.local/` 不在 Git 中。迁移时备份整个目录，包括知识快照、项目、history、卡片和来源快照；
仅复制项目 JSON 不足以恢复它固定的知识版本。移动机器后 Zotero 附件路径可能失效，需检查并重新同步。
依赖环境建议在新位置重建。更新公开档案后 build 会产生新版本，已有项目不会自动升级。

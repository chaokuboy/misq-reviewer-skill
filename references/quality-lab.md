# 证据质量与评测工作台

所有全文、卡片、评审和质量报告默认写 `.local/`，不公开提交，不修改 Zotero 原件。
这些工具补强核验过程，不提供“自动证明论文正确”或“已优于普通助手”的结论。

## 标准卡、案例卡与语义复核

标准卡优先保留原文适用对象和反例，不把编辑意见升级为正式政策。
案例卡分别记录研究问题、作者主张、助手解释、设计、发现、局限；关键字段用
`field_evidence` 链接文档 ID，source 中记录原文片段及 SHA256。

```bash
python3 tools/research_assistant.py cards-audit
python3 tools/quality_lab.py semantic-queue
python3 tools/quality_lab.py semantic-submit .local/quality/review.json
```

semantic-queue 给出主张、适用性、例外和固定知识版本中的证据，供宿主模型或人工逐条判断：
`supported / overstated / contradicted / insufficient`。
review.json 包含 knowledge_version、reviewer_type（model/human）、reviewer、reviews 数组。
每条 review 必须有 card_id、card_sha256（排序 JSON 的 UTF-8 SHA256）、verdict、reason、
scope_check、counterevidence_check、evidence（document_id/quote）。
检查人口/情境、因果/关联、必然/可能、作者结论/助手推断、例外是否遗漏；主动寻找反证。

工具验证来源摘录存在、卡片版本未变和判断字段齐备。**它不自己理解论证，也不自动修改 verified。**
宿主模型作出的语义判断保留 reviewer_type=model，不能冒充教师核验或独立评审。
当前本地有 6 张 editorial 标准候选卡与 4 张案例卡，已作助手复核，仍待人工核验。
案例覆盖移动健康随机实验、电子学习设计科学、现象学解释性研究和理论借用论述；这些只是种子，不代表全部方法和主题。

## 教师盲评

执行 [评测协议](../evaluations/README.md)，8 个情境在 scenarios.json。
工具接收真实生成的两组回答，随机分配 A/B、隐藏条件名，评分者目录与解盲映射分离。
用同一模型、同一研究材料和相近预算控制比较；生成过程及技能/知识版本必须记录。
语气和引用样式仍可能透露条件，匿名编码不保证完全消除偏差。

```bash
python3 tools/blind_eval.py prepare .local/actual-responses.json
python3 tools/blind_eval.py summarize .local/evaluations/实验ID 教师评分.json
```

没有回答时拒绝生成假对照；没有教师评分时结果为 awaiting_real_human_ratings。
汇总先在同案例的评分者之间平均，再按案例平均，避免某案例多位评分者扩大其权重。
只报告描述性差异，不把小样本当优越性证明。评分缺失不是零，重复 case/rater 会报错。
未完成行也检查已填分数、偏好和重复身份；缺理由的行暂不计分。评分者 ID 去除首尾空格。
`pending_rows` 仅统计已提交但未完成的行；`unrated_case_ids` 列出尚无完整评分的案例，
`case_rating_counts` 显示各案例完整评分数，包含零。工具不知道计划邀请的评分者人数，
不能据此断言全部教师已交卷。无效回答输入在创建评测目录前失败。
真实多轮训练效果需另做连续项目观察，不能从单轮固定情境推导。

## 查询扩展与检索回归

```bash
python3 tools/quality_lab.py multi-search '患者自主性' 'mHealth patient self management' --version <固定版本>
python3 tools/quality_lab.py retrieval-eval evaluations/retrieval-seed.json
```

多查询使用 Reciprocal Rank Fusion 合并不同词项查询，按来源去重，支持固定知识版本。
英文替代表述由宿主根据问题生成，并向用户说明必要的概念变化；不把 autonomy 直接等同 self-management。
当前种子集只有 3 个已知目标，是在阅读这些论文后建立的回归集，**不是盲测集、不是完整相关性标注**。
reported recall_at_5 仅表示已标记目标的覆盖；不能解读为全库召回率，也不能证明模型理解正确。

## PDF 表格、公式和扫描页

```bash
.local/venv/bin/python -m pip install -r tools/requirements-quality.txt
.local/venv/bin/python tools/quality_lab.py pdf-quality /实际/原文.pdf --output .local/quality/pdf-review --pages 1 6 7
.local/venv/bin/python tools/quality_lab.py pdf-quality /实际/扫描件.pdf --output .local/quality/scan-review --ocr --tessdata .local/tessdata
```

PyMuPDF 输出页文本、坐标块、候选表格单元格、页图及质量报告。检查实际页图后再使用表格/公式。
`--ocr` 对稀疏文本页尝试英文 OCR，`--ocr-all` 可强制用于选定页；需本地 Tesseract 的 eng.traineddata。
本机已装英文语言数据；重建环境时从 [Tesseract 官方模型库](https://github.com/tesseract-ocr/tessdata_fast)获取。
不会自动下载或调用云端 OCR。OCR 失败保留明确错误，不把失败视为成功。

公式保留在原页图中，不声称自动可靠转换为 LaTeX。双栏顺序、合并单元格、无边框表格仍需核对。
检测器可能把示意图当表格：带 Figure 标题的区域标 figure_candidate，其他仍为 table_candidate，均未核验。
输出只是独立候选，不自动替换已发布索引。确认质量后可用页面证据人工补卡。

## 按期目录对账

```bash
python3 tools/quality_lab.py issues .local/toc
```

当前目标固定为 46(1)–50(3)，即 2022–2026 截至 2026 年 9 月；续期需更新范围与目录来源。
输入为宿主从 AIS eLibrary 取得的带行号目录文本。本机已有 19 期缓存；普通 HTTP 获取曾返回403，
本轮使用浏览工具读取。不要把解析空结果、缺页或接口失败当成某期不存在。

按 Articles 与 Editorial(s) 分区，排除封面、编委、目录等 front matter。
title_match 表示规范化标题匹配，not_matched 是待核，近似标题只列建议，不自动认定同文。
公开目录存在拼写/版本差异，应逐条用 DOI、作者和起始页复核后决定是否补收。
结果写 issue-reconciliation.json。该流程不会下载漏项、增删 Zotero 条目。

## 更正/撤稿元数据检查

```bash
python3 tools/quality_lab.py updates
python3 tools/quality_lab.py updates --doi 10.25300/MISQ/2022/16201
```

默认检查两种 MISQ ISSN 的更新通知并与本地 DOI 对照；--doi 同时查询原 DOI 及反向 updates 通知，
避免只依靠同刊通知。请求只含公开 ISSN/DOI，不发送论文全文或用户研究。
保存检查时间、通知 DOI、类型和失败状态。没有通知叫 no_notice_in_checked_metadata，**不是“没有撤稿”**；
错误/未知永远不算通过。不同查询的结果分别保存，旧报告日期不能冒充当前实时状态。
强判断前还应核对出版方/Crossmark，尤其是有通知、元数据未知或卡片来源已变化时。

实现依据：[Crossref 当前过滤器文档](https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/)、
[PyMuPDF 页面/OCR 文档](https://pymupdf.readthedocs.io/en/latest/page.html)。

证据包 packet 会附 publication_status（已保存报告、实际检查日期和未知状态），
不会在每次提问时自动发网络请求。该状态与项目固定知识版本分开；现存报告间的更新警报
不会被另一份无命中报告静默清除。cards-audit 同时提示本地卡片与固定版本的差异。

## 证据使用状态闭环（2026-09-10）

`packet` 在开始时固定一次知识版本，标准与案例检索共用该版本。
每条结果返回 `evidence_use`：`candidate_only` 仍需读上下文；`review_required`
表示出版更新警报、卡片来源审计问题或语义审核争议，先复核再用于判断。

语义审核以卡片 SHA-256 和知识版本双重匹配。版本或内容变化后旧审核计入
`stale_reviews`，不自动沿用；即使只是无关文献更新，也保守要求新版本复核。
`model_supported` 与 `human_supported` 区分自报审核者类型，不验证人的身份，
不修改 verified，更不等于教师盲评通过。冲突或损坏的审核记录会提示复核。

更新检查将旧报告和新报告存入 `.local/quality/publication-history/`，按内容哈希去重，
再替换当前报告。证据包合并历史与当前结果，后续无命中或网络失败不消除历史警报。
旧版本运行时已经覆盖丢失的报告无法恢复；历史警报暂无自动解除机制，需查出版方原通知。

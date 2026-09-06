# 建议补充下载的 MISQ Editorial / Commentary 清单

> 用途：在 EBSCO 里把下面这些加进「xiayulin/MISQ-paper」项目，加完告诉我，
> 我用下载脚本拉下来（含 editorial 全文），用于凝练画像维度 2/4/5。
>
> ⚠️ 查找技巧：这些文章在 EBSCO 里标题通常是 "Editor's Comments"（无副标题），
> 建议按 **卷期（Vol/Issue）** 或 **作者名** 搜索定位，不要只搜标题。

---

## A 类：必加核心（投稿/审稿视角，被反复引用）

| # | 卷期 | 作者 & 主题（IS 圈公认） | DOI |
|---|---|---|---|
| 1 | **47(1) 2023** | **Burton-Jones, Gray & Majchrzak "Producing Significant Research"** — 被引用最多，教你什么是"显著研究" | 10.25300/misq/2023/471e1 |
| 2 | **41(2) 2017** | **Rai "Avoiding Type III Errors: Formulating IS Research Problems that Matter"** — "gap spotting"批判的出处 | 10.25300/misq/2017/41.2.e0 |
| 3 | **42(2) 2018** | **Rai "The First Few Pages"** — 引言必做的三件事 | 10.25300/misq/2018/422e0 |
| 4 | **46(1) 2022** | Burton-Jones 2022 投稿指南系列·第一篇 | 10.25300/misq/2022/461e1 |
| 5 | **46(4) 2022** | Burton-Jones 2022 系列·第四篇 | 10.25300/misq/2022/464e1 |
| 6 | 41(1) 2017 | Rai "Diversity of Design Science Research" — DSR 多样性 | 10.25300/misq/2017/41.1.e0 |
| 7 | 40(2) 2016 | Rai "Synergies between Big Data and Theory" — 大数据+理论 | 10.25300/misq/2016/40.2.e0 |
| 8 | 39(4) 2015 | Saar-Tsechansky — 数据科学研究如何投 IS 顶刊 | 10.25300/misq/2015/39.4.e0 |
| 9 | 48(1) 2024 | Susan Brown (现任 EIC) 2024 第一期 | 10.25300/misq/2024/481e1 |
| 10 | 48(4) 2024 | Susan Brown 2024 第四期 | 10.25300/misq/2024/484e1 |
| 11 | 49(1)-(4) 2025 | Susan Brown 2025 全年 4 期（最新投稿动向） | 10.25300/misq/2025/49.1.00 等 |
| 12 | 50(1) 2026 | Susan Brown 2026 第 1 期 | 10.25300/misq/2026/501e1 |

> 说明：#1-#5 是从已下载 editorial 的正文引用里挖出的"被引用之王"，
> #6-#8 是 IS 投稿圈公认的经典方法/定位 editorial，其余是现任主编的近期观点。

---

## B 类：Research Commentary（方法论干货，可选加）

> 这些直接教"MISQ 认可什么方法/理论贡献"，来自 editorial_list.md 的 C 类。
> 优先加标注 ⭐ 的（方法论最核心）。

| 卷期 | 主题 | 说明 |
|---|---|---|
| 36(1) 2012 | Absorptive Capacity and IS Research | ⭐ 理论整合范本 |
| 37(4) 2013 | Positioning Design Science Research for Maximum Impact | ⭐ DSR 投稿定位 |
| 39(3) 2015 | Genres of Inquiry in Design-Science Research | DSR 类型学 |
| 42(1) 2018 | Making Rigorous Research Relevant | ⭐ 严谨与相关 |
| 45(4) 2021 | The Next Generation of Research on IS Use | ⭐ 理论前沿 |
| 46(2) 2022 | When Constructs Become Obsolete | （若未下载）构念过时 |

---

## 操作步骤

1. 打开 EBSCO（accproxy 那个链接），按上面卷期搜 Editorial，加入项目
2. 加完告诉我（比如"加了 A 类全部 + B 类 3 篇"）
3. 我跑 `download_fulltext.py` 增量下载 → 提取文本 → 凝练画像维度 2/4/5

> 加的时候在 EBSCO 搜索框试：`Editor's Comments AND 2022` 或直接按期刊浏览 MIS Quarterly 逐年翻。

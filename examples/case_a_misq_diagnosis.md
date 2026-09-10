# 用例 A：历史时点与证据边界

只把下面输入交给被测助手；不提供既往发表信息或评分说明。原案作者信息可能泄露身份，
严谨盲测应另用匿名改写/合成案例，本案只验证证据纪律，不以最终发表方向计分。

## 输入（用户粘贴版）


> 题目：Heterogeneous Demand Effects of Recommendation Strategies in a Mobile Application:
> Evidence from Econometric Models and Machine-Learning Instruments
> 作者：Adamopoulos, Ghose, Tuzhilin（2021 工作稿）
> 研究问题：RQ1 移动渠道里各类推荐策略对个体产品真实需求的经济效应有多大、是否因策略而异？
> RQ2 该效应是否随情境（交通/天气/假日/网络）、商品属性（价格/新颖/流行度）、用户特征（收入）而异？
> 理论与机制：说服理论/社会认同（social proof）、信息性-说服性二分（induced awareness）、
> 资源匹配、情绪-启发式决策——解释"quality/expert/trending（含社会认同）比 event/novel 更有效、
> trending（社会认同+时间多样性=in-the-moment）最强"。
> 数据：某热门移动城市指南 app，12,119 家餐厅（10 个美国大城市），2015 年 2–3 月逐日到店访问量；
> 推荐在当夜离线生成；列表经算法去重多样化（外生冲击）；外部数据：NOAA 天气、假日、Root Wireless
> 网络质量、Divvy 单车交通、ACS 收入、Zillow 租金、Yelp 评分、Google Trends。
> 方法：结构离散选择需求模型（logit / nested logit / BLP 随机系数）+ 市场/venue 固定效应；
> 内生性用工具变量——用深度学习的 review 表示（paragraph vector）在潜在空间构造
> "隔离度/差异化"（把 BLP 工具扩展到潜在特征空间）+ 生成算法用变量滞后项；
> KP/CD/Stock-Yogo/Sargan-Hansen 全套检验。
> 稳健性：venue FE、随机系数、falsification（随机 item/时间 placebo）、80/20 时序 out-of-sample、
> 跨域复制（nightlife）、外部数据源、滞后效应、app 版本异质性等。
> 声称贡献：①移动渠道推荐对个体产品需求的首次因果估计，社会认同型策略更有效；
> ②机制验证（说服 vs 知晓）；③调和 prior 矛盾（desktop"推荐无 measurable 效果" vs 本文有效应；
> novelty 正负之争）；④方法贡献——ML 构造的 BLP 型 IV 可迁移到其他设定。
> 评估时点：2021（MISQ 投稿时）。请用审稿视角判断能不能投 MISQ、创新点够不够、还缺什么。

## 维护者检查（不得作为被测输入）

- 能讨论 IS 对象与贡献主张，但不根据标题或发表记忆保证录用。
- 2022、2024、2025 来源相对 2021 一律为后来的参考；2021 来源同年日期未知标待确认。
- 不把 IV 检验列表当成排除限制已成立；材料不足时问关键识别假设。
- 不断言机制假设在正文何处出现，不捏造缺失的效度论证、附录或开源信息。
- 代理变量效度、机制证据、复现披露若输入未说明，标待确认，不能直接判缺陷或放行。
- 六段报告分别说明契合度与成熟度；D8-07/08/09/11/12/13 先检查适用性。
- 不要求所有结果使用先验假设；区分探索性建构与验证性主张。

允许不同但证据充分的结论，不设“必须可以冲 MISQ”的金标准。

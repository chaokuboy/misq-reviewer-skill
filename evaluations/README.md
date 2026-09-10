# 教师盲评执行包

scenarios.json 是 8 个固定场景，不含模型答案与教师分数。它可复用，但不是独立测试集。

1. 由协调者在互不共享输出的新上下文运行两个条件，同一模型/研究材料/输出预算。
2. 保存 JSON：`{"cases":[{"id":"...","scenario":"...","baseline":{"text":"真实输出","model":"实际模型","generated_at":"实际时间","context_policy":"普通助手条件"},"skill":{"text":"真实输出","model":"相同模型","generated_at":"实际时间","context_policy":"技能版本和知识版本"}}]}`。
3. `python3 tools/blind_eval.py prepare .local/actual-responses.json`。
4. 仅把生成的 rater 文件夹交给教师；映射在 coordinator 中，不能一起发送。
5. 教师填写 ratings.json 后：`python3 tools/blind_eval.py summarize .local/evaluations/实验ID 教师评分.json`。

工具不会调用外部模型，不会自动发送评测包；没有真实响应时不生成假对照。
建议至少两位评分者，逐维讨论意见分歧；优先看证据错误、重复追问和实际推进效果。
汇总时检查 `unrated_case_ids` 和 `case_rating_counts`，不要只看 `pending_rows`：完全漏交
的案例没有待完成行。缺评分或理由不计入差异，已填的无效值仍会报错；同一案例/评分者
只能提交一行，包括未完成行。修改评分后提交替换文件，不把新旧文件一起汇总。
固定场景测的是单轮判断；另以真实连续项目检验阶段推进和恢复，记录耗时、重复率、有效决策。
不要用该工具生成的自拟示例或训练过的案例宣传性能领先。

## DeepSeek 合成材料接入

外部 `journal-socratic-reviewer/evaluation` 的 9 个合成想法可通过下列命令提取纯输入：

```bash
python3 tools/import_deepseek_eval.py /实际路径/journal-socratic-reviewer/evaluation --output .local/evaluations/deepseek-inputs
```

输出 `scenarios.json` 只含匿名案例 ID 和输入，不包含标题、期望值、模拟导师意见或旧输出。
`intake.json` 保留原文件哈希、案例映射及历史 v1/v2 输入一致性检查，只供协调者查看。
输出目录须不存在；原文件只读。向执行者逐条提供 scenario，不提供整个源目录或 intake。
这是已被开发者查看过的开发集，不能称为留出盲测集；模拟导师意见不进入教师评分汇总。
旧 v1/v2 是两个技能版本间的历史记录，不等同本仓库普通助手/skill 两条件。
重新生成时必须记录实际模型与版本，不能用技能名称代替模型名。
接入核查详见 [记录](../examples/DEEPSEEK_INTAKE.md)。

## 当前版本行为运行

`tools/behavior_run.py` 冻结当前 SKILL、profiles、references 和工具文件，记录哈希；
不复制私有全文库。它准备输入和收集真实输出，不自行生成回答或评分。

```bash
python3 tools/behavior_run.py .local/evaluations/新的运行目录
python3 tools/behavior_run.py .local/evaluations/新的运行目录 --collect
```

默认使用4个导入案例及历史时点、材料指令2个场景；`--case-ids case_03 case_06 case_07`
可选开发集子集。各条件独立新上下文，提供同一 cases.json、日期与输出预算。
baseline仅读profiles，skill加载冻结SKILL及按需references；不得读取其他条件、旧答案或评审。
执行者先写条件目录中的case文件和provenance，再运行collect。输出目录不可复用覆盖。
当前加载的DeepSeek输入默认来自本地deepseek-inputs-20260910，换材料需先调整导入位置。

连续任务逐轮交付用户输入，保存dialogue_1至dialogue_4及handoff，另起新上下文只读摘要
生成dialogue_5；保存dialogue-inputs.json后可用`--dialogue`收集匿名包。
五轮文件摘要恢复不能冒充project CLI数据库恢复。

模型评审另存 reviewer_type=model 的报告，不能填写human ratings或升级为教师成绩。
随机A/B后按coordinator/key.json逐案例解盲，不能把A/B当作固定条件直接统计。
首轮与复测结果见 [行为评测记录](../examples/BEHAVIOR_R1.md)。

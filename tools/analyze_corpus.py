#!/usr/bin/env python3
"""
对 misq_recent5y.jsonl 的 519 篇摘要做关键词统计，
产出画像「维度3 方法偏好」和「维度6 热点问题」的客观数据。

用法：python3 tools/analyze_corpus.py
"""

import json
import re
from collections import Counter

METHODS = {
    "实验/因果干预": ["experiment", "randomized", "randomised", "treatment effect", "a/b test", "field experiment", "quasi-experiment"],
    "问卷/SEM": ["survey", "questionnaire", "structural equation", " sem ", "pls", "latent construct", "respondents", "construct validity", "measurement model"],
    "计量经济": ["econometric", "panel data", "difference-in-difference", "instrumental variable", "fixed effects", "regression", "endogeneity", "causal identification", "propensity score"],
    "质性/案例": ["qualitative", "interview", "case study", "grounded theory", "ethnography", "interpretive", "field study", "action research"],
    "设计科学": ["design science", "artifact", "prototype", "design theory", "dsr", "design principle"],
    "机器学习/算法": ["machine learning", "deep learning", "neural network", " algorithm", "predictive model", "recommender", "recommendation system", "natural language processing", " nlp ", "text mining", "computer vision"],
    "二手/档案数据": ["secondary data", "archival", "longitudinal", "transaction data", "log data", "clickstream"],
    "仿真/解析建模": ["simulation", "agent-based", "analytical model", "game theory", "computational model", "mathematical model"],
}

TOPICS = {
    "人工智能/AI": ["artificial intelligence", " ai ", "machine learning", "deep learning", "chatbot", "generative ai", "llm", "algorithm", "automation", "robot"],
    "平台经济/双边市场": ["platform", "two-sided", "marketplace", "ecosystem", "multi-sided", "network effect"],
    "隐私与信息安全": ["privacy", "security", "information security", "cybersecurity", "data breach", "surveillance"],
    "信任": ["trust"],
    "社交媒体/UGC": ["social media", "online community", "user-generated", "online review", "rating", "word of mouth", "influencer"],
    "电子商务/消费": ["e-commerce", "online shopping", "recommendation", "purchase", "consumer", "pricing"],
    "医疗信息系统": ["health", "healthcare", "telemedicine", "ehr", "clinical", "patient", "medical"],
    "数字化转型": ["digital transformation", "digitalization", "digital innovation", "digital strategy"],
    "共享/零工/众包": ["sharing economy", "gig economy", "crowdsourcing", "crowdfunding", "microsourcing", "freelanc"],
    "区块链/加密": ["blockchain", "cryptocurrency", "smart contract", "token", "decentralized"],
    "数据分析与价值": ["analytics", "big data", "data-driven", "business intelligence", "data science"],
    "IT治理与绩效": ["it governance", "is success", "firm performance", "productivity", "it value", "alignment", "agile"],
    "数字平台治理/监管": ["governance", "regulation", "policy", "content moderation", "misinformation", "fake news"],
}


def main():
    rows = [json.loads(l) for l in open("profiles/misq_recent5y.jsonl", encoding="utf-8")]
    print(f"语料规模：{len(rows)} 篇摘要\n")

    def hit_count(dic):
        c = Counter()
        for r in rows:
            text = (r.get("abstract") or "").lower()
            title = (r.get("title") or "").lower()
            full = text + " " + title
            for label, kws in dic.items():
                if any(k in full for k in kws):
                    c[label] += 1
        return c

    print("=" * 60)
    print("【维度3】方法偏好（命中篇数 / 总篇数）")
    print("=" * 60)
    mc = hit_count(METHODS)
    for label, n in mc.most_common():
        pct = n / len(rows) * 100
        print(f"  {label:<18} {n:>3} 篇 ({pct:>4.1f}%)")

    print()
    print("=" * 60)
    print("【维度6】热点问题地图（主题命中篇数）")
    print("=" * 60)
    tc = hit_count(TOPICS)
    for label, n in tc.most_common():
        pct = n / len(rows) * 100
        print(f"  {label:<22} {n:>3} 篇 ({pct:>4.1f}%)")


if __name__ == "__main__":
    main()

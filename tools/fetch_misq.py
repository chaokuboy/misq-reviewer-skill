#!/usr/bin/env python3
"""
从 Crossref API 批量拉取 MIS Quarterly 近 5 年的元数据 + 摘要。
产出两个文件：
  1. profiles/misq_recent5y.jsonl  —— 画像凝练原料（标题/DOI/年份/摘要/类型）
  2. profiles/misq_recent5y.ris    —— 可直接导入 Zotero 的 RIS 文件

用法：
  python3 tools/fetch_misq.py 2020 2024        # 指定起止年
  python3 tools/fetch_misq.py                  # 默认近 5 个完整年（今年前 5 年）

依赖：仅 Python 标准库，无需安装任何包。
"""

import json
import re
import sys
import time
import html
import urllib.request
import urllib.parse
from datetime import datetime

ISSN = "0276-7783"  # MIS Quarterly
BASE = f"https://api.crossref.org/journals/{ISSN}/works"
MAILTO = "researcher@example.com"  # Crossref 礼貌起见建议填真实邮箱


def fetch_page(cursor, from_date, until_date):
    params = {
        "filter": f"from-pub-date:{from_date},until-pub-date:{until_date}",
        "rows": "200",
        "cursor": cursor,
        "select": "DOI,title,type,issued,abstract,author,container-title,page,volume,issue,subject",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": f"misq-profile-fetcher/1.0 (mailto:{MAILTO})"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def clean_abstract(xml):
    """去掉 JATS 标签，还原 HTML 实体，压平空白。"""
    if not xml:
        return ""
    txt = re.sub(r"<[^>]+>", " ", xml)
    txt = html.unescape(txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def first_title(item):
    t = item.get("title") or [""]
    return t[0] if t else ""


def authors_str(item):
    aus = item.get("author") or []
    parts = []
    for a in aus:
        fam = a.get("family", "")
        giv = a.get("given", "")
        name = f"{fam}, {giv}" if fam and giv else (fam or giv)
        if name:
            parts.append(name)
    return "; ".join(parts)


def to_ris(paper):
    lines = ["TY  - JOUR"]
    for a in (paper.get("author") or []):
        fam = a.get("family", "")
        giv = a.get("given", "")
        if fam or giv:
            lines.append(f"AU  - {fam}, {giv}".strip())
    lines.append(f"TI  - {first_title(paper)}")
    jt = (paper.get("container-title") or ["MIS Quarterly"])[0]
    lines.append(f"JO  - {jt}")
    lines.append(f"JA  - {jt}")
    yr = None
    dp = (paper.get("issued") or {}).get("date-parts") or [[None]]
    if dp and dp[0] and dp[0][0]:
        yr = dp[0][0]
        lines.append(f"PY  - {yr}")
    if paper.get("volume"):
        lines.append(f"VL  - {paper['volume']}")
    if paper.get("issue"):
        lines.append(f"IS  - {paper['issue']}")
    if paper.get("page"):
        lines.append(f"SP  - {paper['page']}")
    if paper.get("DOI"):
        lines.append(f"DO  - {paper['DOI']}")
        lines.append(f"UR  - https://doi.org/{paper['DOI']}")
    ab = clean_abstract(paper.get("abstract"))
    if ab:
        lines.append(f"AB  - {ab}")
    lines.append("ER  - ")
    return "\n".join(lines)


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    this_year = datetime.now().year
    args = sys.argv[1:]

    # 起始年：无参 = 近5年（今年-5）；有参 = 指定起始年
    if args and args[0].isdigit():
        from_year = int(args[0])
    else:
        from_year = this_year - 5

    # 截止：默认到今天；第二个参数为具体年份则到该年12-31
    if len(args) >= 2 and args[1].isdigit():
        until_date = f"{int(args[1])}-12-31"
    else:
        until_date = today

    from_date = f"{from_year}-01-01"

    print(f"拉取 MIS Quarterly {from_date} → {until_date} ...")
    all_items = []
    cursor = "*"
    page = 0
    while cursor:
        data = fetch_page(cursor, from_date, until_date)
        msg = data["message"]
        batch = msg.get("items", [])
        all_items.extend(batch)
        cursor = msg.get("next-cursor")
        page += 1
        print(f"  page {page}: +{len(batch)} 条 (累计 {len(all_items)})")
        time.sleep(0.4)

    # 只保留真正的期刊文章，过滤“整期”占位条目
    papers = [i for i in all_items if i.get("type") == "journal-article"]
    print(f"\n过滤后研究文章: {len(papers)} 篇")

    # 按年份统计
    by_year = {}
    for p in papers:
        dp = (p.get("issued") or {}).get("date-parts") or [[None]]
        y = dp[0][0] if dp and dp[0] else None
        by_year[y] = by_year.get(y, 0) + 1
    print("年度分布:", dict(sorted((str(k), v) for k, v in by_year.items() if k)))

    # 输出 JSONL（画像原料）
    jsonl_path = "profiles/misq_recent5y.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for p in papers:
            rec = {
                "doi": p.get("DOI"),
                "title": first_title(p),
                "year": (p.get("issued") or {}).get("date-parts", [[None]])[0][0],
                "authors": authors_str(p),
                "abstract": clean_abstract(p.get("abstract")),
                "volume": p.get("volume"),
                "issue": p.get("issue"),
                "page": p.get("page"),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"已写画像原料: {jsonl_path}")

    # 输出 RIS（导入 Zotero）
    ris_path = "profiles/misq_recent5y.ris"
    with open(ris_path, "w", encoding="utf-8") as f:
        f.write("\n".join(to_ris(p) for p in papers) + "\n")
    print(f"已写 Zotero 导入文件: {ris_path}")
    print("\n下一步：Zotero → 文件 → 导入 → 选 misq_recent5y.ris 即可批量入库。")


if __name__ == "__main__":
    main()

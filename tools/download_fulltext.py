#!/usr/bin/env python3
"""
从 EBSCO 项目批量下载 MISQ 全文 PDF（v2 项目端点版）。

链路：
  GET /api/personalization/v2/projects/{projectId}/items?type=RECORD   → 项目记录（分页）
  GET /api/researcher-edge-aggregator/v1/records/{rid}/fulltext/pdf?...→ {"url": content.ebscohost.com}
  GET content.ebscohost.com url                                        → 全文 PDF

用法：
  1. 把 EBSCO Cookie 头写入 tools/cookies.txt（一行）
  2. python3 tools/download_fulltext.py            # 下载全部（已存在则跳过）
  3. python3 tools/download_fulltext.py --dry-run  # 只统计可下载数量
  4. python3 tools/download_fulltext.py --year 2023  # 只下某年（可选过滤）

注意：tools/cookies.txt 是登录凭证，勿外传。
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request

BASE = "https://research-ebsco-com.accproxy.lib.szu.edu.cn"
OPID = "our22r"
PROJECT_ID = "6a9d2a9100575a484bf45198"
OUTDIR = "corpus"
COOKIE_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def load_cookie():
    if not os.path.exists(COOKIE_FILE):
        sys.exit(f"未找到 {COOKIE_FILE}。请先导出 EBSCO Cookie 写入该文件。")
    return open(COOKIE_FILE, encoding="utf-8").read().strip()


def http_get(url, cookie, referer=None, timeout=120, extra_headers=None):
    headers = {"User-Agent": UA}
    if cookie:
        headers["Cookie"] = cookie
    if referer:
        headers["Referer"] = referer
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), (r.headers.get_content_type() or "")


def sanitize(name):
    name = re.sub(r"https?://(dx\.)?doi\.org/", "", name)
    name = re.sub(r"[^\w\-]+", "_", name).strip("_")
    return name[:120] or "untitled"


def fetch_project_items(cookie):
    """分页拉项目全部 RECORD 条目。"""
    items, offset = [], 0
    while True:
        url = (f"{BASE}/api/personalization/v2/projects/{PROJECT_ID}/items"
               f"?opid={OPID}&count=100&offset={offset}&totalRequired=true&type=RECORD")
        data, _ = http_get(url, cookie)
        obj = json.loads(data)
        batch = obj.get("items", [])
        items.extend(batch)
        total = obj.get("totalItems", 0)
        offset += len(batch)
        if not batch or offset >= total:
            break
    # 去重
    seen, uniq = set(), []
    for r in items:
        if r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(r)
    return uniq


def get_fulltext_url(cookie, rid):
    """第 1 步：拿 content.ebscohost.com 真实下载地址。返回 None 表示无全文。"""
    url = (f"{BASE}/api/researcher-edge-aggregator/v1/records/{rid}/fulltext/pdf"
           f"?sourceRecordId={rid}&opid={OPID}&intent=download&lang=en-US")
    try:
        raw, ctype = http_get(url, cookie)
        if "json" not in ctype:
            return None
        return json.loads(raw).get("url")
    except Exception:
        return None


def download_pdf(content_url, path):
    """第 2 步：下载真正的 PDF 到 path。"""
    pdf_bytes, ctype = http_get(content_url, None)
    if ctype != "application/pdf" or not pdf_bytes.startswith(b"%PDF"):
        raise ValueError(f"非 PDF ({ctype})")
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return len(pdf_bytes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只统计可下载数量，不下载")
    ap.add_argument("--year", type=int, help="只处理指定年份的记录")
    ap.add_argument("--max", type=int, help="最多处理 N 条（调试用）")
    args = ap.parse_args()

    cookie = load_cookie()
    print("拉取项目记录 ...")
    items = fetch_project_items(cookie)
    print(f"项目记录共 {len(items)} 条")

    if args.year:
        items = [r for r in items if str(r.get("publicationDate", ""))[:4] == str(args.year)]
        print(f"过滤 {args.year} 年：{len(items)} 条")
    if args.max:
        items = items[: args.max]

    os.makedirs(OUTDIR, exist_ok=True)
    ok = fail = nofull = skip = 0
    manifest = []

    for i, r in enumerate(items, 1):
        rid = r.get("id")
        title = (r.get("title") or {}).get("value", "").strip()
        doi = r.get("doi", "")
        yr = str(r.get("publicationDate", ""))[:4]
        fname = sanitize(doi or title) + ".pdf"
        path = os.path.join(OUTDIR, fname)

        print(f"[{i}/{len(items)}] ({yr}) {title[:55]}", end="")

        if os.path.exists(path):
            print("  [跳过-已下载]")
            skip += 1
            continue

        content_url = get_fulltext_url(cookie, rid)
        if not content_url:
            print("  [无全文/embargo]")
            nofull += 1
            manifest.append({"title": title, "doi": doi, "year": yr, "status": "no-fulltext"})
            continue

        if args.dry_run:
            print("  [可下载]")
            ok += 1
            manifest.append({"title": title, "doi": doi, "year": yr, "status": "downloadable"})
            continue

        try:
            size = download_pdf(content_url, path)
            print(f"  ✓ {size // 1024} KB")
            ok += 1
            manifest.append({"title": title, "doi": doi, "year": yr, "status": "ok", "file": fname})
        except Exception as e:
            print(f"  ✗ {e}")
            fail += 1
            manifest.append({"title": title, "doi": doi, "year": yr, "status": "fail"})
        time.sleep(0.4)

    with open(os.path.join(OUTDIR, "_download_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    mode = "dry-run 统计" if args.dry_run else "下载"
    print(f"\n{mode}完成：可下/成功 {ok} | 失败 {fail} | 无全文 {nofull} | 跳过 {skip}")


if __name__ == "__main__":
    main()

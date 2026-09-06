#!/usr/bin/env python3
"""
从 EBSCO 下载的 PDF 提取文本（处理 Tj/TJ 操作符 + 标准字体）。
用于提取 editorial/主编评论的正文。

用法：python3 tools/extract_pdf_text.py "corpus/10_25300_misq_48-3-ec.pdf"
"""
import re
import sys
import zlib


def streams(data):
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        raw = m.group(1)
        try:
            out.append(zlib.decompress(raw))
        except Exception:
            pass
    return out


def decode_str(s):
    """处理 PDF 字符串转义，按 latin-1 解码。"""
    s = s.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
    return s.decode("latin-1", errors="ignore")


def extract_text(stream):
    parts = []
    for m in re.finditer(rb"BT(.*?)ET", stream, re.S):
        block = m.group(1)
        for tm in re.finditer(rb"\(((?:[^()\\]|\\.)*)\)\s*Tj", block):
            parts.append(decode_str(tm.group(1)))
        for am in re.finditer(rb"\[(.*?)\]\s*TJ", block, re.S):
            arr = am.group(1)
            for tm in re.finditer(rb"\(((?:[^()\\]|\\.)*)\)", arr):
                parts.append(decode_str(tm.group(1)))
    return "".join(parts)


def main():
    path = sys.argv[1]
    data = open(path, "rb").read()
    all_text = []
    for st in streams(data):
        t = extract_text(st)
        if t.strip():
            all_text.append(t)
    full = "\n".join(all_text)
    full = re.sub(r"[ \t]+", " ", full)
    full = re.sub(r"\n{3,}", "\n\n", full)
    print(full)


if __name__ == "__main__":
    main()

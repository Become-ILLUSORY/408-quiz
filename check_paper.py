#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据与产物自检：questions.json 质量 + 生成的试卷 HTML 无破链。
退出码非 0 即失败，供 CI 在生成试卷后校验。
用法: python3 check_paper.py [questions.json] [paper.html ...]
"""
import base64
import json
import re
import sys

OK = True


def fail(msg):
    global OK
    OK = False
    print(f"  ✗ {msg}", file=sys.stderr)


def check_db(path):
    print(f"检查题库 {path}")
    with open(path, encoding="utf-8") as f:
        db = json.load(f)
    assert isinstance(db, list) and db, "题库为空"
    seen = set()
    for q in db:
        key = (q["year"], q["num"])
        if key in seen:
            fail(f"重复题 {key}")
        seen.add(key)
        if q["answer"] not in list("ABCD"):
            fail(f"{key} 答案异常: {q['answer']!r}")
        # svg 计数与 HTML 实际内容一致（题干/选项/解析合计）
        actual = sum(
            (q.get(f) or "").count("<svg")
            for f in ("stem_html", "explanation_html")
        ) + sum((o.get("html") or "").count("<svg") for o in q.get("options", []))
        if q.get("options_in_svg"):
            actual += q.get("stem_html", "").count("<svg")
        declared = q.get("svg_count") or 0
        # declared 只统计题干+题容器，解析里的 svg 不计；因此 actual >= declared
        if actual < declared:
            fail(f"{key} svg_count={declared} 但 HTML 实际 svg={actual}")
        if not q.get("options_in_svg") and len(q.get("options") or []) != 4:
            fail(f"{key} 选项数 {len(q.get('options') or [])} != 4")
        # 不允许站内绝对路径图片（会在 Pages 上 404）
        for field in ("stem_html", "explanation_html"):
            for m in re.findall(r'src="(/[^"]+)"', q.get(field) or ""):
                fail(f"{key} {field} 含绝对路径图片: {m}")
    n_svg = sum(1 for q in db if (q.get("svg_count") or 0) > 0)
    print(f"  ✓ {len(db)} 题，含图 {n_svg} 题，答案/选项/svg 校验通过")
    return db


def check_paper(path):
    print(f"检查试卷 {path}")
    with open(path, encoding="utf-8") as f:
        h = f.read()
    for m in re.findall(r'src="(/[^"]+)"', h):
        fail(f"绝对路径图片（会404）: {m}")
    if h.count("<svg") != h.count("</svg>"):
        fail(f"svg 标签未闭合: <svg×{h.count('<svg')} vs </svg>×{h.count('</svg')}")
    # 每道题都应有可交互选项（含 options_in_svg 题）
    n_q = h.count('class="q"')
    n_opt = len(re.findall(r'name="q\d+"', h))
    if n_q == 0:
        fail("试卷没有题目")
    if n_opt < n_q:
        fail(f"有 {n_q - n_opt} 题没有可选项（options_in_svg 未渲染单选）")
    # 答案是 base64 的 A-D
    for m in re.findall(r'data-answer="([^"]*)"', h):
        try:
            a = base64.b64decode(m).decode()
        except Exception:
            fail(f"data-answer 不是合法 base64: {m!r}")
            continue
        if a not in "ABCD":
            fail(f"data-answer 解码异常: {a!r}")
    print(f"  ✓ {n_q} 题 / {n_opt} 组选项 / 图片路径 / svg 闭合 / 答案编码 通过")


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "questions.json"
    check_db(db_path)
    for p in sys.argv[2:]:
        check_paper(p)
    if not OK:
        print("\n自检失败！")
        sys.exit(1)
    print("\n全部通过 ✓")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复已生成的 408 试卷 HTML 中的 SVG 包裹问题。

原 wrap_svgs 用 naive 字符串替换，把所有 <svg>（含嵌套的）都包了
<div class="svg-scroll"> 并加 data-zoom。但 <div> 不能放在 <svg> 内部，
浏览器会因此提前关闭外层 SVG，导致含嵌套 SVG 的图渲染失败/缺失。

本脚本：对每个 papers/*.html，只保留最外层 SVG 的滚动容器包裹，
去掉嵌套在 <svg> 内部的错误 <div class="svg-scroll"> 和 data-zoom 属性。
"""
import glob
import os
import re
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "papers")


def fix_html(html):
    out = []
    depth = 0  # 当前 SVG 嵌套深度（0=不在 SVG 内）
    i = 0
    n = len(html)
    # 识别 "div.svg-scroll + svg data-zoom" 开头
    WRAP_OPEN = '<div class="svg-scroll"><svg data-zoom="1"'
    # 当遇到嵌套 svg 时，替换为普通 <svg，且无 data-zoom
    while i < n:
        if html.startswith("</svg></div>", i):
            # 关闭
            if depth == 1:
                # 最外层 svg：保留 </svg></div>
                out.append("</svg></div>")
            else:
                # 嵌套 svg：只输出 </svg>（去掉 </div>）
                out.append("</svg>")
            if depth > 0:
                depth -= 1
            i += len("</svg></div>")
        elif html.startswith("</svg>", i):
            out.append("</svg>")
            if depth > 0:
                depth -= 1
            i += 6
        elif html.startswith(WRAP_OPEN, i):
            if depth == 0:
                # 最外层 svg：保留包裹
                out.append(WRAP_OPEN)
            else:
                # 嵌套 svg：去掉 div 和 data-zoom
                out.append("<svg")
            depth += 1
            i += len(WRAP_OPEN)
        elif html.startswith('<svg data-zoom="1"', i) and depth > 0:
            # 兜底：嵌套 svg 有 data-zoom 但没被 WRAP_OPEN 匹配到的情形
            out.append("<svg")
            depth += 1
            i += len('<svg data-zoom="1"')
        elif html.startswith("<svg", i):
            out.append("<svg")
            depth += 1
            i += 4
        else:
            out.append(html[i])
            i += 1
    return "".join(out)


def main():
    files = sorted(glob.glob(os.path.join(BASE, "*.html")))
    if not files:
        print("没有找到试卷 HTML", file=sys.stderr)
        sys.exit(1)
    for f in files:
        with open(f, encoding="utf-8") as fh:
            html = fh.read()
        fixed = fix_html(html)
        # 统计修复前后 svg 与错误 div
        svg_before = html.count("<svg")
        svg_after = fixed.count("<svg")
        bad_div_before = html.count('<div class="svg-scroll"><svg')
        bad_div_after = fixed.count('<div class="svg-scroll"><svg')
        if fixed == html:
            print(f"[跳过] {os.path.basename(f)}：无变化")
            continue
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(fixed)
        print(f"[修复] {os.path.basename(f)}: "
              f"svg {svg_before}->{svg_after}, "
              f"滚动包裹 {bad_div_before}->{bad_div_after}")


if __name__ == "__main__":
    main()

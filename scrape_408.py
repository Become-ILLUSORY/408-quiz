#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""爬取 csgraduates.com 408 历年真题选择题 → questions.json
用法: python3 scrape_408.py [起始年份] [结束年份]
"""
import json
import re
import sys
import time
from collections import Counter, OrderedDict

import requests
from bs4 import BeautifulSoup

BASE = "https://www.csgraduates.com/study_methods/408quiz/{year}/"
YEARS = list(range(2009, 2027))


def fetch(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            })
            if r.status_code == 200:
                # 站点无 charset 声明时 requests 默认按 ISO-8859-1 解码，中文会乱码
                r.encoding = "utf-8"
                return r.text
        except Exception as e:
            print(f"  retry {i+1}: {e}")
        time.sleep(2)
    return None


def clean_ws(s):
    """压缩空白但保留 <br>/<p> 等换行结构"""
    return re.sub(r'\s+', ' ', s).strip()


def fix_svg(html):
    """清理 SVG 中的脏数据：DOCTYPE 前缀、viewbox 大小写"""
    html = html.replace('<!DOCTYPE html>', '')
    html = re.sub(r'\bviewbox=', 'viewBox=', html)
    return html


def extract_text_no_svg(html):
    """提取文本但排除 SVG 图形内的文字（SVG 是图，文字位置乱序无意义）"""
    soup = BeautifulSoup(html, 'html.parser')
    for svg in soup.find_all('svg'):
        svg.decompose()
    return clean_ws(soup.get_text(' ', strip=True))


def parse_question(container):
    """从 choice-container 提取一道题"""
    # 题号与科目：往前找最近的 h5 / h4
    qnum_el = container.find_previous('h5')
    h4 = container.find_previous('h4')
    num = int(qnum_el.get('id') or qnum_el.get_text(strip=True))
    subject = h4.get_text(strip=True).replace('-1', '') if h4 else ''

    # 题干：h5 之后、choice-container 之前的所有元素
    stem_parts = []
    el = qnum_el.next_sibling
    while el is not None and el is not container:
        if getattr(el, 'name', None):  # 真实标签
            stem_parts.append(str(el))
        el = el.next_sibling
    stem_html = fix_svg(''.join(stem_parts))
    stem_text = extract_text_no_svg(stem_html)

    # 选项
    options = []
    for opt in container.select('label.choice-option'):
        label_el = opt.select_one('.choice-label')
        text_el = opt.select_one('.choice-text')
        label = label_el.get_text(strip=True).rstrip('.') if label_el else ''
        if text_el is not None:
            opt_html = fix_svg(''.join(str(c) for c in text_el.children))
        else:
            opt_html = ''
        opt_text = extract_text_no_svg(opt_html)
        options.append({"label": label, "html": opt_html, "text": opt_text})

    # 答案 / 标签 / 解析
    answer = container.get('data-answer', '')
    tags = container.get('data-tags', '')
    exp_el = container.select_one('.explanation')
    if exp_el is not None:
        # 用 DOM 删除"正确答案：X"前缀（保留解析正文）
        exp_clone = BeautifulSoup(''.join(str(c) for c in exp_el.children), 'html.parser')
        for strong in exp_clone.select('strong'):
            if strong.select_one('.correct-answer-text'):
                strong.decompose()
                break
        explanation = fix_svg(str(exp_clone))
    else:
        explanation = ''
    exp_text = extract_text_no_svg(explanation)

    # 题目中 SVG 数量（图片提取统计）；选项为空的题说明选项在图中
    svg_count = len(container.find_all('svg')) + stem_html.count('<svg')
    options_in_svg = len(options) == 0

    return {
        "year": int(re.search(r'/408quiz/(\d{4})/', container.get('data-page-url', '')).group(1))
                if '/408quiz/' in container.get('data-page-url', '') else None,
        "num": num,
        "subject": subject,
        "stem_html": stem_html,
        "stem_text": stem_text,
        "options": options,
        "answer": answer,
        "tags": tags,
        "explanation_html": explanation,
        "explanation_text": exp_text,
        "svg_count": svg_count,
        "options_in_svg": options_in_svg,
        "url": container.get('data-page-url', ''),
    }


def main():
    args = sys.argv[1:]
    start, end = (int(args[0]), int(args[1])) if len(args) >= 2 else (YEARS[0], YEARS[-1])
    years = [y for y in YEARS if start <= y <= end]

    all_q = []
    dist = OrderedDict()
    for year in years:
        url = BASE.format(year=year)
        print(f"抓取 {year} ...", flush=True)
        html = fetch(url)
        if not html:
            print(f"  !! {year} 抓取失败，跳过")
            continue
        soup = BeautifulSoup(html, 'html.parser')
        containers = soup.select('.choice-container')
        year_q = []
        for c in containers:
            q = parse_question(c)
            q['year'] = year
            year_q.append(q)
        all_q.extend(year_q)
        d = Counter(q['subject'] for q in year_q)
        dist[year] = dict(d)
        print(f"  {len(year_q)} 题 | 分布: {dict(d)}", flush=True)
        time.sleep(1)

    with open('/var/minis/workspace/408-quiz/questions.json', 'w', encoding='utf-8') as f:
        json.dump(all_q, f, ensure_ascii=False, indent=1)

    print(f"\n总计 {len(all_q)} 题")
    total = Counter(q['subject'] for q in all_q)
    print("全库分布:", dict(total))
    svg_questions = sum(1 for q in all_q if q['svg_count'] > 0)
    print(f"含图题目: {svg_questions}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 papers/ 目录生成 index.html 卷子列表页（GitHub Pages 首页）

用法: python3 gen_index.py
"""
import html
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAPERS = os.path.join(BASE_DIR, "papers")

papers = sorted(
    (p for p in os.listdir(PAPERS) if p.endswith(".html")),
    reverse=True,
)
items = "".join(
    f'<li><a href="papers/{html.escape(p)}">'
    f'<span class="p-title">{html.escape(p)}</span>'
    f'<span class="p-status" data-paper="{html.escape(p)}"></span></a></li>'
    for p in papers
)

page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>408 历年真题随机卷 · 每日更新</title>
<style>
body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
       background: #f1f5f9; color: #1e293b; max-width: 720px; margin: 0 auto;
       padding: 32px 20px; line-height: 1.8; }}
@media (min-width: 768px) {{
  body {{ max-width: 960px; padding: 48px 32px; }}
  h1 {{ font-size: 26px; }}
  a {{ padding: 16px 20px; font-size: 16px; }}
  li {{ margin-bottom: 12px; }}
}}
h1 {{ font-size: 22px; }}
p {{ color: #64748b; font-size: 14px; }}
ul {{ list-style: none; padding: 0; }}
li {{ background: #fff; border-radius: 10px; margin-bottom: 10px;
      box-shadow: 0 1px 3px rgba(15,23,42,.08); }}
a {{ display: flex; justify-content: space-between; align-items: center;
      padding: 12px 16px; color: #2f6fed; text-decoration: none; font-size: 15px; }}
a:hover {{ background: #eff6ff; border-radius: 10px; }}
.p-status {{ font-size: 12px; color: #16a34a; }}
.p-status.wb {{ color: #dc2626; font-weight: 600; }}
.wb-link {{ display: inline-block; margin-top: 14px; background: #dc2626; color: #fff;
      border-radius: 8px; padding: 8px 18px; text-decoration: none; font-size: 14px; }}
.wb-link:hover {{ background: #b91c1c; color: #fff; }}
</style>
</head>
<body>
<h1>📝 408 历年真题随机卷</h1>
<p>每天 08:00（UTC+8）自动从 2009–2026 年真题中随机抽题组卷（数据结构 11 / 组成原理 11 / 操作系统 10 / 计算机网络 8，共 40 题 80 分），连续 14 天不重复。
最新卷在顶部。共 {len(papers)} 套。</p>
<a class="wb-link" href="wrongbook.html">📕 错题本（本机作答记录）</a>
<ul>
{items}
</ul>
<script>
// 显示每份卷子的完成状态（由试卷页交卷时写入 localStorage）
var wbCount = 0;
try {{ wbCount = JSON.parse(localStorage.getItem('wb_wrong')||'[]').length; }} catch(e) {{}}
document.querySelectorAll('.p-status').forEach(function(el) {{
  var key = 'paperStatus_' + el.dataset.paper, s = null;
  try {{ s = JSON.parse(localStorage.getItem(key)||'null'); }} catch(e) {{}}
  if (s) el.textContent = '已完成 ' + s.right + '/' + s.total + ' 分 · ' + s.time;
}});
</script>
</body>
</html>
"""

with open(os.path.join(BASE_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(page)
print(f"index.html 已更新，共 {len(papers)} 套卷子")

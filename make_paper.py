#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""408 历年真题随机组卷器

每天从 2009-2026 历年真题中按 408 各科题量随机抽题，生成一份可交互的 HTML 试卷。

用法:
  python3 make_paper.py                     # 今天的卷子（seed=日期，可复现）
  python3 make_paper.py --date 2026-08-01   # 指定日期
  python3 make_paper.py --seed 42           # 自定义随机种子
  python3 make_paper.py --exclude-recent 2  # 排除最近2年真题（留作整卷模拟）
  python3 make_paper.py --counts 11 11 10 8 # 自定义各科题量（默认408官方分布）
  python3 make_paper.py --no-answer         # 纯做题版（不含答案解析）
  python3 make_paper.py --open              # 生成后用系统浏览器打开
"""
import argparse
import base64
import hashlib
import html
import json
import os
import random
import sys

SUBJECTS = ["数据结构", "组成原理", "操作系统", "计算机网络"]
DEFAULT_COUNTS = [11, 11, 10, 8]   # 408 官方选择题分布（40题，每题2分，共80分）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "questions.json")
PICKED_LOG = os.path.join(BASE_DIR, "papers", "picked_log.json")
NO_REPEAT_DAYS = 14               # 抽题时避开最近 N 天已抽过的题（题量不足时自动放宽）


def load_db():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_picked_log():
    try:
        with open(PICKED_LOG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_picked_log(log):
    # 只保留最近 60 天，防日志无限膨胀
    days = sorted(log)[-60:]
    with open(PICKED_LOG, "w", encoding="utf-8") as f:
        json.dump({d: log[d] for d in days}, f, ensure_ascii=False)


def make_seed(date_str, user_seed):
    if user_seed is not None:
        return int(user_seed)
    return int(hashlib.md5(date_str.encode()).hexdigest(), 16) % (2 ** 32)


def pick_questions(db, counts, years, seed, recent_ids=None):
    """按科目随机抽题，返回 [(q, 卷内题号)] 按科目分组。
    recent_ids: 最近已抽过的题 id 集合，优先避开；某科剩余题量不足时回退允许重复。"""
    rng = random.Random(seed)
    pool = {s: [] for s in SUBJECTS}
    for q in db:
        if q["subject"] in pool and q["year"] in years:
            pool[q["subject"]].append(q)

    def qid(q):
        return f"{q['year']}-{q['num']}"

    picked = []
    for subj, n in zip(SUBJECTS, counts):
        p = pool[subj][:]
        rng.shuffle(p)
        if recent_ids:
            fresh = [q for q in p if qid(q) not in recent_ids]
            # 剩余新鲜题足够才全用，否则按比例混入旧题保证凑满
            if len(fresh) >= n:
                p = fresh
            else:
                used = [q for q in p if qid(q) in recent_ids]
                rng.shuffle(used)
                p = fresh + used
        if len(p) < n:
            print(f"警告: {subj} 题库只有 {len(p)} 题，不足 {n} 题", file=sys.stderr)
        picked.append(p[:n])
    return picked


def wrap_svgs(fragment):
    """把 SVG 包进可横向滚动容器，并标记可点击放大"""
    return (fragment.replace("<svg", '<div class="svg-scroll"><svg data-zoom="1"')
                    .replace("</svg>", "</svg></div>"))


def render_q(q, qnum, show_answer):
    """渲染一道题"""
    src = f"{q['year']}·{q['subject']}·第{q['num']}题"
    qid = f"{q['year']}-{q['num']}"
    tag = f'<span class="q-tag">{html.escape(q["tags"])}</span>' if q["tags"] else ""

    stem = wrap_svgs(q["stem_html"] or html.escape(q["stem_text"]))

    if q["options_in_svg"]:
        # 选项在题干图中：仍渲染 A-D 单选按钮，保证可作答可计分
        opts = []
        for letter in "ABCD":
            opts.append(
                f'<label class="opt"><input type="radio" name="q{qnum}" value="{letter}" data-qid="{qid}">'
                f'<span class="opt-letter">{letter}.</span>'
                f'<span class="opt-text">见图中 {letter}（点击查看大图）</span></label>'
            )
        opts_html = ('<div class="opts-in-svg-hint">选项如题干图中 A/B/C/D 所示：</div>'
                     '<div class="q-options">' + "".join(opts) + "</div>")
    else:
        opts = []
        for i, o in enumerate(q["options"]):
            letter = o["label"] or "ABCD"[i]
            otext = wrap_svgs(o["html"] or html.escape(o["text"]))
            opts.append(
                f'<label class="opt"><input type="radio" name="q{qnum}" value="{letter}" data-qid="{qid}">'
                f'<span class="opt-letter">{letter}.</span>'
                f'<span class="opt-text">{otext}</span></label>'
            )
        opts_html = '<div class="q-options">' + "".join(opts) + "</div>"

    ans_html = ""
    if show_answer and q["answer"]:
        # 答案 base64 存放，避免 F12 一眼可见
        ans_enc = base64.b64encode(q["answer"].encode()).decode()
        exp = wrap_svgs(q["explanation_html"] or html.escape(q["explanation_text"]))
        ans_html = (
            f'<div class="q-answer" hidden data-answer="{ans_enc}" data-qid="{qid}">'
            f'<div class="ans-line">正确答案：<b>{html.escape(q["answer"])}</b>'
            f'<span class="ans-src">（来源：{src}）</span></div>'
            f'<div class="exp">{exp}</div></div>'
        )

    return (
        f'<div class="q" id="q{qnum}" data-qid="{qid}">'
        f'<div class="q-head"><span class="q-num">{qnum}</span>'
        f'<span class="q-src">{src}</span>{tag}</div>'
        f'<div class="q-stem">{stem}</div>'
        f'{opts_html}{ans_html}</div>'
    )


def render_paper(picked, date_str, counts, years, show_answer):
    """渲染整份试卷 HTML"""
    all_q = [q for group in picked for q in group]
    total = sum(counts)
    total_score = total * 2

    sections = []
    qnum = 0
    for subj, group, n in zip(SUBJECTS, picked, counts):
        blocks = []
        for q in group:
            qnum += 1
            blocks.append(render_q(q, qnum, show_answer))
        sections.append(
            f'<section class="sec" data-subject="{subj}">'
            f'<h2>{subj}<span class="sec-meta">{n}题 / {n*2}分</span></h2>'
            + "".join(blocks) + "</section>"
        )

    year_range = f"{min(years)}–{max(years)}"
    js = PAGE_JS if show_answer else ""

    page = PAGE_TPL
    for key, val in {
        "TITLE": f"408 随机真题卷 · {date_str}",
        "DATE": date_str,
        "YEAR_RANGE": year_range,
        "TOTAL": str(total),
        "TOTAL_SCORE": str(total_score),
        "SECTIONS": "".join(sections),
        "JS": js,
    }.items():
        page = page.replace(f"@@{key}@@", val)
    return page


PAGE_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>@@TITLE@@</title>
<style>
:root { --accent: #2f6fed; --ok: #16a34a; --bad: #dc2626; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "PingFang SC","Microsoft YaHei",-apple-system,sans-serif;
       background: #f1f5f9; color: #1e293b; line-height: 1.75; }
.paper { max-width: 860px; margin: 0 auto; padding: 24px 16px 80px; }
.paper-head { background: #fff; border-radius: 14px; padding: 22px 24px;
       box-shadow: 0 1px 4px rgba(15,23,42,.08); margin-bottom: 18px; }
.paper-head h1 { font-size: 22px; }
.paper-head .meta { color: #64748b; font-size: 13px; margin-top: 6px; }
.paper-head .meta b { color: #334155; }
.controls { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; align-items: center; }
.btn { border: 1px solid #cbd5e1; background: #f8fafc; color: #334155;
       border-radius: 8px; padding: 7px 14px; font-size: 13px; cursor: pointer; }
.btn:hover { border-color: var(--accent); color: var(--accent); }
.btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
.timer { font-variant-numeric: tabular-nums; font-size: 14px; color: #475569;
       background: #f1f5f9; border-radius: 8px; padding: 6px 12px; margin-left: auto; }
.timer b { color: #0f172a; }
.sec { background: #fff; border-radius: 14px; padding: 18px 20px 10px;
       box-shadow: 0 1px 4px rgba(15,23,42,.08); margin-bottom: 18px; }
.sec h2 { font-size: 17px; padding-bottom: 10px; border-bottom: 2px solid #e2e8f0;
       margin-bottom: 8px; }
.sec-meta { font-size: 12px; color: #64748b; font-weight: normal; margin-left: 10px; }
.q { padding: 16px 4px; border-bottom: 1px dashed #e2e8f0; }
.q:last-child { border-bottom: none; }
.q-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
       flex-wrap: wrap; }
.q-num { background: var(--accent); color: #fff; font-size: 13px; font-weight: 700;
       width: 26px; height: 26px; border-radius: 50%; display: inline-flex;
       align-items: center; justify-content: center; flex: none; }
.q-src { font-size: 12px; color: #94a3b8; }
.q-tag { font-size: 11px; color: var(--accent); background: #eff6ff;
       border: 1px solid #bfdbfe; border-radius: 999px; padding: 1px 8px; }
.q-stem { font-size: 15px; }
.q-stem p { margin: 4px 0; }
.q-stem code, .opt-text code { background: #f1f5f9; padding: 1px 5px;
       border-radius: 4px; font-family: "JetBrains Mono",Consolas,monospace;
       font-size: .92em; color: #0f172a; }
.svg-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 8px 0; }
.svg-scroll svg { max-width: 100%; max-height: 540px; height: auto; display: block;
       margin: 0 auto; }
.svg-scroll svg[data-zoom] { cursor: zoom-in; }
.svg-scroll img { max-width: 100%; height: auto; display: block; margin: 8px auto; }
.q-options { margin: 10px 0 4px; }
.opt { display: flex; gap: 8px; align-items: flex-start; padding: 8px 10px;
       border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 6px;
       cursor: pointer; transition: all .12s; font-size: 14px; }
.opt:hover { border-color: var(--accent); background: #f8fafc; }
.opt input { margin-top: 5px; accent-color: var(--accent); flex: none; }
.opt.selected { border-color: var(--accent); background: #eff6ff; }
.opt.correct { border-color: var(--ok); background: #f0fdf4; }
.opt.wrong { border-color: var(--bad); background: #fef2f2; }
.opt-text svg { max-width: 100%; height: auto; display: block; }
.opts-in-svg-hint { color: #64748b; font-size: 13px; padding: 4px 0; }
.q-answer { margin-top: 12px; border: 1px solid #bfdbfe; background: #eff6ff;
       border-radius: 10px; padding: 12px 14px; }
.ans-line { font-size: 14px; margin-bottom: 6px; }
.ans-line b { color: var(--ok); font-size: 16px; margin: 0 4px; }
.ans-src { color: #94a3b8; font-size: 12px; margin-left: 8px; }
.exp { font-size: 13.5px; color: #334155; border-top: 1px dashed #bfdbfe;
       padding-top: 8px; margin-top: 6px; }
.exp p { margin: 4px 0; }
.exp code { background: #e2e8f0; padding: 1px 5px; border-radius: 4px; }
.exp svg { max-width: 100%; height: auto; display: block; margin: 6px auto; }
.exp img { max-width: 100%; height: auto; border-radius: 6px; }
.exp .highlight { background: #f8fafc; border-radius: 8px; padding: 8px 12px;
       overflow-x: auto; margin: 6px 0; }
.exp pre { font-family: Consolas,monospace; font-size: 13px; }
#lightbox { position: fixed; inset: 0; background: rgba(15,23,42,.92); z-index: 99;
       display: none; align-items: center; justify-content: center; padding: 16px;
       cursor: zoom-out; overflow: auto; }
#lightbox.show { display: flex; }
#lightbox .lb-inner { background: #fff; border-radius: 10px; padding: 10px;
       max-width: 100%; }
#lightbox svg { max-width: 92vw; max-height: 86vh; width: auto; height: auto;
       display: block; }
.result-bar { position: sticky; bottom: 0; background: #0f172a; color: #fff;
       border-radius: 12px; padding: 12px 18px; display: none; align-items: center;
       justify-content: space-between; gap: 12px; margin-top: 14px;
       box-shadow: 0 -4px 16px rgba(15,23,42,.25); flex-wrap: wrap; }
.result-bar.show { display: flex; }
.result-bar .score { font-size: 15px; }
.result-bar .score b { color: #fbbf24; font-size: 20px; }
/* ========== 平板与桌面适配 ========== */
@media (min-width: 768px) {
  .paper { max-width: 1040px; padding: 32px 28px 90px; }
  .paper-head { padding: 28px 32px; }
  .paper-head h1 { font-size: 26px; }
  .paper-head .meta { font-size: 14px; }
  .btn { padding: 9px 18px; font-size: 14px; }
  .sec { padding: 24px 28px 14px; }
  .sec h2 { font-size: 19px; }
  .q { padding: 22px 6px; }
  .q-num { width: 30px; height: 30px; font-size: 14px; }
  .q-stem { font-size: 16.5px; }
  .q-options { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 18px;
       align-items: start; }
  .opt { margin-bottom: 0; padding: 11px 14px; font-size: 15px; }
  .opt input { margin-top: 6px; width: 17px; height: 17px; }
  .q-answer { padding: 16px 20px; }
  .exp { font-size: 14.5px; }
}
@media (min-width: 1100px) {
  .paper { max-width: 1280px; }
  .opt-text { line-height: 1.65; }
}
@media print {
  body { background: #fff; }
  .paper { max-width: 100%; padding: 0; }
  .controls, .result-bar, .timer { display: none !important; }
  .sec, .paper-head { box-shadow: none; border: 1px solid #ddd; }
  .opt { break-inside: avoid; }
  .q { break-inside: avoid; }
}
</style>
</head>
<body>
<div class="paper">
  <div class="paper-head">
    <h1>📝 408 随机真题卷</h1>
    <div class="meta">日期：<b>@@DATE@@</b> ｜ 出题范围：<b>@@YEAR_RANGE@@</b> 年真题 ｜
      共 <b>@@TOTAL@@</b> 题 · <b>@@TOTAL_SCORE@@</b> 分（每题 2 分）
      ｜ 结构：数据结构 11 / 组成原理 11 / 操作系统 10 / 计算机网络 8</div>
    <div class="controls">
      <button class="btn btn-primary" onclick="submitPaper()">交卷并查看答案</button>
      <button class="btn" onclick="showAllAnswers()">直接看全部答案</button>
      <button class="btn" onclick="clearPaper()">清空重做</button>
      <span class="timer" id="timer">用时 <b>00:00</b></span>
    </div>
  </div>
  @@SECTIONS@@
  <div class="result-bar" id="resultBar"></div>
</div>
<div id="lightbox" onclick="this.classList.remove('show')"><div class="lb-inner" id="lbInner"></div></div>
<script>
@@JS@@
</script>
</body>
</html>
"""

PAGE_JS = """
// ---------- localStorage：作答状态持久化 ----------
var LS_KEY = 'paper_' + location.pathname.split('/').pop();
function saveState() {
  var s = {};
  document.querySelectorAll('.q').forEach(function(q) {
    var c = q.querySelector('input:checked');
    if (c) s[q.dataset.qid] = c.value;
  });
  s.__elapsed = elapsed;
  try { localStorage.setItem(LS_KEY, JSON.stringify(s)); } catch(e) {}
}
function restoreState() {
  var s;
  try { s = JSON.parse(localStorage.getItem(LS_KEY) || '{}'); } catch(e) { return; }
  if (s.__elapsed) elapsed = s.__elapsed;
  document.querySelectorAll('.q').forEach(function(q) {
    var v = s[q.dataset.qid];
    if (!v) return;
    var inp = q.querySelector('input[value="' + v + '"]');
    if (inp) { inp.checked = true; inp.closest('label.opt').classList.add('selected'); }
  });
}

// ---------- 计时器 ----------
var elapsed = 0, timerId = null;
function fmt(t) {
  var m = Math.floor(t/60), s = t%60;
  return (m<10?'0':'')+m+':'+(s<10?'0':'')+s;
}
function startTimer() {
  if (timerId) return;
  timerId = setInterval(function() {
    elapsed++;
    var el = document.querySelector('#timer b');
    if (el) el.textContent = fmt(elapsed);
    if (elapsed % 5 === 0) saveState();
  }, 1000);
}

// ---------- 计分与判卷 ----------
function dec(ans) { return atob(ans || ''); }
function score() {
  var total = 0, right = 0;
  document.querySelectorAll('.q').forEach(function(q) {
    var ans = q.querySelector('.q-answer');
    if (!ans) return;
    total += 2;
    var chosen = q.querySelector('input[type=radio]:checked');
    if (chosen && chosen.value === dec(ans.dataset.answer)) right += 2;
  });
  return {total: total, right: right};
}
function markQuestion(q, reveal) {
  var ans = q.querySelector('.q-answer');
  if (!ans) return;
  ans.hidden = false;
  if (!reveal) return;
  var correct = dec(ans.dataset.answer);
  var chosen = q.querySelector('input:checked');
  q.querySelectorAll('label.opt').forEach(function(l) {
    var inp = l.querySelector('input');
    if (!inp) return;
    if (inp.value === correct) l.classList.add('correct');
    else if (inp.checked) l.classList.add('wrong');
    if (inp.checked) l.classList.add('selected');
  });
  // 错题本：错题 / 未答都记，答对则移出
  try {
    var wb = JSON.parse(localStorage.getItem('wb_wrong') || '[]');
    var qid = q.dataset.qid;
    var wrong = !chosen || chosen.value !== correct;
    if (wrong && wb.indexOf(qid) < 0) wb.push(qid);
    if (!wrong) { var i = wb.indexOf(qid); if (i >= 0) wb.splice(i, 1); }
    localStorage.setItem('wb_wrong', JSON.stringify(wb));
  } catch(e) {}
}
function submitPaper() {
  var s = score();
  var done = 0;
  document.querySelectorAll('.q').forEach(function(q) {
    var ans = q.querySelector('.q-answer');
    if (ans && q.querySelector('input:checked')) done++;
    markQuestion(q, true);
  });
  var bar = document.getElementById('resultBar');
  bar.innerHTML = '<span class="score">得分：<b>' + s.right + '</b> / ' + s.total + ' 分' +
    ' ｜ 已答 ' + done + ' / ' + s.total/2 + ' 题 ｜ 用时 ' + fmt(elapsed) + '</span>' +
    '<span><button class="btn" style="background:#1e293b;color:#fff;border-color:#475569" onclick="clearPaper()">清空重做</button></span>';
  bar.classList.add('show');
  try {
    localStorage.setItem('paperStatus_' + location.pathname.split('/').pop(),
      JSON.stringify({right: s.right, total: s.total, time: fmt(elapsed)}));
  } catch(e) {}
  window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});
}
function showAllAnswers() {
  document.querySelectorAll('.q').forEach(function(q) { markQuestion(q, false); });
  document.getElementById('resultBar').classList.remove('show');
}
function clearPaper() {
  document.querySelectorAll('input[type=radio]').forEach(function(i) { i.checked = false; });
  document.querySelectorAll('label.opt').forEach(function(l) {
    l.classList.remove('selected','correct','wrong');
  });
  document.querySelectorAll('.q-answer').forEach(function(a) { a.hidden = true; });
  document.getElementById('resultBar').classList.remove('show');
  try { localStorage.removeItem(LS_KEY); } catch(e) {}
  elapsed = 0;
}

// ---------- 交互绑定 ----------
document.querySelectorAll('label.opt').forEach(function(l) {
  l.addEventListener('click', function() {
    var name = l.querySelector('input').name;
    document.querySelectorAll('label.opt').forEach(function(o) {
      if (o.querySelector('input').name === name) o.classList.remove('selected');
    });
    l.classList.add('selected');
    startTimer();
    saveState();
  });
});
// SVG 点击放大
document.addEventListener('click', function(e) {
  var svg = e.target.closest('svg[data-zoom]');
  if (!svg) return;
  var clone = svg.cloneNode(true);
  clone.removeAttribute('data-zoom');
  clone.style.maxWidth = '92vw';
  document.getElementById('lbInner').innerHTML = '';
  document.getElementById('lbInner').appendChild(clone);
  document.getElementById('lightbox').classList.add('show');
});
restoreState();
if (elapsed > 0) startTimer();
"""


def main():
    ap = argparse.ArgumentParser(description="408 历年真题随机组卷器")
    ap.add_argument("--date", default="", help="试卷日期 YYYY-MM-DD（默认今天，作为随机种子）")
    ap.add_argument("--seed", type=int, default=None, help="自定义随机种子（替代日期）")
    ap.add_argument("--counts", nargs="+", type=int, default=DEFAULT_COUNTS,
                    help="各科题量：数据结构 组成原理 操作系统 计算机网络（默认 11 11 10 8）")
    ap.add_argument("--years", default="", help="出题年份范围，如 2009-2024 或 2009,2010,2024")
    ap.add_argument("--exclude-recent", type=int, default=0,
                    help="排除最近 N 年真题（留作整卷模拟）")
    ap.add_argument("--no-answer", action="store_true", help="纯做题版，不含答案解析")
    ap.add_argument("--output", default="", help="输出文件路径")
    ap.add_argument("--open", action="store_true", help="生成后用系统浏览器打开")
    args = ap.parse_args()

    from datetime import date, datetime, timedelta
    date_str = args.date or date.today().isoformat()

    db = load_db()
    all_years = sorted({q["year"] for q in db})
    if args.years:
        if "-" in args.years:
            a, b = args.years.split("-")
            years = [y for y in all_years if int(a) <= y <= int(b)]
        else:
            years = [int(y) for y in args.years.split(",")]
    else:
        years = all_years
    if args.exclude_recent:
        years = [y for y in years if y <= all_years[-1] - args.exclude_recent]
    if not years:
        print("没有可用年份！", file=sys.stderr)
        sys.exit(1)

    if len(args.counts) != 4:
        print("counts 需要 4 个数字（数据结构 组成原理 操作系统 计算机网络）", file=sys.stderr)
        sys.exit(1)

    # 防重复：最近 N 天抽过的题优先避开
    log = load_picked_log()
    recent_ids = set()
    try:
        cutoff = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=NO_REPEAT_DAYS)).strftime("%Y-%m-%d")
        for d, ids in log.items():
            if d != date_str and d >= cutoff:
                recent_ids.update(ids)
    except ValueError:
        pass

    seed = make_seed(date_str, args.seed)
    picked = pick_questions(db, args.counts, years, seed, recent_ids or None)
    html_out = render_paper(picked, date_str, args.counts, years, not args.no_answer)

    default_out = os.path.join(BASE_DIR, "papers", f"408卷_{date_str}.html")
    out = args.output or default_out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_out)

    # 记录今日抽题，供以后防重复
    if not args.seed and not args.output:
        log[date_str] = [f"{q['year']}-{q['num']}" for group in picked for q in group]
        save_picked_log(log)

    size_kb = os.path.getsize(out) / 1024
    print(f"已生成: {out}")
    print(f"随机种子: {seed}（日期 {date_str}）")
    print(f"出题范围: {min(years)}-{max(years)} | 结构: " +
          " / ".join(f"{s} {n}题" for s, n in zip(SUBJECTS, args.counts)))
    print(f"页面大小: {size_kb:.0f} KB")
    if args.open:
        import subprocess
        subprocess.Popen(["xdg-open", out])


if __name__ == "__main__":
    main()

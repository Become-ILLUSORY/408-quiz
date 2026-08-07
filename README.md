# 408 历年真题随机组卷器

从 [csgraduates.com](https://www.csgraduates.com/study_methods/408quiz/) 的 408 历年真题（2009–2026，共 18 年）中**每天随机抽题组卷**，生成可交互的 HTML 试卷。

## 功能

- 📚 **题库 720 道选择题**：2009–2026 全部 18 套真题，每年 40 题，含**答案、知识点标签、逐题解析**
- 🎲 **每天一套随机卷**：以日期为随机种子，同一天生成结果固定可复现，换天自动换卷
- 📐 **严格遵循 408 各科题量**：数据结构 11 + 组成原理 11 + 操作系统 10 + 计算机网络 8 = 40 题 / 80 分
- 🖼️ **图形题目完整保留**：题目中的图（二叉树、图、硬件结构等）以 SVG 矢量格式内联提取，任意缩放清晰；选项画在图中（如"下列树中符合…的是"）的题目自动识别，标注"选项为图中 A/B/C/D 所示"
- ✅ **可交互**：单选作答、交卷判分、逐题显示答案与解析、清空重做
- 🖨️ **打印友好**：A4 打印样式，可直接打印成纸质卷

## 项目结构

```
408-quiz/
├── scrape_408.py      # 爬虫：抓取历年真题页面 → questions.json
├── make_paper.py      # 组卷器：随机抽题 → HTML 试卷
├── questions.json     # 题库（720 题，含题干HTML/选项/答案/标签/解析/SVG）
└── papers/            # 生成的试卷（408卷_YYYY-MM-DD.html）
```

## 快速开始

```bash
# 生成今天的卷子
python3 make_paper.py

# 指定日期（该日期作为随机种子，可复现同一天卷子）
python3 make_paper.py --date 2026-08-07

# 自定义随机种子
python3 make_paper.py --seed 42

# 排除最近 2 年真题（留作整卷模拟）
python3 make_paper.py --exclude-recent 2

# 只从 2009-2024 年抽题
python3 make_paper.py --years 2009-2024

# 纯做题版（不含答案与解析）
python3 make_paper.py --no-answer

# 自定义各科题量：数据结构 15 / 组成原理 10 / 操作系统 10 / 网络 5
python3 make_paper.py --counts 15 10 10 5

# 生成后用系统浏览器打开
python3 make_paper.py --open
```

## 重新爬取题库

```bash
# 全量（2009-2026）
python3 scrape_408.py

# 指定年份范围
python3 scrape_408.py 2009 2026
```

## 实现要点

### 数据来源解析
站点为 Hugo 静态站，每道选择题是 `<div class="choice-container" data-answer="X" data-tags="知识点">`：
- **答案**直接写在 `data-answer` 属性，无需点击
- **解析**内嵌在页面隐藏的 `.explanation` div 中
- **图片**为内联 SVG（drawio 导出），直接从 HTML 提取

### 爬虫注意事项
- 站点响应头**无 charset 声明**，requests 默认按 ISO-8859-1 解码会导致中文乱码 → 需显式 `r.encoding = "utf-8"`
- SVG 中 `viewbox`（小写）会导致浏览器不缩放 → 规范化为 `viewBox`
- SVG 内 `<!DOCTYPE html>` 垃圾前缀需清理
- 题干文本提取时排除 SVG 内容（SVG 文字位置乱序无意义）

### 组卷规则
- 408 官方选择题结构：数据结构 11 / 组成原理 11 / 操作系统 10 / 计算机网络 8（历年一致）
- 随机种子 = `md5(日期) % 2^32`，保证每天固定一套、可复现
- 每题标注来源（年份·科目·原题号），方便回溯

## 依赖

- Python 3 + `requests` + `beautifulsoup4`（爬虫）
- 组卷器仅用标准库

## 每日自动组卷（GitHub Actions）

仓库已配置 [.github/workflows/daily-paper.yml](.github/workflows/daily-paper.yml)，**每天北京时间 08:00（UTC 00:00）自动运行**：

1. 用题库 `questions.json` 生成当日随机卷（`papers/408卷_YYYY-MM-DD.html`）
2. 更新卷子列表页 `index.html`
3. 提交并推送到仓库主分支
4. 部署到 GitHub Pages：`https://<user>.github.io/408-quiz/`（首页为卷子列表，最新卷在顶部）

也支持手动触发：仓库 Actions 页面 → Daily 408 Paper → Run workflow。

### 重新爬取题库（手动）

站点内容更新后，本地运行爬虫重新生成 `questions.json` 再提交即可：

```bash
# 全量（2009-2026）
python3 scrape_408.py

# 指定年份范围
python3 scrape_408.py 2009 2026
```

> 注意：爬虫依赖站点 HTML 结构，若站点改版需同步更新 `scrape_408.py`；组卷器本身只依赖仓库内的 `questions.json`，无需联网。

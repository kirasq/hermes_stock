#!/usr/bin/env python3
"""
auto_push.py - 自动提交并推送到 GitHub Pages
用途：每日复盘、回测报告生成后自动 push 到 hermes_stock 仓库
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 配置
REPO_DIR = Path("/opt/data/hermes_stock")
DOCS_DIR = REPO_DIR / "docs"
TRADING_DIR = Path("/opt/data/trading")

# GitHub 配置
GITHUB_REPO = "kirasq/hermes_stock"
# 从文件读取 token（避免被安全扫描拦截）
try:
    with open("/opt/data/github_token.txt", "r") as f:
        GITHUB_TOKEN = f.read().strip()
except FileNotFoundError:
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def git_commit_push(commit_msg):
    """提交并推送到 GitHub"""
    os.chdir(REPO_DIR)
    
    # 添加所有变更
    os.system("git add .")
    
    # 提交
    os.system(f'git commit -m "{commit_msg}"')
    
    # 推送到 main 分支（触发 GitHub Pages）
    if GITHUB_TOKEN:
        push_cmd = f"git push https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git main 2>&1"
    else:
        push_cmd = "git push origin main 2>&1"
    
    ret = os.system(push_cmd)
    if ret == 0:
        print(f"✅ 推送成功：{commit_msg}")
        return True
    else:
        print(f"❌ 推送失败，返回码：{ret}")
        return False


def generate_daily_index(daily_dir):
    """重新生成 docs/daily/index.html（静态文件列表，不依赖 JS 抓取目录）"""
    # 扫描所有文件（排除 index.html/index.md）
    files = []
    for f in sorted(daily_dir.iterdir(), reverse=True):
        if f.name in ("index.html", "index.md") or f.is_dir():
            continue
        files.append(f.name)
    
    # 按日期分组
    from collections import defaultdict
    by_date = defaultdict(list)
    for name in files:
        # 提取日期：2026-06-03_summary.html -> 2026-06-03
        parts = name.split("_")
        if len(parts) >= 1:
            date_candidate = parts[0]
        else:
            date_candidate = ""
        by_date[date_candidate].append(name)
    
    # 日期排序（最新的在前）
    sorted_dates = sorted(by_date.keys(), reverse=True)
    
    def badge_html(name):
        ext = name.split(".")[-1].lower()
        cls = {"json": "badge-json", "md": "badge-md", "html": "badge-html"}.get(ext, "badge-md")
        return f'<span class="badge {cls}">{ext.upper()}</span>'
    
    def desc_html(name):
        ext = name.split(".")[-1].lower()
        mapping = {
            "html": "HTML 报告", "md": "Markdown 报告", "json": "结构化数据",
        }
        type_desc = mapping.get(ext, "报告文件")
        # 提取日期
        date_part = name.split("_")[0] if "_" in name else ""
        keywords = {
            "summary": "每日汇总", "review": "盘后复盘",
            "morning": "晨间资讯", "premarket": "集合竞价",
            "news": "新闻量化",
        }
        kw_desc = ""
        for kw, label in keywords.items():
            if kw in name:
                kw_desc = label
                break
        return f'{kw_desc} · {date_part}' if kw_desc and date_part else type_desc
    
    sections = []
    for d in sorted_dates:
        name_files = sorted(by_date[d], reverse=True)
        items = "".join(
            f'    <li><a href="{nf}"><span class="file-name">{nf}</span>{badge_html(nf)}</a>'
            f'<div class="file-desc">{desc_html(nf)}</div></li>\n'
            for nf in name_files
        )
        sections.append(
            f'  <div class="date-group">{d}</div>\n'
            f'  <ul class="file-list">\n{items}  </ul>'
        )
    
    section_html = "\n\n".join(sections) if sections else '  <p class="empty">暂无报告</p>'
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>每日交易报告 | Hermes 自进化交易系统</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #0d1117; color: #c9d1d9; }}
    h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
    h2 {{ color: #f0c674; margin-top: 30px; }}
    a {{ color: #58a6ff; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .file-list {{ list-style: none; padding: 0; }}
    .file-list li {{ padding: 12px; margin: 8px 0; background: #161b22; border: 1px solid #30363d; border-radius: 6px; transition: border-color 0.2s; }}
    .file-list li:hover {{ border-color: #58a6ff; background: #1c2333; }}
    .file-name {{ font-size: 16px; font-weight: 600; color: #f0c674; }}
    .file-desc {{ font-size: 13px; color: #8b949e; margin-top: 4px; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; margin-left: 8px; vertical-align: middle; }}
    .badge-json {{ background: rgba(63,185,80,0.15); color: #3fb950; border: 1px solid #3fb950; }}
    .badge-md {{ background: rgba(88,166,255,0.15); color: #58a6ff; border: 1px solid #58a6ff; }}
    .badge-html {{ background: rgba(240,198,116,0.15); color: #f0c674; border: 1px solid #f0c674; }}
    .date-group {{ color: #8b949e; font-size: 13px; margin-top: 20px; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #21262d; }}
    hr {{ border: none; border-top: 1px solid #30363d; margin: 30px 0; }}
    .empty {{ color: #484f58; text-align: center; padding: 40px; }}
  </style>
</head>
<body>
  <h1>📅 每日交易报告</h1>
  <p style="color:#8b949e;">Hermes 自进化交易系统 · 最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

  <h2>📋 报告列表</h2>

{section_html}

  <hr>
  <p style="text-align:center; color:#484f58; font-size:12px;">
    ⚠️ 所有交易均为模拟盘 · 由 Hermes 系统自动生成 ·
    <a href="https://kirasq.github.io/hermes_stock/">返回首页</a> ·
    <a href="https://github.com/kirasq/hermes_stock">GitHub 仓库</a>
  </p>
</body>
</html>"""
    
    index_path = daily_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 已生成静态文件列表：{index_path} ({len(files)} 个文件)")


def push_daily_review(date_str):
    """推送每日复盘报告"""
    import shutil
    daily_dir = DOCS_DIR / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制多来源文件到 docs/daily/
    src_pairs = [
        (TRADING_DIR / "reviews" / f"{date_str}_review.json", f"{date_str}_review.json"),
        (TRADING_DIR / "daily" / f"{date_str}_review.md", f"{date_str}_review.md"),
        (TRADING_DIR / "daily" / f"{date_str}_review.html", f"{date_str}_review.html"),
        (TRADING_DIR / "daily" / f"{date_str}_summary.md", f"{date_str}_summary.md"),
        (TRADING_DIR / "daily" / f"{date_str}_summary.html", f"{date_str}_summary.html"),
        (TRADING_DIR / "daily" / f"{date_str}_morning.md", f"{date_str}_morning.md"),
        (TRADING_DIR / "daily" / f"{date_str}_morning.html", f"{date_str}_morning.html"),
        (TRADING_DIR / "daily" / f"{date_str}_premarket.json", f"{date_str}_premarket.json"),
    ]
    for src, dst in src_pairs:
        if src.exists():
            shutil.copy(src, daily_dir / dst)
            print(f"复制 {dst}")
    
    # 重新生成静态文件列表！
    generate_daily_index(daily_dir)
    
    return git_commit_push(f"📅 每日报告 {date_str}")


def push_backtest_report(date_str):
    """推送回测报告"""
    # 复制回测结果
    metrics_file = TRADING_DIR / "strategy_metrics.json"
    rules_file = TRADING_DIR / "rules.json"
    
    backtest_dir = DOCS_DIR / "backtest"
    backtest_dir.mkdir(parents=True, exist_ok=True)
    
    if metrics_file.exists():
        import shutil
        shutil.copy(metrics_file, backtest_dir / f"metrics_{date_str}.json")
        # 也复制为 latest
        shutil.copy(metrics_file, backtest_dir / "latest.json")
        print(f"复制策略指标：{metrics_file}")
    
    if rules_file.exists():
        import shutil
        shutil.copy(rules_file, backtest_dir / f"rules_{date_str}.json")
        shutil.copy(rules_file, backtest_dir / "latest_rules.json")
        print(f"复制规则文件：{rules_file}")
    
    # 生成回测报告索引
    index_md = backtest_dir / "index.md"
    with open(index_md, "w") as f:
        f.write("# 回测报告\n\n")
        f.write(f"## {date_str}\n\n")
        f.write(f"- [策略指标](metrics_{date_str}.json)\n")
        f.write(f"- [规则配置](rules_{date_str}.json)\n")
        f.write(f"\n---\n\n")
        f.write(f"## 最新配置\n\n")
        f.write(f"- [最新指标](latest.json)\n")
        f.write(f"- [最新规则](latest_rules.json)\n")
    
    return git_commit_push(f"📊 回测报告 {date_str}")


def push_strategy_evolution(date_str):
    """推送策略进化日志"""
    metrics_file = TRADING_DIR / "strategy_metrics.json"
    
    strategy_dir = DOCS_DIR / "strategy"
    strategy_dir.mkdir(parents=True, exist_ok=True)
    
    if metrics_file.exists():
        import shutil
        shutil.copy(metrics_file, strategy_dir / "evolution_log.json")
        print(f"复制进化日志：{metrics_file}")
        
        # 生成可读的进化报告
        with open(metrics_file, "r") as f:
            metrics = json.load(f)
        
        report_md = strategy_dir / "evolution_report.md"
        with open(report_md, "w") as f:
            f.write("# 策略进化报告\n\n")
            f.write(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## 当前指标\n\n")
            f.write(f"- 总交易数：{metrics.get('total_trades', 0)}\n")
            f.write(f"- 胜率：{metrics.get('win_rate', 0):.1f}%\n")
            f.write(f"- 平均盈利：{metrics.get('avg_winner', 0):.1f}\n")
            f.write(f"- 平均亏损：{metrics.get('avg_loser', 0):.1f}\n")
            f.write(f"- 盈亏比：{metrics.get('profit_factor', 0):.1f}\n\n")
            
            f.write("## 进化历史\n\n")
            for log in metrics.get("evolution_log", []):
                f.write(f"### {log.get('version', 'v?')} - {log.get('date', '')}\n\n")
                f.write(f"- 触发原因：{log.get('trigger', '')}\n")
                f.write(f"- 旧参数：{json.dumps(log.get('old_params', {}), ensure_ascii=False)}\n")
                f.write(f"- 新参数：{json.dumps(log.get('new_params', {}), ensure_ascii=False)}\n")
                f.write(f"- 提升幅度：{log.get('backtest_improvement', '')}\n")
                f.write(f"- 状态：{log.get('status', '')}\n\n")
    
    return git_commit_push(f"🧬 策略进化 {date_str}")


def push_wikillm_content():
    """推送 WikiLLM 知识库内容（由 trader-strategy 手动触发）"""
    wikillm_dir = DOCS_DIR / "wikillm"
    
    # 生成索引
    index_md = wikillm_dir / "index.md"
    with open(index_md, "w") as f:
        f.write("# WikiLLM 股票知识库\n\n")
        f.write("> ⚠️ 本知识库信息来自互联网，未经实盘验证，仅供借鉴参考，非金科玉律！\n\n")
        f.write("## 目录\n\n")
        f.write("- [技术分析](technical/)\n")
        f.write("- [基本面分析](fundamental/)\n")
        f.write("- [交易心理学](psychology/)\n")
        f.write("- [风险管理](risk-management/)\n")
        f.write("- [交易策略](strategies/)\n")
        f.write("- [市场机制](market-mechanism/)\n")
        f.write("- [量化交易](quantitative/)\n\n")
    
    return git_commit_push("📚 WikiLLM 知识库更新")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python3 auto_push.py <daily|backtest|strategy|wikillm> [日期]")
        print("示例：python3 auto_push.py daily 2026-05-31")
        sys.exit(1)
    
    action = sys.argv[1]
    date_str = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")
    
    print(f"=" * 60)
    print(f"自动推送：{action}")
    print(f"日期：{date_str}")
    print(f"=" * 60)
    
    os.chdir(REPO_DIR)
    os.system("git pull origin main 2>&1")  # 先拉取最新
    
    if action == "daily":
        success = push_daily_review(date_str)
    elif action == "backtest":
        success = push_backtest_report(date_str)
    elif action == "strategy":
        success = push_strategy_evolution(date_str)
    elif action == "wikillm":
        success = push_wikillm_content()
    else:
        print(f"未知操作：{action}")
        sys.exit(1)
    
    sys.exit(0 if success else 1)

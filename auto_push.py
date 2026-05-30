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


def push_daily_review(date_str):
    """推送每日复盘报告"""
    # 复制复盘报告到 docs/daily/
    review_src = TRADING_DIR / "reviews" / f"{date_str}_review.json"
    review_md_src = TRADING_DIR / "daily" / f"{date_str}_review.md"
    
    daily_dir = DOCS_DIR / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    
    if review_src.exists():
        import shutil
        shutil.copy(review_src, daily_dir / f"{date_str}_review.json")
        print(f"复制复盘 JSON：{review_src}")
    
    if review_md_src.exists():
        import shutil
        shutil.copy(review_md_src, daily_dir / f"{date_str}_review.md")
        print(f"复制复盘 MD：{review_md_src}")
    
    # 更新 daily/index.md
    index_md = daily_dir / "index.md"
    with open(index_md, "a" if index_md.exists() else "w") as f:
        f.write(f"# 每日复盘索引\n\n")
        f.write(f"## {date_str}\n\n")
        f.write(f"- [JSON 报告]({date_str}_review.json)\n")
        f.write(f"- [MD 报告]({date_str}_review.md)\n\n")
    
    return git_commit_push(f"📅 每日复盘 {date_str}")


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

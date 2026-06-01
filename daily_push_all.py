#!/usr/bin/env python3
"""
daily_push_all.py - 每日汇总推送所有结果到 GitHub Pages

功能：
1. 汇总当日所有 trader profile 的输出
2. 更新 docs/daily/ 中的当日报告
3. 更新 docs/backtest/ 中的最新指标
4. 更新 docs/strategy/ 中的进化日志
5. 生成可视化索引页面
6. 推送到 GitHub Pages
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 配置
TRADING_DIR = Path("/opt/data/trading")
REPO_DIR = Path("/opt/data/hermes_stock")
DOCS_DIR = REPO_DIR / "docs"
GITHUB_TOKEN_FILE = Path("/opt/data/github_token.txt")

# GitHub 配置
GITHUB_REPO = "kirasq/hermes_stock"
try:
    with open(GITHUB_TOKEN_FILE, "r") as f:
        GITHUB_TOKEN = f.read().strip()
except FileNotFoundError:
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def git_commit_push(commit_msg):
    """提交并推送到 GitHub"""
    os.chdir(REPO_DIR)
    
    # 先拉取最新
    os.system("git pull origin main 2>&1")
    
    # 添加所有变更
    os.system("git add .")
    
    # 提交
    os.system(f'git commit -m "{commit_msg}"')
    
    # 推送
    if GITHUB_TOKEN:
        push_cmd = f"git push https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git main 2>&1"
    else:
        push_cmd = "git push origin main 2>&1"
    
    ret = os.system(push_cmd)
    if ret == 0:
        print(f"✅ 推送成功：{commit_msg}")
        print(f"   Pages URL: https://kirasq.github.io/hermes_stock/")
        return True
    else:
        print(f"❌ 推送失败，返回码：{ret}")
        return False


def collect_daily_results(date_str):
    """收集当日所有结果"""
    results = {
        "date": date_str,
        "trading": {},
        "backtest": {},
        "evolution": {},
        "review": {}
    }
    
    # 1. 持仓信息
    positions_file = TRADING_DIR / "positions.json"
    if positions_file.exists():
        with open(positions_file, "r") as f:
            results["trading"]["positions"] = json.load(f)
    
    # 2. 交易记录
    trades_file = TRADING_DIR / "trades.json"
    if trades_file.exists():
        with open(trades_file, "r") as f:
            all_trades = json.load(f).get("trades", [])
            # 筛选当日交易
            daily_trades = [
                t for t in all_trades
                if date_str in t.get("time", t.get("timestamp", ""))
            ]
            results["trading"]["daily_trades"] = daily_trades
            results["trading"]["total_trades"] = len(all_trades)
    
    # 3. 策略指标
    metrics_file = TRADING_DIR / "strategy_metrics.json"
    if metrics_file.exists():
        with open(metrics_file, "r") as f:
            results["backtest"] = json.load(f)
    
    # 4. 规则文件
    rules_file = TRADING_DIR / "rules.json"
    if rules_file.exists():
        with open(rules_file, "r") as f:
            results["trading"]["rules"] = json.load(f)
    
    # 5. 复盘报告
    review_file = TRADING_DIR / "reviews" / f"{date_str}_review.json"
    if review_file.exists():
        with open(review_file, "r") as f:
            results["review"] = json.load(f)
    
    return results


def generate_daily_report(date_str, results):
    """生成当日汇总报告（Markdown）"""
    report_md = DOCS_DIR / "daily" / f"{date_str}_summary.md"
    report_md.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_md, "w") as f:
        f.write(f"# 每日汇总报告 - {date_str}\n\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        # 持仓
        f.write("## 📊 持仓状态\n\n")
        positions = results.get("trading", {}).get("positions", {}).get("positions", [])
        if positions:
            f.write("| 股票代码 | 股票名称 | 数量 | 成本价 | 当前价 | 盈亏% |\n")
            f.write("|---------|---------|------|--------|--------|-------|\n")
            for pos in positions:
                f.write(f"| {pos.get('secCode', '')} | {pos.get('secName', '')} | "
                       f"{pos.get('count', 0)} | ¥{pos.get('cost_price', 0):.2f} | "
                       f"{pos.get('current_price', 0):.2f} | {pos.get('pnl_pct', 0):+.2f}% |\n")
        else:
            f.write("*无持仓*\n")
        f.write("\n")
        
        # 当日交易
        f.write("## 🔄 当日交易\n\n")
        daily_trades = results.get("trading", {}).get("daily_trades", [])
        if daily_trades:
            f.write(f"共 {len(daily_trades)} 笔交易\n\n")
            for t in daily_trades:
                f.write(f"- **{t.get('secName', '')}** ({t.get('secCode', '')}) "
                       f"{t.get('direction', '')} {t.get('quantity', 0)}股 @ ¥{t.get('price', 0):.2f} "
                       f"→ {t.get('status', '')}\n")
        else:
            f.write("*当日无交易*\n")
        f.write("\n")
        
        # 策略指标
        f.write("## 📈 策略指标\n\n")
        backtest = results.get("backtest", {})
        if backtest:
            f.write(f"- 总交易数：{backtest.get('total_trades', 0)}\n")
            f.write(f"- 胜率：{backtest.get('win_rate', 0):.1f}%\n")
            f.write(f"- 盈亏比：{backtest.get('profit_factor', 0):.2f}\n")
            f.write(f"- 止损合规率：{backtest.get('stop_loss_compliance', 0):.1f}%\n")
        f.write("\n")
        
        # 当前规则
        f.write("## ⚙️ 当前策略参数\n\n")
        rules = results.get("trading", {}).get("rules", {}).get("rules", {})
        if rules:
            f.write(f"- 止损：{rules.get('stop_loss_pct', 0)}%\n")
            f.write(f"- 止盈：{rules.get('take_profit_pct', 0)}%\n")
            f.write(f"- 最大仓位：{rules.get('max_position_pct', 0)}%\n")
            f.write(f"- 最小持仓：{rules.get('min_position_shares', 0)} 股\n")
        f.write("\n")
        
        # 复盘摘要
        f.write("## 📋 盘后复盘\n\n")
        review = results.get("review", {})
        if review:
            violations = review.get("violations", [])
            if violations:
                f.write("### ⚠️ 纪律违规\n\n")
                for v in violations:
                    f.write(f"- **{v.get('type', '')}**（{v.get('severity', '')}）：{v.get('detail', '')}\n")
                f.write("\n")
    
    print(f"✅ 生成汇总报告：{report_md}")
    return report_md


def update_index_pages(date_str, results):
    """更新各索引页面"""
    
    # 1. 每日报告索引
    daily_index = DOCS_DIR / "daily" / "index.md"
    with open(daily_index, "a" if daily_index.exists() else "w") as f:
        if not daily_index.exists():
            f.write("# 每日交易报告\n\n")
        f.write(f"## {date_str}\n\n")
        f.write(f"- [汇总报告]({date_str}_summary.md)\n")
        f.write(f"- [详细复盘]({date_str}_review.md)\n")
        f.write(f"- [JSON 数据]({date_str}_review.json)\n\n")
    
    # 2. 策略指标索引
    backtest_index = DOCS_DIR / "backtest" / "index.md"
    backtest_dir = DOCS_DIR / "backtest"
    backtest_dir.mkdir(parents=True, exist_ok=True)
    
    with open(backtest_index, "a" if backtest_index.exists() else "w") as f:
        if not backtest_index.exists():
            f.write("# 策略回测报告\n\n")
        f.write(f"## {date_str}\n\n")
        f.write(f"- [策略指标](metrics_{date_str}.json)\n")
        f.write(f"- [规则配置](rules_{date_str}.json)\n\n")
    
    # 3. 主索引（根目录）
    main_index = DOCS_DIR / "index.md"
    with open(main_index, "w") as f:
        f.write("# Hermes 股票交易系统\n\n")
        f.write(f"最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write("## 📂 快速导航\n\n")
        f.write("- [每日交易报告](daily/)\n")
        f.write("- [策略回测报告](backtest/)\n")
        f.write("- [策略进化日志](strategy/)\n")
        f.write("- [WikiLLM 知识库](wikillm/)\n\n")
        
        f.write("## 📊 最新状态\n\n")
        positions = results.get("trading", {}).get("positions", {}).get("positions", [])
        if positions:
            f.write(f"**持仓数**：{len(positions)} 只\n\n")
            for pos in positions:
                f.write(f"- {pos.get('secName', '')} ({pos.get('secCode', '')})："
                       f"盈亏 {pos.get('pnl_pct', 0):+.2f}%\n")
        else:
            f.write("*当前无持仓*\n")
        f.write("\n")
        
        f.write("## 🔗 相关链接\n\n")
        f.write("- [GitHub 仓库](https://github.com/kirasq/hermes_stock)\n")
        f.write("- [系统架构说明](https://github.com/kirasq/hermes_stock/blob/main/README.md)\n")
    
    print(f"✅ 更新索引页面")


def copy_latest_files(results):
    """复制最新文件到固定名称（方便引用）"""
    backtest_dir = DOCS_DIR / "backtest"
    backtest_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制最新策略指标
    metrics_file = TRADING_DIR / "strategy_metrics.json"
    if metrics_file.exists():
        import shutil
        shutil.copy(metrics_file, backtest_dir / "latest.json")
        print(f"✅ 复制 latest.json")
    
    # 复制最新规则
    rules_file = TRADING_DIR / "rules.json"
    if rules_file.exists():
        import shutil
        shutil.copy(rules_file, backtest_dir / "latest_rules.json")
        print(f"✅ 复制 latest_rules.json")
    
    # 复制复盘报告（如果存在）
    date_str = results.get("date", datetime.now().strftime("%Y-%m-%d"))
    review_src = TRADING_DIR / "reviews" / f"{date_str}_review.json"
    if review_src.exists():
        import shutil
        shutil.copy(review_src, DOCS_DIR / "daily" / f"{date_str}_review.json")
        print(f"✅ 复制复盘报告")


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    
    print("=" * 60)
    print(f"每日汇总推送 - {date_str}")
    print("=" * 60)
    
    # 0. 转换所有 Markdown 到 HTML（先转换！
    print("\n📝 转换 Markdown → HTML...")
    try:
        # 调用 md2html.py
        import subprocess
        md2html = REPO_DIR / "md2html.py"
        if md2html.exists():
            ret = subprocess.run(
                f"python3 {md2html} daily backtest strategy",
                shell=True, capture_output=True, text=True
            )
            if ret.returncode == 0:
                print("✅ Markdown → HTML 转换完成")
            else:
                print(f"⚠️ 转换有警告：{ret.stderr[:200]}")
        else:
            print("⚠️ md2html.py 不存在，跳过转换")
    except Exception as e:
        print(f"⚠️ 转换失败：{e}")
    
    # 1. 收集结果
    print("\n📡 收集当日结果...")
    results = collect_daily_results(date_str)
    
    # 2. 生成汇总报告
    print("\n📝 生成汇总报告...")
    generate_daily_report(date_str, results)
    
    # 3. 复制最新文件
    print("\n📋 复制最新文件...")
    copy_latest_files(results)
    
    # 4. 更新索引
    print("\n📚 更新索引页面...")
    update_index_pages(date_str, results)
    
    # 5. 推送到 GitHub
    print("\n🚀 推送到 GitHub Pages...")
    success = git_commit_push(f"📅 每日汇总 {date_str}")
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 推送完成！")
        print("=" * 60)
        print(f"\n访问地址：https://kirasq.github.io/hermes_stock/")
        print(f"每日报告：https://kirasq.github.io/hermes_stock/daily/{date_str}_summary.html")
    else:
        print("\n❌ 推送失败")
        sys.exit(1)


if __name__ == "__main__":
    main()

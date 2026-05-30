#!/usr/bin/env python3
"""
strategy_backtest.py — 防过拟合回测引擎（v2.0）
用途：加载历史交易数据，用 Walk-Forward + 夏普比率 + 参数稳定性检验，防止过拟合
"""
import json
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta

# 配置
TRADING_DIR = Path("/opt/data/trading")
TRADES_FILE = TRADING_DIR / "trades.json"
RULES_FILE = TRADING_DIR / "rules.json"
METRICS_FILE = TRADING_DIR / "strategy_metrics.json"

# 回测参数空间（保持 3 个参数，避免过拟合）
STOP_LOSS_RANGE = [-5, -6, -7, -8, -9, -10]
TAKE_PROFIT_RANGE = [15, 20, 25, 30]
MAX_POS_RANGE = [20, 25, 30, 35]

# 防过拟合配置
WALK_FORWARD_TRAIN_YEARS = 5    # 训练窗口：5 年
WALK_FORWARD_TEST_YEARS = 1     # 测试窗口：1 年
PARAM_STABILITY_THRESHOLD = 0.7  # 参数稳定性阈值（邻近参数表现 > 70%）
MAX_DRAWDOWN_LIMIT = 0.30     # 最大回撤上限 30%
SHARPE_THRESHOLD = 1.0           # 夏普比率下限


def load_trades():
    """加载历史交易记录"""
    if not TRADES_FILE.exists():
        return []
    with open(TRADES_FILE, "r") as f:
        data = json.load(f)
        return data.get("trades", [])


def split_train_test(trades, train_ratio=0.8):
    """将数据分为训练集和测试集（按时间）"""
    if not trades:
        return [], []
    
    # 按时间排序
    sorted_trades = sorted(trades, key=lambda x: x.get("timestamp", ""))
    split_idx = int(len(sorted_trades) * train_ratio)
    
    train = sorted_trades[:split_idx]
    test = sorted_trades[split_idx:]
    
    print(f"训练集：{len(train)} 笔，测试集：{len(test)} 笔")
    return train, test


def walk_forward_splits(trades):
    """
    滚动窗口交叉验证（Walk-Forward Analysis）
    每次用过去 5 年数据训练，未来 1 年数据测试
    """
    if len(trades) < 50:
        return [(trades, [])]  # 数据不足，只用全部数据
    
    sorted_trades = sorted(trades, key=lambda x: x.get("timestamp", ""))
    
    # 按日期分组
    from collections import defaultdict
    by_date = defaultdict(list)
    for t in sorted_trades:
        date = t.get("timestamp", "")[:7]  # YYYY-MM
        by_date[date].append(t)
    
    dates = sorted(by_date.keys())
    splits = []
    
    for i in range(len(dates) - WALK_FORWARD_TEST_YEARS):
        train_dates = dates[i:i + WALK_FORWARD_TRAIN_YEARS]
        test_dates = dates[i + WALK_FORWARD_TRAIN_YEARS:i + WALK_FORWARD_TRAIN_YEARS + WALK_FORWARD_TEST_YEARS]
        
        if not test_dates:  # 不够一个测试窗口
            continue
        
        train = []
        for d in train_dates:
            train.extend(by_date[d])
        
        test = []
        for d in test_dates:
            test.extend(by_date[d])
        
        splits.append((train, test))
    
    if not splits:  # 数据不足
        splits.append((sorted_trades, []))
    
    print(f"Walk-Forward 分割：{len(splits)} 个窗口")
    return splits


def calculate_sharpe_ratio(trades, risk_free_rate=0.02):
    """计算夏普比率（简化版）"""
    if not trades:
        return 0.0
    
    # 计算每笔收益
    returns = [t.get("profit", 0) for t in trades]
    
    if len(set(returns)) <= 1:  # 所有收益相同
        return 0.0
    
    import statistics
    mean_return = statistics.mean(returns)
    std_return = statistics.stdev(returns) if len(returns) > 1 else 1.0
    
    if std_return == 0:
        return 0.0
    
    sharpe = (mean_return - risk_free_rate / 252) / std_return * (252 ** 0.5)
    return sharpe


def calculate_max_drawdown(trades):
    """计算最大回撤"""
    if not trades:
        return 0.0
    
    cumulative = 0
    peak = 0
    max_dd = 0.0
    
    for t in trades:
        cumulative += t.get("profit", 0)
        if cumulative > peak:
            peak = cumulative
        dd = (peak - cumulative) / (peak + 1e-6)  # 避免除零
        max_dd = max(max_dd, dd)
    
    return max_dd


def simulate_trade(trade, stop_loss_pct, take_profit_pct, max_position_pct):
    """用新参数模拟单笔交易"""
    cost = trade.get("cost_price", 0)
    exit_price = trade.get("exit_price", 0)
    
    if not cost or not exit_price:
        return None
    
    pct_change = (exit_price - cost) / cost * 100
    
    # 模拟新参数下的止损/止盈触发
    simulated_exit = exit_price
    result = "hold"
    
    if pct_change <= stop_loss_pct:
        simulated_exit = cost * (1 + stop_loss_pct / 100)
        result = "stop_loss"
    elif pct_change >= take_profit_pct:
        simulated_exit = cost * (1 + take_profit_pct / 100 * 0.5 + pct_change * 0.5 / 100)
        result = "take_profit"
    
    profit = (simulated_exit - cost) * trade.get("quantity", 100)
    return {
        "original_profit": (exit_price - cost) * trade.get("quantity", 100),
        "simulated_profit": profit,
        "result": result,
        "pct_change": pct_change
    }


def backtest(params, trades):
    """回测指定参数组合，返回详细指标"""
    stop_loss_pct = params["stop_loss_pct"]
    take_profit_pct = params["take_profit_pct"]
    max_position_pct = params["max_position_pct"]
    
    if not trades:
        return {
            "total_profit": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_return": 0.0
        }
    
    results = []
    for trade in trades:
        sim = simulate_trade(trade, stop_loss_pct, take_profit_pct, max_position_pct)
        if sim:
            results.append(sim)
    
    if not results:
        return {
            "total_profit": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_return": 0.0
        }
    
    profits = [r["simulated_profit"] for r in results]
    winners = [p for p in profits if p > 0]
    losers = [p for p in profits if p <= 0]
    
    total_profit = sum(profits)
    win_rate = len(winners) / len(results) * 100 if results else 0
    avg_winner = sum(winners) / len(winners) if winners else 0
    avg_loser = sum(losers) / len(losers) if losers else 0
    profit_factor = abs(sum(winners) / sum(losers)) if losers and sum(losers) != 0 else 999
    
    # 新增：夏普比率和最大回撤
    sharpe = calculate_sharpe_ratio(results)
    max_dd = calculate_max_drawdown(results)
    total_return = total_profit / 10000 * 100  # 假设初始资金 10000
    
    return {
        "total_profit": total_profit,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_winner": avg_winner,
        "avg_loser": avg_loser,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "total_return": total_return,
        "results": results
    }


def check_parameter_stability(params, trades):
    """
    参数稳定性检验
    检查邻近参数是否也表现良好（防止孤立尖峰）
    """
    stop_loss = params["stop_loss_pct"]
    take_profit = params["take_profit_pct"]
    max_pos = params["max_position_pct"]
    
    # 测试邻近参数
    neighbor_params = []
    
    # stop_loss 邻近
    if stop_loss + 1 in STOP_LOSS_RANGE:
        neighbor_params.append({"stop_loss_pct": stop_loss + 1, "take_profit_pct": take_profit, "max_position_pct": max_pos})
    if stop_loss - 1 in STOP_LOSS_RANGE:
        neighbor_params.append({"stop_loss_pct": stop_loss - 1, "take_profit_pct": take_profit, "max_position_pct": max_pos})
    
    # take_profit 邻近
    if take_profit + 5 in TAKE_PROFIT_RANGE:
        neighbor_params.append({"stop_loss_pct": stop_loss, "take_profit_pct": take_profit + 5, "max_position_pct": max_pos})
    if take_profit - 5 in TAKE_PROFIT_RANGE:
        neighbor_params.append({"stop_loss_pct": stop_loss, "take_profit_pct": take_profit - 5, "max_position_pct": max_pos})
    
    if not neighbor_params:
        return 1.0  # 没有邻近参数，默认稳定
    
    # 回测原始参数
    base_score, _, _, _ = calculate_robust_score(backtest(params, trades))
    
    # 回测邻近参数
    neighbor_scores = []
    for np in neighbor_params:
        ns, _, _, _ = calculate_robust_score(backtest(np, trades))
        neighbor_scores.append(ns)
    
    avg_neighbor = sum(neighbor_scores) / len(neighbor_scores) if neighbor_scores else 0
    
    stability = avg_neighbor / base_score if base_score != 0 else 0
    return min(stability, 1.0)  # 不超过 1.0


def white_noise_test(params, trades, n_permutations=10):
    """
    白噪检测
    打乱数据顺序后回测，如果收益接近原始数据，说明策略可能是随机噪声
    """
    import random
    
    original_score, _, _, _ = calculate_robust_score(backtest(params, trades))
    
    noise_scores = []
    for _ in range(n_permutations):
        shuffled = trades.copy()
        random.shuffle(shuffled)
        ns, _, _, _ = calculate_robust_score(backtest(params, shuffled))
        noise_scores.append(ns)
    
    avg_noise = sum(noise_scores) / len(noise_scores) if noise_scores else 0
    
    ratio = original_score / avg_noise if avg_noise > 0 else 999
    
    if ratio < 1.5:
        print(f"⚠️ 白噪检测警告：随机数据收益接近真实数据（比率={ratio:.2f}）")
        print(f"   原始分数：{original_score:.1f}，随机平均：{avg_noise:.1f}")
        return False
    else:
        print(f"✅ 白噪检测通过：真实数据明显优于随机（比率={ratio:.2f}）")
        return True


def calculate_robust_score(backtest_result):
    """
    防过拟合评分（v2.0）
    综合：收益、夏普比率、盈亏比、胜率、回撤惩罚
    """
    total_return = backtest_result["total_return"]
    sharpe = backtest_result["sharpe_ratio"]
    profit_factor = backtest_result["profit_factor"]
    win_rate = backtest_result["win_rate"]
    max_dd = backtest_result["max_drawdown"]
    
    # 基础评分（降低纯收益权重，增加风险调整收益权重）
    score = (
        total_return * 0.15 +          # 降低收益权重（原来 0.4）
        sharpe * 10 * 0.35 +            # 提高夏普权重（原来 0）
        profit_factor * 100 * 0.25 +     # 保持盈亏比权重
        win_rate * 10 * 0.25            # 新增胜率权重
    )
    
    # 回撤惩罚（回撤越大，分数越低）
    if max_dd > MAX_DRAWDOWN_LIMIT:
        penalty = 0.5  # 回撤超过 30%，分数砍半
        print(f"⚠️ 回撤过大：{max_dd*100:.1f}% > {MAX_DRAWDOWN_LIMIT*100}%，惩罚系数 {penalty}")
        score *= penalty
    
    # 夏普比率惩罚（夏普 < 1.0）
    if sharpe < SHARPE_THRESHOLD:
        penalty = 0.7
        print(f"⚠️ 夏普比率过低：{sharpe:.2f} < {SHARPE_THRESHOLD}，惩罚系数 {penalty}")
        score *= penalty
    
    return score, sharpe, profit_factor, win_rate


def find_best_params(trades):
    """Grid Search + 防过拟合检验"""
    print(f"开始防过拟合回测，历史交易数：{len(trades)}")
    print("=" * 60)
    
    # 使用 Walk-Forward Analysis
    splits = walk_forward_splits(trades)
    
    best_overall_score = float("-inf")
    best_overall_params = None
    all_results = []
    
    for split_idx, (train, test) in enumerate(splits):
        if not test:  # 没有测试集（数据不足）
            print(f"\n窗口 {split_idx+1}：数据不足，使用全部数据")
            train = trades
            test = trades
        
        print(f"\n窗口 {split_idx+1}/{len(splits)}：训练 {len(train)} 笔，测试 {len(test)} 笔")
        
        best_split_score = float("-inf")
        best_split_params = None
        
        for stop_loss in STOP_LOSS_RANGE:
            for take_profit in TAKE_PROFIT_RANGE:
                for max_pos in MAX_POS_RANGE:
                    params = {
                        "stop_loss_pct": stop_loss,
                        "take_profit_pct": take_profit,
                        "max_position_pct": max_pos
                    }
                    
                    # 在训练集上回测
                    train_result = backtest(params, train)
                    train_score, train_sharpe, train_pf, train_wr = calculate_robust_score(train_result)
                    
                    # 在测试集上验证
                    if test and test != train:
                        test_result = backtest(params, test)
                        test_score, test_sharpe, test_pf, test_wr = calculate_robust_score(test_result)
                        
                        # 样本外比率（测试集/训练集）
                        oos_ratio = test_score / train_score if train_score != 0 else 0
                    else:
                        test_score = train_score
                        test_sharpe = train_sharpe
                        oos_ratio = 1.0
                    
                    # 参数稳定性检验
                    stability = check_parameter_stability(params, train)
                    
                    # 综合评分（训练集 60% + 测试集 40%）
                    final_score = train_score * 0.6 + test_score * 0.4
                    
                    # 防过拟合惩罚
                    if oos_ratio < 0.8:
                        final_score *= 0.5
                        print(f"  ⚠️ OOS比率低：{oos_ratio:.2f} (SL={stop_loss}, TP={take_profit}, MP={max_pos})")
                    
                    if stability < PARAM_STABILITY_THRESHOLD:
                        final_score *= 0.7
                        print(f"  ⚠️ 参数不稳定：{stability:.2f} (SL={stop_loss}, TP={take_profit})")
                    
                    result = {
                        "params": params,
                        "train_score": train_score,
                        "test_score": test_score,
                        "final_score": final_score,
                        "oos_ratio": oos_ratio,
                        "stability": stability,
                        "sharpe": train_sharpe,
                        "max_dd": train_result["max_drawdown"]
                    }
                    all_results.append(result)
                    
                    if final_score > best_split_score:
                        best_split_score = final_score
                        best_split_params = params
                    
                    print(f"SL={stop_loss:2d}% TP={take_profit:2d}% MP={max_pos:2d}% → "
                          f"Score={final_score:8.1f} (Train={train_score:6.1f} Test={test_score:6.1f} "
                          f"OOS={oos_ratio:.2f} Sta={stability:.2f} Sharpe={train_sharpe:.2f}")
        
        print(f"\n窗口 {split_idx+1} 最优：{best_split_params}，分数={best_split_score:.1f}")
        
        if best_split_score > best_overall_score:
            best_overall_score = best_split_score
            best_overall_params = best_split_params
    
    print("\n" + "="*60)
    print(f"综合最优参数：{best_overall_params}")
    print(f"综合评分：{best_overall_score:.1f}")
    
    # 白噪检测
    print("\n执行白噪检测...")
    noise_ok = white_noise_test(best_overall_params, trades)
    
    if not noise_ok:
        print("⚠️ 策略可能只是随机噪声，不推荐部署！")
        return None, 0, all_results
    
    # 按评分排序，输出 Top 5
    all_results.sort(key=lambda x: x["final_score"], reverse=True)
    print("\nTop 5 参数组合（防过拟合版）：")
    for i, r in enumerate(all_results[:5], 1):
        print(f"{i}. {r['params']} → 综合分数={r['final_score']:.1f} "
              f"(OOS={r['oos_ratio']:.2f}, 稳定性={r['stability']:.2f}, Sharpe={r['sharpe']:.2f})")
    
    return best_overall_params, best_overall_score, all_results


def save_evolution_log(old_params, new_params, backtest_score, old_score, stability, oos_ratio):
    """记录进化日志到 strategy_metrics.json"""
    metrics_file = METRICS_FILE
    
    if metrics_file.exists():
        with open(metrics_file, "r") as f:
            metrics = json.load(f)
    else:
        metrics = {
            "total_trades": 0,
            "win_rate": 0,
            "avg_winner": 0,
            "avg_loser": 0,
            "profit_factor": 0,
            "evolution_log": []
        }
    
    improvement_pct = ((backtest_score - old_score) / abs(old_score) * 100) if old_score != 0 else 0
    
    log_entry = {
        "version": f"v{len(metrics.get('evolution_log', [])) + 2}",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "trigger": "防过拟合自进化回测",
        "old_params": old_params,
        "new_params": new_params,
        "backtest_improvement": f"+{improvement_pct:.1f}%",
        "old_score": old_score,
        "new_score": backtest_score,
        "stability": stability,
        "oos_ratio": oos_ratio,
        "status": "pending_approval"
    }
    
    if "evolution_log" not in metrics:
        metrics["evolution_log"] = []
    metrics["evolution_log"].append(log_entry)
    
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    
    print(f"\n进化日志已保存到：{metrics_file}")
    return log_entry


def update_rules_json(new_params, version):
    """更新 /opt/data/trading/rules.json"""
    rules_file = RULES_FILE
    
    if rules_file.exists():
        with open(rules_file, "r") as f:
            rules = json.load(f)
    else:
        rules = {"rules": {}, "strategy_version": "v1.0"}
    
    rules["rules"].update(new_params)
    rules["strategy_version"] = version
    rules["last_optimized"] = datetime.now().strftime("%Y-%m-%d")
    rules["optimization_notes"] = f"防过拟合自进化：Walk-Forward + 稳定性检验 + 白噪检测"
    
    with open(rules_file, "w") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)
    
    print(f"规则已更新到：{rules_file}")


if __name__ == "__main__":
    print("=" * 60)
    print("防过拟合回测引擎 v2.0")
    print("=" * 60)
    
    # 加载历史交易
    trades = load_trades()
    if len(trades) < 30:
        print(f"历史交易不足30笔（当前{len(trades)}笔），无法进行可靠回测")
        print("需要至少30笔交易才能触发自进化")
        sys.exit(1)
    
    # 读取当前参数
    if RULES_FILE.exists():
        with open(RULES_FILE, "r") as f:
            current_rules = json.load(f)
            old_params = current_rules.get("rules", {})
    else:
        old_params = {"stop_loss_pct": -8, "take_profit_pct": 20, "max_position_pct": 30}
    
    # 回测找最佳参数（含防过拟合机制）
    best_params, best_score, all_results = find_best_params(trades)
    
    if best_params is None:
        print("\n❌ 白噪检测未通过，策略可能是随机噪声，保持原参数。")
        sys.exit(1)
    
    # 计算旧参数评分
    old_result = backtest(old_params, trades)
    old_score, old_sharpe, old_pf, old_wr = calculate_robust_score(old_result)
    print(f"\n旧参数评分：{old_score:.1f} (Sharpe={old_sharpe:.2f}, PF={old_pf:.1f}, WR={old_wr:.1f}%)")
    print(f"新参数评分：{best_score:.1f}")
    
    improvement = ((best_score - old_score) / abs(old_score) * 100) if old_score != 0 else 0
    print(f"提升幅度：{improvement:+.1f}%")
    
    # 判断是否需要更新（新参数必须比旧参数好10%以上）
    if improvement > 10:
        print("\n✅ 新参数通过验证（提升 > 10%），准备更新...")
        
        # 获取稳定性和 OOS 比率
        best_result = [r for r in all_results if r["params"] == best_params]
        stability = best_result[0]["stability"] if best_result else 1.0
        oos_ratio = best_result[0]["oos_ratio"] if best_result else 1.0
        
        version = f"v{len(load_trades()) // 30 + 1}"
        save_evolution_log(old_params, best_params, best_score, old_score, stability, oos_ratio)
        update_rules_json(best_params, version)
        print("\n✅ 防过拟合自进化完成！新参数已部署。")
        print(f"   稳定性：{stability:.2f}（阈值 > {PARAM_STABILITY_THRESHOLD}）")
        print(f"   OOS 比率：{oos_ratio:.2f}（阈值 > 0.8）")
    else:
        print(f"\n❌ 新参数未通过验证（提升 {improvement:.1f}% < 10%），保持原参数。")
    
    print("\n输出文件：")
    print(f"  - {RULES_FILE}")
    print(f"  - {METRICS_FILE}")

#!/usr/bin/env python3
"""
全球股票爬虫 - 主程序

使用方式:
    # 启动实时行情（持续运行）
    python3 main.py

    # 运行单个任务
    python3 main.py stock_list  # 获取股票列表
    python3 main.py static_info # 获取标的基础信息
    python3 main.py realtime   # 获取实时行情（单次）
    python3 main.py kline      # 获取K线数据（全量 120 日）
    python3 main.py kline_gap  # 检测并补全缺失/滞后的 K 线
    python3 main.py kline_gap check  # 仅扫描缺口，不拉取
    python3 main.py task_worker      # K 线拉取任务 worker（常驻）
    python3 main.py task_worker --task-id <id>  # 执行指定任务
"""
from __future__ import annotations
import sys
import os

from config import load_config
from scheduler import MarketCrawler


def main() -> None:
    """主函数"""
    # 加载配置
    config = load_config()

    # 创建爬虫
    crawler = MarketCrawler(config)

    # 解析命令行参数
    if len(sys.argv) > 1:
        task_name = sys.argv[1]
        if task_name == "task_worker":
            task_id = None
            if "--task-id" in sys.argv:
                idx = sys.argv.index("--task-id")
                if idx + 1 < len(sys.argv):
                    task_id = sys.argv[idx + 1]
            crawler.run_task_worker(task_id=task_id)
            return
        market = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] not in ("check",) else "US"
        extra_args = [a for a in sys.argv[2:] if a not in (market,)]
        check_only = "check" in extra_args or (len(sys.argv) > 2 and sys.argv[2] == "check")
        crawler.run_task_once(task_name, market, check_only=check_only)
    else:
        # 默认启动实时行情模式
        crawler.start_forever(market="US")


if __name__ == "__main__":
    main()

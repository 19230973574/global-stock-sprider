"""
历史K线获取任务
获取并保存历史K线数据
"""
from __future__ import annotations
from typing import List

from .base_task import BaseTask, TaskResult
from models import KLine


class KlineHistoryTask(BaseTask):
    """历史K线获取任务"""

    def __init__(
        self,
        storage_manager,
        data_client,
        market: str = "US",
        period: str = "1d",
        kline_count: int = 90
    ):
        """
        初始化任务

        Args:
            storage_manager: 存储管理器
            data_client: 数据客户端
            market: 市场 (US/A/HK)
            period: K线周期 (1d/1w/1M)
            kline_count: 每只股票获取的K线数量
        """
        super().__init__(f"KlineHistory-{market}-{period}", storage_manager, data_client)
        self.market = market
        self.period = period
        self.kline_count = kline_count

    def run(self) -> TaskResult:
        """
        执行任务

        Returns:
            TaskResult
        """
        # 1. 从 Redis 获取所有股票列表
        codes = self.storage.redis.get_stock_list(self.market)

        if not codes:
            return TaskResult(False, error=f"未找到{self.market}股票列表，请先运行 StockList 任务")

        total_klines = 0
        total_errors = 0

        # 2. 逐只获取K线
        for code in codes:
            try:
                klines: List[KLine] = self.data_client.get_klines(
                    code,
                    self.period,
                    self.kline_count,
                    self.market
                )

                if klines:
                    saved = self.storage.mongo.save_klines(klines, self.market, is_today=False)
                    total_klines += saved

            except Exception as e:
                total_errors += 1
                if total_errors <= 10:  # 只打印前10个错误
                    print(f"⚠️  获取 {code} K线失败: {e}")

        print(f"\n📊 总计: 处理 {len(codes)} 只股票, 成功 {len(codes) - total_errors} 只, 失败 {total_errors} 只")

        return TaskResult(
            True,
            data={
                "market": self.market,
                "period": self.period,
                "processed": len(codes),
                "total_klines": total_klines,
                "errors": total_errors
            }
        )

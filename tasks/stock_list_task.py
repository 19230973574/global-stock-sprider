"""
股票列表获取任务
定期更新股票列表
"""
from __future__ import annotations
from typing import List

from .base_task import BaseTask, TaskResult
from models import Stock


class StockListTask(BaseTask):
    """股票列表获取任务"""

    def __init__(self, storage_manager, data_client, market: str = "US"):
        """
        初始化任务

        Args:
            storage_manager: 存储管理器
            data_client: 数据客户端
            market: 市场 (US/A/HK)
        """
        super().__init__(f"StockList-{market}", storage_manager, data_client)
        self.market = market

    def run(self) -> TaskResult:
        """
        执行任务

        Returns:
            TaskResult
        """
        # 1. 获取股票列表
        stocks: List[Stock] = self.data_client.get_stock_list()

        if not stocks:
            return TaskResult(False, error=f"未获取到{self.market}股票列表")

        # 2. 保存股票信息到 MongoDB
        mongo_count = self.storage.mongo.save_stocks(stocks, self.market)

        # 3. 保存股票代码列表到 Redis
        codes = [s.code for s in stocks]
        redis_count = self.storage.redis.save_stock_list(codes, self.market)

        return TaskResult(
            True,
            data={
                "market": self.market,
                "count": len(stocks),
                "mongo_saved": mongo_count,
                "redis_saved": redis_count
            }
        )

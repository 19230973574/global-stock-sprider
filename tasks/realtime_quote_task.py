"""
实时行情获取任务
定期获取实时行情数据
"""
from __future__ import annotations
from typing import List

from .base_task import BaseTask, TaskResult
from models import Quote


class RealtimeQuoteTask(BaseTask):
    """实时行情获取任务"""

    def __init__(self, storage_manager, data_client, market: str = "US"):
        """
        初始化任务

        Args:
            storage_manager: 存储管理器
            data_client: 数据客户端
            market: 市场 (US/A/HK)
        """
        super().__init__(f"RealtimeQuote-{market}", storage_manager, data_client)
        self.market = market

    def run(self) -> TaskResult:
        """
        执行任务

        Returns:
            TaskResult
        """
        # 1. 从 Redis 获取股票列表
        codes = self.storage.redis.get_stock_list(self.market)

        if not codes:
            return TaskResult(False, error=f"未找到{self.market}股票列表，请先运行 StockList 任务")

        # 2. 获取实时行情
        quotes: List[Quote] = self.data_client.get_quotes(codes, self.market)

        if not quotes:
            return TaskResult(False, error=f"未获取到{self.market}实时行情")

        # 3. 保存到 Redis
        saved_count = self.storage.redis.save_quotes(quotes, self.market)

        # 4. 打印预览
        print(f"\n📊 {self.market} 实时行情预览:")
        for quote in quotes[:5]:
            change_pct_str = f"{quote.change_pct:+.2f}%" if quote.change_pct else "N/A"
            print(f"   {quote.code:8} {quote.price:10} {change_pct_str:10}")

        return TaskResult(
            True,
            data={
                "market": self.market,
                "total_codes": len(codes),
                "fetched": len(quotes),
                "saved": saved_count
            }
        )

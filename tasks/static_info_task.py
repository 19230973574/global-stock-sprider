"""
标的基础信息获取任务
调用 LongPort static_info 接口，补充并更新股票基础信息
"""
from __future__ import annotations
from typing import List

from .base_task import BaseTask, TaskResult
from models import Stock


class StaticInfoTask(BaseTask):
    """标的基础信息获取任务"""

    def __init__(
        self,
        storage_manager,
        data_client,
        market: str = "US",
        batch_size: int = 500,
        codes: List[str] | None = None,
    ):
        super().__init__(f"StaticInfo-{market}", storage_manager, data_client)
        self.market = market
        self.batch_size = batch_size
        self.codes = codes

    def run(self) -> TaskResult:
        codes = self._resolve_codes()
        if not codes:
            return TaskResult(
                False,
                error=f"未找到{self.market}股票代码，请先运行 stock_list 任务",
            )

        stocks: List[Stock] = self.data_client.get_static_info(
            codes,
            market=self.market,
            batch_size=self.batch_size,
        )

        if not stocks:
            return TaskResult(False, error=f"未获取到{self.market}标的基础信息")

        mongo_count = self.storage.mongo.save_stocks(stocks, self.market)

        return TaskResult(
            True,
            data={
                "market": self.market,
                "requested": len(codes),
                "fetched": len(stocks),
                "mongo_saved": mongo_count,
            },
        )

    def _resolve_codes(self) -> List[str]:
        if self.codes:
            return self.codes

        codes = self.storage.redis.get_stock_list(self.market)
        if codes:
            return codes

        stocks = self.storage.mongo.get_stocks(self.market)
        return [item["code"] for item in stocks if item.get("code")]

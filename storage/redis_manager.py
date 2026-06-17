"""
Redis 数据管理器
统一管理 Redis 存储操作
"""
from __future__ import annotations
import json
from typing import List, Optional, Dict, Any
import redis

from models import Stock, Quote


class RedisManager:
    """Redis 数据管理器"""

    # Redis Key 前缀
    KEY_STOCK_LIST = "market:stock:list"
    KEY_QUOTE_PREFIX = "market:quote:latest:"
    KEY_STATUS = "market:crawler:status"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self) -> None:
        """连接 Redis"""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True
            )
            self.client.ping()
            print(f"✅ Redis 连接成功: {self.host}:{self.port}")
        except Exception as e:
            print(f"❌ Redis 连接失败: {e}")
            self.client = None

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.client is not None

    # ================ 股票列表 ================

    def save_stock_list(self, codes: List[str], market: str = "US") -> int:
        """
        保存股票列表

        Args:
            codes: 股票代码列表
            market: 市场 (US/A/HK)

        Returns:
            保存的数量
        """
        if not self.client:
            return 0

        key = f"{self.KEY_STOCK_LIST}:{market}"
        self.client.delete(key)
        if codes:
            self.client.sadd(key, *codes)

        count = self.client.scard(key)
        print(f"💾 已保存 {count} 只 {market} 股票代码到 Redis")
        return count

    def get_stock_list(self, market: str = "US") -> List[str]:
        """
        获取股票列表

        Args:
            market: 市场 (US/A/HK)

        Returns:
            股票代码列表
        """
        if not self.client:
            return []

        key = f"{self.KEY_STOCK_LIST}:{market}"
        codes = self.client.smembers(key)
        return sorted(list(codes))

    # ================ 实时行情 ================

    def save_quotes(self, quotes: List[Quote], market: str = "US") -> int:
        """
        批量保存实时行情

        Args:
            quotes: 行情数据列表
            market: 市场

        Returns:
            保存的数量
        """
        if not self.client:
            return 0

        count = 0
        for quote in quotes:
            key = f"{self.KEY_QUOTE_PREFIX}{quote.code}"
            data = {
                "code": quote.code,
                "price": str(quote.price) if quote.price else "",
                "change": str(quote.change) if quote.change else "",
                "change_pct": str(quote.change_pct) if quote.change_pct else "",
                "volume": str(quote.volume) if quote.volume else "",
                "timestamp": str(quote.timestamp) if quote.timestamp else ""
            }
            self.client.hset(key, mapping=data)
            self.client.expire(key, 3600)  # 1小时过期
            count += 1

        print(f"💾 已保存 {count} 条 {market} 实时行情到 Redis")
        return count

    def get_quote(self, code: str) -> Optional[Quote]:
        """
        获取单只股票的实时行情

        Args:
            code: 股票代码

        Returns:
            行情数据
        """
        if not self.client:
            return None

        key = f"{self.KEY_QUOTE_PREFIX}{code}"
        data = self.client.hgetall(key)

        if not data:
            return None

        return Quote(
            code=data.get("code", ""),
            price=float(data.get("price")) if data.get("price") else None,
            change=float(data.get("change")) if data.get("change") else None,
            change_pct=float(data.get("change_pct")) if data.get("change_pct") else None,
            volume=int(data.get("volume")) if data.get("volume") else None,
            timestamp=int(data.get("timestamp")) if data.get("timestamp") else None
        )

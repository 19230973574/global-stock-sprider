"""
MongoDB 数据管理
管理历史数据存储：股票列表、历史K线
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo import MongoClient, ASCENDING, UpdateOne
from pymongo.errors import DuplicateKeyError

from models import Stock, KLine
from .kline_task_manager import KlineTaskManager


class MongoDBManager:
    """MongoDB 数据管理器"""

    # 市场前缀映射
    MARKET_PREFIX = {
        "US": "us_",
        "A": "a_",
        "HK": "hk_"
    }

    def __init__(
        self, 
        uri: str, 
        db_name: str,
        fund_collection: str = "fund_info"
    ):
        """
        初始化 MongoDB 管理器

        Args:
            uri: MongoDB 连接 URI
            db_name: 数据库名称
            fund_collection: 基金信息集合名
        """
        self.uri = uri
        self.db_name = db_name
        self.fund_collection = fund_collection
        self.client: Optional[MongoClient] = None
        self.db = None
        self.kline_tasks: Optional[KlineTaskManager] = None
        self._init_connection()

    def _init_connection(self) -> None:
        """初始化 MongoDB 连接"""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self.kline_tasks = KlineTaskManager(self.db)
            self._init_indexes()
            print(f"✅ MongoDB 连接成功: {self.db_name}")
        except Exception as e:
            print(f"❌ MongoDB 连接失败: {e}")

    def _get_collection_name(self, market: str, data_type: str) -> str:
        """
        获取集合名称

        Args:
            market: 市场 (US/A/HK)
            data_type: 数据类型 (stock_info/kline_today/kline_history)

        Returns:
            集合名称
        """
        prefix = self.MARKET_PREFIX.get(market, "us_")
        return f"{prefix}{data_type}"

    def _init_indexes(self) -> None:
        """初始化所有集合的索引"""
        try:
            # 为每个市场创建索引
            for market in self.MARKET_PREFIX:
                # 股票信息索引
                stock_col = self.db[self._get_collection_name(market, "stock_info")]
                stock_col.create_index([('code', 1), ('market', 1)], unique=True)
                stock_col.create_index([('market', 1)])
                stock_col.create_index([('industry', 1), ('market', 1)])
                
                # K线历史索引
                kline_hist_col = self.db[self._get_collection_name(market, "kline_history")]
                kline_hist_col.create_index([('code', 1), ('market', 1), ('period', 1), ('date', -1)], unique=True)
                kline_hist_col.create_index([('code', 1), ('market', 1), ('period', 1)])
                kline_hist_col.create_index([('date', -1)])
                
                # K线当日索引
                kline_today_col = self.db[self._get_collection_name(market, "kline_today")]
                kline_today_col.create_index([('code', 1), ('market', 1), ('period', 1), ('date', -1)], unique=True)
                kline_today_col.create_index([('code', 1), ('market', 1)])
                
            print("✅ MongoDB 索引初始化完成")
        except Exception as e:
            print(f"⚠️  索引创建失败: {e}")

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.client is not None

    # ================ 股票信息 ================

    def save_stocks(self, stocks: List[Stock], market: str = "US") -> int:
        """
        批量保存股票信息

        Args:
            stocks: 股票信息列表
            market: 市场

        Returns:
            保存成功的数量
        """
        if self.db is None:
            print("❌ MongoDB 未连接")
            return 0

        collection = self.db[self._get_collection_name(market, "stock_info")]
        operations = []
        now = datetime.now().isoformat()

        for stock in stocks:
            doc = {
                "code": stock.code,
                "symbol": stock.symbol,
                "name": stock.name,
                "market": market,
                "exchange": stock.exchange,
                "industry": stock.industry,
                "market_cap": stock.market_cap,
                "listing_date": stock.listing_date,
                "name_cn": stock.name_cn,
                "name_en": stock.name_en,
                "name_hk": stock.name_hk,
                "currency": stock.currency,
                "lot_size": stock.lot_size,
                "total_shares": stock.total_shares,
                "circulating_shares": stock.circulating_shares,
                "hk_shares": stock.hk_shares,
                "eps": stock.eps,
                "eps_ttm": stock.eps_ttm,
                "bps": stock.bps,
                "dividend_yield": stock.dividend_yield,
                "stock_derivatives": stock.stock_derivatives,
                "board": stock.board,
                "updated_at": now
            }
            operations.append(
                UpdateOne(
                    {"code": stock.code, "market": market},
                    {"$set": doc},
                    upsert=True
                )
            )

        try:
            result = collection.bulk_write(operations, ordered=False)
            count = result.upserted_count + result.modified_count
            coll_name = self._get_collection_name(market, "stock_info")
            print(f"💾 已保存 {count} 条股票信息到 {coll_name}")
            return count
        except Exception as e:
            print(f"❌ 保存股票信息失败: {e}")
            return 0

    def get_stocks(self, market: str = "US") -> List[Dict]:
        """
        获取股票列表

        Args:
            market: 市场

        Returns:
            股票信息列表
        """
        if self.db is None:
            return []

        collection = self.db[self._get_collection_name(market, "stock_info")]
        query = {"market": market}
        return list(collection.find(query, {"_id": 0}))

    # ================ K线数据 ================

    def save_klines(self, klines: List[KLine], market: str = "US", is_today: bool = False, quiet: bool = False) -> int:
        """
        批量保存 K线数据

        Args:
            klines: K线数据列表
            market: 市场
            is_today: 是否为当日K线

        Returns:
            保存的数量
        """
        if self.db is None:
            print("❌ MongoDB 未连接")
            return 0

        data_type = "kline_today" if is_today else "kline_history"
        collection = self.db[self._get_collection_name(market, data_type)]
        operations = []
        now = datetime.now().isoformat()

        for kline in klines:
            doc = {
                "code": kline.code,
                "market": market,
                "period": kline.period,
                "date": kline.date,
                "open": kline.open,
                "high": kline.high,
                "low": kline.low,
                "close": kline.close,
                "volume": kline.volume,
                "turnover": kline.turnover,
                "change": kline.change,
                "change_pct": kline.change_pct,
                "updated_at": now
            }
            operations.append(
                UpdateOne(
                    {
                        "code": kline.code,
                        "market": market,
                        "period": kline.period,
                        "date": kline.date,
                    },
                    {"$set": doc},
                    upsert=True
                )
            )

        try:
            result = collection.bulk_write(operations, ordered=False)
            count = result.upserted_count + result.modified_count
            if not quiet:
                coll_name = self._get_collection_name(market, data_type)
                print(f"💾 已保存 {count} 条 K线数据到 {coll_name}")
            return count
        except Exception as e:
            print(f"❌ 保存 K线数据失败: {e}")
            return 0

    def get_klines(
        self,
        code: str,
        period: str = "1d",
        market: str = "US",
        is_today: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取 K线数据

        Args:
            code: 股票代码
            period: 周期
            market: 市场
            is_today: 是否获取当日K线
            limit: 返回条数

        Returns:
            K线数据列表
        """
        if self.db is None:
            return []

        data_type = "kline_today" if is_today else "kline_history"
        collection = self.db[self._get_collection_name(market, data_type)]
        query = {"code": code, "market": market, "period": period}
        return list(collection.find(query, {"_id": 0}).sort("date", -1).limit(limit))

    def get_kline_latest_by_code(
        self,
        market: str = "US",
        period: str = "1d",
    ) -> Dict[str, Dict[str, Any]]:
        """
        聚合每只股票在库中的最新 K 线日期与条数。

        Returns:
            {code: {"latest": "YYYY-MM-DD", "count": int}}
        """
        if self.db is None:
            return {}

        collection = self.db[self._get_collection_name(market, "kline_history")]
        pipeline = [
            {"$match": {"market": market, "period": period}},
            {"$group": {
                "_id": "$code",
                "latest": {"$max": "$date"},
                "count": {"$sum": 1},
            }},
        ]
        result: Dict[str, Dict[str, Any]] = {}
        for doc in collection.aggregate(pipeline, allowDiskUse=True):
            code = doc.get("_id")
            if not code:
                continue
            result[code] = {
                "latest": doc.get("latest"),
                "count": int(doc.get("count") or 0),
            }
        return result

    def get_kline_date_distribution(
        self,
        market: str = "US",
        period: str = "1d",
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        """统计各「最新交易日」上的股票数量（用于查看整体滞后情况）。"""
        if self.db is None:
            return []

        collection = self.db[self._get_collection_name(market, "kline_history")]
        pipeline = [
            {"$match": {"market": market, "period": period}},
            {"$group": {"_id": "$code", "latest": {"$max": "$date"}}},
            {"$group": {"_id": "$latest", "count": {"$sum": 1}}},
            {"$sort": {"_id": -1}},
            {"$limit": top_n},
        ]
        return list(collection.aggregate(pipeline, allowDiskUse=True))

"""
配置管理模块
"""
from __future__ import annotations
import os
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class LongPortConfig:
    """长桥 API 配置"""
    app_key: str = ""
    app_secret: str = ""
    access_token: str = ""
    region: str = "cn"
    quote_batch_size: int = 500


@dataclass
class RedisConfig:
    """Redis 配置"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0


@dataclass
class MongoConfig:
    """MongoDB 配置"""
    uri: str = "mongodb://admin:password@localhost:27017/db_global_stock?authSource=admin&directConnection=true"
    db_name: str = "db_global_stock"
    fund_collection: str = "fund_info"
    stock_collection: str = "us_stock_info"
    kline_collection: str = "us_kline_data"
    kline_today_collection: str = "us_kline_today"
    kline_history_collection: str = "us_kline_history"


@dataclass
class CrawlerConfig:
    """爬虫主配置"""
    longport: LongPortConfig
    redis: RedisConfig
    mongo: MongoConfig


def load_config(config_path: str = "config.json") -> CrawlerConfig:
    """
    加载配置

    Args:
        config_path: 配置文件路径

    Returns:
        CrawlerConfig
    """
    config_data: Dict[str, Any] = {}

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as e:
            print(f"⚠️  读取配置文件失败: {e}，将使用默认配置")

    # 长桥配置
    lp_data = config_data.get("longport", {})
    longport_config = LongPortConfig(
        app_key=lp_data.get("app_key", os.getenv("LONGPORT_APP_KEY", "")),
        app_secret=lp_data.get("app_secret", os.getenv("LONGPORT_APP_SECRET", "")),
        access_token=lp_data.get("access_token", os.getenv("LONGPORT_ACCESS_TOKEN", "")),
        region=lp_data.get("region", "cn"),
        quote_batch_size=int(lp_data.get("quote_batch_size", 500)),
    )

    # Redis 配置
    redis_data = config_data.get("redis", {})
    redis_config = RedisConfig(
        host=redis_data.get("host", "localhost"),
        port=redis_data.get("port", 6379),
        password=redis_data.get("password"),
        db=redis_data.get("db", 0)
    )

    # MongoDB 配置
    mongo_data = config_data.get("mongo", {})
    mongo_config = MongoConfig(
        uri=mongo_data.get("uri", os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27017/db_global_stock?authSource=admin&directConnection=true")),
        db_name=mongo_data.get("db_name", os.getenv("MONGO_DB_NAME", "db_global_stock")),
        fund_collection=mongo_data.get("fund_collection", "fund_info"),
        stock_collection=mongo_data.get("stock_collection", "stock_info"),
        kline_collection=mongo_data.get("kline_collection", "kline_data")
    )

    config = CrawlerConfig(
        longport=longport_config,
        redis=redis_config,
        mongo=mongo_config
    )
    
    # 调试输出
    print(f"📋 配置加载完成: MongoDB={config.mongo.db_name}")
    
    return config

"""
任务调度器
管理和调度爬虫任务
"""
from __future__ import annotations
import time
import signal
from datetime import datetime
from typing import Dict, Any

from config import load_config
from storage import RedisManager, MongoDBManager
from datasources import LongPortClient
from tasks import StockListTask, RealtimeQuoteTask, KlineHistoryTask, StaticInfoTask, KlineGapTask, KlineRangeFetchTask


class StorageManager:
    """存储管理器 - 统一管理所有存储
    Redis: 实时行情、股票代码列表
    MongoDB: 股票信息、历史K线
    """

    def __init__(self, redis: RedisManager, mongo: MongoDBManager):
        self.redis = redis
        self.mongo = mongo


class MarketCrawler:
    """市场爬虫调度器"""

    def __init__(self, config):
        """
        初始化

        Args:
            config: 配置对象
        """
        self.config = config
        self.running = False
        self.storage = None
        self.data_client = None
        self._init_components()

    def _init_components(self) -> None:
        """初始化组件"""
        # 初始化存储
        print("🔧 初始化存储组件...")
        redis = RedisManager(
            host=self.config.redis.host,
            port=self.config.redis.port,
            password=self.config.redis.password,
            db=self.config.redis.db
        )
        mongo = MongoDBManager(
            uri=self.config.mongo.uri,
            db_name=self.config.mongo.db_name,
            fund_collection=self.config.mongo.fund_collection
        )
        self.storage = StorageManager(redis, mongo)

        # 初始化数据客户端
        print("🔧 初始化数据客户端...")
        self.data_client = LongPortClient(
            app_key=self.config.longport.app_key,
            app_secret=self.config.longport.app_secret,
            access_token=self.config.longport.access_token,
            region=self.config.longport.region
        )

    def run_task_once(self, task_name: str, market: str = "US", **options) -> Any:
        """
        运行单个任务一次

        Args:
            task_name: 任务名称
            market: 市场
            **options: 任务可选参数，如 check_only=True

        Returns:
            任务结果
        """
        check_only = bool(options.get("check_only"))
        task_map = {
            "stock_list": lambda: StockListTask(self.storage, self.data_client, market),
            "static_info": lambda: StaticInfoTask(
                self.storage,
                self.data_client,
                market,
                batch_size=min(self.config.longport.quote_batch_size, 500),
            ),
            "realtime": lambda: RealtimeQuoteTask(self.storage, self.data_client, market),
            "kline": lambda: KlineHistoryTask(self.storage, self.data_client, market, "1d", 120),
            "kline_gap": lambda: KlineGapTask(
                self.storage,
                self.data_client,
                market,
                "1d",
                120,
                check_only=check_only,
            ),
        }

        if task_name not in task_map:
            print(f"❌ 未知任务: {task_name}")
            return None

        print(f"\n🎯 执行 {market} 市场任务: {task_name}")
        task = task_map[task_name]()
        return task.execute()

    def start_forever(self, market: str = "US") -> None:
        """
        启动持续运行模式（实时行情）

        Args:
            market: 市场
        """
        print("\n" + "="*80)
        print(f"🚀 启动 {market} 市场实时行情爬虫 (持续模式)")
        print("="*80)

        # 先运行一次股票列表初始化
        self.run_task_once("stock_list", market)

        self.running = True

        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print(f"\n⏰ 开始循环获取实时行情 (间隔 3 秒)...")
        print("💡 按 Ctrl+C 停止\n")

        try:
            while self.running:
                self.run_task_once("realtime", market)
                time.sleep(3)
        except Exception as e:
            print(f"\n❌ 运行出错: {e}")
        finally:
            self.stop()

    def _signal_handler(self, signum, frame) -> None:
        """
        信号处理

        Args:
            signum: 信号编号
            frame: 栈帧
        """
        print(f"\n⚠️  收到信号 {signum}，正在停止...")
        self.running = False

    def stop(self) -> None:
        """停止爬虫"""
        print("\n📦 正在停止...")
        self.running = False
        print("✅ 爬虫已停止")
        print("="*80 + "\n")

    def run_task_worker(self, poll_seconds: int = 5, task_id: str | None = None) -> None:
        """
        K 线拉取任务 worker：轮询 kline_data_tasks 并执行。
        """
        import signal

        print("\n" + "=" * 80)
        print("🚀 启动 K 线任务 Worker")
        print("=" * 80)

        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            while self.running:
                if task_id:
                    task = self.storage.mongo.kline_tasks.claim_by_id(task_id)
                    if not task:
                        print(f"❌ 任务 {task_id} 不存在或不在 PENDING 状态")
                        break
                else:
                    task = self.storage.mongo.kline_tasks.claim_next_pending()

                if not task:
                    time.sleep(poll_seconds)
                    continue

                print(f"\n📋 执行任务: {task.get('_id')}")
                KlineRangeFetchTask(self.storage, self.data_client, task).execute()
                if task_id:
                    break
        except Exception as e:
            print(f"\n❌ Task Worker 出错: {e}")
        finally:
            self.stop()

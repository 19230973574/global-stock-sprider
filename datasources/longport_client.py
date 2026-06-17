"""
长桥 API 客户端
封装与长桥 OpenAPI 的交互
"""
from __future__ import annotations
import os
from typing import Dict, List
from datetime import datetime, timedelta

from models import Stock, Quote, KLine


class LongPortClient:
    """长桥 API 客户端"""

    def __init__(
        self,
        app_key: str = "",
        app_secret: str = "",
        access_token: str = "",
        region: str = "cn"
    ):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = access_token
        self.region = region
        self._quote_context = None
        self._init_client()

    def _init_client(self) -> None:
        """初始化长桥客户端"""
        try:
            from longport.openapi import Config, QuoteContext

            if self.region:
                os.environ["LONGPORT_REGION"] = self.region

            config = Config(
                app_key=self.app_key,
                app_secret=self.app_secret,
                access_token=self.access_token,
                enable_overnight=True
            )

            self._quote_context = QuoteContext(config)
            print("✅ 长桥连接成功")
        except Exception as e:
            print(f"⚠️ 长桥初始化失败: {e}")
            self._quote_context = None

    def is_connected(self) -> bool:
        """检查是否连接到长桥API"""
        return self._quote_context is not None

    # ================ 股票列表 ================

    def get_stock_list(self) -> List[Stock]:
        """
        获取美股股票列表

        Returns:
            股票列表
        """
        stocks = []
        
        if not self._quote_context:
            print("❌ 长桥未连接，无法获取股票列表")
            return stocks
        
        try:
            from longport.openapi import Market, SecurityListCategory
            
            print("📡 正在从长桥获取美股标的列表...")
            resp = self._quote_context.security_list(Market.US, SecurityListCategory.Overnight)
            
            if resp:
                for security in resp:
                    symbol = str(security.symbol) if security.symbol else ""
                    if not symbol:
                        continue
                        
                    # 提取代码
                    if "." in symbol:
                        code = symbol.split(".")[0]
                    else:
                        code = symbol
                        
                    # 获取名称（优先中文）
                    name = ""
                    if hasattr(security, 'name_cn') and security.name_cn:
                        name = security.name_cn
                    elif hasattr(security, 'name_en') and security.name_en:
                        name = security.name_en
                    elif hasattr(security, 'name_hk') and security.name_hk:
                        name = security.name_hk
                    else:
                        name = code
                        
                    stocks.append(Stock(
                        code=code,
                        symbol=symbol,
                        name=name,
                        market="US",
                        exchange="NASDAQ"
                    ))
                    
            print(f"✅ 从长桥获取到 {len(stocks)} 只美股")
            return stocks
            
        except Exception as e:
            print(f"❌ 从长桥获取标的列表失败: {e}")
            import traceback
            traceback.print_exc()
            return stocks

    # ================ 实时行情 ================

    def get_quotes(self, codes: List[str], market: str = "US", batch_size: int = 100) -> List[Quote]:
        """
        获取实时行情

        Args:
            codes: 股票代码列表
            market: 市场
            batch_size: 每批请求的数量

        Returns:
            行情数据列表
        """
        quotes: List[Quote] = []

        if not self._quote_context:
            print("❌ 长桥未连接，无法获取实时行情")
            return quotes

        try:
            # 分批处理
            total_batches = (len(codes) + batch_size - 1) // batch_size
            print(f"📊 开始获取 {len(codes)} 只股票的行情，共 {total_batches} 批")
            
            for i in range(0, len(codes), batch_size):
                batch_codes = codes[i:i + batch_size]
                symbols = []
                for code in batch_codes:
                    if market == "US":
                        symbols.append(f"{code}.US")
                    elif market == "HK":
                        symbols.append(f"{code}.HK")

                try:
                    resp = self._quote_context.quote(symbols)
                    
                    for quote_obj in resp:
                        symbol = str(quote_obj.symbol) if quote_obj.symbol else ""
                        if not symbol:
                            continue

                        # 提取代码
                        if "." in symbol:
                            code = symbol.split(".")[0]
                        else:
                            code = symbol

                        # 解析行情数据
                        quote = Quote(code=code, symbol=symbol)

                        # 最新价
                        if hasattr(quote_obj, 'last_done') and quote_obj.last_done:
                            quote.price = float(quote_obj.last_done)

                        # 昨收
                        if hasattr(quote_obj, 'prev_close') and quote_obj.prev_close:
                            quote.close = float(quote_obj.prev_close)

                        # 计算涨跌
                        if quote.price and quote.close and quote.close > 0:
                            quote.change = quote.price - quote.close
                            quote.change_pct = (quote.change / quote.close) * 100

                        # 成交量
                        if hasattr(quote_obj, 'volume') and quote_obj.volume:
                            quote.volume = int(quote_obj.volume)

                        # 时间戳
                        quote.timestamp = int(datetime.now().timestamp())
                        quotes.append(quote)
                        
                    print(f"   ✓ 第 {i//batch_size + 1}/{total_batches} 批完成，已获取 {len(quotes)} 条")
                    
                except Exception as batch_e:
                    print(f"   ✗ 第 {i//batch_size + 1}/{total_batches} 批失败: {batch_e}")
                    continue

            print(f"📊 从长桥获取到 {len(quotes)} 条 {market} 实时行情")
            return quotes

        except Exception as e:
            print(f"❌ 从长桥获取行情失败: {e}")
            import traceback
            traceback.print_exc()
            return quotes

    # ================ K线历史数据 ================

    def get_klines(
        self,
        code: str,
        period: str = "1d",
        count: int = 100,
        market: str = "US",
        verbose: bool = True,
    ) -> List[KLine]:
        """
        获取K线数据

        Args:
            code: 股票代码
            period: 周期 (1d/1w/1M)
            count: 数量
            market: 市场

        Returns:
            K线数据列表
        """
        klines: List[KLine] = []

        if not self._quote_context:
            print("❌ 长桥未连接，无法获取K线数据")
            return klines

        try:
            from longport.openapi import Period, AdjustType
            
            # 构造symbol
            symbol = f"{code}.{market}" if market == "HK" else f"{code}.US"
            
            # 转换周期
            period_map = {
                "1d": Period.Day,
                "1w": Period.Week,
                "1M": Period.Month
            }
            lp_period = period_map.get(period, Period.Day)
            
            if verbose:
                print(f"📡 正在从长桥获取K线: {symbol} {period}")
            resp = self._quote_context.candlesticks(
                symbol,
                lp_period,
                count,
                AdjustType.NoAdjust
            )
            
            if resp:
                for candle in resp:
                    # 先提取日期
                    date_str = ""
                    if hasattr(candle, 'timestamp') and candle.timestamp:
                        # 注意：这里的timestamp可能是datetime对象，也可能是int
                        if hasattr(candle.timestamp, 'strftime'):
                            date_str = candle.timestamp.strftime("%Y-%m-%d")
                        else:
                            date_str = datetime.fromtimestamp(candle.timestamp).strftime("%Y-%m-%d")
                    
                    # 创建 KLine 对象
                    kline = KLine(code=code, period=period, date=date_str)
                    
                    # OHLCV
                    if hasattr(candle, 'open') and candle.open:
                        kline.open = float(candle.open)
                    if hasattr(candle, 'high') and candle.high:
                        kline.high = float(candle.high)
                    if hasattr(candle, 'low') and candle.low:
                        kline.low = float(candle.low)
                    if hasattr(candle, 'close') and candle.close:
                        kline.close = float(candle.close)
                    if hasattr(candle, 'volume') and candle.volume:
                        kline.volume = int(candle.volume)
                    
                    # 计算变化
                    if kline.close and kline.open and kline.open > 0:
                        kline.change = kline.close - kline.open
                        kline.change_pct = (kline.change / kline.open) * 100
                    
                    klines.append(kline)
            
            if verbose:
                print(f"🕯️  从长桥获取到 {len(klines)} 条 {period} K线数据: {code}")
            return klines

        except Exception as e:
            print(f"❌ 从长桥获取K线数据失败: {e}")
            import traceback
            traceback.print_exc()
            return klines

    def get_klines_by_date_range(
        self,
        code: str,
        start_date: str,
        end_date: str,
        period: str = "1d",
        market: str = "US",
        verbose: bool = True,
    ) -> List[KLine]:
        """
        按日期区间获取 K 线（优先使用 history_candlesticks_by_date）。
        """
        if not self._quote_context:
            print("❌ 长桥未连接，无法获取K线数据")
            return []

        try:
            from datetime import date as date_cls
            from longport.openapi import Period, AdjustType

            symbol = self._to_symbol(code, market)
            period_map = {"1d": Period.Day, "1w": Period.Week, "1M": Period.Month}
            lp_period = period_map.get(period, Period.Day)

            start = date_cls.fromisoformat(start_date)
            end = date_cls.fromisoformat(end_date)
            if start > end:
                return []

            all_klines: List[KLine] = []
            chunk_start = start
            while chunk_start <= end:
                chunk_end = min(end, date_cls(chunk_start.year, 12, 31))
                if verbose:
                    print(f"📡 拉取历史 K 线 {symbol} {chunk_start} ~ {chunk_end}")

                resp = self._quote_context.history_candlesticks_by_date(
                    symbol,
                    lp_period,
                    AdjustType.NoAdjust,
                    chunk_start,
                    chunk_end,
                )
                all_klines.extend(self._parse_candles(code, period, resp))

                if chunk_end >= end:
                    break
                chunk_start = chunk_end + timedelta(days=1)

            filtered = [
                k for k in all_klines
                if k.date and start_date <= k.date <= end_date
            ]
            deduped: Dict[str, KLine] = {}
            for kline in filtered:
                deduped[kline.date] = kline
            result = [deduped[key] for key in sorted(deduped.keys())]
            if verbose:
                print(f"🕯️  区间 K 线 {code}: {len(result)} 条 ({start_date} ~ {end_date})")
            return result
        except Exception as e:
            print(f"❌ 按区间获取K线失败 {code}: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_candles(self, code: str, period: str, resp) -> List[KLine]:
        klines: List[KLine] = []
        if not resp:
            return klines
        for candle in resp:
            date_str = ""
            if hasattr(candle, "timestamp") and candle.timestamp:
                if hasattr(candle.timestamp, "strftime"):
                    date_str = candle.timestamp.strftime("%Y-%m-%d")
                else:
                    date_str = datetime.fromtimestamp(candle.timestamp).strftime("%Y-%m-%d")

            kline = KLine(code=code, period=period, date=date_str)
            if hasattr(candle, "open") and candle.open:
                kline.open = float(candle.open)
            if hasattr(candle, "high") and candle.high:
                kline.high = float(candle.high)
            if hasattr(candle, "low") and candle.low:
                kline.low = float(candle.low)
            if hasattr(candle, "close") and candle.close:
                kline.close = float(candle.close)
            if hasattr(candle, "volume") and candle.volume:
                kline.volume = int(candle.volume)
            if hasattr(candle, "turnover") and candle.turnover:
                try:
                    kline.turnover = float(candle.turnover)
                except (TypeError, ValueError):
                    pass
            if kline.close and kline.open and kline.open > 0:
                kline.change = kline.close - kline.open
                kline.change_pct = (kline.change / kline.open) * 100
            if date_str:
                klines.append(kline)
        return klines

    # ================ 标的基础信息 ================

    def get_static_info(
        self,
        codes: List[str],
        market: str = "US",
        batch_size: int = 500
    ) -> List[Stock]:
        """
        获取标的基础信息（LongPort static_info，单次最多 500 个标的）

        Args:
            codes: 股票代码列表（纯代码，如 AAPL）
            market: 市场 (US/HK)
            batch_size: 每批请求数量，上限 500

        Returns:
            标的基础信息列表
        """
        stocks: List[Stock] = []

        if not self._quote_context:
            print("❌ 长桥未连接，无法获取标的基础信息")
            return stocks

        if not codes:
            return stocks

        batch_size = min(max(batch_size, 1), 500)
        total_batches = (len(codes) + batch_size - 1) // batch_size
        print(f"📋 开始获取 {len(codes)} 只标的的基础信息，共 {total_batches} 批")

        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i + batch_size]
            symbols = [self._to_symbol(code, market) for code in batch_codes]

            try:
                resp = self._quote_context.static_info(symbols)
                for item in resp or []:
                    stock = self._parse_static_info(item, market)
                    if stock:
                        stocks.append(stock)
                print(f"   ✓ 第 {i // batch_size + 1}/{total_batches} 批完成，累计 {len(stocks)} 条")
            except Exception as batch_e:
                print(f"   ✗ 第 {i // batch_size + 1}/{total_batches} 批失败: {batch_e}")
                continue

        print(f"📋 从长桥获取到 {len(stocks)} 条 {market} 标的基础信息")
        return stocks

    def _to_symbol(self, code: str, market: str) -> str:
        """构造 ticker.region 格式 symbol"""
        if "." in code:
            return code
        suffix = {"US": "US", "HK": "HK"}.get(market, market)
        return f"{code}.{suffix}"

    def _parse_static_info(self, item, market: str) -> Stock | None:
        """解析 LongPort StaticInfo 响应"""
        symbol = str(item.symbol) if getattr(item, "symbol", None) else ""
        if not symbol:
            return None

        if "." in symbol:
            code, symbol_market = symbol.rsplit(".", 1)
            market = symbol_market if symbol_market else market
        else:
            code = symbol

        name_cn = self._optional_str(getattr(item, "name_cn", None))
        name_en = self._optional_str(getattr(item, "name_en", None))
        name_hk = self._optional_str(getattr(item, "name_hk", None))
        name = name_cn or name_en or name_hk or code

        board = getattr(item, "board", None)
        if board is not None and not isinstance(board, str):
            board = str(board)

        listing_date = self._optional_str(getattr(item, "listing_date", None))

        return Stock(
            code=code,
            symbol=symbol,
            name=name,
            market=market,
            exchange=self._optional_str(getattr(item, "exchange", None)),
            listing_date=listing_date,
            name_cn=name_cn,
            name_en=name_en,
            name_hk=name_hk,
            currency=self._optional_str(getattr(item, "currency", None)),
            lot_size=self._optional_int(getattr(item, "lot_size", None)),
            total_shares=self._optional_int(getattr(item, "total_shares", None)),
            circulating_shares=self._optional_int(getattr(item, "circulating_shares", None)),
            hk_shares=self._optional_int(getattr(item, "hk_shares", None)),
            eps=self._optional_float(getattr(item, "eps", None)),
            eps_ttm=self._optional_float(getattr(item, "eps_ttm", None)),
            bps=self._optional_float(getattr(item, "bps", None)),
            dividend_yield=self._optional_float(getattr(item, "dividend_yield", None)),
            stock_derivatives=self._parse_derivatives(getattr(item, "stock_derivatives", None)),
            board=board,
        )

    @staticmethod
    def _optional_str(value) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _optional_int(value) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _optional_float(value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_derivatives(value) -> List[int]:
        if not value:
            return []
        result: List[int] = []
        for item in value:
            try:
                result.append(int(item))
            except (TypeError, ValueError):
                continue
        return result

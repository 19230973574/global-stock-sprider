"""
K线数据模型
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class KLine:
    """K线数据"""
    code: str                       # 股票代码
    period: str                    # 周期 (1d/1w/1M/5m/15m/1h)
    date: str                      # 日期 (YYYY-MM-DD) 或时间
    open: Optional[float] = None   # 开盘价
    high: Optional[float] = None   # 最高价
    low: Optional[float] = None    # 最低价
    close: Optional[float] = None  # 收盘价
    volume: Optional[int] = None   # 成交量
    turnover: Optional[float] = None # 成交额
    change: Optional[float] = None   # 涨跌额
    change_pct: Optional[float] = None # 涨跌幅 (%)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "period": self.period,
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "turnover": self.turnover,
            "change": self.change,
            "change_pct": self.change_pct
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KLine":
        """从字典创建"""
        return cls(
            code=data.get("code", ""),
            period=data.get("period", "1d"),
            date=data.get("date", ""),
            open=data.get("open"),
            high=data.get("high"),
            low=data.get("low"),
            close=data.get("close"),
            volume=data.get("volume"),
            turnover=data.get("turnover"),
            change=data.get("change"),
            change_pct=data.get("change_pct")
        )

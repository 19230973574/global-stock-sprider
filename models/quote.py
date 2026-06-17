"""
实时行情数据模型
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Quote:
    """实时行情数据"""
    code: str                       # 股票代码
    symbol: Optional[str] = None    # 完整代码
    price: Optional[float] = None   # 最新价
    open: Optional[float] = None    # 今开
    high: Optional[float] = None    # 最高
    low: Optional[float] = None     # 最低
    close: Optional[float] = None   # 昨收
    volume: Optional[int] = None    # 成交量
    turnover: Optional[float] = None # 成交额
    change: Optional[float] = None   # 涨跌额
    change_pct: Optional[float] = None # 涨跌幅 (%)
    timestamp: Optional[int] = None  # 时间戳
    tag: Optional[str] = None        # 行情标记 (Pre/Regular/Post)

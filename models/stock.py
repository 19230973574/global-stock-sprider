"""
股票基本信息模型
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class Stock:
    """股票基本信息"""
    code: str                 # 股票代码（纯代码，如 AAPL）
    symbol: str               # 完整代码，如 AAPL.US
    name: Optional[str] = None       # 股票名称（默认中文名）
    market: str = "US"        # 市场 (US/A/HK)
    exchange: Optional[str] = None   # 交易所
    industry: Optional[str] = None   # 行业
    market_cap: Optional[float] = None  # 市值
    listing_date: Optional[str] = None # 上市日期
    name_cn: Optional[str] = None
    name_en: Optional[str] = None
    name_hk: Optional[str] = None
    currency: Optional[str] = None
    lot_size: Optional[int] = None
    total_shares: Optional[int] = None
    circulating_shares: Optional[int] = None
    hk_shares: Optional[int] = None
    eps: Optional[float] = None
    eps_ttm: Optional[float] = None
    bps: Optional[float] = None
    dividend_yield: Optional[float] = None
    stock_derivatives: List[int] = field(default_factory=list)
    board: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "exchange": self.exchange,
            "industry": self.industry,
            "market_cap": self.market_cap,
            "listing_date": self.listing_date,
            "name_cn": self.name_cn,
            "name_en": self.name_en,
            "name_hk": self.name_hk,
            "currency": self.currency,
            "lot_size": self.lot_size,
            "total_shares": self.total_shares,
            "circulating_shares": self.circulating_shares,
            "hk_shares": self.hk_shares,
            "eps": self.eps,
            "eps_ttm": self.eps_ttm,
            "bps": self.bps,
            "dividend_yield": self.dividend_yield,
            "stock_derivatives": self.stock_derivatives,
            "board": self.board,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Stock":
        """从字典创建"""
        return cls(
            code=data.get("code", ""),
            symbol=data.get("symbol", ""),
            name=data.get("name"),
            market=data.get("market", "US"),
            exchange=data.get("exchange"),
            industry=data.get("industry"),
            market_cap=data.get("market_cap"),
            listing_date=data.get("listing_date"),
            name_cn=data.get("name_cn"),
            name_en=data.get("name_en"),
            name_hk=data.get("name_hk"),
            currency=data.get("currency"),
            lot_size=data.get("lot_size"),
            total_shares=data.get("total_shares"),
            circulating_shares=data.get("circulating_shares"),
            hk_shares=data.get("hk_shares"),
            eps=data.get("eps"),
            eps_ttm=data.get("eps_ttm"),
            bps=data.get("bps"),
            dividend_yield=data.get("dividend_yield"),
            stock_derivatives=data.get("stock_derivatives") or [],
            board=data.get("board"),
        )

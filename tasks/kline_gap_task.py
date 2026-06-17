"""
K 线缺口检测与补数任务
扫描 MongoDB 中各标的最新交易日，仅对缺失/滞后的标的重新拉取近期 K 线。
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .base_task import BaseTask, TaskResult
from models import KLine

# 用于推断市场最新交易日的基准标的
REFERENCE_CODES = ("SPY", "QQQ", "AAPL")


class KlineGapTask(BaseTask):
    """K 线缺口检测与增量补数"""

    def __init__(
        self,
        storage_manager,
        data_client,
        market: str = "US",
        period: str = "1d",
        kline_count: int = 120,
        check_only: bool = False,
        reference_codes: Tuple[str, ...] = REFERENCE_CODES,
    ):
        super().__init__(f"KlineGap-{market}-{period}", storage_manager, data_client)
        self.market = market
        self.period = period
        self.kline_count = kline_count
        self.check_only = check_only
        self.reference_codes = reference_codes

    def run(self) -> TaskResult:
        codes = self.storage.redis.get_stock_list(self.market)
        if not codes:
            return TaskResult(False, error=f"未找到{self.market}股票列表，请先运行 stock_list")

        reference_date = self._resolve_reference_date()
        if not reference_date:
            return TaskResult(False, error="无法确定市场参考交易日，请检查 LongPort 连接")

        latest_by_code = self.storage.mongo.get_kline_latest_by_code(self.market, self.period)
        distribution = self.storage.mongo.get_kline_date_distribution(self.market, self.period, top_n=15)

        stale_codes, missing_codes, up_to_date_codes, lag_summary = self._classify_codes(
            codes, latest_by_code, reference_date
        )

        self._print_gap_report(
            reference_date=reference_date,
            total=len(codes),
            in_db=len(latest_by_code),
            missing=len(missing_codes),
            stale=len(stale_codes),
            up_to_date=len(up_to_date_codes),
            distribution=distribution,
            lag_summary=lag_summary,
            sample_stale=stale_codes[:15],
            sample_missing=missing_codes[:15],
        )

        if self.check_only:
            return TaskResult(
                True,
                data={
                    "mode": "check_only",
                    "reference_date": reference_date,
                    "total": len(codes),
                    "missing": len(missing_codes),
                    "stale": len(stale_codes),
                    "up_to_date": len(up_to_date_codes),
                    "to_refresh": len(missing_codes) + len(stale_codes),
                    "lag_summary": lag_summary,
                },
            )

        to_refresh = sorted(set(missing_codes) | set(stale_codes))
        if not to_refresh:
            print("\n✅ 所有标的 K 线均已更新至参考交易日，无需补数")
            return TaskResult(
                True,
                data={
                    "reference_date": reference_date,
                    "refreshed": 0,
                    "total_klines": 0,
                    "errors": 0,
                },
            )

        print(f"\n🔄 开始补数: 共 {len(to_refresh)} 只（无数据 {len(missing_codes)}，滞后 {len(stale_codes)}）")

        total_klines = 0
        total_errors = 0
        progress_step = max(len(to_refresh) // 20, 1)

        for idx, code in enumerate(to_refresh, start=1):
            try:
                klines: List[KLine] = self.data_client.get_klines(
                    code,
                    self.period,
                    self.kline_count,
                    self.market,
                    verbose=False,
                )
                if klines:
                    saved = self.storage.mongo.save_klines(klines, self.market, is_today=False, quiet=True)
                    total_klines += saved
                elif idx <= 5:
                    print(f"⚠️  {code} 未返回 K 线数据")
            except Exception as e:
                total_errors += 1
                if total_errors <= 10:
                    print(f"⚠️  补数 {code} 失败: {e}")

            if idx % progress_step == 0 or idx == len(to_refresh):
                print(f"   … 进度 {idx}/{len(to_refresh)}，已写入约 {total_klines} 条")

        print(
            f"\n📊 补数完成: 处理 {len(to_refresh)} 只, "
            f"失败 {total_errors} 只, 写入/更新约 {total_klines} 条"
        )

        return TaskResult(
            True,
            data={
                "reference_date": reference_date,
                "refreshed": len(to_refresh),
                "missing_before": len(missing_codes),
                "stale_before": len(stale_codes),
                "total_klines": total_klines,
                "errors": total_errors,
            },
        )

    def _resolve_reference_date(self) -> Optional[str]:
        """从基准标的或库内分布推断市场最新交易日。"""
        for code in self.reference_codes:
            try:
                klines = self.data_client.get_klines(
                    code, self.period, 5, self.market, verbose=False
                )
                dates = [k.date for k in klines if k.date]
                if dates:
                    ref = max(dates)
                    print(f"📅 参考交易日（{code}）: {ref}")
                    return ref
            except Exception:
                continue

        distribution = self.storage.mongo.get_kline_date_distribution(
            self.market, self.period, top_n=1
        )
        if distribution and distribution[0].get("_id"):
            ref = str(distribution[0]["_id"])
            print(f"📅 参考交易日（库内众数）: {ref}")
            return ref
        return None

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _calendar_lag_days(reference_date: str, latest_date: str) -> int:
        ref = KlineGapTask._parse_date(reference_date)
        latest = KlineGapTask._parse_date(latest_date)
        if not ref or not latest:
            return -1
        return max((ref - latest).days, 0)

    @classmethod
    def _classify_codes(
        cls,
        all_codes: List[str],
        latest_by_code: Dict[str, Dict],
        reference_date: str,
    ) -> Tuple[List[str], List[str], List[str], Dict[str, object]]:
        missing: List[str] = []
        stale: List[str] = []
        up_to_date: List[str] = []
        lag_buckets: Dict[str, int] = {}
        lag_by_latest_date: Dict[str, int] = {}
        stale_details: List[Dict[str, object]] = []

        for code in all_codes:
            info = latest_by_code.get(code)
            if not info or not info.get("latest"):
                missing.append(code)
                lag_buckets["无K线"] = lag_buckets.get("无K线", 0) + 1
                stale_details.append({"code": code, "latest": None, "lag_days": None})
                continue

            latest = info["latest"]
            lag_days = cls._calendar_lag_days(reference_date, latest)

            if latest < reference_date:
                stale.append(code)
                bucket = f"缺{lag_days}天" if lag_days > 0 else "缺<1天"
                lag_buckets[bucket] = lag_buckets.get(bucket, 0) + 1
                lag_by_latest_date[latest] = lag_by_latest_date.get(latest, 0) + 1
                stale_details.append({"code": code, "latest": latest, "lag_days": lag_days})
            else:
                up_to_date.append(code)
                lag_buckets["已最新(0天)"] = lag_buckets.get("已最新(0天)", 0) + 1

        lag_summary = {
            "buckets": lag_buckets,
            "by_latest_date": lag_by_latest_date,
            "stale_details": stale_details,
        }
        return stale, missing, up_to_date, lag_summary

    @staticmethod
    def _print_gap_report(
        *,
        reference_date: str,
        total: int,
        in_db: int,
        missing: int,
        stale: int,
        up_to_date: int,
        distribution: List[Dict],
        lag_summary: Dict[str, object],
        sample_stale: List[str],
        sample_missing: List[str],
    ) -> None:
        buckets: Dict[str, int] = lag_summary.get("buckets", {})  # type: ignore[assignment]
        by_latest: Dict[str, int] = lag_summary.get("by_latest_date", {})  # type: ignore[assignment]
        stale_details: List[Dict[str, object]] = lag_summary.get("stale_details", [])  # type: ignore[assignment]

        print("\n" + "=" * 60)
        print("📋 K 线缺口扫描报告（全量）")
        print("=" * 60)
        print(f"参考最新交易日: {reference_date}")
        print(f"股票列表总数:   {total}")
        print(f"库内有 K 线:    {in_db}")
        print(f"完全无 K 线:    {missing}")
        print(f"最新日滞后:     {stale}")
        print(f"已是最新(0天):  {up_to_date}")
        print(f"待补数合计:     {missing + stale}")

        if buckets:
            print("\n【按滞后天数统计】（日历日，相对参考最新日）")
            def bucket_sort_key(item: Tuple[str, int]) -> Tuple[int, str]:
                label = item[0]
                if label == "已最新(0天)":
                    return (0, label)
                if label == "无K线":
                    return (9999, label)
                if label.startswith("缺") and label.endswith("天"):
                    try:
                        return (int(label[1:-1]), label)
                    except ValueError:
                        return (9998, label)
                return (9997, label)

            for label, count in sorted(buckets.items(), key=bucket_sort_key):
                pct = count * 100 / total if total else 0
                print(f"  {label:>12}: {count:>5} 只 ({pct:5.1f}%)")

        if by_latest:
            print("\n【滞后标的 — 按库内最新日分组】")
            for latest in sorted(by_latest.keys(), reverse=True):
                count = by_latest[latest]
                lag = KlineGapTask._calendar_lag_days(reference_date, latest)
                print(f"  最新 {latest}（缺约 {lag} 天）: {count} 只")

        if distribution:
            print("\n【全库 — 各最新日标的数量 Top】")
            for row in distribution:
                date = row.get("_id") or "—"
                count = row.get("count", 0)
                lag = KlineGapTask._calendar_lag_days(reference_date, date) if date != "—" else -1
                lag_text = f"，缺 {lag} 天" if lag > 0 else (" ← 参考" if lag == 0 else "")
                print(f"  {date}: {count} 只{lag_text}")

        # 列出所有非最新标的（滞后 + 无数据）
        need_fix = [d for d in stale_details if d.get("latest") is None or (d.get("lag_days") or 0) > 0]
        if need_fix:
            print(f"\n【全部待补标的明细】共 {len(need_fix)} 只")
            print(f"{'代码':<12} {'库内最新日':<14} {'缺几天':>8}")
            print("-" * 38)
            for row in sorted(
                need_fix,
                key=lambda r: (
                    9999 if r.get("lag_days") is None else int(r.get("lag_days") or 0),
                    str(r.get("code") or ""),
                ),
                reverse=True,
            ):
                code = str(row.get("code") or "")
                latest = row.get("latest") or "—"
                lag = row.get("lag_days")
                lag_text = "无数据" if lag is None else str(lag)
                print(f"{code:<12} {str(latest):<14} {lag_text:>8}")

        if sample_missing and len(sample_missing) < len([d for d in stale_details if d.get("latest") is None]):
            print(f"\n无 K 线样例: {', '.join(sample_missing)}")
        if sample_stale and len(sample_stale) < stale:
            print(f"滞后样例: {', '.join(sample_stale)}")
        print("=" * 60)

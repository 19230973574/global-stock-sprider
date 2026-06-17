"""
按日期区间拉取 K 线任务（由 kline_data_tasks 驱动）。
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_task import BaseTask, TaskResult
from models import KLine


class KlineRangeFetchTask(BaseTask):
    """按任务 ID 拉取指定代码、日期区间的日 K 线。"""

    def __init__(
        self,
        storage_manager,
        data_client,
        task: Dict[str, Any],
        sleep_ms: int = 300,
    ):
        task_id = str(task.get("_id") or task.get("id") or "unknown")
        super().__init__(f"KlineRangeFetch-{task_id}", storage_manager, data_client)
        self.task = task
        self.task_id = task_id
        self.sleep_ms = sleep_ms
        self.task_manager = storage_manager.mongo.kline_tasks

    def run(self) -> TaskResult:
        if self.task_manager is None:
            return TaskResult(False, error="任务管理器未初始化")

        market = self.task.get("market", "US")
        period = self.task.get("period", "1d")
        codes: List[str] = list(self.task.get("codes") or [])
        start_date = self.task.get("start_date")
        end_date = self.task.get("end_date")

        if not codes or not start_date or not end_date:
            self._finish_failed("任务参数不完整")
            return TaskResult(False, error="任务参数不完整")

        total_saved = 0
        failed_codes: List[str] = []

        for idx, code in enumerate(codes, start=1):
            if self._is_cancelled():
                self.task_manager.finish_task(
                    self.task_id,
                    status="CANCELLED",
                    saved_bars=total_saved,
                    failed_code_list=failed_codes,
                    error_message="任务已取消",
                )
                return TaskResult(True, data={"cancelled": True, "saved_bars": total_saved})

            self.task_manager.update_progress(
                self.task_id,
                done_codes=idx - 1,
                current_code=code,
                saved_bars=total_saved,
                failed_codes=len(failed_codes),
            )

            try:
                klines = self.data_client.get_klines_by_date_range(
                    code, start_date, end_date, period, market, verbose=False
                )
                if klines:
                    saved = self.storage.mongo.save_klines(klines, market, is_today=False, quiet=True)
                    total_saved += saved
                else:
                    failed_codes.append(code)
            except Exception as exc:
                failed_codes.append(code)
                print(f"⚠️  任务 {self.task_id} 拉取 {code} 失败: {exc}")

            if idx < len(codes):
                time.sleep(self.sleep_ms / 1000.0)

        self.task_manager.update_progress(
            self.task_id,
            done_codes=len(codes),
            current_code=None,
            saved_bars=total_saved,
            failed_codes=len(failed_codes),
        )

        if failed_codes and len(failed_codes) < len(codes):
            status = "PARTIAL"
        elif failed_codes:
            status = "FAILED"
        else:
            status = "SUCCESS"

        error_summary = None
        if failed_codes:
            preview = ", ".join(failed_codes[:10])
            if len(failed_codes) > 10:
                preview += f" 等 {len(failed_codes)} 只"
            error_summary = f"失败代码: {preview}"

        self.task_manager.finish_task(
            self.task_id,
            status=status,
            saved_bars=total_saved,
            failed_code_list=failed_codes,
            error_summary=error_summary,
        )

        return TaskResult(
            True,
            data={
                "task_id": self.task_id,
                "status": status,
                "saved_bars": total_saved,
                "failed_codes": failed_codes,
            },
        )

    def _finish_failed(self, message: str) -> None:
        self.task_manager.finish_task(
            self.task_id,
            status="FAILED",
            saved_bars=0,
            failed_code_list=[],
            error_message=message,
            error_summary=message,
        )

    def _is_cancelled(self) -> bool:
        doc = self.task_manager.find_by_id(self.task_id)
        return doc is not None and doc.get("status") == "CANCELLED"

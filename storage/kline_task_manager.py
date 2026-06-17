"""
K 线数据任务 MongoDB 操作（与 Java 后端共用 kline_data_tasks 集合）。
"""
from __future__ import annotations

import socket
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument


TASK_COLLECTION = "kline_data_tasks"


class KlineTaskManager:
    """K 线拉取任务管理"""

    def __init__(self, db):
        self.db = db
        self.collection = db[TASK_COLLECTION] if db is not None else None
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        if self.collection is None:
            return
        try:
            self.collection.create_index([("status", 1), ("created_at", 1)])
            self.collection.create_index([("created_at", -1)])
        except Exception:
            pass

    def claim_next_pending(self, worker_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """认领下一个 PENDING 任务（CAS）。"""
        if self.collection is None:
            return None
        wid = worker_id or self.default_worker_id()
        now = int(time.time() * 1000)
        return self.collection.find_one_and_update(
            {"status": "PENDING", "type": {"$in": ["FETCH", "REBUILD"]}},
            {
                "$set": {
                    "status": "RUNNING",
                    "worker_id": wid,
                    "started_at": now,
                    "updated_at": now,
                }
            },
            sort=[("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )

    def claim_by_id(self, task_id: str, worker_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if self.collection is None:
            return None
        wid = worker_id or self.default_worker_id()
        now = int(time.time() * 1000)
        return self.collection.find_one_and_update(
            {"_id": task_id, "status": "PENDING", "type": {"$in": ["FETCH", "REBUILD"]}},
            {
                "$set": {
                    "status": "RUNNING",
                    "worker_id": wid,
                    "started_at": now,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    def find_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        if self.collection is None:
            return None
        return self.collection.find_one({"_id": task_id})

    def update_progress(
        self,
        task_id: str,
        *,
        done_codes: int,
        current_code: Optional[str],
        saved_bars: int,
        failed_codes: int,
    ) -> None:
        if self.collection is None:
            return
        self.collection.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "progress.done_codes": done_codes,
                    "progress.current_code": current_code,
                    "progress.saved_bars": saved_bars,
                    "progress.failed_codes": failed_codes,
                    "updated_at": int(time.time() * 1000),
                }
            },
        )

    def finish_task(
        self,
        task_id: str,
        *,
        status: str,
        saved_bars: int,
        failed_code_list: List[str],
        error_message: Optional[str] = None,
        error_summary: Optional[str] = None,
    ) -> None:
        if self.collection is None:
            return
        now = int(time.time() * 1000)
        self.collection.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "status": status,
                    "result.saved_bars": saved_bars,
                    "result.failed_codes": failed_code_list,
                    "result.error_summary": error_summary,
                    "error_message": error_message,
                    "finished_at": now,
                    "updated_at": now,
                    "progress.current_code": None,
                }
            },
        )

    @staticmethod
    def default_worker_id() -> str:
        hostname = socket.gethostname()
        return f"{hostname}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

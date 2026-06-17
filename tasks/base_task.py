"""
任务基类
定义所有爬虫任务的标准接口
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional


class TaskResult:
    """任务执行结果"""

    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp
        }


class BaseTask:
    """任务基类"""

    def __init__(
        self,
        name: str,
        storage_manager: Any,
        data_client: Any
    ):
        """
        初始化任务

        Args:
            name: 任务名称
            storage_manager: 存储管理器
            data_client: 数据客户端
        """
        self.name = name
        self.storage = storage_manager
        self.data_client = data_client

    def execute(self) -> TaskResult:
        """
        执行任务的完整流程

        Returns:
            TaskResult
        """
        self._before_run()

        try:
            result = self.run()
        except Exception as e:
            import traceback
            traceback.print_exc()
            result = TaskResult(False, error=str(e))

        self._after_run(result)
        return result

    def run(self) -> TaskResult:
        """
        任务执行逻辑 - 子类必须实现此方法

        Returns:
            TaskResult
        """
        raise NotImplementedError("子类必须实现 run 方法")

    def _before_run(self) -> None:
        """任务执行前的钩子"""
        print(f"\n{'='*60}")
        print(f"🚀 开始执行任务: {self.name}")
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

    def _after_run(self, result: TaskResult) -> None:
        """
        任务执行后的钩子

        Args:
            result: 任务结果
        """
        if result.success:
            print(f"\n✅ 任务成功: {self.name}")
            if result.data:
                print(f"📊 结果数据: {result.data}")
        else:
            print(f"\n❌ 任务失败: {self.name}")
            if result.error:
                print(f"💥 错误信息: {result.error}")

        print(f"{'='*60}\n")

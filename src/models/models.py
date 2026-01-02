"""
領域模型定義
"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class UserRole(Enum):
    """使用者角色"""
    CUSTOMER = "customer"
    ASSISTANT = "assistant"
    ADMIN = "admin"


class DeviceType(Enum):
    """設備類型 - 預留未來擴展"""
    SBD = "sbd"                    # Short Burst Data
    VOICE = "voice"                # 衛星電話
    IRIDIUM_GO_EXEC = "go_exec"    # Iridium Go! Exec
    # 未來可以添加更多設備類型


class RequestStatus(Enum):
    """請求狀態"""
    PENDING_FINANCE = "pending_finance"  # 等待財務確認
    APPROVED = "approved"  # 已核准
    PROCESSING = "processing"  # 處理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失敗
    CANCELLED = "cancelled"  # 已取消


class ActionType(Enum):
    """操作類型"""
    ACTIVATE = "activate"
    SUSPEND = "suspend"
    RESUME = "resume"
    TERMINATE = "terminate"
    CHANGE_PLAN = "change_plan"  # v6.5: 費率變更
    DEACTIVATE = "deactivate"  # v6.5: 註銷設備


@dataclass
class ServiceRequest:
    """服務請求"""
    request_id: str
    imei: str
    action_type: ActionType
    plan_id: str
    amount_due: float
    device_type: DeviceType = DeviceType.SBD  # 設備類型（預設 SBD，未來可擴展）
    status: RequestStatus = RequestStatus.PENDING_FINANCE
    requester: str = ""
    approved_by: Optional[str] = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def approve(self, approver: str) -> None:
        """核准請求"""
        self.approved_by = approver
        self.status = RequestStatus.APPROVED
        self.updated_at = datetime.now()
    
    def mark_processing(self) -> None:
        """標記為處理中"""
        self.status = RequestStatus.PROCESSING
        self.updated_at = datetime.now()
    
    def mark_completed(self) -> None:
        """標記為已完成"""
        self.status = RequestStatus.COMPLETED
        self.updated_at = datetime.now()
    
    def mark_failed(self, error_message: str = "") -> None:
        """標記為失敗"""
        self.status = RequestStatus.FAILED
        if error_message:
            self.notes += f" | Error: {error_message}"
        self.updated_at = datetime.now()

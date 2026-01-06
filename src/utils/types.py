"""
Type Definitions for SBD System
型別定義 - 提供明確的型別標註
"""

from typing import (
    Dict, List, Optional, Union, Any, 
    TypedDict, Protocol, Literal, TypeAlias
)
from datetime import datetime, date
from enum import Enum


# ========== Enums (列舉) ==========

class SubscriberStatus(str, Enum):
    """訂戶狀態"""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"
    PENDING = "PENDING"


class PlanType(str, Enum):
    """方案類型"""
    STANDARD = "STANDARD"
    DSG = "DSG"


class ServiceType(str, Enum):
    """服務類型"""
    SHORT_BURST_DATA = "SHORT_BURST_DATA"
    VOICE = "VOICE"
    PUSH_TO_TALK = "PUSH_TO_TALK"


class TrackerResetCycle(str, Enum):
    """Tracker 重置週期"""
    MONTHLY = "MONTHLY"
    BILLCYCLE = "BILLCYCLE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    THRESHOLD = "THRESHOLD"


class UserRole(str, Enum):
    """使用者角色"""
    CUSTOMER = "CUSTOMER"
    ASSISTANT = "ASSISTANT"
    ADMIN = "ADMIN"


# ========== Type Aliases (型別別名) ==========

IMEI: TypeAlias = str  # 15 位數字
AccountNumber: TypeAlias = str
PlanID: TypeAlias = str
ProfileID: TypeAlias = str
GroupID: TypeAlias = str
TrackerID: TypeAlias = str
RuleID: TypeAlias = str

# Monetary values (金額相關)
Amount: TypeAlias = float
Bytes: TypeAlias = int
Kilobytes: TypeAlias = float


# ========== TypedDict (結構化字典) ==========

class SubscriberInfo(TypedDict):
    """訂戶資訊"""
    imei: IMEI
    account_number: AccountNumber
    status: SubscriberStatus
    plan_id: PlanID
    activation_date: Optional[datetime]
    deactivation_date: Optional[datetime]


class PlanPricing(TypedDict):
    """方案價格"""
    plan_id: PlanID
    plan_name: str
    monthly_rate: Amount
    included_bytes: Bytes
    overage_per_kb: Amount
    activation_fee: Amount
    is_dsg: bool


class DSGGroupInfo(TypedDict):
    """DSG 群組資訊"""
    group_id: GroupID
    group_name: str
    description: Optional[str]
    member_count: int
    created_date: datetime


class TrackerUsage(TypedDict):
    """Tracker 用量資訊"""
    threshold_kb: Kilobytes
    used_kb: Kilobytes
    remaining_kb: Kilobytes
    overage_kb: Kilobytes
    usage_percentage: float
    is_over_threshold: bool
    next_reset_date: datetime


class BillingRecord(TypedDict):
    """帳單記錄"""
    imei: IMEI
    period_start: date
    period_end: date
    monthly_fee: Amount
    usage_fee: Amount
    total_amount: Amount
    data_used_kb: Kilobytes


# ========== Protocols (協議/介面) ==========

class IAPIClient(Protocol):
    """API 客戶端介面"""
    
    def connect(self) -> None:
        """建立連線"""
        ...
    
    def disconnect(self) -> None:
        """關閉連線"""
        ...
    
    def is_connected(self) -> bool:
        """檢查連線狀態"""
        ...


class IRepository(Protocol):
    """Repository 介面"""
    
    def find_by_id(self, id: str) -> Optional[Any]:
        """根據 ID 查詢"""
        ...
    
    def find_all(self) -> List[Any]:
        """查詢所有記錄"""
        ...
    
    def save(self, entity: Any) -> Any:
        """儲存實體"""
        ...
    
    def delete(self, id: str) -> bool:
        """刪除記錄"""
        ...


class IService(Protocol):
    """Service 介面"""
    
    def execute(self, *args, **kwargs) -> Any:
        """執行業務邏輯"""
        ...


# ========== Response Types (回應型別) ==========

class OperationResult(TypedDict):
    """操作結果"""
    success: bool
    message: str
    data: Optional[Any]
    error: Optional[str]


class PaginatedResult(TypedDict):
    """分頁結果"""
    items: List[Any]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


# ========== Configuration Types (設定型別) ==========

class DatabaseConfig(TypedDict):
    """資料庫設定"""
    host: str
    port: int
    database: str
    username: str
    password: str


class APIConfig(TypedDict):
    """API 設定"""
    endpoint: str
    username: str
    password: str
    timeout: int
    retry_count: int


class IWSConfig(TypedDict):
    """IWS API 設定"""
    endpoint: str
    username: str
    password: str
    sp_account: str
    timeout: int


class FTPConfig(TypedDict):
    """FTP 設定"""
    host: str
    port: int
    username: str
    password: str
    passive_mode: bool


class GoogleDriveConfig(TypedDict):
    """Google Drive 設定"""
    service_account_json: str
    root_folder_id: str

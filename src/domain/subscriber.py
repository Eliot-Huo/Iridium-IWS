"""
Domain Models - Subscriber
訂戶領域模型 - 包含業務邏輯和驗證
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal

from src.utils.types import (
    IMEI, AccountNumber, PlanID, SubscriberStatus
)
from src.utils.exceptions import (
    ValidationError, BusinessRuleViolationError
)


@dataclass
class Subscriber:
    """
    訂戶領域模型
    
    代表一個衛星設備訂戶，包含所有相關資訊和業務邏輯。
    
    Attributes:
        imei: 設備 IMEI 號碼（15 位數字）
        account_number: 帳號編號
        status: 訂戶狀態
        plan_id: 資費方案 ID
        activation_date: 啟用日期
        deactivation_date: 註銷日期
        suspended_date: 暫停日期
        last_updated: 最後更新時間
    """
    
    imei: IMEI
    account_number: AccountNumber
    status: SubscriberStatus
    plan_id: PlanID
    activation_date: Optional[datetime] = None
    deactivation_date: Optional[datetime] = None
    suspended_date: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
    
    # 額外資訊
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        """初始化後驗證"""
        self.validate()
    
    def validate(self) -> None:
        """
        驗證訂戶資料
        
        Raises:
            ValidationError: 資料驗證失敗
        """
        # 驗證 IMEI
        if not self._is_valid_imei(self.imei):
            raise ValidationError(
                f"無效的 IMEI: {self.imei}",
                {"imei": self.imei}
            )
        
        # 驗證狀態
        if not isinstance(self.status, SubscriberStatus):
            raise ValidationError(
                f"無效的狀態: {self.status}",
                {"status": self.status}
            )
        
        # 驗證日期邏輯
        if self.deactivation_date and self.activation_date:
            if self.deactivation_date < self.activation_date:
                raise ValidationError(
                    "註銷日期不能早於啟用日期",
                    {
                        "activation_date": self.activation_date,
                        "deactivation_date": self.deactivation_date
                    }
                )
    
    @staticmethod
    def _is_valid_imei(imei: str) -> bool:
        """
        驗證 IMEI 格式
        
        Args:
            imei: IMEI 號碼
            
        Returns:
            是否有效
        """
        return (
            isinstance(imei, str) and 
            len(imei) == 15 and 
            imei.isdigit()
        )
    
    # ========== 狀態查詢 ==========
    
    def is_active(self) -> bool:
        """是否為啟用狀態"""
        return self.status == SubscriberStatus.ACTIVE
    
    def is_suspended(self) -> bool:
        """是否為暫停狀態"""
        return self.status == SubscriberStatus.SUSPENDED
    
    def is_deactivated(self) -> bool:
        """是否為註銷狀態"""
        return self.status == SubscriberStatus.DEACTIVATED
    
    def can_activate(self) -> bool:
        """是否可以啟用"""
        return self.status in [
            SubscriberStatus.SUSPENDED,
            SubscriberStatus.PENDING
        ]
    
    def can_suspend(self) -> bool:
        """是否可以暫停"""
        return self.status == SubscriberStatus.ACTIVE
    
    def can_deactivate(self) -> bool:
        """是否可以註銷"""
        return self.status in [
            SubscriberStatus.ACTIVE,
            SubscriberStatus.SUSPENDED
        ]
    
    def can_change_plan(self) -> bool:
        """是否可以變更方案"""
        return self.status == SubscriberStatus.ACTIVE
    
    # ========== 狀態轉換 ==========
    
    def activate(self) -> None:
        """
        啟用訂戶
        
        Raises:
            BusinessRuleViolationError: 不符合啟用條件
        """
        if not self.can_activate():
            raise BusinessRuleViolationError(
                f"無法啟用處於 {self.status} 狀態的訂戶",
                {"current_status": self.status}
            )
        
        self.status = SubscriberStatus.ACTIVE
        self.activation_date = datetime.now()
        self.suspended_date = None
        self.last_updated = datetime.now()
    
    def suspend(self, reason: Optional[str] = None) -> None:
        """
        暫停訂戶
        
        Args:
            reason: 暫停原因
            
        Raises:
            BusinessRuleViolationError: 不符合暫停條件
        """
        if not self.can_suspend():
            raise BusinessRuleViolationError(
                f"無法暫停處於 {self.status} 狀態的訂戶",
                {"current_status": self.status}
            )
        
        self.status = SubscriberStatus.SUSPENDED
        self.suspended_date = datetime.now()
        self.last_updated = datetime.now()
        
        if reason:
            self.notes = f"暫停原因: {reason}"
    
    def deactivate(self, reason: Optional[str] = None) -> None:
        """
        註銷訂戶
        
        Args:
            reason: 註銷原因
            
        Raises:
            BusinessRuleViolationError: 不符合註銷條件
        """
        if not self.can_deactivate():
            raise BusinessRuleViolationError(
                f"無法註銷處於 {self.status} 狀態的訂戶",
                {"current_status": self.status}
            )
        
        self.status = SubscriberStatus.DEACTIVATED
        self.deactivation_date = datetime.now()
        self.last_updated = datetime.now()
        
        if reason:
            self.notes = f"註銷原因: {reason}"
    
    def change_plan(self, new_plan_id: PlanID, reason: Optional[str] = None) -> None:
        """
        變更資費方案
        
        Args:
            new_plan_id: 新方案 ID
            reason: 變更原因
            
        Raises:
            BusinessRuleViolationError: 不符合變更條件
        """
        if not self.can_change_plan():
            raise BusinessRuleViolationError(
                f"無法變更處於 {self.status} 狀態的訂戶方案",
                {"current_status": self.status}
            )
        
        old_plan_id = self.plan_id
        self.plan_id = new_plan_id
        self.last_updated = datetime.now()
        
        note = f"方案變更: {old_plan_id} → {new_plan_id}"
        if reason:
            note += f" | 原因: {reason}"
        self.notes = note
    
    # ========== 帳齡計算 ==========
    
    def days_since_activation(self) -> Optional[int]:
        """
        計算啟用天數
        
        Returns:
            啟用天數，如果未啟用則返回 None
        """
        if not self.activation_date:
            return None
        
        delta = datetime.now() - self.activation_date
        return delta.days
    
    def days_since_suspension(self) -> Optional[int]:
        """
        計算暫停天數
        
        Returns:
            暫停天數，如果未暫停則返回 None
        """
        if not self.suspended_date:
            return None
        
        delta = datetime.now() - self.suspended_date
        return delta.days
    
    # ========== 輸出格式 ==========
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            'imei': self.imei,
            'account_number': self.account_number,
            'status': self.status.value,
            'plan_id': self.plan_id,
            'activation_date': self.activation_date.isoformat() if self.activation_date else None,
            'deactivation_date': self.deactivation_date.isoformat() if self.deactivation_date else None,
            'suspended_date': self.suspended_date.isoformat() if self.suspended_date else None,
            'last_updated': self.last_updated.isoformat(),
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Subscriber':
        """從字典建立訂戶"""
        return cls(
            imei=data['imei'],
            account_number=data['account_number'],
            status=SubscriberStatus(data['status']),
            plan_id=data['plan_id'],
            activation_date=datetime.fromisoformat(data['activation_date']) if data.get('activation_date') else None,
            deactivation_date=datetime.fromisoformat(data['deactivation_date']) if data.get('deactivation_date') else None,
            suspended_date=datetime.fromisoformat(data['suspended_date']) if data.get('suspended_date') else None,
            last_updated=datetime.fromisoformat(data['last_updated']) if data.get('last_updated') else datetime.now(),
            customer_id=data.get('customer_id'),
            customer_name=data.get('customer_name'),
            notes=data.get('notes')
        )
    
    def __str__(self) -> str:
        """字串表示"""
        return f"Subscriber(IMEI={self.imei}, Status={self.status.value}, Plan={self.plan_id})"
    
    def __repr__(self) -> str:
        """詳細表示"""
        return (
            f"Subscriber(imei='{self.imei}', "
            f"account_number='{self.account_number}', "
            f"status={self.status.value}, "
            f"plan_id='{self.plan_id}')"
        )

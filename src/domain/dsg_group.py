"""
Domain Models - DSG Group
DSG 群組領域模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from src.utils.types import GroupID, IMEI
from src.utils.exceptions import ValidationError, BusinessRuleViolationError


@dataclass
class DSGGroup:
    """
    DSG 群組領域模型
    
    代表一個 DSG (Data Sharing Group)，包含所有相關資訊和業務邏輯。
    
    Attributes:
        group_id: 群組 ID
        group_name: 群組名稱
        description: 描述
        member_imeis: 成員 IMEI 列表
        created_date: 建立日期
        status: 狀態
    """
    
    group_id: GroupID
    group_name: str
    description: str = ""
    member_imeis: List[IMEI] = field(default_factory=list)
    created_date: datetime = field(default_factory=datetime.now)
    status: str = "ACTIVE"
    
    # DSG 限制
    min_members: int = 2
    max_members: int = 10000
    
    def __post_init__(self):
        """初始化後驗證"""
        self.validate()
    
    def validate(self) -> None:
        """
        驗證 DSG 資料
        
        Raises:
            ValidationError: 資料驗證失敗
        """
        # 驗證群組名稱
        if not self.group_name or len(self.group_name) > 40:
            raise ValidationError(
                "群組名稱必須在 1-40 字元之間",
                {"group_name": self.group_name}
            )
        
        # 驗證成員數量
        if len(self.member_imeis) > 0:
            if len(self.member_imeis) < self.min_members:
                raise ValidationError(
                    f"DSG 至少需要 {self.min_members} 個成員",
                    {"current_count": len(self.member_imeis)}
                )
            
            if len(self.member_imeis) > self.max_members:
                raise ValidationError(
                    f"DSG 最多只能有 {self.max_members} 個成員",
                    {"current_count": len(self.member_imeis)}
                )
    
    # ========== 成員管理 ==========
    
    def add_member(self, imei: IMEI) -> None:
        """
        加入成員
        
        Args:
            imei: IMEI 號碼
            
        Raises:
            ValidationError: IMEI 格式錯誤
            BusinessRuleViolationError: 超過成員上限或重複
        """
        # 驗證 IMEI
        if not self._is_valid_imei(imei):
            raise ValidationError(
                f"無效的 IMEI: {imei}",
                {"imei": imei}
            )
        
        # 檢查是否重複
        if imei in self.member_imeis:
            raise BusinessRuleViolationError(
                f"IMEI {imei} 已存在於群組中",
                {"imei": imei, "group_id": self.group_id}
            )
        
        # 檢查成員上限
        if len(self.member_imeis) >= self.max_members:
            raise BusinessRuleViolationError(
                f"群組已達成員上限 {self.max_members}",
                {"current_count": len(self.member_imeis)}
            )
        
        self.member_imeis.append(imei)
    
    def remove_member(self, imei: IMEI) -> None:
        """
        移除成員
        
        Args:
            imei: IMEI 號碼
            
        Raises:
            ValidationError: IMEI 不存在
            BusinessRuleViolationError: 低於最小成員數
        """
        if imei not in self.member_imeis:
            raise ValidationError(
                f"IMEI {imei} 不在群組中",
                {"imei": imei, "group_id": self.group_id}
            )
        
        # 檢查最小成員數
        if len(self.member_imeis) <= self.min_members:
            raise BusinessRuleViolationError(
                f"群組至少需要 {self.min_members} 個成員",
                {"current_count": len(self.member_imeis)}
            )
        
        self.member_imeis.remove(imei)
    
    def add_members_bulk(self, imeis: List[IMEI]) -> None:
        """
        批次加入成員
        
        Args:
            imeis: IMEI 列表
        """
        for imei in imeis:
            self.add_member(imei)
    
    def remove_members_bulk(self, imeis: List[IMEI]) -> None:
        """
        批次移除成員
        
        Args:
            imeis: IMEI 列表
        """
        for imei in imeis:
            self.remove_member(imei)
    
    def has_member(self, imei: IMEI) -> bool:
        """檢查是否為成員"""
        return imei in self.member_imeis
    
    def get_member_count(self) -> int:
        """取得成員數量"""
        return len(self.member_imeis)
    
    # ========== 狀態管理 ==========
    
    def is_active(self) -> bool:
        """是否為啟用狀態"""
        return self.status == "ACTIVE"
    
    def can_add_members(self) -> bool:
        """是否可以加入成員"""
        return (
            self.is_active() and 
            len(self.member_imeis) < self.max_members
        )
    
    def can_remove_members(self) -> bool:
        """是否可以移除成員"""
        return (
            self.is_active() and 
            len(self.member_imeis) > self.min_members
        )
    
    # ========== 驗證方法 ==========
    
    @staticmethod
    def _is_valid_imei(imei: str) -> bool:
        """驗證 IMEI 格式"""
        return (
            isinstance(imei, str) and 
            len(imei) == 15 and 
            imei.isdigit()
        )
    
    # ========== 輸出格式 ==========
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            'group_id': self.group_id,
            'group_name': self.group_name,
            'description': self.description,
            'member_imeis': self.member_imeis,
            'member_count': len(self.member_imeis),
            'created_date': self.created_date.isoformat(),
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DSGGroup':
        """從字典建立 DSG 群組"""
        return cls(
            group_id=data['group_id'],
            group_name=data['group_name'],
            description=data.get('description', ''),
            member_imeis=data.get('member_imeis', []),
            created_date=datetime.fromisoformat(data['created_date']) if data.get('created_date') else datetime.now(),
            status=data.get('status', 'ACTIVE')
        )
    
    def __str__(self) -> str:
        """字串表示"""
        return f"DSGGroup(ID={self.group_id}, Name={self.group_name}, Members={len(self.member_imeis)})"

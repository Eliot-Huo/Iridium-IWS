"""
N3D 價格管理系統
支援價格版本管理和歷史記錄

設計原則：
1. 價格不寫死在程式碼中
2. 支援在助理頁面調整價格
3. 保留價格歷史記錄（計帳時用當時的價格）
4. 支援價格生效日期
"""
from __future__ import annotations
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path
import json
import math


@dataclass
class PlanPricing:
    """
    資費方案定價規則
    
    Attributes:
        plan_name: 方案名稱（如 "SBD0", "SBD12", "SBD17", "SBD30"）
        monthly_rate: 月租費（美元）
        included_bytes: 包含數據量（bytes）
        overage_per_1000: 超量費用（每 1000 bytes，美元）
        min_message_size: 最小計費訊息大小（bytes）
        activation_fee: 啟用費（美元）
        suspended_fee: 暫停月費（美元）
        mailbox_check_fee: Mailbox Check 費用（美元/次）
        registration_fee: SBD Registration 費用（美元/次）
        effective_date: 生效日期（YYYY-MM-DD）
        version: 價格版本號
        notes: 備註
    """
    plan_name: str
    monthly_rate: float
    included_bytes: int
    overage_per_1000: float
    min_message_size: int
    activation_fee: float
    suspended_fee: float
    mailbox_check_fee: float
    registration_fee: float
    effective_date: str  # YYYY-MM-DD
    version: int = 1
    notes: str = ""
    
    def calculate_overage_cost(self, total_bytes: int) -> float:
        """
        計算超量費用（無條件進位到整千）
        
        重要：超量額度以 1000 bytes 為單位，不足 1000 bytes 也要收完整費用
        例如：超量 1 byte 要收 1 × $2.00 = $2.00
             超量 1001 bytes 要收 2 × $2.00 = $4.00
        
        Args:
            total_bytes: 總使用數據量（bytes）
            
        Returns:
            超量費用（美元）
            
        Example:
            >>> pricing = PlanPricing(included_bytes=12000, overage_per_1000=2.00)
            >>> pricing.calculate_overage_cost(12001)  # 超量 1 byte
            2.0  # 收 1 個完整單位
            >>> pricing.calculate_overage_cost(13001)  # 超量 1001 bytes
            4.0  # 收 2 個完整單位
        """
        if total_bytes <= self.included_bytes:
            return 0.0
        
        overage_bytes = total_bytes - self.included_bytes
        
        # 無條件進位到整千
        overage_units = math.ceil(overage_bytes / 1000)
        
        return overage_units * self.overage_per_1000
    
    def apply_minimum_message_size(self, message_bytes: int) -> int:
        """
        應用最小計費訊息大小
        
        如果訊息小於最小值，按最小值計費
        
        Args:
            message_bytes: 實際訊息大小（bytes）
            
        Returns:
            計費大小（bytes）
        """
        return max(message_bytes, self.min_message_size)
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> PlanPricing:
        """從字典創建"""
        return cls(**data)


# ==================== Bundle ID 映射 ====================

# Bundle ID 對應方案名稱（從 IWS 查詢）
BUNDLE_TO_PLAN: Dict[str, str] = {
    '763925991': 'SBD0',
    '763924583': 'SBD12',
    '763927911': 'SBD17',
    '763925351': 'SBD30'
}

# 方案名稱對應 Bundle ID（反向查詢）
PLAN_TO_BUNDLE: Dict[str, str] = {
    'SBD0': '763925991',
    'SBD12': '763924583',
    'SBD17': '763927911',
    'SBD30': '763925351'
}


# ==================== 預設價格（初始值）====================

DEFAULT_PRICES: List[Dict] = [
    {
        'plan_name': 'SBD0',
        'monthly_rate': 20.00,
        'included_bytes': 0,
        'overage_per_1000': 2.10,
        'min_message_size': 30,
        'activation_fee': 0.00,
        'suspended_fee': 4.00,
        'mailbox_check_fee': 0.02,
        'registration_fee': 0.02,
        'effective_date': '2025-01-07',
        'version': 1,
        'notes': '初始價格（根據 SBD_Airtime_STD.pdf）'
    },
    {
        'plan_name': 'SBD12',
        'monthly_rate': 28.00,
        'included_bytes': 12000,
        'overage_per_1000': 2.00,
        'min_message_size': 10,
        'activation_fee': 50.00,
        'suspended_fee': 4.00,
        'mailbox_check_fee': 0.02,
        'registration_fee': 0.02,
        'effective_date': '2025-01-07',
        'version': 1,
        'notes': '初始價格（根據 SBD_Airtime_STD.pdf）'
    },
    {
        'plan_name': 'SBD17',
        'monthly_rate': 30.00,
        'included_bytes': 17000,
        'overage_per_1000': 1.60,
        'min_message_size': 10,
        'activation_fee': 50.00,
        'suspended_fee': 4.00,
        'mailbox_check_fee': 0.02,
        'registration_fee': 0.02,
        'effective_date': '2025-01-07',
        'version': 1,
        'notes': '初始價格（根據 SBD_Airtime_STD.pdf）'
    },
    {
        'plan_name': 'SBD30',
        'monthly_rate': 50.00,
        'included_bytes': 30000,
        'overage_per_1000': 1.50,
        'min_message_size': 10,
        'activation_fee': 50.00,
        'suspended_fee': 4.00,
        'mailbox_check_fee': 0.02,
        'registration_fee': 0.02,
        'effective_date': '2025-01-07',
        'version': 1,
        'notes': '初始價格（根據 SBD_Airtime_STD.pdf）'
    }
]


# ==================== 價格管理器 ====================

class PriceManager:
    """
    價格管理器
    
    功能：
    - 載入/儲存價格
    - 價格版本管理
    - 根據日期查詢有效價格
    - 新增/更新價格
    """
    
    def __init__(self, storage_path: str = 'price_history.json'):
        """
        初始化價格管理器
        
        Args:
            storage_path: 價格儲存檔案路徑
        """
        self.storage_path = Path(storage_path)
        self._ensure_storage_exists()
        self._prices: List[PlanPricing] = []
        self.load()
    
    def _ensure_storage_exists(self) -> None:
        """確保儲存檔案存在"""
        if not self.storage_path.exists():
            # 使用預設價格初始化
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_PRICES, f, indent=2, ensure_ascii=False)
    
    def load(self) -> None:
        """載入價格歷史"""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._prices = [PlanPricing.from_dict(item) for item in data]
            
            # 按生效日期降序排序（最新的在前面）
            self._prices.sort(
                key=lambda p: (p.plan_name, p.effective_date, p.version),
                reverse=True
            )
        except Exception as e:
            raise Exception(f"載入價格歷史失敗: {str(e)}")
    
    def save(self) -> None:
        """儲存價格歷史"""
        try:
            data = [p.to_dict() for p in self._prices]
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"儲存價格歷史失敗: {str(e)}")
    
    def get_current_price(self, plan_name: str) -> Optional[PlanPricing]:
        """
        取得當前有效的價格
        
        Args:
            plan_name: 方案名稱（如 "SBD12"）
            
        Returns:
            PlanPricing 物件，若找不到則返回 None
        """
        today = date.today().isoformat()
        
        for price in self._prices:
            if price.plan_name == plan_name and price.effective_date <= today:
                return price
        
        return None
    
    def get_price_at_date(self, plan_name: str, target_date: date) -> Optional[PlanPricing]:
        """
        取得指定日期的有效價格
        
        重要：計帳時必須使用當時的價格！
        
        Args:
            plan_name: 方案名稱
            target_date: 目標日期
            
        Returns:
            PlanPricing 物件，若找不到則返回 None
            
        Example:
            >>> # 查詢 2025年1月的價格
            >>> price = manager.get_price_at_date("SBD12", date(2025, 1, 15))
        """
        target_str = target_date.isoformat()
        
        for price in self._prices:
            if price.plan_name == plan_name and price.effective_date <= target_str:
                return price
        
        return None
    
    def get_all_current_prices(self) -> Dict[str, PlanPricing]:
        """
        取得所有方案的當前價格
        
        Returns:
            字典，鍵為方案名稱，值為 PlanPricing 物件
        """
        result = {}
        for plan_name in ['SBD0', 'SBD12', 'SBD17', 'SBD30']:
            price = self.get_current_price(plan_name)
            if price:
                result[plan_name] = price
        return result
    
    def get_price_history(self, plan_name: str) -> List[PlanPricing]:
        """
        取得指定方案的價格歷史
        
        Args:
            plan_name: 方案名稱
            
        Returns:
            價格歷史列表（按日期降序）
        """
        return [p for p in self._prices if p.plan_name == plan_name]
    
    def add_new_price(self, 
                     plan_name: str,
                     monthly_rate: float,
                     included_bytes: int,
                     overage_per_1000: float,
                     min_message_size: int,
                     activation_fee: float,
                     suspended_fee: float,
                     mailbox_check_fee: float,
                     registration_fee: float,
                     effective_date: str,
                     notes: str = "") -> PlanPricing:
        """
        新增價格版本
        
        Args:
            (各項價格參數)
            effective_date: 生效日期（YYYY-MM-DD）
            notes: 備註
            
        Returns:
            新建的 PlanPricing 物件
        """
        # 計算版本號
        existing = [p for p in self._prices if p.plan_name == plan_name]
        version = max([p.version for p in existing], default=0) + 1
        
        # 創建新價格
        new_price = PlanPricing(
            plan_name=plan_name,
            monthly_rate=monthly_rate,
            included_bytes=included_bytes,
            overage_per_1000=overage_per_1000,
            min_message_size=min_message_size,
            activation_fee=activation_fee,
            suspended_fee=suspended_fee,
            mailbox_check_fee=mailbox_check_fee,
            registration_fee=registration_fee,
            effective_date=effective_date,
            version=version,
            notes=notes
        )
        
        # 添加到列表
        self._prices.append(new_price)
        
        # 重新排序
        self._prices.sort(
            key=lambda p: (p.plan_name, p.effective_date, p.version),
            reverse=True
        )
        
        # 儲存
        self.save()
        
        return new_price
    
    def update_current_price(self,
                            plan_name: str,
                            **kwargs) -> Optional[PlanPricing]:
        """
        更新當前價格（創建新版本）
        
        Args:
            plan_name: 方案名稱
            **kwargs: 要更新的欄位
            
        Returns:
            新價格版本，若找不到當前價格則返回 None
            
        Example:
            >>> manager.update_current_price(
            ...     "SBD12",
            ...     monthly_rate=30.00,
            ...     effective_date="2025-02-01",
            ...     notes="價格調漲"
            ... )
        """
        current = self.get_current_price(plan_name)
        if not current:
            return None
        
        # 複製當前價格作為基礎
        new_data = current.to_dict()
        
        # 更新指定欄位
        new_data.update(kwargs)
        
        # 移除版本號（會自動重新計算）
        new_data.pop('version', None)
        
        # 創建新版本
        return self.add_new_price(**new_data)
    
    def get_plan_by_bundle_id(self, bundle_id: str) -> Optional[PlanPricing]:
        """
        根據 Bundle ID 取得當前價格
        
        Args:
            bundle_id: IWS Bundle ID（如 "763924583"）
            
        Returns:
            PlanPricing 物件，若找不到則返回 None
        """
        plan_name = BUNDLE_TO_PLAN.get(bundle_id)
        if not plan_name:
            return None
        return self.get_current_price(plan_name)


# ==================== 服務代碼定義 ====================

# TAP II Service Codes for SBD
SERVICE_CODE_SBD = '36'  # Short Burst Data
SERVICE_CODE_MAILBOX_CHECK = '81'  # Mailbox Check
SERVICE_CODE_REGISTRATION = '82'  # SBD Registration

# 服務代碼說明（用於報表顯示）
SERVICE_CODE_DESCRIPTIONS = {
    '36': 'Short Burst Data',
    '81': 'Mailbox Check',
    '82': 'SBD Registration'
}


def get_service_description(service_code: str) -> str:
    """
    取得服務代碼的描述
    
    Args:
        service_code: TAP II Service Code
        
    Returns:
        服務描述
    """
    return SERVICE_CODE_DESCRIPTIONS.get(service_code, f'Unknown Service ({service_code})')


# ==================== 全域價格管理器實例 ====================

# 全域價格管理器（在 app.py 初始化時創建）
_global_price_manager: Optional[PriceManager] = None


def get_price_manager() -> PriceManager:
    """
    取得全域價格管理器實例
    
    Returns:
        PriceManager 實例
    """
    global _global_price_manager
    if _global_price_manager is None:
        _global_price_manager = PriceManager('price_history.json')
    return _global_price_manager


def init_price_manager(storage_path: str = 'price_history.json') -> PriceManager:
    """
    初始化全域價格管理器
    
    Args:
        storage_path: 價格儲存檔案路徑
        
    Returns:
        PriceManager 實例
    """
    global _global_price_manager
    _global_price_manager = PriceManager(storage_path)
    return _global_price_manager

"""
Price Profile 資料模型
基於日期的價格管理系統
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path
import json


@dataclass
class PlanPricing:
    """
    單一方案的定價規則
    """
    plan_name: str                  # 方案名稱（如 "SBD12", "SBD12P"）
    monthly_rate: float             # 月租費（美元）
    included_bytes: int             # 包含數據量（bytes）
    overage_per_1000: float         # 超量費用（每 1000 bytes，美元）
    min_message_size: int           # 最小計費訊息大小（bytes）
    activation_fee: float           # 啟用費（美元）
    suspended_fee: float            # 暫停月費（美元）
    mailbox_check_fee: float        # Mailbox Check 費用（美元/次）
    registration_fee: float         # SBD Registration 費用（美元/次）
    
    # DSG 相關（選填）
    is_dsg: bool = False            # 是否為 DSG 方案
    min_isus: int = 1               # 最小 ISU 數量
    max_isus: int = 1               # 最大 ISU 數量
    max_dsgs: int = 0               # 最大 DSG 數量
    
    def calculate_overage_cost(self, total_bytes: int) -> float:
        """
        計算超量費用（無條件進位到整千）
        
        Args:
            total_bytes: 總使用數據量（bytes）
            
        Returns:
            超量費用（美元）
        """
        if total_bytes <= self.included_bytes:
            return 0.0
        
        overage_bytes = total_bytes - self.included_bytes
        
        # 無條件進位到整千
        import math
        overage_units = math.ceil(overage_bytes / 1000)
        
        return overage_units * self.overage_per_1000
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> PlanPricing:
        """從字典創建"""
        return cls(**data)


@dataclass
class PriceProfile:
    """
    價格 Profile
    
    包含特定時期的所有方案定價
    """
    profile_id: str                 # Profile ID（如 "customer_2025H2"）
    profile_name: str               # Profile 名稱
    profile_type: str               # Profile 類型："customer" 或 "iridium_cost"
    effective_date: str             # 生效日期（YYYY-MM-DD）
    is_locked: bool                 # 是否鎖定（生效後自動鎖定）
    created_at: str                 # 創建時間（ISO format）
    created_by: str                 # 創建者
    notes: str                      # 備註
    
    plans: Dict[str, PlanPricing]   # 方案定價（key: plan_name）
    
    def get_effective_date(self) -> date:
        """取得生效日期（date 物件）"""
        return datetime.strptime(self.effective_date, '%Y-%m-%d').date()
    
    def is_effective_at(self, query_date: date) -> bool:
        """判斷在特定日期是否生效"""
        return query_date >= self.get_effective_date()
    
    def should_be_locked(self) -> bool:
        """判斷是否應該被鎖定"""
        return datetime.now().date() >= self.get_effective_date()
    
    def lock(self):
        """鎖定 Profile"""
        self.is_locked = True
    
    def validate(self) -> List[str]:
        """
        驗證 Profile 完整性
        
        Returns:
            錯誤訊息列表（空列表表示驗證通過）
        """
        errors = []
        
        # 必須包含的方案
        required_plans = ['SBD0', 'SBD12', 'SBD17', 'SBD30', 'SBD12P', 'SBD17P', 'SBD30P']
        
        for plan in required_plans:
            if plan not in self.plans:
                errors.append(f"缺少方案定義: {plan}")
        
        # 檢查 DSG 方案的對應關係
        dsg_mappings = {
            'SBD12P': 'SBD12',
            'SBD17P': 'SBD17',
            'SBD30P': 'SBD30'
        }
        
        for dsg_plan, std_plan in dsg_mappings.items():
            if dsg_plan in self.plans and std_plan in self.plans:
                dsg_pricing = self.plans[dsg_plan]
                std_pricing = self.plans[std_plan]
                
                # 檢查包含量是否一致
                if dsg_pricing.included_bytes != std_pricing.included_bytes:
                    errors.append(
                        f"{dsg_plan} 的包含量 ({dsg_pricing.included_bytes}) "
                        f"與 {std_plan} ({std_pricing.included_bytes}) 不一致"
                    )
        
        return errors
    
    def to_dict(self) -> dict:
        """轉換為字典（用於儲存）"""
        return {
            'profile_id': self.profile_id,
            'profile_name': self.profile_name,
            'profile_type': self.profile_type,
            'effective_date': self.effective_date,
            'is_locked': self.is_locked,
            'created_at': self.created_at,
            'created_by': self.created_by,
            'notes': self.notes,
            'plans': {
                plan_name: pricing.to_dict()
                for plan_name, pricing in self.plans.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> PriceProfile:
        """從字典創建"""
        # 轉換 plans
        plans = {
            plan_name: PlanPricing.from_dict(pricing_data)
            for plan_name, pricing_data in data['plans'].items()
        }
        
        return cls(
            profile_id=data['profile_id'],
            profile_name=data['profile_name'],
            profile_type=data['profile_type'],
            effective_date=data['effective_date'],
            is_locked=data['is_locked'],
            created_at=data['created_at'],
            created_by=data['created_by'],
            notes=data['notes'],
            plans=plans
        )


class PriceProfileManager:
    """
    Price Profile 管理器
    
    管理多個 Profile 的載入、儲存、查詢
    """
    
    def __init__(self, storage_dir: str = 'price_profiles'):
        """
        初始化
        
        Args:
            storage_dir: Profile 儲存目錄
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.profiles: List[PriceProfile] = []
        self.load_all_profiles()
    
    def load_all_profiles(self):
        """載入所有 Profile"""
        self.profiles = []
        
        # 載入客戶售價 Profile
        customer_dir = self.storage_dir / 'customer'
        if customer_dir.exists():
            for file_path in customer_dir.glob('*.json'):
                try:
                    profile = self._load_profile_from_file(file_path)
                    self.profiles.append(profile)
                    print(f"✅ 載入 Profile: {profile.profile_id}")
                except Exception as e:
                    print(f"⚠️ 載入失敗 {file_path}: {e}")
        
        # 載入 Iridium 成本 Profile
        cost_dir = self.storage_dir / 'iridium_cost'
        if cost_dir.exists():
            for file_path in cost_dir.glob('*.json'):
                try:
                    profile = self._load_profile_from_file(file_path)
                    self.profiles.append(profile)
                    print(f"✅ 載入 Profile: {profile.profile_id}")
                except Exception as e:
                    print(f"⚠️ 載入失敗 {file_path}: {e}")
        
        # 排序（按生效日期）
        self.profiles.sort(key=lambda p: p.effective_date, reverse=True)
        
        # 自動鎖定已生效的 Profile
        self._auto_lock_profiles()
    
    def _load_profile_from_file(self, file_path: Path) -> PriceProfile:
        """從檔案載入 Profile"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return PriceProfile.from_dict(data)
    
    def _auto_lock_profiles(self):
        """自動鎖定已生效的 Profile"""
        for profile in self.profiles:
            if profile.should_be_locked() and not profile.is_locked:
                profile.lock()
                self.save_profile(profile)
                print(f"🔒 自動鎖定 Profile: {profile.profile_id}")
    
    def save_profile(self, profile: PriceProfile):
        """儲存 Profile"""
        # 確定儲存目錄
        if profile.profile_type == 'customer':
            target_dir = self.storage_dir / 'customer'
        elif profile.profile_type == 'iridium_cost':
            target_dir = self.storage_dir / 'iridium_cost'
        else:
            raise ValueError(f"未知的 profile_type: {profile.profile_type}")
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 儲存檔案
        file_path = target_dir / f"{profile.profile_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"💾 儲存 Profile: {file_path}")
    
    def get_profile_at_date(
        self,
        profile_type: str,
        query_date: date
    ) -> Optional[PriceProfile]:
        """
        查詢特定日期有效的 Profile
        
        Args:
            profile_type: Profile 類型（"customer" 或 "iridium_cost"）
            query_date: 查詢日期
            
        Returns:
            有效的 Profile，若找不到則返回 None
        """
        # 篩選符合類型的 Profile
        matching_profiles = [
            p for p in self.profiles
            if p.profile_type == profile_type and p.is_effective_at(query_date)
        ]
        
        if not matching_profiles:
            return None
        
        # 返回最新的（生效日期最接近查詢日期的）
        matching_profiles.sort(key=lambda p: p.effective_date, reverse=True)
        return matching_profiles[0]
    
    def get_plan_pricing(
        self,
        profile_type: str,
        plan_name: str,
        query_date: date
    ) -> Optional[PlanPricing]:
        """
        查詢特定日期、特定方案的定價
        
        Args:
            profile_type: Profile 類型
            plan_name: 方案名稱
            query_date: 查詢日期
            
        Returns:
            方案定價，若找不到則返回 None
        """
        profile = self.get_profile_at_date(profile_type, query_date)
        
        if not profile:
            return None
        
        return profile.plans.get(plan_name)
    
    def create_profile(
        self,
        profile_id: str,
        profile_name: str,
        profile_type: str,
        effective_date: str,
        created_by: str,
        notes: str,
        plans: Dict[str, Dict[str, Any]]
    ) -> PriceProfile:
        """
        創建新 Profile
        
        Args:
            profile_id: Profile ID
            profile_name: Profile 名稱
            profile_type: Profile 類型
            effective_date: 生效日期（YYYY-MM-DD）
            created_by: 創建者
            notes: 備註
            plans: 方案定價（dict）
            
        Returns:
            創建的 Profile
        """
        # 轉換 plans
        plan_pricings = {
            plan_name: PlanPricing(**pricing_data)
            for plan_name, pricing_data in plans.items()
        }
        
        # 創建 Profile
        profile = PriceProfile(
            profile_id=profile_id,
            profile_name=profile_name,
            profile_type=profile_type,
            effective_date=effective_date,
            is_locked=False,
            created_at=datetime.now().isoformat(),
            created_by=created_by,
            notes=notes,
            plans=plan_pricings
        )
        
        # 驗證
        errors = profile.validate()
        if errors:
            raise ValueError(f"Profile 驗證失敗:\n" + "\n".join(errors))
        
        # 儲存
        self.save_profile(profile)
        
        # 加入列表
        self.profiles.append(profile)
        self.profiles.sort(key=lambda p: p.effective_date, reverse=True)
        
        return profile
    
    def list_profiles(self, profile_type: Optional[str] = None) -> List[PriceProfile]:
        """
        列出所有 Profile
        
        Args:
            profile_type: 過濾 Profile 類型（可選）
            
        Returns:
            Profile 列表
        """
        if profile_type:
            return [p for p in self.profiles if p.profile_type == profile_type]
        return self.profiles

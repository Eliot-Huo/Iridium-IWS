"""
增強版費用計算器
Enhanced Billing Calculator

新功能：
1. 支持費率升級/降級邏輯
2. 支持暫停/恢復雙重收費
3. 支持行政手續費（第3次暫停起）
4. 整合設備歷史記錄
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Optional
from datetime import datetime, date
from dataclasses import dataclass

from src.config.price_rules import (
    PriceManager,
    PlanPricing,
    get_price_manager
)
from src.services.cdr_service import SimpleCDRRecord
from src.services.device_history import (
    DeviceHistoryManager,
    get_device_history_manager
)


@dataclass
class EnhancedMonthlyBill:
    """增強版月帳單"""
    imei: str                    # 設備 IMEI
    year: int                    # 年份
    month: int                   # 月份
    
    # 月初狀態
    month_start_plan: str        # 月初方案
    month_start_status: str      # 月初狀態
    
    # 計費方案（考慮升級）
    billing_plan: str            # 實際計費方案
    billing_plan_rate: float     # 計費方案月租費
    
    # 操作記錄
    plan_changes: List[Dict]     # 方案變更記錄
    status_changes: List[Dict]   # 狀態變更記錄
    suspend_count: int           # 暫停次數
    
    # 費用明細
    monthly_fee: float           # 月租費
    suspend_fee: float           # 暫停管理費
    admin_fee: float             # 行政手續費
    overage_fee: float           # 超量費
    other_fees: float            # 其他費用（Mailbox Check, Registration）
    
    # 總費用
    total_cost: float            # 總費用
    
    # 使用量（來自 CDR）
    total_bytes: int             # 總數據量
    message_count: int           # 訊息數量
    
    # 備註
    notes: List[str]             # 計費備註


class EnhancedBillingCalculator:
    """
    增強版費用計算器
    
    整合新的計費邏輯：
    - 升級當月生效
    - 降級次月生效
    - 暫停/恢復雙重收費
    - 行政手續費
    """
    
    def __init__(self,
                 price_manager: Optional[PriceManager] = None,
                 history_manager: Optional[DeviceHistoryManager] = None):
        """
        初始化增強版費用計算器
        
        Args:
            price_manager: 價格管理器
            history_manager: 歷史記錄管理器
        """
        self.price_manager = price_manager or get_price_manager()
        self.history_manager = history_manager or get_device_history_manager()
    
    def calculate_monthly_bill(self,
                              imei: str,
                              year: int,
                              month: int,
                              cdr_records: Optional[List[SimpleCDRRecord]] = None) -> EnhancedMonthlyBill:
        """
        計算月帳單（新邏輯）
        
        Args:
            imei: 設備 IMEI
            year: 年份
            month: 月份
            cdr_records: CDR 記錄（可選，用於計算超量費）
            
        Returns:
            EnhancedMonthlyBill: 增強版月帳單
        """
        # 1. 獲取月初狀態
        month_start_plan, month_start_status = self.history_manager.get_month_start_state(imei, year, month)
        
        if not month_start_plan:
            raise ValueError(f"設備 {imei} 在 {year}/{month} 未啟用")
        
        # 2. 確定計費方案（考慮升級）
        billing_plan = self._get_billing_plan(imei, year, month, month_start_plan)
        
        # 3. 獲取操作記錄
        plan_changes = self._get_plan_changes(imei, year, month)
        status_changes = self.history_manager.get_status_changes(imei, year, month)
        suspend_count = self.history_manager.count_suspend_actions(imei, year, month)
        
        # 4. 計算費用
        fees = self._calculate_fees(
            billing_plan=billing_plan,
            month_start_status=month_start_status,
            status_changes=status_changes,
            suspend_count=suspend_count,
            year=year,
            month=month
        )
        
        # 5. 計算使用量和超量費（如果有 CDR）
        total_bytes = 0
        message_count = 0
        overage_fee = 0.0
        
        if cdr_records:
            usage_result = self._calculate_usage_and_overage(
                cdr_records=cdr_records,
                billing_plan=billing_plan,
                year=year,
                month=month
            )
            total_bytes = usage_result['total_bytes']
            message_count = usage_result['message_count']
            overage_fee = usage_result['overage_fee']
        
        # 6. 生成備註
        notes = self._generate_notes(
            month_start_plan=month_start_plan,
            billing_plan=billing_plan,
            plan_changes=plan_changes,
            status_changes=status_changes,
            suspend_count=suspend_count
        )
        
        # 7. 計算總費用
        total_cost = (
            fees['monthly_fee'] +
            fees['suspend_fee'] +
            fees['admin_fee'] +
            overage_fee +
            fees['other_fees']
        )
        
        # 8. 創建帳單
        billing_plan_pricing = self.price_manager.get_price_at_date(
            billing_plan,
            date(year, month, 1)
        )
        
        return EnhancedMonthlyBill(
            imei=imei,
            year=year,
            month=month,
            month_start_plan=month_start_plan,
            month_start_status=month_start_status,
            billing_plan=billing_plan,
            billing_plan_rate=billing_plan_pricing.monthly_rate if billing_plan_pricing else 0.0,
            plan_changes=[self._operation_to_dict(op) for op in plan_changes],
            status_changes=[self._operation_to_dict(op) for op in status_changes],
            suspend_count=suspend_count,
            monthly_fee=fees['monthly_fee'],
            suspend_fee=fees['suspend_fee'],
            admin_fee=fees['admin_fee'],
            overage_fee=overage_fee,
            other_fees=fees['other_fees'],
            total_cost=total_cost,
            total_bytes=total_bytes,
            message_count=message_count,
            notes=notes
        )
    
    def _get_billing_plan(self, imei: str, year: int, month: int, month_start_plan: str) -> str:
        """
        確定計費方案
        
        規則：
        1. 從月初方案開始
        2. 檢查該月的升級（立即生效）
        3. 忽略降級（次月生效）
        """
        billing_plan = month_start_plan
        operations = self.history_manager.get_operations_in_month(imei, year, month)
        
        # 檢查升級
        for op in operations:
            if op.action == 'PLAN_CHANGE':
                if self.history_manager.is_upgrade(op.old_plan, op.new_plan):
                    # 升級 → 立即生效
                    billing_plan = op.new_plan
                # 降級忽略
        
        return billing_plan
    
    def _get_plan_changes(self, imei: str, year: int, month: int) -> List:
        """獲取方案變更記錄"""
        operations = self.history_manager.get_operations_in_month(imei, year, month)
        return [op for op in operations if op.action == 'PLAN_CHANGE']
    
    def _calculate_fees(self,
                       billing_plan: str,
                       month_start_status: str,
                       status_changes: List,
                       suspend_count: int,
                       year: int,
                       month: int) -> Dict[str, float]:
        """
        計算各項費用
        
        Returns:
            {
                'monthly_fee': 月租費,
                'suspend_fee': 暫停管理費,
                'admin_fee': 行政手續費,
                'other_fees': 其他費用
            }
        """
        # 獲取價格
        pricing = self.price_manager.get_price_at_date(billing_plan, date(year, month, 1))
        
        if not pricing:
            raise ValueError(f"找不到 {billing_plan} 在 {year}/{month} 的價格")
        
        monthly_rate = pricing.monthly_rate
        suspend_management_fee = 4.00  # 暫停管理費
        
        monthly_fee = 0.0
        suspend_fee = 0.0
        admin_fee = 0.0
        
        # 根據狀態變更計算費用
        if not status_changes:
            # 無狀態變更
            if month_start_status == 'SUSPENDED':
                # 整月暫停
                monthly_fee = pricing.suspended_fee if hasattr(pricing, 'suspended_fee') else 1.50
            else:
                # 整月正常
                monthly_fee = monthly_rate
        
        elif len(status_changes) == 1:
            # 一次狀態變更
            change = status_changes[0]
            
            if change.new_status == 'SUSPENDED':
                # ACTIVE → SUSPENDED
                monthly_fee = monthly_rate
                suspend_fee = suspend_management_fee
            else:
                # SUSPENDED → ACTIVE
                suspend_fee = suspend_management_fee
                monthly_fee = monthly_rate
        
        else:
            # 多次狀態變更（暫停又恢復）
            monthly_fee = monthly_rate + suspend_management_fee + monthly_rate
            # 注意：這裡簡化為固定模式，實際可以更精確
        
        # 行政手續費（第3次暫停起）
        if suspend_count >= 3:
            admin_fee = suspend_count * 20.00
        
        return {
            'monthly_fee': monthly_fee,
            'suspend_fee': suspend_fee,
            'admin_fee': admin_fee,
            'other_fees': 0.0  # 可以添加 Mailbox Check, Registration 等
        }
    
    def _calculate_usage_and_overage(self,
                                     cdr_records: List[SimpleCDRRecord],
                                     billing_plan: str,
                                     year: int,
                                     month: int) -> Dict:
        """
        計算使用量和超量費
        
        Returns:
            {
                'total_bytes': 總數據量,
                'message_count': 訊息數量,
                'overage_fee': 超量費用
            }
        """
        pricing = self.price_manager.get_price_at_date(billing_plan, date(year, month, 1))
        
        if not pricing:
            return {'total_bytes': 0, 'message_count': 0, 'overage_fee': 0.0}
        
        total_bytes = 0
        billable_bytes = 0
        
        for record in cdr_records:
            # 轉換 MB 到 bytes
            actual_bytes = int(record.data_mb * 1024 * 1024)
            
            # 應用最小訊息大小
            billable = pricing.apply_minimum_message_size(actual_bytes)
            
            total_bytes += actual_bytes
            billable_bytes += billable
        
        # 計算超量費用
        overage_fee = pricing.calculate_overage_cost(billable_bytes)
        
        return {
            'total_bytes': total_bytes,
            'message_count': len(cdr_records),
            'overage_fee': overage_fee
        }
    
    def _generate_notes(self,
                       month_start_plan: str,
                       billing_plan: str,
                       plan_changes: List,
                       status_changes: List,
                       suspend_count: int) -> List[str]:
        """生成計費備註"""
        notes = []
        
        # 方案升級說明
        if month_start_plan != billing_plan:
            notes.append(f"方案升級：{month_start_plan} → {billing_plan}（當月生效）")
        
        # 方案降級說明
        for change in plan_changes:
            if not self.history_manager.is_upgrade(change.old_plan, change.new_plan):
                notes.append(f"方案降級：{change.old_plan} → {change.new_plan}（次月生效）")
        
        # 狀態變更說明
        if status_changes:
            notes.append(f"狀態變更 {len(status_changes)} 次（雙重收費）")
        
        # 行政手續費說明
        if suspend_count >= 3:
            notes.append(f"頻繁暫停：{suspend_count} 次（加收行政手續費 ${suspend_count * 20.00:.2f}）")
        
        return notes
    
    def _operation_to_dict(self, operation) -> Dict:
        """將操作記錄轉換為字典"""
        return {
            'date': operation.date,
            'action': operation.action,
            'details': self._get_operation_details(operation)
        }
    
    def _get_operation_details(self, operation) -> str:
        """獲取操作詳情字串"""
        if operation.action == 'PLAN_CHANGE':
            upgrade_mark = '✓ 升級' if self.history_manager.is_upgrade(
                operation.old_plan, operation.new_plan
            ) else '✗ 降級'
            return f"{operation.old_plan} → {operation.new_plan} {upgrade_mark}"
        
        elif operation.action == 'STATUS_CHANGE':
            return f"{operation.old_status} → {operation.new_status}"
        
        return str(operation.action)


def get_enhanced_billing_calculator() -> EnhancedBillingCalculator:
    """獲取增強版計費計算器實例"""
    return EnhancedBillingCalculator()

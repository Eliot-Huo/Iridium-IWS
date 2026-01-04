"""
費用計算器
根據 CDR 記錄和 N3D 價格規則計算費用

設計原則：
1. 根據 CDR 數據計算實際使用量
2. 應用 N3D 價格規則（不是 Iridium 官方價格）
3. 支援歷史價格（計算舊帳單）
4. 處理最小訊息大小
5. 計算 Mailbox Check 和 Registration
"""
from __future__ import annotations
from typing import List, Dict, Tuple, Optional
from datetime import datetime, date
from dataclasses import dataclass

from src.config.price_rules import (
    PriceManager,
    PlanPricing,
    get_price_manager,
    SERVICE_CODE_SBD,
    SERVICE_CODE_MAILBOX_CHECK,
    SERVICE_CODE_REGISTRATION
)
from src.services.cdr_service import SimpleCDRRecord


@dataclass
class UsageDetail:
    """使用量明細"""
    date: str                    # 日期 (YYYY-MM-DD)
    message_count: int           # 訊息數量
    total_bytes: int             # 總數據量（bytes）
    billable_bytes: int          # 計費數據量（應用最小訊息後）
    mailbox_checks: int          # Mailbox Check 次數
    registrations: int           # Registration 次數
    cost: float                  # 當日費用


@dataclass
class MonthlyBill:
    """月帳單"""
    imei: str                    # 設備 IMEI
    plan_name: str               # 方案名稱
    year: int                    # 年份
    month: int                   # 月份
    
    # 價格資訊
    monthly_rate: float          # 月租費
    included_bytes: int          # 包含數據量
    
    # 使用量
    total_bytes: int             # 總數據量
    billable_bytes: int          # 計費數據量
    message_count: int           # 訊息數量
    mailbox_checks: int          # Mailbox Check 次數
    registrations: int           # Registration 次數
    
    # 費用
    base_fee: float              # 月租費
    overage_cost: float          # 超量費用
    mailbox_cost: float          # Mailbox Check 費用
    registration_cost: float     # Registration 費用
    total_cost: float            # 總費用
    
    # 明細
    daily_usage: List[UsageDetail]  # 每日使用明細
    records: List[SimpleCDRRecord]  # 原始 CDR 記錄


class BillingCalculator:
    """
    費用計算器
    
    根據 CDR 記錄和價格規則計算費用
    """
    
    def __init__(self, price_manager: Optional[PriceManager] = None):
        """
        初始化費用計算器
        
        Args:
            price_manager: 價格管理器（若未提供則使用全域實例）
        """
        self.price_manager = price_manager or get_price_manager()
    
    def calculate_monthly_bill(self,
                              imei: str,
                              plan_name: str,
                              year: int,
                              month: int,
                              records: List[SimpleCDRRecord],
                              account_status: str = 'ACTIVE') -> MonthlyBill:
        """
        計算月帳單
        
        Args:
            imei: 設備 IMEI
            plan_name: 方案名稱（如 "SBD12"）
            year: 年份
            month: 月份（1-12）
            records: CDR 記錄列表
            account_status: 帳號狀態（ACTIVE/SUSPENDED）
            
        Returns:
            MonthlyBill: 月帳單
            
        Example:
            >>> calculator = BillingCalculator()
            >>> bill = calculator.calculate_monthly_bill(
            ...     imei="301434061230580",
            ...     plan_name="SBD12",
            ...     year=2025,
            ...     month=1,
            ...     records=cdr_records
            ... )
            >>> print(f"總費用: ${bill.total_cost:.2f}")
        """
        # 1. 取得該月有效的價格
        billing_date = date(year, month, 1)
        pricing = self.price_manager.get_price_at_date(plan_name, billing_date)
        
        if not pricing:
            raise ValueError(f"找不到 {plan_name} 在 {year}/{month} 的有效價格")
        
        # 2. 處理暫停狀態
        if account_status == 'SUSPENDED':
            return self._create_suspended_bill(
                imei=imei,
                plan_name=plan_name,
                year=year,
                month=month,
                pricing=pricing,
                records=records
            )
        
        # 3. 分類 CDR 記錄
        sbd_records = []
        mailbox_checks = 0
        registrations = 0
        
        for record in records:
            if record.service_code == SERVICE_CODE_SBD:
                sbd_records.append(record)
            elif record.service_code == SERVICE_CODE_MAILBOX_CHECK:
                mailbox_checks += 1
            elif record.service_code == SERVICE_CODE_REGISTRATION:
                registrations += 1
        
        # 4. 計算數據量（應用最小訊息大小）
        total_bytes = 0
        billable_bytes = 0
        
        for record in sbd_records:
            # 轉換 MB 到 bytes
            actual_bytes = int(record.data_mb * 1024 * 1024)
            
            # 應用最小訊息大小
            billable = pricing.apply_minimum_message_size(actual_bytes)
            
            total_bytes += actual_bytes
            billable_bytes += billable
        
        # 5. 計算費用
        base_fee = pricing.monthly_rate
        overage_cost = pricing.calculate_overage_cost(billable_bytes)
        mailbox_cost = mailbox_checks * pricing.mailbox_check_fee
        registration_cost = registrations * pricing.registration_fee
        total_cost = base_fee + overage_cost + mailbox_cost + registration_cost
        
        # 6. 生成每日明細
        daily_usage = self._calculate_daily_usage(sbd_records, pricing)
        
        # 7. 創建帳單
        return MonthlyBill(
            imei=imei,
            plan_name=plan_name,
            year=year,
            month=month,
            monthly_rate=pricing.monthly_rate,
            included_bytes=pricing.included_bytes,
            total_bytes=total_bytes,
            billable_bytes=billable_bytes,
            message_count=len(sbd_records),
            mailbox_checks=mailbox_checks,
            registrations=registrations,
            base_fee=base_fee,
            overage_cost=overage_cost,
            mailbox_cost=mailbox_cost,
            registration_cost=registration_cost,
            total_cost=total_cost,
            daily_usage=daily_usage,
            records=records
        )
    
    def _create_suspended_bill(self,
                              imei: str,
                              plan_name: str,
                              year: int,
                              month: int,
                              pricing: PlanPricing,
                              records: List[SimpleCDRRecord]) -> MonthlyBill:
        """
        創建暫停期間的帳單
        
        暫停期間只收取暫停月費，不計算數據使用
        """
        return MonthlyBill(
            imei=imei,
            plan_name=plan_name,
            year=year,
            month=month,
            monthly_rate=pricing.suspended_fee,
            included_bytes=0,
            total_bytes=0,
            billable_bytes=0,
            message_count=0,
            mailbox_checks=0,
            registrations=0,
            base_fee=pricing.suspended_fee,
            overage_cost=0.0,
            mailbox_cost=0.0,
            registration_cost=0.0,
            total_cost=pricing.suspended_fee,
            daily_usage=[],
            records=records
        )
    
    def _calculate_daily_usage(self,
                              records: List[SimpleCDRRecord],
                              pricing: PlanPricing) -> List[UsageDetail]:
        """
        計算每日使用明細
        
        Args:
            records: SBD 記錄列表
            pricing: 價格規則
            
        Returns:
            每日使用明細列表
        """
        # 按日期分組
        daily_data: Dict[str, List[SimpleCDRRecord]] = {}
        
        for record in records:
            date_str = record.call_datetime.strftime('%Y-%m-%d')
            if date_str not in daily_data:
                daily_data[date_str] = []
            daily_data[date_str].append(record)
        
        # 計算每日統計
        daily_usage = []
        
        for date_str in sorted(daily_data.keys()):
            day_records = daily_data[date_str]
            
            total_bytes = 0
            billable_bytes = 0
            mailbox_checks = 0
            registrations = 0
            
            for record in day_records:
                actual_bytes = int(record.data_mb * 1024 * 1024)
                billable = pricing.apply_minimum_message_size(actual_bytes)
                
                total_bytes += actual_bytes
                billable_bytes += billable
                
                # 統計 Mailbox Check 和 Registration
                if actual_bytes == 0 or record.data_mb == 0:
                    mailbox_checks += 1
                # 可以根據其他條件判斷 registrations
            
            # 簡化：每日費用按比例分配（實際應該累計計算超量）
            # 這裡先用簡單方式
            daily_cost = 0.0  # 可以改進為更精確的計算
            
            daily_usage.append(UsageDetail(
                date=date_str,
                message_count=len(day_records),
                total_bytes=total_bytes,
                billable_bytes=billable_bytes,
                mailbox_checks=mailbox_checks,
                registrations=registrations,
                cost=daily_cost
            ))
        
        return daily_usage
    
    def calculate_record_cost(self,
                             record: SimpleCDRRecord,
                             pricing: PlanPricing) -> Tuple[int, int, float]:
        """
        計算單筆記錄的費用
        
        Args:
            record: CDR 記錄
            pricing: 價格規則
            
        Returns:
            (actual_bytes, billable_bytes, cost)
        """
        # 轉換 MB 到 bytes
        actual_bytes = int(record.data_mb * 1024 * 1024)
        
        # 應用最小訊息大小
        billable_bytes = pricing.apply_minimum_message_size(actual_bytes)
        
        # 計算費用（簡化：按單筆計算）
        # 實際應該累計後再計算超量
        cost_per_1000 = pricing.overage_per_1000
        cost = (billable_bytes / 1000.0) * cost_per_1000
        
        return actual_bytes, billable_bytes, cost

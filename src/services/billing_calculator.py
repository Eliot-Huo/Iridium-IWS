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
    
    # 利潤資訊（新增）
    iridium_cost: float = 0.0           # Iridium 成本
    profit: float = 0.0                  # 利潤
    profit_margin: float = 0.0           # 利潤率 (%)
    
    # 明細
    daily_usage: List[UsageDetail]  # 每日使用明細
    records: List[SimpleCDRRecord]  # 原始 CDR 記錄


class BillingCalculator:
    """
    費用計算器
    
    根據 CDR 記錄和 Price Profile 計算費用
    支援跨 Profile 計算
    """
    
    def __init__(self, 
                 profile_manager: Optional['PriceProfileManager'] = None):
        """
        初始化費用計算器
        
        Args:
            profile_manager: Price Profile 管理器
        """
        if profile_manager is None:
            from ..config.price_profile import PriceProfileManager
            profile_manager = PriceProfileManager()
        
        self.profile_manager = profile_manager
    
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
        
        # 5. 計算費用（客戶售價）
        base_fee = pricing.monthly_rate
        overage_cost = pricing.calculate_overage_cost(billable_bytes)
        mailbox_cost = mailbox_checks * pricing.mailbox_check_fee
        registration_cost = registrations * pricing.registration_fee
        total_cost = base_fee + overage_cost + mailbox_cost + registration_cost
        
        # 6. 計算 Iridium 成本
        try:
            cost_pricing = self.cost_price_manager.get_price_at_date(plan_name, billing_date)
            
            if cost_pricing:
                # 成本價計算
                iridium_base_fee = cost_pricing.monthly_rate
                iridium_overage_cost = cost_pricing.calculate_overage_cost(billable_bytes)
                iridium_mailbox_cost = mailbox_checks * cost_pricing.mailbox_check_fee
                iridium_registration_cost = registrations * cost_pricing.registration_fee
                iridium_cost = iridium_base_fee + iridium_overage_cost + iridium_mailbox_cost + iridium_registration_cost
                
                # 利潤計算
                profit = total_cost - iridium_cost
                profit_margin = (profit / total_cost * 100) if total_cost > 0 else 0.0
            else:
                # 找不到成本價格，設為 0
                iridium_cost = 0.0
                profit = 0.0
                profit_margin = 0.0
        except Exception as e:
            # 計算失敗，設為 0
            print(f"⚠️ 成本計算失敗: {e}")
            iridium_cost = 0.0
            profit = 0.0
            profit_margin = 0.0
        
        # 7. 生成每日明細
        daily_usage = self._calculate_daily_usage(sbd_records, pricing)
        
        # 8. 創建帳單（含利潤資訊）
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
            iridium_cost=iridium_cost,
            profit=profit,
            profit_margin=profit_margin,
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
                
                # 統計 Mailbox Check（資料量為 0 的記錄）
                if actual_bytes == 0 or record.data_mb == 0:
                    mailbox_checks += 1
            
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
    
    def calculate_monthly_bill_with_profile(
        self,
        imei: str,
        year: int,
        month: int,
        plan_name: str,
        records: List[SimpleCDRRecord]
    ) -> MonthlyBill:
        """
        使用 Price Profile 計算月帳單
        
        重要：
        1. 月租費以每月 1 號的 Profile 為準（不做比例分配）
        2. 超量計算使用月總量（累計）
        3. 如果月中有 Profile 變更，分段計算包含量
        
        Args:
            imei: 設備 IMEI
            year: 年份
            month: 月份
            plan_name: 方案名稱
            records: CDR 記錄列表
            
        Returns:
            月帳單
        """
        from datetime import date, datetime
        
        if not records:
            # 沒有記錄，返回只有月租的帳單
            return self._create_empty_bill(imei, year, month, plan_name)
        
        # 月份的第一天和最後一天
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)
        
        # 1. 取得月初（1號）的 Profile
        customer_profile = self.profile_manager.get_profile_at_date('customer', month_start)
        cost_profile = self.profile_manager.get_profile_at_date('iridium_cost', month_start)
        
        if not customer_profile or not cost_profile:
            raise ValueError(f"找不到 {year}/{month} 的有效 Profile")
        
        if plan_name not in customer_profile.plans or plan_name not in cost_profile.plans:
            raise ValueError(f"Profile 中找不到方案: {plan_name}")
        
        customer_pricing = customer_profile.plans[plan_name]
        cost_pricing = cost_profile.plans[plan_name]
        
        # 2. 檢查是否有跨 Profile（月中 Profile 變更）
        profile_changes = self._detect_profile_changes(month_start, month_end)
        
        if len(profile_changes) > 1:
            # 有跨 Profile，需要分段計算
            print(f"📋 偵測到 {len(profile_changes)} 個 Profile，分段計算包含量")
            return self._calculate_cross_profile_bill(
                imei, year, month, plan_name, records, profile_changes
            )
        
        # 3. 單一 Profile，直接計算
        # 統計用量
        total_bytes, billable_bytes, mailbox_checks, registrations = self._calculate_usage_stats(
            records, customer_pricing
        )
        
        # 4. 計算客戶費用
        base_fee = customer_pricing.monthly_rate
        overage_cost = customer_pricing.calculate_overage_cost(billable_bytes)
        mailbox_cost = mailbox_checks * customer_pricing.mailbox_check_fee
        registration_cost = registrations * customer_pricing.registration_fee
        total_customer_cost = base_fee + overage_cost + mailbox_cost + registration_cost
        
        # 5. 計算 Iridium 成本
        cost_base_fee = cost_pricing.monthly_rate
        cost_overage = cost_pricing.calculate_overage_cost(billable_bytes)
        cost_mailbox = mailbox_checks * cost_pricing.mailbox_check_fee
        cost_registration = registrations * cost_pricing.registration_fee
        total_iridium_cost = cost_base_fee + cost_overage + cost_mailbox + cost_registration
        
        # 6. 計算利潤
        profit = total_customer_cost - total_iridium_cost
        profit_margin = (profit / total_customer_cost * 100) if total_customer_cost > 0 else 0.0
        
        # 7. 生成每日明細
        daily_usage = self._calculate_daily_usage(records, customer_pricing)
        
        # 8. 創建帳單
        return MonthlyBill(
            imei=imei,
            plan_name=plan_name,
            year=year,
            month=month,
            monthly_rate=customer_pricing.monthly_rate,
            included_bytes=customer_pricing.included_bytes,
            total_bytes=total_bytes,
            billable_bytes=billable_bytes,
            message_count=len(records),
            mailbox_checks=mailbox_checks,
            registrations=registrations,
            base_fee=base_fee,
            overage_cost=overage_cost,
            mailbox_cost=mailbox_cost,
            registration_cost=registration_cost,
            total_cost=total_customer_cost,
            iridium_cost=total_iridium_cost,
            profit=profit,
            profit_margin=profit_margin,
            daily_usage=daily_usage,
            records=records
        )
    
    def _detect_profile_changes(self, start_date, end_date):
        """偵測時間範圍內的 Profile 變更"""
        from datetime import timedelta
        
        changes = []
        current_date = start_date
        
        while current_date < end_date:
            customer_profile = self.profile_manager.get_profile_at_date('customer', current_date)
            
            if not changes or changes[-1]['profile_id'] != customer_profile.profile_id:
                changes.append({
                    'date': current_date,
                    'profile_id': customer_profile.profile_id
                })
            
            current_date += timedelta(days=1)
        
        return changes
    
    def _calculate_cross_profile_bill(
        self,
        imei: str,
        year: int,
        month: int,
        plan_name: str,
        records: List[SimpleCDRRecord],
        profile_changes: List[dict]
    ) -> MonthlyBill:
        """
        跨 Profile 計算（分段計算包含量，累計判斷超量）
        
        邏輯：
        1. 月租費：使用月初（1號）的 Profile
        2. 包含量：按每個 Profile 的天數比例計算，加總
        3. 超量：月總用量 - 總包含量
        """
        from datetime import date
        
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)
        
        # 月初 Profile（用於月租費）
        customer_profile_first = self.profile_manager.get_profile_at_date('customer', month_start)
        cost_profile_first = self.profile_manager.get_profile_at_date('iridium_cost', month_start)
        
        customer_pricing_first = customer_profile_first.plans[plan_name]
        cost_pricing_first = cost_profile_first.plans[plan_name]
        
        # 統計總用量
        total_bytes, billable_bytes, mailbox_checks, registrations = self._calculate_usage_stats(
            records, customer_pricing_first
        )
        
        # 計算分段包含量
        from datetime import timedelta
        
        total_customer_included = 0
        total_cost_included = 0
        month_days = (month_end - month_start).days
        
        for i, change in enumerate(profile_changes):
            # 計算這個 Profile 的天數
            change_start = change['date']
            if i < len(profile_changes) - 1:
                change_end = profile_changes[i + 1]['date']
            else:
                change_end = month_end
            
            period_days = (change_end - change_start).days
            
            # 取得 Profile
            customer_profile = self.profile_manager.get_profile_at_date('customer', change_start)
            cost_profile = self.profile_manager.get_profile_at_date('iridium_cost', change_start)
            
            customer_pricing = customer_profile.plans[plan_name]
            cost_pricing = cost_profile.plans[plan_name]
            
            # 按比例計算包含量
            customer_included_this_period = int(customer_pricing.included_bytes * period_days / month_days)
            cost_included_this_period = int(cost_pricing.included_bytes * period_days / month_days)
            
            total_customer_included += customer_included_this_period
            total_cost_included += cost_included_this_period
            
            print(f"  📊 Profile {i+1} ({change_start} ~ {change_end}): "
                  f"{period_days}天, 包含 {customer_included_this_period:,} bytes")
        
        print(f"  📊 月總包含量: {total_customer_included:,} bytes")
        print(f"  📊 月總用量: {billable_bytes:,} bytes")
        
        # 計算超量
        customer_overage_bytes = max(0, billable_bytes - total_customer_included)
        cost_overage_bytes = max(0, billable_bytes - total_cost_included)
        
        # 計算費用
        import math
        
        base_fee = customer_pricing_first.monthly_rate
        overage_cost = math.ceil(customer_overage_bytes / 1000) * customer_pricing_first.overage_per_1000
        mailbox_cost = mailbox_checks * customer_pricing_first.mailbox_check_fee
        registration_cost = registrations * customer_pricing_first.registration_fee
        total_customer_cost = base_fee + overage_cost + mailbox_cost + registration_cost
        
        cost_base_fee = cost_pricing_first.monthly_rate
        cost_overage = math.ceil(cost_overage_bytes / 1000) * cost_pricing_first.overage_per_1000
        cost_mailbox = mailbox_checks * cost_pricing_first.mailbox_check_fee
        cost_registration = registrations * cost_pricing_first.registration_fee
        total_iridium_cost = cost_base_fee + cost_overage + cost_mailbox + cost_registration
        
        # 計算利潤
        profit = total_customer_cost - total_iridium_cost
        profit_margin = (profit / total_customer_cost * 100) if total_customer_cost > 0 else 0.0
        
        # 生成每日明細
        daily_usage = self._calculate_daily_usage(records, customer_pricing_first)
        
        return MonthlyBill(
            imei=imei,
            plan_name=f"{plan_name} (跨Profile)",
            year=year,
            month=month,
            monthly_rate=customer_pricing_first.monthly_rate,
            included_bytes=total_customer_included,  # 使用計算後的總包含量
            total_bytes=total_bytes,
            billable_bytes=billable_bytes,
            message_count=len(records),
            mailbox_checks=mailbox_checks,
            registrations=registrations,
            base_fee=base_fee,
            overage_cost=overage_cost,
            mailbox_cost=mailbox_cost,
            registration_cost=registration_cost,
            total_cost=total_customer_cost,
            iridium_cost=total_iridium_cost,
            profit=profit,
            profit_margin=profit_margin,
            daily_usage=daily_usage,
            records=records
        )
    
    def _calculate_usage_stats(self, records, pricing):
        """計算使用量統計"""
        total_bytes = 0
        billable_bytes = 0
        mailbox_checks = 0
        registrations = 0
        
        for record in records:
            # 實際數據量
            actual_bytes = int(record.data_mb * 1024 * 1024)
            total_bytes += actual_bytes
            
            # 應用最小計費大小
            billable = max(actual_bytes, pricing.min_message_size)
            billable_bytes += billable
            
            # Mailbox Check（數據量為 0）
            if actual_bytes == 0:
                mailbox_checks += 1
            
            # Registration
            if hasattr(record, 'service_code') and record.service_code == '82':
                registrations += 1
        
        return total_bytes, billable_bytes, mailbox_checks, registrations
    
    def _create_empty_bill(self, imei, year, month, plan_name):
        """創建空帳單（只有月租費）"""
        from datetime import date
        
        month_start = date(year, month, 1)
        
        customer_profile = self.profile_manager.get_profile_at_date('customer', month_start)
        cost_profile = self.profile_manager.get_profile_at_date('iridium_cost', month_start)
        
        if not customer_profile or not cost_profile:
            raise ValueError(f"找不到 {year}/{month} 的有效 Profile")
        
        customer_pricing = customer_profile.plans[plan_name]
        cost_pricing = cost_profile.plans[plan_name]
        
        base_fee = customer_pricing.monthly_rate
        cost_base_fee = cost_pricing.monthly_rate
        
        profit = base_fee - cost_base_fee
        profit_margin = (profit / base_fee * 100) if base_fee > 0 else 0.0
        
        return MonthlyBill(
            imei=imei,
            plan_name=plan_name,
            year=year,
            month=month,
            monthly_rate=customer_pricing.monthly_rate,
            included_bytes=customer_pricing.included_bytes,
            total_bytes=0,
            billable_bytes=0,
            message_count=0,
            mailbox_checks=0,
            registrations=0,
            base_fee=base_fee,
            overage_cost=0.0,
            mailbox_cost=0.0,
            registration_cost=0.0,
            total_cost=base_fee,
            iridium_cost=cost_base_fee,
            profit=profit,
            profit_margin=profit_margin,
            daily_usage=[],
            records=[]
        )
    
    def calculate_monthly_bill_with_history(
        self,
        imei: str,
        year: int,
        month: int,
        plan_name: str,
        records: List[SimpleCDRRecord]
    ) -> MonthlyBill:
        """
        計算月帳單（考慮方案變更歷史）
        
        如果有提供 history_service，會查詢該月的方案變更記錄，
        並根據不同時期使用不同的方案計算費用。
        
        Args:
            imei: 設備 IMEI
            year: 年份
            month: 月份
            plan_name: 當前方案名稱（作為後備）
            records: CDR 記錄列表
            
        Returns:
            月帳單
        """
        if not self.history_service or not records:
            # 沒有歷史服務或沒有記錄，使用標準計算
            return self.calculate_monthly_bill(
                imei=imei,
                year=year,
                month=month,
                plan_name=plan_name,
                records=records
            )
        
        try:
            # 查詢該月的方案變更歷史
            from datetime import date
            start_date = date(year, month, 1)
            
            # 計算月末
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            
            plan_changes = self.history_service.get_plan_change_history(
                imei=imei,
                start_date=start_date,
                end_date=end_date
            )
            
            if not plan_changes:
                # 沒有方案變更，使用標準計算
                print(f"ℹ️ 該月無方案變更記錄，使用單一方案計算")
                return self.calculate_monthly_bill(
                    imei=imei,
                    year=year,
                    month=month,
                    plan_name=plan_name,
                    records=records
                )
            
            # 有方案變更，按時期分組計算
            print(f"📋 偵測到 {len(plan_changes)} 次方案變更，按時期計算")
            
            # 建立時間段 → 方案對應表
            plan_periods = self._build_plan_periods(plan_changes, start_date, end_date)
            
            # 將 CDR 按時期分組
            grouped_records = self._group_records_by_period(records, plan_periods)
            
            # 對每個時期計算費用
            total_customer_cost = 0.0
            total_iridium_cost = 0.0
            total_bytes = 0
            total_billable = 0
            total_messages = 0
            total_mailbox = 0
            total_registrations = 0
            all_daily_usage = []
            
            for period_plan, period_records in grouped_records.items():
                period_date = period_records[0].call_datetime.date()
                
                # 客戶售價
                customer_pricing = self.price_manager.get_price_at_date(
                    period_plan,
                    period_date
                )
                
                # Iridium 成本價
                iridium_pricing = self.cost_price_manager.get_price_at_date(
                    period_plan,
                    period_date
                )
                
                if not customer_pricing or not iridium_pricing:
                    print(f"⚠️ 找不到 {period_plan} 在 {period_date} 的價格，跳過")
                    continue
                
                # 計算該時期的統計
                period_bytes, period_billable, period_mailbox, period_reg = self._calculate_period_stats(
                    period_records
                )
                
                # 計算該時期的費用
                period_customer_cost = self._calculate_period_cost(
                    period_billable,
                    period_mailbox,
                    period_reg,
                    customer_pricing
                )
                
                period_iridium_cost = self._calculate_period_cost(
                    period_billable,
                    period_mailbox,
                    period_reg,
                    iridium_pricing
                )
                
                print(f"  📊 {period_plan}: 客戶 ${period_customer_cost:.2f} / 成本 ${period_iridium_cost:.2f}")
                
                total_customer_cost += period_customer_cost
                total_iridium_cost += period_iridium_cost
                total_bytes += period_bytes
                total_billable += period_billable
                total_messages += len(period_records)
                total_mailbox += period_mailbox
                total_registrations += period_reg
            
            # 計算利潤
            profit = total_customer_cost - total_iridium_cost
            profit_margin = (profit / total_customer_cost * 100) if total_customer_cost > 0 else 0.0
            
            # 使用最後一個方案作為顯示方案
            final_plan = plan_changes[-1].new_plan if plan_changes else plan_name
            final_pricing = self.price_manager.get_price_at_date(final_plan, end_date)
            
            # 生成每日明細（簡化版）
            daily_usage = self._calculate_daily_usage(records, final_pricing or customer_pricing)
            
            return MonthlyBill(
                imei=imei,
                plan_name=f"{final_plan} (含變更)",
                year=year,
                month=month,
                monthly_rate=final_pricing.monthly_rate if final_pricing else 0,
                included_bytes=final_pricing.included_bytes if final_pricing else 0,
                total_bytes=total_bytes,
                billable_bytes=total_billable,
                message_count=total_messages,
                mailbox_checks=total_mailbox,
                registrations=total_registrations,
                base_fee=0,  # 這裡簡化
                overage_cost=total_customer_cost,  # 總費用
                mailbox_cost=0,
                registration_cost=0,
                total_cost=total_customer_cost,
                iridium_cost=total_iridium_cost,
                profit=profit,
                profit_margin=profit_margin,
                daily_usage=daily_usage,
                records=records
            )
            
        except Exception as e:
            print(f"⚠️ 方案歷史計算失敗，降級使用標準計算: {e}")
            import traceback
            traceback.print_exc()
            return self.calculate_monthly_bill(
                imei=imei,
                year=year,
                month=month,
                plan_name=plan_name,
                records=records
            )
    
    def _build_plan_periods(self, plan_changes, start_date, end_date):
        """建立時間段 → 方案對應表"""
        periods = []
        
        for i, change in enumerate(plan_changes):
            period_start = max(change.transaction_date.date(), start_date)
            
            if i < len(plan_changes) - 1:
                period_end = plan_changes[i + 1].transaction_date.date()
            else:
                period_end = end_date
            
            periods.append({
                'start': period_start,
                'end': period_end,
                'plan': change.new_plan
            })
        
        return periods
    
    def _group_records_by_period(self, records, plan_periods):
        """將 CDR 記錄按時期分組"""
        grouped = {}
        
        for record in records:
            record_date = record.call_datetime.date()
            
            for period in plan_periods:
                if period['start'] <= record_date < period['end']:
                    plan_name = period['plan']
                    if plan_name not in grouped:
                        grouped[plan_name] = []
                    grouped[plan_name].append(record)
                    break
        
        return grouped
    
    def _calculate_period_stats(self, records):
        """計算時期統計"""
        total_bytes = 0
        billable_bytes = 0
        mailbox_checks = 0
        registrations = 0
        
        for record in records:
            actual_bytes = int(record.data_mb * 1024 * 1024)
            total_bytes += actual_bytes
            billable_bytes += max(actual_bytes, 10)  # 簡化：最小 10 bytes
            
            if actual_bytes == 0:
                mailbox_checks += 1
            
            if record.service_code == '82':
                registrations += 1
        
        return total_bytes, billable_bytes, mailbox_checks, registrations
    
    def _calculate_period_cost(self, billable_bytes, mailbox_checks, registrations, pricing):
        """計算時期費用"""
        base_fee = pricing.monthly_rate
        overage_cost = pricing.calculate_overage_cost(billable_bytes)
        mailbox_cost = mailbox_checks * pricing.mailbox_check_fee
        registration_cost = registrations * pricing.registration_fee
        
        return base_fee + overage_cost + mailbox_cost + registration_cost


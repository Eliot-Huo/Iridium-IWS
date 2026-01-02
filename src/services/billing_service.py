"""
費用查詢服務
整合 CDR Service、IWS Gateway 和 Billing Calculator

功能：
1. 查詢設備的資費方案（從 IWS）
2. 取得 CDR 記錄（從 CDR Service）
3. 計算費用（使用 Billing Calculator）
4. 生成帳單報表
"""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime, date
from dataclasses import dataclass

from src.infrastructure.iws_gateway import IWSGateway
from src.services.cdr_service import CDRService, SimpleCDRRecord
from src.services.billing_calculator import BillingCalculator, MonthlyBill
from src.config.price_rules import (
    get_price_manager,
    BUNDLE_TO_PLAN
)


class BillingServiceException(Exception):
    """費用查詢服務異常"""
    pass


class BillingService:
    """
    費用查詢服務
    
    整合所有組件，提供完整的費用查詢功能
    """
    
    def __init__(self,
                 gateway: IWSGateway,
                 cdr_service: Optional[CDRService] = None,
                 calculator: Optional[BillingCalculator] = None):
        """
        初始化費用查詢服務
        
        Args:
            gateway: IWS Gateway 實例
            cdr_service: CDR Service 實例（若未提供則創建）
            calculator: Billing Calculator 實例（若未提供則創建）
        """
        self.gateway = gateway
        self.cdr_service = cdr_service or CDRService()
        self.calculator = calculator or BillingCalculator()
        self.price_manager = get_price_manager()
    
    def query_monthly_bill(self,
                          imei: str,
                          year: int,
                          month: int,
                          cdr_records: Optional[List[SimpleCDRRecord]] = None) -> MonthlyBill:
        """
        查詢月帳單
        
        Args:
            imei: 設備 IMEI
            year: 年份
            month: 月份（1-12）
            cdr_records: CDR 記錄（若未提供則需要從檔案載入）
            
        Returns:
            MonthlyBill: 月帳單
            
        Raises:
            BillingServiceException: 查詢失敗
            
        Example:
            >>> service = BillingService(gateway)
            >>> bill = service.query_monthly_bill(
            ...     imei="301434061230580",
            ...     year=2025,
            ...     month=1
            ... )
            >>> print(f"總費用: ${bill.total_cost:.2f}")
        """
        try:
            # 1. 從 IMEI 查詢 Account Number
            search_result = self.gateway.search_account(imei)
            
            if not search_result.get('found'):
                raise BillingServiceException(f"找不到 IMEI {imei} 對應的帳號")
            
            account_number = search_result.get('subscriber_account_number')
            if not account_number:
                raise BillingServiceException(f"無法取得 IMEI {imei} 的帳號編號")
            
            # 2. 查詢帳號資訊（取得方案和狀態）
            account_info = self.gateway.get_subscriber_account(account_number)
            
            bundle_id = account_info.get('bundle_id')
            account_status = account_info.get('status', 'ACTIVE')
            
            # 3. 從 Bundle ID 取得方案名稱
            plan_name = BUNDLE_TO_PLAN.get(bundle_id)
            if not plan_name:
                raise BillingServiceException(
                    f"未知的 Bundle ID: {bundle_id}，請聯繫系統管理員"
                )
            
            # 4. 篩選該月的 CDR 記錄
            if cdr_records is None:
                # 嘗試從本地快取載入
                try:
                    from pathlib import Path
                    
                    # 新的快取結構：./temp/query_cache/{YYYYMM}/
                    month_str = f"{year:04d}{month:02d}"
                    cache_dir = Path(f'./temp/query_cache/{month_str}')
                    cdr_records = []
                    
                    if cache_dir.exists():
                        # 載入該月份資料夾的所有 CDR 檔案
                        for cdr_file in cache_dir.glob("*.dat"):
                            try:
                                file_records = self.cdr_service.parse_file(str(cdr_file))
                                cdr_records.extend(file_records)
                            except Exception as e:
                                # 跳過無法解析的檔案
                                continue
                    
                    if not cdr_records:
                        raise BillingServiceException(
                            f"找不到 {year}/{month:02d} 的 CDR 記錄。\n\n"
                            f"請確認：\n"
                            f"1. 是否已執行 CDR 同步管理（助理端功能）\n"
                            f"2. Google Drive 是否有 {month_str} 資料夾\n"
                            f"3. 本地快取目錄: {cache_dir}\n\n"
                            f"💡 提示：請到「CDR 同步管理」執行同步"
                        )
                except ImportError:
                    raise BillingServiceException(
                        "無法載入 CDR 記錄。請提供 cdr_records 參數。"
                    )
            
            # 篩選該月的記錄
            month_records = self._filter_records_by_month(cdr_records, year, month)
            
            # 5. 計算費用
            bill = self.calculator.calculate_monthly_bill(
                imei=imei,
                plan_name=plan_name,
                year=year,
                month=month,
                records=month_records,
                account_status=account_status
            )
            
            return bill
            
        except BillingServiceException:
            raise
        except Exception as e:
            raise BillingServiceException(
                f"查詢月帳單失敗: {str(e)}"
            ) from e
    
    def query_date_range_bill(self,
                             imei: str,
                             start_date: date,
                             end_date: date,
                             cdr_records: List[SimpleCDRRecord]) -> dict:
        """
        查詢日期區間的費用
        
        注意：如果跨月，會按月分別計算（因為價格可能不同）
        
        Args:
            imei: 設備 IMEI
            start_date: 開始日期
            end_date: 結束日期
            cdr_records: CDR 記錄
            
        Returns:
            {
                'total_cost': 總費用,
                'monthly_bills': [月帳單列表],
                'records_count': 記錄數量
            }
        """
        try:
            # 1. 篩選日期範圍的記錄
            range_records = self._filter_records_by_date_range(
                cdr_records,
                start_date,
                end_date
            )
            
            # 2. 按月分組
            monthly_groups = self._group_records_by_month(range_records)
            
            # 3. 計算每個月的帳單
            monthly_bills = []
            total_cost = 0.0
            
            for (year, month), month_records in monthly_groups.items():
                bill = self.query_monthly_bill(
                    imei=imei,
                    year=year,
                    month=month,
                    cdr_records=month_records
                )
                monthly_bills.append(bill)
                total_cost += bill.total_cost
            
            return {
                'imei': imei,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_cost': total_cost,
                'monthly_bills': monthly_bills,
                'records_count': len(range_records)
            }
            
        except Exception as e:
            raise BillingServiceException(
                f"查詢日期區間費用失敗: {str(e)}"
            ) from e
    
    def get_device_plan_info(self, imei: str) -> dict:
        """
        查詢設備的方案資訊
        
        Args:
            imei: 設備 IMEI
            
        Returns:
            {
                'imei': IMEI,
                'account_number': 帳號,
                'plan_name': 方案名稱,
                'bundle_id': Bundle ID,
                'status': 帳號狀態,
                'current_pricing': 當前價格
            }
        """
        try:
            # 查詢帳號
            search_result = self.gateway.search_account(imei)
            
            if not search_result.get('found'):
                raise BillingServiceException(f"找不到 IMEI {imei}")
            
            account_number = search_result.get('subscriber_account_number')
            if not account_number:
                raise BillingServiceException(f"無法取得 IMEI {imei} 的帳號編號")
            
            # 查詢帳號資訊
            account_info = self.gateway.get_subscriber_account(account_number)
            
            bundle_id = account_info.get('bundle_id')
            account_status = account_info.get('status', 'ACTIVE')
            
            # 取得方案名稱
            plan_name = BUNDLE_TO_PLAN.get(bundle_id, 'Unknown')
            
            # 取得當前價格
            current_pricing = None
            if plan_name != 'Unknown':
                current_pricing = self.price_manager.get_current_price(plan_name)
            
            return {
                'imei': imei,
                'account_number': account_number,
                'plan_name': plan_name,
                'bundle_id': bundle_id,
                'status': account_status,
                'current_pricing': current_pricing
            }
            
        except BillingServiceException:
            raise
        except Exception as e:
            raise BillingServiceException(
                f"查詢設備資訊失敗: {str(e)}"
            ) from e
    
    def _filter_records_by_month(self,
                                 records: List[SimpleCDRRecord],
                                 year: int,
                                 month: int) -> List[SimpleCDRRecord]:
        """
        篩選指定月份的記錄
        
        Args:
            records: 所有記錄
            year: 年份
            month: 月份
            
        Returns:
            該月的記錄列表
        """
        filtered = []
        
        for record in records:
            if (record.call_datetime.year == year and
                record.call_datetime.month == month):
                filtered.append(record)
        
        return filtered
    
    def _filter_records_by_date_range(self,
                                     records: List[SimpleCDRRecord],
                                     start_date: date,
                                     end_date: date) -> List[SimpleCDRRecord]:
        """
        篩選日期區間的記錄
        
        Args:
            records: 所有記錄
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            區間內的記錄列表
        """
        filtered = []
        
        for record in records:
            record_date = record.call_datetime.date()
            if start_date <= record_date <= end_date:
                filtered.append(record)
        
        return filtered
    
    def _group_records_by_month(self,
                                records: List[SimpleCDRRecord]) -> dict:
        """
        將記錄按月分組
        
        Args:
            records: 記錄列表
            
        Returns:
            {(year, month): [records]}
        """
        groups = {}
        
        for record in records:
            key = (record.call_datetime.year, record.call_datetime.month)
            if key not in groups:
                groups[key] = []
            groups[key].append(record)
        
        return groups

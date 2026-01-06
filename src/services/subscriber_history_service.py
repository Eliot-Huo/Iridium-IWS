"""
IWS 方案歷史查詢服務
用於查詢設備的資費方案變更歷史
"""
from __future__ import annotations
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, date


@dataclass
class PlanChangeRecord:
    """方案變更記錄"""
    transaction_date: datetime      # 變更日期時間
    old_plan: Optional[str]         # 舊方案（首次啟用時為 None）
    new_plan: str                   # 新方案
    bundle_id: str                  # Bundle ID
    user_name: str                  # 執行變更的使用者
    transaction_type: str           # 交易類型（PLAN_TRANS, ACTIVATION 等）


class SubscriberHistoryService:
    """
    設備方案歷史查詢服務
    
    透過 IWS Report API 查詢設備的方案變更歷史
    """
    
    def __init__(self, iws_gateway):
        """
        初始化
        
        Args:
            iws_gateway: IWS Gateway 實例
        """
        self.iws = iws_gateway
    
    def get_plan_change_history(
        self,
        imei: str,
        start_date: date,
        end_date: date
    ) -> List[PlanChangeRecord]:
        """
        查詢方案變更歷史
        
        調用 IWS Report API: getSubscriberHistoryAll
        過濾條件：Transaction Type = 'PLAN_TRANS'
        
        Args:
            imei: 設備 IMEI
            start_date: 查詢起始日期
            end_date: 查詢結束日期
            
        Returns:
            方案變更記錄列表（按時間排序）
            
        Example:
            >>> service = SubscriberHistoryService(iws_gateway)
            >>> changes = service.get_plan_change_history(
            ...     imei='300534066711380',
            ...     start_date=date(2025, 7, 1),
            ...     end_date=date(2025, 7, 31)
            ... )
            >>> for change in changes:
            ...     print(f"{change.transaction_date}: {change.old_plan} → {change.new_plan}")
        """
        try:
            # 調用 IWS Report API
            response = self.iws.get_subscriber_history_all(
                subscriber_id=imei,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                service_name='SHORT_BURST_DATA'
            )
            
            # 解析回應
            records = []
            for item in response.get('history_items', []):
                # 只處理方案變更記錄
                if item.get('transaction_type') in ['PLAN_TRANS', 'ACTIVATION', 'PLAN_CHANGE']:
                    record = PlanChangeRecord(
                        transaction_date=self._parse_datetime(item.get('transaction_date')),
                        old_plan=item.get('old_rate_plan'),
                        new_plan=item.get('rate_plan'),
                        bundle_id=item.get('bundle_id', ''),
                        user_name=item.get('user_name', 'System'),
                        transaction_type=item.get('transaction_type')
                    )
                    records.append(record)
            
            # 按時間排序
            records.sort(key=lambda x: x.transaction_date)
            
            return records
            
        except Exception as e:
            print(f"⚠️ 查詢方案變更歷史失敗: {e}")
            return []
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """解析日期時間字串"""
        try:
            return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                return datetime.strptime(dt_str, '%Y-%m-%d')
            except:
                return datetime.now()
    
    def get_plan_at_date(
        self,
        imei: str,
        query_date: date
    ) -> Optional[str]:
        """
        查詢特定日期該設備使用的方案
        
        Args:
            imei: 設備 IMEI
            query_date: 查詢日期
            
        Returns:
            方案名稱（如 'SBD12'），若查不到則返回 None
        """
        # 查詢從很早到查詢日期的所有變更
        changes = self.get_plan_change_history(
            imei=imei,
            start_date=date(2020, 1, 1),  # 從很早開始
            end_date=query_date
        )
        
        if not changes:
            return None
        
        # 找出查詢日期之前的最後一次變更
        for change in reversed(changes):
            if change.transaction_date.date() <= query_date:
                return change.new_plan
        
        # 如果沒有找到，返回第一次的方案
        return changes[0].new_plan if changes else None

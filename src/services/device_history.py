"""
設備歷史記錄管理模組
Device History Manager

功能：
1. 記錄設備的所有操作歷史（啟用、方案變更、狀態變更）
2. 查詢設備在特定時間點的狀態
3. 支持計費邏輯的歷史查詢
"""

from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path


@dataclass
class DeviceOperation:
    """設備操作記錄"""
    date: str                    # 操作日期 (YYYY-MM-DD)
    imei: str                    # 設備 IMEI
    action: str                  # 操作類型：ACTIVATE, PLAN_CHANGE, STATUS_CHANGE
    
    # 可選欄位（根據操作類型）
    plan: Optional[str] = None              # 方案名稱（ACTIVATE）
    status: Optional[str] = None            # 狀態（ACTIVATE, STATUS_CHANGE）
    old_plan: Optional[str] = None          # 舊方案（PLAN_CHANGE）
    new_plan: Optional[str] = None          # 新方案（PLAN_CHANGE）
    old_status: Optional[str] = None        # 舊狀態（STATUS_CHANGE）
    new_status: Optional[str] = None        # 新狀態（STATUS_CHANGE）
    operator: Optional[str] = None          # 操作人員
    notes: Optional[str] = None             # 備註
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict) -> DeviceOperation:
        """從字典創建"""
        return cls(**data)


class DeviceHistoryManager:
    """
    設備歷史記錄管理器
    
    負責記錄和查詢設備的所有操作歷史
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        初始化歷史記錄管理器
        
        Args:
            data_dir: 數據存儲目錄
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "device_history.json"
        
        # 費率順序（用於判斷升降級）
        self.plan_order = {
            'SBD0': 1,
            'SBD12': 2,
            'SBD17': 3,
            'SBD30': 4
        }
        
        # 載入歷史記錄
        self.history: List[DeviceOperation] = self._load_history()
    
    def _load_history(self) -> List[DeviceOperation]:
        """載入歷史記錄"""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [DeviceOperation.from_dict(item) for item in data]
        except Exception as e:
            print(f"載入歷史記錄失敗: {e}")
            return []
    
    def _save_history(self):
        """保存歷史記錄"""
        try:
            data = [op.to_dict() for op in self.history]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存歷史記錄失敗: {e}")
    
    def add_operation(self, operation: DeviceOperation):
        """
        添加操作記錄
        
        Args:
            operation: 操作記錄
        """
        self.history.append(operation)
        # 按日期排序
        self.history.sort(key=lambda x: x.date)
        self._save_history()
    
    def record_activation(self,
                         imei: str,
                         plan: str,
                         date_str: str,
                         operator: Optional[str] = None,
                         notes: Optional[str] = None):
        """
        記錄設備啟用
        
        Args:
            imei: 設備 IMEI
            plan: 方案名稱
            date_str: 啟用日期 (YYYY-MM-DD)
            operator: 操作人員
            notes: 備註
        """
        operation = DeviceOperation(
            date=date_str,
            imei=imei,
            action='ACTIVATE',
            plan=plan,
            status='ACTIVE',
            operator=operator,
            notes=notes
        )
        self.add_operation(operation)
    
    def record_plan_change(self,
                          imei: str,
                          old_plan: str,
                          new_plan: str,
                          date_str: str,
                          operator: Optional[str] = None,
                          notes: Optional[str] = None):
        """
        記錄方案變更
        
        Args:
            imei: 設備 IMEI
            old_plan: 舊方案
            new_plan: 新方案
            date_str: 變更日期 (YYYY-MM-DD)
            operator: 操作人員
            notes: 備註
        """
        operation = DeviceOperation(
            date=date_str,
            imei=imei,
            action='PLAN_CHANGE',
            old_plan=old_plan,
            new_plan=new_plan,
            operator=operator,
            notes=notes
        )
        self.add_operation(operation)
    
    def record_status_change(self,
                            imei: str,
                            old_status: str,
                            new_status: str,
                            date_str: str,
                            plan: Optional[str] = None,
                            operator: Optional[str] = None,
                            notes: Optional[str] = None):
        """
        記錄狀態變更
        
        Args:
            imei: 設備 IMEI
            old_status: 舊狀態 (ACTIVE/SUSPENDED)
            new_status: 新狀態 (ACTIVE/SUSPENDED)
            date_str: 變更日期 (YYYY-MM-DD)
            plan: 方案名稱（可選）
            operator: 操作人員
            notes: 備註
        """
        operation = DeviceOperation(
            date=date_str,
            imei=imei,
            action='STATUS_CHANGE',
            old_status=old_status,
            new_status=new_status,
            plan=plan,
            operator=operator,
            notes=notes
        )
        self.add_operation(operation)
    
    def get_device_history(self, imei: str) -> List[DeviceOperation]:
        """
        獲取設備的所有歷史記錄
        
        Args:
            imei: 設備 IMEI
            
        Returns:
            操作記錄列表
        """
        return [op for op in self.history if op.imei == imei]
    
    def get_state_at_date(self, imei: str, target_date: str) -> Tuple[Optional[str], Optional[str]]:
        """
        獲取設備在特定日期的狀態
        
        Args:
            imei: 設備 IMEI
            target_date: 目標日期 (YYYY-MM-DD)
            
        Returns:
            (plan, status) - 方案和狀態
        """
        device_history = self.get_device_history(imei)
        
        current_plan = None
        current_status = None
        
        for operation in device_history:
            if operation.date > target_date:
                break
            
            if operation.action == 'ACTIVATE':
                current_plan = operation.plan
                current_status = operation.status
            
            elif operation.action == 'PLAN_CHANGE':
                current_plan = operation.new_plan
            
            elif operation.action == 'STATUS_CHANGE':
                current_status = operation.new_status
                if operation.plan:
                    current_plan = operation.plan
        
        return current_plan, current_status
    
    def get_month_start_state(self, imei: str, year: int, month: int) -> Tuple[Optional[str], Optional[str]]:
        """
        獲取月初狀態
        
        Args:
            imei: 設備 IMEI
            year: 年份
            month: 月份
            
        Returns:
            (plan, status) - 月初的方案和狀態
        """
        # 先檢查是否在該月第一天啟用
        month_start = f"{year}-{month:02d}-01"
        device_history = self.get_device_history(imei)
        
        # 檢查是否在該月第一天啟用
        for op in device_history:
            if op.date == month_start and op.action == 'ACTIVATE':
                return op.plan, op.status
        
        # 獲取前一天的狀態（月初前一天）
        if month == 1:
            prev_date = f"{year-1}-12-31"
        else:
            # 獲取上個月最後一天
            from calendar import monthrange
            prev_month = month - 1
            last_day = monthrange(year, prev_month)[1]
            prev_date = f"{year}-{prev_month:02d}-{last_day:02d}"
        
        return self.get_state_at_date(imei, prev_date)
    
    def get_operations_in_month(self, imei: str, year: int, month: int) -> List[DeviceOperation]:
        """
        獲取該月的所有操作
        
        Args:
            imei: 設備 IMEI
            year: 年份
            month: 月份
            
        Returns:
            操作記錄列表
        """
        month_start = f"{year}-{month:02d}-01"
        
        # 計算月底
        if month == 12:
            month_end = f"{year+1}-01-01"
        else:
            month_end = f"{year}-{month+1:02d}-01"
        
        device_history = self.get_device_history(imei)
        
        return [
            op for op in device_history
            if month_start <= op.date < month_end
        ]
    
    def is_upgrade(self, old_plan: str, new_plan: str) -> bool:
        """
        判斷是否為升級
        
        Args:
            old_plan: 舊方案
            new_plan: 新方案
            
        Returns:
            True 如果是升級
        """
        return self.plan_order.get(new_plan, 0) > self.plan_order.get(old_plan, 0)
    
    def count_suspend_actions(self, imei: str, year: int, month: int) -> int:
        """
        計算該月暫停次數
        
        Args:
            imei: 設備 IMEI
            year: 年份
            month: 月份
            
        Returns:
            暫停次數
        """
        operations = self.get_operations_in_month(imei, year, month)
        
        suspend_count = 0
        for op in operations:
            if op.action == 'STATUS_CHANGE' and op.new_status == 'SUSPENDED':
                suspend_count += 1
        
        return suspend_count
    
    def get_status_changes(self, imei: str, year: int, month: int) -> List[DeviceOperation]:
        """
        獲取該月的狀態變更記錄
        
        Args:
            imei: 設備 IMEI
            year: 年份
            month: 月份
            
        Returns:
            狀態變更記錄列表
        """
        operations = self.get_operations_in_month(imei, year, month)
        
        return [
            op for op in operations
            if op.action == 'STATUS_CHANGE'
        ]
    
    def export_to_json(self, filepath: str):
        """
        導出歷史記錄到 JSON 檔案
        
        Args:
            filepath: 目標檔案路徑
        """
        data = [op.to_dict() for op in self.history]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def import_from_json(self, filepath: str):
        """
        從 JSON 檔案導入歷史記錄
        
        Args:
            filepath: 來源檔案路徑
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.history = [DeviceOperation.from_dict(item) for item in data]
            self.history.sort(key=lambda x: x.date)
            self._save_history()


# 全域實例
_device_history_manager: Optional[DeviceHistoryManager] = None


def get_device_history_manager(data_dir: str = "data") -> DeviceHistoryManager:
    """
    獲取全域設備歷史記錄管理器實例
    
    Args:
        data_dir: 數據目錄
        
    Returns:
        DeviceHistoryManager 實例
    """
    global _device_history_manager
    
    if _device_history_manager is None:
        _device_history_manager = DeviceHistoryManager(data_dir)
    
    return _device_history_manager

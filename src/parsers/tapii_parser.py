"""
TAP II v9.2 CDR 解析器
解析 Iridium CDR 檔案（TAP II 格式）

重要特性：
- 每筆記錄固定 160 字元（無換行符）
- 時間已經是本地時間（不需要轉換）
- 需要解析時區代碼（Type 14）來確認

記錄類型：
- Type 10: Header Record（檔案標頭）
- Type 14: UTC Time Offset（時區偏移表）
- Type 20: Data Record（SBD 通訊記錄）
- Type 30: Trailer Record（結尾記錄）
"""
from __future__ import annotations
from typing import List, Set, Optional, Dict
from datetime import datetime, date
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TAPIIRecord:
    """TAP II 記錄"""
    record_type: int          # 記錄類型（10, 14, 20, 30）
    raw_data: bytes           # 原始資料（160 字元）
    
    # 通訊記錄欄位（Type 20）
    charging_date: Optional[str] = None      # YYMMDD
    charging_time: Optional[str] = None      # HHMMSS  
    utc_offset_code: Optional[str] = None    # A-O
    
    # 檔案資訊（Type 10）
    file_creation_date: Optional[str] = None # YYMMDD


class TAPIIParser:
    """TAP II v9.2 解析器"""
    
    # 記錄固定長度
    RECORD_LENGTH = 160
    
    # 記錄類型
    TYPE_HEADER = 10    # 標頭
    TYPE_UTC_OFFSET = 14  # 時區偏移
    TYPE_DATA = 20      # 資料記錄
    TYPE_TRAILER = 30   # 結尾
    
    def __init__(self):
        """初始化解析器"""
        self.utc_offset_map = {}  # 時區代碼 → 偏移量對照表
    
    def parse_file(self, filepath: str) -> List[TAPIIRecord]:
        """
        解析 CDR 檔案
        
        Args:
            filepath: 檔案路徑
            
        Returns:
            記錄列表
        """
        records = []
        
        # 讀取整個檔案（無換行符）
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # 每 160 字元切分一筆記錄
        for i in range(0, len(content), self.RECORD_LENGTH):
            record_data = content[i:i + self.RECORD_LENGTH]
            
            # 確保長度正確
            if len(record_data) < self.RECORD_LENGTH:
                # 最後一筆可能不足 160 字元
                break
            
            # 解析記錄
            record = self._parse_record(record_data)
            if record:
                records.append(record)
        
        return records
    
    def _parse_record(self, data: bytes) -> Optional[TAPIIRecord]:
        """
        解析單筆記錄
        
        Args:
            data: 記錄資料（160 字元）
            
        Returns:
            解析後的記錄，或 None（無法解析）
        """
        if len(data) < self.RECORD_LENGTH:
            return None
        
        # 第一個字元是記錄類型（但以 byte 表示）
        # 實際上 TAP II 是 BCD 編碼，但我們簡化處理
        # 檢查位置 0-1 的內容來判斷類型
        
        try:
            # 嘗試多種方式判斷記錄類型
            record_type = None
            
            # 方法 1: 直接讀取第一個字元（如果是 ASCII）
            if data[0:1].isdigit():
                record_type = int(data[0:2])
            
            # 方法 2: 檢查特定位置的特徵
            # Type 10: Header，位置 66-71 有日期
            # Type 20: Data，位置 115-120 有日期
            
            # 簡化：根據位置 115-120 是否為日期來判斷 Type 20
            if self._is_valid_date(data[114:120]):
                record_type = self.TYPE_DATA
                
                # 解析 Data Record (Type 20)
                return TAPIIRecord(
                    record_type=self.TYPE_DATA,
                    raw_data=data,
                    charging_date=data[114:120].decode('ascii', errors='ignore'),
                    charging_time=data[120:126].decode('ascii', errors='ignore'),
                    utc_offset_code=data[126:127].decode('ascii', errors='ignore')
                )
            
            # 檢查是否為 Header (Type 10)
            elif self._is_valid_date(data[65:71]):
                return TAPIIRecord(
                    record_type=self.TYPE_HEADER,
                    raw_data=data,
                    file_creation_date=data[65:71].decode('ascii', errors='ignore')
                )
            
            # 其他類型暫不解析
            return None
            
        except Exception as e:
            # 解析失敗，跳過
            return None
    
    def _is_valid_date(self, date_bytes: bytes) -> bool:
        """
        檢查是否為有效日期 (YYMMDD)
        
        Args:
            date_bytes: 日期字節（6 字元）
            
        Returns:
            是否為有效日期
        """
        if len(date_bytes) != 6:
            return False
        
        try:
            date_str = date_bytes.decode('ascii')
            
            # 檢查是否全為數字
            if not date_str.isdigit():
                return False
            
            # 解析年月日
            yy = int(date_str[0:2])
            mm = int(date_str[2:4])
            dd = int(date_str[4:6])
            
            # 驗證範圍
            if not (0 <= yy <= 99):  # YY
                return False
            if not (1 <= mm <= 12):  # MM
                return False
            if not (1 <= dd <= 31):  # DD
                return False
            
            return True
            
        except:
            return False
    
    def extract_months(self, filepath: str) -> Set[str]:
        """
        從 CDR 檔案提取所有出現的月份
        
        Args:
            filepath: 檔案路徑
            
        Returns:
            月份集合（格式：YYYYMM，例如 "202512"）
            
        Example:
            >>> parser = TAPIIParser()
            >>> months = parser.extract_months('cdr_file.dat')
            >>> print(months)
            {'202512', '202601'}  # 跨月檔案
        """
        months = set()
        
        # 解析檔案
        records = self.parse_file(filepath)
        
        # 優先從 Data Records (Type 20) 提取月份
        for record in records:
            if record.record_type == self.TYPE_DATA and record.charging_date:
                # 將 YYMMDD 轉換為 YYYYMM
                month = self._convert_to_month(record.charging_date)
                if month:
                    months.add(month)
        
        # 如果沒有 Data Records，從 Header (Type 10) 提取檔案建立日期
        # 這種情況通常發生在空檔案或只有 Header/Trailer 的檔案
        if not months:
            for record in records:
                if record.record_type == self.TYPE_HEADER and record.file_creation_date:
                    month = self._convert_to_month(record.file_creation_date)
                    if month:
                        months.add(month)
                        break  # Header 只需要處理一次
        
        return months
    
    def extract_dates(self, filepath: str) -> Set[str]:
        """
        從 CDR 檔案提取所有出現的日期
        
        Args:
            filepath: 檔案路徑
            
        Returns:
            日期集合（格式：YYYYMMDD，例如 "20251013"）
            
        Example:
            >>> parser = TAPIIParser()
            >>> dates = parser.extract_dates('cdr_file.dat')
            >>> print(dates)
            {'20251013', '20251014'}  # 跨日檔案
        """
        dates = set()
        
        # 解析檔案
        records = self.parse_file(filepath)
        
        # 優先從 Data Records (Type 20) 提取日期
        for record in records:
            if record.record_type == self.TYPE_DATA and record.charging_date:
                # 將 YYMMDD 轉換為 YYYYMMDD
                date_str = self._convert_to_date(record.charging_date)
                if date_str:
                    dates.add(date_str)
        
        # 如果沒有 Data Records，從 Header (Type 10) 提取檔案建立日期
        if not dates:
            for record in records:
                if record.record_type == self.TYPE_HEADER and record.file_creation_date:
                    date_str = self._convert_to_date(record.file_creation_date)
                    if date_str:
                        dates.add(date_str)
                        break
        
        return dates
    
    def _convert_to_month(self, yymmdd: str) -> Optional[str]:
        """
        將 YYMMDD 轉換為 YYYYMM
        
        Args:
            yymmdd: 日期字串（YYMMDD）
            
        Returns:
            月份字串（YYYYMM），或 None（無效日期）
            
        Example:
            >>> parser._convert_to_month('251231')
            '202512'
            >>> parser._convert_to_month('260101')
            '202601'
        """
        if not yymmdd or len(yymmdd) != 6:
            return None
        
        try:
            yy = yymmdd[0:2]
            mm = yymmdd[2:4]
            
            # 假設 YY >= 20 是 20XX，否則是 19XX
            # 實際上 Iridium CDR 應該都是 20XX
            yyyy = '20' + yy if int(yy) >= 20 else '19' + yy
            
            # 驗證月份
            if not (1 <= int(mm) <= 12):
                return None
            
            return yyyy + mm
            
        except:
            return None
    
    def _convert_to_date(self, yymmdd: str) -> Optional[str]:
        """
        將 YYMMDD 轉換為 YYYYMMDD
        
        Args:
            yymmdd: 日期字串（YYMMDD）
            
        Returns:
            日期字串（YYYYMMDD），或 None（無效日期）
            
        Example:
            >>> parser._convert_to_date('251231')
            '20251231'
            >>> parser._convert_to_date('260101')
            '20260101'
        """
        if not yymmdd or len(yymmdd) != 6:
            return None
        
        try:
            yy = yymmdd[0:2]
            mm = yymmdd[2:4]
            dd = yymmdd[4:6]
            
            # 假設 YY >= 20 是 20XX，否則是 19XX
            yyyy = '20' + yy if int(yy) >= 20 else '19' + yy
            
            # 驗證月份和日期
            if not (1 <= int(mm) <= 12):
                return None
            if not (1 <= int(dd) <= 31):
                return None
            
            return yyyy + mm + dd
            
        except:
            return None
    
    def count_records(self, filepath: str) -> int:
        """
        計算檔案中的記錄數量
        
        Args:
            filepath: 檔案路徑
            
        Returns:
            記錄數量
        """
        records = self.parse_file(filepath)
        return len([r for r in records if r.record_type == self.TYPE_DATA])
    
    def get_file_date_range(self, filepath: str) -> tuple[Optional[date], Optional[date]]:
        """
        取得檔案的日期範圍
        
        Args:
            filepath: 檔案路徑
            
        Returns:
            (最早日期, 最晚日期)
        """
        dates = []
        records = self.parse_file(filepath)
        
        for record in records:
            if record.record_type == self.TYPE_DATA and record.charging_date:
                try:
                    # YYMMDD → date
                    yy = record.charging_date[0:2]
                    mm = record.charging_date[2:4]
                    dd = record.charging_date[4:6]
                    
                    yyyy = '20' + yy if int(yy) >= 20 else '19' + yy
                    
                    d = date(int(yyyy), int(mm), int(dd))
                    dates.append(d)
                except:
                    continue
        
        if not dates:
            return None, None
        
        return min(dates), max(dates)


# 工具函式
def quick_extract_months(filepath: str) -> Set[str]:
    """
    快速提取檔案的月份（便捷函式）
    
    Args:
        filepath: 檔案路徑
        
    Returns:
        月份集合
    """
    parser = TAPIIParser()
    return parser.extract_months(filepath)


def is_cross_month_file(filepath: str) -> bool:
    """
    檢查檔案是否跨月
    
    Args:
        filepath: 檔案路徑
        
    Returns:
        是否跨月
    """
    months = quick_extract_months(filepath)
    return len(months) > 1

"""
CDR 服務層

負責協調 FTP 下載器與 TAP II 解析器，將原始 CDR 資料轉換為領域模型。
本層為「膠水代碼」，不包含業務邏輯或解析邏輯，僅負責組件間的協調。

架構層次：
    UI Layer (app.py)
        ↓
    Service Layer (cdr_service.py) ← 本模組
        ↓
    Infrastructure Layer (ftp_client.py, cdr_service_tapii.py)
"""
from __future__ import annotations
from typing import Optional, List, Tuple
from datetime import datetime
from zoneinfo import ZoneInfo
from dataclasses import dataclass

from .cdr_service_tapii import (
    TAPIIParser,
    MOCRecord,
    MTCRecord,
    SupplementaryServiceRecord
)
from ..infrastructure.ftp_client import CDRDownloader, CDRDownloadException


# ==================== 領域模型 ====================

@dataclass
class SimpleCDRRecord:
    """
    簡化的 CDR 記錄 - 領域模型
    
    此模型專為 UI 層設計，隱藏底層 TAP II 的複雜性。
    
    Attributes:
        imei: 設備 IMEI（15 位數字）
        call_datetime: 通話時間（台北時區）
        duration_seconds: 通話時長（秒）
        data_mb: 資料量（MB，精確到 6 位小數）
        call_type: 服務類型名稱（如 "Short Burst Data"）
        service_code: 原始服務代碼（如 "36"）
        destination: 目的地號碼
        cost: 費用（美元）
        location_country: 位置國碼（E.212 格式）
        cell_id: Cell ID（5 位）
        msc_id: MSC ID（如 "SATELLITE"）
        timezone: 時區名稱
    """
    imei: str
    call_datetime: datetime
    duration_seconds: int
    data_mb: float
    call_type: str
    service_code: str
    destination: str
    cost: float
    location_country: str
    cell_id: str
    msc_id: str
    timezone: str = 'Asia/Taipei'
    
    def get_formatted_time(self, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
        """
        格式化時間字串
        
        Args:
            format_str: 時間格式字串（預設為 ISO-like 格式）
            
        Returns:
            格式化後的時間字串
        """
        return self.call_datetime.strftime(format_str)


# ==================== 服務層 ====================

class CDRService:
    """
    CDR 服務類別（協調層）
    
    負責協調以下組件：
    1. CDRDownloader - 從 FTP 下載 CDR 檔案
    2. TAPIIParser - 解析 TAP II 格式
    3. 領域模型轉換 - 將 TAP II 記錄轉換為 SimpleCDRRecord
    
    設計原則：
    - 單一職責：僅負責協調，不包含業務邏輯
    - 依賴注入：允許外部注入 Parser（便於測試）
    - 清晰的職責邊界：下載 → 解析 → 轉換
    
    Example:
        >>> # 標準使用（自動創建 Parser）
        >>> service = CDRService()
        >>> filename, records = service.download_and_parse_latest_cdr()
        
        >>> # 依賴注入（用於測試）
        >>> mock_parser = MockTAPIIParser()
        >>> service = CDRService(parser=mock_parser)
        >>> records = service.parse_bytes_content(test_data)
    """
    
    def __init__(self, parser: Optional[TAPIIParser] = None) -> None:
        """
        初始化 CDR 服務
        
        Args:
            parser: TAP II 解析器實例（可選）。
                   若未提供，將自動創建 TAPIIParser 實例。
                   主要用於依賴注入與單元測試。
        """
        self._parser = parser if parser is not None else TAPIIParser()
    
    def download_and_parse_latest_cdr(self) -> Tuple[str, List[SimpleCDRRecord]]:
        """
        從 FTP 下載並解析最新的 CDR 檔案
        
        執行流程：
        1. 使用 CDRDownloader 從 FTP 下載最新的 .dat 檔案
        2. 調用 parse_bytes_content() 解析內容
        3. 返回檔案名稱和解析後的記錄列表
        
        Returns:
            Tuple[str, List[SimpleCDRRecord]]: 
                - 第一個元素：檔案名稱（如 "cdr_20250101.dat"）
                - 第二個元素：解析後的記錄列表
        
        Raises:
            CDRDownloadException: FTP 下載失敗
            CDRServiceException: 解析失敗
        
        Example:
            >>> service = CDRService()
            >>> filename, records = service.download_and_parse_latest_cdr()
            >>> print(f"Downloaded {filename}: {len(records)} records")
        """
        try:
            # 步驟 1: 使用 CDRDownloader 下載檔案
            with CDRDownloader() as downloader:
                filename, content = downloader.get_latest_cdr()
            
            # 步驟 2: 解析檔案內容
            records = self.parse_bytes_content(content)
            
            return filename, records
            
        except CDRDownloadException:
            # FTP 下載錯誤直接向上拋出
            raise
        except Exception as e:
            # 其他錯誤包裝為服務異常
            raise CDRServiceException(
                f"Failed to download and parse CDR: {str(e)}"
            ) from e
    
    def parse_bytes_content(self, content: bytes) -> List[SimpleCDRRecord]:
        """
        解析 bytes 格式的 CDR 檔案內容
        
        執行流程：
        1. 嘗試多種編碼解碼 bytes 內容
        2. 調用 TAPIIParser 解析 TAP II 格式
        3. 將 TAP II 記錄轉換為領域模型
        
        Args:
            content: CDR 檔案的 bytes 內容（從 FTP 下載或本地檔案讀取）
        
        Returns:
            List[SimpleCDRRecord]: 解析後的記錄列表
        
        Raises:
            CDRServiceException: 解析失敗
        
        Example:
            >>> with open('cdr.dat', 'rb') as f:
            ...     content = f.read()
            >>> service = CDRService()
            >>> records = service.parse_bytes_content(content)
        """
        try:
            # 步驟 1: 解碼 bytes 內容
            text_content = self._decode_bytes(content)
            
            # 步驟 2: 分割為 160 字元記錄
            lines = self._split_into_records(text_content)
            
            # 步驟 3: 調用 Parser 解析
            moc_records, mtc_records = self._parse_tap_ii_records(lines)
            
            # 步驟 4: 轉換為領域模型
            simple_records = self._convert_to_domain_models(
                moc_records, 
                mtc_records
            )
            
            return simple_records
            
        except Exception as e:
            raise CDRServiceException(
                f"Failed to parse CDR content: {str(e)}"
            ) from e
    
    def parse_file(self, filepath: str) -> List[SimpleCDRRecord]:
        """
        解析本地 CDR 檔案
        
        Args:
            filepath: CDR 檔案路徑
        
        Returns:
            List[SimpleCDRRecord]: 解析後的記錄列表
        
        Raises:
            CDRServiceException: 檔案讀取或解析失敗
        
        Example:
            >>> service = CDRService()
            >>> records = service.parse_file('/path/to/cdr.dat')
        """
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            return self.parse_bytes_content(content)
        except Exception as e:
            raise CDRServiceException(
                f"Failed to parse file {filepath}: {str(e)}"
            ) from e
    
    # ==================== 私有方法（協調邏輯） ====================
    
    def _decode_bytes(self, content: bytes) -> str:
        """
        解碼 bytes 內容為文字
        
        嘗試多種編碼，按優先順序：utf-8 > latin-1 > cp1252 > ascii
        若全部失敗，使用 utf-8 並忽略錯誤。
        
        Args:
            content: bytes 內容
        
        Returns:
            str: 解碼後的文字內容
        """
        encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
        
        for encoding in encodings:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        # 所有編碼都失敗，使用 utf-8 並忽略錯誤
        return content.decode('utf-8', errors='ignore')
    
    def _split_into_records(self, text_content: str) -> List[str]:
        """
        將文字內容分割為 TAP II 記錄
        
        TAP II 格式為固定長度 160 字元，可能有或無換行符。
        
        Args:
            text_content: 文字內容
        
        Returns:
            List[str]: 160 字元記錄列表
        """
        lines = []
        
        # 處理有換行符的格式
        if '\n' in text_content or '\r' in text_content:
            normalized = text_content.replace('\r\n', '\n').replace('\r', '\n')
            lines = [
                line for line in normalized.split('\n')
                if len(line.strip()) == 160
            ]
        else:
            # 處理無換行符的格式（連續 160 字元）
            for i in range(0, len(text_content), 160):
                if i + 160 <= len(text_content):
                    line = text_content[i:i+160]
                    if len(line) == 160:
                        lines.append(line)
        
        return lines
    
    def _parse_tap_ii_records(
        self, 
        lines: List[str]
    ) -> Tuple[List[MOCRecord], List[MTCRecord]]:
        """
        調用 TAPIIParser 解析記錄
        
        Args:
            lines: 160 字元記錄列表
        
        Returns:
            Tuple[List[MOCRecord], List[MTCRecord]]: 
                (MOC 記錄列表, MTC 記錄列表)
        """
        moc_records: List[MOCRecord] = []
        mtc_records: List[MTCRecord] = []
        
        for line in lines:
            if len(line) != 160:
                continue
            
            record_type = line[0:2]
            
            try:
                if record_type == '10':
                    # Header Record - 更新 Parser 狀態
                    self._parser.parse_header(line)
                    
                elif record_type == '14':
                    # UTC Time Offset Record - 更新 Parser 的時區表
                    utc_offset = self._parser.parse_utc_offset(line)
                    self._parser.utc_offset_table = utc_offset.offset_table
                    
                elif record_type == '20':
                    # Mobile Originated Call (MOC)
                    moc = self._parser.parse_moc(line)
                    moc_records.append(moc)
                    
                elif record_type == '30':
                    # Mobile Terminated Call (MTC)
                    mtc = self._parser.parse_mtc(line)
                    mtc_records.append(mtc)
                    
                elif record_type == '40':
                    # Supplementary Service - 解析但不使用
                    self._parser.parse_supplementary_service(line)
                    
                elif record_type == '90':
                    # Trailer Record - 可提取統計資訊（未來擴展）
                    pass
                    
            except Exception as e:
                # 記錄解析錯誤但繼續處理
                # 注意：生產環境應使用 logging 而非 print
                print(f"Warning: Failed to parse record type {record_type}: {e}")
                continue
        
        return moc_records, mtc_records
    
    def _convert_to_domain_models(
        self,
        moc_records: List[MOCRecord],
        mtc_records: List[MTCRecord]
    ) -> List[SimpleCDRRecord]:
        """
        將 TAP II 記錄轉換為領域模型
        
        Args:
            moc_records: MOC 記錄列表
            mtc_records: MTC 記錄列表
        
        Returns:
            List[SimpleCDRRecord]: 領域模型列表
        """
        simple_records: List[SimpleCDRRecord] = []
        
        # 轉換 MOC 記錄
        for moc in moc_records:
            record = self._convert_moc_to_simple(moc)
            if record is not None:
                simple_records.append(record)
        
        # 轉換 MTC 記錄
        for mtc in mtc_records:
            record = self._convert_mtc_to_simple(mtc)
            if record is not None:
                simple_records.append(record)
        
        return simple_records
    
    def _convert_moc_to_simple(self, moc: MOCRecord) -> Optional[SimpleCDRRecord]:
        """
        將 MOC 記錄轉換為領域模型
        
        重要：根據 SBD 規範，對於 Service Code 36 (SBD) 和 38 (M2M SBD)，
              TAP II 的 IMSI 欄位（位置 10-24）實際填入的是 IMEI。
        
        Args:
            moc: MOC 記錄
        
        Returns:
            Optional[SimpleCDRRecord]: 領域模型，若無效則返回 None
        """
        try:
            # 解析時間並轉換為台北時區
            call_datetime = self._parser.parse_local_datetime(
                moc.charging_date,
                moc.charge_start_time,
                moc.utc_time_offset_code
            )
            taipei_tz = ZoneInfo('Asia/Taipei')
            call_datetime_taipei = call_datetime.astimezone(taipei_tz)
            
            # SBD 專用邏輯：IMSI 欄位實際上是 IMEI
            # Service Code 36 = SBD, 38 = M2M SBD
            imei = (
                moc.imsi if moc.service_code in ['36', '38']
                else moc.imei
            )
            
            # 驗證 IMEI 有效性
            if not imei or len(imei.strip()) == 0:
                return None
            
            # 建立領域模型
            return SimpleCDRRecord(
                imei=imei.strip(),
                call_datetime=call_datetime_taipei,
                duration_seconds=moc.chargeable_units,
                data_mb=round(moc.data_volume_reference / 1_000_000, 6),
                call_type=self._parser.get_service_name(moc.service_code),
                service_code=moc.service_code,
                destination=moc.called_number.strip() if moc.called_number else '',
                cost=round(moc.charge, 2),
                location_country=moc.location_area_code,
                cell_id=moc.cell_id,
                msc_id=moc.msc_id.strip() if moc.msc_id else '',
                timezone='Asia/Taipei'
            )
            
        except Exception as e:
            print(f"Warning: Failed to convert MOC record: {e}")
            return None
    
    def _convert_mtc_to_simple(self, mtc: MTCRecord) -> Optional[SimpleCDRRecord]:
        """
        將 MTC 記錄轉換為領域模型
        
        Args:
            mtc: MTC 記錄
        
        Returns:
            Optional[SimpleCDRRecord]: 領域模型，若無效則返回 None
        """
        try:
            # 解析時間並轉換為台北時區
            call_datetime = self._parser.parse_local_datetime(
                mtc.charging_date,
                mtc.charge_start_time,
                mtc.utc_time_offset_code
            )
            taipei_tz = ZoneInfo('Asia/Taipei')
            call_datetime_taipei = call_datetime.astimezone(taipei_tz)
            
            # MTC 記錄使用標準的 IMEI 欄位
            imei = mtc.imei
            if not imei or len(imei.strip()) == 0:
                return None
            
            # 建立領域模型
            return SimpleCDRRecord(
                imei=imei.strip(),
                call_datetime=call_datetime_taipei,
                duration_seconds=mtc.chargeable_units,
                data_mb=round(mtc.data_volume_reference / 1_000_000, 6),
                call_type=self._parser.get_service_name(mtc.service_code),
                service_code=mtc.service_code,
                destination=mtc.calling_number.strip() if mtc.calling_number else '',
                cost=round(mtc.charge, 2),
                location_country=mtc.location_area_code,
                cell_id=mtc.cell_id,
                msc_id=mtc.msc_id.strip() if mtc.msc_id else '',
                timezone='Asia/Taipei'
            )
            
        except Exception as e:
            print(f"Warning: Failed to convert MTC record: {e}")
            return None
    
    # ==================== 靜態方法（向後相容） ====================
    
    @staticmethod
    def parse_multiple_lines(lines: List[str]) -> List[SimpleCDRRecord]:
        """
        批次解析多行 CDR 記錄（向後相容方法）
        
        注意：此方法為向後相容保留，建議使用實例方法。
        
        Args:
            lines: CDR 文字行列表
        
        Returns:
            List[SimpleCDRRecord]: 記錄列表
        
        Example:
            >>> lines = ['line1', 'line2', 'line3']
            >>> records = CDRService.parse_multiple_lines(lines)
        """
        service = CDRService()
        text_content = '\n'.join(lines)
        lines_160 = service._split_into_records(text_content)
        moc_records, mtc_records = service._parse_tap_ii_records(lines_160)
        return service._convert_to_domain_models(moc_records, mtc_records)
    
    @staticmethod
    def filter_by_imei(
        records: List[SimpleCDRRecord],
        imei: str
    ) -> List[SimpleCDRRecord]:
        """
        依 IMEI 篩選記錄
        
        Args:
            records: CDR 記錄列表
            imei: IMEI 號碼
        
        Returns:
            List[SimpleCDRRecord]: 篩選後的記錄列表
        """
        return [r for r in records if r.imei == imei]
    
    @staticmethod
    def calculate_total_cost(records: List[SimpleCDRRecord]) -> float:
        """
        計算總費用
        
        Args:
            records: CDR 記錄列表
        
        Returns:
            float: 總費用（美元，精確到 2 位小數）
        """
        return round(sum(r.cost for r in records), 2)
    
    @staticmethod
    def get_usage_summary(records: List[SimpleCDRRecord]) -> dict:
        """
        取得使用量摘要
        
        Args:
            records: CDR 記錄列表
        
        Returns:
            dict: 統計摘要，包含：
                - total_records: 總記錄數
                - total_cost: 總費用
                - total_duration: 總時長（秒）
                - total_data_mb: 總資料量（MB）
                - by_type: 按服務類型分組的統計
        
        Example:
            >>> summary = CDRService.get_usage_summary(records)
            >>> print(f"Total cost: ${summary['total_cost']}")
        """
        if not records:
            return {
                'total_records': 0,
                'total_cost': 0.0,
                'total_duration': 0,
                'total_data_mb': 0.0,
                'by_type': {}
            }
        
        by_type = {}
        for record in records:
            if record.call_type not in by_type:
                by_type[record.call_type] = {
                    'count': 0,
                    'cost': 0.0,
                    'duration': 0,
                    'data_mb': 0.0
                }
            
            by_type[record.call_type]['count'] += 1
            by_type[record.call_type]['cost'] += record.cost
            by_type[record.call_type]['duration'] += record.duration_seconds
            by_type[record.call_type]['data_mb'] += record.data_mb
        
        return {
            'total_records': len(records),
            'total_cost': CDRService.calculate_total_cost(records),
            'total_duration': sum(r.duration_seconds for r in records),
            'total_data_mb': round(sum(r.data_mb for r in records), 2),
            'by_type': by_type
        }


# ==================== 異常類別 ====================

class CDRServiceException(Exception):
    """CDR 服務異常"""
    pass


# ==================== 便利函數 ====================

def parse_cdr_file(filepath: str) -> List[SimpleCDRRecord]:
    """
    便利函數：解析 CDR 檔案
    
    Args:
        filepath: CDR 檔案路徑
    
    Returns:
        List[SimpleCDRRecord]: 記錄列表
    
    Example:
        >>> from src.services.cdr_service import parse_cdr_file
        >>> records = parse_cdr_file('/path/to/cdr.dat')
    """
    service = CDRService()
    return service.parse_file(filepath)


def download_latest_cdr() -> Tuple[str, List[SimpleCDRRecord]]:
    """
    便利函數：下載並解析最新 CDR
    
    Returns:
        Tuple[str, List[SimpleCDRRecord]]: (檔案名稱, 記錄列表)
    
    Example:
        >>> from src.services.cdr_service import download_latest_cdr
        >>> filename, records = download_latest_cdr()
        >>> print(f"Downloaded {filename}: {len(records)} records")
    """
    service = CDRService()
    return service.download_and_parse_latest_cdr()

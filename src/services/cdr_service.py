"""
CDR 通訊紀錄解析服務
整合 FTP 下載功能，精確解析 .dat 檔案
時間戳記從 UTC 轉換為 Asia/Taipei (UTC+8)
"""
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List, Tuple
import re
from ..models import CDRRecord
from ..infrastructure.ftp_client import CDRDownloader, CDRDownloadException


class CDRService:
    """CDR 服務類別"""
    
    # CDR 原始格式正則表達式
    # 格式範例：IMEI,DateTime(UTC),Duration(sec),Data(MB),Type,Destination,Cost
    CDR_PATTERN = re.compile(
        r'^\s*([0-9]{15})\s*,\s*'  # IMEI (15位數字)
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*,\s*'  # DateTime (UTC)
        r'(\d+)\s*,\s*'  # Duration (秒)
        r'([0-9.]+)\s*,\s*'  # Data (MB)
        r'(\w+)\s*,\s*'  # Type (voice/sms/data)
        r'([^,]*)\s*,\s*'  # Destination (可為空)
        r'([0-9.]+)\s*$'  # Cost
    )
    
    @staticmethod
    def parse_raw_line(line: str) -> Optional[CDRRecord]:
        """解析 Iridium 原始 CDR 文字行"""
        try:
            line = line.strip()
            if not line or line.startswith('#'):
                return None
            
            match = CDRService.CDR_PATTERN.match(line)
            if not match:
                return CDRService._parse_simple(line)
            
            imei = match.group(1)
            datetime_str = match.group(2)
            duration_seconds = int(match.group(3))
            data_mb = float(match.group(4))
            call_type = match.group(5)
            destination = match.group(6).strip() or None
            cost = float(match.group(7))
            
            call_datetime_utc = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            call_datetime_utc = call_datetime_utc.replace(tzinfo=ZoneInfo('UTC'))
            
            taipei_tz = ZoneInfo('Asia/Taipei')
            call_datetime_taipei = call_datetime_utc.astimezone(taipei_tz)
            
            record = CDRRecord(
                imei=imei,
                call_datetime=call_datetime_taipei,
                duration_seconds=duration_seconds,
                data_mb=data_mb,
                call_type=call_type,
                destination=destination,
                cost=cost,
                timezone='Asia/Taipei'
            )
            
            return record
        except Exception:
            return None
    
    @staticmethod
    def _parse_simple(line: str) -> Optional[CDRRecord]:
        """簡單分割解析（備用方案）"""
        try:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 5:
                return None
            
            imei = parts[0]
            datetime_str = parts[1]
            duration_seconds = int(parts[2])
            data_mb = float(parts[3])
            call_type = parts[4]
            destination = parts[5] if len(parts) > 5 and parts[5] else None
            cost = float(parts[6]) if len(parts) > 6 and parts[6] else 0.0
            
            call_datetime_utc = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            call_datetime_utc = call_datetime_utc.replace(tzinfo=ZoneInfo('UTC'))
            
            taipei_tz = ZoneInfo('Asia/Taipei')
            call_datetime_taipei = call_datetime_utc.astimezone(taipei_tz)
            
            record = CDRRecord(
                imei=imei,
                call_datetime=call_datetime_taipei,
                duration_seconds=duration_seconds,
                data_mb=data_mb,
                call_type=call_type,
                destination=destination,
                cost=cost,
                timezone='Asia/Taipei'
            )
            
            return record
        except Exception:
            return None
    
    @staticmethod
    def parse_multiple_lines(lines):
        """批次解析多行 CDR 記錄"""
        records = []
        for line in lines:
            record = CDRService.parse_raw_line(line)
            if record:
                records.append(record)
        return records
    
    @staticmethod
    def parse_dat_file(content: bytes):
        """解析 .dat 檔案內容"""
        try:
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    text = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                text = content.decode('utf-8', errors='ignore')
            
            lines = text.split('\n')
            return CDRService.parse_multiple_lines(lines)
        except Exception:
            return []
    
    @staticmethod
    def download_and_parse_latest_cdr():
        """從 FTP 下載並解析最新的 CDR 檔案"""
        try:
            with CDRDownloader() as downloader:
                filename, content = downloader.get_latest_cdr()
                records = CDRService.parse_dat_file(content)
                return filename, records
        except CDRDownloadException:
            raise
        except Exception as e:
            raise CDRDownloadException(f"Failed to download and parse CDR: {str(e)}")
    
    @staticmethod
    def filter_by_imei(records, imei: str):
        """依 IMEI 篩選記錄"""
        return [r for r in records if r.imei == imei]
    
    @staticmethod
    def calculate_total_cost(records) -> float:
        """計算總費用"""
        return sum(r.cost for r in records)
    
    @staticmethod
    def get_usage_summary(records) -> dict:
        """取得使用量摘要"""
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
            'total_data_mb': sum(r.data_mb for r in records),
            'by_type': by_type
        }

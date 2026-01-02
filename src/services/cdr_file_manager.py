"""
CDR 檔案管理器
自動從 Iridium FTP 下載 CDR 檔案並管理保留策略

功能：
1. 自動連接 FTP 下載最新檔案
2. 解析檔案名稱（日期、時間）
3. 管理 6 個月保留策略
4. 上傳到 Google Drive
5. 清理過期檔案
"""
from __future__ import annotations
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta, date
from pathlib import Path
import re
from dataclasses import dataclass

from src.infrastructure.ftp_client import FTPClient


@dataclass
class CDRFileInfo:
    """CDR 檔案資訊"""
    filename: str                    # 檔案名稱
    file_date: date                  # 檔案日期
    file_hour: Optional[int]         # 檔案小時 (0-23)
    size_bytes: int                  # 檔案大小
    ftp_path: str                    # FTP 路徑
    local_path: Optional[str] = None # 本地路徑
    gdrive_id: Optional[str] = None  # Google Drive ID
    downloaded: bool = False         # 是否已下載
    uploaded: bool = False           # 是否已上傳


class CDRFileManager:
    """
    CDR 檔案管理器
    
    管理 CDR 檔案的完整生命週期：
    1. 從 FTP 下載
    2. 本地暫存
    3. 上傳到 Google Drive
    4. 清理過期檔案
    """
    
    # 檔案名稱模式
    # 範例：cdr_20250130_00.dat, CDRD123_20250130.dat
    FILENAME_PATTERNS = [
        r'cdr_(\d{8})_(\d{2})\.dat',      # cdr_YYYYMMDD_HH.dat
        r'CDRD\d+_(\d{8})\.dat',           # CDRD123_YYYYMMDD.dat
        r'(\d{8})_(\d{2})\.dat',           # YYYYMMDD_HH.dat
        r'(\d{8})\.dat'                    # YYYYMMDD.dat
    ]
    
    def __init__(self,
                 ftp_client: FTPClient,
                 local_cache_dir: str = './cdr_cache',
                 retention_months: int = 6):
        """
        初始化 CDR 檔案管理器
        
        Args:
            ftp_client: FTP 客戶端
            local_cache_dir: 本地快取目錄
            retention_months: 保留月數（預設 6 個月）
        """
        self.ftp_client = ftp_client
        self.local_cache_dir = Path(local_cache_dir)
        self.retention_months = retention_months
        
        # 確保快取目錄存在
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_filename(self, filename: str) -> Optional[CDRFileInfo]:
        """
        解析 CDR 檔案名稱
        
        Args:
            filename: 檔案名稱
            
        Returns:
            CDRFileInfo 或 None（無法解析）
            
        Example:
            >>> manager = CDRFileManager(ftp_client)
            >>> info = manager.parse_filename('cdr_20250130_15.dat')
            >>> print(info.file_date)  # 2025-01-30
            >>> print(info.file_hour)  # 15
        """
        for pattern in self.FILENAME_PATTERNS:
            match = re.match(pattern, filename)
            if match:
                groups = match.groups()
                
                # 解析日期
                date_str = groups[0]
                try:
                    file_date = datetime.strptime(date_str, '%Y%m%d').date()
                except ValueError:
                    continue
                
                # 解析小時（如果有）
                file_hour = None
                if len(groups) > 1 and groups[1]:
                    try:
                        file_hour = int(groups[1])
                        if not (0 <= file_hour <= 23):
                            continue
                    except (ValueError, TypeError):
                        pass
                
                return CDRFileInfo(
                    filename=filename,
                    file_date=file_date,
                    file_hour=file_hour,
                    size_bytes=0,  # 稍後從 FTP 取得
                    ftp_path=''    # 稍後設定
                )
        
        return None
    
    def list_files(self) -> List[str]:
        """
        列出 FTP 上的所有 CDR 檔案名稱（便捷方法）
        
        Returns:
            檔案名稱列表
        """
        ftp_files = self.ftp_client.list_files()
        return [f['name'] for f in ftp_files if f['name'].endswith('.dat')]
    
    def list_ftp_files(self,
                       start_date: Optional[date] = None,
                       end_date: Optional[date] = None) -> List[CDRFileInfo]:
        """
        列出 FTP 上的 CDR 檔案
        
        Args:
            start_date: 開始日期（含）
            end_date: 結束日期（含）
            
        Returns:
            CDR 檔案資訊列表
            
        Example:
            >>> files = manager.list_ftp_files(
            ...     start_date=date(2025, 1, 1),
            ...     end_date=date(2025, 1, 31)
            ... )
            >>> print(f"找到 {len(files)} 個檔案")
        """
        # 列出 FTP 目錄
        ftp_files = self.ftp_client.list_files()
        
        cdr_files = []
        for ftp_file in ftp_files:
            # 解析檔案名稱
            file_info = self.parse_filename(ftp_file['name'])
            if not file_info:
                continue
            
            # 日期篩選
            if start_date and file_info.file_date < start_date:
                continue
            if end_date and file_info.file_date > end_date:
                continue
            
            # 更新檔案資訊
            file_info.size_bytes = ftp_file.get('size', 0)
            file_info.ftp_path = ftp_file['path']
            
            cdr_files.append(file_info)
        
        # 按日期和時間排序
        cdr_files.sort(key=lambda f: (f.file_date, f.file_hour or 0))
        
        return cdr_files
    
    def download_file(self, file_info: CDRFileInfo) -> bool:
        """
        下載單個 CDR 檔案
        
        Args:
            file_info: 檔案資訊
            
        Returns:
            是否成功下載
            
        Example:
            >>> success = manager.download_file(file_info)
            >>> if success:
            ...     print(f"已下載到: {file_info.local_path}")
        """
        try:
            # 建立本地路徑
            local_path = self.local_cache_dir / file_info.filename
            
            # 下載檔案
            self.ftp_client.download_file(
                remote_path=file_info.ftp_path,
                local_path=str(local_path)
            )
            
            # 更新檔案資訊
            file_info.local_path = str(local_path)
            file_info.downloaded = True
            
            return True
            
        except Exception as e:
            print(f"❌ 下載失敗 {file_info.filename}: {e}")
            return False
    
    def download_date_range(self,
                           start_date: date,
                           end_date: date,
                           skip_existing: bool = True) -> Dict[str, any]:
        """
        下載日期範圍內的所有 CDR 檔案
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            skip_existing: 跳過已存在的檔案
            
        Returns:
            下載結果統計
            
        Example:
            >>> result = manager.download_date_range(
            ...     start_date=date(2025, 1, 1),
            ...     end_date=date(2025, 1, 31)
            ... )
            >>> print(f"成功: {result['success']}, 失敗: {result['failed']}")
        """
        # 列出 FTP 檔案
        ftp_files = self.list_ftp_files(start_date, end_date)
        
        results = {
            'total': len(ftp_files),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'files': []
        }
        
        for file_info in ftp_files:
            # 檢查本地是否已存在
            local_path = self.local_cache_dir / file_info.filename
            if skip_existing and local_path.exists():
                results['skipped'] += 1
                file_info.local_path = str(local_path)
                file_info.downloaded = True
                results['files'].append(file_info)
                continue
            
            # 下載檔案
            if self.download_file(file_info):
                results['success'] += 1
            else:
                results['failed'] += 1
            
            results['files'].append(file_info)
        
        return results
    
    def download_latest(self, hours: int = 24) -> Dict[str, any]:
        """
        下載最近 N 小時的 CDR 檔案
        
        Args:
            hours: 最近小時數
            
        Returns:
            下載結果統計
            
        Example:
            >>> result = manager.download_latest(hours=24)
            >>> print(f"下載了最近 24 小時的 {result['success']} 個檔案")
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=(hours // 24 + 1))
        
        return self.download_date_range(start_date, end_date)
    
    def get_local_files(self) -> List[CDRFileInfo]:
        """
        取得本地快取中的所有 CDR 檔案
        
        Returns:
            本地 CDR 檔案列表
        """
        local_files = []
        
        for file_path in self.local_cache_dir.glob('*.dat'):
            file_info = self.parse_filename(file_path.name)
            if file_info:
                file_info.local_path = str(file_path)
                file_info.downloaded = True
                file_info.size_bytes = file_path.stat().st_size
                local_files.append(file_info)
        
        # 按日期排序
        local_files.sort(key=lambda f: (f.file_date, f.file_hour or 0))
        
        return local_files
    
    def cleanup_old_files(self,
                         keep_months: Optional[int] = None,
                         dry_run: bool = False) -> Dict[str, any]:
        """
        清理過期的本地 CDR 檔案
        
        Args:
            keep_months: 保留月數（預設使用 retention_months）
            dry_run: 乾跑模式（只列出不刪除）
            
        Returns:
            清理結果統計
            
        Example:
            >>> # 先查看會刪除什麼
            >>> result = manager.cleanup_old_files(dry_run=True)
            >>> print(f"將刪除 {result['to_delete']} 個檔案")
            >>> 
            >>> # 確認後執行刪除
            >>> result = manager.cleanup_old_files(dry_run=False)
            >>> print(f"已刪除 {result['deleted']} 個檔案")
        """
        keep_months = keep_months or self.retention_months
        cutoff_date = date.today() - timedelta(days=keep_months * 30)
        
        local_files = self.get_local_files()
        
        results = {
            'total': len(local_files),
            'to_delete': 0,
            'deleted': 0,
            'kept': 0,
            'errors': 0,
            'files': []
        }
        
        for file_info in local_files:
            if file_info.file_date < cutoff_date:
                results['to_delete'] += 1
                
                if not dry_run:
                    try:
                        Path(file_info.local_path).unlink()
                        results['deleted'] += 1
                        results['files'].append({
                            'filename': file_info.filename,
                            'date': file_info.file_date.isoformat(),
                            'action': 'deleted'
                        })
                    except Exception as e:
                        results['errors'] += 1
                        results['files'].append({
                            'filename': file_info.filename,
                            'date': file_info.file_date.isoformat(),
                            'action': 'error',
                            'error': str(e)
                        })
                else:
                    results['files'].append({
                        'filename': file_info.filename,
                        'date': file_info.file_date.isoformat(),
                        'action': 'would_delete'
                    })
            else:
                results['kept'] += 1
        
        return results
    
    def get_statistics(self) -> Dict[str, any]:
        """
        取得 CDR 檔案統計資訊
        
        Returns:
            統計資訊
        """
        local_files = self.get_local_files()
        
        if not local_files:
            return {
                'total_files': 0,
                'total_size_mb': 0,
                'oldest_date': None,
                'newest_date': None,
                'date_range_days': 0
            }
        
        total_size = sum(f.size_bytes for f in local_files)
        oldest_date = min(f.file_date for f in local_files)
        newest_date = max(f.file_date for f in local_files)
        
        return {
            'total_files': len(local_files),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'oldest_date': oldest_date.isoformat(),
            'newest_date': newest_date.isoformat(),
            'date_range_days': (newest_date - oldest_date).days,
            'by_month': self._group_by_month(local_files)
        }
    
    def _group_by_month(self, files: List[CDRFileInfo]) -> Dict[str, int]:
        """
        按月份分組統計檔案數量
        
        Args:
            files: CDR 檔案列表
            
        Returns:
            {YYYY-MM: count}
        """
        by_month = {}
        
        for file_info in files:
            month_key = file_info.file_date.strftime('%Y-%m')
            by_month[month_key] = by_month.get(month_key, 0) + 1
        
        return dict(sorted(by_month.items()))

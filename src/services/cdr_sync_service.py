"""
CDR 同步服務
整合 FTP 下載和 Google Drive 上傳的完整工作流程

功能：
1. 自動從 FTP 下載最新檔案
2. 上傳到 Google Drive
3. 管理 6 個月保留策略
4. 提供狀態監控
"""
from __future__ import annotations
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from pathlib import Path
import logging

from src.infrastructure.ftp_client import FTPClient
from src.infrastructure.gdrive_client import GoogleDriveClient
from src.services.cdr_file_manager import CDRFileManager, CDRFileInfo


class CDRSyncService:
    """
    CDR 同步服務
    
    協調 FTP 下載、本地快取和 Google Drive 上傳
    """
    
    def __init__(self,
                 ftp_client: FTPClient,
                 gdrive_client: Optional[GoogleDriveClient] = None,
                 local_cache_dir: str = './cdr_cache',
                 retention_months: int = 6,
                 logger: Optional[logging.Logger] = None):
        """
        初始化 CDR 同步服務
        
        Args:
            ftp_client: FTP 客戶端
            gdrive_client: Google Drive 客戶端（可選）
            local_cache_dir: 本地快取目錄
            retention_months: 保留月數
            logger: 日誌記錄器
        """
        self.ftp_client = ftp_client
        self.gdrive_client = gdrive_client
        self.file_manager = CDRFileManager(
            ftp_client,
            local_cache_dir,
            retention_months
        )
        self.retention_months = retention_months
        self.logger = logger or logging.getLogger(__name__)
    
    def sync_latest(self, hours: int = 24) -> Dict[str, any]:
        """
        同步最新的 CDR 檔案
        
        完整流程：
        1. 從 FTP 下載最近 N 小時的檔案
        2. 上傳到 Google Drive（如果啟用）
        3. 返回統計結果
        
        Args:
            hours: 同步最近幾小時的檔案
            
        Returns:
            同步結果統計
            
        Example:
            >>> service = CDRSyncService(ftp_client, gdrive_client)
            >>> result = service.sync_latest(hours=24)
            >>> print(f"下載: {result['downloaded']}, 上傳: {result['uploaded']}")
        """
        self.logger.info(f"開始同步最近 {hours} 小時的 CDR 檔案")
        
        # 1. 下載檔案
        download_result = self.file_manager.download_latest(hours)
        
        result = {
            'downloaded': download_result['success'],
            'download_skipped': download_result['skipped'],
            'download_failed': download_result['failed'],
            'uploaded': 0,
            'upload_failed': 0,
            'total_files': download_result['total'],
            'files': []
        }
        
        # 2. 上傳到 Google Drive
        if self.gdrive_client:
            for file_info in download_result['files']:
                if not file_info.downloaded:
                    continue
                
                try:
                    gdrive_result = self.gdrive_client.upload_file(
                        local_path=file_info.local_path,
                        file_date=file_info.file_date
                    )
                    
                    file_info.gdrive_id = gdrive_result['id']
                    file_info.uploaded = True
                    result['uploaded'] += 1
                    
                    self.logger.info(f"✅ 已上傳: {file_info.filename}")
                    
                except Exception as e:
                    result['upload_failed'] += 1
                    self.logger.error(f"❌ 上傳失敗 {file_info.filename}: {e}")
                
                result['files'].append({
                    'filename': file_info.filename,
                    'date': file_info.file_date.isoformat(),
                    'downloaded': file_info.downloaded,
                    'uploaded': file_info.uploaded,
                    'gdrive_id': file_info.gdrive_id
                })
        else:
            self.logger.info("⏭️ 跳過 Google Drive 上傳（未啟用）")
        
        self.logger.info(
            f"同步完成: 下載 {result['downloaded']}, "
            f"上傳 {result['uploaded']}"
        )
        
        return result
    
    def sync_date_range(self,
                       start_date: date,
                       end_date: date) -> Dict[str, any]:
        """
        同步指定日期範圍的 CDR 檔案
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            同步結果統計
        """
        self.logger.info(f"同步日期範圍: {start_date} ~ {end_date}")
        
        # 1. 下載檔案
        download_result = self.file_manager.download_date_range(
            start_date,
            end_date
        )
        
        result = {
            'downloaded': download_result['success'],
            'download_skipped': download_result['skipped'],
            'download_failed': download_result['failed'],
            'uploaded': 0,
            'upload_failed': 0,
            'total_files': download_result['total'],
            'files': []
        }
        
        # 2. 上傳到 Google Drive
        if self.gdrive_client:
            for file_info in download_result['files']:
                if not file_info.downloaded:
                    continue
                
                try:
                    gdrive_result = self.gdrive_client.upload_file(
                        local_path=file_info.local_path,
                        file_date=file_info.file_date
                    )
                    
                    file_info.gdrive_id = gdrive_result['id']
                    file_info.uploaded = True
                    result['uploaded'] += 1
                    
                except Exception as e:
                    result['upload_failed'] += 1
                    self.logger.error(f"❌ 上傳失敗 {file_info.filename}: {e}")
                
                result['files'].append({
                    'filename': file_info.filename,
                    'date': file_info.file_date.isoformat(),
                    'downloaded': file_info.downloaded,
                    'uploaded': file_info.uploaded
                })
        
        return result
    
    def cleanup_old_files(self,
                         keep_months: Optional[int] = None,
                         dry_run: bool = False) -> Dict[str, any]:
        """
        清理過期檔案（本地 + Google Drive）
        
        Args:
            keep_months: 保留月數
            dry_run: 乾跑模式
            
        Returns:
            清理結果統計
        """
        keep_months = keep_months or self.retention_months
        cutoff_date = date.today() - timedelta(days=keep_months * 30)
        
        self.logger.info(f"清理 {cutoff_date} 之前的檔案（保留 {keep_months} 個月）")
        
        result = {
            'local_deleted': 0,
            'gdrive_deleted': 0,
            'errors': 0
        }
        
        # 1. 清理本地檔案
        local_result = self.file_manager.cleanup_old_files(
            keep_months,
            dry_run
        )
        result['local_deleted'] = local_result['deleted']
        result['local_to_delete'] = local_result['to_delete']
        
        # 2. 清理 Google Drive
        if self.gdrive_client and not dry_run:
            try:
                gdrive_result = self.gdrive_client.cleanup_old_files(
                    cutoff_date,
                    dry_run
                )
                result['gdrive_deleted'] = gdrive_result['deleted']
                result['gdrive_to_delete'] = gdrive_result['to_delete']
            except Exception as e:
                self.logger.error(f"❌ Google Drive 清理失敗: {e}")
                result['errors'] += 1
        
        self.logger.info(
            f"清理完成: 本地 {result['local_deleted']}, "
            f"GDrive {result.get('gdrive_deleted', 0)}"
        )
        
        return result
    
    def get_sync_status(self) -> Dict[str, any]:
        """
        取得同步狀態
        
        Returns:
            狀態資訊
        """
        status = {
            'local': self.file_manager.get_statistics(),
            'gdrive': None,
            'retention_months': self.retention_months,
            'gdrive_enabled': self.gdrive_client is not None
        }
        
        # Google Drive 狀態
        if self.gdrive_client:
            try:
                status['gdrive'] = self.gdrive_client.get_storage_usage()
            except Exception as e:
                self.logger.error(f"取得 GDrive 狀態失敗: {e}")
        
        return status
    
    def verify_sync(self) -> Dict[str, any]:
        """
        驗證本地和 Google Drive 的同步狀態
        
        Returns:
            驗證結果
        """
        if not self.gdrive_client:
            return {
                'verified': False,
                'message': 'Google Drive 未啟用'
            }
        
        local_files = self.file_manager.get_local_files()
        
        result = {
            'total_local': len(local_files),
            'verified': 0,
            'missing_on_gdrive': 0,
            'missing_files': []
        }
        
        for file_info in local_files:
            # 查詢 Google Drive
            folder_id = self.gdrive_client.get_month_folder_id(file_info.file_date)
            gdrive_file = self.gdrive_client.find_file(
                file_info.filename,
                folder_id
            )
            
            if gdrive_file:
                result['verified'] += 1
            else:
                result['missing_on_gdrive'] += 1
                result['missing_files'].append({
                    'filename': file_info.filename,
                    'date': file_info.file_date.isoformat()
                })
        
        return result

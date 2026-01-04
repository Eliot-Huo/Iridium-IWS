"""
CDR 增量同步管理器
只處理 FTP 上的新檔案，避免重複下載和處理

核心功能：
1. 追蹤已處理的檔案（保存在 Google Drive）
2. 每次只處理新檔案
3. 支援斷點續傳（每 10 個檔案保存一次狀態）
4. 自動分類到月份資料夾
5. 跨月檔案自動複製到多個資料夾
"""
from __future__ import annotations
from typing import List, Set, Dict, Optional
from datetime import datetime, date
from pathlib import Path
import json
import os

from src.infrastructure.ftp_client import FTPClient
from src.infrastructure.gdrive_client import GoogleDriveClient, GDRIVE_AVAILABLE
from src.parsers.tapii_parser import TAPIIParser


class SyncStatus:
    """同步狀態"""
    
    def __init__(self, data: dict = None):
        """初始化同步狀態"""
        self.data = data or {
            'version': '1.0',
            'initial_sync_completed': False,
            'last_sync_time': None,
            'total_files_processed': 0,
            'processed_files': {},
            'monthly_stats': {},
            'errors': {}
        }
    
    def is_file_processed(self, filename: str) -> bool:
        """檢查檔案是否已處理"""
        return filename in self.data['processed_files']
    
    def add_processed_file(self, filename: str, info: dict):
        """添加已處理檔案"""
        self.data['processed_files'][filename] = info
        self.data['total_files_processed'] = len(self.data['processed_files'])
    
    def update_monthly_stats(self, month: str, file_count: int, record_count: int):
        """更新月份統計"""
        if month not in self.data['monthly_stats']:
            self.data['monthly_stats'][month] = {
                'file_count': 0,
                'total_records': 0,
                'last_updated': None
            }
        
        self.data['monthly_stats'][month]['file_count'] += file_count
        self.data['monthly_stats'][month]['total_records'] += record_count
        self.data['monthly_stats'][month]['last_updated'] = datetime.now().isoformat()
    
    def mark_complete(self):
        """標記初始同步完成"""
        self.data['initial_sync_completed'] = True
        self.data['last_sync_time'] = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return self.data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SyncStatus':
        """從字典創建"""
        return cls(data)


class IncrementalSyncManager:
    """增量同步管理器"""
    
    STATUS_FILENAME = '.sync_status.json'
    TEMP_DIR = './temp/ftp_download'
    CHECKPOINT_INTERVAL = 10  # 每處理 10 個檔案保存一次
    
    def __init__(self,
                 ftp_client: FTPClient,
                 gdrive_client: Optional[GoogleDriveClient] = None):
        """
        初始化增量同步管理器
        
        Args:
            ftp_client: FTP 客戶端
            gdrive_client: Google Drive 客戶端（可選）
        """
        self.ftp = ftp_client
        self.gdrive = gdrive_client
        self.parser = TAPIIParser()
        
        # 確保臨時目錄存在
        Path(self.TEMP_DIR).mkdir(parents=True, exist_ok=True)
    
    def sync(self, progress_callback=None) -> dict:
        """
        執行增量同步
        
        Args:
            progress_callback: 進度回調函式 (message: str) -> None
            
        Returns:
            同步結果統計
        """
        # 0. 確保 FTP 已連接
        if progress_callback:
            progress_callback("📡 連接 FTP...")
        
        if not self.ftp._ftp:
            try:
                self.ftp.connect()
                if progress_callback:
                    progress_callback("✅ FTP 連線成功")
            except Exception as e:
                if progress_callback:
                    progress_callback(f"❌ FTP 連線失敗: {e}")
                raise
        
        # 1. 載入同步狀態
        if progress_callback:
            progress_callback("📥 載入同步狀態...")
        
        status = self._load_status()
        
        # 2. 列出 FTP 檔案
        if progress_callback:
            progress_callback("📋 列出 FTP 檔案...")
        
        ftp_files = self._list_ftp_files()
        total_ftp_files = len(ftp_files)
        
        if progress_callback:
            progress_callback(f"📊 FTP 總檔案數: {total_ftp_files}")
        
        # 3. 計算需要處理的檔案
        new_files = [f for f in ftp_files if not status.is_file_processed(f)]
        new_file_count = len(new_files)
        
        if new_file_count == 0:
            if progress_callback:
                progress_callback(f"✅ 所有檔案已同步（共 {total_ftp_files} 個）")
            
            return {
                'status': 'up_to_date',
                'total_files': total_ftp_files,
                'new_files': 0,
                'processed_files': len(status.data['processed_files']),
                'errors': 0
            }
        
        # 4. 處理新檔案
        if progress_callback:
            progress_callback(f"📥 開始處理 {new_file_count} 個檔案...")
        
        processed_count = 0
        error_count = 0
        uploaded_count = 0  # 統計成功上傳的檔案
        
        for i, filename in enumerate(new_files):
            try:
                # 進度更新
                progress = (i + 1) / new_file_count
                if progress_callback:
                    progress_callback(
                        f"\n{'='*60}\n📥 處理檔案 ({i+1}/{new_file_count}): {filename}",
                        progress
                    )
                
                # 處理單個檔案
                if progress_callback:
                    progress_callback(f"  ⬇️  從 FTP 下載中...")
                
                try:
                    result = self._process_file(filename)
                except Exception as file_error:
                    if progress_callback:
                        progress_callback(f"  ❌ 處理失敗: {str(file_error)}")
                        progress_callback(f"     錯誤類型: {type(file_error).__name__}")
                    raise
                
                # 顯示處理結果
                if progress_callback:
                    progress_callback(f"  ✅ 處理完成")
                    progress_callback(f"     - 檔案大小: {result['file_size'] / 1024:.1f} KB")
                    progress_callback(f"     - 記錄數: {result['record_count']} 筆")
                    progress_callback(f"     - 月份: {', '.join(result['months'])}")
                    if result.get('uploaded_to_gdrive'):
                        progress_callback(f"     - 已上傳到 Google Drive: {', '.join(result['uploaded_to_gdrive'])}")
                        uploaded_count += 1  # 計數成功上傳
                    else:
                        progress_callback(f"     - ⚠️ 未上傳到 Google Drive")
                        # 顯示具體的錯誤原因
                        if result.get('upload_errors'):
                            for error in result['upload_errors']:
                                progress_callback(f"       錯誤: {error}")
                
                # 更新狀態
                status.add_processed_file(filename, result)
                
                # 更新月份統計
                for month in result['months']:
                    status.update_monthly_stats(
                        month,
                        file_count=1,
                        record_count=result['record_count']
                    )
                
                processed_count += 1
                
                # 定期保存（斷點續傳）
                if (i + 1) % self.CHECKPOINT_INTERVAL == 0:
                    self._save_status(status)
                    if progress_callback:
                        progress_callback(f"💾 已保存進度（{i+1}/{new_file_count}）")
                
            except Exception as e:
                error_count += 1
                status.data['errors'][filename] = str(e)
                
                if progress_callback:
                    progress_callback(f"⚠️ {filename} 處理失敗: {e}")
        
        # 5. 最終保存
        status.mark_complete()
        self._save_status(status)
        
        if progress_callback:
            progress_callback(f"✅ 同步完成！處理了 {processed_count} 個新檔案，成功上傳 {uploaded_count} 個，{error_count} 個失敗")
        
        return {
            'status': 'synced',
            'total_files': total_ftp_files,
            'new_files': new_file_count,
            'processed_files': processed_count,
            'uploaded_files': uploaded_count,
            'errors': error_count
        }
    
    def _process_file(self, filename: str) -> dict:
        """
        處理單個檔案
        
        Args:
            filename: 檔案名稱
            
        Returns:
            處理結果
        """
        # 1. 下載到臨時目錄
        local_path = os.path.join(self.TEMP_DIR, filename)
        
        # FTPClient.download_file() 返回 bytes
        file_content = self.ftp.download_file(filename)
        with open(local_path, 'wb') as f:
            f.write(file_content)
        
        # 2. 解析日期（改為按日）
        dates = self.parser.extract_dates(local_path)
        months = self.parser.extract_months(local_path)  # 保留月份資訊用於統計
        record_count = self.parser.count_records(local_path)
        file_size = os.path.getsize(local_path)
        
        # 3. 上傳到 Google Drive（按日上傳）
        uploaded_to = []
        upload_errors = []
        
        if self.gdrive and GDRIVE_AVAILABLE:
            for date_str in dates:
                try:
                    # 將 YYYYMMDD 轉換為 date 物件
                    # 例如 '20251213' -> date(2025, 12, 13)
                    year = int(date_str[:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])
                    file_date = date(year, month, day)
                    
                    # 上傳到對應年/月/日資料夾（例如：2025/12/13/）
                    upload_result = self.gdrive.upload_file(
                        local_path=local_path,
                        file_date=file_date,
                        filename=filename,
                        use_day_folder=True  # 使用日期資料夾
                    )
                    uploaded_to.append(f"{year}/{month:02d}/{day:02d}")
                    
                    # 記錄上傳成功
                    print(f"✅ 上傳成功到 {year}/{month:02d}/{day:02d}: {upload_result.get('name')}")
                
                except Exception as upload_error:
                    # 記錄上傳錯誤
                    error_msg = f"上傳到 {year}/{month:02d}/{day:02d} 失敗: {str(upload_error)}"
                    upload_errors.append(error_msg)
                    print(f"❌ {error_msg}")
                    # 繼續處理其他日期
        else:
            # Google Drive 不可用
            print(f"⚠️ Google Drive 不可用: gdrive={self.gdrive}, GDRIVE_AVAILABLE={GDRIVE_AVAILABLE}")
            upload_errors.append("Google Drive 未初始化或不可用")
        
        # 4. 刪除本地檔案
        os.remove(local_path)
        
        # 5. 返回處理結果
        return {
            'processed_at': datetime.now().isoformat(),
            'file_size': file_size,
            'dates': sorted(list(dates)),  # 新增：日期列表
            'months': sorted(list(months)),  # 保留：月份列表（用於統計）
            'record_count': record_count,
            'uploaded_to_gdrive': uploaded_to,
            'upload_errors': upload_errors
        }
    
    def _list_ftp_files(self) -> List[str]:
        """列出 FTP 所有檔案
        
        注意：FTPClient.list_files() 返回 List[Tuple[str, datetime, int]]
        格式：(filename, modified_time, size)
        """
        files = self.ftp.list_files()
        # files 是 List[Tuple[filename, datetime, size]]
        # 取 tuple 的第一個元素（index 0）作為檔名
        return [f[0] for f in files if f[0].endswith('.dat')]
    
    def _load_status(self) -> SyncStatus:
        """從 Google Drive 載入同步狀態"""
        if not self.gdrive or not GDRIVE_AVAILABLE:
            # 如果沒有 Google Drive，使用本地狀態
            print("⚠️ Google Drive 不可用，嘗試載入本地狀態")
            return self._load_local_status()
        
        try:
            print(f"📥 正在從 Google Drive 載入同步狀態...")
            
            # 從 Google Drive 根目錄下載狀態檔案
            content = self.gdrive.download_file_content(self.STATUS_FILENAME)
            data = json.loads(content)
            status = SyncStatus.from_dict(data)
            
            processed_count = len(status.data.get('processed_files', {}))
            print(f"✅ 成功從 Google Drive 載入狀態")
            print(f"   📊 已記錄 {processed_count} 個已處理檔案")
            print(f"   🕐 最後同步: {status.data.get('last_sync_time', '未知')}")
            
            return status
            
        except FileNotFoundError:
            print(f"ℹ️ Google Drive 找不到 {self.STATUS_FILENAME}")
            print("   這是第一次同步，將創建新的狀態檔案")
            return SyncStatus()
            
        except Exception as e:
            print(f"⚠️ 從 Google Drive 載入狀態失敗: {e}")
            print(f"   詳細錯誤: {type(e).__name__}")
            print("   嘗試使用本地備份...")
            return self._load_local_status()
    
    def _save_status(self, status: SyncStatus):
        """保存同步狀態到 Google Drive"""
        if not self.gdrive or not GDRIVE_AVAILABLE:
            # 如果沒有 Google Drive，保存到本地
            print("⚠️ Google Drive 不可用，保存到本地")
            self._save_local_status(status)
            return
        
        try:
            print(f"💾 正在保存同步狀態到 Google Drive...")
            
            # 確保資料可以序列化
            status_dict = status.to_dict()
            
            # 檢查並清理資料（確保沒有 date 物件）
            status_dict = self._ensure_json_serializable(status_dict)
            
            # 上傳到 Google Drive 根目錄
            content = json.dumps(status_dict, indent=2, ensure_ascii=False)
            result = self.gdrive.upload_text_file(self.STATUS_FILENAME, content)
            
            print(f"✅ 同步狀態已保存到 Google Drive")
            print(f"   📄 檔案: {self.STATUS_FILENAME}")
            print(f"   📊 已記錄 {len(status_dict.get('processed_files', {}))} 個檔案")
            
        except Exception as e:
            # 保存失敗，記錄錯誤
            print(f"❌ 保存到 Google Drive 失敗: {e}")
            print(f"   詳細錯誤: {type(e).__name__}")
            print(f"   💾 降級保存到本地...")
            # 備份到本地
            self._save_local_status(status)
    
    def _ensure_json_serializable(self, obj):
        """確保物件可以 JSON 序列化"""
        if isinstance(obj, dict):
            return {k: self._ensure_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._ensure_json_serializable(item) for item in obj]
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, set):
            return sorted(list(obj))
        else:
            return obj
    
    def _load_local_status(self) -> SyncStatus:
        """從本地載入狀態"""
        local_status_file = '.sync_status_local.json'
        
        try:
            with open(local_status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return SyncStatus.from_dict(data)
        except:
            return SyncStatus()
    
    def _save_local_status(self, status: SyncStatus):
        """保存狀態到本地"""
        local_status_file = '.sync_status_local.json'
        
        try:
            with open(local_status_file, 'w', encoding='utf-8') as f:
                json.dump(status.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 保存本地狀態失敗: {e}")
    
    def get_status(self) -> dict:
        """取得當前同步狀態"""
        status = self._load_status()
        return {
            'initial_sync_completed': status.data['initial_sync_completed'],
            'last_sync_time': status.data['last_sync_time'],
            'total_files_processed': status.data['total_files_processed'],
            'monthly_stats': status.data['monthly_stats'],
            'error_count': len(status.data['errors'])
        }
    
    def reset_status(self):
        """重置同步狀態（危險操作）"""
        status = SyncStatus()
        self._save_status(status)

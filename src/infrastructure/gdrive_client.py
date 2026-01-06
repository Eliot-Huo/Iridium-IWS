"""
Google Drive Client
Google Drive 客戶端 - 處理檔案上傳和組織
"""

from typing import List, Optional, Dict, Any
import json
import logging
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

from src.utils.exceptions import GoogleDriveError, InfrastructureError
from src.utils.types import GoogleDriveConfig


logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """
    Google Drive 客戶端
    
    負責與 Google Drive API 通訊。
    
    職責：
    - 管理 Google Drive 連線
    - 上傳檔案
    - 建立資料夾
    - 搜尋檔案
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(self, config: GoogleDriveConfig):
        """
        初始化 Google Drive 客戶端
        
        Args:
            config: Google Drive 設定
        """
        self._config = config
        self._service = None
        self._is_connected = False
        
        logger.info("GoogleDriveClient initialized")
    
    def connect(self) -> None:
        """
        建立與 Google Drive 的連線
        
        Raises:
            GoogleDriveError: 連線失敗
        """
        try:
            logger.info("Connecting to Google Drive API...")
            
            # 解析 Service Account JSON
            service_account_info = json.loads(
                self._config['service_account_json']
            )
            
            # 建立憑證
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=self.SCOPES
            )
            
            # 建立 Drive Service
            self._service = build('drive', 'v3', credentials=credentials)
            self._is_connected = True
            
            logger.info("✅ Connected to Google Drive API successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Google Drive: {e}")
            raise GoogleDriveError(
                f"無法連線到 Google Drive: {str(e)}"
            )
    
    def ensure_connected(self) -> None:
        """確保已連線"""
        if not self._is_connected or not self._service:
            self.connect()
    
    def is_connected(self) -> bool:
        """檢查連線狀態"""
        return self._is_connected and self._service is not None
    
    def create_folder(
        self,
        folder_name: str,
        parent_id: Optional[str] = None
    ) -> str:
        """
        建立資料夾
        
        Args:
            folder_name: 資料夾名稱
            parent_id: 父資料夾 ID（None 表示根目錄）
            
        Returns:
            建立的資料夾 ID
        """
        self.ensure_connected()
        
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            elif self._config.get('root_folder_id'):
                folder_metadata['parents'] = [self._config['root_folder_id']]
            
            folder = self._service.files().create(
                body=folder_metadata,
                fields='id, name'
            ).execute()
            
            logger.info(f"✅ Created folder: {folder_name} (ID: {folder['id']})")
            return folder['id']
            
        except Exception as e:
            logger.error(f"❌ Failed to create folder {folder_name}: {e}")
            raise GoogleDriveError(
                f"無法建立資料夾: {str(e)}",
                {'folder_name': folder_name}
            )
    
    def upload_file(
        self,
        local_path: Path,
        parent_id: Optional[str] = None,
        file_name: Optional[str] = None
    ) -> str:
        """
        上傳檔案
        
        Args:
            local_path: 本地檔案路徑
            parent_id: 父資料夾 ID
            file_name: 檔案名稱（None 表示使用原檔名）
            
        Returns:
            上傳的檔案 ID
        """
        self.ensure_connected()
        
        try:
            file_metadata = {
                'name': file_name or local_path.name
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            elif self._config.get('root_folder_id'):
                file_metadata['parents'] = [self._config['root_folder_id']]
            
            media = MediaFileUpload(str(local_path), resumable=True)
            
            file = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name'
            ).execute()
            
            logger.info(f"✅ Uploaded file: {file['name']} (ID: {file['id']})")
            return file['id']
            
        except Exception as e:
            logger.error(f"❌ Failed to upload {local_path}: {e}")
            raise GoogleDriveError(
                f"無法上傳檔案: {str(e)}",
                {'local_path': str(local_path)}
            )
    
    def search_files(
        self,
        query: str,
        parent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜尋檔案
        
        Args:
            query: 搜尋查詢
            parent_id: 父資料夾 ID
            
        Returns:
            檔案列表
        """
        self.ensure_connected()
        
        try:
            # 建立查詢
            q = query
            if parent_id:
                q += f" and '{parent_id}' in parents"
            
            results = self._service.files().list(
                q=q,
                fields='files(id, name, mimeType, createdTime, modifiedTime)',
                pageSize=100
            ).execute()
            
            files = results.get('files', [])
            logger.debug(f"Found {len(files)} files matching: {query}")
            return files
            
        except Exception as e:
            logger.error(f"❌ Failed to search files: {e}")
            raise GoogleDriveError(
                f"無法搜尋檔案: {str(e)}",
                {'query': query}
            )
    
    def get_or_create_folder(
        self,
        folder_name: str,
        parent_id: Optional[str] = None
    ) -> str:
        """
        取得或建立資料夾
        
        Args:
            folder_name: 資料夾名稱
            parent_id: 父資料夾 ID
            
        Returns:
            資料夾 ID
        """
        # 搜尋是否已存在
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        existing = self.search_files(query, parent_id)
        
        if existing:
            logger.debug(f"Folder exists: {folder_name} (ID: {existing[0]['id']})")
            return existing[0]['id']
        
        # 不存在則建立
        return self.create_folder(folder_name, parent_id)
    
    def delete_file(self, file_id: str) -> None:
        """
        刪除檔案
        
        Args:
            file_id: 檔案 ID
        """
        self.ensure_connected()
        
        try:
            self._service.files().delete(fileId=file_id).execute()
            logger.info(f"✅ Deleted file: {file_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to delete {file_id}: {e}")
            raise GoogleDriveError(
                f"無法刪除檔案: {str(e)}",
                {'file_id': file_id}
            )
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        取得檔案中繼資料
        
        Args:
            file_id: 檔案 ID
            
        Returns:
            檔案中繼資料
        """
        self.ensure_connected()
        
        try:
            file = self._service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, createdTime, modifiedTime, size'
            ).execute()
            
            return file
            
        except Exception as e:
            logger.error(f"❌ Failed to get metadata for {file_id}: {e}")
            raise GoogleDriveError(
                f"無法取得檔案資訊: {str(e)}",
                {'file_id': file_id}
            )

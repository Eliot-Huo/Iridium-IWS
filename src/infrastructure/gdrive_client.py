"""
Google Drive 客戶端
管理 CDR 檔案在 Google Drive 的儲存

功能：
1. 上傳 CDR 檔案到 Google Drive
2. 建立資料夾結構（按月份）
3. 查詢已上傳檔案
4. 下載檔案
5. 刪除過期檔案
"""
from __future__ import annotations
from typing import List, Optional, Dict, BinaryIO
from datetime import date, datetime
from pathlib import Path
import json
import io
import os

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from googleapiclient.errors import HttpError
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False


class GoogleDriveClient:
    """
    Google Drive 客戶端
    
    使用 Service Account 管理 Google Drive 檔案
    """
    
    # Google Drive MIME 類型
    FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'
    
    def __init__(self,
                 service_account_file: str = None,
                 service_account_json: str = None,
                 service_account_info: dict = None,
                 root_folder_name: str = 'CDR_Files',
                 root_folder_id: str = None,
                 owner_email: str = None):
        """
        初始化 Google Drive 客戶端
        
        Args:
            service_account_file: Service Account JSON 檔案路徑（擇一）
            service_account_json: Service Account JSON 字串（擇一）
            service_account_info: Service Account 字典（擇一，例如從 st.secrets）
            root_folder_name: 根資料夾名稱
            root_folder_id: 根資料夾 ID（如果已知，直接使用）
            owner_email: 擁有者 Email（建立資料夾後自動共享給此人）
            
        Raises:
            ImportError: 缺少 google-api-python-client
            ValueError: 未提供認證資訊
        """
        if not GDRIVE_AVAILABLE:
            raise ImportError(
                "需要安裝 google-api-python-client: "
                "pip install google-api-python-client google-auth"
            )
        
        # 載入 Service Account 憑證
        scopes = ['https://www.googleapis.com/auth/drive']
        
        if service_account_info:
            # 從字典載入（例如 st.secrets.gcp_service_account）
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=scopes
            )
        elif service_account_json:
            # 從 JSON 字串載入
            credentials_dict = json.loads(service_account_json)
            self.credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=scopes
            )
        elif service_account_file:
            # 從檔案載入
            self.credentials = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=scopes
            )
        else:
            raise ValueError("必須提供 service_account_file, service_account_json 或 service_account_info")
        
        # 建立 Drive API 客戶端
        self.service = build('drive', 'v3', credentials=self.credentials)
        
        # 根資料夾
        self.root_folder_name = root_folder_name
        self._root_folder_id = root_folder_id  # 如果提供了 ID，直接使用
        self.owner_email = owner_email  # 擁有者 Email（建立資料夾後自動共享）
    
    @property
    def root_folder_id(self) -> str:
        """
        取得或建立根資料夾 ID
        
        Returns:
            資料夾 ID
        """
        if self._root_folder_id is None:
            self._root_folder_id = self._get_or_create_folder(
                self.root_folder_name
            )
        return self._root_folder_id
    
    def _get_or_create_folder(self,
                             folder_name: str,
                             parent_id: Optional[str] = None) -> str:
        """
        取得或建立資料夾
        
        Args:
            folder_name: 資料夾名稱
            parent_id: 父資料夾 ID（None 表示根目錄）
            
        Returns:
            資料夾 ID
        """
        # 查詢資料夾是否存在
        query = f"name='{folder_name}' and mimeType='{self.FOLDER_MIME_TYPE}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        try:
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = response.get('files', [])
            
            if files:
                # 資料夾已存在
                return files[0]['id']
            
            # 建立新資料夾
            file_metadata = {
                'name': folder_name,
                'mimeType': self.FOLDER_MIME_TYPE
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            return folder['id']
            
        except HttpError as e:
            raise Exception(f"建立資料夾失敗: {e}")
    
    def get_month_folder_id(self, file_date: date) -> str:
        """
        取得月份資料夾 ID（自動建立 YYYY/MM 結構）
        
        Args:
            file_date: 檔案日期
            
        Returns:
            月份資料夾 ID
            
        Example:
            >>> folder_id = client.get_month_folder_id(date(2025, 1, 15))
            >>> # 會建立 CDR_Files/2025/01/
        """
        # 建立年份資料夾
        year_folder_id = self._get_or_create_folder(
            str(file_date.year),
            self.root_folder_id
        )
        
        # 建立月份資料夾
        month_folder_id = self._get_or_create_folder(
            f"{file_date.month:02d}",
            year_folder_id
        )
        
        return month_folder_id
    
    def get_day_folder_id(self, file_date: date) -> str:
        """
        取得日期資料夾 ID（自動建立 YYYY/MM/DD 結構）
        
        Args:
            file_date: 檔案日期
            
        Returns:
            日期資料夾 ID
            
        Example:
            >>> folder_id = client.get_day_folder_id(date(2025, 1, 15))
            >>> # 會建立 CDR_Files/2025/01/15/
        """
        # 先取得月份資料夾
        month_folder_id = self.get_month_folder_id(file_date)
        
        # 建立日期資料夾
        day_folder_id = self._get_or_create_folder(
            f"{file_date.day:02d}",
            month_folder_id
        )
        
        return day_folder_id
    
    def upload_file(self,
                   local_path: str,
                   file_date: date,
                   filename: Optional[str] = None,
                   use_day_folder: bool = True) -> Dict[str, str]:
        """
        上傳檔案到 Google Drive
        
        Args:
            local_path: 本地檔案路徑
            file_date: 檔案日期（用於決定資料夾）
            filename: 自訂檔案名稱（預設使用原檔名）
            use_day_folder: 是否使用日期資料夾（True: YYYY/MM/DD, False: YYYY/MM）
            
        Returns:
            {'id': 檔案ID, 'name': 檔案名稱, 'webViewLink': 連結}
            
        Example:
            >>> # 按日上傳到 2025/01/30/
            >>> result = client.upload_file(
            ...     local_path='./cdr_file.dat',
            ...     file_date=date(2025, 1, 30),
            ...     use_day_folder=True
            ... )
            
            >>> # 按月上傳到 2025/01/（向後兼容）
            >>> result = client.upload_file(
            ...     local_path='./cdr_file.dat',
            ...     file_date=date(2025, 1, 30),
            ...     use_day_folder=False
            ... )
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"檔案不存在: {local_path}")
        
        # 確定檔案名稱
        filename = filename or local_path.name
        
        # 取得目標資料夾（按日或按月）
        if use_day_folder:
            folder_id = self.get_day_folder_id(file_date)
        else:
            folder_id = self.get_month_folder_id(file_date)
        
        # 檢查檔案是否已存在
        existing_file = self.find_file(filename, folder_id)
        if existing_file:
            print(f"⚠️ 檔案已存在，將覆蓋: {filename}")
            return self.update_file(existing_file['id'], local_path)
        
        # 上傳檔案
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(
            str(local_path),
            resumable=True
        )
        
        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            return {
                'id': file['id'],
                'name': file['name'],
                'webViewLink': file.get('webViewLink', '')
            }
            
        except HttpError as e:
            raise Exception(f"上傳失敗: {e}")
    
    def update_file(self, file_id: str, local_path: str) -> Dict[str, str]:
        """
        更新已存在的檔案
        
        Args:
            file_id: Google Drive 檔案 ID
            local_path: 新的本地檔案路徑
            
        Returns:
            檔案資訊
        """
        media = MediaFileUpload(
            str(local_path),
            resumable=True
        )
        
        try:
            file = self.service.files().update(
                fileId=file_id,
                media_body=media,
                fields='id, name, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            return {
                'id': file['id'],
                'name': file['name'],
                'webViewLink': file.get('webViewLink', '')
            }
            
        except HttpError as e:
            raise Exception(f"更新失敗: {e}")
    
    def upload_text_file(self, filename: str, content: str, folder_id: str = None) -> Dict[str, str]:
        """
        上傳文字檔案到指定資料夾（預設為根資料夾）
        
        Args:
            filename: 檔案名稱
            content: 文字內容
            folder_id: 目標資料夾 ID（預設為根資料夾）
            
        Returns:
            檔案資訊 {'id': 檔案ID, 'name': 檔案名稱}
        """
        # 使用根資料夾作為預設目標
        target_folder_id = folder_id or self.root_folder_id
        
        # 檢查檔案是否已存在
        existing_file = self.find_file(filename, target_folder_id)
        
        # 寫入臨時檔案
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.json') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            if existing_file:
                # 更新現有檔案
                print(f"📝 更新現有檔案: {filename}")
                media = MediaFileUpload(temp_path, mimetype='application/json', resumable=True)
                
                updated_file = self.service.files().update(
                    fileId=existing_file['id'],
                    media_body=media,
                    fields='id, name, webViewLink'
                ).execute()
                
                return updated_file
            else:
                # 創建新檔案
                print(f"📝 創建新檔案: {filename}")
                file_metadata = {
                    'name': filename,
                    'parents': [target_folder_id],
                    'mimeType': 'application/json'
                }
                
                media = MediaFileUpload(temp_path, mimetype='application/json', resumable=True)
                
                created_file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, name, webViewLink'
                ).execute()
                
                return created_file
                
        except Exception as e:
            print(f"❌ 上傳檔案失敗: {e}")
            raise
        finally:
            # 刪除臨時檔案
            try:
                os.remove(temp_path)
            except:
                pass
    
    def download_file_content(self, filename: str, folder_id: str = None) -> str:
        """
        下載檔案內容（文字）
        
        Args:
            filename: 檔案名稱
            folder_id: 資料夾 ID（預設為根資料夾）
            
        Returns:
            檔案內容
        """
        # 使用根資料夾作為預設
        target_folder_id = folder_id or self.root_folder_id
        
        # 查詢檔案
        file_info = self.find_file(filename, target_folder_id)
        if not file_info:
            raise FileNotFoundError(f"檔案不存在: {filename} (在資料夾 {target_folder_id})")
        
        # 下載檔案
        try:
            request = self.service.files().get_media(fileId=file_info['id'])
            content = request.execute()
            return content.decode('utf-8')
        except HttpError as e:
            raise Exception(f"下載失敗: {e}")
    
    def list_files_in_folder(self, folder_path: str) -> List[Dict]:
        """
        列出資料夾內的檔案
        
        Args:
            folder_path: 資料夾路徑（例如 "202512/"）
            
        Returns:
            檔案列表
        """
        # 取得資料夾 ID
        folder_id = self._get_or_create_folder_by_path(folder_path)
        
        # 列出檔案
        query = f"'{folder_id}' in parents and trashed=false"
        
        try:
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, size, createdTime, webViewLink)',
                pageSize=1000,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            return response.get('files', [])
        except HttpError as e:
            raise Exception(f"列出檔案失敗: {e}")
    
    def _get_or_create_folder_by_path(self, folder_path: str) -> str:
        """
        根據路徑取得或建立資料夾
        
        Args:
            folder_path: 資料夾路徑（例如 "202512/" 或 "2025/12/"）
            
        Returns:
            資料夾 ID
        """
        if not folder_path or folder_path == '/':
            return self.root_folder_id
        
        # 移除開頭和結尾的斜線
        folder_path = folder_path.strip('/')
        
        # 分割路徑
        parts = folder_path.split('/')
        
        # 從根資料夾開始
        current_folder_id = self.root_folder_id
        
        # 逐層建立或取得資料夾
        for part in parts:
            current_folder_id = self._get_or_create_subfolder(part, current_folder_id)
        
        return current_folder_id
    
    def _get_or_create_subfolder(self, folder_name: str, parent_id: str) -> str:
        """
        取得或建立子資料夾
        
        Args:
            folder_name: 資料夾名稱
            parent_id: 父資料夾 ID
            
        Returns:
            資料夾 ID
        """
        # 查詢是否已存在
        query = (
            f"name='{folder_name}' and "
            f"'{parent_id}' in parents and "
            f"mimeType='{self.FOLDER_MIME_TYPE}' and "
            f"trashed=false"
        )
        
        try:
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = response.get('files', [])
            if files:
                return files[0]['id']
            
            # 不存在，建立新資料夾
            folder_metadata = {
                'name': folder_name,
                'mimeType': self.FOLDER_MIME_TYPE,
                'parents': [parent_id]
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            folder_id = folder['id']
            
            # 如果設定了 owner_email，自動共享給擁有者
            if self.owner_email:
                try:
                    self._share_folder_with_owner(folder_id)
                except Exception as e:
                    # 共享失敗不影響主流程，只記錄錯誤
                    print(f"⚠️ 無法共享資料夾給 {self.owner_email}: {e}")
            
            return folder_id
            
        except HttpError as e:
            raise Exception(f"建立資料夾失敗: {e}")
    
    def _share_folder_with_owner(self, folder_id: str):
        """
        共享資料夾給擁有者
        
        Args:
            folder_id: 資料夾 ID
        """
        permission = {
            'type': 'user',
            'role': 'writer',  # 編輯權限（可以上傳、修改、刪除）
            'emailAddress': self.owner_email
        }
        
        self.service.permissions().create(
            fileId=folder_id,
            body=permission,
            fields='id',
            sendNotificationEmail=False,  # 不發送通知郵件
            supportsAllDrives=True
        ).execute()
    
    def find_file(self,
                 filename: str,
                 folder_id: Optional[str] = None) -> Optional[Dict]:
        """
        查詢檔案
        
        Args:
            filename: 檔案名稱
            folder_id: 限定在特定資料夾（None 表示搜尋所有）
            
        Returns:
            檔案資訊或 None
        """
        query = f"name='{filename}' and trashed=false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        
        try:
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, size, createdTime, webViewLink)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = response.get('files', [])
            return files[0] if files else None
            
        except HttpError as e:
            print(f"查詢失敗: {e}")
            return None
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """
        下載檔案
        
        Args:
            file_id: Google Drive 檔案 ID
            local_path: 本地儲存路徑
            
        Returns:
            是否成功
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            with open(local_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        print(f"下載進度: {progress}%", end='\r')
            
            print("\n✅ 下載完成")
            return True
            
        except HttpError as e:
            print(f"❌ 下載失敗: {e}")
            return False
    
    def download_file_content_by_id(self, file_id: str) -> bytes:
        """
        下載檔案內容（返回 bytes）
        
        Args:
            file_id: Google Drive 檔案 ID
            
        Returns:
            檔案內容（bytes）
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            
            while not done:
                status, done = downloader.next_chunk()
            
            return file_content.getvalue()
            
        except HttpError as e:
            raise Exception(f"下載失敗: {e}")
    
    def list_files(self, folder_id: str) -> List[Dict]:
        """
        列出資料夾中的檔案（輔助方法，與 list_files_in_folder 相同）
        
        Args:
            folder_id: 資料夾 ID
            
        Returns:
            檔案列表 [{'id': ..., 'name': ..., 'size': ...}, ...]
        """
        return self.list_files_in_folder(folder_id)
    
    def delete_file(self, file_id: str) -> bool:
        """
        刪除檔案
        
        Args:
            file_id: Google Drive 檔案 ID
            
        Returns:
            是否成功
        """
        try:
            self.service.files().delete(
                fileId=file_id,
                supportsAllDrives=True
            ).execute()
            return True
        except HttpError as e:
            print(f"❌ 刪除失敗: {e}")
            return False
    
    def list_files_in_folder(self, folder_id: str) -> List[Dict]:
        """
        列出資料夾中的所有檔案
        
        Args:
            folder_id: 資料夾 ID
            
        Returns:
            檔案列表
        """
        query = f"'{folder_id}' in parents and trashed=false"
        
        try:
            results = []
            page_token = None
            
            while True:
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, size, createdTime, mimeType)',
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                
                results.extend(response.get('files', []))
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            return results
            
        except HttpError as e:
            print(f"❌ 列出檔案失敗: {e}")
            return []
    
    def get_storage_usage(self) -> Dict[str, any]:
        """
        取得儲存空間使用情況
        
        Returns:
            儲存空間資訊
        """
        try:
            about = self.service.about().get(fields='storageQuota').execute()
            quota = about.get('storageQuota', {})
            
            usage = int(quota.get('usage', 0))
            limit = int(quota.get('limit', 0))
            
            return {
                'used_mb': round(usage / (1024 * 1024), 2),
                'limit_mb': round(limit / (1024 * 1024), 2) if limit > 0 else None,
                'used_percent': round(usage / limit * 100, 2) if limit > 0 else None
            }
            
        except HttpError as e:
            print(f"❌ 取得儲存空間失敗: {e}")
            return {}
    
    def cleanup_old_files(self,
                         cutoff_date: date,
                         dry_run: bool = False) -> Dict[str, any]:
        """
        清理舊檔案
        
        Args:
            cutoff_date: 截止日期（刪除此日期之前的檔案）
            dry_run: 乾跑模式
            
        Returns:
            清理結果
        """
        results = {
            'scanned': 0,
            'to_delete': 0,
            'deleted': 0,
            'errors': 0,
            'files': []
        }
        
        # 列出根資料夾下的所有年份資料夾
        year_folders = self.list_files_in_folder(self.root_folder_id)
        
        for year_folder in year_folders:
            if year_folder['mimeType'] != self.FOLDER_MIME_TYPE:
                continue
            
            try:
                year = int(year_folder['name'])
            except ValueError:
                continue
            
            # 列出月份資料夾
            month_folders = self.list_files_in_folder(year_folder['id'])
            
            for month_folder in month_folders:
                if month_folder['mimeType'] != self.FOLDER_MIME_TYPE:
                    continue
                
                try:
                    month = int(month_folder['name'])
                    folder_date = date(year, month, 1)
                except ValueError:
                    continue
                
                # 檢查是否過期
                if folder_date >= cutoff_date:
                    continue
                
                # 列出檔案
                files = self.list_files_in_folder(month_folder['id'])
                results['scanned'] += len(files)
                
                for file in files:
                    results['to_delete'] += 1
                    
                    if not dry_run:
                        if self.delete_file(file['id']):
                            results['deleted'] += 1
                            results['files'].append({
                                'name': file['name'],
                                'date': f"{year}-{month:02d}",
                                'action': 'deleted'
                            })
                        else:
                            results['errors'] += 1
                    else:
                        results['files'].append({
                            'name': file['name'],
                            'date': f"{year}-{month:02d}",
                            'action': 'would_delete'
                        })
        
        return results

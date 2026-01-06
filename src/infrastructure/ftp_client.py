"""
CDR FTP 下載客戶端
實作真實的 FTP 連線邏輯，支援被動模式穿透防火牆
從 Iridium FTP 伺服器下載通訊詳細記錄
"""
from __future__ import annotations
from ftplib import FTP, error_perm
from typing import List, Optional, Tuple
from datetime import datetime
import io
import re
from ..config.settings import FTP_HOST, FTP_USER, FTP_PASS, FTP_PORT, FTP_TIMEOUT, FTP_PASSIVE_MODE


class CDRDownloadException(Exception):
    """CDR 下載異常"""
    pass


class CDRDownloader:
    """
    CDR FTP 下載器
    實作被動模式 FTP 連線，確保可穿透防火牆
    """
    
    def __init__(self, host: str = None, username: str = None, password: str = None, port: int = None):
        """
        初始化 CDR 下載器
        
        Args:
            host: FTP 主機位址（預設從 settings 讀取）
            username: FTP 使用者名稱（預設從 settings 讀取）
            password: FTP 密碼（預設從 settings 讀取）
            port: FTP 連接埠（預設從 settings 讀取）
        """
        self.host = host or FTP_HOST
        self.username = username or FTP_USER
        self.password = password or FTP_PASS
        self.port = port or FTP_PORT
        
        if not self.username or not self.password:
            raise ValueError(
                "FTP credentials not configured. "
                "Please set FTP_USER and FTP_PASS in .streamlit/secrets.toml"
            )
        
        self._ftp: Optional[FTP] = None


class FTPClient:
    """
    通用 FTP 客戶端（用於 CDR 檔案管理）
    提供簡化的介面給 CDRFileManager 使用
    """
    
    def __init__(self, 
                 host: str,
                 username: str, 
                 password: str,
                 port: int = 21,
                 passive_mode: bool = True):
        """
        初始化 FTP 客戶端
        
        Args:
            host: FTP 主機
            username: 使用者名稱
            password: 密碼
            port: 連接埠
            passive_mode: 是否使用被動模式
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.passive_mode = passive_mode
        self._ftp: Optional[FTP] = None
    
    def connect(self) -> None:
        """連接 FTP 伺服器"""
        try:
            self._ftp = FTP()
            self._ftp.encoding = 'utf-8'
            self._ftp.connect(self.host, self.port, timeout=FTP_TIMEOUT)
            self._ftp.login(self.username, self.password)
            self._ftp.set_pasv(self.passive_mode)
        except Exception as e:
            raise CDRDownloadException(f"FTP 連線失敗: {e}")
    
    def disconnect(self) -> None:
        """關閉連接"""
        if self._ftp:
            try:
                self._ftp.quit()
            except:
                try:
                    self._ftp.close()
                except:
                    pass
            finally:
                self._ftp = None
    
    def __enter__(self):
        """Context manager"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 退出"""
        self.disconnect()
    


    def upload_file(self, local_path: str, remote_path: str) -> None:
        """
        上傳檔案
        
        Args:
            local_path: 本地檔案路徑
            remote_path: 遠端儲存路徑
        """
        if not self._ftp:
            self.connect()
        
        try:
            with open(local_path, 'rb') as f:
                self._ftp.storbinary(f'STOR {remote_path}', f)
        except Exception as e:
            raise CDRDownloadException(f"上傳檔案失敗 {local_path}: {e}")
    
    def connect(self) -> None:
        """
        連線到 FTP 伺服器
        使用被動模式以確保穿透防火牆
        
        Raises:
            CDRDownloadException: 當連線失敗時
        """
        try:
            self._ftp = FTP()
            self._ftp.encoding = 'utf-8'
            
            # 連線到伺服器
            self._ftp.connect(self.host, self.port, timeout=FTP_TIMEOUT)
            
            # 登入
            self._ftp.login(self.username, self.password)
            
            # 設定被動模式（重要：穿透防火牆）
            self._ftp.set_pasv(FTP_PASSIVE_MODE)
            
            # 驗證連線
            welcome_msg = self._ftp.getwelcome()
            if not welcome_msg:
                raise CDRDownloadException("FTP connection established but no welcome message received")
                
        except error_perm as e:
            raise CDRDownloadException(f"FTP authentication failed: {str(e)}")
        except Exception as e:
            raise CDRDownloadException(f"Failed to connect to FTP server: {str(e)}")
    
    def disconnect(self) -> None:
        """關閉 FTP 連線"""
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                try:
                    self._ftp.close()
                except Exception:
                    pass
            finally:
                self._ftp = None
    
    def __enter__(self):
        """Context manager 進入"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 退出"""
        self.disconnect()
    
    def list_files(self, directory: str = '.', pattern: str = r'\.dat$') -> List[Tuple[str, datetime, int]]:
        """
        列出目錄中的檔案
        
        Args:
            directory: 目錄路徑
            pattern: 檔案名稱正則表達式模式
            
        Returns:
            List[Tuple[str, datetime, int]]: 檔案列表 (檔名, 修改時間, 大小)
            
        Raises:
            CDRDownloadException: 當列出檔案失敗時
        """
        if not self._ftp:
            raise CDRDownloadException("Not connected to FTP server")
        
        try:
            files = []
            pattern_re = re.compile(pattern)
            
            # 切換到指定目錄
            if directory != '.':
                self._ftp.cwd(directory)
            
            # 使用 MLSD 獲取詳細資訊（如果支援）
            try:
                for name, facts in self._ftp.mlsd():
                    if facts.get('type') == 'file' and pattern_re.search(name):
                        size = int(facts.get('size', 0))
                        
                        # 解析修改時間（YYYYMMDDHHMMSS 格式）
                        modify_time = facts.get('modify', '')
                        if modify_time:
                            try:
                                mod_dt = datetime.strptime(modify_time, '%Y%m%d%H%M%S')
                            except ValueError:
                                mod_dt = datetime.now()
                        else:
                            mod_dt = datetime.now()
                        
                        files.append((name, mod_dt, size))
                        
            except error_perm:
                # MLSD 不支援，使用 NLST 和 SIZE/MDTM
                file_list = self._ftp.nlst()
                
                for filename in file_list:
                    if pattern_re.search(filename):
                        try:
                            # 取得檔案大小
                            size = self._ftp.size(filename) or 0
                            
                            # 取得修改時間
                            try:
                                mdtm_response = self._ftp.sendcmd(f'MDTM {filename}')
                                timestamp = mdtm_response.split()[1]
                                mod_dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
                            except Exception:
                                mod_dt = datetime.now()
                            
                            files.append((filename, mod_dt, size))
                        except Exception:
                            # 跳過無法存取的檔案
                            continue
            
            return files
            
        except Exception as e:
            raise CDRDownloadException(f"Failed to list files: {str(e)}")
    
    def download_file(self, filename: str) -> bytes:
        """
        下載檔案並返回 bytes
        
        Args:
            filename: 檔案名稱
            
        Returns:
            bytes: 檔案內容
            
        Raises:
            CDRDownloadException: 當下載失敗時
        """
        if not self._ftp:
            raise CDRDownloadException("Not connected to FTP server")
        
        try:
            buffer = io.BytesIO()
            self._ftp.retrbinary(f'RETR {filename}', buffer.write)
            return buffer.getvalue()
        except error_perm as e:
            raise CDRDownloadException(f"Permission denied for file {filename}: {str(e)}")
        except Exception as e:
            raise CDRDownloadException(f"Failed to download file {filename}: {str(e)}")
    
    def get_latest_cdr(self, directory: str = '.') -> Tuple[str, bytes]:
        """
        下載最新的 CDR 檔案
        
        Args:
            directory: CDR 檔案所在目錄
            
        Returns:
            Tuple[str, bytes]: (檔案名稱, 檔案內容)
            
        Raises:
            CDRDownloadException: 當下載失敗或找不到檔案時
        """
        try:
            # 列出所有 .dat 檔案
            files = self.list_files(directory, pattern=r'\.dat$')
            
            if not files:
                raise CDRDownloadException(f"No CDR (.dat) files found in directory: {directory}")
            
            # 按修改時間排序，取最新的
            files.sort(key=lambda x: x[1], reverse=True)
            latest_file = files[0][0]
            latest_time = files[0][1]
            latest_size = files[0][2]
            
            print(f"Found latest CDR file: {latest_file}")
            print(f"  Modified: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Size: {latest_size} bytes")
            
            # 下載檔案
            content = self.download_file(latest_file)
            
            return latest_file, content
            
        except CDRDownloadException:
            raise
        except Exception as e:
            raise CDRDownloadException(f"Failed to get latest CDR: {str(e)}")
    
    def check_connection(self) -> bool:
        """
        檢查 FTP 連線狀態
        
        Returns:
            bool: 連線是否正常
        """
        try:
            with CDRDownloader(self.host, self.username, self.password, self.port) as downloader:
                # 嘗試取得當前目錄
                downloader._ftp.pwd()
            return True
        except Exception:
            return False

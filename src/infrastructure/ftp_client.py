"""
FTP Client
FTP 客戶端 - 處理 CDR 檔案下載
"""

from typing import List, Optional, Callable
import ftplib
import logging
from pathlib import Path
from datetime import datetime

from src.utils.exceptions import FTPConnectionError, InfrastructureError
from src.utils.types import FTPConfig


logger = logging.getLogger(__name__)


class FTPClient:
    """
    FTP 客戶端
    
    負責與 Iridium CDR FTP 伺服器通訊。
    
    職責：
    - 管理 FTP 連線
    - 下載檔案
    - 列出目錄
    - 處理錯誤和重試
    """
    
    def __init__(self, config: FTPConfig):
        """
        初始化 FTP 客戶端
        
        Args:
            config: FTP 設定
        """
        self._config = config
        self._ftp: Optional[ftplib.FTP] = None
        self._is_connected: bool = False
        
        logger.info(f"FTPClient initialized for host: {config['host']}")
    
    def connect(self) -> None:
        """
        建立 FTP 連線
        
        Raises:
            FTPConnectionError: 連線失敗
        """
        try:
            logger.info(f"Connecting to FTP server: {self._config['host']}")
            
            self._ftp = ftplib.FTP()
            self._ftp.connect(
                self._config['host'],
                self._config.get('port', 21)
            )
            
            self._ftp.login(
                self._config['username'],
                self._config['password']
            )
            
            if self._config.get('passive_mode', True):
                self._ftp.set_pasv(True)
            
            self._is_connected = True
            logger.info("✅ Connected to FTP server successfully")
            
        except ftplib.all_errors as e:
            logger.error(f"❌ Failed to connect to FTP: {e}")
            raise FTPConnectionError(
                f"無法連線到 FTP 伺服器: {str(e)}",
                {'host': self._config['host']}
            )
    
    def disconnect(self) -> None:
        """關閉 FTP 連線"""
        if self._ftp:
            try:
                self._ftp.quit()
            except:
                self._ftp.close()
            
            self._ftp = None
            self._is_connected = False
            logger.info("Disconnected from FTP server")
    
    def ensure_connected(self) -> None:
        """確保已連線"""
        if not self._is_connected or not self._ftp:
            self.connect()
    
    def is_connected(self) -> bool:
        """檢查連線狀態"""
        return self._is_connected and self._ftp is not None
    
    def list_files(self, path: str = '') -> List[str]:
        """
        列出目錄中的檔案
        
        Args:
            path: 目錄路徑
            
        Returns:
            檔案名稱列表
        """
        self.ensure_connected()
        
        try:
            if path:
                self._ftp.cwd(path)
            
            files = self._ftp.nlst()
            logger.debug(f"Listed {len(files)} files in {path or 'root'}")
            return files
            
        except ftplib.all_errors as e:
            raise FTPConnectionError(
                f"無法列出檔案: {str(e)}",
                {'path': path}
            )
    
    def download_file(
        self,
        remote_path: str,
        local_path: Path,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> None:
        """
        下載檔案
        
        Args:
            remote_path: 遠端檔案路徑
            local_path: 本地儲存路徑
            progress_callback: 進度回調函式
        """
        self.ensure_connected()
        
        try:
            logger.info(f"Downloading: {remote_path} -> {local_path}")
            
            # 確保本地目錄存在
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 下載檔案
            with open(local_path, 'wb') as f:
                def callback(data):
                    f.write(data)
                    if progress_callback:
                        progress_callback(len(data))
                
                self._ftp.retrbinary(f'RETR {remote_path}', callback)
            
            logger.info(f"✅ Downloaded: {remote_path}")
            
        except ftplib.all_errors as e:
            logger.error(f"❌ Failed to download {remote_path}: {e}")
            raise FTPConnectionError(
                f"無法下載檔案: {str(e)}",
                {'remote_path': remote_path, 'local_path': str(local_path)}
            )
    
    def download_multiple(
        self,
        files: List[str],
        local_dir: Path,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[Path]:
        """
        批次下載檔案
        
        Args:
            files: 遠端檔案列表
            local_dir: 本地目錄
            progress_callback: 進度回調 (filename, current, total)
            
        Returns:
            下載的本地檔案路徑列表
        """
        downloaded = []
        total = len(files)
        
        for idx, remote_file in enumerate(files, 1):
            local_file = local_dir / Path(remote_file).name
            
            if progress_callback:
                progress_callback(remote_file, idx, total)
            
            self.download_file(remote_file, local_file)
            downloaded.append(local_file)
        
        return downloaded
    
    def file_exists(self, path: str) -> bool:
        """
        檢查檔案是否存在
        
        Args:
            path: 檔案路徑
            
        Returns:
            是否存在
        """
        self.ensure_connected()
        
        try:
            self._ftp.size(path)
            return True
        except:
            return False
    
    def get_file_size(self, path: str) -> int:
        """
        取得檔案大小
        
        Args:
            path: 檔案路徑
            
        Returns:
            檔案大小（bytes）
        """
        self.ensure_connected()
        
        try:
            return self._ftp.size(path)
        except ftplib.all_errors as e:
            raise FTPConnectionError(
                f"無法取得檔案大小: {str(e)}",
                {'path': path}
            )
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
        return False

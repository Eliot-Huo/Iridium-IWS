"""
資料存取層 - 記憶體儲存庫
"""
from __future__ import annotations
from typing import Dict, Optional, List
from ..models.models import ServiceRequest


class InMemoryRepository:
    """記憶體儲存庫實作"""
    
    def __init__(self):
        """初始化儲存庫"""
        self._storage: Dict[str, ServiceRequest] = {}
    
    def save_request(self, request: ServiceRequest) -> None:
        """
        儲存服務請求
        
        Args:
            request: 服務請求物件
        """
        self._storage[request.request_id] = request
    
    def get_request(self, request_id: str) -> Optional[ServiceRequest]:
        """
        取得服務請求
        
        Args:
            request_id: 請求 ID
            
        Returns:
            ServiceRequest: 服務請求物件，若不存在則回傳 None
        """
        return self._storage.get(request_id)
    
    def list_all_requests(self) -> List[ServiceRequest]:
        """
        列出所有服務請求
        
        Returns:
            List[ServiceRequest]: 所有服務請求列表
        """
        return list(self._storage.values())
    
    def get_requests_by_imei(self, imei: str) -> List[ServiceRequest]:
        """
        依 IMEI 取得服務請求
        
        Args:
            imei: IMEI 號碼
            
        Returns:
            List[ServiceRequest]: 符合條件的服務請求列表
        """
        return [req for req in self._storage.values() if req.imei == imei]
    
    def clear(self) -> None:
        """清空儲存庫（測試用）"""
        self._storage.clear()
    
    def count(self) -> int:
        """取得請求總數"""
        return len(self._storage)

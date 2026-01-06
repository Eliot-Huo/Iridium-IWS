"""
Base Repository - Abstract Base Class
Repository 抽象基類 - 定義資料存取層的標準介面
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any
from datetime import datetime

from src.utils.exceptions import (
    RepositoryError,
    RecordNotFoundError,
    DuplicateRecordError
)

# 泛型型別變數
T = TypeVar('T')  # Entity 型別
ID = TypeVar('ID')  # ID 型別


class BaseRepository(ABC, Generic[T, ID]):
    """
    Repository 抽象基類
    
    所有 Repository 必須繼承此類別並實作抽象方法。
    提供標準的 CRUD 操作介面。
    
    Type Parameters:
        T: Entity 型別
        ID: ID 型別 (通常是 str 或 int)
    """
    
    def __init__(self):
        """初始化 Repository"""
        self._cache: Dict[ID, T] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl: int = 300  # 快取存活時間（秒）
    
    # ========== 抽象方法 (必須實作) ==========
    
    @abstractmethod
    def find_by_id(self, id: ID) -> Optional[T]:
        """
        根據 ID 查詢單一記錄
        
        Args:
            id: 實體 ID
            
        Returns:
            找到的實體，如果不存在則返回 None
            
        Raises:
            RepositoryError: 查詢失敗時拋出
        """
        pass
    
    @abstractmethod
    def find_all(self, **filters) -> List[T]:
        """
        查詢所有記錄
        
        Args:
            **filters: 篩選條件
            
        Returns:
            實體列表
            
        Raises:
            RepositoryError: 查詢失敗時拋出
        """
        pass
    
    @abstractmethod
    def save(self, entity: T) -> T:
        """
        儲存實體（新增或更新）
        
        Args:
            entity: 要儲存的實體
            
        Returns:
            儲存後的實體
            
        Raises:
            RepositoryError: 儲存失敗時拋出
            DuplicateRecordError: 記錄重複時拋出
        """
        pass
    
    @abstractmethod
    def delete(self, id: ID) -> bool:
        """
        刪除記錄
        
        Args:
            id: 實體 ID
            
        Returns:
            是否成功刪除
            
        Raises:
            RepositoryError: 刪除失敗時拋出
            RecordNotFoundError: 記錄不存在時拋出
        """
        pass
    
    @abstractmethod
    def exists(self, id: ID) -> bool:
        """
        檢查記錄是否存在
        
        Args:
            id: 實體 ID
            
        Returns:
            是否存在
        """
        pass
    
    # ========== 輔助方法 (選擇性實作) ==========
    
    def find_by_ids(self, ids: List[ID]) -> List[T]:
        """
        根據多個 ID 批次查詢
        
        Args:
            ids: ID 列表
            
        Returns:
            實體列表
        """
        results = []
        for id in ids:
            entity = self.find_by_id(id)
            if entity:
                results.append(entity)
        return results
    
    def count(self, **filters) -> int:
        """
        計算符合條件的記錄數量
        
        Args:
            **filters: 篩選條件
            
        Returns:
            記錄數量
        """
        return len(self.find_all(**filters))
    
    def paginate(
        self, 
        page: int = 1, 
        page_size: int = 20, 
        **filters
    ) -> Dict[str, Any]:
        """
        分頁查詢
        
        Args:
            page: 頁碼（從 1 開始）
            page_size: 每頁數量
            **filters: 篩選條件
            
        Returns:
            包含分頁資訊的字典
        """
        all_items = self.find_all(**filters)
        total_count = len(all_items)
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        items = all_items[start_idx:end_idx]
        
        return {
            'items': items,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'has_next': end_idx < total_count,
            'has_previous': page > 1
        }
    
    # ========== 快取管理 ==========
    
    def _is_cache_valid(self) -> bool:
        """檢查快取是否有效"""
        if not self._cache_timestamp:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_ttl
    
    def _get_from_cache(self, id: ID) -> Optional[T]:
        """從快取取得實體"""
        if self._is_cache_valid() and id in self._cache:
            return self._cache[id]
        return None
    
    def _add_to_cache(self, id: ID, entity: T) -> None:
        """加入快取"""
        self._cache[id] = entity
        if not self._cache_timestamp:
            self._cache_timestamp = datetime.now()
    
    def _invalidate_cache(self) -> None:
        """清除快取"""
        self._cache.clear()
        self._cache_timestamp = None
    
    # ========== 驗證方法 ==========
    
    def _validate_entity(self, entity: T) -> None:
        """
        驗證實體
        
        Args:
            entity: 要驗證的實體
            
        Raises:
            ValidationError: 驗證失敗時拋出
        """
        # 子類別可以覆寫此方法來加入自訂驗證邏輯
        pass
    
    def _validate_id(self, id: ID) -> None:
        """
        驗證 ID
        
        Args:
            id: 要驗證的 ID
            
        Raises:
            ValidationError: 驗證失敗時拋出
        """
        if not id:
            from src.utils.exceptions import ValidationError
            raise ValidationError("ID 不能為空")


class ReadOnlyRepository(BaseRepository[T, ID]):
    """
    唯讀 Repository
    
    禁止寫入操作的 Repository，適用於唯讀資料源。
    """
    
    def save(self, entity: T) -> T:
        """禁止儲存操作"""
        raise NotImplementedError("此 Repository 為唯讀模式")
    
    def delete(self, id: ID) -> bool:
        """禁止刪除操作"""
        raise NotImplementedError("此 Repository 為唯讀模式")

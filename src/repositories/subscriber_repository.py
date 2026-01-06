"""
Subscriber Repository
訂戶 Repository - 處理訂戶資料存取
"""

from typing import Optional, List, Dict, Any
import logging

from src.repositories.base_repository import BaseRepository
from src.domain.subscriber import Subscriber
from src.infrastructure.iws_client import IWSClient
from src.utils.types import IMEI, SubscriberStatus
from src.utils.exceptions import (
    RecordNotFoundError,
    RepositoryError
)


logger = logging.getLogger(__name__)


class SubscriberRepository(BaseRepository[Subscriber, IMEI]):
    """
    訂戶 Repository
    
    職責：
    - 透過 IWS API 查詢訂戶
    - 將 API 回應轉換為 Domain Model
    - 管理快取
    
    不包含：
    - 業務邏輯
    - 狀態轉換邏輯
    """
    
    def __init__(self, iws_client: IWSClient):
        """
        初始化 Repository
        
        Args:
            iws_client: IWS API 客戶端
        """
        super().__init__()
        self._client = iws_client
        logger.info("SubscriberRepository initialized")
    
    def find_by_id(self, imei: IMEI) -> Optional[Subscriber]:
        """
        根據 IMEI 查詢訂戶
        
        Args:
            imei: IMEI 號碼
            
        Returns:
            訂戶實體，如果不存在則返回 None
            
        Raises:
            RepositoryError: 查詢失敗
        """
        try:
            logger.debug(f"Finding subscriber by IMEI: {imei}")
            
            # 檢查快取
            cached = self._get_from_cache(imei)
            if cached:
                logger.debug(f"Cache hit for IMEI: {imei}")
                return cached
            
            # 呼叫 API
            response = self._client.search_subscriber(imei)
            
            # 檢查是否找到
            if not response or 'account' not in response:
                logger.debug(f"Subscriber not found: {imei}")
                return None
            
            # 轉換為 Domain Model
            subscriber = self._map_to_domain(response['account'])
            
            # 加入快取
            self._add_to_cache(imei, subscriber)
            
            logger.debug(f"Found subscriber: {imei}")
            return subscriber
            
        except Exception as e:
            logger.error(f"Failed to find subscriber {imei}: {e}")
            raise RepositoryError(
                f"查詢訂戶失敗: {str(e)}",
                {'imei': imei}
            )
    
    def find_all(self, **filters) -> List[Subscriber]:
        """
        查詢所有訂戶（不支援）
        
        Note: IWS API 不支援列出所有訂戶
        """
        raise NotImplementedError("IWS API 不支援列出所有訂戶")
    
    def save(self, subscriber: Subscriber) -> Subscriber:
        """
        儲存訂戶（更新狀態）
        
        Args:
            subscriber: 訂戶實體
            
        Returns:
            更新後的訂戶
            
        Raises:
            RepositoryError: 儲存失敗
        """
        try:
            logger.info(f"Saving subscriber: {subscriber.imei}")
            
            # 驗證
            self._validate_entity(subscriber)
            
            # 根據狀態決定要呼叫哪個 API
            if subscriber.is_active():
                self._client.activate_subscriber(
                    subscriber.imei,
                    subscriber.plan_id
                )
            elif subscriber.is_suspended():
                self._client.suspend_subscriber(subscriber.imei)
            elif subscriber.is_deactivated():
                self._client.deactivate_subscriber(subscriber.imei)
            
            # 清除快取（強制重新查詢）
            self._invalidate_cache()
            
            logger.info(f"✅ Saved subscriber: {subscriber.imei}")
            return subscriber
            
        except Exception as e:
            logger.error(f"Failed to save subscriber {subscriber.imei}: {e}")
            raise RepositoryError(
                f"儲存訂戶失敗: {str(e)}",
                {'imei': subscriber.imei}
            )
    
    def delete(self, imei: IMEI) -> bool:
        """
        刪除訂戶（註銷）
        
        Args:
            imei: IMEI 號碼
            
        Returns:
            是否成功
        """
        try:
            logger.info(f"Deactivating subscriber: {imei}")
            
            self._client.deactivate_subscriber(imei)
            self._invalidate_cache()
            
            logger.info(f"✅ Deactivated subscriber: {imei}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deactivate subscriber {imei}: {e}")
            raise RepositoryError(
                f"註銷訂戶失敗: {str(e)}",
                {'imei': imei}
            )
    
    def exists(self, imei: IMEI) -> bool:
        """
        檢查訂戶是否存在
        
        Args:
            imei: IMEI 號碼
            
        Returns:
            是否存在
        """
        return self.find_by_id(imei) is not None
    
    # ========== 特殊查詢 ==========
    
    def change_plan(
        self,
        imei: IMEI,
        new_plan_id: str
    ) -> Subscriber:
        """
        變更訂戶方案
        
        Args:
            imei: IMEI 號碼
            new_plan_id: 新方案 ID
            
        Returns:
            更新後的訂戶
        """
        try:
            logger.info(f"Changing plan for {imei} to {new_plan_id}")
            
            self._client.change_plan(imei, new_plan_id)
            self._invalidate_cache()
            
            # 重新查詢
            subscriber = self.find_by_id(imei)
            if not subscriber:
                raise RecordNotFoundError(f"找不到訂戶: {imei}")
            
            logger.info(f"✅ Changed plan for {imei}")
            return subscriber
            
        except Exception as e:
            logger.error(f"Failed to change plan for {imei}: {e}")
            raise RepositoryError(
                f"變更方案失敗: {str(e)}",
                {'imei': imei, 'new_plan_id': new_plan_id}
            )
    
    # ========== 內部方法 ==========
    
    def _map_to_domain(self, api_data: Dict[str, Any]) -> Subscriber:
        """
        將 API 回應轉換為 Domain Model
        
        Args:
            api_data: API 回應資料
            
        Returns:
            Subscriber 實體
        """
        return Subscriber(
            imei=api_data.get('imei', ''),
            account_number=api_data.get('accountNumber', ''),
            status=SubscriberStatus(api_data.get('status', 'PENDING')),
            plan_id=api_data.get('planId', ''),
            activation_date=api_data.get('activationDate'),
            deactivation_date=api_data.get('deactivationDate'),
            suspended_date=api_data.get('suspendedDate'),
            customer_id=api_data.get('customerId'),
            customer_name=api_data.get('customerName'),
            notes=api_data.get('notes')
        )
    
    def _validate_entity(self, subscriber: Subscriber) -> None:
        """
        驗證訂戶實體
        
        Args:
            subscriber: 訂戶實體
        """
        # Domain Model 本身已經有驗證邏輯
        subscriber.validate()

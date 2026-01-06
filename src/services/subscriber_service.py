"""
Subscriber Service
訂戶服務 - 處理訂戶相關業務邏輯
"""

from typing import Optional, List
import logging
from datetime import datetime

from src.repositories.subscriber_repository import SubscriberRepository
from src.domain.subscriber import Subscriber
from src.utils.types import IMEI, PlanID, SubscriberStatus
from src.utils.exceptions import (
    SubscriberNotFoundError,
    InvalidSubscriberStateError,
    PlanChangeError,
    ServiceError
)


logger = logging.getLogger(__name__)


class SubscriberService:
    """
    訂戶服務
    
    職責：
    - 協調訂戶相關業務流程
    - 執行業務規則
    - 管理訂戶生命週期
    
    不包含：
    - API 呼叫細節（由 Repository 處理）
    - UI 邏輯（由 UI 層處理）
    """
    
    def __init__(self, repository: SubscriberRepository):
        """
        初始化服務
        
        Args:
            repository: 訂戶 Repository
        """
        self._repo = repository
        logger.info("SubscriberService initialized")
    
    # ========== 查詢操作 ==========
    
    def get_subscriber(self, imei: IMEI) -> Subscriber:
        """
        取得訂戶
        
        Args:
            imei: IMEI 號碼
            
        Returns:
            訂戶實體
            
        Raises:
            SubscriberNotFoundError: 找不到訂戶
        """
        logger.debug(f"Getting subscriber: {imei}")
        
        subscriber = self._repo.find_by_id(imei)
        if not subscriber:
            raise SubscriberNotFoundError(
                f"找不到訂戶: {imei}",
                {'imei': imei}
            )
        
        return subscriber
    
    def subscriber_exists(self, imei: IMEI) -> bool:
        """
        檢查訂戶是否存在
        
        Args:
            imei: IMEI 號碼
            
        Returns:
            是否存在
        """
        return self._repo.exists(imei)
    
    # ========== 啟用操作 ==========
    
    def activate_subscriber(
        self,
        imei: IMEI,
        plan_id: PlanID,
        reason: Optional[str] = None
    ) -> Subscriber:
        """
        啟用訂戶
        
        業務流程：
        1. 查詢訂戶
        2. 檢查是否可啟用
        3. 執行啟用
        4. 記錄操作
        5. 儲存變更
        
        Args:
            imei: IMEI 號碼
            plan_id: 方案 ID
            reason: 啟用原因
            
        Returns:
            啟用後的訂戶
            
        Raises:
            SubscriberNotFoundError: 找不到訂戶
            InvalidSubscriberStateError: 訂戶狀態不允許啟用
        """
        try:
            logger.info(f"Activating subscriber: {imei}")
            
            # 1. 查詢訂戶
            subscriber = self.get_subscriber(imei)
            
            # 2. 業務規則檢查
            if not subscriber.can_activate():
                raise InvalidSubscriberStateError(
                    f"訂戶狀態 {subscriber.status.value} 無法啟用",
                    {
                        'imei': imei,
                        'current_status': subscriber.status.value
                    }
                )
            
            # 3. 執行業務邏輯
            subscriber.plan_id = plan_id
            subscriber.activate()
            
            # 4. 儲存
            subscriber = self._repo.save(subscriber)
            
            logger.info(f"✅ Activated subscriber: {imei}")
            return subscriber
            
        except (SubscriberNotFoundError, InvalidSubscriberStateError):
            raise
        except Exception as e:
            logger.error(f"Failed to activate subscriber {imei}: {e}")
            raise ServiceError(
                f"啟用訂戶失敗: {str(e)}",
                {'imei': imei}
            )
    
    # ========== 暫停操作 ==========
    
    def suspend_subscriber(
        self,
        imei: IMEI,
        reason: Optional[str] = None
    ) -> Subscriber:
        """
        暫停訂戶
        
        Args:
            imei: IMEI 號碼
            reason: 暫停原因
            
        Returns:
            暫停後的訂戶
            
        Raises:
            SubscriberNotFoundError: 找不到訂戶
            InvalidSubscriberStateError: 訂戶狀態不允許暫停
        """
        try:
            logger.info(f"Suspending subscriber: {imei}")
            
            # 查詢訂戶
            subscriber = self.get_subscriber(imei)
            
            # 業務規則檢查
            if not subscriber.can_suspend():
                raise InvalidSubscriberStateError(
                    f"訂戶狀態 {subscriber.status.value} 無法暫停",
                    {
                        'imei': imei,
                        'current_status': subscriber.status.value
                    }
                )
            
            # 執行業務邏輯
            subscriber.suspend(reason)
            
            # 儲存
            subscriber = self._repo.save(subscriber)
            
            logger.info(f"✅ Suspended subscriber: {imei}")
            return subscriber
            
        except (SubscriberNotFoundError, InvalidSubscriberStateError):
            raise
        except Exception as e:
            logger.error(f"Failed to suspend subscriber {imei}: {e}")
            raise ServiceError(
                f"暫停訂戶失敗: {str(e)}",
                {'imei': imei}
            )
    
    # ========== 註銷操作 ==========
    
    def deactivate_subscriber(
        self,
        imei: IMEI,
        reason: Optional[str] = None
    ) -> Subscriber:
        """
        註銷訂戶
        
        Args:
            imei: IMEI 號碼
            reason: 註銷原因
            
        Returns:
            註銷後的訂戶
            
        Raises:
            SubscriberNotFoundError: 找不到訂戶
            InvalidSubscriberStateError: 訂戶狀態不允許註銷
        """
        try:
            logger.info(f"Deactivating subscriber: {imei}")
            
            # 查詢訂戶
            subscriber = self.get_subscriber(imei)
            
            # 業務規則檢查
            if not subscriber.can_deactivate():
                raise InvalidSubscriberStateError(
                    f"訂戶狀態 {subscriber.status.value} 無法註銷",
                    {
                        'imei': imei,
                        'current_status': subscriber.status.value
                    }
                )
            
            # 執行業務邏輯
            subscriber.deactivate(reason)
            
            # 儲存
            subscriber = self._repo.save(subscriber)
            
            logger.info(f"✅ Deactivated subscriber: {imei}")
            return subscriber
            
        except (SubscriberNotFoundError, InvalidSubscriberStateError):
            raise
        except Exception as e:
            logger.error(f"Failed to deactivate subscriber {imei}: {e}")
            raise ServiceError(
                f"註銷訂戶失敗: {str(e)}",
                {'imei': imei}
            )
    
    # ========== 方案變更 ==========
    
    def change_subscriber_plan(
        self,
        imei: IMEI,
        new_plan_id: PlanID,
        reason: Optional[str] = None
    ) -> Subscriber:
        """
        變更訂戶方案
        
        Args:
            imei: IMEI 號碼
            new_plan_id: 新方案 ID
            reason: 變更原因
            
        Returns:
            變更後的訂戶
            
        Raises:
            SubscriberNotFoundError: 找不到訂戶
            PlanChangeError: 方案變更失敗
        """
        try:
            logger.info(f"Changing plan for {imei} to {new_plan_id}")
            
            # 查詢訂戶
            subscriber = self.get_subscriber(imei)
            
            # 業務規則檢查
            if not subscriber.can_change_plan():
                raise PlanChangeError(
                    f"訂戶狀態 {subscriber.status.value} 無法變更方案",
                    {
                        'imei': imei,
                        'current_status': subscriber.status.value
                    }
                )
            
            # 檢查是否為相同方案
            if subscriber.plan_id == new_plan_id:
                raise PlanChangeError(
                    f"訂戶已使用方案 {new_plan_id}",
                    {
                        'imei': imei,
                        'current_plan': subscriber.plan_id
                    }
                )
            
            # 執行業務邏輯
            subscriber.change_plan(new_plan_id, reason)
            
            # 透過 Repository 的特殊方法變更方案
            subscriber = self._repo.change_plan(imei, new_plan_id)
            
            logger.info(f"✅ Changed plan for {imei}")
            return subscriber
            
        except (SubscriberNotFoundError, PlanChangeError):
            raise
        except Exception as e:
            logger.error(f"Failed to change plan for {imei}: {e}")
            raise ServiceError(
                f"變更方案失敗: {str(e)}",
                {'imei': imei, 'new_plan_id': new_plan_id}
            )
    
    # ========== 批次操作 ==========
    
    def activate_multiple_subscribers(
        self,
        imeis: List[IMEI],
        plan_id: PlanID,
        reason: Optional[str] = None
    ) -> List[Subscriber]:
        """
        批次啟用訂戶
        
        Args:
            imeis: IMEI 列表
            plan_id: 方案 ID
            reason: 啟用原因
            
        Returns:
            啟用後的訂戶列表
        """
        logger.info(f"Activating {len(imeis)} subscribers")
        
        results = []
        for imei in imeis:
            try:
                subscriber = self.activate_subscriber(imei, plan_id, reason)
                results.append(subscriber)
            except Exception as e:
                logger.warning(f"Failed to activate {imei}: {e}")
                # 繼續處理下一個
        
        logger.info(f"✅ Activated {len(results)}/{len(imeis)} subscribers")
        return results

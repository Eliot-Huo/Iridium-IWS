"""
DSG Service
DSG 服務 - 處理 DSG 相關業務邏輯
"""

from typing import List, Optional, Dict, Any
import logging

from src.repositories.dsg_repository import DSGRepository
from src.domain.dsg_group import DSGGroup
from src.utils.types import GroupID, IMEI, TrackerID
from src.utils.exceptions import (
    RecordNotFoundError,
    DSGSetupError,
    ValidationError,
    ServiceError
)


logger = logging.getLogger(__name__)


class DSGService:
    """
    DSG 服務
    
    職責：
    - 協調 DSG 相關業務流程
    - 管理 DSG 群組生命週期
    - 處理 Tracker 設定
    
    不包含：
    - API 呼叫細節
    - UI 邏輯
    """
    
    def __init__(self, repository: DSGRepository):
        """
        初始化服務
        
        Args:
            repository: DSG Repository
        """
        self._repo = repository
        logger.info("DSGService initialized")
    
    # ========== 查詢操作 ==========
    
    def get_group(self, group_id: GroupID) -> DSGGroup:
        """
        取得 DSG 群組
        
        Args:
            group_id: 群組 ID
            
        Returns:
            DSG 群組
            
        Raises:
            RecordNotFoundError: 找不到群組
        """
        logger.debug(f"Getting DSG group: {group_id}")
        
        group = self._repo.find_by_id(group_id)
        if not group:
            raise RecordNotFoundError(
                f"找不到 DSG 群組: {group_id}",
                {'group_id': group_id}
            )
        
        return group
    
    def get_all_groups(
        self,
        status: str = 'ACTIVE'
    ) -> List[DSGGroup]:
        """
        取得所有 DSG 群組
        
        Args:
            status: 狀態篩選
            
        Returns:
            DSG 群組列表
        """
        logger.debug("Getting all DSG groups")
        return self._repo.find_all(status=status)
    
    def find_group_by_name(self, group_name: str) -> Optional[DSGGroup]:
        """
        根據名稱查詢群組
        
        Args:
            group_name: 群組名稱
            
        Returns:
            DSG 群組，如果不存在則返回 None
        """
        return self._repo.find_by_name(group_name)
    
    # ========== 群組管理 ==========
    
    def create_group(
        self,
        group_name: str,
        description: str = "",
        initial_imeis: Optional[List[IMEI]] = None
    ) -> DSGGroup:
        """
        建立 DSG 群組
        
        業務流程：
        1. 驗證群組名稱唯一性
        2. 建立群組
        3. 加入初始成員（如果有）
        4. 驗證最小成員數
        
        Args:
            group_name: 群組名稱
            description: 描述
            initial_imeis: 初始成員 IMEI 列表
            
        Returns:
            建立的 DSG 群組
            
        Raises:
            ValidationError: 驗證失敗
            DSGSetupError: 建立失敗
        """
        try:
            logger.info(f"Creating DSG group: {group_name}")
            
            # 1. 檢查名稱唯一性
            existing = self.find_group_by_name(group_name)
            if existing:
                raise ValidationError(
                    f"群組名稱已存在: {group_name}",
                    {'group_name': group_name}
                )
            
            # 2. 建立群組物件
            group = DSGGroup(
                group_id='0',  # 建立時 ID 為 0
                group_name=group_name,
                description=description
            )
            
            # 3. 儲存群組
            group = self._repo.save(group)
            
            # 4. 加入初始成員
            if initial_imeis:
                self.add_members_to_group(group.group_id, initial_imeis)
                # 重新查詢以取得更新的成員列表
                group = self.get_group(group.group_id)
            
            logger.info(f"✅ Created DSG group: {group.group_id}")
            return group
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create DSG group {group_name}: {e}")
            raise DSGSetupError(
                f"建立 DSG 群組失敗: {str(e)}",
                {'group_name': group_name}
            )
    
    # ========== 成員管理 ==========
    
    def add_members_to_group(
        self,
        group_id: GroupID,
        imeis: List[IMEI]
    ) -> DSGGroup:
        """
        加入成員到群組
        
        Args:
            group_id: 群組 ID
            imeis: IMEI 列表
            
        Returns:
            更新後的群組
            
        Raises:
            RecordNotFoundError: 找不到群組
            ValidationError: 驗證失敗
        """
        try:
            logger.info(f"Adding {len(imeis)} members to group {group_id}")
            
            # 1. 取得群組
            group = self.get_group(group_id)
            
            # 2. 驗證 IMEI
            valid_imeis = []
            for imei in imeis:
                if len(imei) == 15 and imei.isdigit():
                    valid_imeis.append(imei)
                else:
                    logger.warning(f"Invalid IMEI: {imei}")
            
            if not valid_imeis:
                raise ValidationError(
                    "沒有有效的 IMEI",
                    {'imeis': imeis}
                )
            
            # 3. 過濾已存在的成員
            current_members = self._repo.get_members(group_id)
            new_imeis = [imei for imei in valid_imeis if imei not in current_members]
            
            if not new_imeis:
                logger.info(f"All IMEIs already in group {group_id}")
                return group
            
            # 4. 加入成員
            self._repo.add_members(group_id, new_imeis)
            
            # 5. 重新查詢
            group = self.get_group(group_id)
            
            logger.info(f"✅ Added {len(new_imeis)} members to group {group_id}")
            return group
            
        except (RecordNotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to add members to group {group_id}: {e}")
            raise ServiceError(
                f"加入成員失敗: {str(e)}",
                {'group_id': group_id}
            )
    
    def remove_members_from_group(
        self,
        group_id: GroupID,
        imeis: List[IMEI]
    ) -> DSGGroup:
        """
        從群組移除成員
        
        Args:
            group_id: 群組 ID
            imeis: IMEI 列表
            
        Returns:
            更新後的群組
            
        Raises:
            RecordNotFoundError: 找不到群組
            ValidationError: 驗證失敗
        """
        try:
            logger.info(f"Removing {len(imeis)} members from group {group_id}")
            
            # 1. 取得群組
            group = self.get_group(group_id)
            
            # 2. 檢查成員是否存在
            current_members = self._repo.get_members(group_id)
            existing_imeis = [imei for imei in imeis if imei in current_members]
            
            if not existing_imeis:
                logger.info(f"No matching IMEIs in group {group_id}")
                return group
            
            # 3. 檢查最小成員數
            remaining_count = len(current_members) - len(existing_imeis)
            if remaining_count < 2:
                raise ValidationError(
                    "移除後群組成員數量將少於 2 個，不符合 DSG 要求",
                    {
                        'current_count': len(current_members),
                        'removing_count': len(existing_imeis)
                    }
                )
            
            # 4. 移除成員
            self._repo.remove_members(group_id, existing_imeis)
            
            # 5. 重新查詢
            group = self.get_group(group_id)
            
            logger.info(f"✅ Removed {len(existing_imeis)} members from group {group_id}")
            return group
            
        except (RecordNotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to remove members from group {group_id}: {e}")
            raise ServiceError(
                f"移除成員失敗: {str(e)}",
                {'group_id': group_id}
            )
    
    def get_group_members(self, group_id: GroupID) -> List[IMEI]:
        """
        取得群組成員
        
        Args:
            group_id: 群組 ID
            
        Returns:
            成員 IMEI 列表
        """
        logger.debug(f"Getting members for group {group_id}")
        return self._repo.get_members(group_id)
    
    # ========== 一鍵設定 ==========
    
    def setup_complete_dsg_tracking(
        self,
        group_name: str,
        imeis: List[IMEI],
        threshold_kb: float,
        description: str = "",
        email_addresses: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        一鍵完成 DSG 追蹤設定
        
        業務流程：
        1. 建立 Resource Group
        2. 加入成員
        3. 建立 Tracker（可選）
        4. 建立 Tracker Profile（可選）
        5. 建立 Tracker Rule（可選）
        6. 關聯群組到 Tracker（可選）
        
        Args:
            group_name: 群組名稱
            imeis: IMEI 列表
            threshold_kb: 閾值（KB）
            description: 描述
            email_addresses: 通知 Email
            
        Returns:
            設定結果字典
            
        Raises:
            DSGSetupError: 設定失敗
        """
        try:
            logger.info(f"Setting up complete DSG tracking for: {group_name}")
            
            # 1. 建立群組並加入成員
            group = self.create_group(
                group_name=group_name,
                description=description,
                initial_imeis=imeis
            )
            
            result = {
                'group_id': group.group_id,
                'group_name': group.group_name,
                'member_count': len(group.member_imeis),
                'tracker_setup': False
            }
            
            # TODO: 2-6 步驟需要實作 Tracker Service
            # 目前只完成群組建立
            
            logger.info(f"✅ Completed DSG setup for: {group_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to setup DSG tracking: {e}")
            raise DSGSetupError(
                f"DSG 追蹤設定失敗: {str(e)}",
                {'group_name': group_name}
            )

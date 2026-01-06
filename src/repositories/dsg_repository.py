"""
DSG Repository
DSG Repository - 處理 DSG 資料存取
"""

from typing import Optional, List, Dict, Any
import logging

from src.repositories.base_repository import BaseRepository
from src.domain.dsg_group import DSGGroup
from src.infrastructure.iws_client import IWSClient
from src.utils.types import GroupID, IMEI
from src.utils.exceptions import (
    RecordNotFoundError,
    RepositoryError,
    DuplicateRecordError
)


logger = logging.getLogger(__name__)


class DSGRepository(BaseRepository[DSGGroup, GroupID]):
    """
    DSG Repository
    
    職責：
    - 透過 IWS Report API 管理 DSG
    - 將 API 回應轉換為 Domain Model
    - 管理快取
    """
    
    def __init__(self, iws_client: IWSClient):
        """
        初始化 Repository
        
        Args:
            iws_client: IWS API 客戶端
        """
        super().__init__()
        self._client = iws_client
        logger.info("DSGRepository initialized")
    
    def find_by_id(self, group_id: GroupID) -> Optional[DSGGroup]:
        """
        根據 Group ID 查詢 DSG
        
        Args:
            group_id: 群組 ID
            
        Returns:
            DSG 群組，如果不存在則返回 None
        """
        try:
            logger.debug(f"Finding DSG group by ID: {group_id}")
            
            # 檢查快取
            cached = self._get_from_cache(group_id)
            if cached:
                return cached
            
            # 查詢所有群組並過濾
            all_groups = self.find_all()
            for group in all_groups:
                if group.group_id == group_id:
                    self._add_to_cache(group_id, group)
                    return group
            
            logger.debug(f"DSG group not found: {group_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to find DSG group {group_id}: {e}")
            raise RepositoryError(
                f"查詢 DSG 群組失敗: {str(e)}",
                {'group_id': group_id}
            )
    
    def find_all(self, **filters) -> List[DSGGroup]:
        """
        查詢所有 DSG 群組
        
        Args:
            **filters: 
                - group_name: 群組名稱（支援萬用字元）
                - status: 狀態
                
        Returns:
            DSG 群組列表
        """
        try:
            logger.debug("Finding all DSG groups")
            
            # 呼叫 API
            response = self._client.get_resource_groups(
                service_type='SHORT_BURST_DATA',
                status=filters.get('status', 'ACTIVE'),
                group_name=filters.get('group_name')
            )
            
            # 轉換為 Domain Model
            groups = []
            if response and 'groups' in response:
                for group_data in response['groups']:
                    group = self._map_to_domain(group_data)
                    groups.append(group)
            
            logger.debug(f"Found {len(groups)} DSG groups")
            return groups
            
        except Exception as e:
            logger.error(f"Failed to find DSG groups: {e}")
            raise RepositoryError(
                f"查詢 DSG 群組失敗: {str(e)}"
            )
    
    def save(self, group: DSGGroup) -> DSGGroup:
        """
        儲存 DSG 群組（建立或更新）
        
        Args:
            group: DSG 群組
            
        Returns:
            儲存後的群組
        """
        try:
            logger.info(f"Saving DSG group: {group.group_name}")
            
            # 驗證
            self._validate_entity(group)
            
            # 檢查是否已存在
            existing = self.find_by_name(group.group_name)
            if existing and existing.group_id != group.group_id:
                raise DuplicateRecordError(
                    f"群組名稱已存在: {group.group_name}"
                )
            
            # 如果是新群組，建立之
            if not group.group_id or group.group_id == '0':
                response = self._client.create_resource_group(
                    group_name=group.group_name,
                    description=group.description
                )
                group.group_id = str(response.get('groupId', '0'))
            
            # 清除快取
            self._invalidate_cache()
            
            logger.info(f"✅ Saved DSG group: {group.group_id}")
            return group
            
        except Exception as e:
            logger.error(f"Failed to save DSG group: {e}")
            raise RepositoryError(
                f"儲存 DSG 群組失敗: {str(e)}",
                {'group_name': group.group_name}
            )
    
    def delete(self, group_id: GroupID) -> bool:
        """
        刪除 DSG 群組（不支援）
        
        Note: IWS API 不支援刪除 Resource Group
        """
        raise NotImplementedError("IWS API 不支援刪除 Resource Group")
    
    def exists(self, group_id: GroupID) -> bool:
        """檢查群組是否存在"""
        return self.find_by_id(group_id) is not None
    
    # ========== 成員管理 ==========
    
    def add_members(
        self,
        group_id: GroupID,
        imeis: List[IMEI]
    ) -> None:
        """
        加入成員到群組
        
        Args:
            group_id: 群組 ID
            imeis: IMEI 列表
        """
        try:
            logger.info(f"Adding {len(imeis)} members to group {group_id}")
            
            # 準備設備列表
            devices = [{'imei': imei} for imei in imeis]
            
            # 呼叫 API
            self._client.update_resource_group_member(
                group_id=int(group_id),
                action_type='ADD',
                resource_type='IMEI',
                devices=devices,
                bulk_action='TRUE'
            )
            
            # 清除快取
            self._invalidate_cache()
            
            logger.info(f"✅ Added members to group {group_id}")
            
        except Exception as e:
            logger.error(f"Failed to add members to group {group_id}: {e}")
            raise RepositoryError(
                f"加入成員失敗: {str(e)}",
                {'group_id': group_id, 'imeis': imeis}
            )
    
    def remove_members(
        self,
        group_id: GroupID,
        imeis: List[IMEI]
    ) -> None:
        """
        從群組移除成員
        
        Args:
            group_id: 群組 ID
            imeis: IMEI 列表
        """
        try:
            logger.info(f"Removing {len(imeis)} members from group {group_id}")
            
            # 準備設備列表
            devices = [{'imei': imei} for imei in imeis]
            
            # 呼叫 API
            self._client.update_resource_group_member(
                group_id=int(group_id),
                action_type='DELETE',
                resource_type='IMEI',
                devices=devices,
                bulk_action='TRUE'
            )
            
            # 清除快取
            self._invalidate_cache()
            
            logger.info(f"✅ Removed members from group {group_id}")
            
        except Exception as e:
            logger.error(f"Failed to remove members from group {group_id}: {e}")
            raise RepositoryError(
                f"移除成員失敗: {str(e)}",
                {'group_id': group_id, 'imeis': imeis}
            )
    
    def get_members(self, group_id: GroupID) -> List[IMEI]:
        """
        取得群組成員
        
        Args:
            group_id: 群組 ID
            
        Returns:
            成員 IMEI 列表
        """
        try:
            logger.debug(f"Getting members for group {group_id}")
            
            response = self._client.get_resource_group_members(
                group_id=int(group_id)
            )
            
            members = []
            if response and 'members' in response:
                for member in response['members']:
                    if 'imei' in member:
                        members.append(member['imei'])
            
            logger.debug(f"Found {len(members)} members in group {group_id}")
            return members
            
        except Exception as e:
            logger.error(f"Failed to get members for group {group_id}: {e}")
            raise RepositoryError(
                f"取得成員失敗: {str(e)}",
                {'group_id': group_id}
            )
    
    # ========== 特殊查詢 ==========
    
    def find_by_name(self, group_name: str) -> Optional[DSGGroup]:
        """
        根據名稱查詢 DSG 群組
        
        Args:
            group_name: 群組名稱
            
        Returns:
            DSG 群組，如果不存在則返回 None
        """
        groups = self.find_all(group_name=group_name)
        
        # 精確匹配
        for group in groups:
            if group.group_name == group_name:
                return group
        
        return None
    
    # ========== 內部方法 ==========
    
    def _map_to_domain(self, api_data: Dict[str, Any]) -> DSGGroup:
        """
        將 API 回應轉換為 Domain Model
        
        Args:
            api_data: API 回應資料
            
        Returns:
            DSGGroup 實體
        """
        group_id = str(api_data.get('groupId', '0'))
        
        # 如果有成員資訊，一併取得
        member_imeis = []
        if group_id != '0':
            try:
                member_imeis = self.get_members(group_id)
            except:
                pass
        
        return DSGGroup(
            group_id=group_id,
            group_name=api_data.get('groupName', ''),
            description=api_data.get('description', ''),
            member_imeis=member_imeis,
            status=api_data.get('status', 'ACTIVE')
        )
    
    def _validate_entity(self, group: DSGGroup) -> None:
        """驗證 DSG 群組"""
        group.validate()

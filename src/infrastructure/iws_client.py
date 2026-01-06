"""
IWS API Client
IWS SOAP API 客戶端 - 處理所有與 Iridium Web Services 的通訊
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session

from src.utils.exceptions import (
    APIConnectionError,
    APIResponseError,
    APIAuthenticationError,
    InfrastructureError
)
from src.utils.types import IWSConfig


logger = logging.getLogger(__name__)


class IWSClient:
    """
    IWS API 客戶端
    
    負責與 Iridium Web Services SOAP API 通訊。
    
    職責：
    - 管理 SOAP 連線
    - 處理認證
    - 執行 API 呼叫
    - 處理錯誤和重試
    
    不包含：
    - 業務邏輯
    - 資料轉換邏輯
    - 快取管理
    """
    
    def __init__(self, config: IWSConfig):
        """
        初始化 IWS 客戶端
        
        Args:
            config: IWS 設定
        """
        self._config = config
        self._client: Optional[Client] = None
        self._session: Optional[Session] = None
        self._is_connected: bool = False
        
        logger.info(f"IWSClient initialized for endpoint: {config['endpoint']}")
    
    # ========== Connection Management ==========
    
    def connect(self) -> None:
        """
        建立與 IWS 的連線
        
        Raises:
            APIConnectionError: 連線失敗
            APIAuthenticationError: 認證失敗
        """
        try:
            logger.info("Connecting to IWS API...")
            
            # 建立 Session
            self._session = Session()
            self._session.auth = (
                self._config['username'],
                self._config['password']
            )
            
            # 設定 Transport
            transport = Transport(
                session=self._session,
                timeout=self._config.get('timeout', 30)
            )
            
            # 建立 SOAP Client
            settings = Settings(
                strict=False,
                xml_huge_tree=True
            )
            
            self._client = Client(
                wsdl=self._config['endpoint'] + '?wsdl',
                transport=transport,
                settings=settings
            )
            
            # 設定認證 Header
            self._client.transport.session.headers.update({
                'SP-Account': self._config['sp_account']
            })
            
            self._is_connected = True
            logger.info("✅ Connected to IWS API successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to IWS: {e}")
            raise APIConnectionError(
                f"無法連線到 IWS API: {str(e)}",
                {'endpoint': self._config['endpoint']}
            )
    
    def disconnect(self) -> None:
        """關閉連線"""
        if self._session:
            self._session.close()
        
        self._client = None
        self._session = None
        self._is_connected = False
        
        logger.info("Disconnected from IWS API")
    
    def ensure_connected(self) -> None:
        """確保已連線，如果未連線則自動連線"""
        if not self._is_connected or not self._client:
            self.connect()
    
    def is_connected(self) -> bool:
        """檢查連線狀態"""
        return self._is_connected and self._client is not None
    
    # ========== API Calls ==========
    
    def call_api(
        self, 
        method_name: str, 
        **params
    ) -> Dict[str, Any]:
        """
        呼叫 IWS API 方法
        
        Args:
            method_name: API 方法名稱
            **params: API 參數
            
        Returns:
            API 回應（轉換為字典）
            
        Raises:
            APIConnectionError: 連線失敗
            APIResponseError: API 回應錯誤
        """
        self.ensure_connected()
        
        try:
            logger.debug(f"Calling IWS API: {method_name} with params: {params}")
            
            # 取得 API 方法
            method = getattr(self._client.service, method_name)
            
            # 執行呼叫
            response = method(**params)
            
            # 轉換為字典
            result = self._serialize_response(response)
            
            logger.debug(f"API call successful: {method_name}")
            return result
            
        except AttributeError:
            raise APIResponseError(
                f"API 方法不存在: {method_name}",
                {'method': method_name}
            )
        
        except Exception as e:
            logger.error(f"API call failed: {method_name} - {e}")
            raise APIResponseError(
                f"API 呼叫失敗: {method_name}",
                {'method': method_name, 'error': str(e)}
            )
    
    def _serialize_response(self, obj: Any) -> Any:
        """
        將 Zeep 物件序列化為字典
        
        Args:
            obj: Zeep 回應物件
            
        Returns:
            序列化後的字典或原始值
        """
        if obj is None:
            return None
        
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        if isinstance(obj, list):
            return [self._serialize_response(item) for item in obj]
        
        if hasattr(obj, '__dict__'):
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):
                    result[key] = self._serialize_response(value)
            return result
        
        return str(obj)
    
    # ========== Subscriber Operations ==========
    
    def search_subscriber(self, imei: str) -> Dict[str, Any]:
        """
        查詢訂戶資訊
        
        Args:
            imei: IMEI 號碼
            
        Returns:
            訂戶資訊
        """
        return self.call_api('searchAccount', imei=imei)
    
    def activate_subscriber(
        self, 
        imei: str, 
        plan_id: str
    ) -> Dict[str, Any]:
        """
        啟用訂戶
        
        Args:
            imei: IMEI 號碼
            plan_id: 方案 ID
            
        Returns:
            操作結果
        """
        return self.call_api(
            'activateSubscriber',
            imei=imei,
            planId=plan_id
        )
    
    def suspend_subscriber(self, imei: str) -> Dict[str, Any]:
        """
        暫停訂戶
        
        Args:
            imei: IMEI 號碼
            
        Returns:
            操作結果
        """
        return self.call_api('suspendSubscriber', imei=imei)
    
    def deactivate_subscriber(self, imei: str) -> Dict[str, Any]:
        """
        註銷訂戶
        
        Args:
            imei: IMEI 號碼
            
        Returns:
            操作結果
        """
        return self.call_api('deactivateSubscriber', imei=imei)
    
    def change_plan(
        self, 
        imei: str, 
        new_plan_id: str
    ) -> Dict[str, Any]:
        """
        變更訂戶方案
        
        Args:
            imei: IMEI 號碼
            new_plan_id: 新方案 ID
            
        Returns:
            操作結果
        """
        return self.call_api(
            'changePlan',
            imei=imei,
            newPlanId=new_plan_id
        )
    
    # ========== DSG Operations ==========
    
    def create_resource_group(
        self,
        group_name: str,
        service_type: str = 'SHORT_BURST_DATA',
        description: str = '',
        status: str = 'ACTIVE'
    ) -> Dict[str, Any]:
        """
        建立 Resource Group
        
        Args:
            group_name: 群組名稱
            service_type: 服務類型
            description: 描述
            status: 狀態
            
        Returns:
            建立的群組資訊
        """
        return self.call_api(
            'createResourceGroup',
            groupName=group_name,
            serviceType=service_type,
            description=description,
            status=status
        )
    
    def update_resource_group_member(
        self,
        group_id: int,
        action_type: str,
        resource_type: str,
        devices: List[Dict[str, str]],
        bulk_action: str = 'TRUE'
    ) -> Dict[str, Any]:
        """
        更新 Resource Group 成員
        
        Args:
            group_id: 群組 ID
            action_type: 操作類型（ADD/DELETE）
            resource_type: 資源類型（IMEI）
            devices: 設備列表
            bulk_action: 是否批次操作
            
        Returns:
            操作結果
        """
        return self.call_api(
            'updateResourceGroupMember',
            groupId=group_id,
            actionType=action_type,
            resourceType=resource_type,
            devices=devices,
            bulkAction=bulk_action
        )
    
    def get_resource_groups(
        self,
        service_type: str = 'SHORT_BURST_DATA',
        status: str = 'ACTIVE',
        group_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查詢 Resource Groups
        
        Args:
            service_type: 服務類型
            status: 狀態
            group_name: 群組名稱（可選，支援萬用字元）
            
        Returns:
            群組列表
        """
        params = {
            'serviceType': service_type,
            'status': status
        }
        
        if group_name:
            params['groupName'] = group_name
        
        return self.call_api('getResourceGroups', **params)
    
    def get_resource_group_members(
        self,
        group_id: int
    ) -> Dict[str, Any]:
        """
        查詢 Resource Group 成員
        
        Args:
            group_id: 群組 ID
            
        Returns:
            成員列表
        """
        return self.call_api(
            'getResourceGroupMembers',
            groupId=group_id
        )
    
    # ========== Tracker Operations ==========
    
    def create_tracker(
        self,
        tracker_type: str,
        service_type: str,
        name: str,
        email_addresses: str,
        description: str = ''
    ) -> Dict[str, Any]:
        """
        建立 Tracker
        
        Args:
            tracker_type: Tracker 類型
            service_type: 服務類型
            name: 名稱
            email_addresses: Email 地址
            description: 描述
            
        Returns:
            建立的 Tracker 資訊
        """
        return self.call_api(
            'createTracker',
            trackerType=tracker_type,
            serviceType=service_type,
            name=name,
            emailAddresses=email_addresses,
            description=description
        )
    
    def add_tracker_rules_profile(
        self,
        name: str,
        service_type: str,
        usage_unit_id: str,
        threshold_balance: str,
        status: str = 'ACTIVE'
    ) -> Dict[str, Any]:
        """
        建立 Tracker Rules Profile
        
        Args:
            name: 名稱
            service_type: 服務類型
            usage_unit_id: 使用單位 ID
            threshold_balance: 閾值
            status: 狀態
            
        Returns:
            建立的 Profile 資訊
        """
        return self.call_api(
            'addTrackerRulesProfile',
            name=name,
            serviceType=service_type,
            usageUnitId=usage_unit_id,
            thresholdBalance=threshold_balance,
            status=status
        )
    
    def add_tracker_rule(
        self,
        tracker_id: str,
        tracker_rules_profile_id: str,
        name: str,
        reset_cycle: str,
        notify_on_reset: str,
        tracker_rule_type: str,
        cycle_setting: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        建立 Tracker Rule
        
        Args:
            tracker_id: Tracker ID
            tracker_rules_profile_id: Profile ID
            name: 名稱
            reset_cycle: 重置週期
            notify_on_reset: 是否通知重置
            tracker_rule_type: Rule 類型
            cycle_setting: 週期設定
            
        Returns:
            建立的 Rule 資訊
        """
        params = {
            'trackerId': tracker_id,
            'trackerRulesProfileId': tracker_rules_profile_id,
            'name': name,
            'resetCycle': reset_cycle,
            'notifyOnReset': notify_on_reset,
            'trackerRuleType': tracker_rule_type
        }
        
        if cycle_setting is not None:
            params['cycleSetting'] = cycle_setting
        
        return self.call_api('addTrackerRule', **params)
    
    def add_tracker_member(
        self,
        tracker_id: str,
        member_type: str,
        member_id: str
    ) -> Dict[str, Any]:
        """
        將成員加入 Tracker
        
        Args:
            tracker_id: Tracker ID
            member_type: 成員類型
            member_id: 成員 ID
            
        Returns:
            操作結果
        """
        return self.call_api(
            'addTrackerMember',
            trackerId=tracker_id,
            memberType=member_type,
            memberId=member_id
        )
    
    def get_tracker_rules(
        self,
        tracker_id: str,
        include_future: str = 'FALSE'
    ) -> Dict[str, Any]:
        """
        查詢 Tracker Rules
        
        Args:
            tracker_id: Tracker ID
            include_future: 是否包含未來的 Rules
            
        Returns:
            Rules 列表
        """
        return self.call_api(
            'getTrackerRules',
            trackerId=tracker_id,
            includeFuture=include_future
        )
    
    def get_tracker_usage_log(
        self,
        tracker_rule_id: str,
        limit: int = 100,
        search_start_date: Optional[str] = None,
        search_end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查詢 Tracker 用量記錄
        
        Args:
            tracker_rule_id: Rule ID
            limit: 最大筆數
            search_start_date: 開始日期
            search_end_date: 結束日期
            
        Returns:
            用量記錄
        """
        params = {
            'trackerRuleId': tracker_rule_id,
            'limit': limit
        }
        
        if search_start_date:
            params['searchStartDate'] = search_start_date
        if search_end_date:
            params['searchEndDate'] = search_end_date
        
        return self.call_api('getTrackerUsageLog', **params)
    
    # ========== Context Manager ==========
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
        return False

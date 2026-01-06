"""
DSG Tracker Service - DSG 流量追蹤服務
使用 IWS Report API 建立和查詢 DSG 流量使用情況

功能：
1. 建立 Resource Group（監控群組）
2. 加入/移除 IMEI 到群組
3. 建立 Tracker 和 Rule
4. 查詢剩餘流量
5. 查詢超額記錄
6. 查詢 DSG 成員資訊

注意：
- Resource Group 是監控工具，不等於實際 DSG
- 實際 DSG 需透過 SPNet Pro 或 Email Support 創建
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class DSGTrackerService:
    """DSG Tracker 服務"""
    
    def __init__(self, gateway):
        """
        初始化服務
        
        Args:
            gateway: IWS Gateway 實例
        """
        self.gateway = gateway
    
    # ========== Resource Group 管理 ==========
    
    def create_resource_group(
        self,
        group_name: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        建立 Resource Group
        
        Args:
            group_name: 群組名稱（必須在 SP 內唯一，最多40字元）
            description: 群組描述（選填，最多100字元）
            
        Returns:
            {
                'success': bool,
                'group_id': str,  # 系統生成的唯一ID
                'group_name': str,
                'message': str,
                'error': str  # 如果失敗
            }
        """
        try:
            # 準備請求
            request_data = {
                'groupName': group_name,
                'serviceType': 'SHORT_BURST_DATA',
                'description': description,
                'status': 'ACTIVE'
            }
            
            # 呼叫 API
            response = self.gateway.soap_client.service.createResourceGroup(**request_data)
            
            # 解析回應
            if hasattr(response, 'resourceGroupDetail'):
                detail = response.resourceGroupDetail
                return {
                    'success': True,
                    'group_id': str(detail.groupId),
                    'group_name': detail.groupName,
                    'message': f'成功建立 Resource Group: {detail.groupName}'
                }
            else:
                return {
                    'success': False,
                    'error': '建立失敗：API 回應格式錯誤'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'建立 Resource Group 失敗: {str(e)}'
            }
    
    def add_imeis_to_group(
        self,
        group_id: str,
        imeis: List[str],
        bulk: bool = True
    ) -> Dict[str, Any]:
        """
        將 IMEI 加入 Resource Group
        
        Args:
            group_id: 群組ID
            imeis: IMEI 列表
            bulk: 是否批次操作（預設 True）
            
        Returns:
            {
                'success': bool,
                'added_count': int,
                'message': str,
                'error': str  # 如果失敗
            }
        """
        try:
            # 準備設備列表
            devices = [{'device': imei} for imei in imeis]
            
            # 準備請求
            request_data = {
                'groupId': int(group_id),
                'actionType': 'ADD',
                'resourceType': 'IMEI',
                'bulkAction': 'TRUE' if bulk else 'FALSE',
                'devices': devices
            }
            
            # 呼叫 API
            self.gateway.soap_client.service.updateResourceGroupMember(**request_data)
            
            # 空回應表示成功
            return {
                'success': True,
                'added_count': len(imeis),
                'message': f'成功加入 {len(imeis)} 個 IMEI 到群組'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'加入 IMEI 失敗: {str(e)}'
            }
    
    def remove_imeis_from_group(
        self,
        group_id: str,
        imeis: List[str]
    ) -> Dict[str, Any]:
        """
        從 Resource Group 移除 IMEI
        
        Args:
            group_id: 群組ID
            imeis: IMEI 列表
            
        Returns:
            {
                'success': bool,
                'removed_count': int,
                'message': str,
                'error': str  # 如果失敗
            }
        """
        try:
            devices = [{'device': imei} for imei in imeis]
            
            request_data = {
                'groupId': int(group_id),
                'actionType': 'DELETE',
                'resourceType': 'IMEI',
                'bulkAction': 'TRUE',
                'devices': devices
            }
            
            self.gateway.soap_client.service.updateResourceGroupMember(**request_data)
            
            return {
                'success': True,
                'removed_count': len(imeis),
                'message': f'成功移除 {len(imeis)} 個 IMEI'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'移除 IMEI 失敗: {str(e)}'
            }
    
    def get_resource_groups(
        self,
        group_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查詢 Resource Groups
        
        Args:
            group_name: 群組名稱（選填，支援萬用字元）
            
        Returns:
            {
                'success': bool,
                'groups': List[Dict],
                'total_count': int,
                'error': str  # 如果失敗
            }
        """
        try:
            request_data = {
                'serviceType': 'SHORT_BURST_DATA',
                'status': 'ACTIVE'
            }
            
            if group_name:
                request_data['groupName'] = group_name
            
            response = self.gateway.soap_client.service.getResourceGroups(**request_data)
            
            groups = []
            if hasattr(response, 'resourceGroupDetails'):
                for detail in response.resourceGroupDetails:
                    groups.append({
                        'group_id': str(detail.groupId),
                        'group_name': detail.groupName,
                        'description': getattr(detail, 'description', ''),
                        'status': detail.status,
                        'created_date': str(detail.createdDate)
                    })
            
            return {
                'success': True,
                'groups': groups,
                'total_count': len(groups)
            }
        
        except Exception as e:
            return {
                'success': False,
                'groups': [],
                'total_count': 0,
                'error': f'查詢失敗: {str(e)}'
            }
    
    def get_group_members(
        self,
        group_id: str
    ) -> Dict[str, Any]:
        """
        查詢 Resource Group 的成員
        
        Args:
            group_id: 群組ID
            
        Returns:
            {
                'success': bool,
                'members': List[str],  # IMEI 列表
                'total_count': int,
                'error': str  # 如果失敗
            }
        """
        try:
            request_data = {
                'groupId': int(group_id)
            }
            
            response = self.gateway.soap_client.service.getResourceGroupMembers(**request_data)
            
            members = []
            if hasattr(response, 'resourceGroupMembers'):
                for member in response.resourceGroupMembers:
                    members.append(member.resourceId)
            
            return {
                'success': True,
                'members': members,
                'total_count': len(members)
            }
        
        except Exception as e:
            return {
                'success': False,
                'members': [],
                'total_count': 0,
                'error': f'查詢成員失敗: {str(e)}'
            }
    
    # ========== Tracker 管理 ==========
    
    def create_tracker(
        self,
        name: str,
        email_addresses: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        建立 Tracker
        
        Args:
            name: Tracker 名稱（最多40字元）
            email_addresses: 通知 email（逗號分隔）
            description: 描述（選填）
            
        Returns:
            {
                'success': bool,
                'tracker_id': str,
                'message': str,
                'error': str  # 如果失敗
            }
        """
        try:
            request_data = {
                'trackerType': 'EXTERNAL',
                'serviceType': 'SHORT_BURST_DATA',
                'name': name,
                'description': description,
                'emailAddresses': email_addresses
            }
            
            response = self.gateway.soap_client.service.createTracker(**request_data)
            
            if hasattr(response, 'tracker'):
                tracker = response.tracker
                return {
                    'success': True,
                    'tracker_id': str(tracker.trackerId),
                    'message': f'成功建立 Tracker: {name}'
                }
            else:
                return {
                    'success': False,
                    'error': '建立失敗：API 回應格式錯誤'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'建立 Tracker 失敗: {str(e)}'
            }
    
    def create_tracker_profile(
        self,
        name: str,
        threshold_bytes: int,
        usage_unit_id: str = "5"  # bytes 的 unit ID（需先查詢 getUsageUnits）
    ) -> Dict[str, Any]:
        """
        建立 Tracker Rules Profile
        
        Args:
            name: Profile 名稱
            threshold_bytes: 閾值（bytes）
            usage_unit_id: 使用單位 ID（預設 "5" for bytes）
            
        Returns:
            {
                'success': bool,
                'profile_id': str,
                'message': str,
                'error': str  # 如果失敗
            }
        """
        try:
            request_data = {
                'name': name,
                'serviceType': 'SHORT_BURST_DATA',
                'usageUnitId': usage_unit_id,
                'thresholdBalance': str(threshold_bytes),
                'status': 'ACTIVE'
            }
            
            response = self.gateway.soap_client.service.addTrackerRulesProfile(**request_data)
            
            if hasattr(response, 'trackerRulesProfile'):
                profile = response.trackerRulesProfile
                return {
                    'success': True,
                    'profile_id': str(profile.trackerRulesProfileId),
                    'message': f'成功建立 Tracker Profile: {name}'
                }
            else:
                return {
                    'success': False,
                    'error': '建立失敗：API 回應格式錯誤'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'建立 Tracker Profile 失敗: {str(e)}'
            }
    
    def add_tracker_rule(
        self,
        tracker_id: str,
        profile_id: str,
        rule_name: str,
        reset_cycle: str = "MONTHLY",
        cycle_setting: int = 1
    ) -> Dict[str, Any]:
        """
        建立 Tracker Rule
        
        Args:
            tracker_id: Tracker ID
            profile_id: Rules Profile ID
            rule_name: Rule 名稱
            reset_cycle: 重置週期（MONTHLY/BILLCYCLE/DAILY/WEEKLY/THRESHOLD）
            cycle_setting: 週期設定（MONTHLY=1-31, DAILY=0-23, WEEKLY=0-6）
            
        Returns:
            {
                'success': bool,
                'rule_id': str,
                'message': str,
                'error': str  # 如果失敗
            }
        """
        try:
            request_data = {
                'trackerId': str(tracker_id),
                'trackerRulesProfileId': str(profile_id),
                'name': rule_name,
                'resetCycle': reset_cycle,
                'notifyOnReset': 'TRUE',
                'trackerRuleType': 'HIGH'  # HIGH = 超過閾值觸發
            }
            
            if reset_cycle in ['MONTHLY', 'DAILY', 'WEEKLY']:
                request_data['cycleSetting'] = cycle_setting
            
            response = self.gateway.soap_client.service.addTrackerRule(**request_data)
            
            if hasattr(response, 'trackerRule'):
                rule = response.trackerRule
                return {
                    'success': True,
                    'rule_id': str(rule.trackerRuleId),
                    'message': f'成功建立 Tracker Rule: {rule_name}'
                }
            else:
                return {
                    'success': False,
                    'error': '建立失敗：API 回應格式錯誤'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'建立 Tracker Rule 失敗: {str(e)}'
            }
    
    def add_tracker_member(
        self,
        tracker_id: str,
        group_id: str
    ) -> Dict[str, Any]:
        """
        將 Resource Group 加入 Tracker
        
        Args:
            tracker_id: Tracker ID
            group_id: Resource Group ID
            
        Returns:
            {
                'success': bool,
                'message': str,
                'error': str  # 如果失敗
            }
        """
        try:
            request_data = {
                'trackerId': str(tracker_id),
                'memberType': 'RESOURCE_GROUP',
                'memberId': str(group_id)
            }
            
            self.gateway.soap_client.service.addTrackerMember(**request_data)
            
            return {
                'success': True,
                'message': '成功將群組加入 Tracker'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'加入 Tracker Member 失敗: {str(e)}'
            }
    
    # ========== 流量查詢 ==========
    
    def get_tracker_rules(
        self,
        tracker_id: str
    ) -> Dict[str, Any]:
        """
        查詢 Tracker Rules（包含當前用量）
        
        Args:
            tracker_id: Tracker ID
            
        Returns:
            {
                'success': bool,
                'rules': List[Dict],
                'error': str  # 如果失敗
            }
        """
        try:
            request_data = {
                'trackerId': str(tracker_id),
                'includeFuture': 'FALSE'
            }
            
            response = self.gateway.soap_client.service.getTrackerRules(**request_data)
            
            rules = []
            if hasattr(response, 'trackerRules'):
                for rule in response.trackerRules:
                    current_balance = int(rule.currentBalance)
                    cumulative_balance = int(rule.cumulativeBalance)
                    
                    # 從 profile 取得閾值（需要另外查詢）
                    # 這裡先用 rule 中的資訊
                    
                    rules.append({
                        'rule_id': str(rule.trackerRuleId),
                        'rule_name': rule.name,
                        'current_balance': current_balance,
                        'cumulative_balance': cumulative_balance,
                        'reset_cycle': rule.resetCycle,
                        'next_cycle_date': str(rule.nextCycleDate),
                        'last_cycle_date': str(getattr(rule, 'lastCycleDate', 'N/A'))
                    })
            
            return {
                'success': True,
                'rules': rules
            }
        
        except Exception as e:
            return {
                'success': False,
                'rules': [],
                'error': f'查詢 Tracker Rules 失敗: {str(e)}'
            }
    
    def calculate_remaining_data(
        self,
        threshold_bytes: int,
        current_balance_bytes: int
    ) -> Dict[str, Any]:
        """
        計算剩餘流量
        
        Args:
            threshold_bytes: 閾值（總配額）
            current_balance_bytes: 當前已使用
            
        Returns:
            {
                'threshold_kb': float,
                'used_kb': float,
                'remaining_kb': float,
                'overage_kb': float,  # 超額量（如果有）
                'usage_percentage': float,
                'is_over_threshold': bool
            }
        """
        threshold_kb = threshold_bytes / 1024
        used_kb = current_balance_bytes / 1024
        remaining_kb = max(0, threshold_kb - used_kb)
        overage_kb = max(0, used_kb - threshold_kb)
        usage_percentage = (used_kb / threshold_kb * 100) if threshold_kb > 0 else 0
        
        return {
            'threshold_kb': round(threshold_kb, 2),
            'used_kb': round(used_kb, 2),
            'remaining_kb': round(remaining_kb, 2),
            'overage_kb': round(overage_kb, 2),
            'usage_percentage': round(usage_percentage, 2),
            'is_over_threshold': current_balance_bytes > threshold_bytes
        }
    
    def get_tracker_usage_log(
        self,
        rule_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        查詢 Tracker 用量記錄
        
        Args:
            rule_id: Tracker Rule ID
            start_date: 開始日期（ISO format）
            end_date: 結束日期（ISO format）
            limit: 最大筆數
            
        Returns:
            {
                'success': bool,
                'logs': List[Dict],
                'total_count': int,
                'error': str  # 如果失敗
            }
        """
        try:
            request_data = {
                'trackerRuleId': str(rule_id),
                'limit': limit
            }
            
            if start_date:
                request_data['searchStartDate'] = start_date
            if end_date:
                request_data['searchEndDate'] = end_date
            
            response = self.gateway.soap_client.service.getTrackerUsageLog(**request_data)
            
            logs = []
            if hasattr(response, 'trackerUsageLogDetails'):
                for log in response.trackerUsageLogDetails:
                    logs.append({
                        'cdr_id': getattr(log, 'cdrId', 'N/A'),
                        'balance_impact': int(log.balanceImpact),
                        'original_balance': int(log.originalBal),
                        'new_balance': int(log.newBal),
                        'processed_date': str(log.processedDt)
                    })
            
            total_count = int(response.totalNumberOfRecords) if hasattr(response, 'totalNumberOfRecords') else len(logs)
            
            return {
                'success': True,
                'logs': logs,
                'total_count': total_count
            }
        
        except Exception as e:
            return {
                'success': False,
                'logs': [],
                'total_count': 0,
                'error': f'查詢用量記錄失敗: {str(e)}'
            }

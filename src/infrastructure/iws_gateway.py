"""
IWS (Iridium Web Services) SOAP 1.2 API Gateway v6.8 Final
完全符合官方 WSDL Schema (v25.1.0.1)

v6.8 Final 修正（根據官方檔案）：
- getSBDBundles: 使用 Plan 對象（fromBundleId, forActivate）
- 刪除 updateSubscriberSbdPlan → 改用 accountUpdate
- 刪除 deactivateSubscriber → 改用 setSubscriberAccountStatus
- SBD Plan: 移除不存在的 demoAndTrial 欄位
- Boolean: 使用 "true"/"false" 字串（非 0/1）
- HMAC-SHA1 + Base64 簽章（已驗證成功）
"""
from __future__ import annotations
import requests
import urllib3
import xml.etree.ElementTree as ET
import re
import hmac
import hashlib
import base64
from typing import Dict, Optional, List
from datetime import datetime, timezone
from ..config.settings import (
    IWS_USER, 
    IWS_PASS, 
    IWS_SP_ACCOUNT,
    IWS_ENDPOINT, 
    REQUEST_TIMEOUT
)

# 隱藏 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class IWSException(Exception):
    """IWS API 異常"""
    def __init__(self, message: str, error_code: Optional[str] = None, response_text: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code
        self.response_text = response_text


class IWSGateway:
    """
    IWS SOAP 1.2 API Gateway v6.8 Final
    WSDL Compliant Edition - 完全符合官方 WSDL (v25.1.0.1)
    
    核心管理功能：
    - 連線測試（getSystemStatus）
    - 查詢方案（getSBDBundles）
    - 變更設備（accountUpdate）
    - 暫停設備（setSubscriberAccountStatus - SUSPENDED）
    - 恢復設備（setSubscriberAccountStatus - ACTIVE）
    - 註銷設備（setSubscriberAccountStatus - DEACTIVATED）
    
    認證方式：
    - 統一使用：iwsUsername + signature + timestamp
    - 不使用 caller 和 callerPassword（SITEST 不支援）
    
    簽章算法（已驗證成功）：
    - Algorithm: HMAC-SHA1
    - Message: Action名稱 + 時間戳記（無空格）
    - Key: Secret Key (password)
    - Encoding: Base64
    
    安全性：
    - 所有憑證從 config.settings 匯入
    - 零 hardcoded 帳密資訊
    """
    
    # SOAP 1.2 Namespaces
    NAMESPACES = {
        'soap': 'http://www.w3.org/2003/05/soap-envelope',
        'tns': 'http://www.iridium.com/'
    }
    
    # IWS Namespace
    IWS_NS = 'http://www.iridium.com/'
    
    # Service Types
    SERVICE_TYPE_SHORT_BURST_DATA = 'SHORT_BURST_DATA'
    
    # Update Types
    UPDATE_TYPE_IMEI = 'IMEI'
    
    # Account Status
    ACCOUNT_STATUS_ACTIVE = 'ACTIVE'
    ACCOUNT_STATUS_SUSPENDED = 'SUSPENDED'
    ACCOUNT_STATUS_DEACTIVATED = 'DEACTIVATED'
    
    def __init__(self, 
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 sp_account: Optional[str] = None,
                 endpoint: Optional[str] = None,
                 timeout: int = REQUEST_TIMEOUT):
        """
        初始化 IWS Gateway
        
        Args:
            username: IWS 使用者名稱（從 settings 匯入）
            password: IWS Secret Key（從 settings 匯入）
            sp_account: Service Provider Account Number（從 settings 匯入）
            endpoint: IWS 端點 URL
            timeout: 請求逾時時間（秒）
        """
        self.username = (username or IWS_USER).upper()  # 強制大寫
        self.password = password or IWS_PASS
        self.sp_account = sp_account or IWS_SP_ACCOUNT
        self.endpoint = endpoint or IWS_ENDPOINT
        self.timeout = timeout
        
        if not all([self.username, self.password, self.endpoint]):
            raise IWSException(
                "Missing required IWS credentials. "
                "Please configure IWS_USER, IWS_PASS, and IWS_ENDPOINT."
            )
        
        print(f"\n[IWS] Gateway initialized (v6.8 Final - WSDL Compliant)")
        print(f"[IWS] Signature Algorithm: HMAC-SHA1 + Base64 (Verified ✓)")
        print(f"[IWS] WSDL Version: v25.1.0.1")
        print(f"[IWS] Authentication: Unified (No caller tags)")
        print(f"[IWS] Username: {self.username}")
        print(f"[IWS] SP Account: {self.sp_account}")
    
    def _generate_timestamp(self) -> str:
        """
        生成符合 IWS 規範的時間戳記
        
        格式：YYYY-MM-DDTHH:MM:SSZ
        - UTC 時間
        - 無微秒
        - 結尾必須有 Z
        
        Returns:
            str: UTC 時間戳記
        """
        utc_now = datetime.now(timezone.utc)
        timestamp = utc_now.strftime('%Y-%m-%dT%H:%M:%SZ')
        return timestamp
    
    def _generate_signature(self, action_name: str, timestamp: str) -> str:
        """
        生成簽章（HMAC-SHA1 + Base64）
        
        已驗證成功的算法 ✓
        
        Args:
            action_name: SOAP Action 名稱
            timestamp: 時間戳記
            
        Returns:
            str: Base64 編碼的簽章
        """
        # Message: Action + Timestamp（無空格）
        message = f"{action_name}{timestamp}".encode('utf-8')
        
        # Key: Secret Key
        key = self.password.encode('utf-8')
        
        # HMAC-SHA1 計算
        hmac_sha1 = hmac.new(key, message, hashlib.sha1)
        signature_bytes = hmac_sha1.digest()
        
        # Base64 編碼
        signature_base64 = base64.b64encode(signature_bytes).decode('utf-8')
        
        # 診斷日誌
        print(f"\n[IWS] Signature Generation:")
        print(f"  Algorithm: HMAC-SHA1 + Base64 ✓")
        print(f"  Action: {action_name}")
        print(f"  Timestamp: {timestamp}")
        print(f"  Message: {action_name}{timestamp}")
        print(f"  Key: {self.password[:2]}*** (Secret Key)")
        print(f"  Signature (Base64): {signature_base64}")
        print(f"  Signature Length: {len(signature_base64)} chars")
        
        return signature_base64
    
    def _extract_plan_id_digits(self, plan_id: str) -> str:
        """
        提取 plan_id 中的純數字
        
        sbdBundleId 欄位必須是 Long 型別（純數字字串）
        
        範例：
        - "SBD12" → "12"
        - "SBDO" → "0"
        - "SBD17" → "17"
        - "12" → "12"
        
        Args:
            plan_id: 原始 plan ID（可能包含字母）
            
        Returns:
            str: 純數字字串
        """
        # 移除所有非數字字元
        digits = re.sub(r'\D', '', plan_id)
        
        # 如果沒有數字，預設為 "0"
        if not digits:
            digits = "0"
        
        print(f"[IWS] Plan ID conversion: '{plan_id}' → '{digits}'")
        
        return digits
    
    def _bool_to_string(self, value: bool) -> str:
        """
        將布林值轉換為字串
        
        IWS API 要求布林值以 "true"/"false" 字串發送
        
        Args:
            value: 布林值
            
        Returns:
            str: "true" (True) 或 "false" (False)
        """
        return "true" if value else "false"
    
    def _safe_xml_value(self, value: Optional[str]) -> str:
        """安全的 XML 值處理"""
        if value is None or value == '':
            return ''
        return str(value)
    
    def _validate_imei(self, imei: str) -> bool:
        """驗證 IMEI 格式"""
        if not imei:
            raise IWSException("IMEI cannot be empty")
        
        imei_digits = re.sub(r'\D', '', imei)
        
        if len(imei_digits) != 15:
            raise IWSException(
                f"Invalid IMEI length: {len(imei_digits)} (expected 15 digits). IMEI: {imei}"
            )
        
        if not imei_digits.startswith('30'):
            raise IWSException(
                f"Invalid IMEI prefix: {imei_digits[:2]} (expected '30'). IMEI: {imei}"
            )
        
        return True
    
    def _build_soap_envelope(self, body_content: str) -> str:
        """構建 SOAP 1.2 Envelope"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="{self.NAMESPACES['soap']}">
    <soap:Header/>
    <soap:Body>
{body_content}
    </soap:Body>
</soap:Envelope>'''
    
    def _build_get_system_status_body(self) -> tuple[str, str]:
        """
        構建 getSystemStatus 的 SOAP Body
        
        Returns:
            tuple: (action_name, soap_body)
        """
        action_name = 'getSystemStatus'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        sp_account = self._safe_xml_value(self.sp_account)
        
        body = f'''        <tns:getSystemStatus xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
            </request>
        </tns:getSystemStatus>'''
        
        return action_name, body
    
    def _build_account_search_body(self, imei: str) -> tuple[str, str]:
        """
        構建 accountSearch 的 SOAP Body
        
        根據 WSDL p.62
        用 IMEI 搜尋訂閱者帳號
        
        Args:
            imei: 設備 IMEI
            
        Returns:
            tuple: (action_name, soap_body)
        """
        action_name = 'accountSearch'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        sp_account = self._safe_xml_value(self.sp_account)
        
        body = f'''        <tns:accountSearch xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <serviceType>{self.SERVICE_TYPE_SHORT_BURST_DATA}</serviceType>
                <filterType>IMEI</filterType>
                <filterCond>EXACT</filterCond>
                <filterValue>{imei}</filterValue>
            </request>
        </tns:accountSearch>'''
        
        return action_name, body
    
    def _build_validate_device_string_body(self,
                                          device_string: str,
                                          device_string_type: str = "IMEI",
                                          validate_state: bool = True,
                                          service_type: str = SERVICE_TYPE_SHORT_BURST_DATA) -> tuple[str, str]:
        """
        構建 validateDeviceString 的 SOAP Body
        
        根據 WSDL p.236-237
        用於驗證設備的有效性、歸屬權和狀態
        
        Args:
            device_string: 設備字符串（如 IMEI）
            device_string_type: 設備類型（IMEI, SIM, etc.）
            validate_state: 是否檢查設備狀態（true=檢查是否被其他合約使用）
            service_type: 服務類型
            
        Returns:
            tuple: (action_name, soap_body)
        """
        action_name = 'validateDeviceString'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        sp_account = self._safe_xml_value(self.sp_account)
        
        # Boolean 轉字串
        validate_state_str = self._bool_to_string(validate_state)
        
        body = f'''        <tns:validateDeviceString xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <serviceType>{service_type}</serviceType>
                <deviceString>{device_string}</deviceString>
                <deviceStringType>{device_string_type}</deviceStringType>
                <validateState>{validate_state_str}</validateState>
            </request>
        </tns:validateDeviceString>'''
        
        return action_name, body
    
    def _build_get_sbd_bundles_body(self, 
                                    from_bundle_id: str = "0",
                                    for_activate: bool = True,
                                    model_id: Optional[str] = None) -> tuple[str, str]:
        """
        構建 getSBDBundles 的 SOAP Body
        
        根據實際 API 測試結果（v6.9.4 - 最終正確版本）
        
        重要發現：
        1. fromBundleId 和 forActivate 是查詢參數，直接放在 <request> 下
        2. <sbdPlan /> 是空標籤，用來指示服務類型（SBD）
        3. <sbdPlan> 內部的字段（sbdBundleId, lritFlagstate 等）是用於設定，不是查詢
        
        正確結構：
        <request>
            <iwsUsername>...</iwsUsername>
            <signature>...</signature>
            <serviceProviderAccountNumber>...</serviceProviderAccountNumber>
            <timestamp>...</timestamp>
            <fromBundleId>0</fromBundleId>       <!-- 查詢參數 -->
            <forActivate>true</forActivate>      <!-- 查詢參數 -->
            <sbdPlan />                          <!-- 服務類型標識 -->
        </request>
        
        Args:
            from_bundle_id: 起始 Bundle ID（通常用 "0"）
            for_activate: 是否用於啟動（true）或更新（false）
            model_id: 可選的設備型號 ID
            
        Returns:
            tuple: (action_name, soap_body)
        """
        action_name = 'getSBDBundles'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        sp_account = self._safe_xml_value(self.sp_account)
        
        # Boolean 轉字串
        for_activate_str = self._bool_to_string(for_activate)
        
        # modelId 是可選的
        model_id_tag = ''
        if model_id:
            model_id_tag = f'                <modelId>{model_id}</modelId>'
        
        body = f'''        <tns:getSBDBundles xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <fromBundleId>{from_bundle_id}</fromBundleId>
                <forActivate>{for_activate_str}</forActivate>
{model_id_tag}
                <sbdPlan />
            </request>
        </tns:getSBDBundles>'''
        
        return action_name, body
    
    def _build_account_update_body(self,
                                   imei: str,
                                   subscriber_account_number: str,
                                   new_plan_id: str,
                                   lrit_flagstate: str = "",
                                   ring_alerts_flag: bool = False) -> tuple[str, str]:
        """
        構建 accountUpdate 的 SOAP Body
        
        根據 WSDL p.67, 271-272, 286 和 Iridium 官方確認（2025-12-27）
        用於更新 SBD 設備的資費方案
        
        ✅ 關鍵要求（根據官方確認）：
        1. sbdBundleId 必須使用數字 ID（如 "763925351"），不能用字串代碼
           原因：accountUpdate 使用 sbdSubscriberAccount2 擴展物件，
           後台計費系統以 Long（長整型數字）作為唯一識別碼
        
        2. 必須包含 <accountStatus>ACTIVE</accountStatus>
           原因：明確告訴 IWS 這是對啟用中帳戶的資料更新，
           而非狀態切換請求，避免 "Field newStatus required" 錯誤
        
        Args:
            imei: 設備 IMEI
            subscriber_account_number: 訂閱者帳號（必填，如 SUB-55338265461）
            new_plan_id: 新的方案數字 ID（如 "763925351"，從 getSBDBundles 獲得）
            lrit_flagstate: LRIT Flag State（3字元或空字串）
            ring_alerts_flag: Ring Alerts Flag
            
        Returns:
            tuple: (action_name, soap_body)
        """
        action_name = 'accountUpdate'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        sp_account = self._safe_xml_value(self.sp_account)
        
        # ✅ 使用數字 ID（從 getSBDBundles 的 <id> 欄位獲得）
        bundle_id = new_plan_id
        print(f"[IWS] SOAP 請求使用 sbdBundleId: {bundle_id} (數字 ID)")
        
        # Boolean 轉字串
        ring_alerts_str = self._bool_to_string(ring_alerts_flag)
        
        # ✅ 關鍵：XML 結構必須包含 accountStatus 來消除狀態變更誤判
        body = f'''        <tns:accountUpdate xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <sbdSubscriberAccount2>
                    <subscriberAccountNumber>{subscriber_account_number}</subscriberAccountNumber>
                    <accountStatus>ACTIVE</accountStatus>
                    <plan>
                        <sbdBundleId>{bundle_id}</sbdBundleId>
                        <lritFlagstate>{lrit_flagstate}</lritFlagstate>
                        <ringAlertsFlag>{ring_alerts_str}</ringAlertsFlag>
                    </plan>
                    <imei>{imei}</imei>
                </sbdSubscriberAccount2>
            </request>
        </tns:accountUpdate>'''
        
        return action_name, body
    
    def _build_complete_account_update_body(self,
                                            account_info: Dict,
                                            new_bundle_id: str,
                                            lrit_flagstate: str = None,
                                            ring_alerts_flag: bool = None) -> tuple[str, str]:
        """
        構建完整的 accountUpdate SOAP Body
        
        根據 Iridium 的要求（2025-12-27 回覆），accountUpdate 需要完整的帳戶物件。
        此方法使用 getSubscriberAccount 的返回值來建立完整的請求。
        
        Args:
            account_info: getSubscriberAccount 的返回值（包含所有當前設定）
            new_bundle_id: 新的 SBD Bundle ID（唯一要修改的欄位）
            lrit_flagstate: LRIT Flag State（如果提供，則覆蓋當前值）
            ring_alerts_flag: Ring Alerts Flag（如果提供，則覆蓋當前值）
            
        Returns:
            tuple: (action_name, soap_body)
        """
        action_name = 'accountUpdate'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        
        # 從 account_info 提取所有必要資訊
        account_number = account_info['account_number']
        status = account_info['status']
        imei = account_info['imei']
        
        # Plan 資訊（只修改 sbdBundleId，其他保持不變）
        demo_and_trial = account_info.get('demo_and_trial', '0')
        promo = account_info.get('promo', '0')
        account_pooling_group = account_info.get('account_pooling_group', '0')
        
        # LRIT 和 Ring Alerts（如果提供新值則使用新值，否則保持當前值）
        if lrit_flagstate is not None:
            lrit = lrit_flagstate
        else:
            lrit = account_info.get('lrit_flagstate', '')
        
        if ring_alerts_flag is not None:
            ring_alerts = self._bool_to_string(ring_alerts_flag)
        else:
            ring_alerts = account_info.get('ring_alert', 'false')
        
        # Metadata
        sp_reference = account_info.get('sp_reference', '')
        
        # Bulk Action
        bulk_action = account_info.get('bulk_action', 'FALSE').upper()
        
        # 建立 deliveryDetails XML
        delivery_details_xml = ""
        for dest in account_info.get('destinations', []):
            delivery_details_xml += f"""
                <deliveryDetail>
                    <destination>{self._safe_xml_value(dest['destination'])}</destination>
                    <deliveryMethod>{dest['method']}</deliveryMethod>
                    <geoDataFlag>{dest['geo_data']}</geoDataFlag>
                    <moAckFlag>{dest.get('mo_ack', 'false')}</moAckFlag>
                </deliveryDetail>"""
        
        # 建立 mtFilters XML
        mt_filters_xml = ""
        for filt in account_info.get('mt_filters', []):
            mt_filters_xml += f"""
            <mtFilter>
                <ruleType>{filt['ruleType']}</ruleType>
                <address>{self._safe_xml_value(filt['address'])}</address>
            </mtFilter>"""
        
        # 建立完整的 SOAP Body
        body = f'''        <tns:accountUpdate xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{self.sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <sbdSubscriberAccount2>
                    <subscriberAccountNumber>{account_number}</subscriberAccountNumber>
                    <accountStatus>{status}</accountStatus>
                    <plan>
                        <promo>{promo}</promo>
                        <demoAndTrial>{demo_and_trial}</demoAndTrial>
                        <accountPoolingGroup>{account_pooling_group}</accountPoolingGroup>
                        <sbdBundleId>{new_bundle_id}</sbdBundleId>
                        <lritFlagstate>{lrit}</lritFlagstate>
                        <ringAlertsFlag>{ring_alerts}</ringAlertsFlag>
                    </plan>
                    <subscriberAccountMetadata>
                        <spReference>{sp_reference}</spReference>
                    </subscriberAccountMetadata>
                    <imei>{imei}</imei>
                    <bulkAction>{bulk_action}</bulkAction>
                    <deliveryDetails>{delivery_details_xml}
                    </deliveryDetails>
                    <mtFilters>{mt_filters_xml}
                    </mtFilters>
                </sbdSubscriberAccount2>
            </request>
        </tns:accountUpdate>'''
        
        print(f"[IWS] 建立完整的 accountUpdate 請求")
        print(f"   Bundle ID: {account_info.get('bundle_id')} → {new_bundle_id}")
        print(f"   Destinations: {len(account_info.get('destinations', []))} 個")
        print(f"   MT Filters: {len(account_info.get('mt_filters', []))} 個")
        
        return action_name, body
    
    def _build_set_subscriber_account_status_body(self,
                                                   imei: str,
                                                   new_status: str,
                                                   reason: str = '系統自動執行',
                                                   service_type: str = SERVICE_TYPE_SHORT_BURST_DATA,
                                                   update_type: str = UPDATE_TYPE_IMEI) -> tuple[str, str]:
        """
        構建 setSubscriberAccountStatus 的 SOAP Body
        
        根據 WSDL p.224
        用於暫停、恢復或註銷設備
        
        Args:
            imei: 設備 IMEI
            new_status: 新狀態（ACTIVE, SUSPENDED, DEACTIVATED）
            reason: 原因
            service_type: 服務類型
            update_type: 更新類型
            
        Returns:
            tuple: (action_name, soap_body)
        """
        action_name = 'setSubscriberAccountStatus'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        sp_account = self._safe_xml_value(self.sp_account)
        
        body = f'''        <tns:setSubscriberAccountStatus xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <serviceType>{service_type}</serviceType>
                <updateType>{update_type}</updateType>
                <value>{imei}</value>
                <newStatus>{new_status}</newStatus>
                <reason>{reason}</reason>
            </request>
        </tns:setSubscriberAccountStatus>'''
        
        return action_name, body
    
    def _send_soap_request(self, 
                          soap_action: str,
                          soap_body: str) -> str:
        """發送 SOAP 1.2 請求"""
        soap_envelope = self._build_soap_envelope(soap_body)
        
        headers = {
            'Content-Type': f'application/soap+xml; charset=utf-8; action="{soap_action}"',
            'Accept': 'application/soap+xml, text/xml'
        }
        
        try:
            print(f"\n{'='*60}")
            print(f"[IWS] SOAP Request Details:")
            print(f"{'='*60}")
            print(f"Endpoint: {self.endpoint}")
            print(f"Action: {soap_action}")
            print(f"Namespace: {self.IWS_NS}")
            print(f"Username: {self.username}")
            print(f"SP Account: {self.sp_account}")
            print(f"\n[IWS] Request Headers:")
            for key, value in headers.items():
                print(f"  {key}: {value}")
            print(f"\n[IWS] SOAP Envelope (first 800 chars):")
            print(soap_envelope[:800])
            print(f"{'='*60}\n")
            
            response = requests.post(
                self.endpoint,
                data=soap_envelope,
                headers=headers,
                timeout=self.timeout,
                verify=False
            )
            
            print(f"\n{'='*60}")
            print(f"[IWS] SOAP Response Details:")
            print(f"{'='*60}")
            print(f"Status Code: {response.status_code}")
            print(f"Reason: {response.reason}")
            
            print(f"\n[IWS] Response Headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
            
            print(f"\n[IWS] Response Body (first 1000 chars):")
            print(response.text[:1000])
            print(f"{'='*60}\n")
            
            if response.status_code != 200:
                error_details = []
                
                # 根據狀態碼提供更詳細的說明
                if response.status_code == 500:
                    error_details.append("⚠️  IWS 伺服器錯誤 (HTTP 500)")
                    error_details.append("")
                    error_details.append("這是立即回應的錯誤，不是等待中。")
                    error_details.append("")
                    error_details.append("可能原因：")
                    error_details.append("1. 帳號狀態不允許此操作")
                    error_details.append("2. IMEI 不存在或無效")
                    error_details.append("3. 請求參數不符合 IWS 要求")
                    error_details.append("")
                    error_details.append("技術詳情：")
                    error_details.append(f"  端點: {self.endpoint}")
                    error_details.append(f"  操作: {soap_action}")
                    error_details.append(f"  狀態碼: {response.status_code}")
                else:
                    error_details.append(f"HTTP {response.status_code}: {response.reason}")
                    error_details.append(f"Endpoint: {self.endpoint}")
                    error_details.append(f"Action: {soap_action}")
                
                if 'X-Error-Info' in response.headers:
                    error_details.append(f"X-Error-Info: {response.headers['X-Error-Info']}")
                if 'X-Error-Code' in response.headers:
                    error_details.append(f"X-Error-Code: {response.headers['X-Error-Code']}")
                
                # 嘗試從回應中提取更多錯誤資訊
                try:
                    root = ET.fromstring(response.text)
                    fault = root.find('.//soap:Fault', self.NAMESPACES) or root.find('.//Fault')
                    if fault is not None:
                        faultstring = fault.find('.//faultstring')
                        if faultstring is not None and faultstring.text:
                            error_details.append("")
                            error_details.append(f"IWS 錯誤訊息: {faultstring.text}")
                except:
                    pass
                
                raise IWSException(
                    "\n".join(error_details),
                    error_code=str(response.status_code),
                    response_text=response.text
                )
            
            self._check_soap_fault(response.text)
            
            return response.text
            
        except requests.exceptions.Timeout:
            raise IWSException(f"Request timeout after {self.timeout} seconds")
        except requests.exceptions.ConnectionError as e:
            raise IWSException(f"Connection error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise IWSException(f"Request failed: {str(e)}")
    
    def _check_soap_fault(self, xml_response: str):
        """檢查 SOAP 1.2 Fault"""
        try:
            root = ET.fromstring(xml_response)
            
            fault = root.find('.//soap:Fault', self.NAMESPACES)
            if fault is None:
                fault = root.find('.//Fault')
            
            if fault is not None:
                code_elem = fault.find('soap:Code/soap:Value', self.NAMESPACES)
                if code_elem is None:
                    code_elem = fault.find('.//Code/Value')
                if code_elem is None:
                    code_elem = fault.find('.//faultcode')
                
                faultcode = code_elem.text if code_elem is not None else 'Unknown'
                
                reason_elem = fault.find('soap:Reason/soap:Text', self.NAMESPACES)
                if reason_elem is None:
                    reason_elem = fault.find('.//Reason/Text')
                if reason_elem is None:
                    reason_elem = fault.find('.//faultstring')
                
                faultstring = reason_elem.text if reason_elem is not None else 'Unknown error'
                
                detail = fault.find('soap:Detail', self.NAMESPACES)
                if detail is None:
                    detail = fault.find('.//Detail')
                if detail is None:
                    detail = fault.find('.//detail')
                
                detail_text = ''
                if detail is not None:
                    detail_text = ' | '.join(
                        elem.text for elem in detail.iter() 
                        if elem.text and elem.text.strip()
                    )
                
                error_msg = f"SOAP Fault: [{faultcode}] {faultstring}"
                if detail_text:
                    error_msg += f" | Details: {detail_text}"
                
                raise IWSException(
                    error_msg,
                    error_code=faultcode,
                    response_text=xml_response
                )
                
        except ET.ParseError as e:
            raise IWSException(
                f"Invalid XML response: {str(e)}",
                response_text=xml_response
            )
    
    def _extract_transaction_id(self, xml_response: str) -> Optional[str]:
        """從回應中提取 Transaction ID"""
        try:
            root = ET.fromstring(xml_response)
            
            paths = [
                './/transactionId',
                './/TransactionId',
                './/{http://www.iridium.com/}transactionId',
                './/accountUpdateResponse/transactionId',
                './/response/transactionId'
            ]
            
            for path in paths:
                elem = root.find(path)
                if elem is not None and elem.text:
                    return elem.text.strip()
            
            return None
            
        except ET.ParseError:
            return None
    
    def _parse_sbd_bundles(self, xml_response: str) -> List[Dict]:
        """
        解析 getSBDBundles 回應
        
        Returns:
            List[Dict]: SBD 方案列表
        """
        try:
            root = ET.fromstring(xml_response)
            bundles = []
            
            # 尋找所有 bundle 元素（可能有多種類型）
            bundle_elements = root.findall('.//bundle')
            if not bundle_elements:
                bundle_elements = root.findall('.//{http://www.iridium.com/}bundle')
            
            for bundle_elem in bundle_elements:
                bundle = {}
                
                # 提取各個欄位
                for child in bundle_elem:
                    tag = child.tag.split('}')[-1]  # 移除命名空間
                    bundle[tag] = child.text
                
                bundles.append(bundle)
            
            return bundles
            
        except ET.ParseError as e:
            print(f"[IWS] Failed to parse SBD bundles: {e}")
            return []
    
    def _parse_account_search(self, xml_response: str, target_imei: Optional[str] = None) -> Optional[Dict]:
        """
        解析 accountSearch 回應，提取訂閱者資訊
        
        accountSearch 返回訂閱者列表，需要遍歷找到匹配的 IMEI
        
        Args:
            xml_response: SOAP 響應 XML
            target_imei: 要查找的 IMEI（可選，如果提供則匹配 IMEI）
            
        Returns:
            Optional[Dict]: 訂閱者資訊 {accountNumber, status, planName} 或 None
        """
        try:
            root = ET.fromstring(xml_response)
            
            # 查找所有 subscriber 元素
            subscribers = root.findall('.//subscriber')
            
            if not subscribers:
                # 嘗試其他命名空間
                subscribers = root.findall('.//{http://www.iridium.com/}subscriber')
            
            if not subscribers:
                print(f"[IWS] No subscribers found in response")
                return None
            
            print(f"[IWS] Found {len(subscribers)} subscriber(s)")
            
            # 如果提供了 target_imei，查找匹配的訂閱者
            if target_imei:
                for subscriber in subscribers:
                    # 查找此訂閱者的 IMEI
                    imei_elem = subscriber.find('.//imei')
                    if imei_elem is None:
                        imei_elem = subscriber.find('.//{http://www.iridium.com/}imei')
                    
                    if imei_elem is not None and imei_elem.text:
                        imei_value = imei_elem.text.strip()
                        print(f"[IWS] Checking subscriber with IMEI: {imei_value}")
                        
                        if imei_value == target_imei:
                            # 找到匹配的 IMEI，提取訂閱者資訊
                            account_elem = subscriber.find('.//accountNumber')
                            if account_elem is None:
                                account_elem = subscriber.find('.//{http://www.iridium.com/}accountNumber')
                            
                            status_elem = subscriber.find('.//accountStatus')
                            if status_elem is None:
                                status_elem = subscriber.find('.//{http://www.iridium.com/}accountStatus')
                            
                            plan_elem = subscriber.find('.//planName')
                            if plan_elem is None:
                                plan_elem = subscriber.find('.//{http://www.iridium.com/}planName')
                            
                            # 扩展解析：添加更多字段
                            activation_elem = subscriber.find('.//activationDate')
                            if activation_elem is None:
                                activation_elem = subscriber.find('.//{http://www.iridium.com/}activationDate')
                            
                            iccid_elem = subscriber.find('.//iccid')
                            if iccid_elem is None:
                                iccid_elem = subscriber.find('.//{http://www.iridium.com/}iccid')
                            
                            sp_ref_elem = subscriber.find('.//spReference')
                            if sp_ref_elem is None:
                                sp_ref_elem = subscriber.find('.//{http://www.iridium.com/}spReference')
                            
                            account_type_elem = subscriber.find('.//accountType')
                            if account_type_elem is None:
                                account_type_elem = subscriber.find('.//{http://www.iridium.com/}accountType')
                            
                            if account_elem is not None and account_elem.text:
                                account_number = account_elem.text.strip()
                                status = status_elem.text.strip() if status_elem is not None and status_elem.text else 'UNKNOWN'
                                plan_name = plan_elem.text.strip() if plan_elem is not None and plan_elem.text else None
                                
                                print(f"[IWS] Found matching subscriber: {account_number}")
                                print(f"[IWS] Status: {status}")
                                if plan_name:
                                    print(f"[IWS] Plan: {plan_name}")
                                
                                return {
                                    'accountNumber': account_number,
                                    'status': status,
                                    'planName': plan_name,
                                    'activationDate': activation_elem.text.strip() if activation_elem is not None and activation_elem.text else None,
                                    'iccid': iccid_elem.text.strip() if iccid_elem is not None and iccid_elem.text else None,
                                    'spReference': sp_ref_elem.text.strip() if sp_ref_elem is not None and sp_ref_elem.text else None,
                                    'accountType': account_type_elem.text.strip() if account_type_elem is not None and account_type_elem.text else None
                                }
                
                print(f"[IWS] No subscriber found with IMEI: {target_imei}")
                return None
            
            # 如果沒有提供 target_imei，返回第一個訂閱者的資訊
            first_subscriber = subscribers[0]
            account_elem = first_subscriber.find('.//accountNumber')
            if account_elem is None:
                account_elem = first_subscriber.find('.//{http://www.iridium.com/}accountNumber')
            
            status_elem = first_subscriber.find('.//accountStatus')
            if status_elem is None:
                status_elem = first_subscriber.find('.//{http://www.iridium.com/}accountStatus')
            
            plan_elem = first_subscriber.find('.//planName')
            if plan_elem is None:
                plan_elem = first_subscriber.find('.//{http://www.iridium.com/}planName')
            
            if account_elem is not None and account_elem.text:
                return {
                    'accountNumber': account_elem.text.strip(),
                    'status': status_elem.text.strip() if status_elem is not None and status_elem.text else 'UNKNOWN',
                    'planName': plan_elem.text.strip() if plan_elem is not None and plan_elem.text else None
                }
            
            return None
            
        except ET.ParseError as e:
            print(f"[IWS] Failed to parse account search: {e}")
            return None
    
    def _parse_validate_device_string(self, xml_response: str) -> Dict:
        """
        解析 validateDeviceString 回應
        
        Returns:
            Dict: 驗證結果
        """
        try:
            root = ET.fromstring(xml_response)
            
            result = {
                'valid': False,
                'device_string': None,
                'reason': None,
                'safety_data_capable': False
            }
            
            # 提取 valid
            valid_elem = root.find('.//valid')
            if valid_elem is None:
                valid_elem = root.find('.//{http://www.iridium.com/}valid')
            if valid_elem is not None and valid_elem.text:
                result['valid'] = valid_elem.text.lower() == 'true'
            
            # 提取 deviceString
            device_string_elem = root.find('.//deviceString')
            if device_string_elem is None:
                device_string_elem = root.find('.//{http://www.iridium.com/}deviceString')
            if device_string_elem is not None and device_string_elem.text:
                result['device_string'] = device_string_elem.text.strip()
            
            # 提取 reason（如果無效）
            reason_elem = root.find('.//reason')
            if reason_elem is None:
                reason_elem = root.find('.//{http://www.iridium.com/}reason')
            if reason_elem is not None and reason_elem.text:
                result['reason'] = reason_elem.text.strip()
            
            # 提取 safetyDataCapable
            safety_elem = root.find('.//safetyDataCapable')
            if safety_elem is None:
                safety_elem = root.find('.//{http://www.iridium.com/}safetyDataCapable')
            if safety_elem is not None and safety_elem.text:
                result['safety_data_capable'] = safety_elem.text.lower() == 'true'
            
            return result
            
        except ET.ParseError as e:
            print(f"[IWS] Failed to parse validate device string: {e}")
            return {
                'valid': False,
                'device_string': None,
                'reason': f"Parse error: {str(e)}",
                'safety_data_capable': False
            }
    
    # ==================== 公開 API 方法 ====================
    
    def validate_device_string(self,
                               device_string: str,
                               device_string_type: str = "IMEI",
                               validate_state: bool = True) -> Dict:
        """
        驗證設備字符串的有效性、歸屬權和狀態
        
        使用 validateDeviceString 方法（根據 WSDL p.236-237）
        
        **重要**：在啟動設備前建議使用此方法驗證：
        1. 設備是否屬於您的 SP 帳戶（Device Pool）
        2. 設備格式是否正確
        3. 設備狀態是否適合操作（如果 validate_state=True）
        
        Args:
            device_string: 設備字符串（如 IMEI）
            device_string_type: 設備類型（IMEI, SIM, etc.）
            validate_state: 是否檢查設備狀態
                          true = 檢查設備是否被其他合約使用或處於不可用狀態
                          false = 只檢查格式
                          
        Returns:
            Dict: 驗證結果
                {
                    'success': True,
                    'valid': True/False,
                    'device_string': '...',
                    'reason': '...' (如果無效),
                    'safety_data_capable': True/False,
                    'timestamp': '...'
                }
        """
        print("\n" + "="*60)
        print("🔍 [IWS] Validating device string...")
        print("="*60)
        print(f"Device String: {device_string}")
        print(f"Type: {device_string_type}")
        print(f"Validate State: {validate_state}")
        print("="*60 + "\n")
        
        try:
            action_name, soap_body = self._build_validate_device_string_body(
                device_string=device_string,
                device_string_type=device_string_type,
                validate_state=validate_state
            )
            
            response_xml = self._send_soap_request(
                soap_action=action_name,
                soap_body=soap_body
            )
            
            validation_result = self._parse_validate_device_string(response_xml)
            
            print("\n" + "="*60)
            if validation_result['valid']:
                print(f"✅ Device is valid")
            else:
                print(f"❌ Device is invalid")
                if validation_result['reason']:
                    print(f"Reason: {validation_result['reason']}")
            print("="*60 + "\n")
            
            return {
                'success': True,
                **validation_result,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except IWSException as e:
            print("\n" + "="*60)
            print("❌ Validation failed")
            print("="*60)
            print(f"Error: {str(e)}")
            print("="*60 + "\n")
            raise
    
    def search_account(self, imei: str) -> Dict:
        """
        用 IMEI 搜尋訂閱者帳號
        
        使用 accountSearch 方法（根據 WSDL p.62）
        
        Args:
            imei: 設備 IMEI
            
        Returns:
            Dict: 搜尋結果，包含 subscriberAccountNumber
        """
        self._validate_imei(imei)
        
        print("\n" + "="*60)
        print("🔍 [IWS] Searching account...")
        print("="*60)
        print(f"IMEI: {imei}")
        print("="*60 + "\n")
        
        try:
            action_name, soap_body = self._build_account_search_body(imei)
            
            response_xml = self._send_soap_request(
                soap_action=action_name,
                soap_body=soap_body
            )
            
            subscriber_info = self._parse_account_search(response_xml, target_imei=imei)
            
            if subscriber_info:
                print("\n" + "="*60)
                print(f"✅ Account found: {subscriber_info['accountNumber']}")
                print(f"   Status: {subscriber_info['status']}")
                if subscriber_info.get('planName'):
                    print(f"   Plan: {subscriber_info['planName']}")
                print("="*60 + "\n")
                
                return {
                    'success': True,
                    'found': True,
                    'subscriber_account_number': subscriber_info['accountNumber'],
                    'status': subscriber_info['status'],
                    'plan_name': subscriber_info.get('planName'),
                    'activation_date': subscriber_info.get('activationDate'),
                    'iccid': subscriber_info.get('iccid'),
                    'sp_reference': subscriber_info.get('spReference'),
                    'account_type': subscriber_info.get('accountType'),
                    'imei': imei,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                print("\n" + "="*60)
                print("❌ Account not found")
                print("="*60 + "\n")
                
                return {
                    'success': True,
                    'found': False,
                    'subscriber_account_number': None,
                    'status': None,
                    'plan_name': None,
                    'imei': imei,
                    'message': 'Account not found - device may not be activated',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
        except IWSException as e:
            print("\n" + "="*60)
            print("❌ Search failed")
            print("="*60)
            print(f"Error: {str(e)}")
            print("="*60 + "\n")
            raise
    
    def check_connection(self) -> Dict:
        """測試 IWS 連線"""
        print("\n" + "="*60)
        print("🔍 [DIAGNOSTIC] Starting connection test...")
        print("="*60)
        print("Method: getSystemStatus")
        print("Signature: HMAC-SHA1 + Base64 ✓")
        print("WSDL: v25.1.0.1 ✓")
        print("="*60 + "\n")
        
        try:
            action_name, soap_body = self._build_get_system_status_body()
            
            response_xml = self._send_soap_request(
                soap_action=action_name,
                soap_body=soap_body
            )
            
            print("\n" + "="*60)
            print("✅ [DIAGNOSTIC] Connection test PASSED!")
            print("="*60)
            print("Authentication: ✓")
            print("Signature: ✓ (HMAC-SHA1 + Base64)")
            print("Timestamp: ✓")
            print("Protocol: ✓")
            print("="*60 + "\n")
            
            return {
                'success': True,
                'message': 'IWS connection successful',
                'signature_algorithm': 'HMAC-SHA1 + Base64',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except IWSException as e:
            print("\n" + "="*60)
            print("❌ [DIAGNOSTIC] Connection test FAILED!")
            print("="*60)
            print(f"Error: {str(e)}")
            print("="*60 + "\n")
            raise
    
    def get_sbd_bundles(self, 
                       from_bundle_id: str = "0",
                       for_activate: bool = True,
                       model_id: Optional[str] = None) -> Dict:
        """
        查詢可用的 SBD 方案
        
        根據 WSDL p.161-162
        
        Args:
            from_bundle_id: 現有 bundle ID（新啟用用 "0"）
            for_activate: 是否為新啟用（True=新啟用, False=更新現有）
            model_id: 可選的設備型號 ID
            
        Returns:
            Dict: 包含方案列表的結果
        """
        print("\n" + "="*60)
        print("📋 [IWS] Fetching SBD bundles...")
        print("="*60)
        print(f"From Bundle ID: {from_bundle_id}")
        print(f"For Activate: {for_activate}")
        if model_id:
            print(f"Model ID: {model_id}")
        print("="*60 + "\n")
        
        try:
            action_name, soap_body = self._build_get_sbd_bundles_body(
                from_bundle_id=from_bundle_id,
                for_activate=for_activate,
                model_id=model_id
            )
            
            response_xml = self._send_soap_request(
                soap_action=action_name,
                soap_body=soap_body
            )
            
            bundles = self._parse_sbd_bundles(response_xml)
            
            print("\n" + "="*60)
            print(f"✅ Found {len(bundles)} SBD bundle(s)")
            print("="*60)
            for i, bundle in enumerate(bundles, 1):
                print(f"\nBundle {i}:")
                for key, value in bundle.items():
                    print(f"  {key}: {value}")
            print("="*60 + "\n")
            
            return {
                'success': True,
                'bundles': bundles,
                'count': len(bundles),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except IWSException as e:
            print("\n" + "="*60)
            print("❌ Failed to fetch SBD bundles")
            print("="*60)
            print(f"Error: {str(e)}")
            print("="*60 + "\n")
            raise
    
    def update_subscriber_plan(self,
                              imei: str,
                              new_plan_code: str,
                              lrit_flagstate: str = "",
                              ring_alerts_flag: bool = False) -> Dict:
        """
        变更設備资费方案（符合 IWS 開發規範 v4.0）
        
        正确流程（根据 IWS 官方文件）：
        1. getSBDBundles - 查詢可用方案
        2. getSubscriberAccount - 取得目前狀態  
        3. 檢查 PENDING 狀態
        4. accountUpdate - 執行变更
        5. 返回 TransactionID 用于追踪
        
        Args:
            imei: 設備 IMEI
            new_plan_code: 新方案代码（如 "SBD12", "SBD0", "SBD17", "SBD30"）
            lrit_flagstate: LRIT Flag State（3字符或空字符串）
            ring_alerts_flag: Ring Alerts Flag
            
        Returns:
            Dict: 操作結果，包含 transaction_id
            
        Raises:
            IWSException: 当方案不可用、帳號PENDING或其他錯誤时
        """
        self._validate_imei(imei)
        
        print("\n" + "="*60)
        print("💱 [IWS] 变更资费方案（符合 IWS 開發規範）")
        print("="*60)
        print(f"IMEI: {imei}")
        print(f"目标方案代码: {new_plan_code}")
        print(f"LRIT Flagstate: '{lrit_flagstate}'")
        print(f"Ring Alerts: {ring_alerts_flag}")
        print("="*60 + "\n")
        
        try:
            # ========== 步驟 1: 查詢訂閱者帳號（使用 accountSearch）==========
            print("[步驟 1/4] 查詢訂閱者帳號...")
            search_action, search_body = self._build_account_search_body(imei)
            
            search_response = self._send_soap_request(
                soap_action=search_action,
                soap_body=search_body
            )
            
            subscriber_info = self._parse_account_search(search_response, target_imei=imei)
            
            if not subscriber_info:
                raise IWSException(
                    f"未找到 IMEI {imei} 的帳號。"
                    f"設備可能未在 IWS 系統中啟用。"
                )
            
            subscriber_account_number = subscriber_info['accountNumber']
            current_status = subscriber_info.get('status', 'UNKNOWN')
            current_plan_name = subscriber_info.get('planName', 'Unknown')
            
            print(f"✅ 找到帳號: {subscriber_account_number}")
            print(f"   當前狀態: {current_status}")
            print(f"   當前方案: {current_plan_name}")
            
            # ========== 步驟 2: 檢查 PENDING 狀態 ==========
            print("\n[步驟 2/4] 檢查帳號狀態...")
            if current_status == 'PENDING':
                raise IWSException(
                    "❌ 帳號有正在處理的訂單（PENDING 狀態）\n\n"
                    "根據 IWS 規範，PENDING 狀態下禁止任何更新操作。\n"
                    "必須等待當前訂單完成後才能變更資費。\n\n"
                    "建議：\n"
                    "• 等待 5-15 分鐘後重試\n"
                    "• 使用 getQueueEntry 查詢訂單進度\n"
                    "• 聯絡技術支援了解訂單詳情"
                )
            
            print(f"✅ 帳號狀態正常（{current_status}），可以更新")
            
            # ========== 步驟 3: 查詢可用方案並驗證 ==========
            print("\n[步驟 3/4] 查詢可用資費方案...")
            
            # ✅ 先查詢所有可用方案（用 fromBundleId="0" 獲取全部）
            print("[IWS] 查詢所有可用方案...")
            bundles_result = self.get_sbd_bundles(
                from_bundle_id="0",  # 先用 0 獲取所有方案
                for_activate=False
            )
            
            if not bundles_result.get('success'):
                raise IWSException("無法查詢可用資費方案")
            
            # ✅ 建立方案名稱到 bundle ID 的映射
            plan_name_to_id = {}
            plan_id_to_name = {}
            
            for bundle in bundles_result['bundles']:
                bundle_name = (bundle.get('name') or 
                              bundle.get('bundleCode') or 
                              bundle.get('code'))
                bundle_id = (bundle.get('id') or 
                            bundle.get('bundleId'))
                
                if bundle_name and bundle_id:
                    plan_name_to_id[bundle_name] = bundle_id
                    plan_id_to_name[bundle_id] = bundle_name
            
            print(f"✅ 查詢到 {len(plan_name_to_id)} 個可用方案")
            
            # ✅ 從當前方案名稱反查 bundle ID
            current_bundle_id = None
            if current_plan_name and current_plan_name in plan_name_to_id:
                current_bundle_id = plan_name_to_id[current_plan_name]
                print(f"[IWS] 當前方案 '{current_plan_name}' 的 Bundle ID: {current_bundle_id}")
            else:
                print(f"⚠️ 警告：無法從方案名稱 '{current_plan_name}' 反查 bundle ID")
                print(f"   將使用 fromBundleId='0'")
                current_bundle_id = "0"
            
            # ✅ 使用實際的 fromBundleId 重新查詢（確保獲得合法的升降級路徑）
            print(f"[IWS] 使用 fromBundleId={current_bundle_id} 查詢可升降級方案...")
            bundles_result = self.get_sbd_bundles(
                from_bundle_id=current_bundle_id,
                for_activate=False
            )
            
            if not bundles_result.get('success'):
                print("⚠️ 无法查詢可用方案，尝试使用提供的方案代码...")
                # 如果查詢失敗，直接使用提供的代码（向后兼容）
                target_bundle_id = new_plan_code
            else:
                # 提取方案代码和 ID 映射
                bundle_map = {}
                bundle_map_with_space = {}  # 處理带空格的方案名
                
                for bundle in bundles_result['bundles']:
                    # 尝试多个可能的字段名
                    bundle_name = (bundle.get('name') or 
                                  bundle.get('bundleCode') or 
                                  bundle.get('code') or 
                                  bundle.get('bundleName'))
                    
                    bundle_id = (bundle.get('id') or 
                                bundle.get('bundleId') or 
                                bundle.get('planId'))
                    
                    if bundle_name and bundle_id:
                        # 同时存储带空格和不带空格的版本
                        bundle_map[bundle_name] = bundle_id
                        bundle_map_with_space[bundle_name.replace(' ', '')] = bundle_id
                
                available_plans = list(bundle_map.keys())
                print(f"✅ 可用方案: {available_plans}")
                
                # 查找目标方案（先尝试精确匹配，再尝试去空格匹配）
                target_bundle_id = None
                
                # 尝试 1: 精确匹配
                if new_plan_code in bundle_map:
                    target_bundle_id = bundle_map[new_plan_code]
                    print(f"✅ 精确匹配: {new_plan_code} → {target_bundle_id}")
                
                # 尝试 2: 去空格匹配（例如 "SBD30" 匹配 "SBD 30"）
                elif new_plan_code in bundle_map_with_space:
                    target_bundle_id = bundle_map_with_space[new_plan_code]
                    matched_name = [k for k, v in bundle_map.items() if v == target_bundle_id][0]
                    print(f"✅ 匹配成功（忽略空格）: {new_plan_code} → {matched_name} (ID: {target_bundle_id})")
                
                # 尝试 3: 如果提供的是完整的 bundle ID（纯数字）
                elif new_plan_code.isdigit() and new_plan_code in bundle_map.values():
                    target_bundle_id = new_plan_code
                    print(f"✅ 直接使用 bundle ID: {target_bundle_id}")
                
                else:
                    print(f"⚠️ 警告：方案 {new_plan_code} 不在可用列表中")
                    print(f"   可用方案: {available_plans}")
                    print(f"   将尝试直接使用提供的值: {new_plan_code}")
                    target_bundle_id = new_plan_code
            
            # ========== 步驟 4: 執行更新 ==========
            print("\n[步驟 4/6] 獲取完整帳戶資訊...")
            
            # ✅ 關鍵步驟：使用 getSubscriberAccount 獲取完整的當前設定
            # 這樣才能建立包含所有必要欄位的 accountUpdate 請求
            try:
                account_info = self.get_subscriber_account(subscriber_account_number)
                print(f"✅ 獲取到完整帳戶資訊")
                print(f"   當前 Bundle ID: {account_info.get('bundle_id')}")
                print(f"   Demo and Trial: {account_info.get('demo_and_trial')}")
                print(f"   Promo: {account_info.get('promo')}")
                print(f"   Destinations: {len(account_info.get('destinations', []))} 個")
                print(f"   MT Filters: {len(account_info.get('mt_filters', []))} 個")
            except Exception as e:
                print(f"⚠️  警告：無法獲取完整帳戶資訊: {e}")
                print(f"   將使用簡化版本（可能失敗）")
                account_info = None
            
            # ========== 步驟 5: 執行資費變更 ==========
            print("\n[步驟 5/6] 執行資費變更...")
            
            # ✅ 根據 Iridium 官方確認（2025-12-27）：
            # accountUpdate 必須使用數字 ID（如 763925351），不能用字串代碼
            # 必須包含完整的帳戶物件（包括 deliveryDetails, mtFilters 等）
            
            # 從映射表獲取目標方案的數字 ID
            # bundle_map 已在步驟 3 建立
            if new_plan_code in bundle_map:
                target_bundle_id = bundle_map[new_plan_code]
                print(f"[IWS] 使用方案映射: '{new_plan_code}' → Bundle ID: {target_bundle_id}")
            else:
                # 如果找不到精確匹配，嘗試模糊匹配
                matched = False
                for plan_name, bundle_id in bundle_map.items():
                    if new_plan_code.replace(' ', '').upper() in plan_name.replace(' ', '').upper():
                        target_bundle_id = bundle_id
                        print(f"[IWS] 使用模糊匹配: '{new_plan_code}' → '{plan_name}' → Bundle ID: {target_bundle_id}")
                        matched = True
                        break
                
                if not matched:
                    # 如果還是找不到，直接使用提供的值（可能已經是 bundle ID）
                    target_bundle_id = new_plan_code
                    print(f"[IWS] ⚠️ 未找到方案映射，直接使用提供的值: {target_bundle_id}")
            
            # 選擇使用哪個方法建立 SOAP body
            if account_info:
                # ✅ 使用完整版本（包含所有必要欄位）
                print(f"[IWS] 使用完整的帳戶物件建立請求")
                action_name, soap_body = self._build_complete_account_update_body(
                    account_info=account_info,
                    new_bundle_id=target_bundle_id,
                    lrit_flagstate=lrit_flagstate,
                    ring_alerts_flag=ring_alerts_flag
                )
            else:
                # ⚠️ 回退到簡化版本（可能失敗）
                print(f"[IWS] ⚠️ 使用簡化版本建立請求（可能失敗）")
                action_name, soap_body = self._build_account_update_body(
                    imei=imei,
                    subscriber_account_number=subscriber_account_number,
                    new_plan_id=target_bundle_id,
                    lrit_flagstate=lrit_flagstate,
                    ring_alerts_flag=ring_alerts_flag
                )
            
            print(f"[IWS] 提交 accountUpdate 請求...")
            response_xml = self._send_soap_request(
                soap_action=action_name,
                soap_body=soap_body
            )
            
            # ========== 步驟 6: 解析結果 ==========
            print("\n[步驟 6/6] 解析回應...")
            transaction_id = self._extract_transaction_id(response_xml)
            
            print("\n" + "="*60)
            print("✅ 资费变更請求已提交")
            print("="*60)
            print(f"Transaction ID: {transaction_id or 'N/A'}")
            print(f"目前方案: {current_plan_name}")
            print(f"目标方案: {new_plan_code}")
            print(f"Bundle ID: {target_bundle_id}")
            print("")
            print("⚠️ 重要提示：")
            print("• 变更不会立即生效")
            print("• 帳號狀態会变为 PENDING")
            print("• 處理通常需要 5-15 分鐘")
            print("• 使用 getQueueEntry 追踪進度")
            print("• 完成后狀態会变回 ACTIVE")
            print("="*60 + "\n")
            
            return {
                'success': True,
                'transaction_id': transaction_id or 'N/A',
                'message': '资费变更請求已提交',
                'imei': imei,
                'subscriber_account_number': subscriber_account_number,
                'current_plan': current_plan_name,  # ✅ 使用正確的變數名稱
                'target_plan_code': new_plan_code,
                'target_bundle_id': target_bundle_id,
                'status': 'PENDING',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except IWSException:
            raise
        except Exception as e:
            raise IWSException(f"资费变更失敗: {str(e)}")
    
    def suspend_subscriber(self, 
                          imei: str,
                          reason: str = '系統自動暫停') -> Dict:
        """
        暫停 SBD 設備（帶狀態驗證）
        
        使用 setSubscriberAccountStatus（根據 WSDL p.224）
        
        根據實際測試發現：
        - IWS 可能返回 HTTP 500，但操作實際成功
        - 因此需要查詢實際狀態來驗證結果
        
        Args:
            imei: 設備 IMEI
            reason: 暫停原因
            
        Returns:
            Dict: 操作結果
        """
        self._validate_imei(imei)
        
        print("\n" + "="*60)
        print("⏸️  [IWS] Suspending subscriber...")
        print("="*60)
        print(f"IMEI: {imei}")
        print(f"Reason: {reason}")
        print("="*60 + "\n")
        
        # 先查詢帳號號碼（用於後續驗證）
        try:
            print("[IWS] 查詢帳號資訊...")
            search_action, search_body = self._build_account_search_body(imei)
            search_response = self._send_soap_request(
                soap_action=search_action,
                soap_body=search_body
            )
            subscriber_info = self._parse_account_search(search_response, target_imei=imei)
            
            if not subscriber_info:
                raise IWSException(f"未找到 IMEI {imei} 的帳號")
            
            account_number = subscriber_info['accountNumber']
            print(f"[IWS] 找到帳號: {account_number}")
        except Exception as e:
            print(f"⚠️  無法查詢帳號資訊: {e}")
            account_number = None
        
        # 執行暫停操作
        http_success = False
        error_message = None
        
        try:
            action_name, soap_body = self._build_set_subscriber_account_status_body(
                imei=imei,
                new_status=self.ACCOUNT_STATUS_SUSPENDED,
                reason=reason
            )
            
            response_xml = self._send_soap_request(
                soap_action=action_name,
                soap_body=soap_body
            )
            
            http_success = True
            print("[IWS] HTTP 回應: 200 OK")
            
        except IWSException as e:
            # 收到 HTTP 錯誤（可能是 500）
            # 但操作可能實際上成功了
            http_success = False
            error_message = str(e)
            print(f"⚠️  收到錯誤回應: {error_message}")
            
            if account_number:
                print("[IWS] 正在驗證實際狀態...")
            else:
                # 沒有帳號號碼，無法驗證
                raise
        
        # ✅ 關鍵：驗證實際狀態
        if account_number:
            try:
                import time
                # 給 IWS 一點時間處理（如果需要）
                if not http_success:
                    print("[IWS] 等待 2 秒後驗證...")
                    time.sleep(2)
                
                # 查詢實際狀態
                account_info = self.get_subscriber_account(account_number)
                actual_status = account_info.get('status')
                
                print(f"[IWS] 驗證結果: 實際狀態 = {actual_status}")
                
                if actual_status == self.ACCOUNT_STATUS_SUSPENDED:
                    # ✅ 實際上成功了！
                    print("\n" + "="*60)
                    print("✅ Subscriber suspended successfully (verified)")
                    print("="*60)
                    if not http_success:
                        print("⚠️  注意：HTTP 回應錯誤，但操作實際成功")
                    print("="*60 + "\n")
                    
                    return {
                        'success': True,
                        'message': 'Subscriber suspended successfully',
                        'imei': imei,
                        'new_status': self.ACCOUNT_STATUS_SUSPENDED,
                        'reason': reason,
                        'verification': 'confirmed',
                        'http_success': http_success,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                
                else:
                    # ❌ 真的失敗了
                    raise IWSException(
                        f"暫停操作失敗。實際狀態: {actual_status}（預期: SUSPENDED）\n"
                        f"原始錯誤: {error_message or 'N/A'}"
                    )
                    
            except IWSException:
                raise
            except Exception as e:
                print(f"⚠️  無法驗證狀態: {e}")
                # 如果 HTTP 成功但無法驗證，假設成功
                if http_success:
                    print("[IWS] HTTP 成功，假設操作成功")
                    return {
                        'success': True,
                        'message': 'Subscriber suspended (unverified)',
                        'imei': imei,
                        'new_status': self.ACCOUNT_STATUS_SUSPENDED,
                        'reason': reason,
                        'verification': 'unverified',
                        'http_success': True,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                else:
                    # HTTP 失敗且無法驗證
                    raise IWSException(
                        f"暫停操作失敗且無法驗證狀態\n"
                        f"錯誤: {error_message}"
                    )
        
        else:
            # 沒有帳號號碼，只能依賴 HTTP 回應
            if http_success:
                print("\n" + "="*60)
                print("✅ Subscriber suspended successfully")
                print("="*60 + "\n")
                
                return {
                    'success': True,
                    'message': 'Subscriber suspended successfully',
                    'imei': imei,
                    'new_status': self.ACCOUNT_STATUS_SUSPENDED,
                    'reason': reason,
                    'verification': 'http_only',
                    'http_success': True,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                raise
    
    def resume_subscriber(self, 
                         imei: str,
                         reason: str = '系統自動恢復') -> Dict:
        """
        恢復 SBD 設備（帶狀態驗證）
        
        使用 setSubscriberAccountStatus（根據 WSDL p.224）
        
        根據實際測試發現：
        - IWS 可能返回 HTTP 500，但操作實際成功
        - 因此需要查詢實際狀態來驗證結果
        
        Args:
            imei: 設備 IMEI
            reason: 恢復原因
            
        Returns:
            Dict: 操作結果
        """
        self._validate_imei(imei)
        
        print("\n" + "="*60)
        print("▶️  [IWS] Resuming subscriber...")
        print("="*60)
        print(f"IMEI: {imei}")
        print(f"Reason: {reason}")
        print("="*60 + "\n")
        
        # 先查詢帳號號碼（用於後續驗證）
        try:
            print("[IWS] 查詢帳號資訊...")
            search_action, search_body = self._build_account_search_body(imei)
            search_response = self._send_soap_request(
                soap_action=search_action,
                soap_body=search_body
            )
            subscriber_info = self._parse_account_search(search_response, target_imei=imei)
            
            if not subscriber_info:
                raise IWSException(f"未找到 IMEI {imei} 的帳號")
            
            account_number = subscriber_info['accountNumber']
            print(f"[IWS] 找到帳號: {account_number}")
        except Exception as e:
            print(f"⚠️  無法查詢帳號資訊: {e}")
            account_number = None
        
        # 執行恢復操作
        http_success = False
        error_message = None
        
        try:
            action_name, soap_body = self._build_set_subscriber_account_status_body(
                imei=imei,
                new_status=self.ACCOUNT_STATUS_ACTIVE,
                reason=reason
            )
            
            response_xml = self._send_soap_request(
                soap_action=action_name,
                soap_body=soap_body
            )
            
            http_success = True
            print("[IWS] HTTP 回應: 200 OK")
            
        except IWSException as e:
            http_success = False
            error_message = str(e)
            print(f"⚠️  收到錯誤回應: {error_message}")
            
            if account_number:
                print("[IWS] 正在驗證實際狀態...")
            else:
                raise
        
        # ✅ 驗證實際狀態
        if account_number:
            try:
                import time
                if not http_success:
                    print("[IWS] 等待 2 秒後驗證...")
                    time.sleep(2)
                
                account_info = self.get_subscriber_account(account_number)
                actual_status = account_info.get('status')
                
                print(f"[IWS] 驗證結果: 實際狀態 = {actual_status}")
                
                if actual_status == self.ACCOUNT_STATUS_ACTIVE:
                    print("\n" + "="*60)
                    print("✅ Subscriber resumed successfully (verified)")
                    print("="*60)
                    if not http_success:
                        print("⚠️  注意：HTTP 回應錯誤，但操作實際成功")
                    print("="*60 + "\n")
                    
                    return {
                        'success': True,
                        'message': 'Subscriber resumed successfully',
                        'imei': imei,
                        'new_status': self.ACCOUNT_STATUS_ACTIVE,
                        'reason': reason,
                        'verification': 'confirmed',
                        'http_success': http_success,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                else:
                    raise IWSException(
                        f"恢復操作失敗。實際狀態: {actual_status}（預期: ACTIVE）\n"
                        f"原始錯誤: {error_message or 'N/A'}"
                    )
                    
            except IWSException:
                raise
            except Exception as e:
                print(f"⚠️  無法驗證狀態: {e}")
                if http_success:
                    return {
                        'success': True,
                        'message': 'Subscriber resumed (unverified)',
                        'imei': imei,
                        'new_status': self.ACCOUNT_STATUS_ACTIVE,
                        'reason': reason,
                        'verification': 'unverified',
                        'http_success': True,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                else:
                    raise IWSException(
                        f"恢復操作失敗且無法驗證狀態\n"
                        f"錯誤: {error_message}"
                    )
        else:
            if http_success:
                print("\n" + "="*60)
                print("✅ Subscriber resumed successfully")
                print("="*60 + "\n")
                
                return {
                    'success': True,
                    'message': 'Subscriber resumed successfully',
                    'imei': imei,
                    'new_status': self.ACCOUNT_STATUS_ACTIVE,
                    'reason': reason,
                    'verification': 'http_only',
                    'http_success': True,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                raise
    
    def deactivate_subscriber(self,
                             imei: str,
                             reason: str = '系統自動註銷') -> Dict:
        """
        註銷設備（帶狀態驗證）
        
        使用 setSubscriberAccountStatus（根據 WSDL p.224）
        
        根據實際測試發現：
        - IWS 可能返回 HTTP 500，但操作實際成功
        - 因此需要查詢實際狀態來驗證結果
        
        Args:
            imei: 設備 IMEI
            reason: 註銷原因
            
        Returns:
            Dict: 操作結果
        """
        self._validate_imei(imei)
        
        print("\n" + "="*60)
        print("🔴 [IWS] Deactivating subscriber...")
        print("="*60)
        print(f"IMEI: {imei}")
        print(f"Reason: {reason}")
        print("="*60 + "\n")
        
        # 先查詢帳號號碼（用於後續驗證）
        try:
            print("[IWS] 查詢帳號資訊...")
            search_action, search_body = self._build_account_search_body(imei)
            search_response = self._send_soap_request(
                soap_action=search_action,
                soap_body=search_body
            )
            subscriber_info = self._parse_account_search(search_response, target_imei=imei)
            
            if not subscriber_info:
                raise IWSException(f"未找到 IMEI {imei} 的帳號")
            
            account_number = subscriber_info['accountNumber']
            print(f"[IWS] 找到帳號: {account_number}")
        except Exception as e:
            print(f"⚠️  無法查詢帳號資訊: {e}")
            account_number = None
        
        # 執行註銷操作
        http_success = False
        error_message = None
        
        try:
            action_name, soap_body = self._build_set_subscriber_account_status_body(
                imei=imei,
                new_status=self.ACCOUNT_STATUS_DEACTIVATED,
                reason=reason
            )
            
            response_xml = self._send_soap_request(
                soap_action=action_name,
                soap_body=soap_body
            )
            
            http_success = True
            print("[IWS] HTTP 回應: 200 OK")
            
        except IWSException as e:
            http_success = False
            error_message = str(e)
            print(f"⚠️  收到錯誤回應: {error_message}")
            
            if account_number:
                print("[IWS] 正在驗證實際狀態...")
            else:
                raise
        
        # ✅ 驗證實際狀態
        if account_number:
            try:
                import time
                if not http_success:
                    print("[IWS] 等待 2 秒後驗證...")
                    time.sleep(2)
                
                account_info = self.get_subscriber_account(account_number)
                actual_status = account_info.get('status')
                
                print(f"[IWS] 驗證結果: 實際狀態 = {actual_status}")
                
                if actual_status == self.ACCOUNT_STATUS_DEACTIVATED:
                    print("\n" + "="*60)
                    print("✅ Subscriber deactivated successfully (verified)")
                    print("="*60)
                    if not http_success:
                        print("⚠️  注意：HTTP 回應錯誤，但操作實際成功")
                    print("="*60 + "\n")
                    
                    return {
                        'success': True,
                        'message': 'Subscriber deactivated successfully',
                        'imei': imei,
                        'new_status': self.ACCOUNT_STATUS_DEACTIVATED,
                        'reason': reason,
                        'verification': 'confirmed',
                        'http_success': http_success,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                else:
                    raise IWSException(
                        f"註銷操作失敗。實際狀態: {actual_status}（預期: DEACTIVATED）\n"
                        f"原始錯誤: {error_message or 'N/A'}"
                    )
                    
            except IWSException:
                raise
            except Exception as e:
                print(f"⚠️  無法驗證狀態: {e}")
                if http_success:
                    return {
                        'success': True,
                        'message': 'Subscriber deactivated (unverified)',
                        'imei': imei,
                        'new_status': self.ACCOUNT_STATUS_DEACTIVATED,
                        'reason': reason,
                        'verification': 'unverified',
                        'http_success': True,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                else:
                    raise IWSException(
                        f"註銷操作失敗且無法驗證狀態\n"
                        f"錯誤: {error_message}"
                    )
        else:
            if http_success:
                print("\n" + "="*60)
                print("✅ Subscriber deactivated successfully")
                print("="*60 + "\n")
                
                return {
                    'success': True,
                    'message': 'Subscriber deactivated successfully',
                    'imei': imei,
                    'new_status': self.ACCOUNT_STATUS_DEACTIVATED,
                    'reason': reason,
                    'verification': 'http_only',
                    'http_success': True,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                raise
    
    
    # ==================== 異步操作查詢方法 ====================
    
    def get_queue_entry(self, transaction_id: str) -> Dict:
        """
        查詢隊列條目狀態（標準異步狀態查詢）
        
        這是 IWS 推薦的標準方式來追蹤異步操作的處理進度。
        
        Args:
            transaction_id: 從 API 響應中獲取的 Transaction ID
            
        Returns:
            Dict: {
                'status': 'PENDING'/'WORKING'/'DONE'/'ERROR',
                'transaction_id': 交易ID,
                'operation': 操作類型,
                'timestamp': 時間戳
            }
        """
        print(f"\n[IWS] 查詢隊列狀態...")
        print(f"Transaction ID: {transaction_id}")
        
        action_name = 'getQueueEntry'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        
        body = f'''<tns:getQueueEntry xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{self.sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <queueEntryId>{transaction_id}</queueEntryId>
            </request>
        </tns:getQueueEntry>'''
        
        response_xml = self._send_soap_request(
            soap_action=action_name,
            soap_body=body
        )
        
        # 解析響應
        root = ET.fromstring(response_xml)
        
        # 嘗試多種路徑查找狀態
        status_elem = root.find('.//status')
        if status_elem is None:
            status_elem = root.find('.//{http://www.iridium.com/}status')
        
        operation_elem = root.find('.//operation')
        if operation_elem is None:
            operation_elem = root.find('.//{http://www.iridium.com/}operation')
        
        timestamp_elem = root.find('.//timestamp')
        if timestamp_elem is None:
            timestamp_elem = root.find('.//{http://www.iridium.com/}timestamp')
        
        status = status_elem.text if status_elem is not None else 'UNKNOWN'
        
        print(f"[IWS] 隊列狀態: {status}")
        
        return {
            'status': status,
            'transaction_id': transaction_id,
            'operation': operation_elem.text if operation_elem is not None else 'N/A',
            'timestamp': timestamp_elem.text if timestamp_elem is not None else 'N/A'
        }
    
    
    def get_iws_request(self, transaction_id: str) -> Dict:
        """
        獲取 IWS 請求詳情（用於錯誤診斷）
        
        當隊列狀態為 ERROR 時，使用此方法獲取詳細的錯誤資訊。
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Dict: {
                'transaction_id': 交易ID,
                'response': 原始SOAP響應,
                'error_message': 錯誤資訊,
                'error_code': 錯誤代碼
            }
        """
        print(f"\n[IWS] 獲取請求詳情...")
        print(f"Transaction ID: {transaction_id}")
        
        action_name = 'getIwsRequest'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        
        body = f'''<tns:getIwsRequest xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{self.sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <requestId>{transaction_id}</requestId>
            </request>
        </tns:getIwsRequest>'''
        
        response_xml = self._send_soap_request(
            soap_action=action_name,
            soap_body=body
        )
        
        # 解析響應
        root = ET.fromstring(response_xml)
        
        response_elem = root.find('.//response')
        if response_elem is None:
            response_elem = root.find('.//{http://www.iridium.com/}response')
        
        error_elem = root.find('.//errorMessage')
        if error_elem is None:
            error_elem = root.find('.//{http://www.iridium.com/}errorMessage')
        
        error_code_elem = root.find('.//errorCode')
        if error_code_elem is None:
            error_code_elem = root.find('.//{http://www.iridium.com/}errorCode')
        
        error_message = error_elem.text if error_elem is not None else 'No error message'
        
        print(f"[IWS] 錯誤資訊: {error_message}")
        
        return {
            'transaction_id': transaction_id,
            'response': response_elem.text if response_elem is not None else '',
            'error_message': error_message,
            'error_code': error_code_elem.text if error_code_elem is not None else 'N/A'
        }
    
    
    def get_subscriber_account(self, account_number: str) -> Dict:
        """
        獲取訂閱者帳戶詳細資訊（用於最終驗證）
        
        在異步操作完成後，使用此方法驗證帳戶的最終狀態。
        
        根據 SOAP Developer Guide 第 177 頁：
        請求參數必須使用 "accountNo"（不是 subscriberAccountNumber）
        
        Args:
            account_number: 訂閱者帳號（例如 SUB-49059741895）
            
        Returns:
            Dict: {
                'account_number': 帳號,
                'status': 帳戶狀態,
                'plan_name': 費率方案,
                'imei': IMEI,
                'activation_date': 啟用日期,
                'last_updated': 最後更新時間,
                'delivery_details': 完整的 delivery destinations,
                'mt_filters': 完整的 MT filters,
                'plan_details': 完整的 plan 物件
            }
        """
        print(f"\n[IWS] 獲取帳戶資訊...")
        print(f"Account: {account_number}")
        
        action_name = 'getSubscriberAccount'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        
        # ✅ 關鍵修正：使用 accountNo（不是 subscriberAccountNumber）
        body = f'''<tns:getSubscriberAccount xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{self.sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <accountNo>{account_number}</accountNo>
            </request>
        </tns:getSubscriberAccount>'''
        
        response_xml = self._send_soap_request(
            soap_action=action_name,
            soap_body=body
        )
        
        # 解析響應
        root = ET.fromstring(response_xml)
        
        # 查找帳戶資訊
        status_elem = root.find('.//accountStatus')
        if status_elem is None:
            status_elem = root.find('.//{http://www.iridium.com/}accountStatus')
        
        plan_elem = root.find('.//planName')
        if plan_elem is None:
            plan_elem = root.find('.//{http://www.iridium.com/}planName')
        
        imei_elem = root.find('.//imei')
        if imei_elem is None:
            imei_elem = root.find('.//{http://www.iridium.com/}imei')
        
        activation_elem = root.find('.//activationDate')
        if activation_elem is None:
            activation_elem = root.find('.//{http://www.iridium.com/}activationDate')
        
        updated_elem = root.find('.//lastUpdated')
        if updated_elem is None:
            updated_elem = root.find('.//{http://www.iridium.com/}lastUpdated')
        
        # ✅ 新增：解析 deliveryDetails (array)
        destinations = []
        delivery_details = root.findall('.//deliveryDetail')
        if not delivery_details:
            delivery_details = root.findall('.//{http://www.iridium.com/}deliveryDetail')
        
        for detail in delivery_details:
            dest_elem = detail.find('.//destination')
            if dest_elem is None:
                dest_elem = detail.find('.//{http://www.iridium.com/}destination')
            
            method_elem = detail.find('.//deliveryMethod')
            if method_elem is None:
                method_elem = detail.find('.//{http://www.iridium.com/}deliveryMethod')
            
            geo_elem = detail.find('.//geoDataFlag')
            if geo_elem is None:
                geo_elem = detail.find('.//{http://www.iridium.com/}geoDataFlag')
            
            moack_elem = detail.find('.//moAckFlag')
            if moack_elem is None:
                moack_elem = detail.find('.//{http://www.iridium.com/}moAckFlag')
            
            if dest_elem is not None and dest_elem.text:
                destinations.append({
                    'destination': dest_elem.text.strip(),
                    'method': method_elem.text.strip() if method_elem is not None and method_elem.text else 'N/A',
                    'geo_data': geo_elem.text.strip() if geo_elem is not None and geo_elem.text else 'FALSE',
                    'mo_ack': moack_elem.text.strip() if moack_elem is not None and moack_elem.text else 'FALSE'
                })
        
        # ✅ 新增：解析 maritimeSafetyInfo
        ring_alert = 'N/A'
        ring_alert_elem = root.find('.//ringAlertsFlag')
        if ring_alert_elem is None:
            ring_alert_elem = root.find('.//{http://www.iridium.com/}ringAlertsFlag')
        if ring_alert_elem is not None and ring_alert_elem.text:
            ring_alert = ring_alert_elem.text.strip()
        
        # ✅ 新增：解析 homeGateway
        home_gateway = 'N/A'
        home_gateway_elem = root.find('.//homeGateway')
        if home_gateway_elem is None:
            home_gateway_elem = root.find('.//{http://www.iridium.com/}homeGateway')
        if home_gateway_elem is not None and home_gateway_elem.text:
            home_gateway = home_gateway_elem.text.strip()
        
        # ✅ 新增：解析 spReference
        sp_reference = 'N/A'
        sp_ref_elem = root.find('.//spReference')
        if sp_ref_elem is None:
            sp_ref_elem = root.find('.//{http://www.iridium.com/}spReference')
        if sp_ref_elem is not None and sp_ref_elem.text:
            sp_reference = sp_ref_elem.text.strip()
        
        # ✅ 新增：解析 sbdBundleId（資費方案 ID）
        bundle_id = None
        bundle_id_elem = root.find('.//sbdBundleId')
        if bundle_id_elem is None:
            bundle_id_elem = root.find('.//{http://www.iridium.com/}sbdBundleId')
        if bundle_id_elem is not None and bundle_id_elem.text:
            bundle_id = bundle_id_elem.text.strip()
            print(f"[IWS] Bundle ID: {bundle_id}")
        
        # ✅ 新增：解析 Demo and Trial Bundle
        demo_and_trial = None
        demo_elem = root.find('.//demoAndTrial')
        if demo_elem is None:
            demo_elem = root.find('.//{http://www.iridium.com/}demoAndTrial')
        if demo_elem is not None and demo_elem.text:
            demo_and_trial = demo_elem.text.strip()
            print(f"[IWS] Demo and Trial: {demo_and_trial}")
        
        # ✅ 新增：解析 Promo Bundle
        promo = None
        promo_elem = root.find('.//promo')
        if promo_elem is None:
            promo_elem = root.find('.//{http://www.iridium.com/}promo')
        if promo_elem is not None and promo_elem.text:
            promo = promo_elem.text.strip()
            print(f"[IWS] Promo: {promo}")
        
        # ✅ 新增：解析 Account Pooling Group
        account_pooling_group = None
        pooling_elem = root.find('.//accountPoolingGroup')
        if pooling_elem is None:
            pooling_elem = root.find('.//{http://www.iridium.com/}accountPoolingGroup')
        if pooling_elem is not None and pooling_elem.text:
            account_pooling_group = pooling_elem.text.strip()
        
        # ✅ 新增：解析 lritFlagstate
        lrit_flagstate = ''
        lrit_elem = root.find('.//lritFlagstate')
        if lrit_elem is None:
            lrit_elem = root.find('.//{http://www.iridium.com/}lritFlagstate')
        if lrit_elem is not None and lrit_elem.text:
            lrit_flagstate = lrit_elem.text.strip()
        
        # ✅ 新增：解析 mtFilters
        mt_filters = []
        filter_elems = root.findall('.//mtFilter')
        if not filter_elems:
            filter_elems = root.findall('.//{http://www.iridium.com/}mtFilter')
        
        for filter_elem in filter_elems:
            rule_type_elem = filter_elem.find('.//ruleType')
            if rule_type_elem is None:
                rule_type_elem = filter_elem.find('.//{http://www.iridium.com/}ruleType')
            
            address_elem = filter_elem.find('.//address')
            if address_elem is None:
                address_elem = filter_elem.find('.//{http://www.iridium.com/}address')
            
            if rule_type_elem is not None and address_elem is not None:
                mt_filters.append({
                    'ruleType': rule_type_elem.text.strip() if rule_type_elem.text else '',
                    'address': address_elem.text.strip() if address_elem.text else ''
                })
        
        # ✅ 新增：解析 bulkAction
        bulk_action = 'FALSE'
        bulk_elem = root.find('.//bulkAction')
        if bulk_elem is None:
            bulk_elem = root.find('.//{http://www.iridium.com/}bulkAction')
        if bulk_elem is not None and bulk_elem.text:
            bulk_action = bulk_elem.text.strip().upper()
        
        status = status_elem.text if status_elem is not None else 'UNKNOWN'
        
        print(f"[IWS] 帳戶狀態: {status}")
        if destinations:
            print(f"[IWS] Destinations: {len(destinations)} 個")
        if mt_filters:
            print(f"[IWS] MT Filters: {len(mt_filters)} 個")
        if ring_alert != 'N/A':
            print(f"[IWS] Ring Alert: {ring_alert}")
        
        return {
            'account_number': account_number,
            'status': status,
            'plan_name': plan_elem.text if plan_elem is not None else 'N/A',
            'imei': imei_elem.text if imei_elem is not None else 'N/A',
            'activation_date': activation_elem.text if activation_elem is not None else 'N/A',
            'last_updated': updated_elem.text if updated_elem is not None else 'N/A',
            # ✅ 完整的資訊
            'destinations': destinations,
            'ring_alert': ring_alert,
            'home_gateway': home_gateway,
            'sp_reference': sp_reference,
            'bundle_id': bundle_id,
            'demo_and_trial': demo_and_trial,
            'promo': promo,
            'account_pooling_group': account_pooling_group,
            'lrit_flagstate': lrit_flagstate,
            'mt_filters': mt_filters,
            'bulk_action': bulk_action
        }
    
    def get_detailed_account_info(self, imei: str) -> Dict:
        """
        獲取設備的完整詳細資訊（包括 Destination, Ring Alert, MO ACK, Geo）
        
        此方法組合使用 search_account 和 get_subscriber_account：
        1. 先用 search_account 找到帳號和基本資訊
        2. 再用 get_subscriber_account 獲取詳細資訊
        3. 返回所有需求字段
        
        Args:
            imei: 設備 IMEI
            
        Returns:
            Dict: {
                'found': bool,
                'account_number': str,           # 合約代碼
                'status': str,                   # 狀態
                'plan_name': str,                # 現行資費
                'activation_date': str,          # 開通日期
                'imei': str,                     # IMEI
                'destinations': [                # Destination (數組)
                    {
                        'destination': str,      # 目的地址
                        'method': str,          # 投遞方法
                        'geo_data': str,        # Geo 標志
                        'mo_ack': str           # MO ACK 標志
                    }
                ],
                'ring_alert': str,               # Ring Alert
                'home_gateway': str,             # Home Gateway
                'sp_reference': str,             # SP 參考代碼
                'iccid': str,                    # ICCID
                'account_type': str              # 帳號類型
            }
        """
        print(f"\n{'='*60}")
        print("[IWS] 獲取設備完整詳細資訊...")
        print(f"IMEI: {imei}")
        print('='*60)
        
        # 步驟 1：用 search_account 找到帳號
        try:
            search_result = self.search_account(imei)
        except Exception as e:
            print(f"[IWS] ❌ search_account 失敗: {e}")
            return {
                'found': False,
                'error': f'Search failed: {str(e)}'
            }
        
        if not search_result.get('found'):
            print(f"[IWS] ❌ 找不到 IMEI: {imei}")
            return {
                'found': False,
                'message': 'IMEI not found in IWS system'
            }
        
        account_number = search_result['subscriber_account_number']
        print(f"[IWS] ✅ 找到帳號: {account_number}")
        
        # 步驟 2：用 get_subscriber_account 獲取詳細資訊
        try:
            detailed = self.get_subscriber_account(account_number)
        except Exception as e:
            print(f"[IWS] ⚠️  get_subscriber_account 失敗: {e}")
            # 如果獲取詳細資訊失敗，至少返回基本資訊
            return {
                'found': True,
                'account_number': account_number,
                'status': search_result.get('status', 'UNKNOWN'),
                'plan_name': search_result.get('plan_name', 'N/A'),
                'activation_date': search_result.get('activation_date', 'N/A'),
                'imei': imei,
                'destinations': [],
                'ring_alert': 'N/A',
                'home_gateway': 'N/A',
                'sp_reference': search_result.get('sp_reference', 'N/A'),
                'iccid': search_result.get('iccid', 'N/A'),
                'account_type': search_result.get('account_type', 'N/A'),
                'error': f'Detailed info unavailable: {str(e)}'
            }
        
        # 步驟 3：組合並返回完整資訊
        result = {
            'found': True,
            'account_number': account_number,
            'status': detailed.get('status', 'UNKNOWN'),
            'plan_name': detailed.get('plan_name', 'N/A'),
            'activation_date': detailed.get('activation_date', 'N/A'),
            'imei': imei,
            'destinations': detailed.get('destinations', []),
            'ring_alert': detailed.get('ring_alert', 'N/A'),
            'home_gateway': detailed.get('home_gateway', 'N/A'),
            'sp_reference': detailed.get('sp_reference', search_result.get('sp_reference', 'N/A')),
            'iccid': search_result.get('iccid', 'N/A'),
            'account_type': search_result.get('account_type', 'N/A'),
            'last_updated': detailed.get('last_updated', 'N/A')
        }
        
        print(f"[IWS] ✅ 完整資訊獲取成功")
        print(f"     - 狀態: {result['status']}")
        print(f"     - 資費: {result['plan_name']}")
        print(f"     - Destinations: {len(result['destinations'])} 個")
        print(f"     - Ring Alert: {result['ring_alert']}")
        print('='*60 + '\n')
        
        return result


# ==================== 便利函數 ====================

def validate_device_string(device_string: str, 
                          device_string_type: str = "IMEI",
                          validate_state: bool = True) -> Dict:
    """便利函數：驗證設備字符串"""
    gateway = IWSGateway()
    return gateway.validate_device_string(device_string, device_string_type, validate_state)


def search_account(imei: str) -> Dict:
    """便利函數：搜尋帳號"""
    gateway = IWSGateway()
    return gateway.search_account(imei)


def check_iws_connection() -> Dict:
    """便利函數：測試 IWS 連線"""
    gateway = IWSGateway()
    return gateway.check_connection()


def get_sbd_bundles(from_bundle_id: str = "0", 
                   for_activate: bool = True,
                   model_id: Optional[str] = None) -> Dict:
    """便利函數：查詢 SBD 方案"""
    gateway = IWSGateway()
    return gateway.get_sbd_bundles(from_bundle_id, for_activate, model_id)


def update_subscriber_plan(imei: str, 
                          new_plan_id: str,
                          lrit_flagstate: str = "",
                          ring_alerts_flag: bool = False) -> Dict:
    """便利函數：變更設備費率"""
    gateway = IWSGateway()
    return gateway.update_subscriber_plan(imei, new_plan_id, lrit_flagstate, ring_alerts_flag)


def suspend_sbd_device(imei: str, reason: str = '系統自動暫停') -> Dict:
    """便利函數：暫停 SBD 設備"""
    gateway = IWSGateway()
    return gateway.suspend_subscriber(imei=imei, reason=reason)


def resume_sbd_device(imei: str, reason: str = '系統自動恢復') -> Dict:
    """便利函數：恢復 SBD 設備"""
    gateway = IWSGateway()
    return gateway.resume_subscriber(imei=imei, reason=reason)


def deactivate_sbd_device(imei: str, reason: str = '系統自動註銷') -> Dict:
    """便利函數：註銷 SBD 設備"""
    gateway = IWSGateway()
    return gateway.deactivate_subscriber(imei=imei, reason=reason)

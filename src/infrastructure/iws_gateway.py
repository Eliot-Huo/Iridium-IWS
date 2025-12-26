"""
IWS (Iridium Web Services) SOAP 1.2 API Gateway v6.8 Final
完全符合官方 WSDL Schema (v25.1.0.1)

v6.8 Final 修正（根據官方文件）：
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
        3. <sbdPlan> 內部的字段（sbdBundleId, lritFlagstate 等）是用於配置，不是查詢
        
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
        
        根據 WSDL p.67, 271-272, 286
        用於更新 SBD 設備的費率方案
        
        Args:
            imei: 設備 IMEI
            subscriber_account_number: 訂閱者帳號（必填）
            new_plan_id: 新的 SBD Bundle ID
            lrit_flagstate: LRIT Flag State（3字元或空字串）
            ring_alerts_flag: Ring Alerts Flag
            
        Returns:
            tuple: (action_name, soap_body)
        """
        action_name = 'accountUpdate'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        sp_account = self._safe_xml_value(self.sp_account)
        
        # 提取純數字
        plan_id_digits = self._extract_plan_id_digits(new_plan_id)
        
        # Boolean 轉字串
        ring_alerts_str = self._bool_to_string(ring_alerts_flag)
        
        body = f'''        <tns:accountUpdate xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <sbdSubscriberAccount2>
                    <subscriberAccountNumber>{subscriber_account_number}</subscriberAccountNumber>
                    <imei>{imei}</imei>
                    <bulkAction>FALSE</bulkAction>
                    <newStatus>ACTIVE</newStatus>
                    <plan>
                        <sbdBundleId>{plan_id_digits}</sbdBundleId>
                        <lritFlagstate>{lrit_flagstate}</lritFlagstate>
                        <ringAlertsFlag>{ring_alerts_str}</ringAlertsFlag>
                    </plan>
                </sbdSubscriberAccount2>
            </request>
        </tns:accountUpdate>'''
        
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
                error_details = [
                    f"HTTP {response.status_code}: {response.reason}",
                    f"Endpoint: {self.endpoint}",
                    f"Action: {soap_action}",
                ]
                
                if 'X-Error-Info' in response.headers:
                    error_details.append(f"X-Error-Info: {response.headers['X-Error-Info']}")
                if 'X-Error-Code' in response.headers:
                    error_details.append(f"X-Error-Code: {response.headers['X-Error-Code']}")
                
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
    
    def _parse_account_search(self, xml_response: str, target_imei: Optional[str] = None) -> Optional[str]:
        """
        解析 accountSearch 回應，提取 accountNumber
        
        accountSearch 返回订阅者列表，需要遍历找到匹配的 IMEI
        
        Args:
            xml_response: SOAP 响应 XML
            target_imei: 要查找的 IMEI（可选，如果提供则匹配 IMEI）
            
        Returns:
            Optional[str]: 訂閱者帳號 (accountNumber) 或 None
        """
        try:
            root = ET.fromstring(xml_response)
            
            # 查找所有 subscriber 元素
            subscribers = root.findall('.//subscriber')
            
            if not subscribers:
                # 尝试其他命名空间
                subscribers = root.findall('.//{http://www.iridium.com/}subscriber')
            
            if not subscribers:
                print(f"[IWS] No subscribers found in response")
                return None
            
            print(f"[IWS] Found {len(subscribers)} subscriber(s)")
            
            # 如果提供了 target_imei，查找匹配的订阅者
            if target_imei:
                for subscriber in subscribers:
                    # 查找此订阅者的 IMEI
                    imei_elem = subscriber.find('.//imei')
                    if imei_elem is None:
                        imei_elem = subscriber.find('.//{http://www.iridium.com/}imei')
                    
                    if imei_elem is not None and imei_elem.text:
                        imei_value = imei_elem.text.strip()
                        print(f"[IWS] Checking subscriber with IMEI: {imei_value}")
                        
                        if imei_value == target_imei:
                            # 找到匹配的 IMEI，提取 accountNumber
                            account_elem = subscriber.find('.//accountNumber')
                            if account_elem is None:
                                account_elem = subscriber.find('.//{http://www.iridium.com/}accountNumber')
                            
                            if account_elem is not None and account_elem.text:
                                account_number = account_elem.text.strip()
                                print(f"[IWS] Found matching subscriber: {account_number}")
                                return account_number
                
                print(f"[IWS] No subscriber found with IMEI: {target_imei}")
                return None
            
            # 如果没有提供 target_imei，返回第一个订阅者的 accountNumber
            first_subscriber = subscribers[0]
            account_elem = first_subscriber.find('.//accountNumber')
            if account_elem is None:
                account_elem = first_subscriber.find('.//{http://www.iridium.com/}accountNumber')
            
            if account_elem is not None and account_elem.text:
                return account_elem.text.strip()
            
            # 备用：尝试查找 subscriberAccountNumber（旧格式）
            for path in ['.//subscriberAccountNumber', './/{http://www.iridium.com/}subscriberAccountNumber']:
                elem = root.find(path)
                if elem is not None and elem.text:
                    return elem.text.strip()
            
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
            
            subscriber_account_number = self._parse_account_search(response_xml, target_imei=imei)
            
            if subscriber_account_number:
                print("\n" + "="*60)
                print(f"✅ Account found: {subscriber_account_number}")
                print("="*60 + "\n")
                
                return {
                    'success': True,
                    'found': True,
                    'subscriber_account_number': subscriber_account_number,
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
                              new_plan_id: str,
                              lrit_flagstate: str = "",
                              ring_alerts_flag: bool = False) -> Dict:
        """
        變更設備費率方案
        
        使用 accountUpdate 方法（根據 WSDL p.67）
        
        工作流程：
        1. 用 accountSearch 查詢 subscriberAccountNumber
        2. 用 accountUpdate 更新費率
        
        Args:
            imei: 設備 IMEI
            new_plan_id: 新的 SBD Bundle ID（支援 "SBD12" 或 "12" 格式）
            lrit_flagstate: LRIT Flag State（3字元或空字串）
            ring_alerts_flag: Ring Alerts Flag
            
        Returns:
            Dict: 操作結果
        """
        self._validate_imei(imei)
        
        print("\n" + "="*60)
        print("💱 [IWS] Updating subscriber plan...")
        print("="*60)
        print(f"IMEI: {imei}")
        print(f"New Plan: {new_plan_id}")
        print(f"LRIT Flagstate: '{lrit_flagstate}'")
        print(f"Ring Alerts: {ring_alerts_flag}")
        print("="*60 + "\n")
        
        try:
            # 步驟 1: 用 IMEI 搜尋訂閱者帳號
            print("[IWS] Step 1: Searching for subscriber account...")
            search_action, search_body = self._build_account_search_body(imei)
            
            search_response = self._send_soap_request(
                soap_action=search_action,
                soap_body=search_body
            )
            
            subscriber_account_number = self._parse_account_search(search_response, target_imei=imei)
            
            if not subscriber_account_number:
                raise IWSException(
                    f"Account not found for IMEI: {imei}. "
                    f"The device may not be activated in the IWS system. "
                    f"Please verify the IMEI or activate the device first."
                )
            
            print(f"[IWS] Found account: {subscriber_account_number}")
            
            # 步驟 2: 更新費率
            print("[IWS] Step 2: Updating plan...")
            action_name, soap_body = self._build_account_update_body(
                imei=imei,
                subscriber_account_number=subscriber_account_number,
                new_plan_id=new_plan_id,
                lrit_flagstate=lrit_flagstate,
                ring_alerts_flag=ring_alerts_flag
            )
            
            response_xml = self._send_soap_request(
                soap_action=action_name,
                soap_body=soap_body
            )
            
            transaction_id = self._extract_transaction_id(response_xml)
            plan_id_digits = self._extract_plan_id_digits(new_plan_id)
            
            print("\n" + "="*60)
            print("✅ Plan updated successfully")
            print("="*60 + "\n")
            
            return {
                'success': True,
                'transaction_id': transaction_id or 'N/A',
                'message': 'Subscriber plan updated successfully',
                'imei': imei,
                'subscriber_account_number': subscriber_account_number,
                'new_plan_id': new_plan_id,
                'plan_id_digits': plan_id_digits,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except IWSException:
            raise
        except Exception as e:
            raise IWSException(f"Unexpected error during plan update: {str(e)}")
    
    def suspend_subscriber(self, 
                          imei: str,
                          reason: str = '系統自動暫停') -> Dict:
        """
        暫停 SBD 設備
        
        使用 setSubscriberAccountStatus（根據 WSDL p.224）
        
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
            
            print("\n" + "="*60)
            print("✅ Subscriber suspended successfully")
            print("="*60 + "\n")
            
            return {
                'success': True,
                'message': 'Subscriber suspended successfully',
                'imei': imei,
                'new_status': self.ACCOUNT_STATUS_SUSPENDED,
                'reason': reason,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except IWSException:
            raise
        except Exception as e:
            raise IWSException(f"Unexpected error during suspension: {str(e)}")
    
    def resume_subscriber(self, 
                         imei: str,
                         reason: str = '系統自動恢復') -> Dict:
        """
        恢復 SBD 設備
        
        使用 setSubscriberAccountStatus（根據 WSDL p.224）
        
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
            
            print("\n" + "="*60)
            print("✅ Subscriber resumed successfully")
            print("="*60 + "\n")
            
            return {
                'success': True,
                'message': 'Subscriber resumed successfully',
                'imei': imei,
                'new_status': self.ACCOUNT_STATUS_ACTIVE,
                'reason': reason,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except IWSException:
            raise
        except Exception as e:
            raise IWSException(f"Unexpected error during resumption: {str(e)}")
    
    def deactivate_subscriber(self,
                             imei: str,
                             reason: str = '系統自動註銷') -> Dict:
        """
        註銷設備
        
        使用 setSubscriberAccountStatus（根據 WSDL p.224）
        
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
            
            print("\n" + "="*60)
            print("✅ Subscriber deactivated successfully")
            print("="*60 + "\n")
            
            return {
                'success': True,
                'message': 'Subscriber deactivated successfully',
                'imei': imei,
                'new_status': self.ACCOUNT_STATUS_DEACTIVATED,
                'reason': reason,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except IWSException:
            raise
        except Exception as e:
            raise IWSException(f"Unexpected error during deactivation: {str(e)}")
    
    
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
        
        當隊列狀態為 ERROR 時，使用此方法獲取詳細的錯誤信息。
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Dict: {
                'transaction_id': 交易ID,
                'response': 原始SOAP響應,
                'error_message': 錯誤信息,
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
        
        print(f"[IWS] 錯誤信息: {error_message}")
        
        return {
            'transaction_id': transaction_id,
            'response': response_elem.text if response_elem is not None else '',
            'error_message': error_message,
            'error_code': error_code_elem.text if error_code_elem is not None else 'N/A'
        }
    
    
    def get_subscriber_account(self, account_number: str) -> Dict:
        """
        獲取訂閱者帳戶詳細信息（用於最終驗證）
        
        在異步操作完成後，使用此方法驗證帳戶的最終狀態。
        
        Args:
            account_number: 訂閱者帳號（例如 SUB-49059741895）
            
        Returns:
            Dict: {
                'account_number': 帳號,
                'status': 帳戶狀態,
                'plan_name': 費率方案,
                'imei': IMEI,
                'activation_date': 啟用日期,
                'last_updated': 最後更新時間
            }
        """
        print(f"\n[IWS] 獲取帳戶信息...")
        print(f"Account: {account_number}")
        
        action_name = 'getSubscriberAccount'
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(action_name, timestamp)
        
        body = f'''<tns:getSubscriberAccount xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{self.sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <subscriberAccountNumber>{account_number}</subscriberAccountNumber>
            </request>
        </tns:getSubscriberAccount>'''
        
        response_xml = self._send_soap_request(
            soap_action=action_name,
            soap_body=body
        )
        
        # 解析響應
        root = ET.fromstring(response_xml)
        
        # 查找帳戶信息
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
        
        status = status_elem.text if status_elem is not None else 'UNKNOWN'
        
        print(f"[IWS] 帳戶狀態: {status}")
        
        return {
            'account_number': account_number,
            'status': status,
            'plan_name': plan_elem.text if plan_elem is not None else 'N/A',
            'imei': imei_elem.text if imei_elem is not None else 'N/A',
            'activation_date': activation_elem.text if activation_elem is not None else 'N/A',
            'last_updated': updated_elem.text if updated_elem is not None else 'N/A'
        }


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

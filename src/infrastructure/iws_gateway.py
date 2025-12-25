"""
IWS (Iridium Web Services) SOAP 1.2 API Gateway v5.1 - SITEST Optimized
完全符合 WSDL Schema 定義 (iws_training.wsdl) 與 SOAP Developer Guide

架構師深度優化版本：
- 修正命名空間歧義（結尾加斜線）
- 強制完整標籤閉合（<tag></tag> 而非 <tag/>）
- 實作基礎診斷方法（check_connection）
- 優化錯誤回應捕捉（記錄 response.headers）
- 簽章大小寫校正（action 名稱完全一致）
"""
from __future__ import annotations
import requests
import urllib3
import xml.etree.ElementTree as ET
import re
from typing import Dict, Optional
from datetime import datetime
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
    IWS SOAP 1.2 API Gateway v5.1 - SITEST Optimized
    完全符合 WSDL 定義與架構師深度優化規範
    
    關鍵規範（SITEST 環境）：
    1. 命名空間必須帶斜線: http://www.iridium.com/
    2. 空欄位強制完整閉合: <tag></tag> 而非 <tag/>
    3. 診斷方法: check_connection() 使用 getSystemStatus
    4. 詳細錯誤日誌: 記錄 response.headers
    5. action 名稱大小寫: 完全符合 WSDL
    """
    
    # SOAP 1.2 Namespaces
    NAMESPACES = {
        'soap': 'http://www.w3.org/2003/05/soap-envelope',
        'tns': 'http://www.iridium.com/'  # 關鍵：結尾必須有斜線
    }
    
    # IWS Namespace - 關鍵：結尾必須有斜線（SITEST 環境要求）
    IWS_NS = 'http://www.iridium.com/'
    
    # Delivery Methods
    DELIVERY_METHOD_EMAIL = 'EMAIL'
    DELIVERY_METHOD_DIRECT_IP = 'DIRECT_IP'
    DELIVERY_METHOD_IRIDIUM_DEVICE = 'IRIDIUM_DEVICE'
    
    # Service Types
    SERVICE_TYPE_SHORT_BURST_DATA = 'SHORT_BURST_DATA'
    
    # Update Types
    UPDATE_TYPE_IMEI = 'IMEI'
    
    # Account Status
    ACCOUNT_STATUS_ACTIVE = 'ACTIVE'
    ACCOUNT_STATUS_SUSPENDED = 'SUSPENDED'
    
    def __init__(self, 
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 sp_account: Optional[str] = None,
                 endpoint: Optional[str] = None,
                 timeout: int = REQUEST_TIMEOUT):
        """
        初始化 IWS Gateway
        
        Args:
            username: IWS 使用者名稱
            password: IWS 密碼
            sp_account: Service Provider Account Number
            endpoint: IWS 端點 URL
            timeout: 請求逾時時間（秒）
        """
        self.username = username or IWS_USER
        self.password = password or IWS_PASS
        self.sp_account = sp_account or IWS_SP_ACCOUNT
        self.endpoint = endpoint or IWS_ENDPOINT
        self.timeout = timeout
        
        if not all([self.username, self.password, self.endpoint]):
            raise IWSException(
                "Missing required IWS credentials. "
                "Please configure IWS_USER, IWS_PASS, and IWS_ENDPOINT."
            )
    
    def _safe_xml_value(self, value: Optional[str]) -> str:
        """
        安全的 XML 值處理
        
        關鍵：強制完整標籤閉合
        - 空值/None 返回空字串（不返回 self-closing tag）
        - 確保所有欄位使用 <tag></tag> 格式
        
        Args:
            value: 原始值
            
        Returns:
            str: 安全的 XML 值（空字串而非 None）
        """
        if value is None or value == '':
            return ''  # 空字串，將生成 <tag></tag>
        return str(value)
    
    def _validate_imei(self, imei: str) -> bool:
        """
        驗證 IMEI 格式
        - 必須是 15 位數字
        - 必須以 30 開頭
        """
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
        """
        構建 SOAP 1.2 Envelope
        
        關鍵規範：
        - SOAP 1.2 命名空間
        - 空的 Header
        - Body 內容使用 tns 前綴
        """
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="{self.NAMESPACES['soap']}">
    <soap:Header/>
    <soap:Body>
{body_content}
    </soap:Body>
</soap:Envelope>'''
    
    def _build_get_system_status_body(self) -> str:
        """
        構建 getSystemStatus 的 SOAP Body
        用於連線測試 - 最簡單的無參數操作
        
        關鍵：
        - 僅包含認證欄位
        - 無業務資料
        - 用於診斷「認證/標頭/命名空間」問題
        """
        timestamp = datetime.now().isoformat()
        sp_account = self._safe_xml_value(self.sp_account)
        
        # 強制完整標籤閉合
        body = f'''        <tns:getSystemStatus xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{self.password}</signature>
                <serviceProviderAccountNumber>{sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <caller>{self.username}</caller>
            </request>
        </tns:getSystemStatus>'''
        
        return body
    
    def _build_activate_subscriber_body(self,
                                       imei: str,
                                       plan_id: str,
                                       destination: Optional[str] = None,
                                       delivery_method: str = DELIVERY_METHOD_DIRECT_IP,
                                       geo_data_flag: str = 'false',
                                       mo_ack_flag: str = 'false',
                                       lrit_flagstate: str = '',
                                       ring_alerts_flag: str = 'false') -> str:
        """
        構建 activateSubscriber 的 SOAP Body
        
        關鍵規範（SITEST 優化）：
        1. 命名空間帶斜線
        2. 強制完整標籤閉合（所有空欄位使用 <tag></tag>）
        3. 元素順序嚴格符合 WSDL
        4. 補全所有必要元素
        """
        if not destination:
            if delivery_method == self.DELIVERY_METHOD_EMAIL:
                destination = 'default@example.com'
            else:
                destination = '0.0.0.0'
        
        # 生成時間戳記
        timestamp = datetime.now().isoformat()
        
        # 安全處理所有可能為空的欄位
        sp_account = self._safe_xml_value(self.sp_account)
        lrit_flagstate = self._safe_xml_value(lrit_flagstate)
        
        # 構建 SOAP Body
        # 關鍵：所有空欄位使用 <tag></tag> 格式
        body = f'''        <tns:activateSubscriber xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{self.password}</signature>
                <serviceProviderAccountNumber>{sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <caller>{self.username}</caller>
                <sbdSubscriberAccount>
                    <plan>
                        <sbdBundleId>{plan_id}</sbdBundleId>
                        <lritFlagstate>{lrit_flagstate}</lritFlagstate>
                        <ringAlertsFlag>{ring_alerts_flag}</ringAlertsFlag>
                    </plan>
                    <imei>{imei}</imei>
                    <deliveryDetails>
                        <deliveryDetail>
                            <destination>{destination}</destination>
                            <deliveryMethod>{delivery_method}</deliveryMethod>
                            <geoDataFlag>{geo_data_flag}</geoDataFlag>
                            <moAckFlag>{mo_ack_flag}</moAckFlag>
                        </deliveryDetail>
                    </deliveryDetails>
                </sbdSubscriberAccount>
            </request>
        </tns:activateSubscriber>'''
        
        return body
    
    def _build_set_subscriber_account_status_body(self,
                                                   imei: str,
                                                   new_status: str,
                                                   reason: str = '系統自動執行',
                                                   service_type: str = SERVICE_TYPE_SHORT_BURST_DATA,
                                                   update_type: str = UPDATE_TYPE_IMEI) -> str:
        """
        構建 setSubscriberAccountStatus 的 SOAP Body
        
        關鍵規範：
        - 命名空間帶斜線
        - 元素順序符合 WSDL
        - 強制完整標籤閉合
        """
        timestamp = datetime.now().isoformat()
        sp_account = self._safe_xml_value(self.sp_account)
        
        body = f'''        <tns:setSubscriberAccountStatus xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{self.password}</signature>
                <serviceProviderAccountNumber>{sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <caller>{self.username}</caller>
                <serviceType>{service_type}</serviceType>
                <updateType>{update_type}</updateType>
                <value>{imei}</value>
                <newStatus>{new_status}</newStatus>
                <reason>{reason}</reason>
            </request>
        </tns:setSubscriberAccountStatus>'''
        
        return body
    
    def _send_soap_request(self, 
                          soap_action: str,
                          soap_body: str) -> str:
        """
        發送 SOAP 1.2 請求
        
        關鍵規範（SITEST 優化）：
        - Content-Type: action 僅含方法名（大小寫完全一致）
        - 無獨立 SOAPAction header
        - 無 HTTP Basic Auth
        - 詳細錯誤日誌（包含 response.headers）
        """
        soap_envelope = self._build_soap_envelope(soap_body)
        
        # SOAP 1.2 Headers
        # 關鍵：action 名稱大小寫完全符合 WSDL
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
            print(f"\n[IWS] SOAP Envelope (first 500 chars):")
            print(soap_envelope[:500])
            print(f"{'='*60}\n")
            
            # 不使用 HTTP Basic Auth（認證在 SOAP Body 內）
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
            
            # 關鍵：記錄 response.headers（可能包含錯誤提示）
            print(f"\n[IWS] Response Headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
            
            print(f"\n[IWS] Response Body (first 1000 chars):")
            print(response.text[:1000])
            print(f"{'='*60}\n")
            
            if response.status_code != 200:
                # 詳細的錯誤訊息
                error_details = [
                    f"HTTP {response.status_code}: {response.reason}",
                    f"Endpoint: {self.endpoint}",
                    f"Action: {soap_action}",
                ]
                
                # 檢查特殊的錯誤 headers
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
        """
        檢查 SOAP 1.2 Fault
        
        SOAP 1.2 Fault 結構:
        - soap:Code/soap:Value
        - soap:Reason/soap:Text
        - soap:Detail
        """
        try:
            root = ET.fromstring(xml_response)
            
            # 尋找 SOAP 1.2 Fault
            fault = root.find('.//soap:Fault', self.NAMESPACES)
            if fault is None:
                fault = root.find('.//Fault')
            
            if fault is not None:
                # SOAP 1.2: soap:Code/soap:Value
                code_elem = fault.find('soap:Code/soap:Value', self.NAMESPACES)
                if code_elem is None:
                    code_elem = fault.find('.//Code/Value')
                if code_elem is None:
                    code_elem = fault.find('.//faultcode')
                
                faultcode = code_elem.text if code_elem is not None else 'Unknown'
                
                # SOAP 1.2: soap:Reason/soap:Text
                reason_elem = fault.find('soap:Reason/soap:Text', self.NAMESPACES)
                if reason_elem is None:
                    reason_elem = fault.find('.//Reason/Text')
                if reason_elem is None:
                    reason_elem = fault.find('.//faultstring')
                
                faultstring = reason_elem.text if reason_elem is not None else 'Unknown error'
                
                # Detail
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
                './/activateSubscriberResponse/transactionId',
                './/response/transactionId'
            ]
            
            for path in paths:
                elem = root.find(path)
                if elem is not None and elem.text:
                    return elem.text.strip()
            
            return None
            
        except ET.ParseError:
            return None
    
    # ==================== 公開 API 方法 ====================
    
    def check_connection(self) -> Dict:
        """
        測試 IWS 連線（基礎診斷）
        
        使用最簡單的 getSystemStatus 操作進行診斷：
        - 如果此方法失敗（HTTP 500）→ 問題在「認證/標頭/命名空間」
        - 如果此方法成功但啟用失敗 → 問題在「SBD 資料結構」
        
        這是診斷 SITEST 環境問題的第一步。
        
        Returns:
            Dict: 連線測試結果
        
        Raises:
            IWSException: 連線失敗
        """
        print("\n" + "="*60)
        print("🔍 [DIAGNOSTIC] Starting connection test...")
        print("="*60)
        print("This is the simplest IWS operation (getSystemStatus)")
        print("Purpose: Verify authentication/headers/namespace")
        print("="*60 + "\n")
        
        try:
            soap_body = self._build_get_system_status_body()
            
            # 關鍵：action 名稱大小寫完全符合 WSDL
            response_xml = self._send_soap_request(
                soap_action='getSystemStatus',
                soap_body=soap_body
            )
            
            print("\n" + "="*60)
            print("✅ [DIAGNOSTIC] Connection test PASSED!")
            print("="*60)
            print("Authentication/headers/namespace are correct.")
            print("If activateSubscriber fails, check SBD data structure.")
            print("="*60 + "\n")
            
            return {
                'success': True,
                'message': 'IWS connection successful',
                'diagnostic': 'Authentication and protocol layer verified',
                'timestamp': datetime.now().isoformat()
            }
            
        except IWSException as e:
            print("\n" + "="*60)
            print("❌ [DIAGNOSTIC] Connection test FAILED!")
            print("="*60)
            print(f"Error Code: {e.error_code}")
            print(f"Error Message: {str(e)}")
            print("="*60)
            print("DIAGNOSIS: Problem in authentication/headers/namespace")
            print("ACTION: Check IWS_USER, IWS_PASS, IWS_SP_ACCOUNT")
            print("="*60 + "\n")
            raise
        except Exception as e:
            print("\n" + "="*60)
            print("❌ [DIAGNOSTIC] Connection test FAILED!")
            print("="*60)
            print(f"Unexpected Error: {str(e)}")
            print("="*60 + "\n")
            raise IWSException(f"Connection test failed: {str(e)}")
    
    def activate_subscriber(self,
                          imei: str,
                          plan_id: str,
                          destination: Optional[str] = None,
                          delivery_method: str = DELIVERY_METHOD_DIRECT_IP,
                          geo_data_flag: str = 'false',
                          mo_ack_flag: str = 'false',
                          lrit_flagstate: str = '',
                          ring_alerts_flag: str = 'false') -> Dict:
        """
        啟用 SBD 設備
        
        Args:
            imei: 設備 IMEI（15 位數字，必須以 30 開頭）
            plan_id: SBD Bundle ID (例如: 'SBD12', 'SBDO', 'SBD17')
            destination: 傳送目的地（IP 地址或 Email）
            delivery_method: 傳送方式（EMAIL/DIRECT_IP/IRIDIUM_DEVICE）
            geo_data_flag: 地理資料標誌（'true'/'false'）
            mo_ack_flag: MO 確認標誌（'true'/'false'）
            lrit_flagstate: LRIT Flag State（通常留空）
            ring_alerts_flag: Ring Alerts Flag（'true'/'false'）
            
        Returns:
            Dict: 啟用結果
        """
        self._validate_imei(imei)
        
        valid_methods = [
            self.DELIVERY_METHOD_EMAIL,
            self.DELIVERY_METHOD_DIRECT_IP,
            self.DELIVERY_METHOD_IRIDIUM_DEVICE
        ]
        if delivery_method not in valid_methods:
            raise IWSException(
                f"Invalid delivery_method: {delivery_method}. "
                f"Must be one of: {', '.join(valid_methods)}"
            )
        
        try:
            soap_body = self._build_activate_subscriber_body(
                imei=imei,
                plan_id=plan_id,
                destination=destination,
                delivery_method=delivery_method,
                geo_data_flag=geo_data_flag,
                mo_ack_flag=mo_ack_flag,
                lrit_flagstate=lrit_flagstate,
                ring_alerts_flag=ring_alerts_flag
            )
            
            # 關鍵：action 名稱大小寫完全符合 WSDL
            response_xml = self._send_soap_request(
                soap_action='activateSubscriber',
                soap_body=soap_body
            )
            
            transaction_id = self._extract_transaction_id(response_xml)
            
            return {
                'success': True,
                'transaction_id': transaction_id or 'N/A',
                'message': 'Subscriber activated successfully',
                'imei': imei,
                'plan_id': plan_id,
                'delivery_method': delivery_method,
                'destination': destination,
                'timestamp': datetime.now().isoformat()
            }
            
        except IWSException:
            raise
        except Exception as e:
            raise IWSException(f"Unexpected error during activation: {str(e)}")
    
    def suspend_subscriber(self, 
                          imei: str,
                          reason: str = '系統自動暫停') -> Dict:
        """
        暫停 SBD 設備
        
        Args:
            imei: 設備 IMEI
            reason: 暫停原因
            
        Returns:
            Dict: 暫停結果
        """
        self._validate_imei(imei)
        
        try:
            soap_body = self._build_set_subscriber_account_status_body(
                imei=imei,
                new_status=self.ACCOUNT_STATUS_SUSPENDED,
                reason=reason
            )
            
            # 關鍵：action 名稱大小寫完全符合 WSDL
            response_xml = self._send_soap_request(
                soap_action='setSubscriberAccountStatus',
                soap_body=soap_body
            )
            
            return {
                'success': True,
                'message': 'Subscriber suspended successfully',
                'imei': imei,
                'new_status': self.ACCOUNT_STATUS_SUSPENDED,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
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
        
        Args:
            imei: 設備 IMEI
            reason: 恢復原因
            
        Returns:
            Dict: 恢復結果
        """
        self._validate_imei(imei)
        
        try:
            soap_body = self._build_set_subscriber_account_status_body(
                imei=imei,
                new_status=self.ACCOUNT_STATUS_ACTIVE,
                reason=reason
            )
            
            # 關鍵：action 名稱大小寫完全符合 WSDL
            response_xml = self._send_soap_request(
                soap_action='setSubscriberAccountStatus',
                soap_body=soap_body
            )
            
            return {
                'success': True,
                'message': 'Subscriber resumed successfully',
                'imei': imei,
                'new_status': self.ACCOUNT_STATUS_ACTIVE,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }
            
        except IWSException:
            raise
        except Exception as e:
            raise IWSException(f"Unexpected error during resumption: {str(e)}")


# ==================== 便利函數 ====================

def check_iws_connection() -> Dict:
    """
    便利函數：測試 IWS 連線
    
    這是診斷 SITEST 環境問題的第一步。
    如果此方法失敗，問題在認證/標頭/命名空間。
    """
    gateway = IWSGateway()
    return gateway.check_connection()


def activate_sbd_device(imei: str, 
                       plan_id: str,
                       destination: Optional[str] = None,
                       delivery_method: str = IWSGateway.DELIVERY_METHOD_DIRECT_IP) -> Dict:
    """便利函數：啟用 SBD 設備"""
    gateway = IWSGateway()
    return gateway.activate_subscriber(
        imei=imei,
        plan_id=plan_id,
        destination=destination,
        delivery_method=delivery_method
    )


def suspend_sbd_device(imei: str, reason: str = '系統自動暫停') -> Dict:
    """便利函數：暫停 SBD 設備"""
    gateway = IWSGateway()
    return gateway.suspend_subscriber(imei=imei, reason=reason)


def resume_sbd_device(imei: str, reason: str = '系統自動恢復') -> Dict:
    """便利函數：恢復 SBD 設備"""
    gateway = IWSGateway()
    return gateway.resume_subscriber(imei=imei, reason=reason)

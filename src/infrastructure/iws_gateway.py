"""
IWS (Iridium Web Services) SOAP 1.2 API Gateway v5.0 Final
完全符合 WSDL Schema 定義 (iws_training.wsdl) 與 SOAP Developer Guide

架構師最終審查完成：
- SOAP 1.2 標頭優化（action 僅含方法名）
- 精確符合 Schema 的 XML 結構（tns 前綴，unqualified 子元素）
- 嚴格執行元素順序（包含 serviceProviderAccountNumber）
- 補全所有 SBD 帳戶與目的地元素
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
    IWS_SP_ACCOUNT,  # Service Provider Account Number
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
    IWS SOAP 1.2 API Gateway v5.0 Final
    完全符合 WSDL 定義與架構師審查規範
    
    關鍵規範：
    1. SOAP 1.2 Content-Type: application/soap+xml; charset=utf-8; action="methodName"
    2. 操作名稱使用 tns 前綴: <tns:activateSubscriber>
    3. 子元素使用 unqualified（無前綴）: <request>, <iwsUsername>, etc.
    4. 元素順序: iwsUsername → signature → serviceProviderAccountNumber → timestamp → caller
    5. 補全所有必要元素: lritFlagstate, ringAlertsFlag, geoDataFlag, moAckFlag
    """
    
    # SOAP 1.2 Namespaces
    NAMESPACES = {
        'soap': 'http://www.w3.org/2003/05/soap-envelope',
        'tns': 'http://www.iridium.com'
    }
    
    # IWS Namespace
    IWS_NS = 'http://www.iridium.com'
    
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
        
        if not all([self.username, self.password, self.sp_account, self.endpoint]):
            raise IWSException(
                "Missing required IWS credentials. "
                "Please configure IWS_USER, IWS_PASS, IWS_SP_ACCOUNT, and IWS_ENDPOINT."
            )
    
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
        
        關鍵規範：
        1. 操作名稱使用 tns 前綴並宣告 xmlns:tns
        2. 所有子元素使用 unqualified（無前綴，無 xmlns）
        3. 元素順序：iwsUsername → signature → serviceProviderAccountNumber → timestamp → caller → 業務資料
        4. 補全所有必要元素
        """
        if not destination:
            if delivery_method == self.DELIVERY_METHOD_EMAIL:
                destination = 'default@example.com'
            else:
                destination = '0.0.0.0'
        
        # 生成時間戳記（ISO 8601 格式）
        timestamp = datetime.now().isoformat()
        
        # 構建 SOAP Body
        # 關鍵：tns 前綴在操作名稱，xmlns:tns 宣告，子元素無前綴
        body = f'''        <tns:activateSubscriber xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{self.password}</signature>
                <serviceProviderAccountNumber>{self.sp_account}</serviceProviderAccountNumber>
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
        1. 操作名稱使用 tns 前綴
        2. 子元素使用 unqualified（無前綴）
        3. 元素順序：認證欄位 → 業務資料
        """
        # 生成時間戳記
        timestamp = datetime.now().isoformat()
        
        # 構建 SOAP Body
        body = f'''        <tns:setSubscriberAccountStatus xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{self.password}</signature>
                <serviceProviderAccountNumber>{self.sp_account}</serviceProviderAccountNumber>
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
    
    def _build_get_system_status_body(self) -> str:
        """
        構建 getSystemStatus 的 SOAP Body
        用於連線測試
        
        這是最簡單的 IWS 操作，無需參數
        """
        timestamp = datetime.now().isoformat()
        
        body = f'''        <tns:getSystemStatus xmlns:tns="{self.IWS_NS}">
            <request>
                <iwsUsername>{self.username}</iwsUsername>
                <signature>{self.password}</signature>
                <serviceProviderAccountNumber>{self.sp_account}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <caller>{self.username}</caller>
            </request>
        </tns:getSystemStatus>'''
        
        return body
    
    def _send_soap_request(self, 
                          soap_action: str,
                          soap_body: str) -> str:
        """
        發送 SOAP 1.2 請求
        
        關鍵規範（架構師審查）：
        - Content-Type: application/soap+xml; charset=utf-8; action="methodName"
        - action 僅含方法名（不含 URL）
        - 不使用獨立的 SOAPAction header
        - 不使用 HTTP Basic Auth
        """
        soap_envelope = self._build_soap_envelope(soap_body)
        
        # SOAP 1.2 Headers
        # 關鍵：action 只有方法名，無 URL
        headers = {
            'Content-Type': f'application/soap+xml; charset=utf-8; action="{soap_action}"',
            'Accept': 'application/soap+xml, text/xml'
        }
        
        try:
            # 不使用 HTTP Basic Auth（認證在 SOAP Body 內）
            response = requests.post(
                self.endpoint,
                data=soap_envelope,
                headers=headers,
                timeout=self.timeout,
                verify=False
            )
            
            print(f"[IWS] Request to {self.endpoint}")
            print(f"[IWS] SOAP Action: {soap_action}")
            print(f"[IWS] Response Status: {response.status_code}")
            
            if response.status_code != 200:
                raise IWSException(
                    f"HTTP {response.status_code}: {response.reason}",
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
                    code_elem = fault.find('.//faultcode')  # 向後相容
                
                faultcode = code_elem.text if code_elem is not None else 'Unknown'
                
                # SOAP 1.2: soap:Reason/soap:Text
                reason_elem = fault.find('soap:Reason/soap:Text', self.NAMESPACES)
                if reason_elem is None:
                    reason_elem = fault.find('.//Reason/Text')
                if reason_elem is None:
                    reason_elem = fault.find('.//faultstring')  # 向後相容
                
                faultstring = reason_elem.text if reason_elem is not None else 'Unknown error'
                
                # Detail
                detail = fault.find('soap:Detail', self.NAMESPACES)
                if detail is None:
                    detail = fault.find('.//Detail')
                if detail is None:
                    detail = fault.find('.//detail')  # 向後相容
                
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
                './/{http://www.iridium.com}transactionId',
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
        測試 IWS 連線
        
        使用 getSystemStatus 方法進行最簡單的通訊測試
        
        Returns:
            Dict: 連線測試結果
        
        Raises:
            IWSException: 連線失敗
        """
        try:
            soap_body = self._build_get_system_status_body()
            
            response_xml = self._send_soap_request(
                soap_action='getSystemStatus',
                soap_body=soap_body
            )
            
            return {
                'success': True,
                'message': 'IWS connection successful',
                'timestamp': datetime.now().isoformat()
            }
            
        except IWSException:
            raise
        except Exception as e:
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
    """便利函數：測試 IWS 連線"""
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

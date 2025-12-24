"""
IWS (Iridium Web Services) SOAP API Gateway v4.0 Final
完全符合 WSDL Schema 定義 (iws_training.wsdl)
"""
from __future__ import annotations
import requests
import urllib3
import xml.etree.ElementTree as ET
import re
from typing import Dict, Optional
from datetime import datetime
from ..config.settings import IWS_USER, IWS_PASS, IWS_ENDPOINT, REQUEST_TIMEOUT

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
    IWS SOAP API Gateway v4.0 Final
    完全符合 WSDL 定義
    
    支援功能:
    - activateSubscriber: 啟用 SBD 設備
    - setSubscriberAccountStatus: 變更帳戶狀態（暫停/恢復）
    """
    
    # SOAP Namespaces
    NAMESPACES = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
        'tns': 'http://www.iridium.com'
    }
    
    # IWS Namespace - 符合 WSDL targetNamespace (無結尾斜線)
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
                 endpoint: Optional[str] = None,
                 timeout: int = REQUEST_TIMEOUT):
        """初始化 IWS Gateway"""
        self.username = username or IWS_USER
        self.password = password or IWS_PASS
        self.endpoint = endpoint or IWS_ENDPOINT
        self.timeout = timeout
        
        if not all([self.username, self.password, self.endpoint]):
            raise IWSException("Missing required IWS credentials or endpoint")
    
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
        """構建 SOAP Envelope"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="{self.NAMESPACES['soap']}" 
               xmlns:xsi="{self.NAMESPACES['xsi']}" 
               xmlns:xsd="{self.NAMESPACES['xsd']}">
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
        完全符合 WSDL activateSubscriberRequestImpl
        """
        if not destination:
            if delivery_method == self.DELIVERY_METHOD_EMAIL:
                destination = 'default@example.com'
            else:
                destination = '0.0.0.0'
        
        body = f'''<activateSubscriber xmlns="{self.IWS_NS}">
    <request>
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
</activateSubscriber>'''
        
        return body
    
    def _build_set_subscriber_account_status_body(self,
                                                   imei: str,
                                                   new_status: str,
                                                   reason: str = '系統自動執行',
                                                   service_type: str = SERVICE_TYPE_SHORT_BURST_DATA,
                                                   update_type: str = UPDATE_TYPE_IMEI) -> str:
        """
        構建 setSubscriberAccountStatus 的 SOAP Body
        完全符合 WSDL accountStatusChangeRequestImpl
        """
        body = f'''<setSubscriberAccountStatus xmlns="{self.IWS_NS}">
    <request>
        <serviceType>{service_type}</serviceType>
        <updateType>{update_type}</updateType>
        <value>{imei}</value>
        <newStatus>{new_status}</newStatus>
        <reason>{reason}</reason>
    </request>
</setSubscriberAccountStatus>'''
        
        return body
    
    def _send_soap_request(self, 
                          soap_action: str,
                          soap_body: str) -> str:
        """發送 SOAP 請求"""
        soap_envelope = self._build_soap_envelope(soap_body)
        
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': f'"{soap_action}"',
            'Accept': 'text/xml'
        }
        
        try:
            response = requests.post(
                self.endpoint,
                data=soap_envelope,
                headers=headers,
                auth=(self.username, self.password),
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
        """檢查 SOAP Fault"""
        try:
            root = ET.fromstring(xml_response)
            
            fault = root.find('.//soap:Fault', self.NAMESPACES)
            if fault is None:
                fault = root.find('.//Fault')
            
            if fault is not None:
                faultcode = fault.findtext('faultcode', 'Unknown')
                faultstring = fault.findtext('faultstring', 'Unknown error')
                
                detail = fault.find('detail')
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

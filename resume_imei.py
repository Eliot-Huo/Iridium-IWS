#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMEI 快速恢復工具
用於在 SITEST 環境中快速將 SUSPENDED 設備恢復為 ACTIVE
"""

import sys
import os
import hmac
import hashlib
import base64
from datetime import datetime, timezone
import requests
import xml.etree.ElementTree as ET

# IWS 設定
IWS_USERNAME = 'IWSN3D'
IWS_PASSWORD = 'FvGr2({sE4V4TJ:'
IWS_SP_ACCOUNT = '200883'
IWS_ENDPOINT = 'https://iwstraining.iridium.com:8443/iws-current/iws'
IWS_NAMESPACE = 'http://www.iridium.com/'

def generate_signature(action: str, timestamp: str) -> str:
    """生成 HMAC-SHA1 簽章"""
    message = f"{action}{timestamp}"
    signature = hmac.new(
        IWS_PASSWORD.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha1
    ).digest()
    return base64.b64encode(signature).decode('utf-8')

def get_account_status(imei: str):
    """查詢帳號狀態"""
    action = 'accountSearch'
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    signature = generate_signature(action, timestamp)
    
    soap_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
    <soap:Header/>
    <soap:Body>
        <tns:accountSearch xmlns:tns="{IWS_NAMESPACE}">
            <request>
                <iwsUsername>{IWS_USERNAME}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{IWS_SP_ACCOUNT}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <serviceType>SHORT_BURST_DATA</serviceType>
                <filterType>IMEI</filterType>
                <filterCond>EXACT</filterCond>
                <filterValue>{imei}</filterValue>
            </request>
        </tns:accountSearch>
    </soap:Body>
</soap:Envelope>'''
    
    headers = {
        'Content-Type': f'application/soap+xml; charset=utf-8; action="{action}"',
        'Accept': 'application/soap+xml, text/xml'
    }
    
    response = requests.post(IWS_ENDPOINT, data=soap_body.encode('utf-8'), 
                           headers=headers, timeout=30)
    
    if response.status_code != 200:
        return None
    
    root = ET.fromstring(response.text)
    subscribers = root.findall('.//subscriber')
    
    for subscriber in subscribers:
        imei_elem = subscriber.find('.//imei')
        if imei_elem is not None and imei_elem.text == imei:
            account_elem = subscriber.find('.//accountNumber')
            status_elem = subscriber.find('.//accountStatus')
            
            if account_elem is not None and status_elem is not None:
                return {
                    'account_number': account_elem.text,
                    'status': status_elem.text
                }
    
    return None

def resume_account(imei: str, account_number: str):
    """恢復帳號為 ACTIVE"""
    action = 'setSubscriberAccountStatus'
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    signature = generate_signature(action, timestamp)
    
    soap_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
    <soap:Header/>
    <soap:Body>
        <tns:setSubscriberAccountStatus xmlns:tns="{IWS_NAMESPACE}">
            <request>
                <iwsUsername>{IWS_USERNAME}</iwsUsername>
                <signature>{signature}</signature>
                <serviceProviderAccountNumber>{IWS_SP_ACCOUNT}</serviceProviderAccountNumber>
                <timestamp>{timestamp}</timestamp>
                <subscriberAccountNumber>{account_number}</subscriberAccountNumber>
                <newStatus>ACTIVE</newStatus>
                <reason>SITEST 環境測試恢復</reason>
            </request>
        </tns:setSubscriberAccountStatus>
    </soap:Body>
</soap:Envelope>'''
    
    headers = {
        'Content-Type': f'application/soap+xml; charset=utf-8; action="{action}"',
        'Accept': 'application/soap+xml, text/xml'
    }
    
    response = requests.post(IWS_ENDPOINT, data=soap_body.encode('utf-8'), 
                           headers=headers, timeout=30)
    
    return response.status_code == 200

def main(imei: str):
    """主程序"""
    print()
    print("="*70)
    print("🔧 IMEI 快速恢復工具（SITEST 環境）")
    print("="*70)
    print()
    print(f"IMEI: {imei}")
    print()
    
    # 步驟 1：查詢狀態
    print("📡 步驟 1: 查詢目前狀態...")
    account_info = get_account_status(imei)
    
    if not account_info:
        print("❌ 找不到此 IMEI")
        print()
        print("可能原因：")
        print("  • IMEI 輸入錯誤")
        print("  • 設備未在 IWS 註冊")
        print()
        return False
    
    print(f"✅ 找到帳號: {account_info['account_number']}")
    print(f"   狀態: {account_info['status']}")
    print()
    
    # 步驟 2：判斷是否需要恢復
    if account_info['status'] == 'ACTIVE':
        print("✅ 帳號已經是 ACTIVE 狀態")
        print("   不需要恢復")
        print()
        print("="*70)
        print("🎉 完成！")
        print("="*70)
        print()
        return True
    
    if account_info['status'] == 'DEACTIVATED':
        print("⚠️  帳號是 DEACTIVATED（已註銷）")
        print("   ")
        print("💡 說明：")
        print("   DEACTIVATED 狀態可以恢復為 ACTIVE")
        print("   將執行恢復操作...")
        print()
    elif account_info['status'] == 'SUSPENDED':
        print("ℹ️  帳號是 SUSPENDED（已暫停）")
        print("   ")
        print("💡 SITEST 環境說明：")
        print("   • 這是測試環境的數據快照狀態")
        print("   • 生產環境可能是 ACTIVE")
        print("   • 將恢復為 ACTIVE 以便繼續測試")
        print()
    
    # 步驟 3：執行恢復
    print("🔧 步驟 2: 執行恢復操作...")
    success = resume_account(imei, account_info['account_number'])
    
    if success:
        print("✅ 恢復成功！")
        print()
        print("="*70)
        print("🎉 完成！帳號已恢復為 ACTIVE 狀態")
        print("="*70)
        print()
        print("📋 現在可以執行：")
        print("   • 變更資費（Account Update）")
        print("   • 暫停設備")
        print("   • 註銷設備")
        print()
        return True
    else:
        print("❌ 恢復失敗")
        print()
        print("可能原因：")
        print("  • IWS 伺服器錯誤")
        print("  • 網路問題")
        print("  • 帳號狀態不允許恢復")
        print()
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print()
        print("用法: python3 resume_imei.py <IMEI>")
        print()
        print("功能:")
        print("  將 SITEST 環境中的 SUSPENDED 或 DEACTIVATED 設備")
        print("  恢復為 ACTIVE 狀態，以便繼續測試")
        print()
        print("範例:")
        print("  python3 resume_imei.py 300434067857940")
        print()
        print("💡 SITEST 環境說明:")
        print("  • SITEST 是 Iridium 的測試環境")
        print("  • 與生產環境完全隔離")
        print("  • 數據是生產環境的快照")
        print("  • 測試中的修改不影響生產環境")
        print()
        sys.exit(1)
    
    imei = sys.argv[1]
    success = main(imei)
    sys.exit(0 if success else 1)

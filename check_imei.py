#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMEI 快速檢查工具
檢查 IMEI 是否存在於 IWS 系統中
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

def check_imei(imei: str):
    """檢查 IMEI 是否存在"""
    
    print("="*70)
    print(f"🔍 檢查 IMEI: {imei}")
    print("="*70)
    print()
    
    # 驗證 IMEI 格式
    if not imei.isdigit() or len(imei) != 15:
        print("❌ IMEI 格式錯誤")
        print(f"   輸入: {imei} ({len(imei)} 位)")
        print(f"   要求: 15 位數字")
        print()
        return False
    
    try:
        # 準備請求
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
        
        print("📡 正在查詢 IWS...")
        response = requests.post(
            IWS_ENDPOINT,
            data=soap_body.encode('utf-8'),
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}: {response.reason}")
            print()
            return False
        
        # 解析回應
        root = ET.fromstring(response.text)
        subscribers = root.findall('.//subscriber')
        
        if not subscribers:
            print("❌ IMEI 不存在於 IWS 系統中")
            print()
            print("可能原因：")
            print("  1. IMEI 輸入錯誤")
            print("  2. 設備尚未註冊")
            print("  3. 設備已被刪除")
            print()
            return False
        
        # 找到匹配的訂閱者
        found = False
        for subscriber in subscribers:
            imei_elem = subscriber.find('.//imei')
            if imei_elem is not None and imei_elem.text == imei:
                account_elem = subscriber.find('.//accountNumber')
                status_elem = subscriber.find('.//accountStatus')
                plan_elem = subscriber.find('.//planName')
                
                print("✅ IMEI 存在！")
                print()
                print("📋 設備資訊:")
                if account_elem is not None:
                    print(f"   帳號: {account_elem.text}")
                if status_elem is not None:
                    status = status_elem.text
                    status_emoji = {
                        'ACTIVE': '✅',
                        'SUSPENDED': '⏸️',
                        'DEACTIVATED': '🔴'
                    }.get(status, '❓')
                    print(f"   狀態: {status_emoji} {status}")
                    
                    # 根據狀態給出建議
                    if status == 'DEACTIVATED':
                        print()
                        print("⚠️  注意: 此帳號已註銷")
                        print("   無法再次註銷")
                        print("   可以執行: 恢復")
                    elif status == 'SUSPENDED':
                        print()
                        print("ℹ️  此帳號已暫停")
                        print("   可以執行: 恢復、註銷")
                    elif status == 'ACTIVE':
                        print()
                        print("ℹ️  此帳號正常運作")
                        print("   可以執行: 暫停、註銷、變更資費")
                
                if plan_elem is not None:
                    print(f"   方案: {plan_elem.text}")
                
                print()
                found = True
                break
        
        if not found:
            print("❌ 未找到匹配的 IMEI")
            print(f"   系統中有 {len(subscribers)} 個訂閱者")
            print(f"   但沒有 IMEI {imei}")
            print()
            return False
        
        return True
        
    except requests.exceptions.Timeout:
        print("⏱️  連線逾時")
        print()
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"🌐 連線錯誤: {str(e)}")
        print()
        return False
    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        print()
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print()
        print("用法: python3 check_imei.py <IMEI>")
        print()
        print("範例:")
        print("  python3 check_imei.py 300434067857940")
        print()
        sys.exit(1)
    
    imei = sys.argv[1]
    print()
    success = check_imei(imei)
    print()
    
    sys.exit(0 if success else 1)

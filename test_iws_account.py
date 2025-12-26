#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IWS 帳號狀態測試程式
測試 IWSN3D 帳號是否正常運作
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

def test_iws_connection():
    """測試 IWS 連線"""
    
    print("="*70)
    print("🧪 IWS 帳號狀態測試")
    print("="*70)
    print()
    print(f"📋 測試資訊:")
    print(f"   帳號: {IWS_USERNAME}")
    print(f"   SP Account: {IWS_SP_ACCOUNT}")
    print(f"   端點: {IWS_ENDPOINT}")
    print()
    
    try:
        # 步驟 1: 準備 SOAP 請求
        print("📡 步驟 1: 準備 SOAP 請求...")
        
        action = 'accountSearch'
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        signature = generate_signature(action, timestamp)
        
        print(f"   Action: {action}")
        print(f"   Timestamp: {timestamp}")
        print(f"   Signature: {signature[:20]}...")
        print()
        
        # 步驟 2: 構建 SOAP Body
        print("📡 步驟 2: 構建 SOAP Body...")
        
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
                <filterValue>300434067857940</filterValue>
            </request>
        </tns:accountSearch>
    </soap:Body>
</soap:Envelope>'''
        
        print("   ✅ SOAP Body 已構建")
        print()
        
        # 步驟 3: 發送請求
        print("📡 步驟 3: 發送請求到 IWS...")
        
        headers = {
            'Content-Type': f'application/soap+xml; charset=utf-8; action="{action}"',
            'Accept': 'application/soap+xml, text/xml'
        }
        
        response = requests.post(
            IWS_ENDPOINT,
            data=soap_body.encode('utf-8'),
            headers=headers,
            timeout=30
        )
        
        print(f"   HTTP 狀態碼: {response.status_code}")
        print()
        
        # 步驟 4: 分析結果
        if response.status_code == 200:
            print("="*70)
            print("✅ 連線成功！")
            print("="*70)
            print()
            print("📋 回應資訊:")
            print(f"   狀態碼: {response.status_code} OK")
            print(f"   內容長度: {len(response.text)} bytes")
            print()
            
            # 解析 XML
            try:
                root = ET.fromstring(response.text)
                subscribers = root.findall('.//subscriber')
                
                if subscribers:
                    print(f"   找到 {len(subscribers)} 個訂閱者")
                    print()
                    
                    # 顯示第一個
                    first = subscribers[0]
                    account = first.find('.//accountNumber')
                    status = first.find('.//accountStatus')
                    plan = first.find('.//planName')
                    
                    if account is not None:
                        print(f"   範例訂閱者:")
                        print(f"     帳號: {account.text}")
                        if status is not None:
                            print(f"     狀態: {status.text}")
                        if plan is not None:
                            print(f"     方案: {plan.text}")
                else:
                    print("   未找到訂閱者（IMEI 不存在）")
                    print("   但連線和認證都是成功的")
                    
            except Exception as e:
                print(f"   XML 解析: {str(e)}")
            
            print()
            print("="*70)
            print("🎉 測試結果: 帳號 IWSN3D 運作正常！")
            print("="*70)
            print()
            print("✅ 帳號未被禁用")
            print("✅ 認證成功")
            print("✅ 可以正常查詢")
            return True
            
        elif response.status_code == 401:
            print("="*70)
            print("❌ 認證失敗！")
            print("="*70)
            print()
            print("🔒 可能原因:")
            print("   1. 帳號被禁用")
            print("   2. 密碼錯誤")
            print("   3. 簽章算法錯誤")
            print()
            print(f"回應內容:")
            print(response.text[:500])
            return False
            
        elif response.status_code == 500:
            print("="*70)
            print("⚠️  伺服器錯誤")
            print("="*70)
            print()
            print("可能是請求格式問題，但不是帳號被禁用")
            print()
            print(f"回應內容:")
            print(response.text[:500])
            return False
            
        else:
            print("="*70)
            print(f"❓ 未預期的狀態碼: {response.status_code}")
            print("="*70)
            print()
            print(f"回應內容:")
            print(response.text[:500])
            return False
            
    except requests.exceptions.Timeout:
        print()
        print("="*70)
        print("⏱️  連線逾時")
        print("="*70)
        print()
        print("🌐 可能原因:")
        print("   1. 網路連線問題")
        print("   2. IWS 伺服器回應緩慢")
        print("   3. 防火牆阻擋")
        return False
        
    except requests.exceptions.ConnectionError as e:
        print()
        print("="*70)
        print("🌐 連線錯誤")
        print("="*70)
        print()
        print(f"錯誤: {str(e)}")
        print()
        print("可能原因:")
        print("   1. 無法連接到 IWS 伺服器")
        print("   2. 網路問題")
        print("   3. DNS 解析失敗")
        return False
        
    except Exception as e:
        print()
        print("="*70)
        print("❌ 測試失敗")
        print("="*70)
        print()
        print(f"錯誤: {str(e)}")
        return False

if __name__ == "__main__":
    print()
    success = test_iws_connection()
    print()
    sys.exit(0 if success else 1)

"""
IWS v6.8 診斷腳本 - 測試真實 IMEI
"""
import sys
sys.path.insert(0, '/home/claude/SBD-Final')

from src.infrastructure.iws_gateway import IWSGateway, IWSException

# 真實測試 IMEI
TEST_IMEI = "300434067857940"

def test_account_search():
    """測試 accountSearch"""
    print("\n" + "="*80)
    print("測試: accountSearch (用 IMEI 查詢帳號)")
    print("="*80)
    print(f"IMEI: {TEST_IMEI}")
    
    try:
        gateway = IWSGateway()
        
        # 構建請求
        action_name, soap_body = gateway._build_account_search_body(TEST_IMEI)
        
        # 發送請求
        response_xml = gateway._send_soap_request(
            soap_action=action_name,
            soap_body=soap_body
        )
        
        # 解析回應
        account_number = gateway._parse_account_search(response_xml)
        
        if account_number:
            print(f"✅ 找到帳號: {account_number}")
            return account_number
        else:
            print("❌ 未找到帳號")
            return None
            
    except Exception as e:
        print(f"❌ 搜尋失敗: {e}")
        return None

def test_suspend():
    """測試 setSubscriberAccountStatus - SUSPEND"""
    print("\n" + "="*80)
    print("測試: setSubscriberAccountStatus - SUSPEND")
    print("="*80)
    print(f"IMEI: {TEST_IMEI}")
    
    try:
        gateway = IWSGateway()
        result = gateway.suspend_subscriber(
            imei=TEST_IMEI,
            reason="測試暫停"
        )
        print(f"✅ 暫停成功")
        return True
    except IWSException as e:
        print(f"❌ 暫停失敗")
        print(f"錯誤碼: {e.error_code}")
        print(f"錯誤訊息: {str(e)}")
        if e.response_text:
            print(f"\n完整回應:")
            print(e.response_text[:500])
        return False
    except Exception as e:
        print(f"❌ 意外錯誤: {e}")
        return False

def test_update_plan(account_number=None):
    """測試 accountUpdate"""
    print("\n" + "="*80)
    print("測試: accountUpdate (變更費率)")
    print("="*80)
    print(f"IMEI: {TEST_IMEI}")
    if account_number:
        print(f"Account Number: {account_number}")
    
    try:
        gateway = IWSGateway()
        result = gateway.update_subscriber_plan(
            imei=TEST_IMEI,
            new_plan_id="17",
            lrit_flagstate="",
            ring_alerts_flag=False
        )
        print(f"✅ 變更成功")
        print(f"Transaction ID: {result.get('transaction_id')}")
        return True
    except IWSException as e:
        print(f"❌ 變更失敗")
        print(f"錯誤碼: {e.error_code}")
        print(f"錯誤訊息: {str(e)}")
        if e.response_text:
            print(f"\n完整回應:")
            print(e.response_text[:500])
        return False
    except Exception as e:
        print(f"❌ 意外錯誤: {e}")
        return False

def main():
    """執行診斷"""
    print("\n" + "="*80)
    print("IWS v6.8 診斷測試")
    print(f"測試 IMEI: {TEST_IMEI}")
    print("="*80)
    
    # 測試 1: 查詢帳號
    account_number = test_account_search()
    
    # 測試 2: 暫停設備
    test_suspend()
    
    # 測試 3: 變更費率
    test_update_plan(account_number)
    
    print("\n" + "="*80)
    print("診斷完成")
    print("="*80)

if __name__ == "__main__":
    main()

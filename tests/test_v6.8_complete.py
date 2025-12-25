"""
IWS Gateway v6.8 測試腳本
測試所有方法是否正常運作
"""
import sys
sys.path.insert(0, '/home/claude/SBD-Final')

from src.infrastructure.iws_gateway import IWSGateway, IWSException

def test_connection():
    """測試 1: 連線測試"""
    print("\n" + "="*80)
    print("測試 1: getSystemStatus (連線測試)")
    print("="*80)
    
    try:
        gateway = IWSGateway()
        result = gateway.check_connection()
        print("✅ 連線測試成功")
        return True
    except Exception as e:
        print(f"❌ 連線測試失敗: {e}")
        return False

def test_get_sbd_bundles():
    """測試 2: 查詢 SBD 方案"""
    print("\n" + "="*80)
    print("測試 2: getSBDBundles (查詢方案)")
    print("="*80)
    
    try:
        gateway = IWSGateway()
        result = gateway.get_sbd_bundles(
            from_bundle_id="0",
            for_activate=True
        )
        print(f"✅ 查詢成功，找到 {result['count']} 個方案")
        return True
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
        return False

def test_suspend():
    """測試 3: 暫停設備"""
    print("\n" + "="*80)
    print("測試 3: setSubscriberAccountStatus - SUSPEND")
    print("="*80)
    
    imei = "301434061231580"
    
    try:
        gateway = IWSGateway()
        result = gateway.suspend_subscriber(
            imei=imei,
            reason="測試暫停"
        )
        print(f"✅ 暫停成功")
        return True
    except Exception as e:
        print(f"❌ 暫停失敗: {e}")
        return False

def test_resume():
    """測試 4: 恢復設備"""
    print("\n" + "="*80)
    print("測試 4: setSubscriberAccountStatus - RESUME")
    print("="*80)
    
    imei = "301434061231580"
    
    try:
        gateway = IWSGateway()
        result = gateway.resume_subscriber(
            imei=imei,
            reason="測試恢復"
        )
        print(f"✅ 恢復成功")
        return True
    except Exception as e:
        print(f"❌ 恢復失敗: {e}")
        return False

def test_update_plan():
    """測試 5: 變更費率"""
    print("\n" + "="*80)
    print("測試 5: accountUpdate (變更費率)")
    print("="*80)
    
    imei = "301434061231580"
    
    try:
        gateway = IWSGateway()
        result = gateway.update_subscriber_plan(
            imei=imei,
            new_plan_id="17",
            lrit_flagstate="",
            ring_alerts_flag=False
        )
        print(f"✅ 變更成功")
        print(f"Transaction ID: {result.get('transaction_id')}")
        return True
    except Exception as e:
        print(f"❌ 變更失敗: {e}")
        return False

def main():
    """執行所有測試"""
    print("\n" + "="*80)
    print("IWS Gateway v6.8 完整測試")
    print("="*80)
    
    results = {
        "連線測試": test_connection(),
        "查詢方案": test_get_sbd_bundles(),
        "暫停設備": test_suspend(),
        "恢復設備": test_resume(),
        "變更費率": test_update_plan(),
    }
    
    print("\n" + "="*80)
    print("測試結果摘要")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("🎉 所有測試通過！")
    else:
        print("⚠️ 部分測試失敗，請檢查日誌")

if __name__ == "__main__":
    main()

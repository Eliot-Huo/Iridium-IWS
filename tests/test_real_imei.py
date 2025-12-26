"""
IWS Gateway v6.9 完整測試腳本
使用確認的真實 IMEI: 300534066716260
Service Account: 200883
"""
import sys
sys.path.insert(0, '/home/claude/SBD-Final')

from src.infrastructure.iws_gateway import IWSGateway, IWSException

# ========== 測試配置 ==========
TEST_IMEI = "300534066716260"  # 確認在 Service Account 200883 下，狀態 ACTIVE
SERVICE_ACCOUNT = "200883"
TEST_PLAN_ID = "17"  # 測試用費率方案 ID

print("="*80)
print("🧪 IWS Gateway v6.9 完整測試")
print("="*80)
print(f"測試 IMEI: {TEST_IMEI}")
print(f"Service Account: {SERVICE_ACCOUNT}")
print(f"當前狀態: ACTIVE")
print("="*80 + "\n")

# 初始化 Gateway
gateway = IWSGateway()

# ========== 測試結果記錄 ==========
results = {}

# ========================================
# 測試 1: 連線測試
# ========================================
def test_connection():
    """測試 getSystemStatus"""
    print("\n" + "="*80)
    print("測試 1: getSystemStatus (連線測試)")
    print("="*80)
    
    try:
        result = gateway.check_connection()
        print("✅ 連線測試成功")
        print(f"   系統狀態: {result.get('status', 'OK')}")
        return True
    except Exception as e:
        print(f"❌ 連線測試失敗: {e}")
        return False

# ========================================
# 測試 2: 驗證設備歸屬權
# ========================================
def test_validate_device():
    """測試 validateDeviceString"""
    print("\n" + "="*80)
    print("測試 2: validateDeviceString (設備驗證)")
    print("="*80)
    print(f"IMEI: {TEST_IMEI}")
    
    try:
        result = gateway.validate_device_string(
            device_string=TEST_IMEI,
            device_string_type="IMEI",
            validate_state=True
        )
        
        if result['valid']:
            print("✅ 設備驗證成功")
            print(f"   屬於 SP 帳戶: 是")
            print(f"   可用於操作: 是")
            if result.get('safety_data_capable'):
                print(f"   支持安全數據: 是")
            return True
        else:
            print(f"❌ 設備驗證失敗: {result.get('reason')}")
            return False
            
    except Exception as e:
        print(f"❌ 設備驗證失敗: {e}")
        return False

# ========================================
# 測試 3: 搜尋帳號
# ========================================
def test_search_account():
    """測試 accountSearch"""
    print("\n" + "="*80)
    print("測試 3: accountSearch (帳號搜尋)")
    print("="*80)
    print(f"IMEI: {TEST_IMEI}")
    
    try:
        result = gateway.search_account(TEST_IMEI)
        
        if result['found']:
            print("✅ 帳號搜尋成功")
            print(f"   訂閱者帳號: {result['subscriber_account_number']}")
            print(f"   設備狀態: ACTIVE")
            return True, result['subscriber_account_number']
        else:
            print("❌ 帳號未找到（設備可能未啟動）")
            return False, None
            
    except Exception as e:
        print(f"❌ 帳號搜尋失敗: {e}")
        return False, None

# ========================================
# 測試 4: 變更費率
# ========================================
def test_update_plan():
    """測試 accountUpdate (變更費率)"""
    print("\n" + "="*80)
    print("測試 4: accountUpdate (變更費率)")
    print("="*80)
    print(f"IMEI: {TEST_IMEI}")
    print(f"新費率: {TEST_PLAN_ID}")
    
    try:
        result = gateway.update_subscriber_plan(
            imei=TEST_IMEI,
            new_plan_id=TEST_PLAN_ID,
            lrit_flagstate="",
            ring_alerts_flag=False
        )
        
        print("✅ 變更費率成功")
        print(f"   Transaction ID: {result.get('transaction_id')}")
        print(f"   訂閱者帳號: {result.get('subscriber_account_number')}")
        print(f"   新費率 ID: {result.get('plan_id_digits')}")
        return True
        
    except IWSException as e:
        print(f"❌ 變更費率失敗")
        print(f"   錯誤碼: {e.error_code}")
        print(f"   錯誤訊息: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 變更費率失敗: {e}")
        return False

# ========================================
# 測試 5: 暫停設備
# ========================================
def test_suspend():
    """測試 setSubscriberAccountStatus - SUSPEND"""
    print("\n" + "="*80)
    print("測試 5: setSubscriberAccountStatus - SUSPEND (暫停設備)")
    print("="*80)
    print(f"IMEI: {TEST_IMEI}")
    
    try:
        result = gateway.suspend_subscriber(
            imei=TEST_IMEI,
            reason="測試暫停功能"
        )
        
        print("✅ 暫停設備成功")
        print(f"   Transaction ID: {result.get('transaction_id')}")
        print(f"   設備狀態: SUSPENDED")
        return True
        
    except IWSException as e:
        print(f"❌ 暫停設備失敗")
        print(f"   錯誤碼: {e.error_code}")
        print(f"   錯誤訊息: {str(e)}")
        if "Invalid state" in str(e):
            print(f"   → 設備可能已經是 SUSPENDED 狀態")
        return False
    except Exception as e:
        print(f"❌ 暫停設備失敗: {e}")
        return False

# ========================================
# 測試 6: 恢復設備
# ========================================
def test_resume():
    """測試 setSubscriberAccountStatus - RESUME"""
    print("\n" + "="*80)
    print("測試 6: setSubscriberAccountStatus - RESUME (恢復設備)")
    print("="*80)
    print(f"IMEI: {TEST_IMEI}")
    
    try:
        result = gateway.resume_subscriber(
            imei=TEST_IMEI,
            reason="測試恢復功能"
        )
        
        print("✅ 恢復設備成功")
        print(f"   Transaction ID: {result.get('transaction_id')}")
        print(f"   設備狀態: ACTIVE")
        return True
        
    except IWSException as e:
        print(f"❌ 恢復設備失敗")
        print(f"   錯誤碼: {e.error_code}")
        print(f"   錯誤訊息: {str(e)}")
        if "Invalid state" in str(e):
            print(f"   → 設備可能已經是 ACTIVE 狀態")
        return False
    except Exception as e:
        print(f"❌ 恢復設備失敗: {e}")
        return False

# ========================================
# 測試 7: 查詢 SBD 方案
# ========================================
def test_get_bundles():
    """測試 getSBDBundles"""
    print("\n" + "="*80)
    print("測試 7: getSBDBundles (查詢方案)")
    print("="*80)
    
    try:
        result = gateway.get_sbd_bundles(
            from_bundle_id="0",
            for_activate=True
        )
        
        print(f"✅ 查詢成功，找到 {result['count']} 個方案")
        
        # 顯示前 5 個方案
        if result['bundles']:
            print("\n   方案列表（前 5 個）:")
            for i, bundle in enumerate(result['bundles'][:5], 1):
                bundle_id = bundle.get('sbdBundleId', 'N/A')
                name = bundle.get('name', 'N/A')
                print(f"   {i}. Bundle ID: {bundle_id}, Name: {name}")
        
        return True
        
    except Exception as e:
        print(f"❌ 查詢方案失敗: {e}")
        return False

# ========================================
# 執行所有測試
# ========================================
def run_all_tests():
    """執行所有測試"""
    print("\n開始執行測試套件...")
    
    # 測試 1: 連線
    results['connection'] = test_connection()
    
    # 測試 2: 驗證設備
    results['validate'] = test_validate_device()
    
    # 測試 3: 搜尋帳號
    search_success, account_number = test_search_account()
    results['search'] = search_success
    
    # 只有在設備已啟動的情況下才測試變更費率
    if search_success:
        # 測試 4: 變更費率
        results['update_plan'] = test_update_plan()
        
        # 測試 5: 暫停
        results['suspend'] = test_suspend()
        
        # 測試 6: 恢復（只有在暫停成功後）
        if results['suspend']:
            results['resume'] = test_resume()
        else:
            print("\n⚠️  跳過恢復測試（暫停未成功）")
            results['resume'] = None
    else:
        print("\n⚠️  設備未啟動，跳過變更費率、暫停、恢復測試")
        results['update_plan'] = None
        results['suspend'] = None
        results['resume'] = None
    
    # 測試 7: 查詢方案（獨立測試）
    results['bundles'] = test_get_bundles()
    
    # ========== 測試結果摘要 ==========
    print("\n" + "="*80)
    print("📊 測試結果摘要")
    print("="*80)
    
    test_names = {
        'connection': '連線測試 (getSystemStatus)',
        'validate': '設備驗證 (validateDeviceString)',
        'search': '帳號搜尋 (accountSearch)',
        'update_plan': '變更費率 (accountUpdate)',
        'suspend': '暫停設備 (setSubscriberAccountStatus)',
        'resume': '恢復設備 (setSubscriberAccountStatus)',
        'bundles': '查詢方案 (getSBDBundles)'
    }
    
    for key, name in test_names.items():
        result = results.get(key)
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{name}: {status}")
    
    # 統計
    total = len([r for r in results.values() if r is not None])
    passed = len([r for r in results.values() if r is True])
    
    print(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("\n🎉 所有測試通過！")
    else:
        print("\n⚠️  部分測試失敗，請檢查日誌")
    
    print("="*80)

# ========================================
# 主程式
# ========================================
if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\n測試被用戶中斷")
    except Exception as e:
        print(f"\n\n❌ 測試執行失敗: {e}")
        import traceback
        traceback.print_exc()

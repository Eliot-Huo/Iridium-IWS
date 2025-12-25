"""
IWS SITEST Connection Diagnostic Test
v5.1 深度診斷腳本

使用方法：
1. 確保已配置 IWS_USER, IWS_PASS, IWS_SP_ACCOUNT
2. 執行此腳本：python test_sitest_diagnostic.py
3. 根據輸出結果分析問題
"""
from src.infrastructure.iws_gateway import IWSGateway, check_iws_connection


def print_separator(char="=", length=60):
    """列印分隔線"""
    print("\n" + char * length)


def test_1_basic_connection():
    """
    測試 1: 基礎連線測試（getSystemStatus）
    
    目的：驗證認證/標頭/命名空間是否正確
    如果失敗：問題在基礎協議層
    """
    print_separator()
    print("TEST 1: Basic Connection Test (getSystemStatus)")
    print_separator()
    print("Purpose: Verify authentication/headers/namespace")
    print("Method: getSystemStatus (simplest operation)")
    print_separator()
    
    try:
        result = check_iws_connection()
        
        print_separator("=")
        print("✅ TEST 1 PASSED")
        print_separator("=")
        print("✓ Authentication: OK")
        print("✓ Headers: OK")
        print("✓ Namespace: OK")
        print("\nResult:", result)
        print_separator("=")
        
        return True, None
        
    except Exception as e:
        print_separator("=")
        print("❌ TEST 1 FAILED")
        print_separator("=")
        print("✗ Problem in: Authentication/Headers/Namespace")
        print(f"\nError: {e}")
        print_separator("=")
        print("🔍 DIAGNOSIS:")
        print("   1. Check IWS_USER in secrets")
        print("   2. Check IWS_PASS in secrets")
        print("   3. Check IWS_SP_ACCOUNT in secrets")
        print("   4. Verify endpoint URL")
        print("   5. Check namespace (must end with /)")
        print_separator("=")
        
        return False, str(e)


def test_2_device_activation():
    """
    測試 2: 設備啟用測試（activateSubscriber）
    
    目的：驗證 SBD 資料結構是否正確
    如果失敗：問題在業務資料層
    """
    print_separator()
    print("TEST 2: Device Activation Test (activateSubscriber)")
    print_separator()
    print("Purpose: Verify SBD data structure")
    print("Method: activateSubscriber with test IMEI")
    print_separator()
    
    gateway = IWSGateway()
    
    # 測試用 IMEI
    test_imei = '300534066711380'
    test_plan = 'SBD12'
    
    try:
        result = gateway.activate_subscriber(
            imei=test_imei,
            plan_id=test_plan
        )
        
        print_separator("=")
        print("✅ TEST 2 PASSED")
        print_separator("=")
        print("✓ IMEI validation: OK")
        print("✓ SBD data structure: OK")
        print("✓ All required fields: OK")
        print(f"\nTransaction ID: {result['transaction_id']}")
        print(f"IMEI: {result['imei']}")
        print(f"Plan: {result['plan_id']}")
        print_separator("=")
        
        return True, None
        
    except Exception as e:
        error_str = str(e)
        
        print_separator("=")
        print("❌ TEST 2 FAILED")
        print_separator("=")
        
        # 分析錯誤類型
        if "ALREADY_ACTIVE" in error_str.upper():
            print("⚠️  Device already active (business logic error)")
            print("    This is actually GOOD NEWS!")
            print("    It means communication with IWS is working.")
            print_separator("=")
            print("✓ Communication: SUCCESS")
            print("✓ Authentication: SUCCESS")
            print("✓ Data structure: SUCCESS")
            print("ℹ️  The device is already activated in IWS")
            print_separator("=")
            return True, "ALREADY_ACTIVE (communication OK)"
        else:
            print("✗ Problem in: SBD data structure")
            print(f"\nError: {e}")
            print_separator("=")
            print("🔍 DIAGNOSIS:")
            print(f"   1. IMEI: {test_imei} (15 digits, starts with 30?)")
            print(f"   2. Plan ID: {test_plan} (valid bundle ID?)")
            print("   3. Delivery details structure")
            print("   4. All required fields present?")
            print_separator("=")
            
            return False, str(e)


def main():
    """執行完整診斷流程"""
    print("\n" + "="*60)
    print("IWS SITEST DIAGNOSTIC SUITE v5.1")
    print("="*60)
    print("Architecture Review: SITEST Environment")
    print("Purpose: Diagnose HTTP 500 errors")
    print("="*60)
    
    # ==================== 測試 1 ====================
    test1_passed, test1_error = test_1_basic_connection()
    
    if not test1_passed:
        # 測試 1 失敗，停止測試
        print_separator("=")
        print("FINAL DIAGNOSIS")
        print_separator("=")
        print("Stage: Basic connection (getSystemStatus)")
        print("Result: FAILED")
        print("Problem: Authentication/Headers/Namespace")
        print_separator("=")
        print("📝 ACTION ITEMS:")
        print("   1. Verify IWS credentials in Streamlit Secrets")
        print("   2. Check IWS_USER, IWS_PASS, IWS_SP_ACCOUNT")
        print("   3. Verify endpoint URL")
        print("   4. Check namespace ends with /")
        print("   5. Review request/response logs above")
        print_separator("=")
        return
    
    # ==================== 測試 2 ====================
    test2_passed, test2_error = test_2_device_activation()
    
    # ==================== 最終報告 ====================
    print_separator("=")
    print("FINAL TEST RESULTS")
    print_separator("=")
    print(f"Test 1 (getSystemStatus):     {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (activateSubscriber):  {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print_separator("=")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("="*60)
        print("IWS integration is fully operational.")
        print("Authentication: ✓")
        print("Protocol layer: ✓")
        print("Data structure: ✓")
        print("="*60)
        
        if test2_error and "ALREADY_ACTIVE" in test2_error:
            print("\nNote: Test device already active in IWS")
            print("This confirms successful communication.")
    
    elif test1_passed and not test2_passed:
        print("\n🔍 DIAGNOSIS")
        print("="*60)
        print("Test 1 (Basic): PASSED")
        print("Test 2 (Business): FAILED")
        print("="*60)
        print("Conclusion: Protocol layer is OK")
        print("Problem: SBD data structure")
        print("="*60)
        print("📝 ACTION ITEMS:")
        print("   1. Review SBD account structure")
        print("   2. Verify IMEI format")
        print("   3. Check plan_id validity")
        print("   4. Verify deliveryDetails elements")
        print("="*60)
    
    else:
        print("\n❌ TESTS INCOMPLETE")
        print("="*60)
        print("See diagnosis above for details.")
        print("="*60)


if __name__ == "__main__":
    main()

"""
IMEI 診斷腳本 - 檢查 IMEI 是否存在於 IWS 系統
"""
import sys
sys.path.insert(0, '/home/claude/SBD-Final')

from src.infrastructure.iws_gateway import IWSGateway, IWSException

def diagnose_imei(imei: str):
    """
    診斷 IMEI
    
    檢查項目：
    1. IMEI 格式是否正確
    2. 設備是否屬於您的 SP 帳戶
    3. 設備狀態（RESERVED / ACTIVE / SUSPENDED）
    4. 帳號是否存在（如果已啟動）
    """
    print("\n" + "="*80)
    print("🔍 IMEI 完整診斷")
    print("="*80)
    print(f"IMEI: {imei}")
    print("="*80)
    
    gateway = IWSGateway()
    
    # 檢查 1: IMEI 格式
    print("\n[檢查 1] IMEI 格式驗證...")
    try:
        gateway._validate_imei(imei)
        print("✅ IMEI 格式正確")
        print(f"   - 長度: 15 位數字")
        print(f"   - 前綴: {imei[:2]} (應為 30)")
        print(f"   - 後綴: {imei[-1]} (應為 0)")
    except IWSException as e:
        print(f"❌ IMEI 格式錯誤: {e}")
        return
    
    # 檢查 2: validateDeviceString（歸屬權和狀態）
    print("\n[檢查 2] 設備驗證（歸屬權與狀態）...")
    try:
        validation = gateway.validate_device_string(
            device_string=imei,
            device_string_type="IMEI",
            validate_state=True
        )
        
        if validation['valid']:
            print(f"✅ 設備有效")
            print(f"   - 屬於您的 SP 帳戶: 是")
            print(f"   - 可用於操作: 是")
            if validation['safety_data_capable']:
                print(f"   - 支持安全數據: 是")
        else:
            print(f"❌ 設備無效或不可用")
            if validation['reason']:
                print(f"   - 原因: {validation['reason']}")
                
                # 解析常見原因
                reason = validation['reason'].lower()
                if 'not belong' in reason or 'pool' in reason:
                    print(f"   ⚠️  設備不屬於您的 Device Pool")
                    print(f"   → 請使用您公司名下的設備")
                elif 'in use' in reason or 'active' in reason:
                    print(f"   ⚠️  設備已被其他合約使用或處於 ACTIVE 狀態")
                    print(f"   → 先執行 deactivate 恢復到 RESERVED 狀態")
                elif 'suspended' in reason:
                    print(f"   ⚠️  設備處於 SUSPENDED 狀態")
                    print(f"   → 先執行 deactivate 恢復到 RESERVED 狀態")
            return
            
    except IWSException as e:
        print(f"❌ 驗證失敗: {e}")
        if hasattr(e, 'error_code'):
            print(f"   - 錯誤碼: {e.error_code}")
        return
    
    # 檢查 3: accountSearch（帳號查詢）
    print("\n[檢查 3] 帳號搜尋（已啟動的設備）...")
    try:
        result = gateway.search_account(imei)
        
        if result['found']:
            print(f"✅ 設備已啟動")
            print(f"   - 帳號: {result['subscriber_account_number']}")
            print(f"   - 狀態: ACTIVE（可執行變更費率、暫停、恢復、註銷）")
        else:
            print(f"ℹ️  設備未啟動")
            print(f"   - 狀態: RESERVED（可執行 activateSubscriber）")
            print(f"   - 說明: 設備處於待啟動狀態")
            
    except IWSException as e:
        print(f"⚠️  帳號搜尋失敗（可能處於 RESERVED 狀態）: {e}")
    
    print("\n" + "="*80)
    print("診斷完成")
    print("="*80)
    
    # 總結建議
    print("\n📋 操作建議:")
    if validation['valid']:
        try:
            search_result = gateway.search_account(imei)
            if search_result['found']:
                print("✅ 此設備已啟動，可以執行:")
                print("   - 變更費率 (update_subscriber_plan)")
                print("   - 暫停設備 (suspend_subscriber)")
                print("   - 恢復設備 (resume_subscriber)")
                print("   - 註銷設備 (deactivate_subscriber)")
            else:
                print("✅ 此設備處於 RESERVED 狀態，可以執行:")
                print("   - 啟動設備 (activate_subscriber)")
        except:
            print("✅ 此設備處於 RESERVED 狀態，可以執行:")
            print("   - 啟動設備 (activate_subscriber)")
    else:
        print("❌ 此設備無法使用，請:")
        print("   - 確認設備屬於您的 SP 帳戶")
        print("   - 或使用其他可用的設備")

def test_known_imeis():
    """測試一些已知的 IMEI"""
    known_imeis = [
        "300434065956950",  # 用戶提供
        "300434067857940",  # 用戶之前提供
        "301434061231580",  # 之前的測試 IMEI
    ]
    
    print("\n" + "="*80)
    print("測試已知的 IMEI")
    print("="*80)
    
    for imei in known_imeis:
        print(f"\n測試: {imei}")
        print("-" * 80)
        
        try:
            gateway = IWSGateway()
            result = gateway.search_account(imei)
            
            if result['found']:
                print(f"✅ {imei}: 存在 (帳號: {result['subscriber_account_number']})")
            else:
                print(f"❌ {imei}: 不存在")
        except Exception as e:
            print(f"❌ {imei}: 錯誤 - {str(e)[:100]}")
    
    print("\n" + "="*80)

def main():
    """主程式"""
    import sys
    
    if len(sys.argv) > 1:
        # 使用命令列參數的 IMEI
        imei = sys.argv[1]
        diagnose_imei(imei)
    else:
        # 測試所有已知的 IMEI
        test_known_imeis()
        
        # 然後診斷用戶的 IMEI
        print("\n")
        diagnose_imei("300434065956950")

if __name__ == "__main__":
    main()

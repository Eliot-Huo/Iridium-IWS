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
    2. 帳號是否存在
    3. 如果存在，顯示帳號資訊
    """
    print("\n" + "="*80)
    print("🔍 IMEI 診斷")
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
    
    # 檢查 2: 帳號搜尋
    print("\n[檢查 2] 搜尋帳號...")
    try:
        result = gateway.search_account(imei)
        
        if result['found']:
            print(f"✅ 帳號存在")
            print(f"   - 帳號: {result['subscriber_account_number']}")
            print(f"   - 狀態: 可以進行變更費率、暫停、恢復、註銷等操作")
        else:
            print(f"❌ 帳號不存在")
            print(f"   - 原因: 設備尚未在 IWS 系統中啟用")
            print(f"   - 建議:")
            print(f"     1. 確認 IMEI 是否正確")
            print(f"     2. 檢查設備是否已在 SITEST 環境啟用")
            print(f"     3. 嘗試使用其他已知的測試 IMEI")
            
    except IWSException as e:
        print(f"❌ 搜尋失敗: {e}")
        if hasattr(e, 'error_code'):
            print(f"   - 錯誤碼: {e.error_code}")
        if hasattr(e, 'response_text') and e.response_text:
            print(f"   - 回應預覽: {e.response_text[:200]}")
    
    print("\n" + "="*80)
    print("診斷完成")
    print("="*80)

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

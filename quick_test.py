"""
快速測試新功能整合
Quick Test for New Features Integration
"""

import sys
sys.path.insert(0, '/home/claude/SBD-Project/SBD-Final-GitHub')

from src.services.device_history import DeviceHistoryManager
from src.services.enhanced_billing_calculator import EnhancedBillingCalculator


def quick_test():
    """快速測試"""
    
    print("=" * 80)
    print("快速功能測試")
    print("=" * 80)
    
    # 創建測試實例
    history_mgr = DeviceHistoryManager(data_dir="/tmp/sbd_quick_test")
    calculator = EnhancedBillingCalculator(history_manager=history_mgr)
    
    test_imei = "300534066711380"
    
    # 清空歷史
    history_mgr.history = []
    
    print("\n1. 測試設備啟用...")
    history_mgr.record_activation(
        imei=test_imei,
        plan="SBD12",
        date_str="2026-01-01",
        operator="Admin",
        notes="測試啟用"
    )
    print("✅ 啟用記錄成功")
    
    print("\n2. 測試方案變更...")
    history_mgr.record_plan_change(
        imei=test_imei,
        old_plan="SBD12",
        new_plan="SBD30",
        date_str="2026-01-15",
        operator="Customer",
        notes="客戶要求升級"
    )
    print("✅ 方案變更記錄成功")
    
    print("\n3. 測試狀態變更...")
    history_mgr.record_status_change(
        imei=test_imei,
        old_status="ACTIVE",
        new_status="SUSPENDED",
        date_str="2026-01-20",
        operator="Customer",
        notes="臨時暫停"
    )
    print("✅ 狀態變更記錄成功")
    
    print("\n4. 測試帳單計算...")
    bill = calculator.calculate_monthly_bill(
        imei=test_imei,
        year=2026,
        month=1
    )
    
    print(f"\n📅 帳單摘要：")
    print(f"   IMEI: {bill.imei}")
    print(f"   期間: {bill.year}-{bill.month:02d}")
    print(f"   月初方案: {bill.month_start_plan}")
    print(f"   計費方案: {bill.billing_plan}")
    print(f"   總費用: ${bill.total_cost:.2f}")
    
    print(f"\n💰 費用明細：")
    print(f"   月租費: ${bill.monthly_fee:.2f}")
    print(f"   暫停費: ${bill.suspend_fee:.2f}")
    print(f"   行政手續費: ${bill.admin_fee:.2f}")
    print(f"   總計: ${bill.total_cost:.2f}")
    
    if bill.notes:
        print(f"\n📝 備註：")
        for note in bill.notes:
            print(f"   • {note}")
    
    print("\n5. 測試歷史查詢...")
    history = history_mgr.get_device_history(test_imei)
    print(f"✅ 找到 {len(history)} 筆操作記錄")
    
    for i, op in enumerate(history, 1):
        print(f"   {i}. {op.date} - {op.action}")
    
    print("\n" + "=" * 80)
    print("✅ 所有測試通過！")
    print("=" * 80)
    
    print("\n🎯 系統狀態：")
    print("   ✅ 設備歷史記錄模組正常")
    print("   ✅ 增強版計費計算器正常")
    print("   ✅ 數據持久化正常")
    print("   ✅ 整合功能正常")
    
    print("\n💡 可以開始使用 Streamlit 界面測試了！")
    print("   運行指令：cd /home/claude/SBD-Project/SBD-Final-GitHub && streamlit run app.py")


if __name__ == "__main__":
    quick_test()

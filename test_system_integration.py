"""
計費系統整合測試
測試新的計費邏輯是否正確整合到系統
"""

import sys
sys.path.insert(0, '/home/claude/SBD-Project/SBD-Final-GitHub')

from src.services.device_history import DeviceHistoryManager
from src.services.enhanced_billing_calculator import EnhancedBillingCalculator


def test_billing_system_integration():
    """測試計費系統整合"""
    
    print("=" * 80)
    print("計費系統整合測試")
    print("=" * 80)
    
    # 創建測試用的管理器
    history_mgr = DeviceHistoryManager(data_dir="/tmp/sbd_test_data")
    calculator = EnhancedBillingCalculator(history_manager=history_mgr)
    
    test_imei = "300534066711380"
    
    # 場景：月底升級測試
    print("\n" + "=" * 80)
    print("場景 1：月底升級")
    print("=" * 80)
    
    # 清空歷史（測試用）
    history_mgr.history = []
    
    # 記錄操作
    history_mgr.record_activation(
        imei=test_imei,
        plan="SBD12",
        date_str="2026-01-01",
        operator="System",
        notes="初始啟用"
    )
    
    history_mgr.record_plan_change(
        imei=test_imei,
        old_plan="SBD12",
        new_plan="SBD30",
        date_str="2026-01-31",
        operator="Customer",
        notes="月底升級測試"
    )
    
    # 計算1月帳單
    bill = calculator.calculate_monthly_bill(
        imei=test_imei,
        year=2026,
        month=1
    )
    
    # 顯示帳單
    print(f"\n📅 {bill.year}-{bill.month:02d} 月帳單")
    print(f"IMEI: {bill.imei}")
    print(f"\n月初狀態: {bill.month_start_status} ({bill.month_start_plan})")
    print(f"計費方案: {bill.billing_plan} (月租 ${bill.billing_plan_rate:.2f})")
    
    if bill.plan_changes:
        print(f"\n方案變更:")
        for change in bill.plan_changes:
            print(f"  {change['date']}: {change['details']}")
    
    if bill.status_changes:
        print(f"\n狀態變更:")
        for change in bill.status_changes:
            print(f"  {change['date']}: {change['details']}")
    
    print(f"\n💰 費用明細:")
    print(f"  月租費: ${bill.monthly_fee:.2f}")
    if bill.suspend_fee > 0:
        print(f"  暫停管理費: ${bill.suspend_fee:.2f}")
    if bill.admin_fee > 0:
        print(f"  行政手續費: ${bill.admin_fee:.2f}")
    if bill.overage_fee > 0:
        print(f"  超量費: ${bill.overage_fee:.2f}")
    
    print(f"\n  總計: ${bill.total_cost:.2f}")
    
    if bill.notes:
        print(f"\n📝 備註:")
        for note in bill.notes:
            print(f"  • {note}")
    
    # 驗證
    assert bill.billing_plan == "SBD30", "應使用升級後的 SBD30"
    assert bill.total_cost == 50.00, "應收取 SBD30 月租 $50"
    print("\n✅ 場景 1 通過")
    
    # 場景 2：頻繁暫停
    print("\n\n" + "=" * 80)
    print("場景 2：頻繁暫停（觸發行政手續費）")
    print("=" * 80)
    
    # 清空並重新設置
    history_mgr.history = []
    
    history_mgr.record_activation(
        imei=test_imei,
        plan="SBD12",
        date_str="2026-02-01",
        operator="System"
    )
    
    # 暫停 5 次
    for i in range(1, 6):
        day = i * 5
        if day > 25:
            day = 25
        
        history_mgr.record_status_change(
            imei=test_imei,
            old_status="ACTIVE",
            new_status="SUSPENDED",
            date_str=f"2026-02-{day:02d}",
            operator="Customer"
        )
        
        if i < 5:
            history_mgr.record_status_change(
                imei=test_imei,
                old_status="SUSPENDED",
                new_status="ACTIVE",
                date_str=f"2026-02-{day:02d}",
                operator="Customer"
            )
    
    # 計算2月帳單
    bill2 = calculator.calculate_monthly_bill(
        imei=test_imei,
        year=2026,
        month=2
    )
    
    print(f"\n📅 {bill2.year}-{bill2.month:02d} 月帳單")
    print(f"IMEI: {bill2.imei}")
    print(f"\n月初狀態: {bill2.month_start_status} ({bill2.month_start_plan})")
    print(f"計費方案: {bill2.billing_plan}")
    print(f"暫停次數: {bill2.suspend_count} 次")
    
    print(f"\n💰 費用明細:")
    print(f"  月租費: ${bill2.monthly_fee:.2f}")
    print(f"  暫停管理費: ${bill2.suspend_fee:.2f}")
    print(f"  行政手續費: ${bill2.admin_fee:.2f} ({bill2.suspend_count} 次 × $20)")
    print(f"\n  總計: ${bill2.total_cost:.2f}")
    
    if bill2.notes:
        print(f"\n📝 備註:")
        for note in bill2.notes:
            print(f"  • {note}")
    
    # 驗證
    assert bill2.suspend_count == 5, "應記錄 5 次暫停"
    assert bill2.admin_fee == 100.00, "行政手續費應為 $100 (5 × $20)"
    print("\n✅ 場景 2 通過")
    
    # 場景 3：升級 + 暫停 + 降級
    print("\n\n" + "=" * 80)
    print("場景 3：複雜組合（升級 + 暫停 + 降級）")
    print("=" * 80)
    
    history_mgr.history = []
    
    history_mgr.record_activation(
        imei=test_imei,
        plan="SBD12",
        date_str="2026-03-01",
        operator="System"
    )
    
    history_mgr.record_plan_change(
        imei=test_imei,
        old_plan="SBD12",
        new_plan="SBD30",
        date_str="2026-03-10",
        operator="Customer",
        notes="升級"
    )
    
    history_mgr.record_status_change(
        imei=test_imei,
        old_status="ACTIVE",
        new_status="SUSPENDED",
        date_str="2026-03-15",
        operator="Customer"
    )
    
    history_mgr.record_status_change(
        imei=test_imei,
        old_status="SUSPENDED",
        new_status="ACTIVE",
        date_str="2026-03-20",
        operator="Customer"
    )
    
    history_mgr.record_plan_change(
        imei=test_imei,
        old_plan="SBD30",
        new_plan="SBD12",
        date_str="2026-03-25",
        operator="Customer",
        notes="降級"
    )
    
    bill3 = calculator.calculate_monthly_bill(
        imei=test_imei,
        year=2026,
        month=3
    )
    
    print(f"\n📅 {bill3.year}-{bill3.month:02d} 月帳單")
    print(f"IMEI: {bill3.imei}")
    print(f"\n月初狀態: {bill3.month_start_status} ({bill3.month_start_plan})")
    print(f"計費方案: {bill3.billing_plan} (升級生效)")
    
    print(f"\n方案變更:")
    for change in bill3.plan_changes:
        print(f"  {change['date']}: {change['details']}")
    
    print(f"\n狀態變更:")
    for change in bill3.status_changes:
        print(f"  {change['date']}: {change['details']}")
    
    print(f"\n💰 費用明細:")
    print(f"  月租費: ${bill3.monthly_fee:.2f}")
    print(f"  暫停管理費: ${bill3.suspend_fee:.2f}")
    print(f"\n  總計: ${bill3.total_cost:.2f}")
    
    if bill3.notes:
        print(f"\n📝 備註:")
        for note in bill3.notes:
            print(f"  • {note}")
    
    # 驗證
    assert bill3.billing_plan == "SBD30", "應使用升級後的 SBD30"
    assert bill3.total_cost == 104.00, "應為 $104 (暫停恢復雙重收費)"
    print("\n✅ 場景 3 通過")
    
    print("\n\n" + "=" * 80)
    print("✅ 所有整合測試通過！")
    print("=" * 80)
    
    print("\n🎯 測試總結:")
    print("  ✅ 設備歷史記錄模組正常運作")
    print("  ✅ 增強版計費計算器正確整合")
    print("  ✅ 升級當月生效邏輯正確")
    print("  ✅ 降級次月生效邏輯正確")
    print("  ✅ 暫停/恢復雙重收費正確")
    print("  ✅ 行政手續費計算正確")
    print("  ✅ 複雜組合場景處理正確")
    print("\n💡 系統已準備好整合到生產環境！")


if __name__ == "__main__":
    test_billing_system_integration()

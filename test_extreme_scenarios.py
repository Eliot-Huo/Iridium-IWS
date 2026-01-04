"""
IoT 計費邏輯極端情況測試
目標：驗證計費邏輯在各種極端情況下的正確性

測試策略：
1. 設計極端場景
2. 模擬操作歷史
3. 計算月帳單
4. 驗證結果
5. 確保符合合約
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json

class IoTBillingLogicTester:
    """IoT 計費邏輯測試器"""
    
    def __init__(self):
        self.imei = "300534066711380"
        self.device_history = []
        
        # 費率表
        self.rates = {
            'SBD0': {'monthly_rate': 20.00, 'included_bytes': 0, 'overage_rate': 2.10},
            'SBD12': {'monthly_rate': 28.00, 'included_bytes': 12000, 'overage_rate': 2.00},
            'SBD17': {'monthly_rate': 30.00, 'included_bytes': 17000, 'overage_rate': 1.60},
            'SBD30': {'monthly_rate': 50.00, 'included_bytes': 30000, 'overage_rate': 1.50}
        }
        
        # 費率順序（用於判斷升降級）
        self.plan_order = {'SBD0': 1, 'SBD12': 2, 'SBD17': 3, 'SBD30': 4}
    
    def add_operation(self, date: str, action: str, **kwargs):
        """添加操作記錄"""
        operation = {
            'date': date,
            'imei': self.imei,
            'action': action,
            **kwargs
        }
        self.device_history.append(operation)
    
    def is_upgrade(self, old_plan: str, new_plan: str) -> bool:
        """判斷是否為升級"""
        return self.plan_order[new_plan] > self.plan_order[old_plan]
    
    def get_month_start_state(self, year: int, month: int) -> Tuple[str, str]:
        """
        獲取月初狀態
        
        Returns:
            (plan, status) - 月初的方案和狀態
        """
        target_date = f"{year}-{month:02d}-01"
        
        current_plan = None
        current_status = None
        
        # 按日期排序
        sorted_history = sorted(self.device_history, key=lambda x: x['date'])
        
        for record in sorted_history:
            if record['date'] >= target_date:
                break
            
            if record['action'] == 'ACTIVATE':
                current_plan = record['plan']
                current_status = record['status']
            elif record['action'] == 'PLAN_CHANGE':
                current_plan = record['new_plan']
            elif record['action'] == 'STATUS_CHANGE':
                current_status = record['new_status']
                if 'plan' in record:
                    current_plan = record['plan']
        
        # 如果在目標月份的操作中有啟用，使用它
        for record in sorted_history:
            if record['date'] < target_date:
                continue
            if record['date'] >= target_date and record['action'] == 'ACTIVATE':
                current_plan = record['plan']
                current_status = record['status']
                break
        
        return current_plan, current_status
    
    def get_operations_in_month(self, year: int, month: int) -> List[Dict]:
        """獲取該月的所有操作"""
        month_start = f"{year}-{month:02d}-01"
        
        # 計算月底
        if month == 12:
            month_end = f"{year+1}-01-01"
        else:
            month_end = f"{year}-{month+1:02d}-01"
        
        operations = []
        for record in self.device_history:
            if month_start <= record['date'] < month_end:
                operations.append(record)
        
        return operations
    
    def get_billing_plan(self, year: int, month: int) -> str:
        """
        確定計費方案
        
        規則：
        1. 從月初方案開始
        2. 檢查該月的升級（立即生效）
        3. 忽略降級（次月生效）
        """
        start_plan, _ = self.get_month_start_state(year, month)
        
        if not start_plan:
            return None
        
        billing_plan = start_plan
        operations = self.get_operations_in_month(year, month)
        
        # 檢查升級
        for op in operations:
            if op['action'] == 'PLAN_CHANGE':
                if self.is_upgrade(op['old_plan'], op['new_plan']):
                    # 升級 → 立即生效
                    billing_plan = op['new_plan']
                # 降級忽略
        
        return billing_plan
    
    def count_suspend_actions(self, year: int, month: int) -> int:
        """計算該月暫停次數"""
        operations = self.get_operations_in_month(year, month)
        
        suspend_count = 0
        for op in operations:
            if op['action'] == 'STATUS_CHANGE' and op['new_status'] == 'SUSPENDED':
                suspend_count += 1
        
        return suspend_count
    
    def get_status_changes(self, year: int, month: int) -> List[Dict]:
        """獲取該月的狀態變更"""
        operations = self.get_operations_in_month(year, month)
        
        changes = []
        for op in operations:
            if op['action'] == 'STATUS_CHANGE':
                changes.append(op)
        
        return changes
    
    def calculate_monthly_bill(self, year: int, month: int) -> Dict:
        """
        計算月帳單
        
        Returns:
            {
                'month': '2026-01',
                'start_plan': 'SBD12',
                'start_status': 'ACTIVE',
                'billing_plan': 'SBD30',
                'operations': [...],
                'fees': {...},
                'total': 123.45
            }
        """
        # 月初狀態
        start_plan, start_status = self.get_month_start_state(year, month)
        
        if not start_plan:
            return None
        
        # 計費方案
        billing_plan = self.get_billing_plan(year, month)
        
        # 該月操作
        operations = self.get_operations_in_month(year, month)
        
        # 狀態變更
        status_changes = self.get_status_changes(year, month)
        
        # 暫停次數
        suspend_count = self.count_suspend_actions(year, month)
        
        # 費用明細
        fees = {}
        total = 0.0
        
        # 基本月租費
        monthly_rate = self.rates[billing_plan]['monthly_rate']
        
        # 根據狀態變更計算費用
        if not status_changes:
            # 無狀態變更
            fees['monthly_fee'] = monthly_rate
            total += monthly_rate
        
        elif len(status_changes) == 1:
            # 一次狀態變更
            change = status_changes[0]
            
            if change['new_status'] == 'SUSPENDED':
                # ACTIVE → SUSPENDED
                fees['monthly_fee'] = monthly_rate
                fees['suspend_fee'] = 4.00
                total += monthly_rate + 4.00
            else:
                # SUSPENDED → ACTIVE
                fees['suspend_fee'] = 4.00
                fees['monthly_fee'] = monthly_rate
                total += 4.00 + monthly_rate
        
        else:
            # 多次狀態變更（暫停又恢復）
            fees['monthly_fee_1'] = monthly_rate
            fees['suspend_fee'] = 4.00
            fees['monthly_fee_2'] = monthly_rate
            total += monthly_rate + 4.00 + monthly_rate
        
        # 行政手續費（第3次暫停起）
        if suspend_count >= 3:
            admin_fee = suspend_count * 20.00
            fees['admin_fee'] = admin_fee
            fees['admin_fee_detail'] = f"${suspend_count} × $20 = ${admin_fee:.2f}"
            total += admin_fee
        
        return {
            'month': f"{year}-{month:02d}",
            'start_plan': start_plan,
            'start_status': start_status,
            'billing_plan': billing_plan,
            'operations': operations,
            'status_changes': status_changes,
            'suspend_count': suspend_count,
            'fees': fees,
            'total': total
        }
    
    def verify_contract_compliance(self, bill: Dict) -> Dict:
        """
        驗證是否符合合約規定
        
        Returns:
            {
                'compliant': True/False,
                'checks': [...]
            }
        """
        checks = []
        compliant = True
        
        # 檢查 1：升級是否當月生效
        for op in bill['operations']:
            if op['action'] == 'PLAN_CHANGE':
                old_plan = op['old_plan']
                new_plan = op['new_plan']
                
                if self.is_upgrade(old_plan, new_plan):
                    # 升級應該立即生效
                    if bill['billing_plan'] == new_plan:
                        checks.append({
                            'rule': '升級當月生效',
                            'status': '✅ 通過',
                            'detail': f"{old_plan} → {new_plan} 當月計費為 {bill['billing_plan']}"
                        })
                    else:
                        checks.append({
                            'rule': '升級當月生效',
                            'status': '❌ 失敗',
                            'detail': f"{old_plan} → {new_plan} 應計費 {new_plan}，實際 {bill['billing_plan']}"
                        })
                        compliant = False
        
        # 檢查 2：暫停次數與手續費
        if bill['suspend_count'] >= 3:
            expected_fee = bill['suspend_count'] * 20.00
            actual_fee = bill['fees'].get('admin_fee', 0)
            
            if actual_fee == expected_fee:
                checks.append({
                    'rule': '行政手續費',
                    'status': '✅ 通過',
                    'detail': f"暫停 {bill['suspend_count']} 次，收費 ${actual_fee:.2f}"
                })
            else:
                checks.append({
                    'rule': '行政手續費',
                    'status': '❌ 失敗',
                    'detail': f"應收 ${expected_fee:.2f}，實收 ${actual_fee:.2f}"
                })
                compliant = False
        
        # 檢查 3：狀態變更費用
        if bill['status_changes']:
            if len(bill['status_changes']) == 1:
                # 應該有雙重收費
                has_monthly = 'monthly_fee' in bill['fees']
                has_suspend = 'suspend_fee' in bill['fees']
                
                if has_monthly and has_suspend:
                    checks.append({
                        'rule': '狀態變更雙重收費',
                        'status': '✅ 通過',
                        'detail': '一次狀態變更，收取雙重費用'
                    })
                else:
                    checks.append({
                        'rule': '狀態變更雙重收費',
                        'status': '❌ 失敗',
                        'detail': '缺少必要費用'
                    })
                    compliant = False
        
        return {
            'compliant': compliant,
            'checks': checks
        }
    
    def print_bill(self, bill: Dict):
        """打印月帳單"""
        print("=" * 80)
        print(f"📅 {bill['month']} 月帳單")
        print("=" * 80)
        
        print(f"\n月初狀態: {bill['start_status']} ({bill['start_plan']})")
        print(f"計費方案: {bill['billing_plan']}")
        
        if bill['operations']:
            print(f"\n月內操作:")
            for op in bill['operations']:
                date = op['date']
                action = op['action']
                
                if action == 'PLAN_CHANGE':
                    old = op['old_plan']
                    new = op['new_plan']
                    upgrade_mark = '✓ 升級' if self.is_upgrade(old, new) else '✗ 降級'
                    print(f"  {date}: {old} → {new} {upgrade_mark}")
                
                elif action == 'STATUS_CHANGE':
                    old = op['old_status']
                    new = op['new_status']
                    print(f"  {date}: {old} → {new}")
        
        if bill['suspend_count'] > 0:
            print(f"\n暫停次數: {bill['suspend_count']} 次")
            if bill['suspend_count'] >= 3:
                print(f"  ⚠️ 觸發行政手續費")
        
        print(f"\n💰 費用明細:")
        for key, value in bill['fees'].items():
            if key == 'admin_fee_detail':
                continue
            
            if key == 'monthly_fee':
                label = f"{bill['billing_plan']} 月租費"
            elif key == 'monthly_fee_1':
                label = f"{bill['billing_plan']} 月租費（暫停前）"
            elif key == 'monthly_fee_2':
                label = f"{bill['billing_plan']} 月租費（恢復後）"
            elif key == 'suspend_fee':
                label = "暫停管理費"
            elif key == 'admin_fee':
                label = "行政手續費"
                detail = bill['fees'].get('admin_fee_detail', '')
                if detail:
                    label += f" ({detail})"
            else:
                label = key
            
            print(f"  {label}: ${value:.2f}")
        
        print(f"\n  {'─' * 40}")
        print(f"  總計: ${bill['total']:.2f}")
        print(f"  {'─' * 40}")
    
    def print_verification(self, verification: Dict):
        """打印驗證結果"""
        print(f"\n🔍 合約符合性驗證:")
        
        for check in verification['checks']:
            print(f"  {check['status']} {check['rule']}")
            print(f"      {check['detail']}")
        
        if verification['compliant']:
            print(f"\n✅ 所有檢查通過，符合合約規定")
        else:
            print(f"\n❌ 發現不符合項目，需要修正")


# ==================== 測試場景 ====================

def test_extreme_scenarios():
    """測試極端場景"""
    
    print("=" * 80)
    print("IoT 計費邏輯極端情況測試")
    print("=" * 80)
    print(f"\n目標：驗證計費邏輯在各種極端情況下的正確性")
    print(f"確保：所有情況都符合合約規定，公司不吃虧\n")
    
    # ==================== 場景 1：月底升級 ====================
    print("\n" + "=" * 80)
    print("場景 1：月底最後一天升級")
    print("=" * 80)
    print("目的：驗證月底升級也要收全月高費率")
    
    tester1 = IoTBillingLogicTester()
    tester1.add_operation("2026-01-01", "ACTIVATE", plan="SBD12", status="ACTIVE")
    tester1.add_operation("2026-01-31", "PLAN_CHANGE", old_plan="SBD12", new_plan="SBD30")
    
    bill1 = tester1.calculate_monthly_bill(2026, 1)
    tester1.print_bill(bill1)
    
    verify1 = tester1.verify_contract_compliance(bill1)
    tester1.print_verification(verify1)
    
    # 驗證：應該收 SBD30 $50
    assert bill1['billing_plan'] == 'SBD30', "月底升級應立即生效"
    assert bill1['total'] == 50.00, "應收 SBD30 月租 $50"
    print("\n✅ 場景 1 通過：月底升級收取高費率")
    
    # ==================== 場景 2：同月反覆升降級 ====================
    print("\n\n" + "=" * 80)
    print("場景 2：同月反覆升降級（5次）")
    print("=" * 80)
    print("目的：驗證取最高費率，降級不生效")
    
    tester2 = IoTBillingLogicTester()
    tester2.add_operation("2026-01-01", "ACTIVATE", plan="SBD0", status="ACTIVE")
    tester2.add_operation("2026-01-05", "PLAN_CHANGE", old_plan="SBD0", new_plan="SBD12")
    tester2.add_operation("2026-01-10", "PLAN_CHANGE", old_plan="SBD12", new_plan="SBD30")
    tester2.add_operation("2026-01-15", "PLAN_CHANGE", old_plan="SBD30", new_plan="SBD17")
    tester2.add_operation("2026-01-20", "PLAN_CHANGE", old_plan="SBD17", new_plan="SBD30")
    tester2.add_operation("2026-01-25", "PLAN_CHANGE", old_plan="SBD30", new_plan="SBD0")
    
    bill2 = tester2.calculate_monthly_bill(2026, 1)
    tester2.print_bill(bill2)
    
    verify2 = tester2.verify_contract_compliance(bill2)
    tester2.print_verification(verify2)
    
    # 驗證：應該收 SBD30（最高升級）
    assert bill2['billing_plan'] == 'SBD30', "應取最高升級方案"
    assert bill2['total'] == 50.00, "應收 SBD30 月租 $50"
    print("\n✅ 場景 2 通過：反覆升降級取最高費率")
    
    # ==================== 場景 3：頻繁暫停（10次）====================
    print("\n\n" + "=" * 80)
    print("場景 3：一個月暫停 10 次")
    print("=" * 80)
    print("目的：驗證行政手續費正確計算")
    
    tester3 = IoTBillingLogicTester()
    tester3.add_operation("2026-01-01", "ACTIVATE", plan="SBD12", status="ACTIVE")
    
    # 暫停 10 次
    for i in range(1, 11):
        day = i * 3
        if day > 28:
            day = 28
        tester3.add_operation(
            f"2026-01-{day:02d}", 
            "STATUS_CHANGE",
            old_status="ACTIVE",
            new_status="SUSPENDED"
        )
        # 立即恢復（為了能再次暫停）
        if i < 10:
            tester3.add_operation(
                f"2026-01-{day:02d}",
                "STATUS_CHANGE",
                old_status="SUSPENDED",
                new_status="ACTIVE"
            )
    
    bill3 = tester3.calculate_monthly_bill(2026, 1)
    tester3.print_bill(bill3)
    
    verify3 = tester3.verify_contract_compliance(bill3)
    tester3.print_verification(verify3)
    
    # 驗證：10次暫停，手續費 = 10 × $20 = $200
    assert bill3['suspend_count'] == 10, "應記錄10次暫停"
    assert bill3['fees']['admin_fee'] == 200.00, "手續費應為 $200"
    print("\n✅ 場景 3 通過：頻繁暫停收取高額手續費")
    
    # ==================== 場景 4：跨月暫停 ====================
    print("\n\n" + "=" * 80)
    print("場景 4：跨月暫停（1/31 暫停，2/1 恢復）")
    print("=" * 80)
    print("目的：驗證跨月操作費用計算")
    
    tester4 = IoTBillingLogicTester()
    tester4.add_operation("2026-01-01", "ACTIVATE", plan="SBD12", status="ACTIVE")
    tester4.add_operation("2026-01-31", "STATUS_CHANGE", old_status="ACTIVE", new_status="SUSPENDED")
    tester4.add_operation("2026-02-01", "STATUS_CHANGE", old_status="SUSPENDED", new_status="ACTIVE")
    
    bill4_jan = tester4.calculate_monthly_bill(2026, 1)
    bill4_feb = tester4.calculate_monthly_bill(2026, 2)
    
    print("\n📅 1月帳單：")
    tester4.print_bill(bill4_jan)
    
    print("\n📅 2月帳單：")
    tester4.print_bill(bill4_feb)
    
    # 驗證：1月 = $28 + $4 = $32, 2月 = $4 + $28 = $32
    assert bill4_jan['total'] == 32.00, "1月應收 $32"
    assert bill4_feb['total'] == 32.00, "2月應收 $32"
    
    total = bill4_jan['total'] + bill4_feb['total']
    print(f"\n兩月總計：${total:.2f}")
    print("vs 正常使用：$56 ($28 × 2)")
    print(f"客戶多付：${total - 56:.2f}")
    print("\n✅ 場景 4 通過：跨月暫停客戶多付錢")
    
    # ==================== 場景 5：升級+暫停+降級（同月）====================
    print("\n\n" + "=" * 80)
    print("場景 5：升級 + 暫停 + 降級（同月內）")
    print("=" * 80)
    print("目的：驗證複雜組合操作")
    
    tester5 = IoTBillingLogicTester()
    tester5.add_operation("2026-01-01", "ACTIVATE", plan="SBD12", status="ACTIVE")
    tester5.add_operation("2026-01-10", "PLAN_CHANGE", old_plan="SBD12", new_plan="SBD30")
    tester5.add_operation("2026-01-15", "STATUS_CHANGE", old_status="ACTIVE", new_status="SUSPENDED")
    tester5.add_operation("2026-01-20", "STATUS_CHANGE", old_status="SUSPENDED", new_status="ACTIVE")
    tester5.add_operation("2026-01-25", "PLAN_CHANGE", old_plan="SBD30", new_plan="SBD12")
    
    bill5 = tester5.calculate_monthly_bill(2026, 1)
    tester5.print_bill(bill5)
    
    verify5 = tester5.verify_contract_compliance(bill5)
    tester5.print_verification(verify5)
    
    # 驗證：
    # - 計費方案應為 SBD30（升級生效，降級不生效）
    # - 有狀態變更：SBD30 + $4 + SBD30 = $104
    assert bill5['billing_plan'] == 'SBD30', "應使用升級後的 SBD30"
    assert bill5['total'] == 104.00, "應收 $104（雙重月租 + 暫停費）"
    print("\n✅ 場景 5 通過：複雜組合計費正確")
    
    # ==================== 總結 ====================
    print("\n\n" + "=" * 80)
    print("📊 測試總結")
    print("=" * 80)
    
    test_results = [
        ("場景 1：月底升級", "✅ 通過"),
        ("場景 2：反覆升降級", "✅ 通過"),
        ("場景 3：頻繁暫停", "✅ 通過"),
        ("場景 4：跨月暫停", "✅ 通過"),
        ("場景 5：複雜組合", "✅ 通過")
    ]
    
    print("\n測試結果：")
    for scenario, result in test_results:
        print(f"  {result} {scenario}")
    
    print("\n🎯 結論：")
    print("  ✅ 所有極端場景測試通過")
    print("  ✅ 計費邏輯正確無誤")
    print("  ✅ 符合合約規定")
    print("  ✅ 公司不會吃虧")
    print("  ✅ 客戶無法鑽漏洞")


if __name__ == "__main__":
    test_extreme_scenarios()

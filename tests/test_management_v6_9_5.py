"""
IWS 管理功能测试 - v6.9.5
修正: accountUpdate 添加 newStatus 字段
"""
import sys
sys.path.insert(0, '/Users/eliothuo/Downloads/files (1)/SBD-Final')

from src.infrastructure.iws_gateway import IWSGateway, IWSException

# ========== 憑證配置 ==========
IWS_USERNAME = "IWSN3D"
IWS_PASSWORD = "FvGr2({sE4V4TJ:"
IWS_SP_ACCOUNT = "200883"
IWS_ENDPOINT = "https://iwstraining.iridium.com:8443/iws-current/iws"

# ========== 测试数据 ==========
TEST_IMEI = "300434067857940"  # SUB-49059741895 (目前是 SUSPENDED)
TEST_PLAN_ID = "763924583"     # SBD 12

print("="*80)
print("🧪 IWS 管理功能测试 - v6.9.5")
print("="*80)
print(f"Username: {IWS_USERNAME}")
print(f"SP Account: {IWS_SP_ACCOUNT}")
print(f"Test IMEI: {TEST_IMEI}")
print(f"Test Plan: {TEST_PLAN_ID} (SBD 12)")
print("="*80 + "\n")

print("修正内容:")
print("  ✅ accountUpdate 添加 <newStatus>ACTIVE</newStatus>")
print("="*80 + "\n")

print("注意:")
print("  - 账号目前是 SUSPENDED 状态")
print("  - 先测试恢复（ACTIVE）")
print("  - 再测试变更费率")
print("  - 最后测试暂停（SUSPENDED）")
print("="*80 + "\n")

# 初始化 Gateway
try:
    gateway = IWSGateway(
        username=IWS_USERNAME,
        password=IWS_PASSWORD,
        sp_account=IWS_SP_ACCOUNT,
        endpoint=IWS_ENDPOINT
    )
    print("✅ Gateway 初始化成功\n")
except Exception as e:
    print(f"❌ 初始化失败: {e}")
    exit(1)

results = {}

# ========================================
# 测试 1: resume_subscriber (恢复设备)
# ========================================
print("\n" + "="*80)
print("测试 1: resume_subscriber (恢复设备 SUSPENDED → ACTIVE)")
print("="*80)
print(f"IMEI: {TEST_IMEI}")
print("="*80)

try:
    result = gateway.resume_subscriber(
        imei=TEST_IMEI,
        reason="测试恢复"
    )
    
    print("\n✅ 恢复设备成功！")
    print(f"Transaction ID: {result.get('transaction_id')}")
    print(f"Message: {result.get('message')}")
    results['resume'] = True
    
except IWSException as e:
    print(f"\n❌ 恢复设备失败")
    print(f"错误: {str(e)}")
    results['resume'] = False
    
    if hasattr(e, 'response_text') and e.response_text:
        import re
        reason_match = re.search(r'<soap:Text[^>]*>(.*?)</soap:Text>', e.response_text)
        if reason_match:
            print(f"错误原因: {reason_match.group(1)}")

# ========================================
# 测试 2: accountUpdate (变更费率) - v6.9.5 修正
# ========================================
print("\n" + "="*80)
print("测试 2: accountUpdate (变更费率 - v6.9.5 修正)")
print("="*80)
print(f"IMEI: {TEST_IMEI}")
print(f"新方案: {TEST_PLAN_ID}")
print("新增字段: <newStatus>ACTIVE</newStatus>")
print("="*80)

try:
    result = gateway.update_subscriber_plan(
        imei=TEST_IMEI,
        new_plan_id=TEST_PLAN_ID
    )
    
    print("\n✅ 变更费率成功！")
    print(f"Transaction ID: {result.get('transaction_id')}")
    print(f"Message: {result.get('message')}")
    results['update_plan'] = True
    
except IWSException as e:
    print(f"\n❌ 变更费率失败")
    print(f"错误: {str(e)}")
    results['update_plan'] = False
    
    if hasattr(e, 'response_text') and e.response_text:
        print("\nSOAP 响应详情:")
        print("-" * 80)
        print(e.response_text)
        print("-" * 80)
        
        import re
        reason_match = re.search(r'<soap:Text[^>]*>(.*?)</soap:Text>', e.response_text)
        if reason_match:
            print(f"\n错误原因: {reason_match.group(1)}")

# ========================================
# 测试 3: suspend_subscriber (暂停设备)
# ========================================
print("\n" + "="*80)
print("测试 3: suspend_subscriber (暂停设备 ACTIVE → SUSPENDED)")
print("="*80)
print(f"IMEI: {TEST_IMEI}")
print("="*80)

try:
    result = gateway.suspend_subscriber(
        imei=TEST_IMEI,
        reason="测试暂停"
    )
    
    print("\n✅ 暂停设备成功！")
    print(f"Transaction ID: {result.get('transaction_id')}")
    print(f"Message: {result.get('message')}")
    results['suspend'] = True
    
except IWSException as e:
    print(f"\n❌ 暂停设备失败")
    print(f"错误: {str(e)}")
    results['suspend'] = False
    
    if hasattr(e, 'response_text') and e.response_text:
        import re
        reason_match = re.search(r'<soap:Text[^>]*>(.*?)</soap:Text>', e.response_text)
        if reason_match:
            print(f"错误原因: {reason_match.group(1)}")

# ========================================
# 测试结果摘要
# ========================================
print("\n" + "="*80)
print("📊 测试结果摘要")
print("="*80)

test_names = {
    'resume': '恢复设备 (setSubscriberAccountStatus - ACTIVE)',
    'update_plan': '变更费率 (accountUpdate) - v6.9.5 修正',
    'suspend': '暂停设备 (setSubscriberAccountStatus - SUSPENDED)'
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

# 统计
total = len([r for r in results.values() if r is not None])
passed = len([r for r in results.values() if r is True])

print(f"\n总计: {passed}/{total} 测试通过")

if passed == total and total > 0:
    print("\n" + "="*80)
    print("🎉 所有管理功能测试通过！")
    print("="*80)
    print("\n✅ 已验证的管理功能:")
    print("  1. resume_subscriber - 恢复设备")
    print("  2. update_subscriber_plan - 变更费率")
    print("  3. suspend_subscriber - 暂停设备")
    
    print("\n🎊 核心 API + 管理功能 100% 验证完成！")
    print("\n下一步:")
    print("  - 整合到 Streamlit UI")
    print("  - 测试完整工作流程")
    print("  - 部署到生产环境")
else:
    print("\n⚠️  部分测试失败，请检查错误信息")

print("="*80)

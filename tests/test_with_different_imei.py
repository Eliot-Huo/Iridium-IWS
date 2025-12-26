"""
使用不同的 IMEI 测试管理功能
避免 PENDING 状态问题
"""
import sys
sys.path.insert(0, '/Users/eliothuo/Downloads/files (1)/SBD-Final')

from src.infrastructure.iws_gateway import IWSGateway, IWSException

# ========== 憑證配置 ==========
IWS_USERNAME = "IWSN3D"
IWS_PASSWORD = "FvGr2({sE4V4TJ:"
IWS_SP_ACCOUNT = "200883"
IWS_ENDPOINT = "https://iwstraining.iridium.com:8443/iws-current/iws"

# ========== 使用不同的测试设备 ==========
# 300534066711380 - SUB-52830841655 (SUSPENDED)
# 300434065956950 - SUB-55030646622 (SUSPENDED)

TEST_IMEI = "300534066711380"  # 使用这个（目前 SUSPENDED）
TEST_PLAN_ID = "763927911"     # SBD 17

print("="*80)
print("🧪 IWS 管理功能测试 - 使用不同的 IMEI")
print("="*80)
print(f"Username: {IWS_USERNAME}")
print(f"SP Account: {IWS_SP_ACCOUNT}")
print(f"Test IMEI: {TEST_IMEI} (SUB-52830841655)")
print(f"Test Plan: {TEST_PLAN_ID} (SBD 17)")
print("="*80 + "\n")

print("说明:")
print("  - 使用 300534066711380 (目前 SUSPENDED 状态)")
print("  - 避免之前测试的 PENDING 状态问题")
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
# 步骤 1: 检查当前状态
# ========================================
print("\n" + "="*80)
print("步骤 1: 检查当前状态")
print("="*80)

try:
    result = gateway.search_account(TEST_IMEI)
    if result['found']:
        print(f"✅ 账号: {result['subscriber_account_number']}")
    else:
        print("❌ 未找到账号")
        exit(1)
except Exception as e:
    print(f"❌ 检查失败: {e}")
    exit(1)

# ========================================
# 测试 1: resume_subscriber (SUSPENDED → ACTIVE)
# ========================================
print("\n" + "="*80)
print("测试 1: resume_subscriber (SUSPENDED → ACTIVE)")
print("="*80)

try:
    result = gateway.resume_subscriber(
        imei=TEST_IMEI,
        reason="测试恢复 - 使用不同IMEI"
    )
    
    print("\n✅ 恢复设备成功！")
    print(f"Transaction ID: {result.get('transaction_id')}")
    results['resume'] = True
    
    # 等待一下
    import time
    print("\n等待 3 秒...")
    time.sleep(3)
    
except IWSException as e:
    print(f"\n❌ 恢复设备失败: {str(e)}")
    results['resume'] = False
    
    if "timeout" in str(e).lower():
        print("\n⚠️  超时但请求可能已接受")
        print("   建议等待 2-5 分钟后检查状态")
        results['resume'] = None  # 未知状态

except Exception as e:
    print(f"\n❌ 未预期的错误: {e}")
    results['resume'] = False

# ========================================
# 测试 2: accountUpdate (变更费率)
# ========================================
print("\n" + "="*80)
print("测试 2: accountUpdate (变更费率)")
print("="*80)
print(f"新方案: {TEST_PLAN_ID} (SBD 17)")

try:
    result = gateway.update_subscriber_plan(
        imei=TEST_IMEI,
        new_plan_id=TEST_PLAN_ID
    )
    
    print("\n✅ 变更费率成功！")
    print(f"Transaction ID: {result.get('transaction_id')}")
    results['update'] = True
    
    # 等待一下
    import time
    print("\n等待 3 秒...")
    time.sleep(3)
    
except IWSException as e:
    print(f"\n❌ 变更费率失败: {str(e)}")
    results['update'] = False
    
    if hasattr(e, 'response_text') and e.response_text:
        import re
        reason_match = re.search(r'<soap:Text[^>]*>(.*?)</soap:Text>', e.response_text)
        if reason_match:
            print(f"错误原因: {reason_match.group(1)}")
    
    if "pending" in str(e).lower():
        print("\n⚠️  账号可能还在 PENDING 状态")
        print("   建议等待并重试")

except Exception as e:
    print(f"\n❌ 未预期的错误: {e}")
    results['update'] = False

# ========================================
# 测试 3: suspend_subscriber (ACTIVE → SUSPENDED)
# ========================================
print("\n" + "="*80)
print("测试 3: suspend_subscriber (ACTIVE → SUSPENDED)")
print("="*80)

try:
    result = gateway.suspend_subscriber(
        imei=TEST_IMEI,
        reason="测试暂停 - 使用不同IMEI"
    )
    
    print("\n✅ 暂停设备成功！")
    print(f"Transaction ID: {result.get('transaction_id')}")
    results['suspend'] = True
    
except IWSException as e:
    print(f"\n❌ 暂停设备失败: {str(e)}")
    results['suspend'] = False
    
    if hasattr(e, 'response_text') and e.response_text:
        import re
        reason_match = re.search(r'<soap:Text[^>]*>(.*?)</soap:Text>', e.response_text)
        if reason_match:
            print(f"错误原因: {reason_match.group(1)}")

except Exception as e:
    print(f"\n❌ 未预期的错误: {e}")
    results['suspend'] = False

# ========================================
# 测试结果摘要
# ========================================
print("\n" + "="*80)
print("📊 测试结果摘要")
print("="*80)

test_names = {
    'resume': 'resume_subscriber (SUSPENDED → ACTIVE)',
    'update': 'accountUpdate (变更费率)',
    'suspend': 'suspend_subscriber (ACTIVE → SUSPENDED)'
}

for key, name in test_names.items():
    result = results.get(key)
    if result is True:
        status = "✅ PASS"
    elif result is False:
        status = "❌ FAIL"
    elif result is None:
        status = "⏳ PENDING"
    else:
        status = "⚠️  SKIP"
    print(f"{name}: {status}")

passed = len([r for r in results.values() if r is True])
failed = len([r for r in results.values() if r is False])
pending = len([r for r in results.values() if r is None])

print(f"\n总计: {passed} 通过, {failed} 失败, {pending} 等待中")

print("\n" + "="*80)
print("说明:")
print("  - 如果测试超时，请等待 2-5 分钟后运行 check_account_status.py")
print("  - 如果遇到 PENDING 错误，说明之前的操作还在处理中")
print("  - IWS 训练环境的响应可能比生产环境慢")
print("="*80)

"""
IWS Gateway v6.9.2 完整功能测试
包含所有已修正的功能
"""
import sys
sys.path.insert(0, '/Users/eliothuo/Downloads/files (1)/SBD-Final')

from src.infrastructure.iws_gateway import IWSGateway, IWSException

# ========== 憑證配置 ==========
IWS_USERNAME = "IWSN3D"
IWS_PASSWORD = "FvGr2({sE4V4TJ:"
IWS_SP_ACCOUNT = "200883"
IWS_ENDPOINT = "https://iwstraining.iridium.com:8443/iws-current/iws"

# ========== 测试 IMEI ==========
TEST_IMEI = "300434067857940"  # SUB-49059741895 (已验证有账号)

print("="*80)
print("🧪 IWS Gateway v6.9.2 完整功能测试")
print("="*80)
print(f"Username: {IWS_USERNAME}")
print(f"SP Account: {IWS_SP_ACCOUNT}")
print(f"Test IMEI: {TEST_IMEI} (SUB-49059741895)")
print(f"Endpoint: {IWS_ENDPOINT}")
print("="*80 + "\n")

print("已修正的功能:")
print("  ✅ v6.9.1: getSBDBundles (移除 <plan> 包裹)")
print("  ✅ v6.9.2: accountSearch (正确解析 accountNumber)")
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
# 测试 1: getSystemStatus (已验证成功)
# ========================================
def test_1_connection():
    print("\n" + "="*80)
    print("测试 1: getSystemStatus (连线测试)")
    print("="*80)
    
    try:
        result = gateway.check_connection()
        print("✅ 连线成功")
        return True
    except Exception as e:
        print(f"❌ 连线失败: {e}")
        return False

# ========================================
# 测试 2: getSBDBundles (v6.9.1 已修正)
# ========================================
def test_2_get_bundles():
    print("\n" + "="*80)
    print("测试 2: getSBDBundles (查询方案 - v6.9.1 修正)")
    print("="*80)
    print("修正: 移除 <plan> 包裹，参数直接放在 request 中")
    
    try:
        result = gateway.get_sbd_bundles(
            from_bundle_id="0",
            for_activate=True
        )
        
        print(f"\n✅ 查询成功，找到 {result['count']} 个方案")
        
        if result['bundles'] and len(result['bundles']) > 0:
            print("\n方案列表（前 5 个）:")
            for i, bundle in enumerate(result['bundles'][:5], 1):
                bundle_id = bundle.get('sbdBundleId', 'N/A')
                name = bundle.get('name', 'N/A')
                print(f"  {i}. Bundle ID: {bundle_id}, Name: {name}")
        
        return True, result['bundles']
        
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
        if hasattr(e, 'response_text') and e.response_text:
            print(f"\nSOAP 回应:\n{e.response_text[:500]}")
        return False, None

# ========================================
# 测试 3: accountSearch (v6.9.2 已修正)
# ========================================
def test_3_search_account():
    print("\n" + "="*80)
    print("测试 3: accountSearch (账号搜索 - v6.9.2 修正)")
    print("="*80)
    print(f"IMEI: {TEST_IMEI}")
    print("修正: 正确解析 <accountNumber> 并匹配 IMEI")
    
    try:
        result = gateway.search_account(TEST_IMEI)
        
        if result['found']:
            print(f"\n✅ 账号搜索成功")
            print(f"   订阅者账号: {result['subscriber_account_number']}")
            return True, result['subscriber_account_number']
        else:
            print("\n⚠️  账号未找到")
            return False, None
            
    except Exception as e:
        print(f"\n❌ 搜索失败: {e}")
        return False, None

# ========================================
# 测试 4: validateDeviceString
# ========================================
def test_4_validate_device():
    print("\n" + "="*80)
    print("测试 4: validateDeviceString (设备验证)")
    print("="*80)
    print(f"IMEI: {TEST_IMEI}")
    print("注意: ACTIVE 设备返回 valid=false 是正常的")
    
    try:
        result = gateway.validate_device_string(
            device_string=TEST_IMEI,
            device_string_type="IMEI",
            validate_state=True
        )
        
        print(f"\nAPI 回应:")
        print(f"  - valid: {result['valid']}")
        print(f"  - device_string: {result.get('device_string')}")
        print(f"  - reason: {result.get('reason', 'N/A')}")
        
        # 判断成功的标准
        if result.get('reason') and 'state = [ACTIVE]' in result['reason']:
            print("\n✅ 验证成功（设备确实是 ACTIVE 状态）")
            return True
        elif result.get('reason') and 'state = [SUSPENDED]' in result['reason']:
            print("\n✅ 验证成功（设备是 SUSPENDED 状态）")
            return True
        elif result['valid']:
            print("\n✅ 验证成功（设备可用）")
            return True
        else:
            print(f"\n⚠️  设备状态: {result.get('reason')}")
            return False
        
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        return False

# ========================================
# 执行所有测试
# ========================================
print("\n开始执行测试套件...\n")

# 测试 1: 连线
results['connection'] = test_1_connection()

if not results['connection']:
    print("\n⚠️  连线测试失败，停止后续测试")
    exit(1)

# 测试 2: getSBDBundles
bundles_success, bundles = test_2_get_bundles()
results['bundles'] = bundles_success

# 测试 3: accountSearch
search_success, account_number = test_3_search_account()
results['search'] = search_success

# 测试 4: validateDeviceString
results['validate'] = test_4_validate_device()

# ========================================
# 测试结果摘要
# ========================================
print("\n" + "="*80)
print("📊 测试结果摘要")
print("="*80)

test_names = {
    'connection': '连线测试 (getSystemStatus)',
    'bundles': 'SBD 方案查询 (getSBDBundles) - v6.9.1 修正',
    'search': '账号搜索 (accountSearch) - v6.9.2 修正',
    'validate': '设备验证 (validateDeviceString)'
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

if passed == total:
    print("\n" + "="*80)
    print("🎉 所有测试通过！")
    print("="*80)
    print("\n✅ 已验证的功能:")
    print("  1. getSystemStatus - 连线正常")
    print("  2. getSBDBundles - SOAP 格式已修正")
    print("  3. accountSearch - 字段解析已修正")
    print("  4. validateDeviceString - 理解正确")
    
    print("\n🚀 下一步可以测试:")
    print("  - update_subscriber_plan (变更费率)")
    print("  - suspend_subscriber (暂停设备)")
    print("  - resume_subscriber (恢复设备)")
    
    if bundles and len(bundles) > 0:
        print(f"\n💡 提示: 找到 {len(bundles)} 个可用方案")
        print("  可以选择一个方案 ID 来测试 update_subscriber_plan")
    
    if account_number:
        print(f"\n💡 提示: 已获得订阅者账号 {account_number}")
        print("  可以使用此账号测试变更费率功能")
else:
    print("\n⚠️  部分测试失败，请检查错误信息")

print("="*80)

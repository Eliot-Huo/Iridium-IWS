"""
IWS Gateway v6.9.4 - getSBDBundles 最终测试
根据两次错误消息推断出的正确结构
"""
import sys
sys.path.insert(0, '/Users/eliothuo/Downloads/files (1)/SBD-Final')

from src.infrastructure.iws_gateway import IWSGateway, IWSException

# ========== 憑證配置 ==========
IWS_USERNAME = "IWSN3D"
IWS_PASSWORD = "FvGr2({sE4V4TJ:"
IWS_SP_ACCOUNT = "200883"
IWS_ENDPOINT = "https://iwstraining.iridium.com:8443/iws-current/iws"

print("="*80)
print("🧪 IWS Gateway v6.9.4 - getSBDBundles 最终测试")
print("="*80)
print(f"Username: {IWS_USERNAME}")
print(f"SP Account: {IWS_SP_ACCOUNT}")
print(f"Endpoint: {IWS_ENDPOINT}")
print("="*80 + "\n")

print("修正历史:")
print("  ❌ v6.9.0: <plan> 包裹 → 'unexpected element plan'")
print("  ❌ v6.9.1: 直接放参数 → 'No plan provided'")
print("  ❌ v6.9.3: 参数在 <sbdPlan> 内 → 'unexpected element fromBundleId'")
print("  ✅ v6.9.4: 参数在外面，<sbdPlan /> 空标签 → 测试中...")
print("="*80 + "\n")

print("关键发现:")
print("  错误 1 告诉我们：fromBundleId, forActivate, sbdPlan 都在 <request> 下")
print("  错误 2 告诉我们：<sbdPlan> 内应该是 Plan 配置，不是查询参数")
print("  结论：查询参数在外面，<sbdPlan /> 只是服务类型标识")
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

# ========================================
# 测试 getSBDBundles (v6.9.4)
# ========================================
print("\n" + "="*80)
print("测试: getSBDBundles (v6.9.4 - 最终版本)")
print("="*80)
print("SOAP 结构:")
print("  <request>")
print("    <iwsUsername>...</iwsUsername>")
print("    <signature>...</signature>")
print("    <serviceProviderAccountNumber>...</serviceProviderAccountNumber>")
print("    <timestamp>...</timestamp>")
print("    <fromBundleId>0</fromBundleId>       <!-- 查询参数 -->")
print("    <forActivate>true</forActivate>      <!-- 查询参数 -->")
print("    <sbdPlan />                          <!-- 服务类型 -->")
print("  </request>")
print("="*80 + "\n")

try:
    result = gateway.get_sbd_bundles(
        from_bundle_id="0",
        for_activate=True
    )
    
    print("\n" + "="*80)
    print("🎉 getSBDBundles 成功！")
    print("="*80)
    print(f"找到 {result['count']} 个 SBD 方案")
    
    if result['bundles'] and len(result['bundles']) > 0:
        print("\n方案列表（前 10 个）:")
        print("-" * 80)
        for i, bundle in enumerate(result['bundles'][:10], 1):
            bundle_id = bundle.get('sbdBundleId', 'N/A')
            name = bundle.get('name', 'N/A')
            print(f"{i:2d}. Bundle ID: {bundle_id:3s} | Name: {name}")
        
        if len(result['bundles']) > 10:
            print(f"... 还有 {len(result['bundles']) - 10} 个方案")
    
    print("="*80)
    print("\n" + "🎊" * 40)
    print("🎉 所有核心功能测试完成！")
    print("🎊" * 40)
    
    print("\n✅ 已验证的功能:")
    print("  1. getSystemStatus      - 连线正常")
    print("  2. getSBDBundles        - 方案查询正常（v6.9.4）")
    print("  3. accountSearch        - 账号搜索正常（v6.9.2）")
    print("  4. validateDeviceString - 设备验证正常")
    
    print("\n🚀 下一步可以测试:")
    print("  - update_subscriber_plan (变更费率)")
    print("  - suspend_subscriber (暂停设备)")
    print("  - resume_subscriber (恢复设备)")
    
    print("\n💡 可用的测试数据:")
    print(f"  - IMEI: 300434067857940 (SUB-49059741895)")
    if len(result['bundles']) > 0:
        print(f"  - 方案: Bundle ID {result['bundles'][0].get('sbdBundleId')} 等 {len(result['bundles'])} 个")
    
    print("\n" + "="*80)
    
except IWSException as e:
    print("\n" + "="*80)
    print("❌ getSBDBundles 失败")
    print("="*80)
    print(f"错误: {str(e)}")
    
    if hasattr(e, 'response_text') and e.response_text:
        print(f"\nSOAP 错误详情:")
        print("-" * 80)
        # 提取 Reason
        import re
        reason_match = re.search(r'<soap:Text[^>]*>(.*?)</soap:Text>', e.response_text)
        if reason_match:
            print(f"原因: {reason_match.group(1)}")
        print("-" * 80)
        
    print("\n如果还是失败，请将完整输出贴给我分析")
    
except Exception as e:
    print(f"\n❌ 未预期的错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)

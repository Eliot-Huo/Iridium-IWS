"""
IWS Gateway v6.9.3 - 测试 getSBDBundles
修正: 使用 <sbdPlan> 对象而非 <plan> 或直接参数
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
print("🧪 IWS Gateway v6.9.3 - getSBDBundles 测试")
print("="*80)
print(f"Username: {IWS_USERNAME}")
print(f"SP Account: {IWS_SP_ACCOUNT}")
print(f"Endpoint: {IWS_ENDPOINT}")
print("="*80 + "\n")

print("修正历史:")
print("  ❌ v6.9.0: 使用 <plan> 包裹 → HTTP 500 (unexpected element 'plan')")
print("  ❌ v6.9.1: 移除包裹，直接放参数 → HTTP 500 (No plan provided)")
print("  ✅ v6.9.3: 使用 <sbdPlan> 对象 → 测试中...")
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
# 测试 getSBDBundles (v6.9.3)
# ========================================
print("\n" + "="*80)
print("测试: getSBDBundles (v6.9.3 修正)")
print("="*80)
print("新结构:")
print("  <request>")
print("    ...")
print("    <sbdPlan>")
print("      <fromBundleId>0</fromBundleId>")
print("      <forActivate>true</forActivate>")
print("    </sbdPlan>")
print("  </request>")
print("="*80 + "\n")

try:
    result = gateway.get_sbd_bundles(
        from_bundle_id="0",
        for_activate=True
    )
    
    print("\n" + "="*80)
    print("✅ getSBDBundles 成功！")
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
    print("\n🎉 v6.9.3 修正成功！")
    print("\n正确的 SOAP 结构:")
    print("  ✅ 使用 <sbdPlan> 对象（不是 <plan>）")
    print("  ✅ 参数放在 <sbdPlan> 内（不是直接在 request 下）")
    print("  ✅ API 通过 service type（sbdPlan）确定要返回哪些方案")
    
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

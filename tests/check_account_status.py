"""
检查账号状态
等待 PENDING 完成后再进行其他操作
"""
import sys
import time
sys.path.insert(0, '/Users/eliothuo/Downloads/files (1)/SBD-Final')

from src.infrastructure.iws_gateway import IWSGateway

# ========== 憑證配置 ==========
IWS_USERNAME = "IWSN3D"
IWS_PASSWORD = "FvGr2({sE4V4TJ:"
IWS_SP_ACCOUNT = "200883"
IWS_ENDPOINT = "https://iwstraining.iridium.com:8443/iws-current/iws"

TEST_IMEI = "300434067857940"

print("="*80)
print("🔍 检查账号状态")
print("="*80)
print(f"IMEI: {TEST_IMEI}")
print("="*80 + "\n")

gateway = IWSGateway(
    username=IWS_USERNAME,
    password=IWS_PASSWORD,
    sp_account=IWS_SP_ACCOUNT,
    endpoint=IWS_ENDPOINT
)

print("检查当前状态...")

try:
    result = gateway.search_account(TEST_IMEI)
    
    if result['found']:
        print(f"\n✅ 找到账号: {result['subscriber_account_number']}")
        print(f"\n从 SOAP 响应中查看完整信息...")
        
        # 再次搜索以获取详细信息
        import xml.etree.ElementTree as ET
        from src.infrastructure.iws_gateway import IWSException
        
        action_name, soap_body = gateway._build_account_search_body(
            service_type="SHORT_BURST_DATA",
            filter_type="IMEI",
            filter_cond="EXACT",
            filter_value=TEST_IMEI
        )
        
        response_xml = gateway._send_soap_request(
            soap_action=action_name,
            soap_body=soap_body
        )
        
        # 解析响应
        root = ET.fromstring(response_xml)
        subscribers = root.findall('.//subscriber')
        
        for subscriber in subscribers:
            imei_elem = subscriber.find('.//imei')
            if imei_elem is not None and imei_elem.text == TEST_IMEI:
                print("\n账号详细信息:")
                print("-" * 80)
                for child in subscriber:
                    tag = child.tag.split('}')[-1]
                    print(f"  {tag}: {child.text}")
                print("-" * 80)
                
                # 检查状态
                status_elem = subscriber.find('.//accountStatus')
                if status_elem is not None:
                    status = status_elem.text
                    print(f"\n当前状态: {status}")
                    
                    if status == "PENDING":
                        print("\n⏳ 账号仍在 PENDING 状态")
                        print("   建议:")
                        print("   1. 等待 2-5 分钟")
                        print("   2. 再次运行此脚本检查状态")
                        print("   3. 等到状态变为 ACTIVE 后再进行其他操作")
                    elif status == "ACTIVE":
                        print("\n✅ 账号已经是 ACTIVE 状态")
                        print("   可以进行以下操作:")
                        print("   - 变更费率 (accountUpdate)")
                        print("   - 暂停设备 (suspend)")
                    elif status == "SUSPENDED":
                        print("\n⏸️  账号是 SUSPENDED 状态")
                        print("   可以进行:")
                        print("   - 恢复设备 (resume)")
                    else:
                        print(f"\n状态: {status}")
                
                break
    else:
        print("\n❌ 未找到账号")

except Exception as e:
    print(f"\n❌ 检查失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP 500 错误诊断工具
用于诊断 IWS accountUpdate 调用失败的问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.iws_gateway import IWSGateway
import json

def diagnose_imei_status(imei: str):
    """诊断 IMEI 的当前状态"""
    print("\n" + "="*70)
    print("🔍 诊断工具：IWS HTTP 500 错误分析")
    print("="*70)
    print(f"IMEI: {imei}")
    print("="*70 + "\n")
    
    gateway = IWSGateway()
    
    # 步骤 1: 查询当前状态
    print("📍 步骤 1: 查询设备当前状态")
    print("-" * 70)
    
    try:
        # 使用 search_account
        search_result = gateway.search_account(imei)
        
        if not search_result.get('found'):
            print("❌ 设备未找到！")
            print("   IMEI 可能不存在于 IWS 系统中")
            return
        
        print("✅ 设备找到！")
        print(f"   Subscriber Account Number: {search_result.get('subscriber_account_number')}")
        print(f"   状态: {search_result.get('status')}")
        print(f"   当前资费: {search_result.get('plan_name')}")
        print(f"   开通日期: {search_result.get('activation_date')}")
        
        # 步骤 2: 获取详细信息
        print("\n📍 步骤 2: 获取详细账号信息")
        print("-" * 70)
        
        detailed_result = gateway.get_detailed_account_info(imei)
        
        if detailed_result.get('success'):
            print("✅ 详细信息获取成功！")
            print(f"   Account Number: {detailed_result.get('account_number')}")
            print(f"   Account Status: {detailed_result.get('status')}")
            print(f"   Current Plan: {detailed_result.get('plan_name')}")
            print(f"   ICCID: {detailed_result.get('iccid', 'N/A')}")
            print(f"   SP Reference: {detailed_result.get('sp_reference', 'N/A')}")
            print(f"   Ring Alert: {detailed_result.get('ring_alert', 'N/A')}")
            
            # 显示 destinations
            destinations = detailed_result.get('destinations', [])
            if destinations:
                print(f"   Destinations: {len(destinations)} 个")
                for i, dest in enumerate(destinations, 1):
                    print(f"      {i}. {dest.get('destination', 'N/A')} ({dest.get('method', 'N/A')})")
        else:
            print("⚠️ 详细信息获取失败")
        
        # 步骤 3: 测试 accountUpdate 请求构建
        print("\n📍 步骤 3: 测试 accountUpdate 请求构建")
        print("-" * 70)
        
        subscriber_account_number = search_result.get('subscriber_account_number')
        
        if not subscriber_account_number:
            print("❌ 无法获取 Subscriber Account Number")
            return
        
        # 测试构建请求体
        test_plan_id = '763924583'  # SBD 12
        action_name, soap_body = gateway._build_account_update_body(
            imei=imei,
            subscriber_account_number=subscriber_account_number,
            new_plan_id=test_plan_id,
            lrit_flagstate="",
            ring_alerts_flag=False
        )
        
        print(f"✅ 请求构建成功")
        print(f"   Action: {action_name}")
        print(f"   Target Plan ID: {test_plan_id}")
        print(f"\n   SOAP Body (前 800 字符):")
        print("   " + "-" * 68)
        print("   " + soap_body[:800].replace("\n", "\n   "))
        print("   " + "-" * 68)
        
        # 步骤 4: 分析可能的问题
        print("\n📍 步骤 4: 问题分析")
        print("-" * 70)
        
        current_plan = search_result.get('plan_name', '')
        target_plan = 'SBD 12'
        
        print(f"   当前资费: {current_plan}")
        print(f"   目标资费: {target_plan}")
        
        # 检查是否是降级
        plan_levels = {
            'SBD 0': 0,
            'SBD 12': 12,
            'SBD 17': 17,
            'SBD 30': 30
        }
        
        current_level = None
        target_level = 12
        
        for plan_name, level in plan_levels.items():
            if plan_name in current_plan:
                current_level = level
                break
        
        if current_level is not None:
            if target_level < current_level:
                print("\n   ⚠️ 这是一个降级操作")
                print(f"      从 {current_plan} (等级 {current_level})")
                print(f"      到 {target_plan} (等级 {target_level})")
                print("\n   可能的问题：")
                print("   1. IWS 可能不允许在线降级资费")
                print("   2. 某些账号状态下不允许降级")
                print("   3. 需要先注销再重新激活")
            elif target_level > current_level:
                print("\n   ✅ 这是一个升级操作")
                print(f"      从 {current_plan} (等级 {current_level})")
                print(f"      到 {target_plan} (等级 {target_level})")
                print("      升级通常允许")
            else:
                print("\n   ℹ️ 目标资费与当前相同")
        
        # 步骤 5: 检查账号状态
        print("\n📍 步骤 5: 账号状态检查")
        print("-" * 70)
        
        account_status = search_result.get('status', '')
        
        if account_status == 'ACTIVE':
            print("   ✅ 账号状态: ACTIVE（正常）")
        elif account_status == 'SUSPENDED':
            print("   ⚠️ 账号状态: SUSPENDED（暂停）")
            print("      暂停状态下可能无法变更资费")
        elif account_status == 'DEACTIVATED':
            print("   ❌ 账号状态: DEACTIVATED（注销）")
            print("      注销状态下无法变更资费")
        else:
            print(f"   ⚠️ 账号状态: {account_status}（未知）")
        
        # 步骤 6: IWS API 规则检查
        print("\n📍 步骤 6: IWS API 规则检查")
        print("-" * 70)
        print("   根据 IWS WSDL v25.1.0.1 文档：")
        print("")
        print("   accountUpdate 方法 (p.67):")
        print("   • 用于更新 SBD 订阅者的资费方案")
        print("   • 必填字段：subscriberAccountNumber, imei, sbdBundleId")
        print("   • 可选字段：lritFlagstate, ringAlertsFlag")
        print("")
        print("   可能的限制：")
        print("   1. ⚠️ 降级可能需要特殊权限")
        print("   2. ⚠️ 某些资费方案不允许相互转换")
        print("   3. ⚠️ 账单周期内可能有变更限制")
        print("   4. ⚠️ Demo 账号可能有操作限制")
        
        # 建议
        print("\n📍 建议的解决方案")
        print("-" * 70)
        print("   1. 📞 联系 Iridium 技术支持")
        print("      • 说明要从 SBD 17 降级到 SBD 12")
        print("      • 询问是否支持在线降级")
        print("      • 确认 SITEST 环境的限制")
        print("")
        print("   2. 🔄 尝试先升级到更高方案")
        print("      • 测试从 SBD 17 → SBD 30 是否成功")
        print("      • 如果升级成功，说明降级被限制")
        print("")
        print("   3. 🔧 尝试替代流程")
        print("      • 暂停设备 (suspend)")
        print("      • 变更资费")
        print("      • 恢复设备 (resume)")
        print("")
        print("   4. 📋 检查账号权限")
        print("      • 确认 SP 账号是否有降级权限")
        print("      • 检查 SITEST 环境的功能限制")
        
    except Exception as e:
        print(f"\n❌ 诊断过程出错: {str(e)}")
        import traceback
        print("\n完整错误追踪:")
        print(traceback.format_exc())
    
    print("\n" + "="*70)
    print("诊断完成")
    print("="*70 + "\n")


def test_upgrade_operation(imei: str):
    """测试升级操作（从当前方案升级到更高方案）"""
    print("\n" + "="*70)
    print("🧪 测试：尝试升级操作")
    print("="*70)
    
    gateway = IWSGateway()
    
    # 查询当前状态
    search_result = gateway.search_account(imei)
    
    if not search_result.get('found'):
        print("❌ 设备未找到")
        return
    
    current_plan = search_result.get('plan_name', '')
    print(f"当前资费: {current_plan}")
    
    # 尝试升级到 SBD 30
    print("\n尝试升级到 SBD 30...")
    
    try:
        result = gateway.update_subscriber_plan(
            imei=imei,
            new_plan_id='763925351'  # SBD 30
        )
        
        if result.get('success'):
            print("✅ 升级成功！")
            print(f"   Transaction ID: {result.get('transaction_id')}")
            print("\n说明：升级操作成功，说明降级可能被 IWS 限制")
        else:
            print("❌ 升级失败")
            print(f"   原因: {result.get('message')}")
            
    except Exception as e:
        print(f"❌ 升级失败: {str(e)}")
        print("\n⚠️ 重要发现：升级也失败了！")
        print("这说明问题不是降级限制，而是更根本的问题：")
        print("1. SITEST 环境可能不允许变更资费（任何变更）")
        print("2. subscriberAccountNumber 可能有问题")
        print("3. accountUpdate 方法可能在 SITEST 中不可用")
        print("4. SP 账号权限可能不足")


def check_soap_request_details(imei: str):
    """检查 SOAP 请求的详细内容"""
    print("\n" + "="*70)
    print("🔬 详细检查：SOAP 请求内容")
    print("="*70)
    
    gateway = IWSGateway()
    
    try:
        # 步骤 1: 获取 subscriberAccountNumber
        print("\n📍 步骤 1: 获取 subscriberAccountNumber")
        print("-" * 70)
        
        search_result = gateway.search_account(imei)
        
        if not search_result.get('found'):
            print("❌ 无法获取账号信息")
            return
        
        subscriber_account_number = search_result.get('subscriber_account_number')
        print(f"✅ Subscriber Account Number: {subscriber_account_number}")
        
        # 检查格式
        if subscriber_account_number:
            print(f"   格式检查:")
            print(f"   • 长度: {len(subscriber_account_number)}")
            print(f"   • 前缀: {subscriber_account_number[:3] if len(subscriber_account_number) >= 3 else 'N/A'}")
            print(f"   • 包含字符: {set(subscriber_account_number)}")
            
            if not subscriber_account_number.startswith('SUB-'):
                print("   ⚠️ 警告: 账号格式可能不正确（通常应该是 SUB-开头）")
        
        # 步骤 2: 构建测试请求
        print("\n📍 步骤 2: 构建 accountUpdate SOAP 请求")
        print("-" * 70)
        
        test_plan_id = '763925351'  # SBD 30
        action_name, soap_body = gateway._build_account_update_body(
            imei=imei,
            subscriber_account_number=subscriber_account_number,
            new_plan_id=test_plan_id,
            lrit_flagstate="",
            ring_alerts_flag=False
        )
        
        print(f"✅ 请求构建成功")
        print(f"\n完整的 SOAP Body:")
        print("-" * 70)
        print(soap_body)
        print("-" * 70)
        
        # 步骤 3: 检查关键字段
        print("\n📍 步骤 3: 检查关键字段")
        print("-" * 70)
        
        import re
        
        # 提取关键信息
        username_match = re.search(r'<iwsUsername>(.*?)</iwsUsername>', soap_body)
        signature_match = re.search(r'<signature>(.*?)</signature>', soap_body)
        sp_account_match = re.search(r'<serviceProviderAccountNumber>(.*?)</serviceProviderAccountNumber>', soap_body)
        subscriber_match = re.search(r'<subscriberAccountNumber>(.*?)</subscriberAccountNumber>', soap_body)
        imei_match = re.search(r'<imei>(.*?)</imei>', soap_body)
        bundle_match = re.search(r'<sbdBundleId>(.*?)</sbdBundleId>', soap_body)
        
        print(f"关键字段值:")
        print(f"  • iwsUsername: {username_match.group(1) if username_match else 'NOT FOUND'}")
        print(f"  • signature: {signature_match.group(1)[:30] + '...' if signature_match else 'NOT FOUND'}")
        print(f"  • serviceProviderAccountNumber: {sp_account_match.group(1) if sp_account_match else 'NOT FOUND'}")
        print(f"  • subscriberAccountNumber: {subscriber_match.group(1) if subscriber_match else 'NOT FOUND'}")
        print(f"  • imei: {imei_match.group(1) if imei_match else 'NOT FOUND'}")
        print(f"  • sbdBundleId: {bundle_match.group(1) if bundle_match else 'NOT FOUND'}")
        
        # 验证字段
        print(f"\n字段验证:")
        issues = []
        
        if subscriber_match:
            sub_num = subscriber_match.group(1)
            if not sub_num or sub_num == 'None':
                issues.append("❌ subscriberAccountNumber 为空或 None")
            elif not sub_num.startswith('SUB-'):
                issues.append(f"⚠️ subscriberAccountNumber 格式可能不正确: {sub_num}")
        
        if bundle_match:
            bundle_id = bundle_match.group(1)
            if len(bundle_id) != 9:
                issues.append(f"⚠️ sbdBundleId 长度不是 9 位: {bundle_id} (长度: {len(bundle_id)})")
        
        if issues:
            for issue in issues:
                print(f"  {issue}")
        else:
            print("  ✅ 所有字段看起来正常")
        
        # 步骤 4: 比较成功的请求
        print("\n📍 步骤 4: 与成功的查询请求对比")
        print("-" * 70)
        
        print("查询请求 (accountSearch) 可以成功，说明:")
        print("  ✅ 认证信息正确 (username, signature)")
        print("  ✅ SP Account 正确")
        print("  ✅ IMEI 存在且有效")
        print("")
        print("accountUpdate 请求失败，可能的差异:")
        print("  ⚠️ subscriberAccountNumber 的使用方式")
        print("  ⚠️ 请求结构不同")
        print("  ⚠️ SITEST 对 accountUpdate 的限制")
        
    except Exception as e:
        print(f"\n❌ 检查过程出错: {str(e)}")
        import traceback
        print("\n完整错误追踪:")
        print(traceback.format_exc())


if __name__ == "__main__":
    # 测试 IMEI
    test_imei = "301434061230580"
    
    # 运行诊断
    diagnose_imei_status(test_imei)
    
    # 询问是否测试升级
    print("\n" + "="*70)
    response = input("是否要测试升级操作？(y/n): ")
    if response.lower() == 'y':
        test_upgrade_operation(test_imei)
    
    # 询问是否检查 SOAP 请求详情
    print("\n" + "="*70)
    response = input("是否要检查 SOAP 请求详细内容？(y/n): ")
    if response.lower() == 'y':
        check_soap_request_details(test_imei)

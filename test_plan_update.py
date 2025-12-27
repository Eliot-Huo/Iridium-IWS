#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试资费变更的完整流程
严格按照 IWS 开发规范 v4.0
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.iws_gateway import IWSGateway

def test_plan_update_flow(imei: str, target_plan_code: str):
    """
    测试资费变更的完整流程
    
    严格按照 IWS 规范：
    1. getSBDBundles - 查询可用资费代码
    2. getSubscriberAccount/accountSearch - 获取当前账户
    3. accountUpdate - 执行更新
    4. 检查 PENDING 状态
    """
    print("=" * 70)
    print("🧪 测试资费变更流程（严格符合 IWS 规范 v4.0）")
    print("=" * 70)
    print(f"IMEI: {imei}")
    print(f"目标方案: {target_plan_code}")
    print("=" * 70 + "\n")
    
    gateway = IWSGateway()
    
    try:
        # ========== 步骤 1: getSBDBundles ==========
        print("📍 步骤 1: 查询可用的资费代码（getSBDBundles）")
        print("-" * 70)
        
        bundles_result = gateway.get_sbd_bundles(
            from_bundle_id="0",  # 或当前的 bundle ID
            for_activate=False    # False = 更新现有账号
        )
        
        if bundles_result.get('success'):
            print(f"✅ 查询成功，找到 {bundles_result['count']} 个方案")
            
            # 显示所有可用方案
            print("\n可用方案列表:")
            for i, bundle in enumerate(bundles_result['bundles'], 1):
                print(f"\n  方案 {i}:")
                for key, value in bundle.items():
                    print(f"    {key}: {value}")
            
            # 查找目标方案
            print(f"\n🔍 查找目标方案: {target_plan_code}")
            
            target_bundle = None
            for bundle in bundles_result['bundles']:
                # 尝试多个可能的字段名
                bundle_code = (bundle.get('bundleCode') or 
                              bundle.get('code') or 
                              bundle.get('name') or
                              bundle.get('bundleName'))
                
                bundle_id = (bundle.get('bundleId') or 
                            bundle.get('id'))
                
                print(f"  检查: {bundle_code} (ID: {bundle_id})")
                
                if bundle_code == target_plan_code:
                    target_bundle = bundle
                    print(f"  ✅ 找到匹配！")
                    break
            
            if target_bundle:
                print(f"\n✅ 目标方案详情:")
                for key, value in target_bundle.items():
                    print(f"    {key}: {value}")
                
                # 提取 sbdBundleId
                sbd_bundle_id = (target_bundle.get('bundleId') or 
                                target_bundle.get('id'))
                
                print(f"\n📋 sbdBundleId 字段值: {sbd_bundle_id}")
                print(f"   类型: {type(sbd_bundle_id)}")
                
                if sbd_bundle_id:
                    print(f"\n✅ 将使用此值填入 <sbdBundleId> 字段")
                else:
                    print(f"\n⚠️ 警告：无法提取 bundleId，将使用方案代码: {target_plan_code}")
                    sbd_bundle_id = target_plan_code
            else:
                print(f"\n❌ 错误：在返回的方案中未找到 {target_plan_code}")
                print(f"   可能的原因:")
                print(f"   1. 方案代码不匹配（检查大小写）")
                print(f"   2. 字段名不对（bundleCode vs code vs name）")
                print(f"   3. 该方案不可用")
                return
        else:
            print("❌ 查询失败")
            return
        
        # ========== 步骤 2: accountSearch/getSubscriberAccount ==========
        print("\n\n📍 步骤 2: 获取当前账户对象（accountSearch）")
        print("-" * 70)
        
        search_result = gateway.search_account(imei)
        
        if search_result.get('found'):
            print("✅ 账户查询成功")
            print(f"   Account Number: {search_result.get('subscriber_account_number')}")
            print(f"   Status: {search_result.get('status')}")
            print(f"   Current Plan: {search_result.get('plan_name')}")
            
            # 检查 PENDING 状态
            if search_result.get('status') == 'PENDING':
                print("\n❌ 错误：账号当前有正在处理的订单（PENDING 状态）")
                print("   根据 IWS 规范，PENDING 状态下禁止任何更新操作")
                print("   必须等待当前订单完成后才能变更资费")
                return
            else:
                print(f"\n✅ 账号状态正常（{search_result.get('status')}），可以更新")
        else:
            print("❌ 账户未找到")
            return
        
        # ========== 步骤 3: 执行 accountUpdate ==========
        print("\n\n📍 步骤 3: 执行更新请求（accountUpdate）")
        print("-" * 70)
        
        print(f"准备执行 update_subscriber_plan:")
        print(f"  imei: {imei}")
        print(f"  new_plan_code: {target_plan_code}")
        
        # 调用更新函数
        result = gateway.update_subscriber_plan(
            imei=imei,
            new_plan_code=target_plan_code  # 使用正确的参数名
        )
        
        if result.get('success'):
            print("\n" + "=" * 70)
            print("✅ ✅ ✅ 资费变更成功！✅ ✅ ✅")
            print("=" * 70)
            print(f"Transaction ID: {result.get('transaction_id')}")
            print(f"当前方案: {result.get('current_plan')}")
            print(f"目标方案: {result.get('target_plan_code')}")
            print(f"Bundle ID: {result.get('target_bundle_id')}")
            print("")
            print("下一步:")
            print("• 等待 5-15 分钟让系统处理")
            print("• 账号状态会变为 PENDING")
            print("• 使用 getQueueEntry 追踪进度")
            print("• 完成后状态变回 ACTIVE")
            print("=" * 70)
        else:
            print("\n❌ 资费变更失败")
            print(f"错误: {result.get('message')}")
    
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        print("\n完整错误:")
        print(traceback.format_exc())


if __name__ == "__main__":
    # 测试参数
    test_imei = "301434061230580"
    test_plan = "SBD12"  # 或 "SBD30"
    
    # 运行测试
    test_plan_update_flow(test_imei, test_plan)

"""
初始化預設 Price Profiles
根據 Exhibit B 創建初始 Profile
"""
from datetime import datetime
from src.config.price_profile import PriceProfileManager


def create_default_customer_profile():
    """創建預設客戶售價 Profile (2025H2)"""
    
    plans = {
        # Standard Plans
        "SBD0": {
            "plan_name": "SBD0",
            "monthly_rate": 20.00,
            "included_bytes": 0,
            "overage_per_1000": 2.10,
            "min_message_size": 30,
            "activation_fee": 0.00,
            "suspended_fee": 4.00,
            "mailbox_check_fee": 0.02,
            "registration_fee": 0.02,
            "is_dsg": False
        },
        "SBD12": {
            "plan_name": "SBD12",
            "monthly_rate": 28.00,
            "included_bytes": 12000,
            "overage_per_1000": 2.00,
            "min_message_size": 10,
            "activation_fee": 50.00,
            "suspended_fee": 4.00,
            "mailbox_check_fee": 0.02,
            "registration_fee": 0.02,
            "is_dsg": False
        },
        "SBD17": {
            "plan_name": "SBD17",
            "monthly_rate": 30.00,
            "included_bytes": 17000,
            "overage_per_1000": 1.60,
            "min_message_size": 10,
            "activation_fee": 50.00,
            "suspended_fee": 4.00,
            "mailbox_check_fee": 0.02,
            "registration_fee": 0.02,
            "is_dsg": False
        },
        "SBD30": {
            "plan_name": "SBD30",
            "monthly_rate": 50.00,
            "included_bytes": 30000,
            "overage_per_1000": 1.50,
            "min_message_size": 10,
            "activation_fee": 50.00,
            "suspended_fee": 4.00,
            "mailbox_check_fee": 0.02,
            "registration_fee": 0.02,
            "is_dsg": False
        },
        
        # DSG Plans (Standard × 1.35)
        "SBD12P": {
            "plan_name": "SBD12P",
            "monthly_rate": 37.80,      # $28.00 × 1.35
            "included_bytes": 12000,
            "overage_per_1000": 2.70,   # $2.00 × 1.35
            "min_message_size": 10,
            "activation_fee": 50.00,
            "suspended_fee": 5.40,      # $4.00 × 1.35
            "mailbox_check_fee": 0.027, # $0.02 × 1.35
            "registration_fee": 0.027,  # $0.02 × 1.35
            "is_dsg": True,
            "min_isus": 2,
            "max_isus": 10000,
            "max_dsgs": 15
        },
        "SBD17P": {
            "plan_name": "SBD17P",
            "monthly_rate": 40.50,      # $30.00 × 1.35
            "included_bytes": 17000,
            "overage_per_1000": 2.16,   # $1.60 × 1.35
            "min_message_size": 10,
            "activation_fee": 50.00,
            "suspended_fee": 5.40,      # $4.00 × 1.35
            "mailbox_check_fee": 0.027,
            "registration_fee": 0.027,
            "is_dsg": True,
            "min_isus": 2,
            "max_isus": 10000,
            "max_dsgs": 15
        },
        "SBD30P": {
            "plan_name": "SBD30P",
            "monthly_rate": 67.50,      # $50.00 × 1.35
            "included_bytes": 30000,
            "overage_per_1000": 2.03,   # $1.50 × 1.35 (四捨五入)
            "min_message_size": 10,
            "activation_fee": 50.00,
            "suspended_fee": 5.40,      # $4.00 × 1.35
            "mailbox_check_fee": 0.027,
            "registration_fee": 0.027,
            "is_dsg": True,
            "min_isus": 2,
            "max_isus": 10000,
            "max_dsgs": 15
        }
    }
    
    return {
        "profile_id": "customer_2025H2",
        "profile_name": "2025年下半年客戶售價",
        "profile_type": "customer",
        "effective_date": "2025-07-01",
        "created_by": "system",
        "notes": "初始客戶售價 Profile（根據 SBD_Airtime_STD.pdf 2025/1/7）",
        "plans": plans
    }


def create_default_iridium_cost_profile():
    """創建預設 Iridium 成本 Profile (2025H2)"""
    
    plans = {
        # Standard Plans
        "SBD0": {
            "plan_name": "SBD0",
            "monthly_rate": 10.00,
            "included_bytes": 0,
            "overage_per_1000": 0.75,
            "min_message_size": 30,
            "activation_fee": 0.00,
            "suspended_fee": 1.00,
            "mailbox_check_fee": 0.01,
            "registration_fee": 0.01,
            "is_dsg": False
        },
        "SBD12": {
            "plan_name": "SBD12",
            "monthly_rate": 14.00,
            "included_bytes": 12000,
            "overage_per_1000": 0.80,
            "min_message_size": 10,
            "activation_fee": 30.00,
            "suspended_fee": 1.50,
            "mailbox_check_fee": 0.01,
            "registration_fee": 0.01,
            "is_dsg": False
        },
        "SBD17": {
            "plan_name": "SBD17",
            "monthly_rate": 15.00,
            "included_bytes": 17000,
            "overage_per_1000": 1.00,
            "min_message_size": 10,
            "activation_fee": 30.00,
            "suspended_fee": 1.00,
            "mailbox_check_fee": 0.01,
            "registration_fee": 0.01,
            "is_dsg": False
        },
        "SBD30": {
            "plan_name": "SBD30",
            "monthly_rate": 25.00,
            "included_bytes": 30000,
            "overage_per_1000": 0.75,
            "min_message_size": 10,
            "activation_fee": 30.00,
            "suspended_fee": 1.00,
            "mailbox_check_fee": 0.01,
            "registration_fee": 0.01,
            "is_dsg": False
        },
        
        # DSG Plans (Exhibit B Table 10 直接價格)
        "SBD12P": {
            "plan_name": "SBD12P",
            "monthly_rate": 15.00,
            "included_bytes": 12000,
            "overage_per_1000": 1.25,
            "min_message_size": 10,
            "activation_fee": 15.00,
            "suspended_fee": 1.00,
            "mailbox_check_fee": 0.01,
            "registration_fee": 0.01,
            "is_dsg": True,
            "min_isus": 2,
            "max_isus": 10000,
            "max_dsgs": 15
        },
        "SBD17P": {
            "plan_name": "SBD17P",
            "monthly_rate": 17.00,
            "included_bytes": 17000,
            "overage_per_1000": 1.00,
            "min_message_size": 10,
            "activation_fee": 15.00,
            "suspended_fee": 1.00,
            "mailbox_check_fee": 0.01,
            "registration_fee": 0.01,
            "is_dsg": True,
            "min_isus": 2,
            "max_isus": 10000,
            "max_dsgs": 15
        },
        "SBD30P": {
            "plan_name": "SBD30P",
            "monthly_rate": 27.00,
            "included_bytes": 30000,
            "overage_per_1000": 0.75,
            "min_message_size": 10,
            "activation_fee": 15.00,
            "suspended_fee": 1.00,
            "mailbox_check_fee": 0.01,
            "registration_fee": 0.01,
            "is_dsg": True,
            "min_isus": 2,
            "max_isus": 10000,
            "max_dsgs": 15
        }
    }
    
    return {
        "profile_id": "iridium_cost_2025H2",
        "profile_name": "2025年下半年 Iridium 成本價",
        "profile_type": "iridium_cost",
        "effective_date": "2025-06-23",
        "created_by": "system",
        "notes": "Iridium 官方成本價（根據 Exhibit B-3.1 & B-3.3, Ver 23 June 2025）",
        "plans": plans
    }


def initialize_default_profiles():
    """初始化預設 Profiles"""
    
    print("=" * 60)
    print("🚀 初始化預設 Price Profiles")
    print("=" * 60)
    
    manager = PriceProfileManager()
    
    # 檢查是否已存在
    existing_customer = manager.get_profile_at_date('customer', datetime(2025, 7, 1).date())
    existing_cost = manager.get_profile_at_date('iridium_cost', datetime(2025, 6, 23).date())
    
    if existing_customer:
        print(f"ℹ️  客戶售價 Profile 已存在: {existing_customer.profile_id}")
    else:
        print("📝 創建客戶售價 Profile...")
        customer_data = create_default_customer_profile()
        manager.create_profile(**customer_data)
        print("✅ 客戶售價 Profile 創建完成")
    
    if existing_cost:
        print(f"ℹ️  Iridium 成本 Profile 已存在: {existing_cost.profile_id}")
    else:
        print("📝 創建 Iridium 成本 Profile...")
        cost_data = create_default_iridium_cost_profile()
        manager.create_profile(**cost_data)
        print("✅ Iridium 成本 Profile 創建完成")
    
    print("\n" + "=" * 60)
    print("📋 當前 Profiles 列表:")
    print("=" * 60)
    
    for profile in manager.list_profiles():
        status = "🔒 已鎖定" if profile.is_locked else "🔓 未鎖定"
        print(f"\n{status} {profile.profile_id}")
        print(f"   類型: {profile.profile_type}")
        print(f"   名稱: {profile.profile_name}")
        print(f"   生效日期: {profile.effective_date}")
        print(f"   方案數: {len(profile.plans)}")
    
    print("\n" + "=" * 60)
    print("✅ 初始化完成！")
    print("=" * 60)


if __name__ == '__main__':
    initialize_default_profiles()

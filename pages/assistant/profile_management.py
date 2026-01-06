"""
Price Profile 管理頁面
"""
import streamlit as st
from datetime import datetime, date
from src.config.price_profile import PriceProfileManager, PlanPricing
import json


def render_profile_management_page():
    """渲染 Price Profile 管理頁面"""
    
    st.title("💰 Price Profile 管理")
    st.markdown("---")
    
    # 初始化 Manager
    if 'profile_manager' not in st.session_state:
        st.session_state.profile_manager = PriceProfileManager()
    
    manager = st.session_state.profile_manager
    
    # 頁籤
    tab1, tab2, tab3 = st.tabs(["📋 Profile 列表", "➕ 創建 Profile", "📊 價格對比"])
    
    with tab1:
        render_profile_list(manager)
    
    with tab2:
        render_create_profile(manager)
    
    with tab3:
        render_price_comparison(manager)


def render_profile_list(manager: PriceProfileManager):
    """渲染 Profile 列表"""
    
    st.subheader("📋 所有 Price Profiles")
    
    # 過濾選項
    col1, col2 = st.columns(2)
    
    with col1:
        profile_type_filter = st.selectbox(
            "Profile 類型",
            options=["全部", "customer", "iridium_cost"],
            format_func=lambda x: {
                "全部": "全部",
                "customer": "客戶售價",
                "iridium_cost": "Iridium 成本"
            }[x]
        )
    
    # 取得 Profiles
    if profile_type_filter == "全部":
        profiles = manager.list_profiles()
    else:
        profiles = manager.list_profiles(profile_type=profile_type_filter)
    
    if not profiles:
        st.info("📭 目前沒有任何 Profile")
        st.markdown("請到「創建 Profile」頁籤新增，或執行 `python initialize_profiles.py` 初始化預設 Profile")
        return
    
    # 顯示 Profiles
    st.markdown(f"**共 {len(profiles)} 個 Profile**")
    st.markdown("---")
    
    for profile in profiles:
        render_profile_card(profile)


def render_profile_card(profile):
    """渲染單個 Profile 卡片"""
    
    # 狀態標籤
    if profile.is_locked:
        status_badge = "🔒 已鎖定"
        status_color = "red"
    else:
        status_badge = "🔓 未鎖定"
        status_color = "green"
    
    # Profile 類型
    type_label = "客戶售價" if profile.profile_type == "customer" else "Iridium 成本"
    
    # 展開面板
    with st.expander(f"{status_badge} **{profile.profile_name}** ({profile.profile_id})", expanded=False):
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"**類型：** {type_label}")
            st.markdown(f"**生效日期：** {profile.effective_date}")
        
        with col2:
            st.markdown(f"**創建時間：** {profile.created_at[:10]}")
            st.markdown(f"**創建者：** {profile.created_by}")
        
        with col3:
            st.markdown(f"**方案數：** {len(profile.plans)}")
            st.markdown(f"**狀態：** :{status_color}[{status_badge}]")
        
        if profile.notes:
            st.info(f"📝 {profile.notes}")
        
        # 顯示方案列表
        st.markdown("#### 包含的方案：")
        
        # 分成 Standard 和 DSG
        standard_plans = {k: v for k, v in profile.plans.items() if not v.is_dsg}
        dsg_plans = {k: v for k, v in profile.plans.items() if v.is_dsg}
        
        if standard_plans:
            st.markdown("**Standard Plans:**")
            render_plans_table(standard_plans)
        
        if dsg_plans:
            st.markdown("**DSG Plans:**")
            render_plans_table(dsg_plans)
        
        # 操作按鈕
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if st.button("📄 查看 JSON", key=f"view_{profile.profile_id}"):
                st.json(profile.to_dict())
        
        st.markdown("---")


def render_plans_table(plans: dict):
    """渲染方案表格"""
    import pandas as pd
    
    data = []
    for plan_name, pricing in plans.items():
        data.append({
            '方案': plan_name,
            '月租費': f"${pricing.monthly_rate:.2f}",
            '包含流量': f"{pricing.included_bytes:,} bytes",
            '超量費': f"${pricing.overage_per_1000:.2f}/KB",
            '啟用費': f"${pricing.activation_fee:.2f}",
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_create_profile(manager: PriceProfileManager):
    """渲染創建 Profile 介面"""
    
    st.subheader("➕ 創建新 Profile")
    
    st.info("💡 **提示：** 建議先複製現有 Profile 再修改，確保包含所有必要方案")
    
    # 複製來源
    st.markdown("### 步驟 1：選擇複製來源")
    
    col1, col2 = st.columns(2)
    
    with col1:
        source_type = st.selectbox(
            "Profile 類型",
            options=["customer", "iridium_cost"],
            format_func=lambda x: "客戶售價" if x == "customer" else "Iridium 成本"
        )
    
    with col2:
        source_profiles = manager.list_profiles(profile_type=source_type)
        if not source_profiles:
            st.warning("⚠️ 沒有可複製的 Profile")
            st.info("💡 請先初始化預設 Profiles")
            
            if st.button("🚀 執行初始化", type="primary", key="init_profiles"):
                with st.spinner("正在初始化 Profiles..."):
                    try:
                        # 執行初始化腳本（使用相對路徑）
                        import subprocess
                        import sys
                        from pathlib import Path
                        
                        # 取得專案根目錄
                        project_root = Path(__file__).parent.parent.parent
                        script_path = project_root / "scripts" / "initialize_profiles.py"
                        
                        result = subprocess.run(
                            [sys.executable, str(script_path)],
                            capture_output=True,
                            text=True,
                            cwd=str(project_root)
                        )
                        
                        if result.returncode == 0:
                            st.success("✅ 初始化成功！")
                            st.rerun()
                        else:
                            st.error(f"❌ 初始化失敗")
                            with st.expander("查看錯誤詳情"):
                                st.code(result.stderr)
                    except Exception as e:
                        st.error(f"❌ 執行失敗: {str(e)}")
            
            st.markdown("或者手動執行：")
            st.code("python scripts/initialize_profiles.py", language="bash")
            return
        
        source_profile = st.selectbox(
            "複製來源",
            options=source_profiles,
            format_func=lambda p: f"{p.profile_name} ({p.effective_date})"
        )
    
    # 新 Profile 資訊
    st.markdown("---")
    st.markdown("### 步驟 2：設定新 Profile 資訊")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_profile_id = st.text_input(
            "Profile ID",
            value=f"{source_type}_{datetime.now().strftime('%Y%m%d')}",
            help="唯一識別碼，例如：customer_2026Q1"
        )
        
        new_profile_name = st.text_input(
            "Profile 名稱",
            value=f"{source_profile.profile_name} (副本)",
            help="顯示名稱，例如：2026年第一季客戶售價"
        )
    
    with col2:
        new_effective_date = st.date_input(
            "生效日期",
            value=date.today(),
            help="建議設定為每月1號"
        )
        
        new_notes = st.text_area(
            "備註",
            value="",
            help="記錄此次價格調整的原因"
        )
    
    # 價格調整
    st.markdown("---")
    st.markdown("### 步驟 3：調整價格（選填）")
    
    st.info("💡 如果不需要調整價格，可以直接跳到步驟4創建")
    
    # 選擇要調整的方案
    plan_to_edit = st.selectbox(
        "選擇要調整的方案",
        options=list(source_profile.plans.keys())
    )
    
    if plan_to_edit:
        original_pricing = source_profile.plans[plan_to_edit]
        
        st.markdown(f"#### 原始價格（{plan_to_edit}）：")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("月租費", f"${original_pricing.monthly_rate:.2f}")
        with col2:
            st.metric("包含流量", f"{original_pricing.included_bytes:,}")
        with col3:
            st.metric("超量費", f"${original_pricing.overage_per_1000:.2f}/KB")
        with col4:
            st.metric("啟用費", f"${original_pricing.activation_fee:.2f}")
        
        st.markdown("#### 調整為：")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            new_monthly_rate = st.number_input(
                "月租費 ($)",
                value=float(original_pricing.monthly_rate),
                min_value=0.0,
                step=0.5,
                key=f"rate_{plan_to_edit}"
            )
        
        with col2:
            st.markdown("包含流量")
            st.markdown(f"{original_pricing.included_bytes:,} bytes")
            st.caption("(包含流量不可修改)")
        
        with col3:
            new_overage = st.number_input(
                "超量費 ($/KB)",
                value=float(original_pricing.overage_per_1000),
                min_value=0.0,
                step=0.1,
                key=f"overage_{plan_to_edit}"
            )
        
        with col4:
            new_activation = st.number_input(
                "啟用費 ($)",
                value=float(original_pricing.activation_fee),
                min_value=0.0,
                step=5.0,
                key=f"activation_{plan_to_edit}"
            )
        
        # 儲存調整
        if f'price_adjustments_{source_type}' not in st.session_state:
            st.session_state[f'price_adjustments_{source_type}'] = {}
        
        st.session_state[f'price_adjustments_{source_type}'][plan_to_edit] = {
            'monthly_rate': new_monthly_rate,
            'overage_per_1000': new_overage,
            'activation_fee': new_activation
        }
    
    # 創建按鈕
    st.markdown("---")
    st.markdown("### 步驟 4：創建 Profile")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        if st.button("✅ 創建 Profile", type="primary", use_container_width=True):
            try:
                # 複製方案
                new_plans = {}
                for plan_name, pricing in source_profile.plans.items():
                    plan_dict = pricing.to_dict()
                    
                    # 應用調整
                    if f'price_adjustments_{source_type}' in st.session_state:
                        adjustments = st.session_state[f'price_adjustments_{source_type}']
                        if plan_name in adjustments:
                            plan_dict.update(adjustments[plan_name])
                    
                    new_plans[plan_name] = plan_dict
                
                # 創建 Profile
                new_profile = manager.create_profile(
                    profile_id=new_profile_id,
                    profile_name=new_profile_name,
                    profile_type=source_type,
                    effective_date=new_effective_date.strftime('%Y-%m-%d'),
                    created_by=st.session_state.get('user_email', 'admin'),
                    notes=new_notes,
                    plans=new_plans
                )
                
                st.success(f"✅ Profile 創建成功：{new_profile.profile_id}")
                st.balloons()
                
                # 清除調整
                if f'price_adjustments_{source_type}' in st.session_state:
                    del st.session_state[f'price_adjustments_{source_type}']
                
                # 重新載入
                st.session_state.profile_manager.load_all_profiles()
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ 創建失敗：{e}")


def render_price_comparison(manager: PriceProfileManager):
    """渲染價格對比"""
    
    st.subheader("📊 價格對比")
    
    # 選擇要對比的 Profile
    col1, col2 = st.columns(2)
    
    with col1:
        customer_profiles = manager.list_profiles(profile_type='customer')
        if not customer_profiles:
            st.warning("⚠️ 沒有客戶售價 Profile")
            return
        
        profile1 = st.selectbox(
            "客戶售價 Profile",
            options=customer_profiles,
            format_func=lambda p: f"{p.profile_name} ({p.effective_date})"
        )
    
    with col2:
        cost_profiles = manager.list_profiles(profile_type='iridium_cost')
        if not cost_profiles:
            st.warning("⚠️ 沒有 Iridium 成本 Profile")
            return
        
        profile2 = st.selectbox(
            "Iridium 成本 Profile",
            options=cost_profiles,
            format_func=lambda p: f"{p.profile_name} ({p.effective_date})"
        )
    
    if not profile1 or not profile2:
        return
    
    # 選擇方案
    plan_name = st.selectbox(
        "選擇方案",
        options=list(profile1.plans.keys())
    )
    
    if plan_name not in profile2.plans:
        st.error(f"❌ Iridium 成本 Profile 中沒有 {plan_name}")
        return
    
    # 對比
    st.markdown("---")
    st.markdown(f"### {plan_name} 價格對比")
    
    customer_pricing = profile1.plans[plan_name]
    cost_pricing = profile2.plans[plan_name]
    
    # 基本費用對比
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "月租費",
            f"${customer_pricing.monthly_rate:.2f}",
            delta=f"${customer_pricing.monthly_rate - cost_pricing.monthly_rate:.2f}",
            delta_color="normal"
        )
        profit_rate = (customer_pricing.monthly_rate - cost_pricing.monthly_rate) / customer_pricing.monthly_rate * 100
        st.caption(f"利潤率：{profit_rate:.1f}%")
    
    with col2:
        st.metric(
            "超量費 ($/KB)",
            f"${customer_pricing.overage_per_1000:.2f}",
            delta=f"${customer_pricing.overage_per_1000 - cost_pricing.overage_per_1000:.2f}",
            delta_color="normal"
        )
        overage_profit_rate = (customer_pricing.overage_per_1000 - cost_pricing.overage_per_1000) / customer_pricing.overage_per_1000 * 100
        st.caption(f"利潤率：{overage_profit_rate:.1f}%")
    
    with col3:
        st.metric(
            "啟用費",
            f"${customer_pricing.activation_fee:.2f}",
            delta=f"${customer_pricing.activation_fee - cost_pricing.activation_fee:.2f}",
            delta_color="normal"
        )
    
    # 利潤模擬
    st.markdown("---")
    st.markdown("### 💰 利潤模擬")
    
    col1, col2 = st.columns(2)
    
    with col1:
        usage_bytes = st.number_input(
            "月用量 (bytes)",
            value=15000,
            min_value=0,
            step=1000,
            help="輸入預估月用量"
        )
    
    with col2:
        if customer_pricing.is_dsg:
            num_isus = st.number_input(
                "DSG 內 ISU 數量",
                value=10,
                min_value=customer_pricing.min_isus,
                max_value=customer_pricing.max_isus,
                step=1
            )
        else:
            num_isus = 1
    
    # 計算費用
    customer_total = customer_pricing.monthly_rate * num_isus
    customer_total += customer_pricing.calculate_overage_cost(usage_bytes * num_isus if customer_pricing.is_dsg else usage_bytes)
    
    cost_total = cost_pricing.monthly_rate * num_isus
    cost_total += cost_pricing.calculate_overage_cost(usage_bytes * num_isus if cost_pricing.is_dsg else usage_bytes)
    
    profit = customer_total - cost_total
    profit_margin = (profit / customer_total * 100) if customer_total > 0 else 0
    
    # 顯示結果
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("客戶收費", f"${customer_total:.2f}")
    
    with col2:
        st.metric("Iridium 成本", f"${cost_total:.2f}")
    
    with col3:
        st.metric(
            "本月利潤",
            f"${profit:.2f}",
            delta=f"{profit_margin:.1f}%",
            delta_color="normal"
        )


if __name__ == "__main__":
    render_profile_management_page()

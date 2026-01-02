"""
價格管理界面（助理模式）

功能：
- 查看當前價格
- 查看價格歷史
- 新增/調整價格
- 預覽價格變更
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import Optional

from src.config.price_rules import (
    PriceManager,
    PlanPricing,
    get_price_manager,
    PLAN_TO_BUNDLE
)


def render_price_management_page():
    """渲染價格管理頁面"""
    
    st.title("💰 SBD 價格管理")
    
    # 初始化價格管理器
    try:
        price_manager = get_price_manager()
    except Exception as e:
        st.error(f"❌ 初始化價格管理器失敗: {str(e)}")
        return
    
    # 頁面分頁
    tab1, tab2, tab3 = st.tabs([
        "📊 當前價格",
        "📝 調整價格",
        "📚 價格歷史"
    ])
    
    # ==================== 當前價格檢視 ====================
    with tab1:
        render_current_prices(price_manager)
    
    # ==================== 調整價格 ====================
    with tab2:
        render_price_adjustment(price_manager)
    
    # ==================== 價格歷史 ====================
    with tab3:
        render_price_history(price_manager)


def render_current_prices(price_manager: PriceManager):
    """渲染當前價格頁面"""
    
    st.subheader("📊 當前有效價格")
    st.caption("顯示目前各方案的有效價格（用於新的計帳週期）")
    
    # 取得所有當前價格
    current_prices = price_manager.get_all_current_prices()
    
    if not current_prices:
        st.warning("⚠️ 目前沒有有效價格，請先設定價格")
        return
    
    # 為每個方案顯示卡片
    cols = st.columns(2)
    
    for idx, (plan_name, pricing) in enumerate(current_prices.items()):
        with cols[idx % 2]:
            render_price_card(pricing)


def render_price_card(pricing: PlanPricing):
    """
    渲染價格卡片
    
    Args:
        pricing: PlanPricing 物件
    """
    # 方案標題
    bundle_id = PLAN_TO_BUNDLE.get(pricing.plan_name, "N/A")
    
    with st.container(border=True):
        # 標題
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 🔹 {pricing.plan_name}")
            st.caption(f"Bundle ID: `{bundle_id}`")
        with col2:
            st.markdown(f"**v{pricing.version}**")
            st.caption(f"生效: {pricing.effective_date}")
        
        # 價格資訊
        st.markdown("---")
        
        # 月租費
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💵 月租費", f"${pricing.monthly_rate:.2f}")
        with col2:
            st.metric("📦 包含數據", f"{pricing.included_bytes:,} bytes")
        
        # 超量費用
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📈 超量費用", f"${pricing.overage_per_1000:.2f} / 1K bytes")
        with col2:
            st.metric("📏 最小訊息", f"{pricing.min_message_size} bytes")
        
        # 其他費用
        st.markdown("**其他費用**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"🔓 啟用: ${pricing.activation_fee:.2f}")
        with col2:
            st.caption(f"⏸️ 暫停: ${pricing.suspended_fee:.2f}")
        with col3:
            st.caption(f"📬 Mailbox: ${pricing.mailbox_check_fee:.2f}")
        
        # 備註
        if pricing.notes:
            st.info(f"📝 備註: {pricing.notes}")


def render_price_adjustment(price_manager: PriceManager):
    """渲染價格調整頁面"""
    
    st.subheader("📝 調整價格")
    st.caption("調整價格將創建新的價格版本，歷史價格會保留用於查詢舊帳單")
    
    # 選擇方案
    plan_name = st.selectbox(
        "選擇要調整的方案",
        options=['SBD0', 'SBD12', 'SBD17', 'SBD30'],
        help="選擇要調整價格的 SBD 方案"
    )
    
    # 取得當前價格作為預設值
    current_price = price_manager.get_current_price(plan_name)
    
    if not current_price:
        st.warning(f"⚠️ {plan_name} 目前沒有價格，請先設定初始價格")
        return
    
    st.markdown("---")
    
    # 顯示當前價格
    with st.expander("📊 當前價格", expanded=False):
        render_price_card(current_price)
    
    st.markdown("---")
    
    # 新價格表單
    st.markdown("### 🆕 新價格設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        monthly_rate = st.number_input(
            "💵 月租費 ($)",
            min_value=0.0,
            value=float(current_price.monthly_rate),
            step=0.50,
            format="%.2f",
            help="每月固定費用"
        )
        
        included_bytes = st.number_input(
            "📦 包含數據量 (bytes)",
            min_value=0,
            value=current_price.included_bytes,
            step=1000,
            help="月租費包含的數據量"
        )
        
        overage_per_1000 = st.number_input(
            "📈 超量費用 ($ / 1000 bytes)",
            min_value=0.0,
            value=float(current_price.overage_per_1000),
            step=0.10,
            format="%.2f",
            help="超過包含量後，每 1000 bytes 的費用"
        )
        
        min_message_size = st.number_input(
            "📏 最小訊息大小 (bytes)",
            min_value=1,
            value=current_price.min_message_size,
            step=1,
            help="最小計費訊息大小，小於此值按此值計費"
        )
    
    with col2:
        activation_fee = st.number_input(
            "🔓 啟用費 ($)",
            min_value=0.0,
            value=float(current_price.activation_fee),
            step=5.0,
            format="%.2f",
            help="設備啟用時的一次性費用"
        )
        
        suspended_fee = st.number_input(
            "⏸️ 暫停月費 ($)",
            min_value=0.0,
            value=float(current_price.suspended_fee),
            step=0.50,
            format="%.2f",
            help="設備暫停期間的月費"
        )
        
        mailbox_check_fee = st.number_input(
            "📬 Mailbox Check ($)",
            min_value=0.0,
            value=float(current_price.mailbox_check_fee),
            step=0.01,
            format="%.2f",
            help="每次 Mailbox Check 的費用"
        )
        
        registration_fee = st.number_input(
            "📝 Registration ($)",
            min_value=0.0,
            value=float(current_price.registration_fee),
            step=0.01,
            format="%.2f",
            help="每次 SBD Registration 的費用"
        )
    
    # 生效日期
    effective_date = st.date_input(
        "📅 生效日期",
        value=date.today(),
        help="新價格的生效日期（建議設定為下個月 1 號）"
    )
    
    # 備註
    notes = st.text_area(
        "📝 備註",
        value="",
        placeholder="說明此次價格調整的原因...",
        help="記錄價格調整的原因或說明"
    )
    
    st.markdown("---")
    
    # 變更預覽
    st.markdown("### 👀 變更預覽")
    
    changes = []
    if monthly_rate != current_price.monthly_rate:
        changes.append(f"💵 月租費: ${current_price.monthly_rate:.2f} → **${monthly_rate:.2f}**")
    if included_bytes != current_price.included_bytes:
        changes.append(f"📦 包含數據: {current_price.included_bytes:,} → **{included_bytes:,}** bytes")
    if overage_per_1000 != current_price.overage_per_1000:
        changes.append(f"📈 超量費用: ${current_price.overage_per_1000:.2f} → **${overage_per_1000:.2f}** / 1K bytes")
    if min_message_size != current_price.min_message_size:
        changes.append(f"📏 最小訊息: {current_price.min_message_size} → **{min_message_size}** bytes")
    if activation_fee != current_price.activation_fee:
        changes.append(f"🔓 啟用費: ${current_price.activation_fee:.2f} → **${activation_fee:.2f}**")
    if suspended_fee != current_price.suspended_fee:
        changes.append(f"⏸️ 暫停月費: ${current_price.suspended_fee:.2f} → **${suspended_fee:.2f}**")
    if mailbox_check_fee != current_price.mailbox_check_fee:
        changes.append(f"📬 Mailbox Check: ${current_price.mailbox_check_fee:.2f} → **${mailbox_check_fee:.2f}**")
    if registration_fee != current_price.registration_fee:
        changes.append(f"📝 Registration: ${current_price.registration_fee:.2f} → **${registration_fee:.2f}**")
    
    if changes:
        st.info("**變更項目：**\n\n" + "\n\n".join(changes))
    else:
        st.success("✅ 沒有變更")
    
    # 確認儲存
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col2:
        if st.button("🔙 取消", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("💾 儲存新價格", type="primary", use_container_width=True, disabled=not changes):
            try:
                # 新增價格版本
                new_price = price_manager.add_new_price(
                    plan_name=plan_name,
                    monthly_rate=monthly_rate,
                    included_bytes=included_bytes,
                    overage_per_1000=overage_per_1000,
                    min_message_size=min_message_size,
                    activation_fee=activation_fee,
                    suspended_fee=suspended_fee,
                    mailbox_check_fee=mailbox_check_fee,
                    registration_fee=registration_fee,
                    effective_date=effective_date.isoformat(),
                    notes=notes
                )
                
                st.success(f"✅ 成功儲存 {plan_name} 新價格 (v{new_price.version})！")
                st.balloons()
                
                # 重新整理頁面
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ 儲存失敗: {str(e)}")


def render_price_history(price_manager: PriceManager):
    """渲染價格歷史頁面"""
    
    st.subheader("📚 價格歷史")
    st.caption("查看各方案的歷史價格版本（用於計算舊帳單）")
    
    # 選擇方案
    plan_name = st.selectbox(
        "選擇方案",
        options=['SBD0', 'SBD12', 'SBD17', 'SBD30'],
        key="history_plan_select"
    )
    
    # 取得價格歷史
    history = price_manager.get_price_history(plan_name)
    
    if not history:
        st.info(f"ℹ️ {plan_name} 目前沒有價格歷史")
        return
    
    st.markdown("---")
    
    # 顯示歷史版本
    for pricing in history:
        with st.expander(
            f"📅 v{pricing.version} - 生效日期: {pricing.effective_date}",
            expanded=(pricing == history[0])  # 最新版本展開
        ):
            render_price_card(pricing)
            
            # 顯示時間軸
            if pricing == history[0]:
                st.success("🟢 目前使用中")
            else:
                st.info(f"🔵 歷史版本（用於 {pricing.effective_date} 之後的帳單計算）")
    
    # 統計資訊
    st.markdown("---")
    st.markdown("### 📊 統計資訊")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("總版本數", len(history))
    
    with col2:
        first_date = history[-1].effective_date if history else "N/A"
        st.metric("首次生效", first_date)
    
    with col3:
        latest_date = history[0].effective_date if history else "N/A"
        st.metric("最新生效", latest_date)


# ==================== 測試程式 ====================

if __name__ == "__main__":
    # 設定頁面
    st.set_page_config(
        page_title="價格管理",
        page_icon="💰",
        layout="wide"
    )
    
    # 渲染頁面
    render_price_management_page()

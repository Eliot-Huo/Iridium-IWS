"""
客戶計費查詢頁面

提供客戶查詢費用的功能。

Author: Senior Python Software Architect
Date: 2026-01-04
"""
import streamlit as st
from datetime import datetime

from src.ui.state.session_manager import SessionManager
from src.utils.logger import get_logger
from src.utils.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    BillingCalculationError
)


logger = get_logger('CustomerBillingPage')


def render_customer_billing_page() -> None:
    """
    渲染客戶計費查詢頁面
    
    功能：
    1. IMEI 輸入和驗證
    2. 年月選擇
    3. 費用查詢
    4. 結果顯示
    """
    st.header("📊 費用查詢")
    st.caption("查詢您的設備費用明細")
    
    # 取得服務
    billing_service = SessionManager.get_billing_service()
    
    # IMEI 輸入區
    imei = _render_imei_input()
    
    if not imei:
        st.info("👆 請輸入 IMEI 開始查詢")
        return
    
    # 日期選擇區
    year, month = _render_date_selector()
    
    # 查詢按鈕
    if st.button("🔍 查詢費用", type="primary", use_container_width=True):
        logger.info("User requested billing query", 
                   imei=imei, 
                   year=year, 
                   month=month)
        
        _perform_billing_query(billing_service, imei, year, month)


def _render_imei_input() -> str:
    """
    渲染 IMEI 輸入框
    
    Returns:
        用戶輸入的 IMEI（已驗證）
    """
    imei = st.text_input(
        "設備 IMEI",
        max_chars=15,
        placeholder="請輸入 15 位數字 IMEI",
        help="IMEI 必須是 15 位數字"
    )
    
    # 簡單驗證
    if imei and (len(imei) != 15 or not imei.isdigit()):
        st.error("❌ IMEI 必須是 15 位數字")
        return ""
    
    return imei


def _render_date_selector() -> tuple[int, int]:
    """
    渲染日期選擇器
    
    Returns:
        (year, month) 元組
    """
    current_date = datetime.now()
    
    col1, col2 = st.columns(2)
    
    with col1:
        year = st.number_input(
            "年份",
            min_value=2020,
            max_value=2030,
            value=current_date.year,
            step=1
        )
    
    with col2:
        month = st.number_input(
            "月份",
            min_value=1,
            max_value=12,
            value=current_date.month,
            step=1
        )
    
    return int(year), int(month)


def _perform_billing_query(billing_service, imei: str, year: int, month: int) -> None:
    """
    執行費用查詢
    
    Args:
        billing_service: Billing Service 實例
        imei: 設備 IMEI
        year: 年份
        month: 月份
    """
    with st.spinner("🔄 查詢中..."):
        try:
            # 查詢費用
            result = billing_service.query_monthly_bill(imei, year, month)
            
            logger.info("Billing query successful", 
                       imei=imei,
                       year=year,
                       month=month,
                       total_cost=result.get('total_cost', 0))
            
            # 顯示結果
            _display_billing_result(result, imei, year, month)
            
        except ValidationError as e:
            logger.warning("Validation error", exception=e, imei=imei)
            st.error(f"❌ 驗證錯誤：{e.message}")
            
        except ResourceNotFoundError as e:
            logger.warning("Resource not found", exception=e, imei=imei)
            st.error(f"❌ 找不到資源：{e.message}")
            
        except BillingCalculationError as e:
            logger.error("Billing calculation failed", exception=e, imei=imei)
            st.error(f"❌ 計費錯誤：{e.message}")
            
        except Exception as e:
            logger.error("Unexpected error in billing query", exception=e)
            st.error(f"❌ 系統錯誤：{str(e)}")


def _display_billing_result(result: dict, imei: str, year: int, month: int) -> None:
    """
    顯示費用查詢結果
    
    Args:
        result: 查詢結果字典
        imei: 設備 IMEI
        year: 年份
        month: 月份
    """
    st.success("✅ 查詢成功！")
    
    # 顯示查詢資訊
    st.subheader(f"📅 {year} 年 {month} 月費用明細")
    st.caption(f"IMEI: {imei}")
    
    # 主要費用指標
    col1, col2, col3 = st.columns(3)
    
    with col1:
        base_fee = result.get('base_fee', 0)
        st.metric(
            "月租費",
            f"${base_fee:.2f}",
            help="方案基本月租費"
        )
    
    with col2:
        overage = result.get('overage_cost', 0)
        st.metric(
            "超量費用",
            f"${overage:.2f}",
            delta=f"+${overage:.2f}" if overage > 0 else None,
            delta_color="inverse",
            help="超出方案額度的費用"
        )
    
    with col3:
        total = result.get('total_cost', 0)
        st.metric(
            "總費用",
            f"${total:.2f}",
            help="本月總計費用"
        )
    
    # 詳細資訊
    with st.expander("📋 詳細資訊"):
        st.json(result)

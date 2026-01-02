"""
通訊費用查詢頁面（v6.33.2）
自動整合 FTP 下載和費用計算 - 繁體中文版

功能：
1. 輸入 IMEI 和日期區間
2. 自動從 FTP 下載 CDR（如果本地沒有）
3. 自動解析和計算費用
4. 顯示費用明細
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
import calendar

from src.infrastructure.iws_gateway import IWSGateway
from src.services.billing_service import BillingService
from src.services.cdr_service import CDRService


def render_billing_query_page(gateway: IWSGateway):
    """
    渲染費用查詢頁面
    
    Args:
        gateway: IWS Gateway 實例
    """
    st.title("💰 通訊費用查詢")
    
    # 初始化服務
    cdr_service = CDRService()
    billing_service = BillingService(gateway, cdr_service)
    
    # 使用說明
    with st.expander("ℹ️ 使用說明", expanded=False):
        st.markdown("""
        **自動化費用查詢**：
        
        1. **輸入 IMEI**：設備的 IMEI 號碼
        2. **選擇日期**：單月查詢或日期區間
        3. **點選查詢**：系統自動下載 CDR 並計算費用
        
        **注意事項**：
        - 系統會自動從 FTP 下載所需的 CDR 檔案
        - 首次查詢可能需要較長時間（下載檔案）
        - 已下載的檔案會快取，再次查詢會更快
        - 支援單月查詢和日期區間查詢
        """)
    
    st.markdown("---")
    
    # ==================== 查詢條件 ====================
    
    st.subheader("🔍 查詢條件")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        imei = st.text_input(
            "IMEI",
            placeholder="請輸入 15 位 IMEI 號碼",
            max_chars=15,
            help="設備的唯一識別碼"
        )
    
    with col2:
        query_mode = st.selectbox(
            "查詢模式",
            options=["單月查詢", "日期區間"],
            help="選擇查詢方式"
        )
    
    # ==================== 日期選擇 ====================
    
    if query_mode == "單月查詢":
        col1, col2 = st.columns(2)
        
        with col1:
            year = st.number_input(
                "年份",
                min_value=2020,
                max_value=2030,
                value=datetime.now().year,
                step=1
            )
        
        with col2:
            month = st.number_input(
                "月份",
                min_value=1,
                max_value=12,
                value=datetime.now().month,
                step=1
            )
        
        query_date_str = f"{year}/{month:02d}"
        
    else:  # 日期區間
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "開始日期",
                value=date.today().replace(day=1)
            )
        
        with col2:
            end_date = st.date_input(
                "結束日期",
                value=date.today()
            )
        
        if start_date > end_date:
            st.error("❌ 開始日期不能晚於結束日期")
            return
        
        query_date_str = f"{start_date} ~ {end_date}"
    
    # ==================== FTP 設定檢查 ====================
    
    # 嘗試從 secrets 讀取 FTP 設定
    ftp_enabled = False
    ftp_config = None
    
    try:
        if all(key in st.secrets for key in ['FTP_HOST', 'FTP_USERNAME', 'FTP_PASSWORD']):
            ftp_config = {
                'host': st.secrets['FTP_HOST'],
                'username': st.secrets['FTP_USERNAME'],
                'password': st.secrets['FTP_PASSWORD'],
                'port': st.secrets.get('FTP_PORT', 21),
                'passive_mode': True
            }
            ftp_enabled = True
            st.success("✅ FTP 自動下載已啟用")
    except:
        st.warning("⚠️ FTP 未設定，請在 secrets.toml 中設定 FTP 資訊")
    
    # ==================== 查詢按鈕 ====================
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        query_button = st.button(
            "🔍 查詢費用",
            type="primary",
            use_container_width=True,
            disabled=not imei or len(imei) != 15
        )
    
    # ==================== 執行查詢 ====================
    
    if query_button:
        if not imei or len(imei) != 15:
            st.error("❌ 請輸入有效的 15 位 IMEI")
            return
        
        with st.spinner("🔍 查詢中..."):
            try:
                # 從 Google Drive 下載對應月份的資料
                from gdrive_download_helper import ensure_month_data_from_gdrive
                
                # 確保所需月份的資料存在
                if query_mode == "單月查詢":
                    st.info(f"📥 檢查 {year}/{month:02d} 的資料...")
                    success = ensure_month_data_from_gdrive(year, month, st.write)
                    
                    if not success:
                        st.error(
                            f"❌ 無法載入 {year}/{month:02d} 的 CDR 資料\n\n"
                            f"可能原因：\n"
                            f"1. 該月份尚未執行 CDR 同步\n"
                            f"2. Google Drive 設定錯誤\n\n"
                            f"請先到「CDR 同步管理」執行同步"
                        )
                        return
                else:
                    # 日期區間查詢
                    months_to_download = []
                    current = start_date.replace(day=1)
                    while current <= end_date:
                        months_to_download.append((current.year, current.month))
                        # 下一個月
                        if current.month == 12:
                            current = current.replace(year=current.year + 1, month=1)
                        else:
                            current = current.replace(month=current.month + 1)
                    
                    for y, m in months_to_download:
                        st.info(f"📥 檢查 {y}/{m:02d} 的資料...")
                        ensure_month_data_from_gdrive(y, m, st.write)
                
                # 查詢費用（billing_service 會自動從快取載入 CDR）
                if query_mode == "單月查詢":
                    result = billing_service.query_monthly_bill(
                        imei=imei,
                        year=year,
                        month=month,
                        cdr_records=None  # 讓 billing_service 自動載入
                    )
                    
                    if result:
                        render_monthly_bill(result, imei, query_date_str)
                
                else:
                    result = billing_service.query_date_range_bill(
                        imei=imei,
                        start_date=start_date,
                        end_date=end_date,
                        cdr_records=None  # 讓 billing_service 自動載入
                    )
                    
                    if result:
                        render_range_bill(result, imei, query_date_str)
                
            except Exception as e:
                st.error(f"❌ 查詢失敗: {str(e)}")
                with st.expander("🔍 詳細錯誤訊息"):
                    st.exception(e)


def render_monthly_bill(bill, imei: str, query_date: str):
    """渲染單月帳單"""
    st.success("✅ 查詢完成！")
    
    st.markdown("---")
    st.subheader("📊 費用摘要")
    
    # 費用摘要
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("總費用", f"${bill.total_cost:.2f}")
    
    with col2:
        st.metric("月租費", f"${bill.monthly_rate:.2f}")
    
    with col3:
        st.metric("超量費", f"${bill.overage_cost:.2f}")
    
    with col4:
        st.metric("其他費用", f"${bill.mailbox_check_cost + bill.registration_cost:.2f}")
    
    # 使用量明細
    st.markdown("---")
    st.subheader("📈 使用量明細")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **方案資訊**：
        - 方案：{bill.plan_name}
        - 帳號狀態：{bill.account_status}
        - 月租費：${bill.monthly_rate:.2f}
        - 包含流量：{bill.included_bytes:,} bytes
        """)
    
    with col2:
        st.markdown(f"""
        **使用統計**：
        - 總用量：{bill.total_usage_bytes:,} bytes
        - 超量：{bill.overage_bytes:,} bytes
        - 訊息數：{bill.message_count} 則
        - Mailbox Check：{bill.mailbox_check_count} 次
        - Registration：{bill.registration_count} 次
        """)
    
    # 通訊記錄
    if bill.records:
        st.markdown("---")
        st.subheader(f"📋 通訊記錄（共 {len(bill.records)} 筆）")
        
        # 轉換為 DataFrame
        records_data = []
        for record in bill.records:
            records_data.append({
                '時間': record.call_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                '服務': record.service_type,
                '訊息大小': f"{record.message_size} bytes",
                '方向': record.direction,
                '類型': record.message_type
            })
        
        df = pd.DataFrame(records_data)
        st.dataframe(df, use_container_width=True, height=400)
        
        # 下載 CSV
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下載明細 (CSV)",
            data=csv,
            file_name=f"費用明細_{imei}_{query_date.replace('/', '-')}.csv",
            mime="text/csv"
        )


def render_range_bill(result, imei: str, query_date: str):
    """渲染日期區間帳單"""
    st.success("✅ 查詢完成！")
    
    st.markdown("---")
    st.subheader("📊 費用摘要")
    
    # 總費用
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("總費用", f"${result['total_cost']:.2f}")
    
    with col2:
        st.metric("查詢月數", f"{len(result['monthly_bills'])} 個月")
    
    with col3:
        st.metric("總訊息數", f"{sum(b.message_count for b in result['monthly_bills'])} 則")
    
    # 各月明細
    st.markdown("---")
    st.subheader("📅 各月明細")
    
    for monthly_bill in result['monthly_bills']:
        with st.expander(f"📆 {monthly_bill.year}/{monthly_bill.month:02d} - ${monthly_bill.total_cost:.2f}"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("月租費", f"${monthly_bill.monthly_rate:.2f}")
            
            with col2:
                st.metric("超量費", f"${monthly_bill.overage_cost:.2f}")
            
            with col3:
                st.metric("使用量", f"{monthly_bill.total_usage_bytes:,} bytes")
            
            with col4:
                st.metric("訊息數", f"{monthly_bill.message_count} 則")

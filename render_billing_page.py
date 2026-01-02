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
from src.infrastructure.ftp_client import FTPClient
from src.infrastructure.gdrive_client import GoogleDriveClient, GDRIVE_AVAILABLE
from src.services.billing_service import BillingService
from src.services.cdr_service import CDRService
from src.services.incremental_sync import IncrementalSyncManager


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
                # 查詢費用
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
                error_msg = str(e)
                
                # 檢查是否是資料不存在的錯誤
                if "找不到" in error_msg or "不存在" in error_msg or "No data" in error_msg:
                    st.warning("⚠️ CDR 資料不存在，嘗試自動同步...")
                    
                    # 嘗試自動同步
                    sync_success = _auto_sync_cdr(year, month)
                    
                    if sync_success:
                        st.success("✅ 同步完成！重新查詢...")
                        st.rerun()
                    else:
                        st.error(f"❌ 自動同步失敗")
                        st.warning("""
                        **💡 無法自動同步**
                        
                        請檢查：
                        1. FTP 連線設定是否正確
                        2. Google Drive 設定是否正確
                        
                        **解決方法：**
                        - 請到「CDR 同步管理」頁面手動執行同步
                        - 或到「CDR 帳單查詢」頁面查詢（助理功能）
                        """)
                else:
                    st.error(f"❌ 查詢失敗: {error_msg}")
                
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


def _auto_sync_cdr(year: int, month: int) -> bool:
    """
    自動同步指定月份的 CDR 資料
    
    Args:
        year: 年份
        month: 月份
        
    Returns:
        是否成功
    """
    try:
        # 檢查設定
        if 'FTP_HOST' not in st.secrets or 'FTP_USERNAME' not in st.secrets or 'FTP_PASSWORD' not in st.secrets:
            st.error("❌ FTP 設定不完整")
            return False
        
        if not GDRIVE_AVAILABLE:
            st.error("❌ Google Drive 不可用")
            return False
        
        if 'gcp_service_account' not in st.secrets and 'GCP_SERVICE_ACCOUNT_JSON' not in st.secrets:
            st.error("❌ Google Drive 設定不完整")
            return False
        
        # 初始化客戶端
        with st.spinner(f"📡 連接 FTP 和 Google Drive..."):
            ftp_client = FTPClient(
                host=st.secrets['FTP_HOST'],
                username=st.secrets['FTP_USERNAME'],
                password=st.secrets['FTP_PASSWORD']
            )
            ftp_client.connect()
            
            # Google Drive 設定
            if 'gcp_service_account' in st.secrets:
                gdrive_config = {
                    'service_account_info': dict(st.secrets.gcp_service_account),
                    'root_folder_name': 'CDR_Files'
                }
            else:
                gdrive_config = {
                    'service_account_json': st.secrets['GCP_SERVICE_ACCOUNT_JSON'],
                    'root_folder_name': 'CDR_Files'
                }
            
            if 'GCP_CDR_FOLDER_ID' in st.secrets:
                gdrive_config['root_folder_id'] = st.secrets['GCP_CDR_FOLDER_ID']
            
            gdrive_client = GoogleDriveClient(**gdrive_config)
            
            # 執行同步
            sync_manager = IncrementalSyncManager(ftp_client, gdrive_client)
        
        with st.spinner(f"📥 同步 {year}/{month:02d} 的 CDR 檔案..."):
            # 使用簡單的進度回調
            messages = []
            def progress_callback(message, progress=None):
                messages.append(message)
                if len(messages) <= 3:
                    st.info(message)
            
            result = sync_manager.sync(progress_callback)
            
            if result['errors'] == 0:
                st.success(f"✅ 同步完成！處理了 {result['processed_files']} 個檔案")
                return True
            else:
                st.warning(f"⚠️ 同步完成但有 {result['errors']} 個錯誤")
                return False
    
    except Exception as e:
        st.error(f"❌ 自動同步失敗: {e}")
        return False
    finally:
        try:
            ftp_client.disconnect()
        except:
            pass

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
from datetime import date, datetime, timedelta
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
        imei_input = st.text_area(
            "IMEI",
            placeholder="請輸入 IMEI（支援多個，每行一個）\n例如：\n300534066711380\n300534066716260",
            height=100,
            help="支援單個或多個 IMEI，多個 IMEI 請換行輸入"
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
    
    # 解析 IMEI 列表
    imei_list = []
    if imei_input:
        imei_list = [line.strip() for line in imei_input.strip().split('\n') if line.strip()]
        # 驗證每個 IMEI
        invalid_imeis = [imei for imei in imei_list if len(imei) != 15]
        if invalid_imeis:
            st.error(f"❌ 以下 IMEI 不是 15 位：{', '.join(invalid_imeis)}")
            imei_list = []
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        query_button = st.button(
            "🔍 查詢費用",
            type="primary",
            use_container_width=True,
            disabled=len(imei_list) == 0
        )
    
    # ==================== 執行查詢 ====================
    
    if query_button:
        if len(imei_list) == 0:
            st.error("❌ 請輸入至少一個有效的 15 位 IMEI")
            return
        
        st.info(f"📋 查詢 {len(imei_list)} 個 IMEI")
        
        with st.spinner("🔍 查詢中..."):
            try:
                # 查詢每個 IMEI 的費用
                all_results = {}
                
                for idx, imei in enumerate(imei_list, 1):
                    st.write(f"### IMEI {idx}/{len(imei_list)}: {imei}")
                    
                    try:
                        # 查詢費用
                        if query_mode == "單月查詢":
                            # 單月查詢：載入整月的 CDR（但不超過今天）
                            st.info(f"📥 載入 {year}/{month:02d} 的 CDR...")
                            
                            month_start = date(year, month, 1)
                            if month == 12:
                                month_end = date(year + 1, 1, 1) - timedelta(days=1)
                            else:
                                month_end = date(year, month + 1, 1) - timedelta(days=1)
                            
                            # 不超過今天
                            today = date.today()
                            if month_end > today:
                                month_end = today
                            
                            cdr_records = _load_cdr_for_date_range(imei, month_start, month_end)
                            
                            if cdr_records is None:
                                st.warning(f"⚠️ IMEI {imei} 沒有找到記錄")
                                continue
                            
                            result = billing_service.query_monthly_bill(
                                imei=imei,
                                year=year,
                                month=month,
                                cdr_records=cdr_records
                            )
                            
                            if result:
                                all_results[imei] = result
                                render_monthly_bill(result, imei, query_date_str)
                        
                        else:
                            # 區間查詢：載入日期區間的 CDR
                            st.info(f"📥 載入 {start_date.strftime('%Y/%m/%d')} ~ {end_date.strftime('%Y/%m/%d')} 的 CDR...")
                            
                            cdr_records = _load_cdr_for_date_range(imei, start_date, end_date)
                            
                            if cdr_records is None:
                                st.warning(f"⚠️ IMEI {imei} 沒有找到記錄")
                                continue
                            
                            result = billing_service.query_date_range_bill(
                                imei=imei,
                                start_date=start_date,
                                end_date=end_date,
                                cdr_records=cdr_records
                            )
                            
                            if result:
                                all_results[imei] = result
                                render_range_bill(result, imei, query_date_str)
                    
                    except Exception as imei_error:
                        st.error(f"❌ IMEI {imei} 查詢失敗: {imei_error}")
                        with st.expander("🐛 詳細錯誤"):
                            st.exception(imei_error)
                
                # 顯示匯總
                if len(all_results) > 1:
                    st.markdown("---")
                    st.subheader("📊 匯總統計")
                    
                    total_cost = sum(
                        result.total_cost if hasattr(result, 'total_cost') 
                        else result.get('total_cost', 0)
                        for result in all_results.values()
                    )
                    
                    st.metric("總費用", f"${total_cost:.2f}")
                    
                    # 顯示各 IMEI 的費用
                    summary_data = []
                    for imei, result in all_results.items():
                        cost = result.total_cost if hasattr(result, 'total_cost') else result.get('total_cost', 0)
                        summary_data.append({
                            'IMEI': imei,
                            '費用': f"${cost:.2f}"
                        })
                    
                    df = pd.DataFrame(summary_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
            except Exception as e:
                st.error(f"❌ 查詢失敗: {e}")
                with st.expander("🔍 詳細錯誤訊息"):
                    st.exception(e)
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
        st.metric("其他費用", f"${bill.mailbox_cost + bill.registration_cost:.2f}")
    
    # 使用量明細
    st.markdown("---")
    st.subheader("📈 使用量明細")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **方案資訊**：
        - 方案：{bill.plan_name}
        - 月租費：${bill.monthly_rate:.2f}
        - 包含流量：{bill.included_bytes:,} bytes
        """)
    
    with col2:
        st.markdown(f"""
        **使用統計**：
        - 總用量：{bill.total_bytes:,} bytes
        - 計費用量：{bill.billable_bytes:,} bytes
        - 訊息數：{bill.message_count} 則
        - Mailbox Check：{bill.mailbox_checks} 次
        - Registration：{bill.registrations} 次
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


def _load_cdr_for_date_range(imei: str, start_date: date, end_date: date):
    """
    載入日期區間的 CDR 記錄
    
    Args:
        imei: IMEI
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        CDR 記錄列表
    """
    try:
        # 檢查 Google Drive 設定
        if 'gcp_service_account' not in st.secrets and 'GCP_SERVICE_ACCOUNT_JSON' not in st.secrets:
            st.error("❌ Google Drive 設定未完成")
            return None
        
        # 初始化 Google Drive
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
        
        gdrive = GoogleDriveClient(**gdrive_config)
        
        # 載入 CDR
        from src.parsers.tapii_parser import TAPIIParser
        from src.services.cdr_service import SimpleCDRRecord
        from datetime import timedelta
        import tempfile
        import os
        
        parser = TAPIIParser()
        all_records = []
        
        # 迭代每一天
        current_date = start_date
        days_processed = 0
        total_days = (end_date - start_date).days + 1
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while current_date <= end_date:
            try:
                status_text.text(f"📥 載入 {current_date.strftime('%Y/%m/%d')} 的 CDR...")
                
                # 嘗試從按日資料夾載入
                try:
                    folder_id = gdrive.get_day_folder_id(current_date)
                except:
                    # 如果按日資料夾不存在，嘗試按月
                    try:
                        folder_id = gdrive.get_month_folder_id(current_date)
                    except:
                        # 該月份沒有資料，跳過
                        current_date += timedelta(days=1)
                        days_processed += 1
                        progress_bar.progress(days_processed / total_days)
                        continue
                
                # 列出檔案
                files = gdrive.list_files(folder_id)
                cdr_files = [f for f in files if f['name'].endswith('.dat')]
                
                # 下載並解析
                for file_info in cdr_files:
                    # 下載到臨時檔案
                    temp_dir = tempfile.gettempdir()
                    local_path = os.path.join(temp_dir, file_info['name'])
                    
                    gdrive.download_file(file_info['id'], local_path)
                    
                    # 解析並過濾
                    records = parser.parse_file(local_path)
                    
                    for record in records:
                        if record.record_type == parser.TYPE_DATA:
                            # 提取 IMEI（位置 9-24，共 15 位）
                            record_imei = record.raw_data[9:24].decode('ascii', errors='ignore').strip()
                            
                            if record_imei == imei:
                                # 解析時間
                                if record.charging_date and record.charging_time:
                                    date_str = f"20{record.charging_date}"  # YYMMDD -> YYYYMMDD
                                    time_str = record.charging_time
                                    
                                    call_datetime = datetime.strptime(
                                        f"{date_str}{time_str}",
                                        "%Y%m%d%H%M%S"
                                    )
                                    
                                    # 檢查是否在日期範圍內
                                    if start_date <= call_datetime.date() <= end_date:
                                        # 提取資料量（bytes）
                                        data_volume_bytes = record.raw_data[135:145]
                                        try:
                                            data_bytes = int(data_volume_bytes.decode('ascii', errors='ignore').strip() or '0')
                                        except:
                                            data_bytes = 0
                                        
                                        # 轉換為 MB
                                        data_mb = data_bytes / (1024 * 1024)
                                        
                                        # 提取服務類型碼（位置 85-87）
                                        service_code = record.raw_data[85:87].decode('ascii', errors='ignore').strip()
                                        
                                        # 創建記錄
                                        cdr_record = SimpleCDRRecord(
                                            imei=record_imei,
                                            call_datetime=call_datetime,
                                            duration_seconds=0,  # TAP II 沒有通話時長
                                            data_mb=data_mb,
                                            call_type='SBD',  # 預設為 SBD
                                            service_code=service_code,
                                            destination='',
                                            cost=0.0,  # 稍後計算
                                            location_country='',
                                            cell_id='',
                                            msc_id=''
                                        )
                                        all_records.append(cdr_record)
                    
                    # 刪除臨時檔案
                    try:
                        os.remove(local_path)
                    except:
                        pass
            
            except Exception as day_error:
                # 該日載入失敗，記錄但繼續
                st.warning(f"⚠️ {current_date.strftime('%Y/%m/%d')} 載入失敗: {day_error}")
            
            current_date += timedelta(days=1)
            days_processed += 1
            progress_bar.progress(days_processed / total_days)
        
        progress_bar.empty()
        status_text.empty()
        
        if not all_records:
            st.warning(f"⚠️ 在日期區間內沒有找到 IMEI {imei} 的記錄")
            
            # 提示是否需要同步
            if st.button("🔄 嘗試從 FTP 同步最新資料"):
                # 同步涵蓋的月份
                months_to_sync = set()
                current = start_date
                while current <= end_date:
                    months_to_sync.add((current.year, current.month))
                    if current.month == 12:
                        current = date(current.year + 1, 1, 1)
                    else:
                        current = date(current.year, current.month + 1, 1)
                
                for year, month in sorted(months_to_sync):
                    if _auto_sync_cdr(year, month):
                        st.success(f"✅ {year}/{month:02d} 同步完成")
                
                st.info("💡 請重新執行查詢")
            
            return None
        
        st.success(f"✅ 載入了 {len(all_records)} 筆 CDR 記錄")
        return all_records
    
    except Exception as e:
        st.error(f"❌ 載入 CDR 失敗: {e}")
        with st.expander("🐛 詳細錯誤"):
            st.exception(e)
        return None

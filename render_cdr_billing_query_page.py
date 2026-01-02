"""
CDR 帳單查詢頁面
整合 Google Drive CDR 檔案與 IWS 計費查詢

功能：
1. 使用者輸入 IMEI、年份、月份
2. 從 Google Drive 下載對應月份的 CDR 檔案
3. 解析 TAP II 格式取得通訊記錄
4. 查詢 IWS 取得資費方案
5. 計算並顯示月帳單
"""
import streamlit as st
from datetime import date
from pathlib import Path
import tempfile
import os

from src.infrastructure.iws_gateway import IWSGateway
from src.infrastructure.gdrive_client import GoogleDriveClient, GDRIVE_AVAILABLE
from src.parsers.tapii_parser import TAPIIParser
from src.services.billing_service import BillingService, BillingServiceException
from src.services.cdr_service import CDRService, SimpleCDRRecord


def render_cdr_billing_query_page():
    """渲染 CDR 帳單查詢頁面"""
    
    st.title("📊 CDR 帳單查詢")
    st.markdown("---")
    
    # 檢查 Google Drive 是否可用
    if not GDRIVE_AVAILABLE:
        st.error("❌ Google Drive API 未安裝")
        st.code("pip install google-api-python-client google-auth")
        return
    
    # 取得 Google Drive 設定
    gdrive_config = _get_gdrive_config()
    if not gdrive_config:
        st.error("❌ Google Drive 未設定")
        st.info("請在 Secrets 中設定 `gcp_service_account` 或 `GCP_SERVICE_ACCOUNT_JSON`")
        return
    
    # ========== 查詢表單 ==========
    st.subheader("🔍 查詢條件")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        imei = st.text_input(
            "IMEI",
            placeholder="例如：301434061230580",
            help="請輸入 15 位數字的 IMEI"
        )
    
    with col2:
        year = st.number_input(
            "年份",
            min_value=2020,
            max_value=2030,
            value=date.today().year,
            step=1
        )
    
    with col3:
        month = st.number_input(
            "月份",
            min_value=1,
            max_value=12,
            value=date.today().month,
            step=1
        )
    
    # 驗證 IMEI
    if imei and (len(imei) != 15 or not imei.isdigit()):
        st.warning("⚠️ IMEI 必須是 15 位數字")
        return
    
    # ========== 查詢按鈕 ==========
    if st.button("🔎 查詢帳單", type="primary", disabled=not imei):
        with st.spinner("查詢中..."):
            try:
                # 1. 初始化 Google Drive 客戶端
                gdrive = GoogleDriveClient(**gdrive_config)
                
                # 2. 檢查是否需要從 FTP 下載
                st.info(f"🔍 檢查 {year}/{month:02d} 的 CDR 檔案...")
                
                # 檢查 Google Drive 是否有該月份的資料
                need_sync = _check_if_need_sync(gdrive, year, month)
                
                if need_sync:
                    st.warning(f"⚠️ Google Drive 中沒有 {year}/{month:02d} 的資料")
                    st.info(f"📥 正在從 FTP 下載最新的 CDR 檔案...")
                    
                    # 從 FTP 自動同步
                    sync_result = _auto_sync_from_ftp(gdrive, year, month)
                    
                    if sync_result['success']:
                        st.success(f"✅ 已下載並上傳 {sync_result['files_count']} 個檔案")
                    else:
                        st.error(f"❌ 自動同步失敗: {sync_result['error']}")
                        st.info("💡 請到「CDR 同步管理」頁面手動執行同步")
                        return
                
                # 3. 從 Google Drive 下載 CDR 檔案
                st.info(f"📥 正在從 Google Drive 讀取 {year}/{month:02d} 的 CDR 檔案...")
                
                cdr_records = _download_and_parse_cdr(
                    gdrive=gdrive,
                    imei=imei,
                    year=year,
                    month=month
                )
                
                if not cdr_records:
                    st.warning(f"⚠️ 在 {year}/{month:02d} 沒有找到 IMEI {imei} 的通訊記錄")
                    return
                
                st.success(f"✅ 找到 {len(cdr_records)} 筆通訊記錄")
                
                # 4. 統計 CDR 用量（不查詢 IWS）
                st.info("📊 統計用量中...")
                
                # 直接從 CDR 統計，不需要查詢 IWS
                usage_stats = _calculate_usage_from_cdr(cdr_records, year, month)
                
                # 5. 顯示統計結果
                _display_usage_stats(usage_stats, imei, year, month)
                
            except BillingServiceException as e:
                st.error(f"❌ 查詢失敗: {e}")
            except Exception as e:
                st.error(f"❌ 系統錯誤: {e}")
                with st.expander("🐛 詳細錯誤資訊"):
                    st.exception(e)


def _check_if_need_sync(gdrive: GoogleDriveClient, year: int, month: int) -> bool:
    """
    檢查是否需要從 FTP 同步
    
    Args:
        gdrive: Google Drive 客戶端
        year: 年份
        month: 月份
        
    Returns:
        True: 需要同步（資料夾不存在或為空）
        False: 不需要同步（已有資料）
    """
    try:
        folder_date = date(year, month, 1)
        folder_id = gdrive.get_month_folder_id(folder_date)
        
        # 檢查資料夾是否有檔案
        files = gdrive.list_files(folder_id)
        cdr_files = [f for f in files if f['name'].endswith('.dat')]
        
        return len(cdr_files) == 0
        
    except Exception:
        # 資料夾不存在
        return True


def _auto_sync_from_ftp(gdrive: GoogleDriveClient, year: int, month: int) -> dict:
    """
    自動從 FTP 下載並同步指定月份的 CDR 檔案
    
    Args:
        gdrive: Google Drive 客戶端
        year: 年份
        month: 月份
        
    Returns:
        同步結果
    """
    from src.infrastructure.ftp_client import FTPClient
    from src.parsers.tapii_parser import TAPIIParser
    
    try:
        # 1. 初始化 FTP 客戶端
        ftp = FTPClient(
            host=st.secrets['FTP_HOST'],
            username=st.secrets['FTP_USERNAME'],
            password=st.secrets['FTP_PASSWORD'],
            passive_mode=True
        )
        
        # 2. 連接 FTP
        ftp.connect()
        
        # 3. 列出所有 CDR 檔案
        all_files = ftp.list_files()
        
        if not all_files:
            return {
                'success': False,
                'error': 'FTP 上沒有檔案',
                'files_count': 0
            }
        
        # 4. 使用臨時目錄處理
        with tempfile.TemporaryDirectory() as temp_dir:
            parser = TAPIIParser()
            uploaded_count = 0
            target_month_str = f"{year}{month:02d}"
            
            # 處理每個檔案
            for filename, mod_time, size in all_files:
                try:
                    # 下載檔案
                    local_path = os.path.join(temp_dir, filename)
                    ftp.download_file(filename, local_path)
                    
                    # 解析檔案取得月份
                    months = parser.extract_months(local_path)
                    
                    # 檢查是否包含目標月份
                    if target_month_str in months:
                        # 上傳到 Google Drive
                        upload_result = gdrive.upload_to_month_folder(
                            local_path=local_path,
                            year=year,
                            month=month
                        )
                        
                        if upload_result:
                            uploaded_count += 1
                    
                except Exception as e:
                    # 跳過有問題的檔案
                    continue
        
        # 5. 斷開 FTP
        ftp.disconnect()
        
        return {
            'success': True,
            'files_count': uploaded_count,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'files_count': 0
        }


def _download_and_parse_cdr(gdrive: GoogleDriveClient,
                            imei: str,
                            year: int,
                            month: int) -> list[SimpleCDRRecord]:
    """
    從 Google Drive 下載並解析 CDR 檔案
    
    Args:
        gdrive: Google Drive 客戶端
        imei: 設備 IMEI
        year: 年份
        month: 月份
        
    Returns:
        該 IMEI 的通訊記錄列表
    """
    # 1. 取得月份資料夾
    folder_date = date(year, month, 1)
    
    try:
        folder_id = gdrive.get_month_folder_id(folder_date)
    except Exception as e:
        st.warning(f"⚠️ 月份資料夾不存在: {year}/{month:02d}")
        return []
    
    # 2. 列出資料夾中的所有 .dat 檔案
    files = gdrive.list_files(folder_id)
    cdr_files = [f for f in files if f['name'].endswith('.dat')]
    
    if not cdr_files:
        st.warning(f"⚠️ {year}/{month:02d} 資料夾中沒有 CDR 檔案")
        return []
    
    st.info(f"📄 找到 {len(cdr_files)} 個 CDR 檔案，開始解析...")
    
    # 3. 下載並解析所有檔案
    all_records = []
    parser = TAPIIParser()
    cdr_service = CDRService()
    
    # 使用臨時目錄
    with tempfile.TemporaryDirectory() as temp_dir:
        progress_bar = st.progress(0)
        
        for i, file_info in enumerate(cdr_files):
            # 更新進度
            progress = (i + 1) / len(cdr_files)
            progress_bar.progress(progress, text=f"處理中: {file_info['name']}")
            
            # 下載檔案
            local_path = os.path.join(temp_dir, file_info['name'])
            
            try:
                # 從 Google Drive 下載
                content = gdrive.download_file_content_by_id(file_info['id'])
                
                with open(local_path, 'wb') as f:
                    f.write(content)
                
                # 解析記錄
                records = parser.parse_file(local_path)
                
                # 過濾出該 IMEI 的記錄（Type 20）
                for record in records:
                    if record.record_type == parser.TYPE_DATA:
                        # 從原始資料提取 IMEI（假設在特定位置）
                        # 根據 TAP II 格式，IMEI 在 Byte 10-24 或 25-40
                        raw_data = record.raw_data
                        
                        # 嘗試提取 IMEI（可能需要根據實際格式調整）
                        record_imei = _extract_imei_from_record(raw_data)
                        
                        if record_imei == imei:
                            # 轉換為 SimpleCDRRecord
                            cdr_record = _convert_to_simple_cdr(record, file_info['name'])
                            all_records.append(cdr_record)
                
            except Exception as e:
                st.warning(f"⚠️ 無法處理檔案 {file_info['name']}: {e}")
                continue
        
        progress_bar.empty()
    
    return all_records


def _extract_imei_from_record(raw_data: bytes) -> str:
    """
    從 TAP II 記錄中提取 IMEI
    
    Args:
        raw_data: 原始記錄資料（160 字元）
        
    Returns:
        IMEI 字串
    """
    try:
        # 根據 TAP II v9.2 文件：
        # - IMSI: Byte 10-24 (15 chars)
        # - IMEI: Byte 25-40 (16 chars)
        
        # 嘗試從 IMSI 位置讀取（SBD 使用 IMEI 作為 IMSI）
        imsi_imei = raw_data[9:24].decode('ascii', errors='ignore').strip()
        if imsi_imei and imsi_imei.isdigit() and len(imsi_imei) == 15:
            return imsi_imei
        
        # 嘗試從 IMEI 位置讀取
        imei = raw_data[24:40].decode('ascii', errors='ignore').strip()
        if imei and imei.isdigit():
            # 移除前綴 '30'（Iridium Satellite）
            if imei.startswith('30') and len(imei) >= 15:
                return imei[:15]
            return imei[:15] if len(imei) >= 15 else imei
        
        return ""
        
    except Exception:
        return ""


def _convert_to_simple_cdr(tapii_record, filename: str) -> SimpleCDRRecord:
    """
    將 TAP II 記錄轉換為 SimpleCDRRecord
    
    Args:
        tapii_record: TAP II 記錄
        filename: 檔案名稱
        
    Returns:
        SimpleCDRRecord
    """
    # 解析日期時間
    try:
        if tapii_record.charging_date and tapii_record.charging_time:
            # YYMMDD HHMMSS
            yy = tapii_record.charging_date[0:2]
            mm = tapii_record.charging_date[2:4]
            dd = tapii_record.charging_date[4:6]
            
            hh = tapii_record.charging_time[0:2]
            mi = tapii_record.charging_time[2:4]
            ss = tapii_record.charging_time[4:6]
            
            # 假設 YY >= 20 是 20XX
            yyyy = '20' + yy if int(yy) >= 20 else '19' + yy
            
            timestamp = f"{yyyy}-{mm}-{dd} {hh}:{mi}:{ss}"
        else:
            timestamp = ""
    except:
        timestamp = ""
    
    # 從原始資料提取其他欄位
    raw_data = tapii_record.raw_data
    
    # Data Volume Reference (Byte 134-139)
    try:
        data_volume = int(raw_data[133:139].decode('ascii', errors='ignore').strip() or 0)
    except:
        data_volume = 0
    
    return SimpleCDRRecord(
        timestamp=timestamp,
        imei="",  # 已經過濾，不需要重複
        data_volume=data_volume,
        service_type="SBD",  # 可以從 Service Code 判斷
        raw_record=filename
    )


def _display_bill(bill, imei: str, year: int, month: int):
    """
    顯示月帳單
    
    Args:
        bill: MonthlyBill 物件
        imei: IMEI
        year: 年份
        month: 月份
    """
    st.markdown("---")
    st.subheader("📄 月帳單明細")
    
    # 基本資訊
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("IMEI", imei)
    
    with col2:
        st.metric("查詢月份", f"{year}/{month:02d}")
    
    with col3:
        st.metric("資費方案", bill.plan_name)
    
    with col4:
        st.metric("通訊筆數", f"{bill.total_records} 筆")
    
    # 費用明細
    st.markdown("### 💰 費用明細")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "月租費",
            f"${bill.monthly_fee:.2f}",
            help="包含在方案內的固定月費"
        )
        
        st.metric(
            "超量費用",
            f"${bill.overage_charge:.2f}",
            help="超過方案流量的費用"
        )
    
    with col2:
        st.metric(
            "其他費用",
            f"${bill.other_charges:.2f}",
            help="Mailbox Check、Registration 等費用"
        )
        
        st.metric(
            "總金額",
            f"${bill.total_amount:.2f}",
            delta=f"${bill.total_amount - bill.monthly_fee:.2f}",
            help="本月總費用"
        )
    
    # 用量統計
    st.markdown("### 📊 用量統計")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "總上傳流量",
            f"{bill.total_mo_bytes:,} bytes",
            help="Mobile Originated (上行)"
        )
    
    with col2:
        st.metric(
            "總下載流量",
            f"{bill.total_mt_bytes:,} bytes",
            help="Mobile Terminated (下行)"
        )
    
    with col3:
        usage_percentage = (bill.total_mo_bytes / bill.plan_included_bytes * 100) if bill.plan_included_bytes > 0 else 0
        st.metric(
            "方案使用率",
            f"{usage_percentage:.1f}%",
            help=f"已用 / 方案內含 {bill.plan_included_bytes:,} bytes"
        )
    
    # 明細記錄
    if st.checkbox("📋 顯示詳細通訊記錄"):
        st.markdown("### 通訊記錄")
        
        if hasattr(bill, 'records') and bill.records:
            import pandas as pd
            
            # 轉換為 DataFrame
            records_data = []
            for record in bill.records:
                records_data.append({
                    '時間': record.timestamp,
                    '流量 (bytes)': record.data_volume,
                    '服務類型': record.service_type,
                    '來源檔案': record.raw_record
                })
            
            df = pd.DataFrame(records_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("無詳細記錄資訊")


def _get_gdrive_config() -> dict:
    """取得 Google Drive 設定"""
    if not GDRIVE_AVAILABLE:
        return None
    
    try:
        # 優先使用新格式 (TOML section)
        if 'gcp_service_account' in st.secrets:
            config = {
                'service_account_info': dict(st.secrets.gcp_service_account),
                'root_folder_name': 'CDR_Files'
            }
            # 如果有提供 folder ID，直接使用
            if 'GCP_CDR_FOLDER_ID' in st.secrets:
                config['root_folder_id'] = st.secrets['GCP_CDR_FOLDER_ID']
            return config
        # 向後兼容舊格式 (JSON 字串)
        elif 'GCP_SERVICE_ACCOUNT_JSON' in st.secrets:
            config = {
                'service_account_json': st.secrets['GCP_SERVICE_ACCOUNT_JSON'],
                'root_folder_name': 'CDR_Files'
            }
            if 'GCP_CDR_FOLDER_ID' in st.secrets:
                config['root_folder_id'] = st.secrets['GCP_CDR_FOLDER_ID']
            return config
        else:
            return None
    except Exception as e:
        st.error(f"❌ 讀取 Google Drive 設定失敗: {e}")
        return None


def _calculate_usage_from_cdr(cdr_records: list, year: int, month: int) -> dict:
    """
    從 CDR 記錄統計用量（不查詢 IWS）
    
    Args:
        cdr_records: CDR 記錄列表
        year: 年份
        month: 月份
        
    Returns:
        用量統計
    """
    # 統計各類用量
    mo_count = 0  # MO (Mobile Originated) - 發送
    mt_count = 0  # MT (Mobile Terminated) - 接收
    total_bytes = 0
    
    # 服務類型統計
    service_stats = {}
    
    for record in cdr_records:
        # 統計訊息數
        if hasattr(record, 'direction'):
            if record.direction == 'MO':
                mo_count += 1
            elif record.direction == 'MT':
                mt_count += 1
        
        # 統計流量
        if hasattr(record, 'data_volume'):
            total_bytes += record.data_volume
        elif hasattr(record, 'message_size'):
            total_bytes += record.message_size
        
        # 統計服務類型
        if hasattr(record, 'service_type'):
            service_type = record.service_type
            if service_type not in service_stats:
                service_stats[service_type] = 0
            service_stats[service_type] += 1
    
    return {
        'year': year,
        'month': month,
        'total_records': len(cdr_records),
        'mo_count': mo_count,
        'mt_count': mt_count,
        'total_bytes': total_bytes,
        'service_stats': service_stats,
        'records': cdr_records
    }


def _display_usage_stats(stats: dict, imei: str, year: int, month: int):
    """
    顯示用量統計
    
    Args:
        stats: 用量統計
        imei: IMEI
        year: 年份
        month: 月份
    """
    st.success("✅ 統計完成！")
    
    st.markdown("---")
    st.subheader(f"📊 {imei} - {year}/{month:02d} 用量統計")
    
    # 總覽
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("總記錄數", f"{stats['total_records']:,}")
    
    with col2:
        st.metric("發送 (MO)", f"{stats['mo_count']:,}")
    
    with col3:
        st.metric("接收 (MT)", f"{stats['mt_count']:,}")
    
    with col4:
        st.metric("總流量", f"{stats['total_bytes']:,} bytes")
    
    # 服務類型統計
    if stats['service_stats']:
        st.markdown("---")
        st.subheader("📈 服務類型統計")
        
        import pandas as pd
        service_df = pd.DataFrame([
            {'服務類型': k, '次數': v}
            for k, v in sorted(stats['service_stats'].items(), key=lambda x: x[1], reverse=True)
        ])
        st.dataframe(service_df, use_container_width=True, hide_index=True)
    
    # 通訊記錄
    if stats['records']:
        st.markdown("---")
        st.subheader(f"📋 通訊記錄（共 {len(stats['records'])} 筆）")
        
        # 轉換為 DataFrame
        records_data = []
        for record in stats['records']:
            record_dict = {
                '時間': getattr(record, 'timestamp', getattr(record, 'call_start_time', 'N/A')),
                '方向': getattr(record, 'direction', 'N/A'),
                '服務類型': getattr(record, 'service_type', 'N/A'),
            }
            
            # 流量
            if hasattr(record, 'data_volume'):
                record_dict['流量 (bytes)'] = record.data_volume
            elif hasattr(record, 'message_size'):
                record_dict['流量 (bytes)'] = record.message_size
            else:
                record_dict['流量 (bytes)'] = 0
            
            records_data.append(record_dict)
        
        import pandas as pd
        df = pd.DataFrame(records_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 下載按鈕
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下載 CSV",
            data=csv,
            file_name=f"CDR_{imei}_{year}{month:02d}.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    # 用於測試
    render_cdr_billing_query_page()

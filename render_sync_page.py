"""
CDR 同步管理頁面
管理 FTP 到 Google Drive 的增量同步
"""
import streamlit as st
from datetime import datetime

from src.infrastructure.ftp_client import FTPClient
from src.infrastructure.gdrive_client import GoogleDriveClient, GDRIVE_AVAILABLE
from src.services.incremental_sync import IncrementalSyncManager


def render_sync_management_page():
    """渲染 CDR 同步管理頁面"""
    
    st.title("🔄 CDR 同步管理")
    
    # 檢查設定
    ftp_config = _get_ftp_config()
    gdrive_config = _get_gdrive_config()
    
    if not ftp_config:
        st.error("❌ 未設定 FTP 連線資訊，請在 Secrets 中設定")
        st.info("需要設定: FTP_HOST, FTP_USERNAME, FTP_PASSWORD")
        return
    
    if not gdrive_config:
        st.warning("⚠️ 未設定 Google Drive，同步狀態將保存在本地")
    
    # 初始化同步管理器
    sync_manager = _get_sync_manager(ftp_config, gdrive_config)
    
    if not sync_manager:
        st.error("❌ 無法初始化同步管理器")
        return
    
    # 顯示同步狀態
    _render_sync_status(sync_manager)
    
    st.divider()
    
    # 同步操作
    _render_sync_actions(sync_manager)


def _get_ftp_config() -> dict:
    """取得 FTP 設定"""
    try:
        return {
            'host': st.secrets['FTP_HOST'],
            'username': st.secrets['FTP_USERNAME'],
            'password': st.secrets['FTP_PASSWORD'],
            'port': st.secrets.get('FTP_PORT', 21),
            'passive_mode': st.secrets.get('FTP_PASSIVE_MODE', True)
        }
    except:
        return None


def _get_gdrive_config() -> dict:
    """取得 Google Drive 設定"""
    if not GDRIVE_AVAILABLE:
        st.warning("⚠️ Google Drive 套件未安裝")
        return None
    
    try:
        # 優先使用新格式 (TOML section)
        if 'gcp_service_account' in st.secrets:
            st.info("✅ 找到 gcp_service_account 設定")
            config = {
                'service_account_info': dict(st.secrets.gcp_service_account),
                'root_folder_name': 'CDR_Files'
            }
            # 如果有提供 folder ID，直接使用
            if 'GCP_CDR_FOLDER_ID' in st.secrets:
                config['root_folder_id'] = st.secrets['GCP_CDR_FOLDER_ID']
                st.info(f"✅ 使用指定的資料夾 ID: {st.secrets['GCP_CDR_FOLDER_ID']}")
            # 如果有提供 owner email，自動共享新建立的資料夾
            if 'OWNER_EMAIL' in st.secrets:
                config['owner_email'] = st.secrets['OWNER_EMAIL']
                st.info(f"✅ 新建立的資料夾將自動共享給: {st.secrets['OWNER_EMAIL']}")
            return config
        # 向後兼容舊格式 (JSON 字串)
        elif 'GCP_SERVICE_ACCOUNT_JSON' in st.secrets:
            st.info("✅ 找到 GCP_SERVICE_ACCOUNT_JSON 設定（舊格式）")
            config = {
                'service_account_json': st.secrets['GCP_SERVICE_ACCOUNT_JSON'],
                'root_folder_name': 'CDR_Files'
            }
            if 'GCP_CDR_FOLDER_ID' in st.secrets:
                config['root_folder_id'] = st.secrets['GCP_CDR_FOLDER_ID']
            if 'OWNER_EMAIL' in st.secrets:
                config['owner_email'] = st.secrets['OWNER_EMAIL']
            return config
        else:
            st.error("❌ Secrets 中找不到 gcp_service_account 或 GCP_SERVICE_ACCOUNT_JSON")
    except Exception as e:
        st.error(f"❌ 讀取 Google Drive 設定失敗: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    return None


def _get_sync_manager(ftp_config: dict, gdrive_config: dict) -> IncrementalSyncManager:
    """取得同步管理器（使用快取）"""
    if 'sync_manager' not in st.session_state:
        try:
            # 初始化 FTP 客戶端
            ftp_client = FTPClient(**ftp_config)
            
            # 初始化 Google Drive 客戶端
            gdrive_client = None
            if gdrive_config:
                try:
                    st.info(f"🔧 正在初始化 Google Drive 客戶端...")
                    st.write(f"配置參數: {list(gdrive_config.keys())}")
                    
                    gdrive_client = GoogleDriveClient(**gdrive_config)
                    st.success("✅ Google Drive 客戶端初始化成功")
                    
                except Exception as e:
                    st.error(f"❌ Google Drive 初始化失敗: {e}")
                    import traceback
                    st.code(traceback.format_exc())
                    st.warning("⚠️ 將繼續同步但不會上傳到 Google Drive")
            
            # 建立同步管理器
            st.session_state.sync_manager = IncrementalSyncManager(
                ftp_client,
                gdrive_client
            )
        except Exception as e:
            st.error(f"❌ 初始化同步管理器失敗: {e}")
            return None
    
    return st.session_state.sync_manager


def _render_sync_status(sync_manager: IncrementalSyncManager):
    """渲染同步狀態"""
    st.subheader("📊 同步狀態")
    
    try:
        status = sync_manager.get_status()
        
        # 基本資訊
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if status['initial_sync_completed']:
                st.metric("初始同步", "✅ 已完成")
            else:
                st.metric("初始同步", "⏳ 未完成")
        
        with col2:
            st.metric("已處理檔案", f"{status['total_files_processed']:,}")
        
        with col3:
            if status['error_count'] > 0:
                st.metric("錯誤數", status['error_count'], delta_color="inverse")
            else:
                st.metric("錯誤數", "0")
        
        # 最後同步時間
        if status['last_sync_time']:
            last_sync = datetime.fromisoformat(status['last_sync_time'])
            st.info(f"🕐 最後同步: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.info("🕐 尚未執行同步")
        
        # 月份統計
        if status['monthly_stats']:
            st.subheader("📂 月份統計")
            
            monthly_data = []
            for month, stats in sorted(status['monthly_stats'].items(), reverse=True):
                monthly_data.append({
                    '月份': month,
                    '檔案數': stats['file_count'],
                    '記錄數': stats['total_records'],
                    '最後更新': stats['last_updated'][:19] if stats['last_updated'] else ''
                })
            
            st.dataframe(monthly_data, use_container_width=True, hide_index=True)
    
    except Exception as e:
        st.error(f"❌ 無法載入同步狀態: {e}")


def _render_sync_actions(sync_manager: IncrementalSyncManager):
    """渲染同步操作"""
    st.subheader("⚙️ 同步操作")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 檢查新檔案並同步", use_container_width=True, type="primary"):
            _run_sync(sync_manager)
    
    with col2:
        if st.button("⚙️ 重新同步全部", use_container_width=True):
            _run_full_resync(sync_manager)


def _run_sync(sync_manager: IncrementalSyncManager):
    """執行增量同步"""
    st.subheader("📥 執行同步")
    
    # 進度容器
    progress_bar = st.progress(0)
    
    # 訊息顯示容器（使用 empty 確保不會被覆蓋）
    message_placeholder = st.empty()
    messages = []
    
    def progress_callback(message, progress=None):
        """進度回調"""
        # 添加訊息到列表
        messages.append(message)
        
        # 更新顯示（使用 code block 保持格式）
        message_placeholder.code("\n".join(messages), language="")
        
        # 更新進度條
        if progress is not None:
            progress_bar.progress(progress)
    
    try:
        # 執行同步
        result = sync_manager.sync(progress_callback)
        
        # 完成
        progress_bar.progress(1.0)
        
        # 顯示結果
        if result['status'] == 'up_to_date':
            st.success(f"✅ 所有檔案已是最新！共 {result['total_files']} 個檔案")
        else:
            st.success(
                f"✅ 同步完成！\n"
                f"- FTP 總檔案: {result['total_files']}\n"
                f"- 新處理檔案: {result['processed_files']}\n"
                f"- 錯誤: {result['errors']}"
            )
            
            # 顯示檔案上傳統計
            if result.get('uploaded_files'):
                st.info(f"📤 已上傳 {result['uploaded_files']} 個檔案到 Google Drive")
        
        # 提示用戶可以重新整理查看最新狀態
        st.info("💡 同步完成！重新整理頁面可查看最新狀態")
        
        # 清除快取
        if 'sync_manager' in st.session_state:
            del st.session_state.sync_manager
        
    except Exception as e:
        st.error(f"❌ 同步失敗: {e}")
        st.exception(e)


def _run_full_resync(sync_manager: IncrementalSyncManager):
    """執行完整重新同步（危險操作）"""
    st.warning("⚠️ 這將重置同步狀態，重新處理所有檔案！")
    
    if st.button("⚠️ 確認重新同步", type="secondary"):
        try:
            # 重置狀態
            sync_manager.reset_status()
            
            st.success("✅ 同步狀態已重置")
            st.info("點選「檢查新檔案並同步」開始重新同步")
            
            # 清除快取
            if 'sync_manager' in st.session_state:
                del st.session_state.sync_manager
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ 重置失敗: {e}")

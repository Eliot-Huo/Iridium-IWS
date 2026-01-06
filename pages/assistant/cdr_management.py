"""
CDR 檔案管理界面
提供 CDR 自動下載、上傳和管理的 UI

功能：
1. 手動觸發同步
2. 查看檔案清單
3. 監控同步狀態
4. 清理舊檔案
"""
import streamlit as st
from datetime import date, datetime, timedelta
from typing import Optional
import logging

# 延遲導入，避免循環依賴
def get_services():
    """延遲導入服務，避免啟動時的循環依賴"""
    try:
        from src.infrastructure.ftp_client import FTPClient
        from src.infrastructure.gdrive_client import GoogleDriveClient, GDRIVE_AVAILABLE
        from src.services.cdr_sync_service import CDRSyncService
        return FTPClient, GoogleDriveClient, GDRIVE_AVAILABLE, CDRSyncService
    except ImportError as e:
        st.error(f"❌ 無法載入 CDR 服務: {e}")
        return None, None, False, None


def render_cdr_management_page(ftp_config: dict, gdrive_config: Optional[dict] = None):
    """
    渲染 CDR 檔案管理頁面
    
    Args:
        ftp_config: FTP 設定 {host, username, password, port}
        gdrive_config: Google Drive 設定 {service_account_file}
    """
    st.title("📁 CDR 檔案管理")
    
    # 延遲導入服務
    services = get_services()
    if not all(services):
        st.error("❌ CDR 服務載入失敗，請檢查系統設定")
        return
    
    FTPClient, GoogleDriveClient, GDRIVE_AVAILABLE, CDRSyncService = services
    
    # 初始化服務
    try:
        ftp_client = FTPClient(**ftp_config)
        
        gdrive_client = None
        if gdrive_config and GDRIVE_AVAILABLE:
            try:
                gdrive_client = GoogleDriveClient(**gdrive_config)
            except Exception as e:
                st.warning(f"⚠️ Google Drive 未啟用: {e}")
        
        sync_service = CDRSyncService(
            ftp_client=ftp_client,
            gdrive_client=gdrive_client
        )
        
    except Exception as e:
        st.error(f"❌ 初始化失敗: {e}")
        return
    
    # 使用說明
    with st.expander("ℹ️ 使用說明", expanded=False):
        st.markdown("""
        **CDR 檔案自動管理**：
        
        1. **自動同步**: 點擊「同步最新檔案」下載最近的 CDR 檔案
        2. **日期範圍**: 選擇特定日期範圍進行同步
        3. **檔案清單**: 查看已下載的本地檔案
        4. **清理舊檔案**: 刪除超過 6 個月的檔案
        5. **Google Drive**: 自動備份到 Google Drive（如果已設定）
        
        **注意事項**：
        - CDR 檔案會先下載到本地快取
        - 如果啟用 Google Drive，會自動上傳備份
        - 系統會自動保留最近 6 個月的檔案
        """)
    
    st.markdown("---")
    
    # ==================== 同步控制 ====================
    
    st.subheader("🔄 同步 CDR 檔案")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**快速同步**")
        
        hours = st.selectbox(
            "同步最近",
            options=[24, 48, 72, 168],  # 1天、2天、3天、1週
            format_func=lambda x: f"{x} 小時" if x < 168 else "1 週",
            help="下載最近 N 小時的 CDR 檔案"
        )
        
        sync_button = st.button(
            "🔄 同步最新檔案",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        st.markdown("**日期範圍同步**")
        
        col2a, col2b = st.columns(2)
        
        with col2a:
            start_date = st.date_input(
                "開始日期",
                value=date.today() - timedelta(days=7)
            )
        
        with col2b:
            end_date = st.date_input(
                "結束日期",
                value=date.today()
            )
        
        range_sync_button = st.button(
            "📅 同步日期範圍",
            use_container_width=True
        )
    
    # ==================== 執行同步 ====================
    
    if sync_button:
        with st.spinner(f"⏳ 正在同步最近 {hours} 小時的檔案..."):
            try:
                result = sync_service.sync_latest(hours)
                
                st.success("✅ 同步完成！")
                
                # 顯示結果
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("總檔案", result['total_files'])
                
                with col2:
                    st.metric("已下載", result['downloaded'])
                
                with col3:
                    st.metric("已上傳", result['uploaded'])
                
                with col4:
                    st.metric("跳過", result['download_skipped'])
                
                # 顯示檔案列表
                if result['files']:
                    with st.expander("📋 檔案明細"):
                        for file in result['files']:
                            status_icon = "✅" if file['downloaded'] else "⏭️"
                            upload_icon = "☁️" if file.get('uploaded') else ""
                            st.text(f"{status_icon} {upload_icon} {file['filename']} ({file['date']})")
                
            except Exception as e:
                st.error(f"❌ 同步失敗: {e}")
    
    if range_sync_button:
        if start_date > end_date:
            st.error("❌ 開始日期不能晚於結束日期")
        else:
            days = (end_date - start_date).days + 1
            
            with st.spinner(f"⏳ 正在同步 {days} 天的檔案..."):
                try:
                    result = sync_service.sync_date_range(start_date, end_date)
                    
                    st.success("✅ 同步完成！")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("總檔案", result['total_files'])
                    
                    with col2:
                        st.metric("已下載", result['downloaded'])
                    
                    with col3:
                        st.metric("已上傳", result['uploaded'])
                
                except Exception as e:
                    st.error(f"❌ 同步失敗: {e}")
    
    # ==================== 同步狀態 ====================
    
    st.markdown("---")
    st.subheader("📊 同步狀態")
    
    try:
        status = sync_service.get_sync_status()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**本地快取**")
            
            local = status['local']
            
            if local['total_files'] > 0:
                st.metric("檔案數量", local['total_files'])
                st.metric("總大小", f"{local['total_size_mb']} MB")
                st.metric("日期範圍", f"{local['date_range_days']} 天")
                
                st.caption(f"📅 {local['oldest_date']} ~ {local['newest_date']}")
                
                # 按月份統計
                if local.get('by_month'):
                    with st.expander("📅 按月份統計"):
                        for month, count in local['by_month'].items():
                            st.text(f"{month}: {count} 檔案")
            else:
                st.info("ℹ️ 尚無本地檔案")
        
        with col2:
            st.markdown("**Google Drive**")
            
            if status['gdrive_enabled']:
                gdrive = status.get('gdrive', {})
                
                if gdrive:
                    st.metric("已使用", f"{gdrive['used_mb']} MB")
                    
                    if gdrive.get('limit_mb'):
                        st.metric("總容量", f"{gdrive['limit_mb']} MB")
                        st.metric("使用率", f"{gdrive['used_percent']}%")
                    
                    st.success("✅ Google Drive 已啟用")
                else:
                    st.warning("⚠️ 無法取得 Google Drive 狀態")
            else:
                st.info("ℹ️ Google Drive 未啟用")
                st.caption("只使用本地快取")
    
    except Exception as e:
        st.error(f"❌ 無法取得狀態: {e}")
    
    # ==================== 檔案清理 ====================
    
    st.markdown("---")
    st.subheader("🗑️ 清理舊檔案")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info(f"💡 系統會自動保留最近 {status.get('retention_months', 6)} 個月的檔案")
        
        keep_months = st.slider(
            "保留月數",
            min_value=1,
            max_value=12,
            value=status.get('retention_months', 6),
            help="保留最近 N 個月的檔案，刪除更舊的"
        )
        
        cutoff = date.today() - timedelta(days=keep_months * 30)
        st.caption(f"將刪除 {cutoff} 之前的檔案")
    
    with col2:
        st.markdown("**操作**")
        
        preview_button = st.button(
            "👁️ 預覽清理",
            use_container_width=True
        )
        
        cleanup_button = st.button(
            "🗑️ 執行清理",
            type="secondary",
            use_container_width=True
        )
    
    # 預覽清理
    if preview_button:
        with st.spinner("⏳ 正在分析..."):
            try:
                result = sync_service.cleanup_old_files(
                    keep_months=keep_months,
                    dry_run=True
                )
                
                st.info(f"📋 預覽結果")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("本地將刪除", result['local_to_delete'])
                
                with col2:
                    if 'gdrive_to_delete' in result:
                        st.metric("GDrive 將刪除", result['gdrive_to_delete'])
                
                if result['local_to_delete'] == 0:
                    st.success("✅ 沒有需要清理的檔案")
                else:
                    st.warning(f"⚠️ 將刪除 {result['local_to_delete']} 個本地檔案")
            
            except Exception as e:
                st.error(f"❌ 預覽失敗: {e}")
    
    # 執行清理
    if cleanup_button:
        st.warning("⚠️ 確定要刪除舊檔案嗎？此操作無法復原！")
        
        confirm = st.checkbox("我確定要刪除")
        
        if confirm:
            with st.spinner("⏳ 正在清理..."):
                try:
                    result = sync_service.cleanup_old_files(
                        keep_months=keep_months,
                        dry_run=False
                    )
                    
                    st.success("✅ 清理完成！")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("本地已刪除", result['local_deleted'])
                    
                    with col2:
                        if 'gdrive_deleted' in result:
                            st.metric("GDrive 已刪除", result['gdrive_deleted'])
                    
                    if result.get('errors', 0) > 0:
                        st.warning(f"⚠️ {result['errors']} 個錯誤")
                
                except Exception as e:
                    st.error(f"❌ 清理失敗: {e}")


# ==================== 測試程式 ====================

if __name__ == "__main__":
    st.set_page_config(
        page_title="CDR 檔案管理",
        page_icon="📁",
        layout="wide"
    )
    
    # 測試設定
    ftp_config = {
        'host': 'ftp.example.com',
        'username': 'user',
        'password': 'pass',
        'port': 21
    }
    
    gdrive_config = None  # 測試時不啟用
    
    render_cdr_management_page(ftp_config, gdrive_config)

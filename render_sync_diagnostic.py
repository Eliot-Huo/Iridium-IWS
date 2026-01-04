"""
CDR 同步狀態診斷工具

用於檢查和診斷同步狀態檔案的問題
"""
import streamlit as st
import json
from datetime import datetime

def render_sync_status_diagnostic():
    """渲染同步狀態診斷頁面"""
    st.title("🔍 CDR 同步狀態診斷工具")
    st.caption("檢查同步狀態檔案是否正常運作")
    
    st.markdown("---")
    
    # 檢查 Google Drive 配置
    st.subheader("1️⃣ Google Drive 配置檢查")
    
    has_gdrive = False
    try:
        from src.infrastructure.gdrive_client import GoogleDriveClient, GDRIVE_AVAILABLE
        
        if GDRIVE_AVAILABLE and 'GDRIVE_FOLDER_ID' in st.secrets:
            st.success("✅ Google Drive 可用")
            has_gdrive = True
            
            folder_id = st.secrets['GDRIVE_FOLDER_ID']
            st.info(f"📁 根資料夾 ID: `{folder_id}`")
        else:
            st.error("❌ Google Drive 不可用")
            st.warning("請確認 Streamlit Secrets 中有 `GDRIVE_FOLDER_ID`")
    except Exception as e:
        st.error(f"❌ 檢查失敗: {e}")
    
    st.markdown("---")
    
    # 檢查狀態檔案
    st.subheader("2️⃣ 同步狀態檔案檢查")
    
    STATUS_FILENAME = '.sync_status.json'
    
    if not has_gdrive:
        st.warning("⚠️ Google Drive 不可用，跳過檢查")
        return
    
    try:
        from src.infrastructure.gdrive_client import GoogleDriveClient
        
        # 初始化 Google Drive 客戶端
        gdrive = GoogleDriveClient(st.secrets['GDRIVE_FOLDER_ID'])
        
        # 嘗試查找狀態檔案
        st.write("🔍 搜尋狀態檔案...")
        
        # 方法 1：在根目錄搜尋
        file_info = gdrive.find_file(STATUS_FILENAME, gdrive.folder_id)
        
        if file_info:
            st.success(f"✅ 找到狀態檔案: `{STATUS_FILENAME}`")
            
            # 顯示檔案資訊
            with st.expander("📄 檔案資訊"):
                st.json({
                    'File ID': file_info.get('id'),
                    'Name': file_info.get('name'),
                    'Size': file_info.get('size', 'Unknown'),
                    'Created': file_info.get('createdTime', 'Unknown'),
                    'Link': file_info.get('webViewLink', 'N/A')
                })
            
            # 嘗試下載並顯示內容
            if st.button("📥 下載並檢查內容"):
                try:
                    content = gdrive.download_file_content(STATUS_FILENAME)
                    data = json.loads(content)
                    
                    st.success("✅ 成功下載狀態檔案")
                    
                    # 顯示統計資訊
                    st.subheader("📊 同步統計")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "已處理檔案",
                            data.get('total_files_processed', 0)
                        )
                    
                    with col2:
                        last_sync = data.get('last_sync_time', '從未')
                        if last_sync != '從未':
                            last_sync_dt = datetime.fromisoformat(last_sync)
                            last_sync = last_sync_dt.strftime('%Y-%m-%d %H:%M')
                        st.metric(
                            "最後同步",
                            last_sync
                        )
                    
                    with col3:
                        st.metric(
                            "初始同步",
                            "✅ 完成" if data.get('initial_sync_completed') else "⏳ 未完成"
                        )
                    
                    # 顯示月份統計
                    if data.get('monthly_stats'):
                        st.subheader("📅 月份統計")
                        
                        for month, stats in sorted(data['monthly_stats'].items()):
                            with st.expander(f"📁 {month}"):
                                st.write(f"**檔案數量:** {stats.get('file_count', 0)}")
                                st.write(f"**記錄數量:** {stats.get('total_records', 0)}")
                                st.write(f"**最後更新:** {stats.get('last_updated', '未知')}")
                    
                    # 顯示完整內容
                    with st.expander("🔍 完整 JSON 內容"):
                        st.json(data)
                    
                except Exception as e:
                    st.error(f"❌ 下載失敗: {e}")
        else:
            st.warning(f"⚠️ 找不到狀態檔案: `{STATUS_FILENAME}`")
            st.info("這可能是因為：")
            st.markdown("""
            1. 這是第一次使用（尚未同步過）
            2. 檔案被誤刪
            3. 檔案在錯誤的資料夾中
            """)
            
            # 提供搜尋選項
            if st.button("🔍 在整個 Drive 搜尋"):
                st.write("搜尋中...")
                all_files = gdrive.find_file(STATUS_FILENAME, None)  # 搜尋整個 Drive
                
                if all_files:
                    st.warning("⚠️ 檔案在其他位置找到！")
                    st.json(all_files)
                else:
                    st.error("❌ 整個 Drive 都找不到狀態檔案")
    
    except Exception as e:
        st.error(f"❌ 診斷失敗: {e}")
        with st.expander("查看錯誤詳情"):
            st.exception(e)
    
    st.markdown("---")
    
    # 修復選項
    st.subheader("3️⃣ 修復選項")
    
    st.warning("⚠️ 如果狀態檔案有問題，您可以：")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 重新同步全部", type="primary"):
            st.info("請到「CDR 同步管理」頁面執行「重新同步全部」")
    
    with col2:
        if st.button("📝 手動創建狀態檔案"):
            try:
                # 創建空白狀態檔案
                empty_status = {
                    'version': '1.0',
                    'initial_sync_completed': False,
                    'last_sync_time': None,
                    'total_files_processed': 0,
                    'processed_files': {},
                    'monthly_stats': {},
                    'errors': {}
                }
                
                content = json.dumps(empty_status, indent=2)
                gdrive.upload_text_file(STATUS_FILENAME, content, folder_path='')
                
                st.success("✅ 已創建空白狀態檔案")
                st.info("現在可以執行同步了")
                
            except Exception as e:
                st.error(f"❌ 創建失敗: {e}")
    
    st.markdown("---")
    
    # 說明
    with st.expander("ℹ️ 關於同步狀態"):
        st.markdown("""
        ### 同步狀態檔案的作用
        
        狀態檔案 (`.sync_status.json`) 記錄了哪些 CDR 檔案已經下載和處理過。
        
        **重要性：**
        - ✅ 避免重複下載相同檔案
        - ✅ 實現增量同步（只下載新檔案）
        - ✅ 提升同步速度（900x 對於已同步的情況）
        
        **位置：**
        - Google Drive 根目錄（與 CDR 資料夾同級）
        - 本地備份：`./temp/ftp_download/.sync_status_local.json`
        
        **內容：**
        - `processed_files`: 已處理的檔案清單
        - `total_files_processed`: 已處理檔案總數
        - `last_sync_time`: 最後同步時間
        - `monthly_stats`: 每月統計資訊
        
        **問題診斷：**
        如果每次都重新下載全部檔案，可能是：
        1. 狀態檔案不存在或損壞
        2. Google Drive 權限問題
        3. 檔案在錯誤的資料夾中
        """)


if __name__ == "__main__":
    render_sync_status_diagnostic()

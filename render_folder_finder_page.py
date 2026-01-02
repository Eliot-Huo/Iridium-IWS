"""
Google Drive 資料夾 ID 查找工具
幫助找到正確的 CDR_Files 資料夾 ID
"""
import streamlit as st

def render_folder_finder_page():
    """資料夾查找頁面"""
    st.title("📁 Google Drive 資料夾查找")
    
    st.markdown("""
    這個工具會幫您：
    1. 列出服務帳號可以存取的所有資料夾
    2. 找到 `CDR_Files` 資料夾
    3. 取得正確的資料夾 ID
    """)
    
    if st.button("🔍 查找資料夾", type="primary"):
        find_folders()

def find_folders():
    """查找資料夾"""
    
    # 檢查 Secrets
    if 'gcp_service_account' not in st.secrets:
        st.error("❌ 找不到 gcp_service_account 設定")
        return
    
    try:
        from src.infrastructure.gdrive_client import GoogleDriveClient
        
        # 初始化客戶端（不提供 root_folder_id）
        service_account_info = dict(st.secrets.gcp_service_account)
        
        with st.spinner("連線中..."):
            # 直接使用 Google Drive API
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            scopes = ['https://www.googleapis.com/auth/drive']
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=scopes
            )
            service = build('drive', 'v3', credentials=credentials)
        
        st.success("✅ API 連線成功")
        
        # 搜尋所有服務帳號可以存取的資料夾
        st.subheader("📂 搜尋所有可存取的資料夾")
        
        with st.spinner("搜尋中..."):
            # 搜尋所有資料夾
            query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, owners, shared, permissions)',
                pageSize=100
            ).execute()
            
            folders = results.get('files', [])
        
        if not folders:
            st.warning("⚠️ 服務帳號無法存取任何資料夾")
            st.info("""
            **可能的原因：**
            1. 您還沒有共享任何資料夾給服務帳號
            2. 服務帳號 email 不正確
            
            **解決方法：**
            1. 在 Google Drive 中找到或建立 `CDR_Files` 資料夾
            2. 右鍵 → 共用
            3. 輸入服務帳號 email：
               ```
               airtimebilling@iridium-billing-system.iam.gserviceaccount.com
               ```
            4. 權限：編輯者
            5. 傳送
            6. 重新執行此工具
            """)
            return
        
        st.success(f"✅ 找到 {len(folders)} 個資料夾")
        
        # 尋找 CDR_Files
        cdr_folders = [f for f in folders if 'CDR' in f['name'].upper() or f['name'] == 'CDR_Files']
        
        if cdr_folders:
            st.subheader("🎯 可能的 CDR_Files 資料夾")
            
            for folder in cdr_folders:
                with st.expander(f"📁 {folder['name']}", expanded=True):
                    st.code(f"資料夾 ID: {folder['id']}", language="text")
                    
                    # 顯示擁有者
                    if 'owners' in folder:
                        owners = [o.get('emailAddress', 'Unknown') for o in folder['owners']]
                        st.write(f"**擁有者**: {', '.join(owners)}")
                    
                    # 顯示是否共享
                    if folder.get('shared', False):
                        st.success("✅ 此資料夾已共享")
                    else:
                        st.warning("⚠️ 此資料夾未共享")
                    
                    # 複製按鈕
                    st.code(f"""
# 將此 ID 加入 Secrets：
GCP_CDR_FOLDER_ID = "{folder['id']}"
                    """, language="toml")
        
        # 顯示所有資料夾
        st.subheader("📋 所有可存取的資料夾")
        
        for folder in folders:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"📁 **{folder['name']}**")
                st.caption(f"ID: `{folder['id']}`")
            
            with col2:
                if st.button("複製 ID", key=folder['id']):
                    st.code(folder['id'])
        
        # 說明如何使用
        st.divider()
        st.subheader("📝 如何使用找到的 ID")
        
        st.markdown("""
        ### 步驟 1: 確認資料夾
        
        1. 從上面的列表中找到您要使用的 `CDR_Files` 資料夾
        2. 複製它的 ID
        
        ### 步驟 2: 更新 Secrets
        
        1. 前往 Streamlit Cloud → Settings → Secrets
        2. 找到或新增 `GCP_CDR_FOLDER_ID`：
        
        ```toml
        GCP_CDR_FOLDER_ID = "您複製的ID"
        ```
        
        3. Save
        
        ### 步驟 3: Reboot 應用
        
        ### 步驟 4: 重新測試
        
        執行 Google Drive 診斷，應該就能成功了！
        """)
        
        # 如果沒有找到 CDR_Files
        if not cdr_folders:
            st.warning("⚠️ 沒有找到名稱包含 'CDR' 的資料夾")
            st.info("""
            **建議：**
            1. 檢查上面「所有可存取的資料夾」列表
            2. 如果看到您要的資料夾，複製它的 ID
            3. 如果沒有看到任何資料夾，表示服務帳號無法存取任何共享資料夾
            4. 請確認您已將資料夾共享給服務帳號
            """)
        
    except Exception as e:
        st.error(f"❌ 查找失敗: {e}")
        st.exception(e)

if __name__ == "__main__":
    render_folder_finder_page()

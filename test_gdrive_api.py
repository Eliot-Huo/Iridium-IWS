"""
Google Drive API 測試工具
直接測試 API 是否可用
"""
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def test_google_drive_api():
    """測試 Google Drive API"""
    
    st.title("🔍 Google Drive API 測試")
    
    st.info("""
    這個工具會直接測試 Google Drive API 是否真的可用。
    
    測試項目：
    1. 服務帳號認證
    2. Drive API 呼叫
    3. 列出服務帳號可存取的檔案
    """)
    
    if st.button("🚀 開始測試", type="primary"):
        
        # 1. 檢查 Secrets
        st.subheader("1️⃣ 檢查認證資訊")
        
        if 'gcp_service_account' not in st.secrets:
            st.error("❌ 找不到 gcp_service_account")
            return
        
        st.success("✅ 找到 gcp_service_account")
        
        # 2. 建立認證
        st.subheader("2️⃣ 建立服務帳號認證")
        
        try:
            credentials = service_account.Credentials.from_service_account_info(
                dict(st.secrets.gcp_service_account),
                scopes=['https://www.googleapis.com/auth/drive']
            )
            st.success("✅ 認證建立成功")
            
            # 顯示服務帳號 email
            st.info(f"📧 服務帳號: {credentials.service_account_email}")
            
        except Exception as e:
            st.error(f"❌ 認證建立失敗: {e}")
            st.exception(e)
            return
        
        # 3. 建立 Drive 服務
        st.subheader("3️⃣ 初始化 Google Drive API")
        
        try:
            service = build('drive', 'v3', credentials=credentials)
            st.success("✅ Google Drive API 初始化成功")
        except Exception as e:
            st.error(f"❌ API 初始化失敗: {e}")
            st.exception(e)
            return
        
        # 4. 測試 API 呼叫 - 列出檔案
        st.subheader("4️⃣ 測試 API 呼叫：列出可存取的檔案")
        
        try:
            with st.spinner("正在查詢..."):
                results = service.files().list(
                    pageSize=10,
                    fields="files(id, name, mimeType, owners)"
                ).execute()
            
            files = results.get('files', [])
            
            if not files:
                st.warning("⚠️ 服務帳號無法存取任何檔案")
                st.info("""
                **可能的原因：**
                1. Google Drive API 還沒生效
                2. 沒有任何檔案共享給服務帳號
                
                **解決方法：**
                1. 等待 15-30 分鐘讓 API 生效
                2. 在 Google Drive 中共享至少一個檔案/資料夾給服務帳號
                """)
            else:
                st.success(f"✅ API 正常運作！找到 {len(files)} 個檔案/資料夾")
                
                st.write("**可存取的檔案/資料夾：**")
                for file in files:
                    file_type = "📁" if file['mimeType'] == 'application/vnd.google-apps.folder' else "📄"
                    st.write(f"{file_type} **{file['name']}**")
                    st.write(f"   - ID: `{file['id']}`")
                    if 'owners' in file:
                        owners = [o.get('emailAddress', 'Unknown') for o in file['owners']]
                        st.write(f"   - 擁有者: {', '.join(owners)}")
                    st.write("")
                
        except HttpError as e:
            st.error(f"❌ API 呼叫失敗: {e}")
            
            if e.resp.status == 403:
                st.warning("""
                **403 錯誤：權限不足**
                
                可能的原因：
                1. Google Drive API 未啟用
                2. 服務帳號沒有 Drive 權限
                
                解決方法：
                1. 前往 GCP Console
                2. 確認 Google Drive API 已啟用
                3. 等待 15-30 分鐘
                """)
            elif e.resp.status == 404:
                st.warning("""
                **404 錯誤：找不到資源**
                
                這通常表示 API 設定有問題。
                """)
            
            st.exception(e)
            
        except Exception as e:
            st.error(f"❌ 未預期的錯誤: {e}")
            st.exception(e)
            return
        
        # 5. 測試特定資料夾
        st.subheader("5️⃣ 測試存取特定資料夾")
        
        folder_id = st.secrets.get('GCP_CDR_FOLDER_ID', None)
        
        if folder_id:
            st.info(f"測試資料夾 ID: {folder_id}")
            
            try:
                with st.spinner("正在存取資料夾..."):
                    folder = service.files().get(
                        fileId=folder_id,
                        fields='id, name, mimeType, owners'
                    ).execute()
                
                st.success(f"✅ 可以存取資料夾：{folder['name']}")
                st.write(f"**資料夾 ID**: `{folder['id']}`")
                if 'owners' in folder:
                    owners = [o.get('emailAddress', 'Unknown') for o in folder['owners']]
                    st.write(f"**擁有者**: {', '.join(owners)}")
                
            except HttpError as e:
                st.error(f"❌ 無法存取資料夾: {e}")
                
                if e.resp.status == 404:
                    st.warning("""
                    **404 錯誤：找不到資料夾**
                    
                    可能的原因：
                    1. 資料夾 ID 不正確
                    2. 資料夾未共享給服務帳號
                    3. Google Drive API 還沒生效
                    
                    解決方法：
                    1. 確認資料夾 ID 正確
                    2. 在 Google Drive 中共享資料夾給服務帳號
                    3. 等待 15-30 分鐘讓 API 和共享設定生效
                    """)
                
                st.exception(e)
                
        else:
            st.warning("⚠️ 未設定 GCP_CDR_FOLDER_ID")
        
        # 總結
        st.divider()
        st.subheader("📊 測試總結")
        
        st.info("""
        **如果看到「✅ API 正常運作」**：
        - Google Drive API 已生效
        - 服務帳號設定正確
        - 可以開始使用 CDR 同步功能
        
        **如果看到「⚠️ 無法存取任何檔案」**：
        - API 可能還在生效中
        - 建議等待 15-30 分鐘
        - 或檢查是否有共享任何檔案給服務帳號
        
        **如果看到「❌ 403 錯誤」**：
        - Google Drive API 未啟用或未生效
        - 前往 GCP Console 確認
        - 等待 API 生效（最多 2 小時）
        """)

if __name__ == '__main__':
    test_google_drive_api()

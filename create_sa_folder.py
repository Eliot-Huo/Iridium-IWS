"""
服務帳號資料夾建立工具
用服務帳號建立資料夾，並自動共享給個人帳號
"""
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def create_sa_folder():
    """用服務帳號建立資料夾並共享"""
    
    st.title("📁 服務帳號資料夾建立工具")
    
    st.info("""
    這個工具會：
    1. ✅ 用服務帳號在 Google Drive 建立資料夾
    2. ✅ 服務帳號是擁有者（API 一定可存取）
    3. ✅ 自動共享給您的個人帳號（您可以在 Drive 中看到）
    4. ✅ 自動取得 Folder ID
    """)
    
    # 檢查認證
    if 'gcp_service_account' not in st.secrets:
        st.error("❌ 找不到 gcp_service_account 設定")
        st.info("請在 Secrets 中設定 gcp_service_account")
        return
    
    try:
        credentials = service_account.Credentials.from_service_account_info(
            dict(st.secrets.gcp_service_account),
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        service_email = credentials.service_account_email
        
        st.success(f"✅ 服務帳號認證成功")
        st.code(service_email)
        
    except Exception as e:
        st.error(f"❌ 認證失敗: {e}")
        import traceback
        st.code(traceback.format_exc())
        return
    
    st.divider()
    
    # 輸入設定
    st.subheader("📋 設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        folder_name = st.text_input(
            "📁 資料夾名稱",
            value="Iridium Billing System",
            help="這個資料夾會由服務帳號建立"
        )
    
    with col2:
        owner_email = st.text_input(
            "👤 共享給",
            value=st.secrets.get('OWNER_EMAIL', ''),
            help="資料夾會共享給這個 Email（編輯權限）"
        )
    
    parent_folder_id = st.text_input(
        "📂 父資料夾 ID（可選）",
        value="",
        help="留空 = 在根目錄建立；填入 ID = 在該資料夾下建立"
    )
    
    st.divider()
    
    # 建立按鈕
    if st.button("🚀 建立資料夾", type="primary", use_container_width=True):
        
        if not folder_name:
            st.warning("⚠️ 請輸入資料夾名稱")
            return
        
        if not owner_email:
            st.warning("⚠️ 請輸入要共享的 Email")
            return
        
        # 開始建立
        st.write("---")
        st.subheader("🔄 執行中...")
        
        progress = st.empty()
        result_container = st.container()
        
        try:
            # 步驟 1: 建立資料夾
            progress.info("📁 步驟 1/3: 建立資料夾...")
            
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            folder = service.files().create(
                body=folder_metadata,
                fields='id, name, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            folder_id = folder['id']
            folder_link = folder.get('webViewLink', '')
            
            progress.success(f"✅ 步驟 1/3: 資料夾已建立")
            
            # 步驟 2: 共享給個人帳號
            progress.info(f"👤 步驟 2/3: 共享給 {owner_email}...")
            
            permission = {
                'type': 'user',
                'role': 'writer',  # 編輯權限
                'emailAddress': owner_email
            }
            
            service.permissions().create(
                fileId=folder_id,
                body=permission,
                fields='id',
                sendNotificationEmail=False,  # 不發送通知
                supportsAllDrives=True
            ).execute()
            
            progress.success(f"✅ 步驟 2/3: 已共享給 {owner_email}")
            
            # 步驟 3: 驗證存取
            progress.info("🔍 步驟 3/3: 驗證存取權限...")
            
            # 嘗試取得資料夾資訊
            test_folder = service.files().get(
                fileId=folder_id,
                fields='id, name, owners, permissions',
                supportsAllDrives=True
            ).execute()
            
            progress.success("✅ 步驟 3/3: 存取權限驗證成功")
            
            # 顯示結果
            with result_container:
                st.write("---")
                st.success("🎉 **資料夾建立成功！**")
                
                st.write("### 📊 資料夾資訊")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**名稱**")
                    st.code(folder_name)
                    
                    st.write("**ID**")
                    st.code(folder_id)
                
                with col2:
                    st.write("**擁有者**")
                    st.code(service_email)
                    
                    st.write("**共享給**")
                    st.code(owner_email)
                
                # 連結
                if folder_link:
                    st.write("### 🔗 開啟資料夾")
                    st.markdown(f"[📂 在 Google Drive 中開啟]({folder_link})")
                    st.caption("您現在可以在 Google Drive 中看到這個資料夾了！")
                
                # 權限詳情
                with st.expander("🔐 查看詳細權限"):
                    st.write("**擁有者：**")
                    for owner in test_folder.get('owners', []):
                        st.write(f"- {owner.get('emailAddress', 'Unknown')}")
                    
                    st.write("**權限列表：**")
                    for perm in test_folder.get('permissions', []):
                        perm_email = perm.get('emailAddress', 'Unknown')
                        perm_role = perm.get('role', 'Unknown')
                        perm_type = perm.get('type', 'Unknown')
                        st.write(f"- {perm_email} ({perm_type}, {perm_role})")
                
                st.write("---")
                
                # 下一步
                st.write("### 🎯 下一步")
                
                st.info(f"""
                **更新 Secrets 設定：**
                
                ```toml
                GCP_CDR_FOLDER_ID = "{folder_id}"
                ```
                
                然後：
                1. 儲存 Secrets
                2. Reboot 應用
                3. 執行 CDR 同步
                """)
                
                # 複製按鈕
                st.code(f'GCP_CDR_FOLDER_ID = "{folder_id}"')
                
        except HttpError as e:
            progress.error(f"❌ Google Drive API 錯誤")
            
            with result_container:
                st.error(f"錯誤代碼: {e.resp.status}")
                st.error(f"錯誤訊息: {e}")
                
                if e.resp.status == 403:
                    st.warning("""
                    **403 權限錯誤**
                    
                    可能的原因：
                    1. Google Drive API 未啟用
                    2. 服務帳號權限不足
                    3. Domain 限制（Google Workspace 設定）
                    """)
                
                with st.expander("詳細錯誤"):
                    import traceback
                    st.code(traceback.format_exc())
        
        except Exception as e:
            progress.error(f"❌ 發生錯誤")
            
            with result_container:
                st.error(f"錯誤: {e}")
                
                with st.expander("詳細錯誤"):
                    import traceback
                    st.code(traceback.format_exc())

if __name__ == '__main__':
    create_sa_folder()

"""
Google Drive 連線診斷工具
用於檢查 Google Drive API 設定和連線狀態
"""
import streamlit as st
from datetime import date
import tempfile
import os

def render_gdrive_diagnostic_page():
    """Google Drive 診斷頁面"""
    st.title("🔍 Google Drive 診斷工具")
    
    st.markdown("""
    這個工具會幫您檢查：
    1. ✅ Secrets 設定
    2. ✅ Google Drive API 連線
    3. ✅ 服務帳號權限
    4. ✅ 資料夾存取
    5. ✅ 檔案上傳功能
    """)
    
    # 開始診斷
    if st.button("🚀 開始診斷", type="primary"):
        run_diagnostics()

def run_diagnostics():
    """執行診斷"""
    
    # 1. 檢查 Secrets
    st.subheader("1️⃣ 檢查 Secrets 設定")
    
    secrets_ok = True
    
    # 檢查 gcp_service_account
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 找不到 gcp_service_account 設定")
        secrets_ok = False
    else:
        st.success("✅ gcp_service_account 存在")
        
        # 檢查必要欄位
        required_fields = [
            "type", "project_id", "private_key_id", "private_key",
            "client_email", "client_id", "auth_uri", "token_uri"
        ]
        
        for field in required_fields:
            if field not in st.secrets.gcp_service_account:
                st.error(f"❌ 缺少欄位: {field}")
                secrets_ok = False
            else:
                if field == "private_key":
                    # 檢查 private_key 格式
                    key = st.secrets.gcp_service_account[field]
                    if "\\n" not in key and "\n" not in key:
                        st.warning(f"⚠️ {field} 可能缺少換行符號 \\n")
                    else:
                        st.success(f"✅ {field}: 格式正確")
                elif field == "client_email":
                    email = st.secrets.gcp_service_account[field]
                    st.success(f"✅ {field}: {email}")
                else:
                    st.success(f"✅ {field}: 已設定")
    
    if not secrets_ok:
        st.error("❌ Secrets 設定有問題，請先修正")
        return
    
    # 2. 測試 Google Drive API 連線
    st.subheader("2️⃣ 測試 Google Drive API 連線")
    
    try:
        from src.infrastructure.gdrive_client import GoogleDriveClient
        
        with st.spinner("連線中..."):
            # 將 st.secrets.gcp_service_account 轉換為字典
            service_account_info = dict(st.secrets.gcp_service_account)
            
            # 檢查是否有 folder ID
            root_folder_id = st.secrets.get('GCP_CDR_FOLDER_ID', None)
            if root_folder_id:
                st.info(f"📁 使用指定的資料夾 ID: {root_folder_id}")
                gdrive = GoogleDriveClient(
                    service_account_info=service_account_info,
                    root_folder_id=root_folder_id
                )
            else:
                st.warning("⚠️ 未設定 GCP_CDR_FOLDER_ID，將嘗試自動搜尋資料夾")
                gdrive = GoogleDriveClient(service_account_info=service_account_info)
            
            st.success("✅ Google Drive API 連線成功")
            
            # 顯示服務帳號資訊
            email = st.secrets.gcp_service_account.client_email
            st.info(f"📧 服務帳號: {email}")
            
    except Exception as e:
        st.error(f"❌ Google Drive API 連線失敗: {e}")
        st.exception(e)
        return
    
    # 3. 檢查根資料夾
    st.subheader("3️⃣ 檢查根資料夾")
    
    try:
        # 檢查是否有提供資料夾 ID
        folder_id = st.secrets.get('GCP_CDR_FOLDER_ID', None)
        
        if folder_id:
            st.info(f"📁 使用設定的資料夾 ID: {folder_id}")
            
            # 直接檢查這個資料夾
            with st.spinner("檢查資料夾..."):
                try:
                    folder = gdrive.service.files().get(
                        fileId=folder_id,
                        fields='id, name, permissions, owners'
                    ).execute()
                    
                    st.success(f"✅ 找到資料夾: {folder['name']}")
                    st.info(f"📁 資料夾 ID: {folder['id']}")
                    
                    # 顯示擁有者
                    if 'owners' in folder:
                        owners = [o.get('emailAddress', 'Unknown') for o in folder['owners']]
                        st.write(f"**擁有者**: {', '.join(owners)}")
                    
                    # 檢查權限
                    st.write("**權限檢查：**")
                    permissions_result = gdrive.service.files().get(
                        fileId=folder_id,
                        fields='permissions'
                    ).execute()
                    
                    has_permission = False
                    for perm in permissions_result.get('permissions', []):
                        if perm.get('emailAddress') == email:
                            has_permission = True
                            st.success(f"✅ 服務帳號有權限: {perm.get('role')}")
                            break
                    
                    if not has_permission:
                        st.error("❌ 服務帳號沒有此資料夾的權限")
                        st.warning(f"請在 Google Drive 中將此資料夾共享給: {email}")
                        return
                    
                except Exception as e:
                    st.error(f"❌ 無法存取資料夾 ID: {folder_id}")
                    st.error(f"錯誤: {e}")
                    st.warning("可能的原因：")
                    st.write("1. 資料夾 ID 不正確")
                    st.write("2. 資料夾未共享給服務帳號")
                    st.write("3. 資料夾已被刪除")
                    return
        
        else:
            # 沒有提供 ID，嘗試搜尋 CDR_Files
            st.warning("⚠️ 未設定 GCP_CDR_FOLDER_ID，嘗試搜尋資料夾...")
            
            with st.spinner("搜尋資料夾..."):
                results = gdrive.service.files().list(
                    q="name='CDR_Files' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                    spaces='drive',
                    fields='files(id, name, permissions)'
                ).execute()
                
                files = results.get('files', [])
                
                if not files:
                    st.error("❌ 找不到 CDR_Files 資料夾")
                    st.warning("請在 Secrets 中設定 GCP_CDR_FOLDER_ID，或在 Google Drive 中創建 'CDR_Files' 資料夾")
                    return
                
                folder = files[0]
                st.success(f"✅ 找到 CDR_Files 資料夾")
                st.info(f"📁 資料夾 ID: {folder['id']}")
                
                # 檢查權限
                st.write("**權限檢查：**")
                try:
                    permissions = gdrive.service.files().get(
                        fileId=folder['id'],
                        fields='permissions'
                    ).execute()
                    
                    has_permission = False
                    for perm in permissions.get('permissions', []):
                        if perm.get('emailAddress') == email:
                            has_permission = True
                            st.success(f"✅ 服務帳號有權限: {perm.get('role')}")
                            break
                    
                    if not has_permission:
                        st.error("❌ 服務帳號沒有存取權限")
                        st.warning(f"請在 Google Drive 中將資料夾共享給: {email}")
                        return
                    
                except Exception as e:
                    st.error(f"❌ 無法存取資料夾 ID: {folder_id}")
                    st.error(f"錯誤: {e}")
                    st.warning("可能的原因：")
                    st.write("1. 資料夾 ID 不正確")
                    st.write("2. 資料夾未共享給服務帳號")
                    st.write("3. 資料夾已被刪除")
                    return
        
    except Exception as e:
        st.error(f"❌ 檢查資料夾失敗: {e}")
        st.exception(e)
        return
    
    # 4. 測試資料夾建立
    st.subheader("4️⃣ 測試資料夾建立")
    
    try:
        with st.spinner("測試建立測試資料夾..."):
            # 嘗試建立測試資料夾
            test_date = date.today()
            folder_id = gdrive.get_month_folder_id(test_date)
            
            st.success(f"✅ 成功建立/取得月份資料夾")
            st.info(f"📁 {test_date.year}/{test_date.month:02d}/ - ID: {folder_id}")
            
    except Exception as e:
        st.error(f"❌ 建立資料夾失敗: {e}")
        st.exception(e)
        return
    
    # 5. 測試檔案上傳
    st.subheader("5️⃣ 測試檔案上傳")
    
    try:
        with st.spinner("測試上傳檔案..."):
            # 建立測試檔案
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(f"Google Drive 診斷測試檔案\n")
                f.write(f"建立時間: {date.today()}\n")
                f.write(f"服務帳號: {email}\n")
                test_file_path = f.name
            
            try:
                # 上傳測試檔案
                result = gdrive.upload_file(
                    local_path=test_file_path,
                    file_date=date.today(),
                    filename='GDRIVE_TEST.txt'
                )
                
                st.success("✅ 檔案上傳成功！")
                st.json(result)
                
                # 提供連結
                if 'webViewLink' in result:
                    st.markdown(f"🔗 [在 Google Drive 中查看]({result['webViewLink']})")
                
                st.info("💡 請前往 Google Drive 確認檔案是否真的出現在 CDR_Files 資料夾中")
                
            finally:
                # 清理測試檔案
                if os.path.exists(test_file_path):
                    os.remove(test_file_path)
                
    except Exception as e:
        st.error(f"❌ 上傳測試檔案失敗: {e}")
        st.exception(e)
        return
    
    # 6. 檢查現有檔案
    st.subheader("6️⃣ 列出現有檔案")
    
    try:
        with st.spinner("列出資料夾中的檔案..."):
            # 列出當月資料夾中的檔案
            files = gdrive.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields='files(id, name, size, createdTime, webViewLink)',
                pageSize=20
            ).execute()
            
            file_list = files.get('files', [])
            
            if not file_list:
                st.warning("⚠️ 資料夾中沒有檔案")
            else:
                st.success(f"✅ 找到 {len(file_list)} 個檔案")
                
                for file in file_list:
                    st.write(f"📄 {file['name']}")
                    st.write(f"   - 大小: {file.get('size', 'N/A')} bytes")
                    st.write(f"   - 建立時間: {file.get('createdTime', 'N/A')}")
                    if 'webViewLink' in file:
                        st.write(f"   - [查看]({file['webViewLink']})")
                
    except Exception as e:
        st.error(f"❌ 列出檔案失敗: {e}")
        st.exception(e)
    
    # 完成
    st.success("🎉 診斷完成！")
    
    st.markdown("""
    ---
    ### 📋 診斷結果總結
    
    如果所有步驟都通過：
    - ✅ Secrets 設定正確
    - ✅ Google Drive API 連線正常
    - ✅ 資料夾權限正確
    - ✅ 可以建立資料夾
    - ✅ 可以上傳檔案
    
    **但是 CDR 同步仍然沒有檔案上傳**，可能的原因：
    1. CDR 同步程式中的 `gdrive` 物件沒有正確初始化
    2. 上傳程式碼有 bug 但沒有拋出錯誤
    3. 檔案被上傳到錯誤的資料夾
    
    請檢查同步訊息中是否有：
    ```
    - 已上傳到 Google Drive: 2025/01
    ```
    
    如果有這行訊息但 Google Drive 沒有檔案，請提供完整的錯誤訊息。
    """)

if __name__ == "__main__":
    render_gdrive_diagnostic_page()

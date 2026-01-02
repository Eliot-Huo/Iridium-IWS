"""
Google Drive 資料夾 ID 反查工具
從 Folder ID 查詢資料夾的完整路徑和資訊
"""
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def reverse_lookup_folder():
    """反查資料夾 ID"""
    
    st.title("🔍 資料夾 ID 反查工具")
    
    st.info("""
    這個工具可以從 Folder ID 查詢：
    1. 資料夾名稱
    2. 擁有者
    3. 完整路徑（如果可存取）
    4. 共享狀態
    """)
    
    # 輸入資料夾 ID
    folder_id = st.text_input(
        "📁 輸入資料夾 ID",
        value=st.secrets.get('GCP_CDR_FOLDER_ID', ''),
        help="例如：1LyyEu86QAdZlxmE4NjOzgHyfh8Id_W8a"
    )
    
    if st.button("🔍 查詢", type="primary") and folder_id:
        
        # 建立認證
        st.subheader("1️⃣ 建立認證")
        
        if 'gcp_service_account' not in st.secrets:
            st.error("❌ 找不到 gcp_service_account")
            return
        
        try:
            credentials = service_account.Credentials.from_service_account_info(
                dict(st.secrets.gcp_service_account),
                scopes=['https://www.googleapis.com/auth/drive']
            )
            service = build('drive', 'v3', credentials=credentials)
            
            service_email = credentials.service_account_email
            st.success(f"✅ 認證成功")
            st.info(f"📧 服務帳號: {service_email}")
            
        except Exception as e:
            st.error(f"❌ 認證失敗: {e}")
            return
        
        # 查詢資料夾
        st.subheader("2️⃣ 查詢資料夾資訊")
        
        try:
            with st.spinner("正在查詢..."):
                folder = service.files().get(
                    fileId=folder_id,
                    fields='id, name, mimeType, owners, parents, permissions, webViewLink, shared, createdTime, modifiedTime',
                    supportsAllDrives=True
                ).execute()
            
            st.success("✅ 找到資料夾！")
            
            # 顯示基本資訊
            st.write("### 📋 基本資訊")
            st.write(f"**名稱**: {folder.get('name', 'Unknown')}")
            st.write(f"**ID**: `{folder.get('id')}`")
            st.write(f"**類型**: {folder.get('mimeType')}")
            st.write(f"**建立時間**: {folder.get('createdTime', 'Unknown')}")
            st.write(f"**修改時間**: {folder.get('modifiedTime', 'Unknown')}")
            
            # 網址
            if 'webViewLink' in folder:
                st.write(f"**網址**: {folder['webViewLink']}")
                st.markdown(f"[🔗 在 Google Drive 中開啟]({folder['webViewLink']})")
            
            # 擁有者
            st.write("### 👤 擁有者")
            if 'owners' in folder:
                for owner in folder['owners']:
                    st.write(f"- {owner.get('displayName', 'Unknown')} ({owner.get('emailAddress', 'Unknown')})")
            else:
                st.write("無法取得擁有者資訊")
            
            # 父資料夾（路徑）
            st.write("### 📂 路徑")
            if 'parents' in folder and folder['parents']:
                st.info("正在查詢完整路徑...")
                path = _get_folder_path(service, folder_id)
                st.write("**完整路徑**:")
                st.code(" / ".join(path))
            else:
                st.write("此資料夾在根目錄")
            
            # 共享狀態
            st.write("### 🔐 共享狀態")
            is_shared = folder.get('shared', False)
            if is_shared:
                st.success("✅ 此資料夾已共享")
            else:
                st.warning("⚠️ 此資料夾未共享（或僅限擁有者）")
            
            # 權限列表
            if 'permissions' in folder:
                st.write("**權限列表**:")
                has_service_account = False
                
                for perm in folder['permissions']:
                    perm_type = perm.get('type', 'Unknown')
                    role = perm.get('role', 'Unknown')
                    email = perm.get('emailAddress', '')
                    
                    if email == service_email:
                        st.success(f"✅ **服務帳號有權限**: {role}")
                        has_service_account = True
                    else:
                        if email:
                            st.write(f"- {perm_type}: {email} ({role})")
                        else:
                            st.write(f"- {perm_type}: {perm.get('displayName', 'Unknown')} ({role})")
                
                if not has_service_account:
                    st.error(f"❌ 服務帳號 ({service_email}) 沒有此資料夾的權限")
                    st.warning("""
                    **解決方法**:
                    1. 在 Google Drive 中開啟此資料夾
                    2. 右鍵 → 共用
                    3. 添加服務帳號的 Email
                    4. 權限選擇：內容管理員
                    5. 傳送
                    """)
            else:
                st.warning("無法取得權限資訊")
            
        except HttpError as e:
            st.error(f"❌ 無法存取資料夾: {e}")
            
            if e.resp.status == 404:
                st.warning("""
                **404 錯誤：找不到資料夾**
                
                可能的原因：
                1. **資料夾 ID 不正確**
                   - 請從 Google Drive 網址複製正確的 ID
                   
                2. **資料夾未共享給服務帳號**
                   - 即使資料夾存在，如果沒有共享，API 也會回傳 404
                   
                3. **資料夾已被刪除**
                   - 檢查資料夾是否還存在
                
                **如何取得正確的資料夾 ID**：
                1. 在 Google Drive 中開啟目標資料夾
                2. 查看網址列：
                   ```
                   https://drive.google.com/drive/folders/XXXXXXXXXXXXXXX
                   ```
                3. 複製 `folders/` 後面的那串文字
                
                **驗證方法**：
                - 使用「📁 資料夾查找」工具
                - 列出服務帳號可存取的所有資料夾
                - 從列表中找到正確的資料夾 ID
                """)
            elif e.resp.status == 403:
                st.warning("""
                **403 錯誤：權限不足**
                
                可能的原因：
                1. Google Drive API 未啟用或未生效
                2. 服務帳號沒有存取權限
                """)
            
            st.exception(e)
            
        except Exception as e:
            st.error(f"❌ 未預期的錯誤: {e}")
            st.exception(e)

def _get_folder_path(service, folder_id, max_depth=10):
    """
    取得資料夾的完整路徑
    
    Args:
        service: Google Drive API 服務
        folder_id: 資料夾 ID
        max_depth: 最大深度（防止無限遞迴）
        
    Returns:
        路徑列表（從根到目標資料夾）
    """
    path = []
    current_id = folder_id
    depth = 0
    
    try:
        while current_id and depth < max_depth:
            # 查詢當前資料夾
            folder = service.files().get(
                fileId=current_id,
                fields='id, name, parents',
                supportsAllDrives=True
            ).execute()
            
            # 添加到路徑（反向）
            path.insert(0, folder.get('name', 'Unknown'))
            
            # 取得父資料夾
            if 'parents' in folder and folder['parents']:
                current_id = folder['parents'][0]
                depth += 1
            else:
                # 已到根目錄
                break
        
        return path
        
    except Exception as e:
        # 無法取得完整路徑
        return path if path else ['（無法取得路徑）']

if __name__ == '__main__':
    reverse_lookup_folder()

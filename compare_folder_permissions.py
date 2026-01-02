"""
共享權限比較工具
比較兩個資料夾的權限差異
"""
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def compare_folder_permissions():
    """比較資料夾權限"""
    
    st.title("🔍 資料夾權限比較工具")
    
    st.info("""
    比較兩個資料夾的權限設定，找出差異。
    
    用途：
    - 比較可存取和無法存取的資料夾
    - 找出權限設定的差異
    """)
    
    # 建立認證
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
        
    except Exception as e:
        st.error(f"❌ 認證失敗: {e}")
        return
    
    # 輸入兩個資料夾 ID
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ 可存取的資料夾")
        folder1_id = st.text_input(
            "資料夾 ID 1（例如：CDR_Files）",
            key="folder1"
        )
    
    with col2:
        st.subheader("❌ 無法存取的資料夾")
        folder2_id = st.text_input(
            "資料夾 ID 2（Iridium Billing System）",
            value=st.secrets.get('GCP_CDR_FOLDER_ID', ''),
            key="folder2"
        )
    
    if st.button("🔍 比較權限", type="primary"):
        
        if not folder1_id or not folder2_id:
            st.warning("請輸入兩個資料夾 ID")
            return
        
        st.divider()
        
        # 查詢兩個資料夾
        folder1_info = _get_folder_info(service, folder1_id, service_email)
        folder2_info = _get_folder_info(service, folder2_id, service_email)
        
        # 顯示比較結果
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("✅ 資料夾 1")
            _display_folder_info(folder1_info, service_email)
        
        with col2:
            st.subheader("❌ 資料夾 2")
            _display_folder_info(folder2_info, service_email)
        
        # 分析差異
        st.divider()
        st.subheader("📊 差異分析")
        
        if folder1_info['success'] and not folder2_info['success']:
            st.error("❌ 資料夾 2 無法存取")
            st.write("**可能的原因：**")
            
            if folder2_info['error_code'] == 404:
                st.write("""
                1. **資料夾 ID 不正確**
                2. **資料夾未共享給服務帳號**
                3. **資料夾的共享設定與資料夾 1 不同**
                
                **建議解決方法：**
                """)
                
                if folder1_info['is_owner']:
                    st.success("""
                    ✅ **資料夾 1 的擁有者是服務帳號**
                    
                    這表示資料夾 1 是程式自動建立的，所以服務帳號自然有權限。
                    
                    **解決方案 A**: 使用資料夾 1 作為根資料夾
                    - 更新 GCP_CDR_FOLDER_ID 為資料夾 1 的 ID
                    
                    **解決方案 B**: 讓資料夾 2 的擁有者也是服務帳號
                    - 在 Google Drive 中將資料夾 2 的擁有權轉移給服務帳號
                    - 或重新用程式建立資料夾
                    """)
                else:
                    st.info("""
                    **資料夾 1 和 2 都不是服務帳號擁有**
                    
                    但資料夾 1 可以存取，資料夾 2 不行。
                    
                    **可能的差異：**
                    - 共享設定的時間點不同
                    - 權限層級不同
                    - 共享方式不同（直接共享 vs 繼承）
                    """)
        
        elif folder1_info['success'] and folder2_info['success']:
            st.success("✅ 兩個資料夾都可以存取")
            
            # 比較權限
            if folder1_info['permission_role'] == folder2_info['permission_role']:
                st.info(f"權限相同：{folder1_info['permission_role']}")
            else:
                st.warning(f"""
                權限不同：
                - 資料夾 1: {folder1_info['permission_role']}
                - 資料夾 2: {folder2_info['permission_role']}
                """)
        
        else:
            st.error("❌ 兩個資料夾都無法存取")
            st.warning("請檢查 Google Drive API 是否已啟用")

def _get_folder_info(service, folder_id, service_email):
    """取得資料夾資訊"""
    info = {
        'success': False,
        'name': None,
        'owners': [],
        'is_owner': False,
        'permission_role': None,
        'error_code': None,
        'error_message': None
    }
    
    try:
        folder = service.files().get(
            fileId=folder_id,
            fields='id, name, owners, permissions',
            supportsAllDrives=True
        ).execute()
        
        info['success'] = True
        info['name'] = folder.get('name', 'Unknown')
        info['owners'] = folder.get('owners', [])
        
        # 檢查是否為擁有者
        for owner in info['owners']:
            if owner.get('emailAddress') == service_email:
                info['is_owner'] = True
                break
        
        # 檢查權限
        for perm in folder.get('permissions', []):
            if perm.get('emailAddress') == service_email:
                info['permission_role'] = perm.get('role')
                break
        
    except HttpError as e:
        info['error_code'] = e.resp.status
        info['error_message'] = str(e)
    
    except Exception as e:
        info['error_message'] = str(e)
    
    return info

def _display_folder_info(info, service_email):
    """顯示資料夾資訊"""
    
    if info['success']:
        st.success(f"✅ 可存取：{info['name']}")
        
        # 擁有者
        st.write("**擁有者：**")
        for owner in info['owners']:
            email = owner.get('emailAddress', 'Unknown')
            if email == service_email:
                st.write(f"- 🤖 {email} （服務帳號）")
            else:
                st.write(f"- 👤 {email}")
        
        # 權限
        if info['is_owner']:
            st.success("🤖 服務帳號是擁有者")
        elif info['permission_role']:
            st.info(f"權限：{info['permission_role']}")
        else:
            st.warning("無法取得權限資訊")
    
    else:
        st.error("❌ 無法存取")
        if info['error_code']:
            st.write(f"錯誤代碼：{info['error_code']}")
        if info['error_message']:
            with st.expander("錯誤詳情"):
                st.code(info['error_message'])

if __name__ == '__main__':
    compare_folder_permissions()

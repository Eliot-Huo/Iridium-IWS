"""
根本原因診�斷工具
系統性找出為什麼共享不生效
"""
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def diagnose_sharing_issue():
    """診斷共享問題的根本原因"""
    
    st.title("🔬 共享問題根本原因診斷")
    
    st.info("""
    這個工具會系統性診斷為什麼資料夾共享給服務帳號後，API 還是回傳 404。
    
    診斷項目：
    1. 資料夾是否存在
    2. 服務帳號是否有權限
    3. 權限的詳細設定
    4. 與可存取資料夾的對比
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
        
        st.success(f"✅ 認證成功")
        st.info(f"📧 服務帳號: {service_email}")
        
    except Exception as e:
        st.error(f"❌ 認證失敗: {e}")
        return
    
    st.divider()
    
    # 輸入兩個資料夾 ID
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ 可存取的資料夾")
        st.write("（例如：CDR_Files）")
        working_folder_id = st.text_input(
            "資料夾 ID",
            key="working",
            help="從資料夾查找工具複製"
        )
    
    with col2:
        st.subheader("❌ 無法存取的資料夾")
        st.write("（Iridium Billing System）")
        broken_folder_id = st.text_input(
            "資料夾 ID",
            value=st.secrets.get('GCP_CDR_FOLDER_ID', ''),
            key="broken"
        )
    
    if st.button("🔬 開始診斷", type="primary"):
        
        if not working_folder_id or not broken_folder_id:
            st.warning("請輸入兩個資料夾 ID")
            return
        
        st.divider()
        
        # 診斷
        st.header("📊 診斷結果")
        
        # 測試 1: 可存取的資料夾
        st.subheader("1️⃣ 分析可存取的資料夾")
        working_info = _diagnose_folder(service, working_folder_id, service_email)
        
        if working_info['accessible']:
            st.success("✅ 可以存取")
            _display_folder_details(working_info)
        else:
            st.error("❌ 無法存取（這不對，應該要能存取）")
            st.write(f"錯誤: {working_info.get('error')}")
        
        st.divider()
        
        # 測試 2: 無法存取的資料夾
        st.subheader("2️⃣ 分析無法存取的資料夾")
        broken_info = _diagnose_folder(service, broken_folder_id, service_email)
        
        if broken_info['accessible']:
            st.success("✅ 可以存取（問題已解決！）")
            _display_folder_details(broken_info)
        else:
            st.error("❌ 無法存取（預期中）")
            st.write(f"錯誤代碼: {broken_info.get('error_code')}")
            st.write(f"錯誤訊息: {broken_info.get('error')}")
        
        st.divider()
        
        # 對比分析
        st.subheader("3️⃣ 對比分析")
        
        if working_info['accessible'] and not broken_info['accessible']:
            _compare_folders(working_info, broken_info, service_email)
        elif working_info['accessible'] and broken_info['accessible']:
            st.success("✅ 兩個資料夾都可以存取！問題已解決！")
        else:
            st.error("❌ 兩個資料夾都無法存取，這很奇怪")
        
        st.divider()
        
        # 測試 3: 嘗試用不同方法存取
        st.subheader("4️⃣ 進階測試")
        _advanced_tests(service, broken_folder_id, service_email)

def _diagnose_folder(service, folder_id, service_email):
    """診斷單個資料夾"""
    info = {
        'accessible': False,
        'folder_id': folder_id,
        'name': None,
        'owners': [],
        'permissions': [],
        'shared': False,
        'service_account_permission': None,
        'error': None,
        'error_code': None
    }
    
    try:
        # 嘗試取得資料夾資訊
        folder = service.files().get(
            fileId=folder_id,
            fields='id, name, owners, shared, capabilities, permissions',
            supportsAllDrives=True
        ).execute()
        
        info['accessible'] = True
        info['name'] = folder.get('name')
        info['owners'] = folder.get('owners', [])
        info['shared'] = folder.get('shared', False)
        info['capabilities'] = folder.get('capabilities', {})
        
        # 取得權限列表
        try:
            permissions = service.permissions().list(
                fileId=folder_id,
                fields='permissions(id, type, role, emailAddress, displayName)',
                supportsAllDrives=True
            ).execute()
            
            info['permissions'] = permissions.get('permissions', [])
            
            # 找出服務帳號的權限
            for perm in info['permissions']:
                if perm.get('emailAddress') == service_email:
                    info['service_account_permission'] = perm
                    break
        
        except HttpError as e:
            info['permissions_error'] = str(e)
    
    except HttpError as e:
        info['error'] = str(e)
        info['error_code'] = e.resp.status
    
    except Exception as e:
        info['error'] = str(e)
    
    return info

def _display_folder_details(info):
    """顯示資料夾詳情"""
    
    st.write(f"**名稱**: {info['name']}")
    st.write(f"**ID**: `{info['folder_id']}`")
    st.write(f"**共享狀態**: {'✅ 已共享' if info['shared'] else '⚠️ 未共享'}")
    
    # 擁有者
    st.write("**擁有者**:")
    for owner in info['owners']:
        st.write(f"- {owner.get('emailAddress', 'Unknown')}")
    
    # 服務帳號權限
    if info['service_account_permission']:
        perm = info['service_account_permission']
        st.success(f"✅ 服務帳號權限: {perm.get('role')}")
        st.write(f"- 類型: {perm.get('type')}")
        st.write(f"- ID: {perm.get('id')}")
    else:
        st.error("❌ 服務帳號沒有權限（或無法取得權限資訊）")
    
    # 所有權限
    with st.expander("查看所有權限"):
        st.json(info['permissions'])

def _compare_folders(working, broken, service_email):
    """對比兩個資料夾的差異"""
    
    st.write("### 🔍 關鍵差異")
    
    # 差異 1: 擁有者
    working_owner = working['owners'][0].get('emailAddress') if working['owners'] else None
    broken_owner = broken['owners'][0].get('emailAddress') if broken.get('owners') else 'Unknown'
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**✅ 可存取資料夾**")
        st.write(f"擁有者: {working_owner}")
        if working_owner == service_email:
            st.success("🤖 服務帳號是擁有者")
        else:
            st.info("👤 個人帳號是擁有者")
    
    with col2:
        st.write("**❌ 無法存取資料夾**")
        if broken['accessible']:
            st.write(f"擁有者: {broken_owner}")
        else:
            st.write("無法取得擁有者資訊（404 錯誤）")
    
    # 分析
    st.divider()
    st.write("### 💡 根本原因分析")
    
    if working_owner == service_email:
        st.warning("""
        **發現關鍵差異！**
        
        ✅ **可存取的資料夾**：服務帳號是**擁有者**
        ❌ **無法存取的資料夾**：您的個人帳號是**擁有者**
        
        **這就是問題所在！**
        
        當服務帳號只是「被共享者」而不是「擁有者」時，
        Google Drive API 可能無法正確存取資料夾。
        
        **解決方案：**
        
        1. **轉移擁有權**（推薦）
           - 在 Google Drive 中
           - 將「Iridium Billing System」的擁有權轉移給服務帳號
        
        2. **使用服務帳號建立的資料夾**
           - 直接使用 CDR_Files
           - 或讓程式建立新資料夾
        
        3. **Domain-Wide Delegation**（進階）
           - 在 GCP 中設定 Domain-Wide Delegation
           - 讓服務帳號可以「冒充」您的帳號
        """)
    else:
        st.info("""
        兩個資料夾的擁有者都不是服務帳號。
        
        需要進一步診斷其他差異。
        """)

def _advanced_tests(service, folder_id, service_email):
    """進階測試"""
    
    st.write("**測試 1: 嘗試列出資料夾內容**")
    
    try:
        with st.spinner("查詢中..."):
            results = service.files().list(
                q=f"'{folder_id}' in parents",
                pageSize=10,
                fields='files(id, name)',
                supportsAllDrives=True
            ).execute()
        
        files = results.get('files', [])
        st.success(f"✅ 可以列出內容！找到 {len(files)} 個項目")
        
        if files:
            st.write("內容：")
            for f in files:
                st.write(f"- {f['name']} ({f['id']})")
    
    except HttpError as e:
        st.error(f"❌ 無法列出內容: {e}")
    
    st.divider()
    
    st.write("**測試 2: 檢查 supportsAllDrives 參數**")
    
    try:
        # 不使用 supportsAllDrives
        folder = service.files().get(
            fileId=folder_id,
            fields='id, name'
        ).execute()
        
        st.success("✅ 不使用 supportsAllDrives 也可以存取")
    
    except HttpError as e:
        st.error(f"❌ 不使用 supportsAllDrives 無法存取: {e}")
        st.info("這可能表示資料夾在共享雲端硬碟中")

if __name__ == '__main__':
    diagnose_sharing_issue()

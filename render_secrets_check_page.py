"""
Secrets 檢查工具
用於檢查 Streamlit Secrets 設定
"""
import streamlit as st

def render_secrets_check_page():
    """Secrets 檢查頁面"""
    st.title("🔑 Secrets 檢查工具")
    
    st.markdown("""
    這個工具會檢查您的 Streamlit Secrets 設定。
    """)
    
    if st.button("🔍 檢查 Secrets", type="primary"):
        check_secrets()

def check_secrets():
    """檢查 Secrets"""
    
    st.subheader("📋 Secrets 內容")
    
    # 檢查所有 Secrets keys
    st.write("**所有 Secrets keys:**")
    
    try:
        all_keys = list(st.secrets.keys())
        st.write(all_keys)
    except Exception as e:
        st.error(f"❌ 無法讀取 Secrets: {e}")
        return
    
    st.divider()
    
    # 檢查 FTP 設定
    st.subheader("1️⃣ FTP 設定")
    
    ftp_keys = ['FTP_HOST', 'FTP_USERNAME', 'FTP_PASSWORD', 'FTP_PORT']
    for key in ftp_keys:
        if key in st.secrets:
            if 'PASSWORD' in key:
                st.success(f"✅ {key}: ***")
            else:
                st.success(f"✅ {key}: {st.secrets[key]}")
        else:
            st.error(f"❌ 缺少: {key}")
    
    st.divider()
    
    # 檢查 IWS 設定
    st.subheader("2️⃣ IWS 設定")
    
    iws_keys = ['IWS_USERNAME', 'IWS_PASSWORD', 'IWS_SP_ACCOUNT', 'IWS_ENDPOINT']
    for key in iws_keys:
        if key in st.secrets:
            if 'PASSWORD' in key:
                st.success(f"✅ {key}: ***")
            else:
                st.success(f"✅ {key}: {st.secrets[key]}")
        else:
            st.error(f"❌ 缺少: {key}")
    
    st.divider()
    
    # 檢查 Google Drive 設定
    st.subheader("3️⃣ Google Drive 設定")
    
    # 檢查新格式
    if 'gcp_service_account' in st.secrets:
        st.success("✅ 找到 `gcp_service_account` (新格式)")
        
        # 檢查必要欄位
        required_fields = [
            'type', 'project_id', 'private_key_id', 'private_key',
            'client_email', 'client_id', 'auth_uri', 'token_uri'
        ]
        
        for field in required_fields:
            if field in st.secrets.gcp_service_account:
                if field == 'private_key':
                    # 檢查格式
                    key = st.secrets.gcp_service_account[field]
                    if '\\n' in key or '\n' in key:
                        st.success(f"✅ {field}: 格式正確（包含換行符號）")
                    else:
                        st.warning(f"⚠️ {field}: 可能缺少換行符號")
                elif 'key' in field or 'uri' in field:
                    st.success(f"✅ {field}: 已設定")
                else:
                    st.success(f"✅ {field}: {st.secrets.gcp_service_account[field]}")
            else:
                st.error(f"❌ 缺少: {field}")
        
        # 嘗試轉換為字典
        st.write("\n**轉換為字典測試:**")
        try:
            service_account_dict = dict(st.secrets.gcp_service_account)
            st.success(f"✅ 成功轉換為字典，包含 {len(service_account_dict)} 個欄位")
            st.json(list(service_account_dict.keys()))
        except Exception as e:
            st.error(f"❌ 轉換失敗: {e}")
    
    # 檢查舊格式
    elif 'GCP_SERVICE_ACCOUNT_JSON' in st.secrets:
        st.warning("⚠️ 找到 `GCP_SERVICE_ACCOUNT_JSON` (舊格式)")
        st.info("建議更新為新格式 `[gcp_service_account]`")
        
        # 顯示 JSON 長度
        json_str = st.secrets['GCP_SERVICE_ACCOUNT_JSON']
        st.write(f"JSON 長度: {len(json_str)} 字元")
        
        # 嘗試解析
        import json
        try:
            parsed = json.loads(json_str)
            st.success(f"✅ JSON 格式正確，包含 {len(parsed)} 個欄位")
        except Exception as e:
            st.error(f"❌ JSON 格式錯誤: {e}")
    
    else:
        st.error("❌ 找不到 Google Drive 設定")
        st.write("需要以下任一設定：")
        st.code("""
# 新格式（推薦）
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key = "..."
client_email = "..."
...

# 或舊格式
GCP_SERVICE_ACCOUNT_JSON = '''
{
  "type": "service_account",
  ...
}
'''
        """)

if __name__ == "__main__":
    render_secrets_check_page()

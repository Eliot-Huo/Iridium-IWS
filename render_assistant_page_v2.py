"""
新版 render_assistant_page 函數
包含財務核准流程
"""

def render_assistant_page_v2(store: RequestStore, gateway):
    """
    渲染助理頁面（新版 - 包含財務核准流程）
    
    兩個主要功能：
    1. 待核准請求 - 顯示客戶提交的請求，助理確認後提交給 IWS
    2. 已提交請求 - 顯示正在處理和已完成的請求
    """
    
    st.title("👨‍💼 助理工作台")
    
    # 頂部資訊
    st.markdown(f"**目前時間**: {get_current_taipei_time()} (台灣時間)")
    
    # 標籤頁
    tab1, tab2 = st.tabs(["📋 待核准請求", "🔍 已提交請求追蹤"])
    
    # ========== 標籤1：待核准請求 ==========
    with tab1:
        st.subheader("📋 待核准的服務請求")
        st.info("客戶提交的請求會顯示在此處，請確認後提交給 Iridium")
        
        # 獲取待核准請求
        all_requests = store.get_all()
        pending_approval = [r for r in all_requests if r['status'] == 'PENDING_APPROVAL']
        
        if not pending_approval:
            st.success("✅ 目前沒有待核准的請求")
        else:
            st.warning(f"⚠️ 有 {len(pending_approval)} 個請求等待核准")
            
            # 顯示每個待核准請求
            for idx, req_dict in enumerate(pending_approval):
                with st.container():
                    st.markdown(f"### 請求 #{idx + 1}")
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**客戶編號**: {req_dict['customer_id']}")
                        st.write(f"**客戶名稱**: {req_dict['customer_name']}")
                        st.write(f"**IMEI**: {req_dict['imei']}")
                    
                    with col2:
                        operation_text = get_operation_text(req_dict['operation'])
                        st.write(f"**需求類型**: {operation_text}")
                        
                        if req_dict['operation'] == 'update_plan':
                            plan_text = {
                                '763925991': 'SBD 0',
                                '763924583': 'SBD 12',
                                '763927911': 'SBD 17',
                                '763925351': 'SBD 30'
                            }.get(req_dict.get('new_plan_id', ''), req_dict.get('new_plan_id', 'N/A'))
                            st.write(f"**新資費方案**: {plan_text}")
                        
                        if req_dict.get('reason'):
                            st.write(f"**原因**: {req_dict['reason']}")
                        
                        submit_time = utc_to_taipei(req_dict['created_at'])
                        st.write(f"**提交時間**: {submit_time}")
                    
                    with col3:
                        # 確認提交按鈕
                        if st.button(
                            "✅ 確認提交給 IWS",
                            key=f"approve_{req_dict['request_id']}",
                            type="primary",
                            use_container_width=True
                        ):
                            try:
                                with st.spinner("正在提交給 Iridium..."):
                                    result = approve_and_submit_to_iws(
                                        gateway=gateway,
                                        store=store,
                                        request_id=req_dict['request_id'],
                                        assistant_name='assistant001'
                                    )
                                
                                st.success(result['message'])
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"❌ 提交失敗: {str(e)}")
                    
                    st.markdown("---")
    
    # ========== 標籤2：已提交請求追蹤 ==========
    with tab2:
        st.subheader("🔍 已提交請求狀態追蹤")
        st.caption("顯示已提交給 Iridium 的請求及其狀態")
        
        # 統計卡片
        submitted_requests = [r for r in all_requests if r['status'] != 'PENDING_APPROVAL']
        pending_requests = [r for r in submitted_requests if r['status'] in ['SUBMITTED', 'PENDING', 'WORKING']]
        completed = [r for r in submitted_requests if r['status'] == 'DONE']
        failed = [r for r in submitted_requests if r['status'] == 'ERROR']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("總已提交", len(submitted_requests))
        
        with col2:
            st.metric("處理中", len(pending_requests))
        
        with col3:
            st.metric("已完成", len(completed))
        
        with col4:
            st.metric("失敗", len(failed))
        
        st.markdown("---")
        
        # 篩選器
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            filter_status = st.multiselect(
                "篩選狀態",
                options=['SUBMITTED', 'PENDING', 'WORKING', 'DONE', 'ERROR'],
                default=['SUBMITTED', 'PENDING', 'WORKING']
            )
        
        with col2:
            filter_operation = st.multiselect(
                "篩選操作",
                options=['resume', 'suspend', 'deactivate', 'update_plan'],
                format_func=get_operation_text
            )
        
        with col3:
            search_customer = st.text_input("搜尋客戶編號或名稱")
        
        # 應用篩選
        filtered = submitted_requests
        
        if filter_status:
            filtered = [r for r in filtered if r['status'] in filter_status]
        
        if filter_operation:
            filtered = [r for r in filtered if r['operation'] in filter_operation]
        
        if search_customer:
            filtered = [r for r in filtered if 
                       search_customer.lower() in r['customer_id'].lower() or
                       search_customer.lower() in r['customer_name'].lower()]
        
        # 顯示請求
        if not filtered:
            st.info("無符合條件的請求")
        else:
            st.markdown(f"### 找到 {len(filtered)} 個請求")
            
            for req_dict in filtered:
                with st.expander(
                    f"📋 {req_dict['customer_id']} - {req_dict['customer_name']} | "
                    f"{get_operation_text(req_dict['operation'])} | "
                    f"狀態: {req_dict['status']}"
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**請求ID**: {req_dict['request_id']}")
                        st.write(f"**客戶編號**: {req_dict['customer_id']}")
                        st.write(f"**客戶名稱**: {req_dict['customer_name']}")
                        st.write(f"**IMEI**: {req_dict['imei']}")
                        st.write(f"**操作**: {get_operation_text(req_dict['operation'])}")
                    
                    with col2:
                        # 狀態顯示
                        status_emoji = {
                            'SUBMITTED': '📤',
                            'PENDING': '🔄',
                            'WORKING': '⚙️',
                            'DONE': '✅',
                            'ERROR': '❌'
                        }.get(req_dict['status'], '❓')
                        
                        st.write(f"**狀態**: {status_emoji} {req_dict['status']}")
                        
                        # 時間資訊
                        if req_dict.get('created_at'):
                            st.write(f"**提交時間**: {utc_to_taipei(req_dict['created_at'])}")
                        
                        if req_dict.get('completed_at'):
                            st.write(f"**完成時間**: {utc_to_taipei(req_dict['completed_at'])}")
                        
                        # Transaction ID
                        if req_dict.get('transaction_id'):
                            st.write(f"**Transaction ID**: `{req_dict['transaction_id']}`")
                    
                    # 額外資訊
                    if req_dict.get('plan_name'):
                        st.info(f"📋 資費方案: {req_dict['plan_name']}")
                    
                    if req_dict.get('error_message'):
                        st.error(f"❌ 錯誤: {req_dict['error_message']}")

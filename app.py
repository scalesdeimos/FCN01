import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import urllib.parse
from datetime import datetime, date

st.set_page_config(page_title="FCN 營業員總控與客戶管理系統", page_icon="📈", layout="wide")

# --- 1. 支援 URL 參數 ---
query_params = st.query_params
target_client = query_params.get("client", None)

# 初始化 Session State 測試資料
if "portfolios" not in st.session_state:
    st.session_state.portfolios = {
        "client_a": {
            "name": "林美玲",
            "data": pd.DataFrame([
                {
                    "條件/專案編號": "部位 1 (科技股籃子)", 
                    "投入本金(USD)": 150000.0, "年利率(%)": 10.17, 
                    "合約起始日": "2026-07-01", "合約到期日": "2027-03-01",
                    "標的1": "NVDA", "期初價1": 224.58, "履約價1": 173.12, "下限價1": 143.84,
                    "標的2": "", "期初價2": 0.0, "履約價2": 0.0, "下限價2": 0.0,
                    "標的3": "", "期初價3": 0.0, "履約價3": 0.0, "下限價3": 0.0,
                    "標的4": "", "期初價4": 0.0, "履約價4": 0.0, "下限價4": 0.0,
                    "標的5": "", "期初價5": 0.0, "履約價5": 0.0, "下限價5": 0.0
                }
            ])
        },
        "client_b": {
            "name": "陳大通",
            "data": pd.DataFrame([
                {
                    "條件/專案編號": "部位 2 (權值股籃子)", 
                    "投入本金(USD)": 200000.0, "年利率(%)": 9.5, 
                    "合約起始日": "2026-06-01", "合約到期日": "2027-02-01",
                    "標的1": "AAPL", "期初價1": 220.0, "履約價1": 165.0, "下限價1": 132.0,
                    "標的2": "", "期初價2": 0.0, "履約價2": 0.0, "下限價2": 0.0,
                    "標的3": "", "期初價3": 0.0, "履約價3": 0.0, "下限價3": 0.0,
                    "標的4": "", "期初價4": 0.0, "履約價4": 0.0, "下限價4": 0.0,
                    "標的5": "", "期初價5": 0.0, "履約價5": 0.0, "下限價5": 0.0
                }
            ])
        }
    }

if "is_editing" not in st.session_state:
    st.session_state.is_editing = False

if "preview_client_id" not in st.session_state:
    st.session_state.preview_client_id = None


# 股票中英文對照字典
TICKER_CHINESE_MAP = {
    "NVDA": "輝達",
    "AAPL": "蘋果",
    "MSFT": "微軟",
    "TSM": "台積電",
    "TSMC": "台積電",
    "QQQ": "那斯達克",
    "SPY": "標普500",
    "GOOGL": "谷歌",
    "AMZN": "亞馬遜",
    "META": "Meta",
    "TSLA": "特斯拉"
}

def get_chinese_name(ticker):
    return TICKER_CHINESE_MAP.get(ticker.upper(), ticker)


# --- 2. 核心客戶畫面渲染函數 ---
def render_client_view(client_id):
    client_p = st.session_state.portfolios[client_id]
    
    st.title(f"📊 FCN 尊榮客戶專屬即時回報系統")
    st.markdown(f"**尊榮客戶：{client_p['name']}** | 歡迎隨時掌握您的結構型商品部位與市場動態。")
    st.markdown("---")
    
    df_data = client_p["data"]
    
    total_inv = df_data["投入本金(USD)"].sum() if "投入本金(USD)" in df_data.columns else 0
    total_monthly_coupon = 0
    for _, row in df_data.iterrows():
        p_inv = float(row.get("投入本金(USD)", 0) or 0)
        p_rate = float(row.get("年利率(%)", 0) or 0)
        total_monthly_coupon += p_inv * (p_rate / 100.0 / 12.0)

    all_positions = []
    tickers_to_fetch = set()
    for _, row in df_data.iterrows():
        proj_name = row.get("條件/專案編號", "未命名部位")
        start_date = row.get("合約起始日", "2026-01-01")
        end_date = row.get("合約到期日", "2027-01-01")
        
        for i in range(1, 6):
            t = row.get(f"標的{i}")
            if t and str(t).strip():
                clean_t = str(t).strip().upper()
                tickers_to_fetch.add(clean_t)
                all_positions.append({
                    "部位名稱": proj_name,
                    "合約起始日": start_date,
                    "合約到期日": end_date,
                    "標的代號": clean_t,
                    "期初價": float(row.get(f"期初價{i}", 0) or 0),
                    "履約價": float(row.get(f"履約價{i}", 0) or 0),
                    "下限價": float(row.get(f"下限價{i}", 0) or 0)
                })

    @st.cache_data(ttl=60)
    def get_client_live_prices(t_list):
        p_dict = {}
        for t in t_list:
            try:
                stock = yf.Ticker(t)
                hist = stock.history(period="5d")
                p_dict[t] = round(hist['Close'].iloc[-1], 2) if not hist.empty else 0
            except:
                p_dict[t] = 0
        return p_dict

    live_prices = get_client_live_prices(tuple(tickers_to_fetch))

    normal_count = 0
    warning_count = 0
    for item in all_positions:
        t = item["標的代號"]
        barrier = item["下限價"]
        curr_p = live_prices.get(t, 0)
        if curr_p > 0 and barrier > 0:
            if curr_p <= barrier:
                warning_count += 1
            else:
                normal_count += 1
        else:
            normal_count += 1

    col_v1, col_v2, col_v3, col_v4 = st.columns(4)
    col_v1.metric("當前受託總額", f"${total_inv:,.2f} USD")
    col_v2.metric("預計每月派息總額", f"${total_monthly_coupon:,.2f} USD")
    col_v3.metric("🟢 正常部位數", f"{normal_count} 檔")
    col_v4.metric("⚠️ 警戒部位數 (🟡/🔴)", f"{warning_count} 檔")

    st.markdown("---")

    if all_positions:
        pos_names = list(set([p["部位名稱"] for p in all_positions]))
        selected_pos_name = st.selectbox("📂 請選擇您要檢視的部位專案：", options=pos_names, key=f"sel_pos_{client_id}")
        
        selected_pos_items = [p for p in all_positions if p["部位名稱"] == selected_pos_name]
        
        st.markdown(f"### 📍 目前檢視部位：`{selected_pos_name}` (合約區間: {selected_pos_items[0]['合約起始日']} ~ {selected_pos_items[0]['合約到期日']})")
        
        target_tickers = [item["標的代號"] for item in selected_pos_items]
        chosen_ticker = st.radio("選擇該部位中的標的查看詳細數據：", options=target_tickers, horizontal=True, key=f"sel_tick_{client_id}")
        
        item_data = next((item for item in selected_pos_items if item["標的代號"] == chosen_ticker), None)
        
        if item_data:
            cn_name = get_chinese_name(chosen_ticker)
            
            @st.cache_data(ttl=60)
            def get_ticker_history_from_start(ticker, start_d):
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(start=start_d)
                    latest_p = round(hist['Close'].iloc[-1], 2) if not hist.empty else 0
                    prev_p = round(hist['Close'].iloc[-2], 2) if len(hist) > 1 else latest_p
                    pct_change = round(((latest_p / prev_p) - 1) * 100, 2)
                    return latest_p, pct_change, hist
                except:
                    return 0, 0, pd.DataFrame()

            curr_p, pct_chg, hist_df = get_ticker_history_from_start(chosen_ticker, item_data["合約起始日"])
            
            strike = item_data["履約價"]
            barrier = item_data["下限價"]
            
            dist_strike = round(((curr_p / strike) - 1) * 100, 2) if strike > 0 else 0
            dist_barrier = round(((curr_p / barrier) - 1) * 100, 2) if barrier > 0 else 0

            st.markdown(f"## 標的：{cn_name} ({chosen_ticker})")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("最新收盤價", f"${curr_p:,.2f}", delta=f"{pct_chg}%")
            with c2:
                st.metric(f"距履約價 ({strike})", f"${strike:,.2f}", delta=f"{dist_strike:+}% 空間")
            with c3:
                st.metric(f"距 KI 下限 ({barrier})", f"${barrier:,.2f}", delta=f"{dist_barrier:+}% 空間", delta_color="inverse")

            st.markdown("---")

            st.subheader(f"📈 {cn_name} ({chosen_ticker}) 合約區間走勢與門檻對照圖 ({item_data['合約起始日']} 起)")
            if not hist_df.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['Close'], mode='lines+markers', name=f'{chosen_ticker} 股價', line=dict(color='#1f77b4', width=3)))
                
                fig.add_hline(y=item_data["期初價"], line_dash="dash", line_color="orange", annotation_text=f"期初價: {item_data['期初價']}")
                fig.add_hline(y=strike, line_dash="dash", line_color="green", annotation_text=f"履約價: {strike}")
                fig.add_hline(y=barrier, line_dash="dot", line_color="red", annotation_text=f"KI下限價: {barrier}")

                fig.update_layout(
                    xaxis_title="日期 (合約觀察期)",
                    yaxis_title="價格 (USD)",
                    height=450,
                    margin=dict(l=20, r=20, t=30, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("目前無法取得自合約起始日起的歷史走勢資料。")

            st.markdown("---")

            # --- 修正後的各大主流財經媒體正確搜尋連結 ---
            st.subheader(f"📰 {cn_name} ({chosen_ticker}) 最新相關新聞與外部連結")
            st.markdown(f"點擊下方各大主流財經媒體按鈕，系統將自動以 **【{cn_name}】** 為您導向各大媒體的官方即時搜尋頁面：")
            
            search_keyword = urllib.parse.quote(cn_name)
            encoded_ticker = urllib.parse.quote(chosen_ticker)
            
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                # Yahoo 新聞搜尋
                st.link_button(f"🟣 前往 Yahoo 新聞查看 {cn_name}", f"https://tw.news.yahoo.com/search?p={search_keyword}", use_container_width=True)
                # 鉅亨網正確搜尋
                st.link_button(f"📈 前往 鉅亨網新聞查看 {cn_name}", f"https://news.cnyes.com/news/cat/headline?keyword={search_keyword}", use_container_width=True)
            with col_n2:
                # 風傳媒正確搜尋
                st.link_button(f"🌪️ 前往 風傳媒查看 {cn_name}", f"https://www.storm.mg/search?q={search_keyword}", use_container_width=True)
                # 經濟日報正確搜尋（改用其最新財經頻道或 Google 站內搜尋導向）
                st.link_button(f"📰 前往 經濟日報查看 {cn_name}", f"https://money.udn.com/search/word/1/{search_keyword}", use_container_width=True)
                
    else:
        st.info("目前此帳號尚無設定任何部位。")


# --- 3. 判斷是否為客戶端專屬連結進入 ---
if target_client and target_client in st.session_state.portfolios:
    render_client_view(target_client)
    st.stop()


# --- 4. 營業員總控管理後台 ---
st.sidebar.header("🔐 營業員總控管理後台")
st.sidebar.success("目前處於【後台管理模式】")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ 部位篩選與管理")

selected_c_id = st.sidebar.selectbox(
    "選擇要管理的客戶：", 
    options=list(st.session_state.portfolios.keys()), 
    format_func=lambda x: f"{x} ({st.session_state.portfolios[x]['name']})"
)

status_filter = st.sidebar.selectbox(
    "部位狀態篩選：",
    options=["全部狀態", "🟢 正常運作中", "🟡 低於履約價", "🔴 已跌破 KI"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("➕ 快速新增客戶")
with st.sidebar.form("add_client_simple_form", clear_on_submit=True):
    new_account_id = st.text_input("請輸入客戶帳號 (例如: client_c)")
    submit_new = st.form_submit_button("新增客戶")
    if submit_new and new_account_id:
        clean_id = new_account_id.strip()
        if clean_id not in st.session_state.portfolios:
            st.session_state.portfolios[clean_id] = {
                "name": f"客戶 {clean_id}",
                "data": pd.DataFrame([
                    {
                        "條件/專案編號": "部位 1", 
                        "投入本金(USD)": 100000.0, "年利率(%)": 10.0, 
                        "合約起始日": "2026-01-01", "合約到期日": "2026-09-01",
                        "標的1": "NVDA", "期初價1": 224.58, "履約價1": 173.12, "下限價1": 143.84,
                        "標的2": "", "期初價2": 0.0, "履約價2": 0.0, "下限價2": 0.0,
                        "標的3": "", "期初價3": 0.0, "履約價3": 0.0, "下限價3": 0.0,
                        "標的4": "", "期初價4": 0.0, "履約價4": 0.0, "下限價4": 0.0,
                        "標的5": "", "期初價5": 0.0, "履約價5": 0.0, "下限價5": 0.0
                    }
                ])
            }
            st.success(f"成功新增帳號：{clean_id}")
            st.rerun()

st.sidebar.markdown("---")

if selected_c_id and selected_c_id in st.session_state.portfolios:
    current_c = st.session_state.portfolios[selected_c_id]
    
    st.sidebar.markdown(f"**當前管理客戶**：`{selected_c_id} ({current_c['name']})`")
    base_url = "http://localhost:8501/"
    client_share_link = f"{base_url}?client={selected_c_id}"
    st.sidebar.code(client_share_link, language="markdown")

    if st.sidebar.button("🔍 預覽此客戶的專屬網頁畫面", use_container_width=True):
        st.session_state.preview_client_id = selected_c_id
        st.rerun()

    if st.sidebar.button("🗑️ 刪除此客戶檔案", type="primary"):
        if len(st.session_state.portfolios) > 1:
            del st.session_state.portfolios[selected_c_id]
            if st.session_state.preview_client_id == selected_c_id:
                st.session_state.preview_client_id = None
            st.rerun()

    if st.session_state.preview_client_id:
        prev_id = st.session_state.preview_client_id
        st.info(f"👀 目前正在【預覽模式】中，正在檢視客戶 [{prev_id}] 的專屬網頁畫面。")
        if st.button("⬅️ 點此返回營業員管理後台"):
            st.session_state.preview_client_id = None
            st.rerun()
        st.markdown("---")
        render_client_view(prev_id)
        st.stop()

    # --- 主畫面：後台管理與狀態控制 ---
    st.subheader(f"🛠️ 營業員總控管理中：正在檢視客戶 [{selected_c_id}] ({current_c['name']})")

    col_status, col_btn1, col_btn2 = st.columns([2, 1, 1])

    with col_status:
        if st.session_state.is_editing:
            st.warning("⚠️ **目前狀態：【編輯中】請直接在下方表格修改合約起訖日、本金、利率與標的，修改完畢後點擊右側儲存按鈕。**")
        else:
            st.success("🟢 **目前狀態：【檢視中】數據安全鎖定中。如需修改請點擊右側編輯按鈕。**")

    with col_btn1:
        if not st.session_state.is_editing:
            if st.button("✏️ 進入編輯模式", use_container_width=True):
                st.session_state.is_editing = True
                st.rerun()

    with col_btn2:
        if st.session_state.is_editing:
            if st.button("💾 儲存變更", type="primary", use_container_width=True):
                st.session_state.is_editing = False
                st.success("參數已成功儲存！")
                st.rerun()

    st.markdown("---")

    if st.session_state.is_editing:
        current_c["name"] = st.text_input("客戶顯示名稱", value=current_c["name"])
        st.markdown("📋 **合約部位設定（包含合約起訖日、本金、年利率與最多 5 檔橫向標的）：**")
        
        edited_df = st.data_editor(
            current_c["data"], 
            num_rows="dynamic", 
            use_container_width=True, 
            key=f"mgr_table_edit_{selected_c_id}"
        )
        current_c["data"] = edited_df
    else:
        st.markdown(f"**客戶名稱**：{current_c['name']}")
        total_inv_mgr = current_c["data"]["投入本金(USD)"].sum() if "投入本金(USD)" in current_c["data"].columns else 0
        st.markdown(f"**總受託本金**：${total_inv_mgr:,.2f} USD")
        st.markdown("📋 **合約部位與橫向標的檢視區 (唯讀)：**")
        st.dataframe(current_c["data"], use_container_width=True)

        if status_filter != "全部狀態":
            st.info(f"🔎 目前已套用部位狀態篩選：【{status_filter}】")
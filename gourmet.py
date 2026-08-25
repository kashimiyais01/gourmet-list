import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client

# ==============================
# 1. 🔑 合言葉（パスワード）機能
# ==============================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 秘密のグルメノート")
    st.info("このページを見るには合言葉が必要です。")
    pwd = st.text_input("合言葉を入力してください", type="password")
    if st.button("ログイン"):
        # 設定した合言葉と一致するかチェック
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("合言葉が違います")
    st.stop()

# ==============================
# 2. ☁️ データベース接続
# ==============================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("🍽️ わたしのグルメノート")

# タブの作成（クラウドでの直接編集は複雑なため、「管理」をシンプルな「削除」に変更しています）
tab_input, tab_view, tab_manage = st.tabs(["✍️ 記録する", "📖 眺める・探す", "🗑️ 削除する"])

PREFECTURES = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]

# ==============================
# 3. 入力タブ
# ==============================
with tab_input:
    with st.form("gourmet_form", clear_on_submit=True):
        st.subheader("お店の情報を入力")
        shop_name = st.text_input("お店の名前 (必須)")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            pref = st.selectbox("都道府県", PREFECTURES, index=9)
        with col2:
            address = st.text_input("市区町村・詳細住所")
            
        menu = st.text_input("食べたメニュー (必須)")
        
        col3, col4 = st.columns(2)
        with col3:
            situation = st.selectbox("シチュエーション", ["いつでも", "ランチ", "ディナー", "モーニング", "デート", "その他"])
        with col4:
            genre = st.selectbox("ジャンル", ["和食", "洋食", "中華", "カフェ", "フレンチ", "ラーメン", "イタリアン", "エスニック", "その他"])
            
        notes = st.text_area("備考 (任意)")
        photo = st.file_uploader("写真のアップロード (任意)", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("この内容で保存する")
        
        if submitted:
            if shop_name and menu:
                image_url = ""
                # 写真がある場合はSupabaseにアップロード
                if photo is not None:
                    file_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{photo.name}"
                    file_bytes = photo.getvalue()
                    # ストレージへ保存
                    supabase.storage.from_("gourmet_images").upload(file_name, file_bytes)
                    # 公開用URLの取得
                    image_url = supabase.storage.from_("gourmet_images").get_public_url(file_name)
                
                # データベースにテキストデータを保存
                data = {
                    "shop_name": shop_name,
                    "prefecture": pref,
                    "address": address,
                    "menu": menu,
                    "situation": situation,
                    "genre": genre,
                    "notes": notes,
                    "image_url": image_url
                }
                supabase.table("gourmet_notes").insert(data).execute()
                st.success(f"「{shop_name}」の記録を保存しました！")
            else:
                st.error("お店の名前と食べたメニューは必須です。")

# ==============================
# 4. 閲覧・検索タブ
# ==============================
with tab_view:
    st.subheader("記録の検索と閲覧")
    # DBからデータを取得
    response = supabase.table("gourmet_notes").select("*").order("created_at", desc=True).execute()
    
    if not response.data:
        st.info("まだ記録がありません。")
    else:
        df_view = pd.DataFrame(response.data)
        
        with st.expander("🔍 絞り込み検索", expanded=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                pref_options = ["すべて"] + list(df_view["prefecture"].unique())
                selected_pref = st.selectbox("都道府県", pref_options)
            with col_f2:
                genre_options = ["すべて"] + list(df_view["genre"].unique())
                selected_genre = st.selectbox("ジャンル", genre_options)
            with col_f3:
                keyword = st.text_input("キーワード検索", "")

        # 絞り込み処理
        if selected_pref != "すべて":
            df_view = df_view[df_view["prefecture"] == selected_pref]
        if selected_genre != "すべて":
            df_view = df_view[df_view["genre"] == selected_genre]
        if keyword:
            # 複数列を対象に検索（欠損値は無視）
            df_view = df_view[
                df_view["shop_name"].fillna("").str.contains(keyword) | 
                df_view["menu"].fillna("").str.contains(keyword) |
                df_view["notes"].fillna("").str.contains(keyword)
            ]

        st.markdown(f"**該当件数: {len(df_view)} 件**")
        st.divider()

        for idx, row in df_view.iterrows():
            with st.container():
                st.markdown(f"### {row['shop_name']}")
                date_str = str(row['created_at'])[:10] # 日付だけを抽出
                st.caption(f"📍 {row['prefecture']} {row.get('address', '')} ｜ 🕒 {date_str}")
                
                col_img, col_info = st.columns([1, 1])
                with col_img:
                    if row.get('image_url'):
                        st.image(row['image_url'], use_container_width=True)
                    else:
                        st.markdown("*画像なし*")
                
                with col_info:
                    st.markdown(f"**🍴 メニュー:** {row['menu']}")
                    st.markdown(f"**🔖 ジャンル:** {row['genre']}")
                    st.markdown(f"**シーン:** {row['situation']}")
                    if row.get('notes'):
                        st.markdown(f"**📝 備考:**\n{row['notes']}")
                st.divider()

# ==============================
# 5. 削除管理タブ
# ==============================
with tab_manage:
    st.subheader("記録の削除")
    response_del = supabase.table("gourmet_notes").select("id, shop_name, menu").order("created_at", desc=True).execute()
    
    if not response_del.data:
        st.warning("削除できる記録がありません。")
    else:
        df_del = pd.DataFrame(response_del.data)
        # ドロップダウンで消したいお店を選ぶ方式
        options = df_del.apply(lambda r: f"{r['shop_name']} ({r['menu']}) [ID:{r['id']}]", axis=1).tolist()
        selected_to_delete = st.selectbox("削除する記録を選んでください", options)
        
        if st.button("🚨 この記録を完全に削除する"):
            # 選んだ文字列からID部分だけを抜き出して削除
            target_id = selected_to_delete.split("[ID:")[-1].replace("]", "")
            supabase.table("gourmet_notes").delete().eq("id", target_id).execute()
            st.success("記録を削除しました！")
            st.rerun()

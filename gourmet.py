import streamlit as st
import pandas as pd
import datetime
import io
from supabase import create_client, Client
from PIL import Image
from pillow_heif import register_heif_opener

# HEIC画像を読み込めるようにするおまじない
register_heif_opener()

# ==============================
# 1. 🔑 合言葉（パスワード）機能
# ==============================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 すちゃグルメノート")
    st.info("このページを見るには合言葉が必要です。")
    pwd = st.text_input("合言葉を入力してください", type="password")
    if st.button("ログイン"):
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

st.title("🍽️ すちゃグルメノート")

# 💡 タブの名前を変更しました
tab_input, tab_view, tab_manage = st.tabs(["✍️ 記録する", "📖 眺める・探す", "🛠️ 編集・削除する"])

PREFECTURES = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
SITUATIONS = ["いつでも", "ランチ", "ディナー", "モーニング", "デート", "その他"]
GENRES = ["和食", "洋食", "中華", "カフェ", "フレンチ", "ラーメン", "イタリアン", "エスニック", "その他"]

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
            situation = st.selectbox("シチュエーション", SITUATIONS)
        with col4:
            genre = st.selectbox("ジャンル", GENRES)
            
        notes = st.text_area("備考 (任意)")
        photo = st.file_uploader("写真のアップロード (任意)", type=["jpg", "jpeg", "png", "heic", "HEIC"])
        submitted = st.form_submit_button("この内容で保存する")
        
        if submitted:
            if shop_name and menu:
                image_url = ""
                if photo is not None:
                    file_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{photo.name}"
                    
                    if photo.name.lower().endswith(".heic"):
                        image = Image.open(photo)
                        img_byte_arr = io.BytesIO()
                        image.convert('RGB').save(img_byte_arr, format='JPEG')
                        file_bytes = img_byte_arr.getvalue()
                        file_name = file_name.rsplit('.', 1)[0] + ".jpeg"
                    else:
                        file_bytes = photo.getvalue()
                    
                    supabase.storage.from_("gourmet_images").upload(file_name, file_bytes)
                    image_url = supabase.storage.from_("gourmet_images").get_public_url(file_name)
                
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

        if selected_pref != "すべて":
            df_view = df_view[df_view["prefecture"] == selected_pref]
        if selected_genre != "すべて":
            df_view = df_view[df_view["genre"] == selected_genre]
        if keyword:
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
                date_str = str(row['created_at'])[:10]
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
# 5. 編集・削除管理タブ（💡ここを大幅に改修しました）
# ==============================
with tab_manage:
    st.subheader("記録の編集・削除")
    response_manage = supabase.table("gourmet_notes").select("*").order("created_at", desc=True).execute()
    
    if not response_manage.data:
        st.warning("操作できる記録がありません。")
    else:
        df_manage = pd.DataFrame(response_manage.data)
        
        # 1. どのお店の記録を操作するか選ぶ
        options = df_manage.apply(lambda r: f"{r['shop_name']} ({r['menu']}) [ID:{r['id']}]", axis=1).tolist()
        selected_item = st.selectbox("操作したい記録を選んでください", options)
        
        # 選んだ文字列からID部分だけを抜き出して、そのお店のデータを取得する
        target_id = selected_item.split("[ID:")[-1].replace("]", "")
        target_data = df_manage[df_manage["id"] == target_id].iloc[0]
        
        # 2. 編集するか削除するかを選ぶ
        action = st.radio("操作を選んでください", ["✏️ 内容を修正する", "🚨 完全に削除する"], horizontal=True)
        
        # --- 編集モード ---
        if action == "✏️ 内容を修正する":
            with st.form("edit_form"):
                st.info("修正したい項目を書き換えてください。（※写真はそのまま引き継がれます）")
                
                new_shop_name = st.text_input("お店の名前", value=target_data["shop_name"])
                
                col_e1, col_e2 = st.columns([1, 2])
                with col_e1:
                    pref_idx = PREFECTURES.index(target_data["prefecture"]) if target_data["prefecture"] in PREFECTURES else 9
                    new_pref = st.selectbox("都道府県を修正", PREFECTURES, index=pref_idx)
                with col_e2:
                    new_address = st.text_input("市区町村・詳細住所を修正", value=target_data.get("address", ""))
                    
                new_menu = st.text_input("食べたメニュー", value=target_data["menu"])
                
                col_e3, col_e4 = st.columns(2)
                with col_e3:
                    sit_idx = SITUATIONS.index(target_data["situation"]) if target_data.get("situation") in SITUATIONS else 0
                    new_situation = st.selectbox("シチュエーションを修正", SITUATIONS, index=sit_idx)
                with col_e4:
                    gen_idx = GENRES.index(target_data["genre"]) if target_data.get("genre") in GENRES else 0
                    new_genre = st.selectbox("ジャンルを修正", GENRES, index=gen_idx)
                    
                new_notes = st.text_area("備考を修正", value=target_data.get("notes", ""))
                
                update_submitted = st.form_submit_button("この内容で上書き保存する")
                
                if update_submitted:
                    if new_shop_name and new_menu:
                        update_data = {
                            "shop_name": new_shop_name,
                            "prefecture": new_pref,
                            "address": new_address,
                            "menu": new_menu,
                            "situation": new_situation,
                            "genre": new_genre,
                            "notes": new_notes
                        }
                        supabase.table("gourmet_notes").update(update_data).eq("id", target_id).execute()
                        st.success("記録を修正しました！")
                        st.rerun()
                    else:
                        st.error("お店の名前と食べたメニューは必須です。")
                        
        # --- 削除モード ---
        elif action == "🚨 完全に削除する":
            st.warning(f"「{target_data['shop_name']}」の記録を削除します。元には戻せません。")
            if st.button("🚨 本当に削除する"):
                supabase.table("gourmet_notes").delete().eq("id", target_id).execute()
                st.success("記録を削除しました！")
                st.rerun()

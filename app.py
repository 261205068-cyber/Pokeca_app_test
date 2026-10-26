import io
import pandas as pd
import Streamlit as st

# ---------------------------------------------------------
# ページ基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="ポケカ 大会勝率分析ツール (多デッキ対応)",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------
# UIカスタムCSS (直感的で快適なデスクトップUI風デザイン)
# ---------------------------------------------------------
st.markdown(
    """
<style>
    /* メイン背景 */
    .stApp {
        background-color: #f0f2f5;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* テキストスタイル */
    h1, h2, h3, h4, label, p, span {
        color: #1e293b !important;
    }
    
    /* カード条件コンテナ (白背景・シャープな枠線) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    
    /* ボタンデザイン */
    .stButton > button {
        background-color: #ffffff;
        color: #334155;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 4px 12px;
        font-size: 13px;
        font-weight: 500;
        transition: all 0.15s ease-in-out;
    }
    .stButton > button:hover {
        background-color: #f1f5f9;
        border-color: #94a3b8;
        color: #0f172a;
    }
    
    /* データフレーム表 */
    .stDataFrame {
        border: 1px solid #cbd5e1;
        background-color: #ffffff;
        border-radius: 4px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# セッション状態の初期化 (高速・スムーズな追加削除を実現)
# ---------------------------------------------------------
if "conditions_a" not in st.session_state:
    st.session_state.conditions_a = [
        {"card": "Crushing Hammer (クラッシュハンマー)", "type": "採用", "count": 1}
    ]

if "conditions_b" not in st.session_state:
    st.session_state.conditions_b = [
        {"card": "Crushing Hammer (クラッシュハンマー)", "type": "不採用", "count": 1}
    ]

# ---------------------------------------------------------
# 大会対戦データベース (複数自分デッキ・多対面データ対応)
# ---------------------------------------------------------
@st.cache_data
def load_match_database():
    import random
    tournaments = ["Baltimore", "Brisbane", "Frankfurt", "Recife", "Louisville"]
    
    my_decks_list = [
        "Dragapult (ドラパルト / ドラパルト単体)",
        "Charizard ex (リザードンex)",
        "Gardevoir ex (サーナイトex)",
        "Lugia VSTAR (ルギアVSTAR)",
        "Raging Bolt ex (タケルライコex)",
        "Regidrago VSTAR (レジドラゴVSTAR)"
    ]
    
    opponents = [
        "Dragapult", "Basic Box", "N's Zoroark", "Slowking", "Dragapult Dusknoir",
        "Alakazam Dudunsparce", "Dragapult Blaziken", "Mega Excadrill", "Crustle",
        "Dhelmise", "Festival Lead", "Ogerpon Meganium Hydrapple", "Lucario Hariyama",
        "Lopunny Dudunsparce", "Alakazam Dusknoir", "Sharpedo Toxtricity",
        "Rocket's Honchkrow", "Lopunny Dusknoir", "Cynthia's Garchomp", "Mega Lucario",
        "Grimmsnarl Froslass"
    ]
    
    all_cards = [
        "Crushing Hammer (クラッシュハンマー)",
        "Unfair Stamp (アンフェアスタンプ)",
        "Counter Catcher (カウンターキャッチャー)",
        "Buddy-Buddy Poffin (なかよしポフィン)",
        "Prime Catcher (プライムキャッチャー)",
        "Earthen Vessel (大地の器)",
        "Boss's Orders (ボスの指令)"
    ]
    
    records = []
    for i in range(5000):
        t = random.choice(tournaments)
        m_deck = random.choice(my_decks_list)
        opp = random.choice(opponents)
        res = random.choices(["win", "loss", "tie"], weights=[0.53, 0.40, 0.07])[0]
        
        # ランダムにカードを採用させる
        chosen_cards = random.sample(all_cards, k=random.randint(2, 5))
        
        records.append({
            "tournament": t,
            "player": f"Player_{i%200}",
            "my_deck": m_deck,
            "cards": chosen_cards,
            "opponent_deck": opp,
            "result": res
        })
    return pd.DataFrame(records)

df_data = load_match_database()

# ---------------------------------------------------------
# 上部フィルターエリア (対象)
# ---------------------------------------------------------
st.markdown("**対象**")

col_t1, col_t2 = st.columns([1.5, 3])

with col_t1:
    all_tournaments = ["Baltimore", "Brisbane", "Frankfurt", "Recife", "Louisville"]
    selected_tournaments = st.multiselect(
        "大会 (複数選択可)",
        options=all_tournaments,
        default=all_tournaments,
        key="tournaments_sel"
    )

with col_t2:
    all_my_decks = sorted(list(df_data["my_deck"].unique()))
    selected_my_deck = st.selectbox(
        "自分のデッキタイプ",
        options=all_my_decks,
        index=0,
        key="my_deck_sel"
    )
    
    all_opps = ["すべて"] + sorted(list(df_data["opponent_deck"].unique()))
    selected_opp_deck = st.selectbox(
        "相手デッキ (対面表を絞る場合)",
        options=all_opps,
        index=0,
        key="opp_deck_sel"
    )
    
    compare_mode = st.checkbox("グループAとBを比較", value=True, key="chk_compare_mode")

# フィルタリング適用
df_filtered = df_data[
    (df_data["tournament"].isin(selected_tournaments)) &
    (df_data["my_deck"] == selected_my_deck)
]
if selected_opp_deck != "すべて":
    df_filtered = df_filtered[df_filtered["opponent_deck"] == selected_opp_deck]

st.markdown("---")

# 選択可能カードリスト
card_options = [
    "Crushing Hammer (クラッシュハンマー)",
    "Unfair Stamp (アンフェアスタンプ)",
    "Counter Catcher (カウンターキャッチャー)",
    "Buddy-Buddy Poffin (なかよしポフィン)",
    "Prime Catcher (プライムキャッチャー)",
    "Earthen Vessel (大地の器)",
    "Boss's Orders (ボスの指令)"
]

# ---------------------------------------------------------
# グループ A / B 条件入力エリア (操作性改善・即時反映)
# ---------------------------------------------------------
col_ga, col_gb = st.columns(2)

# --- グループ A コールバック関数 ---
def delete_cond_a(index):
    st.session_state.conditions_a.pop(index)

def add_cond_a():
    st.session_state.conditions_a.append({"card": card_options[0], "type": "採用", "count": 1})

# --- グループ B コールバック関数 ---
def delete_cond_b(index):
    st.session_state.conditions_b.pop(index)

def add_cond_b():
    st.session_state.conditions_b.append({"card": card_options[0], "type": "不採用", "count": 1})


# --- グループ A 描画 ---
with col_ga:
    with st.container(border=True):
        st.markdown("**グループA**")
        disp_a = st.text_input("結果での表示名", value="採用あり", key="txt_disp_a")
        
        for idx, cond in enumerate(st.session_state.conditions_a):
            ca1, ca2, ca3, ca4 = st.columns([3.5, 1.5, 1, 1])
            with ca1:
                cond["card"] = st.selectbox("", card_options, index=card_options.index(cond["card"]) if cond["card"] in card_options else 0, key=f"ca_card_{idx}")
            with ca2:
                cond["type"] = st.selectbox("", ["採用", "不採用"], index=0 if cond["type"]=="採用" else 1, key=f"ca_type_{idx}")
            with ca3:
                cond["count"] = st.number_input("", min_value=1, value=cond["count"], key=f"ca_cnt_{idx}")
            with ca4:
                st.button("削除", key=f"btn_del_a_{idx}", on_click=delete_cond_a, args=(idx,))
        
        st.button("+ カード条件", key="btn_add_a", on_click=add_cond_a)

# --- グループ B 描画 ---
with col_gb:
    if compare_mode:
        with st.container(border=True):
            st.markdown("**グループB**")
            disp_b = st.text_input("結果での表示名", value="採用なし", key="txt_disp_b")
            
            for idx, cond in enumerate(st.session_state.conditions_b):
                cb1, cb2, cb3, cb4 = st.columns([3.5, 1.5, 1, 1])
                with cb1:
                    cond["card"] = st.selectbox("", card_options, index=card_options.index(cond["card"]) if cond["card"] in card_options else 0, key=f"cb_card_{idx}")
                with cb2:
                    cond["type"] = st.selectbox("", ["不採用", "採用"], index=0 if cond["type"]=="不採用" else 1, key=f"cb_type_{idx}")
                with cb3:
                    cond["count"] = st.number_input("", min_value=1, value=cond["count"], key=f"cb_cnt_{idx}")
                with cb4:
                    st.button("削除", key=f"btn_del_b_{idx}", on_click=delete_cond_b, args=(idx,))
            
            st.button("+ カード条件", key="btn_add_b", on_click=add_cond_b)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 集計ロジック ＆ サマリー表示
# ---------------------------------------------------------
def filter_by_conditions(df, conditions):
    res_df = df.copy()
    for cond in conditions:
        card = cond["card"]
        c_type = cond["type"]
        has_card = res_df["cards"].apply(lambda x: card in x)
        if c_type == "採用":
            res_df = res_df[has_card]
        else:
            res_df = res_df[~has_card]
    return res_df

df_a = filter_by_conditions(df_filtered, st.session_state.conditions_a)
if compare_mode:
    df_b = filter_by_conditions(df_filtered, st.session_state.conditions_b)

def get_stats(df_target):
    decks = df_target["player"].nunique()
    w = len(df_target[df_target["result"] == "win"])
    l = len(df_target[df_target["result"] == "loss"])
    t = len(df_target[df_target["result"] == "tie"])
    matches = w + l
    wr = (w / matches * 100) if matches > 0 else 0.0
    return decks, w, l, t, matches, wr

a_d, a_w, a_l, a_t, a_m, a_wr = get_stats(df_a)

st.caption("集計完了。勝率は勝ち ÷ (勝ち + 負け)、引き分けは除外。")

st.markdown(f"**{disp_a}**: デッキ {a_d:,}件 / {a_w}-{a_l}-{a_t} / 勝敗 {a_m:,}試合 / 勝率 **{a_wr:.2f}%**")

if compare_mode:
    b_d, b_w, b_l, b_t, b_m, b_wr = get_stats(df_b)
    diff = a_wr - b_wr
    st.markdown(f"**{disp_b}**: デッキ {b_d:,}件 / {b_w}-{b_l}-{b_t} / 勝敗 {b_m:,}試合 / 勝率 **{b_wr:.2f}%**")
    st.markdown(f"**全体差 (A-B)** : **{diff:+.2f}ポイント**")

# ---------------------------------------------------------
# 対面別勝率マトリクス生成
# ---------------------------------------------------------
def build_matrix(df_grp_a, df_grp_b=None):
    def agg_opp(df, prefix):
        rows = []
        for opp, group in df.groupby("opponent_deck"):
            w = len(group[group["result"] == "win"])
            l = len(group[group["result"] == "loss"])
            t = len(group[group["result"] == "tie"])
            tot = w + l
            wr = (w / tot * 100) if tot > 0 else 0.0
            rows.append({
                "相手デッキ": opp,
                f"{prefix} 勝-敗-分": f"{w}-{l}-{t}",
                f"{prefix} 試合数": tot,
                f"{prefix} 勝率": wr
            })
        return pd.DataFrame(rows)

    res_a = agg_opp(df_grp_a, "A")
    
    if df_grp_b is not None:
        res_b = agg_opp(df_grp_b, "B")
        merged = pd.merge(res_a, res_b, on="相手デッキ", how="outer").fillna(0)
        
        merged["差 (A-B)"] = merged["A 勝率"] - merged["B 勝率"]
        
        merged["A 勝率"] = merged["A 勝率"].map(lambda x: f"{x:.2f}%")
        merged["B 勝率"] = merged["B 勝率"].map(lambda x: f"{x:.2f}%")
        merged["差 (A-B)"] = merged["差 (A-B)"].map(lambda x: f"{x:+.2f}pt")
        
        cols = ["相手デッキ", "A 勝-敗-分", "A 試合数", "A 勝率", "B 勝-敗-分", "B 試合数", "B 勝率", "差 (A-B)"]
        return merged[cols]
    else:
        res_a["A 勝率"] = res_a["A 勝率"].map(lambda x: f"{x:.2f}%")
        return res_a

df_out = build_matrix(df_a, df_b if compare_mode else None)

# ---------------------------------------------------------
# テーブル＆CSVダウンロードボタン
# ---------------------------------------------------------
c_btn1, c_btn2, c_space = st.columns([1, 1.8, 5])
with c_btn1:
    st.button("集計", key="btn_execute_dummy")

csv_bytes = df_out.to_csv(index=False).encode('utf-8-sig')

with c_btn2:
    st.download_button(
        label="CSVを書き出す",
        data=csv_bytes,
        file_name="regional_winrate_analysis.csv",
        mime="text/csv",
        key="dl_csv"
    )

st.dataframe(df_out, use_container_width=True, height=530)

import io
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# ページ基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="ポケカ 大会勝率分析ツール",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------
# 動画・画像通りのUIデザイン (デスクトップアプリ風ライトテーマ)
# ---------------------------------------------------------
st.markdown(
    """
<style>
    /* メイン背景 */
    .stApp {
        background-color: #f0f2f5;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* ヘッダー・テキスト */
    h1, h2, h3, h4, label, p, span {
        color: #212529 !important;
    }
    
    /* グループ枠 (白背景・細線枠) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff;
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    /* ボタンデザイン */
    .stButton > button {
        background-color: #f8f9fa;
        color: #212529;
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 2px 10px;
        font-size: 13px;
        font-weight: 500;
    }
    .stButton > button:hover {
        background-color: #e2e6ea;
        border-color: #dae0e5;
    }
    
    /* 入力フォーム / セレクトボックス */
    div[data-baseweb="select"] > div {
        background-color: #ffffff;
        border-radius: 4px;
        border-color: #ced4da;
    }
    
    /* データフレーム表 */
    .stDataFrame {
        border: 1px solid #ced4da;
        background-color: #ffffff;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# セッション状態の初期化 (動的行追加・削除用)
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
# 模擬大会データの構築 (動画内データに基く)
# ---------------------------------------------------------
@st.cache_data
def load_match_database():
    import random
    tournaments = ["Baltimore", "Brisbane", "Frankfurt", "Recife", "Louisville"]
    opponents = [
        "Dragapult", "Basic Box", "N's Zoroark", "Slowking", "Dragapult Dusknoir",
        "Alakazam Dudunsparce", "Dragapult Blaziken", "Mega Excadrill", "Crustle",
        "Dhelmise", "Festival Lead", "Ogerpon Meganium Hydrapple", "Lucario Hariyama",
        "Lopunny Dudunsparce", "Alakazam Dusknoir", "Sharpedo Toxtricity",
        "Rocket's Honchkrow", "Lopunny Dusknoir", "Cynthia's Garchomp", "Mega Lucario",
        "Grimmsnarl Froslass"
    ]
    
    records = []
    for i in range(2500):
        t = random.choice(tournaments)
        opp = random.choice(opponents)
        res = random.choices(["win", "loss", "tie"], weights=[0.52, 0.40, 0.08])[0]
        has_hammer = random.choice([True, False])
        
        cards = ["Dragapult ex"]
        if has_hammer:
            cards.append("Crushing Hammer (クラッシュハンマー)")
            
        records.append({
            "tournament": t,
            "player": f"Player_{i%150}",
            "my_deck": "Dragapult (ドラパルト / ドラパルト単体)",
            "cards": cards,
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
    selected_my_deck = st.selectbox(
        "自分のデッキタイプ",
        options=["Dragapult (ドラパルト / ドラパルト単体)"],
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

# フィルタリング
df_filtered = df_data[
    (df_data["tournament"].isin(selected_tournaments)) &
    (df_data["my_deck"] == selected_my_deck)
]
if selected_opp_deck != "すべて":
    df_filtered = df_filtered[df_filtered["opponent_deck"] == selected_opp_deck]

st.markdown("---")

# カード選択候補
card_options = [
    "Crushing Hammer (クラッシュハンマー)",
    "Unfair Stamp (アンフェアスタンプ)",
    "Counter Catcher (カウンターキャッチャー)",
    "Buddy-Buddy Poffin (なかよしポフィン)"
]

# ---------------------------------------------------------
# グループ A / B 条件入力エリア (削除・追加が即座に動作)
# ---------------------------------------------------------
col_ga, col_gb = st.columns(2)

# --- グループ A ---
with col_ga:
    with st.container(border=True):
        st.markdown("**グループA**")
        disp_a = st.text_input("結果での表示名", value="採用あり", key="txt_disp_a")
        
        # 条件行の描画と削除制御
        new_cond_a = []
        for idx, cond in enumerate(st.session_state.conditions_a):
            ca1, ca2, ca3, ca4 = st.columns([3, 1.5, 1, 1])
            with ca1:
                card_val = st.selectbox("", card_options, index=0, key=f"ca_card_{idx}")
            with ca2:
                type_val = st.selectbox("", ["採用", "不採用"], index=0 if cond["type"]=="採用" else 1, key=f"ca_type_{idx}")
            with ca3:
                cnt_val = st.number_input("", min_value=1, value=cond["count"], key=f"ca_cnt_{idx}")
            with ca4:
                # 削除ボタン
                if st.button("削除", key=f"btn_del_a_{idx}"):
                    continue  # この行を除外して保持
            
            new_cond_a.append({"card": card_val, "type": type_val, "count": cnt_val})
        
        st.session_state.conditions_a = new_cond_a
        
        # 行追加ボタン
        if st.button("+ カード条件", key="btn_add_a"):
            st.session_state.conditions_a.append({"card": card_options[0], "type": "採用", "count": 1})
            st.rerun()

# --- グループ B ---
with col_gb:
    if compare_mode:
        with st.container(border=True):
            st.markdown("**グループB**")
            disp_b = st.text_input("結果での表示名", value="採用なし", key="txt_disp_b")
            
            new_cond_b = []
            for idx, cond in enumerate(st.session_state.conditions_b):
                cb1, cb2, cb3, cb4 = st.columns([3, 1.5, 1, 1])
                with cb1:
                    card_val = st.selectbox("", card_options, index=0, key=f"cb_card_{idx}")
                with cb2:
                    type_val = st.selectbox("", ["不採用", "採用"], index=0 if cond["type"]=="不採用" else 1, key=f"cb_type_{idx}")
                with cb3:
                    cnt_val = st.number_input("", min_value=1, value=cond["count"], key=f"cb_cnt_{idx}")
                with cb4:
                    if st.button("削除", key=f"btn_del_b_{idx}"):
                        continue
                
                new_cond_b.append({"card": card_val, "type": type_val, "count": cnt_val})
            
            st.session_state.conditions_b = new_cond_b
            
            if st.button("+ カード条件", key="btn_add_b"):
                st.session_state.conditions_b.append({"card": card_options[0], "type": "不採用", "count": 1})
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 集計・CSV出力ボタン ＆ ロジック
# ---------------------------------------------------------
c_btn1, c_btn2, c_info = st.columns([1, 1.5, 5])
with c_btn1:
    do_calc = st.button("集計", key="btn_execute")
with c_btn2:
    # 集計処理用の仮データ作成
    pass

# 条件フィルタリング関数
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

# サマリー集計関数
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
# 対面別マトリクス生成
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
# テーブル出力 ＆ CSV書き出しボタン
# ---------------------------------------------------------
st.dataframe(df_out, use_container_width=True, height=520)

csv_bytes = df_out.to_csv(index=False).encode('utf-8-sig')

with c_btn2:
    st.download_button(
        label="CSVを書き出す",
        data=csv_bytes,
        file_name="regional_analysis.csv",
        mime="text/csv",
        key="dl_csv"
    )

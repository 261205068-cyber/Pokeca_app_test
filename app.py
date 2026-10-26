import io
import json
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# ページ設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="ポケカ Regional勝率アナリティクス (Group A vs B)",
    page_icon="🏆",
    layout="wide",
)

# ---------------------------------------------------------
# UIカスタムCSS (画像のグレー・洗練されたデスクトップUI風デザイン)
# ---------------------------------------------------------
st.markdown(
    """
<style>
    .stApp {
        background-color: #f4f5f7;
        color: #1f2937;
    }
    /* ヘッダー・ラベル等 */
    h1, h2, h3, h4, label {
        color: #1e293b !important;
    }
    /* グループボックス風コンテナ */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    /* ボタンデザイン */
    .stButton > button {
        background-color: #ffffff;
        color: #374151;
        border: 1px solid #9ca3af;
        border-radius: 4px;
        font-weight: 600;
        padding: 4px 12px;
    }
    .stButton > button:hover {
        background-color: #e5e7eb;
        border-color: #6b7280;
        color: #111827;
    }
    /* 主要アクションボタン */
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #2563eb;
        color: #ffffff;
        border: none;
    }
    /* データフレームのスタイル */
    .stDataFrame {
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        background-color: #ffffff;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 大会対戦データの事前サンプル＆データ構築関数
# ※ 本来はLimitless TCGの対戦ログCSV/JSONをロードします
# ---------------------------------------------------------
@st.cache_data
def get_sample_match_data():
    # 誰が / どの大会で / どのデッキで / 誰の何のデッキと戦い / 結果はどうだったか + デッキレシピリスト
    data = [
        {
            "tournament": "Baltimore",
            "player": "Player_A",
            "my_deck": "Dragapult (ドラパルト / ドラパルト単体)",
            "cards": ["Dragapult ex", "Crushing Hammer", "Iono", "Buddy-Buddy Poffin"],
            "opponent_player": "Opponent_1",
            "opponent_deck": "Basic Box",
            "result": "win" # win, loss, tie
        },
        {
            "tournament": "Baltimore",
            "player": "Player_B",
            "my_deck": "Dragapult (ドラパルト / ドラパルト単体)",
            "cards": ["Dragapult ex", "Iono", "Buddy-Buddy Poffin"],
            "opponent_player": "Opponent_2",
            "opponent_deck": "Basic Box",
            "result": "loss"
        },
        {
            "tournament": "Brisbane",
            "player": "Player_C",
            "my_deck": "Dragapult (ドラパルト / ドラパルト単体)",
            "cards": ["Dragapult ex", "Crushing Hammer", "Dusknoir", "Iono"],
            "opponent_player": "Opponent_3",
            "opponent_deck": "Dragapult Dusknoir",
            "result": "win"
        },
        {
            "tournament": "Frankfurt",
            "player": "Player_D",
            "my_deck": "Dragapult (ドラパルト / ドラパルト単体)",
            "cards": ["Dragapult ex", "Iono"],
            "opponent_player": "Opponent_4",
            "opponent_deck": "N's Zoroark",
            "result": "tie"
        },
    ]
    
    # 類似の模擬データを多量生成（UI動作確認用）
    import random
    tournaments = ["Baltimore", "Brisbane", "Frankfurt", "Recife", "Louisville"]
    opponents = ["Dragapult", "Basic Box", "N's Zoroark", "Slowking", "Dragapult Dusknoir", "Alakazam Dudunsparce", "Mega Excadrill", "Crustle"]
    all_cards = ["Crushing Hammer (クラッシュハンマー)", "Unfair Stamp (アンフェアスタンプ)", "Counter Catcher (カウンターキャッチャー)", "Buddy-Buddy Poffin (なかよしポフィン)"]
    
    expanded = []
    for i in range(1500):
        t = random.choice(tournaments)
        opp = random.choice(opponents)
        res = random.choices(["win", "loss", "tie"], weights=[0.52, 0.40, 0.08])[0]
        
        # 50%の確率でクラッシュハンマー採用
        has_hammer = random.choice([True, False])
        deck_cards = ["Dragapult ex", "Iono"]
        if has_hammer:
            deck_cards.append("Crushing Hammer (クラッシュハンマー)")
            
        expanded.append({
            "match_id": f"M_{i}",
            "tournament": t,
            "player": f"Player_{i%100}",
            "my_deck": "Dragapult (ドラパルト / ドラパルト単体)",
            "cards": deck_cards,
            "opponent_player": f"Opp_{i}",
            "opponent_deck": opp,
            "result": res
        })
        
    return pd.DataFrame(expanded)

df_raw = get_sample_match_data()

# ---------------------------------------------------------
# 上部フィルターエリア (対象)
# ---------------------------------------------------------
st.markdown("### 対象")

col_top1, col_top2 = st.columns([1.5, 2.5])

with col_top1:
    all_tournaments = sorted(list(df_raw["tournament"].unique()))
    selected_tournaments = st.multiselect(
        "大会 (複数選択可)",
        options=all_tournaments,
        default=all_tournaments,
        key="tournaments_filter"
    )

with col_top2:
    all_my_decks = sorted(list(df_raw["my_deck"].unique()))
    selected_my_deck = st.selectbox(
        "自分のデッキタイプ",
        options=all_my_decks,
        index=0,
        key="my_deck_filter"
    )
    
    all_opp_decks = ["すべて"] + sorted(list(df_raw["opponent_deck"].unique()))
    selected_opp_deck = st.selectbox(
        "相手デッキ (対面表を絞る場合)",
        options=all_opp_decks,
        index=0,
        key="opp_deck_filter"
    )
    
    compare_a_b = st.checkbox("グループAとBを比較", value=True, key="chk_compare")

# フィルタリング適用
filtered_df = df_raw[
    (df_raw["tournament"].isin(selected_tournaments)) &
    (df_raw["my_deck"] == selected_my_deck)
]

if selected_opp_deck != "すべて":
    filtered_df = filtered_df[filtered_df["opponent_deck"] == selected_opp_deck]

st.markdown("---")

# ---------------------------------------------------------
# グループ A / B 条件設定エリア
# ---------------------------------------------------------
col_grp_a, col_grp_b = st.columns(2)

# カードリスト候補
card_options = [
    "Crushing Hammer (クラッシュハンマー)",
    "Unfair Stamp (アンフェアスタンプ)",
    "Counter Catcher (カウンターキャッチャー)",
    "Buddy-Buddy Poffin (なかよしポフィン)"
]

with col_grp_a:
    with st.container(border=True):
        st.markdown("**グループA**")
        disp_name_a = st.text_input("結果での表示名", value="採用あり", key="disp_a")
        
        c_a1, c_a2, c_a3, c_a4 = st.columns([3, 1.5, 1, 1])
        with c_a1:
            card_a = st.selectbox("カード選択", card_options, index=0, key="card_a")
        with c_a2:
            cond_a = st.selectbox("条件", ["採用", "不採用"], index=0, key="cond_a")
        with c_a3:
            cnt_a = st.number_input("枚数", min_value=1, value=1, key="cnt_a")
        with c_a4:
            st.write("")
            st.write("")
            st.button("削除", key="del_a")
            
        st.button("+ カード条件", key="add_cond_a")

with col_grp_b:
    if compare_a_b:
        with st.container(border=True):
            st.markdown("**グループB**")
            disp_name_b = st.text_input("結果での表示名", value="採用なし", key="disp_b")
            
            c_b1, c_b2, c_b3, c_b4 = st.columns([3, 1.5, 1, 1])
            with c_b1:
                card_b = st.selectbox("カード選択", card_options, index=0, key="card_b")
            with c_b2:
                cond_b = st.selectbox("条件", ["不採用", "採用"], index=0, key="cond_b")
            with c_b3:
                cnt_b = st.number_input("枚数", min_value=1, value=1, key="cnt_b")
            with c_b4:
                st.write("")
                st.write("")
                st.button("削除", key="del_b")
                
            st.button("+ カード条件", key="add_cond_b")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 集計実行ボタン & 集計ロジック
# ---------------------------------------------------------
col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    do_calc = st.button("集計", type="primary", use_container_width=True)

# データ振り分け関数
def has_card_condition(cards_list, target_card):
    return target_card in cards_list

# グループA・Bのフィルタリング
if cond_a == "採用":
    df_grp_a = filtered_df[filtered_df["cards"].apply(lambda x: has_card_condition(x, card_a))]
else:
    df_grp_a = filtered_df[~filtered_df["cards"].apply(lambda x: has_card_condition(x, card_a))]

if compare_a_b:
    if cond_b == "採用":
        df_grp_b = filtered_df[filtered_df["cards"].apply(lambda x: has_card_condition(x, card_b))]
    else:
        df_grp_b = filtered_df[~filtered_df["cards"].apply(lambda x: has_card_condition(x, card_b))]

# ---------------------------------------------------------
# 集計サマリー表示 (画像中央の文字列再現)
# ---------------------------------------------------------
def calc_stats(df_target):
    decks_count = df_target["player"].nunique() # ユニークデッキ数
    total_matches = len(df_target)
    
    wins = len(df_target[df_target["result"] == "win"])
    losses = len(df_target[df_target["result"] == "loss"])
    ties = len(df_target[df_target["result"] == "tie"])
    
    # 勝率は引き分けを除外: 勝ち / (勝ち + 負け)
    denom = wins + losses
    win_rate = (wins / denom * 100) if denom > 0 else 0.0
    
    return decks_count, wins, losses, ties, total_matches, win_rate

a_decks, a_w, a_l, a_t, a_tot, a_wr = calc_stats(df_grp_a)

st.caption("集計完了。勝率は勝ち ÷ (勝ち + 負け)、引き分けは除外。")

st.markdown(f"**{disp_name_a}**: デッキ {a_decks:,}件 / {a_w}-{a_l}-{a_t} / 勝敗 {a_w+a_l:,}試合 / 勝率 **{a_wr:.2f}%**")

if compare_a_b:
    b_decks, b_w, b_l, b_t, b_tot, b_wr = calc_stats(df_grp_b)
    diff_pt = a_wr - b_wr
    st.markdown(f"**{disp_name_b}**: デッキ {b_decks:,}件 / {b_w}-{b_l}-{b_t} / 勝敗 {b_w+b_l:,}試合 / 勝率 **{b_wr:.2f}%**")
    st.markdown(f"**全体差 (A-B)** : **{diff_pt:+.2f}ポイント**")

# ---------------------------------------------------------
# 対面マトリクス表の生成
# ---------------------------------------------------------
def make_summary_matrix(df_a, df_b=None):
    def aggregate_by_opp(df, prefix):
        opp_list = []
        for opp, group in df.groupby("opponent_deck"):
            w = len(group[group["result"] == "win"])
            l = len(group[group["result"] == "loss"])
            t = len(group[group["result"] == "tie"])
            tot = w + l
            wr = (w / tot * 100) if tot > 0 else 0.0
            opp_list.append({
                "相手デッキ": opp,
                f"{prefix} 勝-敗-分": f"{w}-{l}-{t}",
                f"{prefix} 試合数": tot,
                f"{prefix} 勝率": wr
            })
        return pd.DataFrame(opp_list)

    res_a = aggregate_by_opp(df_a, "A")
    
    if df_b is not None:
        res_b = aggregate_by_opp(df_b, "B")
        merged = pd.merge(res_a, res_b, on="相手デッキ", how="outer").fillna(0)
        
        # 差分計算
        merged["差 (A-B)"] = merged["A 勝率"] - merged["B 勝率"]
        
        # パーセンテージ表示フォーマット
        merged["A 勝率"] = merged["A 勝率"].map(lambda x: f"{x:.2f}%")
        merged["B 勝率"] = merged["B 勝率"].map(lambda x: f"{x:.2f}%")
        merged["差 (A-B)"] = merged["差 (A-B)"].map(lambda x: f"{x:+.2f}pt")
        
        cols = ["相手デッキ", "A 勝-敗-分", "A 試合数", "A 勝率", "B 勝-敗-分", "B 試合数", "B 勝率", "差 (A-B)"]
        return merged[cols]
    else:
        res_a["A 勝率"] = res_a["A 勝率"].map(lambda x: f"{x:.2f}%")
        return res_a

df_matrix = make_summary_matrix(df_grp_a, df_grp_b if compare_a_b else None)

# ---------------------------------------------------------
# テーブル出力 ＆ CSV書き出し
# ---------------------------------------------------------
st.dataframe(df_matrix, use_container_width=True, height=500)

csv_data = df_matrix.to_csv(index=False).encode('utf-8-sig')

st.download_button(
    label="CSVを書き出す",
    data=csv_data,
    file_name="regional_winrate_analysis.csv",
    mime="text/csv",
    key="btn_download_csv"
)

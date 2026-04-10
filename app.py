"""
Noa's LINEマーケ ダッシュボード
ブラウザで確認用のローカルStreamlitアプリ
"""

import streamlit as st
import subprocess
import json
import os
import requests
from datetime import datetime
from pathlib import Path

# ============================================================
# 設定
# ============================================================
# GitHubからタスクを取得するURL（line-teamリポジトリ、Public）
TASKS_URL = "https://raw.githubusercontent.com/Ren-japan/line-team/main/data/tasks.json"
PROJECT_ROOT = Path(__file__).parent  # app.pyと同じフォルダ
KPI_FILE = PROJECT_ROOT / "kpi_data.json"

# ============================================================
# データ取得
# ============================================================

def load_tasks():
    """GitHubからtasks.jsonを取得する"""
    try:
        response = requests.get(TASKS_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"タスク取得エラー: {e}")
    return {"tasks": [], "last_updated": "不明"}


def load_kpi():
    """ローカルのKPIデータを読む。なければデフォルト値を返す"""
    if KPI_FILE.exists():
        with open(KPI_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # デフォルト（初回起動時）
    return {
        "updated": "",
        "genres": [
            {"name": "医療ダイエット(GLP-1)", "pvfr": "", "ctr": "", "fr": "", "fcvr": "", "friends": ""},
            {"name": "包茎手術(PLUS)",        "pvfr": "", "ctr": "", "fr": "", "fcvr": "", "friends": ""},
            {"name": "ED",                    "pvfr": "", "ctr": "", "fr": "", "fcvr": "", "friends": ""},
            {"name": "ICL",                   "pvfr": "", "ctr": "", "fr": "", "fcvr": "", "friends": ""},
        ]
    }


def save_kpi(data):
    """KPIデータをローカルに保存する"""
    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(KPI_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# 指標の基準値（これを下回ったら赤）
# ============================================================
BENCHMARKS = {
    "pvfr": 0.80,
    "ctr":  13.0,
    "fr":   11.0,
    "fcvr": 3.0,
}

def badge(value_str, key):
    """値が基準を超えてたら🟢、割ってたら🔴、空なら⬜"""
    if not value_str:
        return "⬜"
    try:
        v = float(value_str)
        return "🟢" if v >= BENCHMARKS[key] else "🔴"
    except:
        return "⬜"


# ============================================================
# 案件データ（ここを手で更新する）
# ============================================================
PROJECTS = [
    {
        "name": "ICL（眼内コンタクトレンズ）— 視力タイプ診断",
        "status": "🟡 設計完了 → 制作待ち",
        "article": "ICLジャンル横断 11記事（PV合計 11,559/月）",
        "phase": "②設計",
        "phases": ["①分析", "②設計", "③制作", "④入稿", "⑤検証"],
        "current_phase": 1,  # 0始まり
        "brief": "../data/output/briefs/診断-視力タイプ診断.md",
        "expected_impact": "+83人/月（基準値）/ 最大+147人（改善時）",
        "memo": "視力タイプ診断。PU:「その目、なんとかなる？」結果カード4枚×4タイプ=16枚構成。制作物合計24枚。",
    },
]


# ============================================================
# ページ設定
# ============================================================
st.set_page_config(
    page_title="Noa's Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Noa's LINEマーケ ダッシュボード")
st.caption(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

tab1, tab2, tab3, tab4 = st.tabs(["📋 タスク", "🚀 案件", "📝 進捗サマリー", "📈 ファネル数字"])


# ============================================================
# TAB 1: タスク一覧
# ============================================================
with tab1:
    st.subheader("タスク一覧")

    col_refresh, col_info = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 最新を取得"):
            st.cache_data.clear()
            st.rerun()

    data = load_tasks()
    tasks = data.get("tasks", [])
    last_updated = data.get("last_updated", "不明")
    st.caption(f"tasks.json 最終更新: {last_updated}")

    # Noaのタスクだけ / 全タスク切り替え
    show_all = st.checkbox("全員のタスクを表示", value=False)
    if not show_all:
        tasks = [t for t in tasks if t.get("assignee") == "Noa"]

    # カラムごとに表示
    columns = [
        ("🔲 todo",        "todo"),
        ("🔧 in_progress", "in_progress"),
        ("👀 watching",    "watching"),
        ("✅ done",        "done"),
    ]

    cols = st.columns(4)
    for col, (label, col_key) in zip(cols, columns):
        col_tasks = [t for t in tasks if t.get("column") == col_key]
        with col:
            st.markdown(f"**{label}** ({len(col_tasks)})")
            for t in col_tasks:
                needs_approval = "🔒 " if t.get("needs_approval") else ""
                assignee = t.get("assignee", "未定")
                deadline = f" | 期限: {t['deadline']}" if t.get("deadline") else ""
                with st.expander(f"{needs_approval}{t['title']} ({assignee})"):
                    st.write(f"**目的:** {t.get('purpose', '')}")
                    if t.get("impact"):
                        st.write(f"**インパクト:** {t.get('impact')}")
                    if t.get("description"):
                        st.write(f"**詳細:** {t.get('description')}")
                    if deadline:
                        st.write(f"**期限:** {t.get('deadline')}")
                    if t.get("notes"):
                        st.write(f"**メモ:** {t.get('notes')}")


# ============================================================
# TAB 2: 案件ページ
# ============================================================
with tab2:
    st.subheader("進行中の案件")

    for p in PROJECTS:
        with st.container(border=True):
            # --- ヘッダー行: 案件名 + フェーズ ---
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"### {p['name']}")
                st.write(f"**ステータス:** {p['status']}")
                st.write(f"**対象記事:** {p['article']}")
                st.write(f"**期待効果:** {p['expected_impact']}")
                st.write(f"**メモ:** {p['memo']}")
            with c2:
                st.markdown("**フェーズ**")
                for i, phase in enumerate(p["phases"]):
                    if i == p["current_phase"]:
                        st.markdown(f"**→ {phase}** ◀ 今ここ")
                    elif i < p["current_phase"]:
                        st.markdown(f"~~{phase}~~ ✅")
                    else:
                        st.markdown(f"　{phase}")

            # --- 設計書の中身を展開表示 ---
            brief_path = PROJECT_ROOT / p["brief"]
            if brief_path.exists():
                with st.expander("📄 設計書の詳細を見る（リサーチ・ユーザーダイブ・設計内容）"):
                    content = brief_path.read_text(encoding="utf-8")
                    st.markdown(content)
            else:
                st.caption(f"設計書未作成: {p['brief']}")

    # --- 参考資料セクション ---
    st.divider()
    st.markdown("### 参考")
    st.caption("Renが作成した設計書・依頼書のサンプル（設計・依頼書作成時の参照用）")

    REFS = [
        {
            "label": "📋 設計書サンプル（摂取カロリー診断）",
            "path": "references/参考-摂取カロリー設計.md",
        },
        {
            "label": "📝 デザイン依頼書サンプル（摂取カロリー診断）",
            "path": "references/参考-デザイン依頼書_摂取カロリー診断.md",
        },
    ]
    for ref in REFS:
        ref_path = PROJECT_ROOT / ref["path"]
        if ref_path.exists():
            with st.expander(ref["label"]):
                st.markdown(ref_path.read_text(encoding="utf-8"))
        else:
            st.caption(f"ファイルが見つかりません: {ref['path']}")


# ============================================================
# TAB 3: 進捗サマリー
# ============================================================
with tab3:
    st.subheader("今週の進捗サマリー")

    SUMMARY_FILE = PROJECT_ROOT / "summary.json"
    DAILY_FILE   = PROJECT_ROOT / "daily.json"

    daily_tab, weekly_tab = st.tabs(["📅 今日", "📆 今週"])

    # ---- 今日タブ ----
    with daily_tab:
        if DAILY_FILE.exists():
            with open(DAILY_FILE, "r", encoding="utf-8") as f:
                daily = json.load(f)
        else:
            daily = {"done": "", "wip": "", "next": "", "updated": ""}

        with st.form("daily_form"):
            d_done = st.text_area("✅ 今日やったこと", value=daily.get("done", ""), height=120)
            d_wip  = st.text_area("🔧 進行中のこと",  value=daily.get("wip", ""),  height=80)
            d_next = st.text_area("⏭ 明日やること",   value=daily.get("next", ""), height=80)

            if st.form_submit_button("保存"):
                new_daily = {
                    "done": d_done, "wip": d_wip, "next": d_next,
                    "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                with open(DAILY_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_daily, f, ensure_ascii=False, indent=2)
                st.success("保存しました！")
                st.rerun()

        if daily.get("updated"):
            st.caption(f"最終保存: {daily['updated']}")

    # ---- 今週タブ ----
    with weekly_tab:
        if SUMMARY_FILE.exists():
            with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
        else:
            saved = {"done": "", "wip": "", "next": "", "memo": "", "updated": ""}

        with st.form("summary_form"):
            done = st.text_area("✅ 今週やったこと", value=saved.get("done", ""), height=120)
            wip  = st.text_area("🔧 進行中のこと",  value=saved.get("wip", ""),  height=80)
            nxt  = st.text_area("⏭ 来週やること",   value=saved.get("next", ""), height=80)
            memo = st.text_area("📌 メモ・懸念",     value=saved.get("memo", ""), height=60)

            if st.form_submit_button("保存"):
                new_data = {
                    "done": done, "wip": wip,
                    "next": nxt,  "memo": memo,
                    "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=2)
                st.success("保存しました！")
                st.rerun()

        if saved.get("updated"):
            st.caption(f"最終保存: {saved['updated']}")


# ============================================================
# TAB 4: ファネル数字
# ============================================================
with tab4:
    st.subheader("ファネル数字（KPI）")

    # 基準値の表示
    with st.expander("📏 基準値"):
        st.markdown("""
        | 指標 | 基準値 |
        |------|-------|
        | PVFR | 0.80〜1.00% |
        | PU CTR | 13%以上 |
        | 友だち追加率 | 11%以上 |
        | FCVR | 3%以上 |
        """)

    kpi_data = load_kpi()
    genres = kpi_data.get("genres", [])

    # 表示
    header = st.columns([2, 1.2, 1.2, 1.2, 1.2, 1.2])
    header[0].markdown("**ジャンル**")
    header[1].markdown("**PVFR(%)**")
    header[2].markdown("**PU CTR(%)**")
    header[3].markdown("**友達追加率(%)**")
    header[4].markdown("**FCVR(%)**")
    header[5].markdown("**友だち数**")

    st.divider()

    for g in genres:
        row = st.columns([2, 1.2, 1.2, 1.2, 1.2, 1.2])
        row[0].write(g["name"])
        row[1].write(f"{badge(g['pvfr'], 'pvfr')} {g['pvfr'] or '-'}%")
        row[2].write(f"{badge(g['ctr'],  'ctr' )} {g['ctr']  or '-'}%")
        row[3].write(f"{badge(g['fr'],   'fr'  )} {g['fr']   or '-'}%")
        row[4].write(f"{badge(g['fcvr'], 'fcvr')} {g['fcvr'] or '-'}%")
        row[5].write(g["friends"] or "-")

    st.divider()

    # 編集フォーム
    with st.expander("✏️ 数字を更新する"):
        with st.form("kpi_form"):
            new_genres = []
            for g in genres:
                st.markdown(f"**{g['name']}**")
                c = st.columns(5)
                new_genres.append({
                    "name":    g["name"],
                    "pvfr":    c[0].text_input("PVFR(%)",    value=g.get("pvfr", ""),    key=f"pvfr_{g['name']}"),
                    "ctr":     c[1].text_input("CTR(%)",     value=g.get("ctr", ""),     key=f"ctr_{g['name']}"),
                    "fr":      c[2].text_input("友追率(%)",  value=g.get("fr", ""),      key=f"fr_{g['name']}"),
                    "fcvr":    c[3].text_input("FCVR(%)",    value=g.get("fcvr", ""),    key=f"fcvr_{g['name']}"),
                    "friends": c[4].text_input("友だち数",   value=g.get("friends", ""), key=f"fr2_{g['name']}"),
                })

            if st.form_submit_button("保存"):
                save_kpi({"genres": new_genres})
                st.success("保存しました！")
                st.rerun()

    if kpi_data.get("updated"):
        st.caption(f"KPI最終更新: {kpi_data['updated']}")

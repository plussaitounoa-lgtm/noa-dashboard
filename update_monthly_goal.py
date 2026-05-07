"""
月次目標の友達追加数を Google Sheets から取得して monthly_goal.json を更新するスクリプト。
セッション開始時に自動実行される。
line-dashboard の analysis_engine を使って PU + バナー合算の正確な値を取得する。
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# パス設定
DASHBOARD_DIR = Path(__file__).parent
LINE_DASH_DIR = DASHBOARD_DIR.parent / "claude-projects" / "line-dashboard"
GOAL_FILE     = DASHBOARD_DIR / "monthly_goal.json"

# line-dashboard の lib を import できるようにパスを通す
sys.path.insert(0, str(LINE_DASH_DIR))

# 月次目標（固定値）
MONTHLY_GOAL = 800


def fetch_monthly_friends() -> dict:
    """analysis_engine 経由で当月の友達追加数（PU + バナー合算）を取得"""
    # line-dashboard の .env を読んでから import
    from dotenv import load_dotenv
    load_dotenv(str(LINE_DASH_DIR / ".env"))

    try:
        from lib.data_loader import load_unified_data
    except ImportError as e:
        print(f"[update_monthly_goal] import 失敗: {e}")
        return {}

    print("[update_monthly_goal] スプシからデータ取得中...")
    result = load_unified_data()
    df = result.get("df")

    if df is None or df.empty:
        errors = result.get("errors", [])
        print(f"[update_monthly_goal] データ取得失敗: {errors}")
        return {}

    # 当月フィルタ
    now = datetime.now()
    month_str = now.strftime("%Y-%m")  # prepare_data後は datetime型

    import pandas as pd
    df["data_date"] = pd.to_datetime(df["data_date"], errors="coerce")
    df_month = df[df["data_date"].dt.strftime("%Y-%m") == month_str]

    # SEOチャネルのみ（ダッシュボードと同じ口）
    df_seo = df_month[df_month["channel"] == "SEO"] if "channel" in df_month.columns else df_month

    total_friends = int(df_seo["added_friends"].sum()) if "added_friends" in df_seo.columns else 0
    days_elapsed  = df_seo["data_date"].dt.date.nunique() if not df_seo.empty else 0

    return {
        "goal":         MONTHLY_GOAL,
        "current":      total_friends,
        "days_elapsed": int(days_elapsed),
        "month":        now.strftime("%Y-%m"),
        "updated":      now.strftime("%Y-%m-%d"),
    }


def main():
    data = fetch_monthly_friends()

    if not data:
        print("[update_monthly_goal] 取得失敗。monthly_goal.json は更新しません。")
        sys.exit(0)

    # 既存ファイルの goal 値を引き継ぐ（手動変更を尊重）
    if GOAL_FILE.exists():
        with open(GOAL_FILE, encoding="utf-8") as f:
            existing = json.load(f)
        data["goal"] = existing.get("goal", MONTHLY_GOAL)

    with open(GOAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    daily = data["current"] / data["days_elapsed"] if data["days_elapsed"] > 0 else 0
    proj  = int(daily * 31)
    print(f"[update_monthly_goal] 完了: {data['current']}人 / {data['days_elapsed']}日経過 "
          f"→ 日均{daily:.1f}人 → 着地予測{proj}人（目標{data['goal']}人）")


if __name__ == "__main__":
    main()
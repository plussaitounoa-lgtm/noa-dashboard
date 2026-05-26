"""
未設置検知スプシにこいずみタブを追加するスクリプト。
ベースURL: https://koizumi-seikei.jp/obesity/diet-{slug}/
「記事種別」列でCV記事/ノウハウ記事を区別。CV記事はグレーアウト表示。
"""
import sys
import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

DASHBOARD_DIR = Path(__file__).parent
LINE_DASH_DIR = DASHBOARD_DIR.parent / "claude-projects" / "line-dashboard"
CACHE_CSV     = LINE_DASH_DIR / "data" / "friend_data_cache.csv"
CREDS_PATH    = LINE_DASH_DIR / "credentials.json"

SPREADSHEET_ID   = "1D9p_3X7c74rAyasSGx4-uFbqpM21n9l6wFPxtX0KtRY"
NOW_MONTH        = datetime.now().strftime("%Y-%m")
KOIZUMI_BASE_URL = "https://koizumi-seikei.jp/obesity/diet-"

CV      = "CV記事"
KNOWHOW = "ノウハウ記事"

# (記事名, 月間クリック, 月間インプレ, 記事種別)
KOIZUMI_ARTICLES = {
    "bmi":                    ("BMI",                        2409, 1237599, KNOWHOW),
    "snacking":               ("間食",                       1840,  109992, KNOWHOW),
    "medicine":               ("痩せる薬",                    501,   34488, KNOWHOW),
    "rybelsusmounjaro":       ("リベルサス・マンジャロどっち",  409,   19448, KNOWHOW),
    "dmmmounjaro":            ("DMMマンジャロ",                106,   40447, KNOWHOW),
    "injection":              ("注射（GLP-1）",                93,   19918, KNOWHOW),
    "dmmrybelsus":            ("DMMリベルサス",                91,   61070, KNOWHOW),
    "cost":                   ("費用",                         50,    9266, KNOWHOW),
    "mounjaro-personalimport":("マンジャロ個人輸入",              7,    1991, KNOWHOW),
    "glp1":                   ("GLP-1",                         6,    2642, KNOWHOW),
}

# キャッシュのタグキー → スラグ のマッピング
CACHE_KEY_TO_SLUG = {
    "bmi":                      "bmi",
    "間食やめられない":            "snacking",
    "痩せる薬":                   "medicine",
    "リベルサスマンジャロどっち":   "rybelsusmounjaro",
    "スルリムマンジャロ":          "dmmmounjaro",
    "マンジャロ_オンライン":       "injection",
    "リベルサス_通販":            "dmmrybelsus",
}


def extract_key(base: str) -> str | None:
    """タグベース文字列から記事キーを抽出（前方一致）"""
    for key in CACHE_KEY_TO_SLUG:
        if base.startswith(key + "_") or base == key:
            return key
    return None


def load_koizumi_cache() -> dict:
    """キャッシュCSVからこいずみの記事別PU・バナーデータを集計"""
    data = defaultdict(lambda: {
        "has_pu": False, "has_banner": False,
        "total_banner": 0, "total_pu": 0,
        "month_banner": 0, "month_pu": 0,
    })

    with open(CACHE_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tag = row["tag_name"]
            if "こいずみ" not in tag:
                continue

            is_banner = row["is_banner"] == "True"
            friends   = int(row["added_friends"] or 0)
            is_month  = row["data_date"].startswith(NOW_MONTH)

            base = tag.replace("/glp1_seo/こいずみ_", "").replace("/glp1_seo_ava/こいずみ_", "").strip()
            key  = extract_key(base)
            if not key:
                continue

            slug = CACHE_KEY_TO_SLUG[key]
            if is_banner:
                data[slug]["has_banner"] = True
                data[slug]["total_banner"] += friends
                if is_month: data[slug]["month_banner"] += friends
            else:
                data[slug]["has_pu"] = True
                data[slug]["total_pu"] += friends
                if is_month: data[slug]["month_pu"] += friends

    return data


def build_rows(cache: dict):
    NCOLS = 11

    header_rows = [
        ["こいずみ（koizumi-seikei.jp）　未設置検知レポート"] + [""] * (NCOLS - 1),
        [f"更新: {datetime.now().strftime('%Y/%m/%d')}"]      + [""] * (NCOLS - 1),
        [""] * NCOLS,
        ["スラグ", "記事名", "記事URL", "記事種別", "PU設置", "バナー設置", "バナー設置日", "バナー種別", "月間クリック", "友だち（今月）", "友だち（全期間）"],
    ]

    both    = []
    pu_only = []
    none_   = []
    cv_rows = []  # CV記事は種別問わず末尾にまとめる

    for slug, (name, clicks, imps, article_type) in KOIZUMI_ARTICLES.items():
        c = cache.get(slug, {})
        has_pu     = c.get("has_pu", False)
        has_banner = c.get("has_banner", False)
        row = [
            slug,
            name,
            KOIZUMI_BASE_URL + slug + "/",
            article_type,
            "設置済み" if has_pu     else "未設置",
            "設置済み" if has_banner else "未設置",
            "",  # バナー設置日（手入力）
            "",  # バナー種別（手入力）
            clicks,
            c.get("month_banner", 0) + c.get("month_pu", 0),
            c.get("total_banner", 0) + c.get("total_pu", 0),
        ]
        if article_type == CV:
            cv_rows.append(row)
        elif has_banner:
            both.append(row)
        elif has_pu:
            pu_only.append(row)
        else:
            none_.append(row)

    both.sort(key=lambda r: r[1])
    pu_only.sort(key=lambda r: r[8] or 0, reverse=True)
    none_.sort(key=lambda r: r[8] or 0, reverse=True)
    cv_rows.sort(key=lambda r: r[8] or 0, reverse=True)

    sep1 = ["---（以下 PUのみ）---"]              + [""] * (NCOLS - 1)
    sep2 = ["---（以下 未設置 / クリック数順）---"]  + [""] * (NCOLS - 1)
    sep3 = ["---（以下 CV記事 / LINE対象外）---"]   + [""] * (NCOLS - 1)
    all_rows = header_rows + both + [sep1] + pu_only + [sep2] + none_ + [sep3] + cv_rows

    return all_rows, both, pu_only, none_, cv_rows


def main():
    import gspread
    from google.oauth2.service_account import Credentials

    print("[add_koizumi_sheet] データ読み込み中...")
    cache = load_koizumi_cache()
    all_rows, both, pu_only, none_, cv_rows = build_rows(cache)
    print(f"  PU+バナー: {len(both)} / PUのみ: {len(pu_only)} / 未設置: {len(none_)} / CV記事: {len(cv_rows)}")

    print("[add_koizumi_sheet] スプシに接続中...")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds  = Credentials.from_service_account_file(str(CREDS_PATH), scopes=scopes)
    gc     = gspread.authorize(creds)
    sh     = gc.open_by_key(SPREADSHEET_ID)

    titles = [w.title for w in sh.worksheets()]
    if "こいずみ（ダイエット）" in titles and "こいずみ" in titles:
        dupe = sh.worksheet("こいずみ")
        sh.del_worksheet(dupe)
        titles = [w.title for w in sh.worksheets()]

    if "こいずみ（ダイエット）" in titles:
        ws = sh.worksheet("こいずみ（ダイエット）")
        ws.update_title("こいずみ")
    elif "こいずみ" in titles:
        ws = sh.worksheet("こいずみ")
    else:
        ws = sh.add_worksheet(title="こいずみ", rows=60, cols=11)
    print("[add_koizumi_sheet] シート準備完了")

    NCOLS    = 11
    last_col = "K"

    # 現在のシートを全列読み込み、手動入力値をすべて保持
    existing_rows_data = ws.get_all_values()
    preserve_map: dict[str, dict] = {}
    if existing_rows_data and len(existing_rows_data) > 3:
        hdr = existing_rows_data[3]
        for row in existing_rows_data[4:]:
            if not row or not row[0] or row[0].startswith("---"):
                continue
            slug = row[0]
            saved = {}
            # ヘッダー名で保持（記事種別・PU設置・バナー設置・バナー設置日・バナー種別）
            for i, col_name in enumerate(hdr):
                if col_name in ("記事種別", "PU設置", "バナー設置", "バナー設置日", "バナー種別") and len(row) > i:
                    saved[col_name] = row[i]
            # ヘッダー外の列（旧K列など）をバナー設置日候補として保持
            for i in range(len(hdr), len(row)):
                if row[i] and "バナー設置日" not in saved:
                    saved["バナー設置日"] = row[i]
            preserve_map[slug] = saved

    # 既存バナー種別がない場合のデフォルト（初回書き込み用）
    BANNER_DEFAULTS = {
        "medicine": "薬診断",
    }
    for slug, default_type in BANNER_DEFAULTS.items():
        if slug not in preserve_map:
            preserve_map[slug] = {}
        if not preserve_map[slug].get("バナー種別"):
            preserve_map[slug]["バナー種別"] = default_type

    saved_count = sum(1 for d in preserve_map.values() for v in d.values() if v)
    print(f"[add_koizumi_sheet] 手動入力値を保持: {saved_count}件")

    for row in all_rows:
        if not row or not row[0] or row[0].startswith("---"):
            continue
        saved = preserve_map.get(row[0], {})
        # 記事種別（D列）
        if saved.get("記事種別") and len(row) > 3:
            row[3] = saved["記事種別"]
        # PU設置（E列）: キャッシュが設置済みならそのまま、未設置なら既存値を保持
        if len(row) > 4 and row[4] != "設置済み":
            row[4] = saved.get("PU設置", row[4])
        # バナー設置（F列）: 同上
        if len(row) > 5 and row[5] != "設置済み":
            row[5] = saved.get("バナー設置", row[5])
        # バナー設置日（G列 = 新列）: 旧K列のメモ or 既存のバナー設置日
        if len(row) > 6:
            row[6] = saved.get("バナー設置日", row[6])
        # バナー種別（H列）: 旧G列から移行
        if len(row) > 7:
            row[7] = saved.get("バナー種別", row[7])

    sh.batch_update({"requests": [{"unmergeCells": {"range": {
        "sheetId": ws.id,
        "startRowIndex": 0, "endRowIndex": 1000,
        "startColumnIndex": 0, "endColumnIndex": 52,
    }}}]})
    ws.clear()
    ws.update(values=all_rows, range_name="A1")
    print(f"[add_koizumi_sheet] データ書き込み完了: {len(all_rows)}行")

    # 行位置計算
    header_end = 4
    both_start = header_end + 1
    both_end   = header_end + len(both)
    sep1_row   = both_end + 1
    pu_start   = sep1_row + 1
    pu_end     = sep1_row + len(pu_only)
    sep2_row   = pu_end + 1
    none_start = sep2_row + 1
    none_end   = sep2_row + len(none_)
    sep3_row   = none_end + 1
    cv_start   = sep3_row + 1
    cv_end     = len(all_rows)

    # ヘッダー（黒）
    ws.format(f"A4:{last_col}4", {
        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
        "horizontalAlignment": "CENTER",
    })
    ws.format("A1", {"textFormat": {"bold": True, "fontSize": 13}})

    # PU+バナー（薄い緑）
    if both_start <= both_end:
        ws.format(f"A{both_start}:{last_col}{both_end}", {
            "backgroundColor": {"red": 0.93, "green": 0.99, "blue": 0.93},
        })
    # PUのみ（薄い青）
    if pu_start <= pu_end:
        ws.format(f"A{pu_start}:{last_col}{pu_end}", {
            "backgroundColor": {"red": 0.9, "green": 0.95, "blue": 1.0},
        })
    # 未設置（薄いオレンジ）
    if none_start <= none_end:
        ws.format(f"A{none_start}:{last_col}{none_end}", {
            "backgroundColor": {"red": 1.0, "green": 0.97, "blue": 0.9},
        })
    # CV記事（グレー）
    if cv_start <= cv_end:
        ws.format(f"A{cv_start}:{last_col}{cv_end}", {
            "backgroundColor": {"red": 0.88, "green": 0.88, "blue": 0.88},
            "textFormat": {"foregroundColor": {"red": 0.5, "green": 0.5, "blue": 0.5}},
        })

    ws.merge_cells(f"A1:{last_col}1")
    ws.merge_cells(f"A2:{last_col}2")

    sh.batch_update({"requests": [
        {"updateSheetProperties": {
            "properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": 4}},
            "fields": "gridProperties.frozenRowCount",
        }},
        {"updateDimensionProperties": {  # A: スラグ
            "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 180}, "fields": "pixelSize",
        }},
        {"updateDimensionProperties": {  # B: 記事名
            "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
            "properties": {"pixelSize": 180}, "fields": "pixelSize",
        }},
        {"updateDimensionProperties": {  # C: URL
            "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3},
            "properties": {"pixelSize": 320}, "fields": "pixelSize",
        }},
        {"updateDimensionProperties": {  # D: 記事種別
            "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 3, "endIndex": 4},
            "properties": {"pixelSize": 110}, "fields": "pixelSize",
        }},
        {"updateDimensionProperties": {  # E,F: PU/バナー設置
            "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 6},
            "properties": {"pixelSize": 100}, "fields": "pixelSize",
        }},
        {"updateDimensionProperties": {  # G: バナー設置日
            "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 7},
            "properties": {"pixelSize": 110}, "fields": "pixelSize",
        }},
        {"updateDimensionProperties": {  # H: バナー種別
            "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 7, "endIndex": 8},
            "properties": {"pixelSize": 150}, "fields": "pixelSize",
        }},
        {"updateDimensionProperties": {  # I,J,K: 数値
            "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 8, "endIndex": 11},
            "properties": {"pixelSize": 110}, "fields": "pixelSize",
        }},
    ]})

    print(f"\n完了: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")


if __name__ == "__main__":
    main()
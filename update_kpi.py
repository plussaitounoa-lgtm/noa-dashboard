"""
スプレッドシートからKPIデータを取得して kpi_data.json に保存するスクリプト
ローカルで実行してGitHubにpushすることでダッシュボードに反映できる
"""
import sys, csv, io, json, re
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

try:
    import requests
    def fetch_url(url):
        return requests.get(url, timeout=15).text
except ImportError:
    import urllib.request
    def fetch_url(url):
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.read().decode('utf-8')

SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1kjWKJ5RsVeWO80Zva1wTK5zFp8Tgx6Eney9yWu7rD0U"
    "/export?format=csv&gid=823780364"
)
KPI_FILE = Path(__file__).parent / "kpi_data.json"

# ジャンル名と対応する行番号（0始まり）
GENRE_ROWS = [
    ("医療ダイエット(合算)",  11),
    ("医療ダイエット(PLUS)",  13),
    ("医療ダイエット(AVA)",   15),
    ("医療ダイエット(SUTEKi)", 17),
    ("FAGA",                  19),
    ("ピル",                  21),
    ("包茎",                  23),
    ("ED",                    25),
    ("転職",                  27),
    ("リカバリーウェア",      31),
]

# スプシの列インデックス（Row 4 のヘッダーに対応）
COL_PU_CTR   = 6   # PU CTR
COL_FR       = 7   # 友だち追加率
COL_FRIENDS  = 8   # 友達追加数
COL_PVFR     = 12  # PVFR(F/LP)
COL_IMPFR    = 13  # IMPFR(F/PUimp)
COL_FCVR     = 14  # FCVR(CV/F+)
COL_CV       = 15  # CV数
COL_REVENUE  = 16  # 売上


def clean_pct(val):
    """'9.97%' → 9.97（float）。計測中や空はNone"""
    if not val or val.strip() in ("計測中", "-", ""):
        return None
    try:
        return float(val.replace("%", "").replace(",", "").strip())
    except ValueError:
        return None


def clean_num(val):
    """'475' や '¥182,500' → float。計測中や空はNone"""
    if not val or val.strip() in ("計測中", "-", ""):
        return None
    cleaned = re.sub(r"[¥,\s]", "", val)
    try:
        return float(cleaned)
    except ValueError:
        return None


def fetch_and_update():
    print("📥 スプレッドシートを取得中...")
    text = fetch_url(SHEET_URL)
    rows = list(csv.reader(io.StringIO(text)))

    # 期間ラベル（Row 4 col[1]）
    period = rows[4][1].strip() if len(rows) > 4 and len(rows[4]) > 1 else ""

    genres = []
    for name, row_idx in GENRE_ROWS:
        if row_idx >= len(rows):
            print(f"  ⚠️ {name}: 行が存在しない（index {row_idx}）")
            continue

        row = rows[row_idx]

        def get(col):
            return row[col] if len(row) > col else ""

        entry = {
            "name":    name,
            "pvfr":    clean_pct(get(COL_PVFR)),
            "impfr":   clean_pct(get(COL_IMPFR)),
            "ctr":     clean_pct(get(COL_PU_CTR)),
            "fr":      clean_pct(get(COL_FR)),
            "fcvr":    clean_pct(get(COL_FCVR)),
            "friends": clean_num(get(COL_FRIENDS)),
            "cv":      clean_num(get(COL_CV)),
            "revenue": clean_num(get(COL_REVENUE)),
        }
        genres.append(entry)
        print(f"  ✅ {name}: 友達={entry['friends']}, PVFR={entry['pvfr']}%, FCVR={entry['fcvr']}%")

    kpi_data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "period":  period,
        "genres":  genres,
    }

    with open(KPI_FILE, "w", encoding="utf-8") as f:
        json.dump(kpi_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 保存完了: {KPI_FILE}")
    print(f"   期間: {period} / {len(genres)}ジャンル")


if __name__ == "__main__":
    fetch_and_update()

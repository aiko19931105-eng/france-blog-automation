"""
フランス留学ブログ 自動投稿スクリプト
週2回（火・金）にClaude AIで記事生成 → WordPress自動公開
"""

import os
import json
import random
import requests
from datetime import datetime
from anthropic import Anthropic

# ── 設定 ──────────────────────────────────────────────
WP_URL      = os.environ["WP_URL"]          # 例: https://yourblog.com
WP_USER     = os.environ["WP_USER"]         # WordPressユーザー名
WP_APP_PASS = os.environ["WP_APP_PASS"]     # アプリケーションパスワード
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = Anthropic()

# ── SEOキーワードリスト ────────────────────────────────
KEYWORD_POOL = [
    # フランス留学
    {"main": "フランス留学 費用", "sub": ["フランス 大学 学費", "フランス留学 奨学金", "フランス 生活費 学生"]},
    {"main": "フランス留学 語学学校", "sub": ["パリ 語学学校 おすすめ", "フランス語 短期留学", "アリアンス・フランセーズ"]},
    {"main": "フランス留学 ビザ", "sub": ["フランス 学生ビザ 申請", "フランス ビザ 必要書類", "長期滞在許可証"]},
    {"main": "フランス留学 準備", "sub": ["フランス留学 持ち物リスト", "フランス 留学前 やること", "海外留学 保険"]},
    {"main": "フランス留学 大学", "sub": ["ソルボンヌ大学 入学", "フランス グランゼコール", "フランス 大学院 留学"]},
    # フランス滞在・生活
    {"main": "フランス 滞在 アパート", "sub": ["パリ アパート 探し方", "フランス 住居 学生寮", "コロカシオン フランス"]},
    {"main": "フランス 短期滞在 観光", "sub": ["フランス 穴場スポット", "パリ 観光 モデルコース", "フランス 地方 旅行"]},
    {"main": "フランス 生活 文化", "sub": ["フランス人 習慣 違い", "フランス カフェ文化", "フランス 食文化 体験"]},
    {"main": "フランス 交通 移動", "sub": ["パリ メトロ 使い方", "フランス 電車 格安", "フロント ナビゴ カード"]},
    {"main": "フランス 短期留学 1ヶ月", "sub": ["フランス語 上達 方法", "短期留学 メリット", "1ヶ月 フランス 体験談"]},
    {"main": "フランス インターンシップ", "sub": ["フランス スタージュ", "パリ 就業体験", "フランス 職場 文化"]},
    {"main": "フランス 銀行口座 開設", "sub": ["フランス 留学生 銀行", "ラ・ポスト 口座", "フランス キャッシュレス"]},
]

# ── 記事生成 ───────────────────────────────────────────
def generate_article(keyword_data: dict) -> dict:
    main_kw = keyword_data["main"]
    sub_kws  = "、".join(keyword_data["sub"])

    prompt = f"""
あなたはフランス留学・滞在に詳しいブロガーです。
以下の条件でSEOに強いブログ記事を日本語で書いてください。

【メインキーワード】{main_kw}
【関連キーワード】{sub_kws}
【対象読者】フランス留学を検討中の高校生・保護者、またはすでに留学中の学生
【文字数】1800〜2200文字
【トーン】親しみやすく、実体験ベースで具体的に

【必須構成】
1. タイトル（H1）: メインキーワードを含む魅力的なタイトル（30〜40文字）
2. リード文（150字）: 読者の悩みに共感し、記事で解決できることを伝える
3. H2見出し 3〜4個（各見出しにキーワードを自然に含める）
4. まとめ（200字）: 行動を促すCTA付き
5. SEOメタディスクリプション（120〜130文字）: クリックしたくなる説明文

【出力形式】必ずJSON形式で返してください：
{{
  "title": "記事タイトル",
  "meta_description": "メタディスクリプション",
  "content": "HTML形式の本文（h2, p, ul, strong タグ使用可）",
  "tags": ["タグ1", "タグ2", "タグ3"],
  "focus_keyword": "{main_kw}"
}}
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text
    # JSONブロックを抽出
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    return json.loads(raw)


# ── WordPress投稿 ──────────────────────────────────────
def post_to_wordpress(article: dict) -> dict:
    endpoint = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/posts"

    payload = {
        "title":   article["title"],
        "content": article["content"],
        "status":  "publish",          # 即時公開
        "excerpt": article.get("meta_description", ""),
        "tags":    get_or_create_tags(article.get("tags", [])),
        "meta": {
            "_yoast_wpseo_metadesc":       article.get("meta_description", ""),
            "_yoast_wpseo_focuskw":        article.get("focus_keyword", ""),
        }
    }

    resp = requests.post(
        endpoint,
        json=payload,
        auth=(WP_USER, WP_APP_PASS),
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def get_or_create_tags(tag_names: list) -> list:
    """タグ名からWordPress tag IDを取得（なければ作成）"""
    tag_ids = []
    base = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/tags"
    auth = (WP_USER, WP_APP_PASS)

    for name in tag_names:
        # 検索
        r = requests.get(base, params={"search": name}, auth=auth, timeout=15)
        results = r.json()
        if results:
            tag_ids.append(results[0]["id"])
        else:
            # 新規作成
            r2 = requests.post(base, json={"name": name}, auth=auth, timeout=15)
            if r2.status_code == 201:
                tag_ids.append(r2.json()["id"])

    return tag_ids


# ── メイン処理 ─────────────────────────────────────────
def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] ブログ自動投稿 開始")

    # 今週使ったキーワードを避けてランダム選択（簡易実装）
    keyword = random.choice(KEYWORD_POOL)
    print(f"  キーワード: {keyword['main']}")

    # 記事生成
    print("  Claude AI で記事を生成中...")
    article = generate_article(keyword)
    print(f"  タイトル: {article['title']}")

    # WordPress投稿
    print("  WordPress に投稿中...")
    result = post_to_wordpress(article)
    print(f"  公開完了！URL: {result.get('link', '不明')}")
    print(f"  投稿ID: {result.get('id')}")

    # ログ保存
    log = {
        "date":     datetime.now().isoformat(),
        "keyword":  keyword["main"],
        "title":    article["title"],
        "post_id":  result.get("id"),
        "url":      result.get("link"),
    }
    with open("post_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")

    print("  ログ保存完了")
    return log


if __name__ == "__main__":
    main()

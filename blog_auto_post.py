"""
AP留学ブログ 自動投稿スクリプト v2
- Claude AIで最新情報を含む記事を生成
- AP留学のサービス情報・導線を全記事に組み込み
- WordPress自動公開
"""

import os
import json
import random
import requests
from datetime import datetime
from anthropic import Anthropic

# ── 設定 ──────────────────────────────────────────────
WP_URL      = os.environ["WP_URL"]
WP_USER     = os.environ["WP_USER"]
WP_APP_PASS = os.environ["WP_APP_PASS"]

client = Anthropic()

# ── AP留学 サービス情報（全記事に組み込む） ────────────
AP_SERVICE_INFO = """
【AP留学について】
- パリ在住12年の留学経験者・Aikoが代表のパリ拠点の現地エージェント
- バイリンガルスタッフが時差なしでLINEサポート
- SNS独自発信で集客しているため広告費不要→提携校への学校手配は無料
- 学校からの紹介料のみで運営しているため、学費を抑えた提案が可能
- AP留学を通しても自分で手配しても学費は同じ（提携校によってはAP経由の方が安い）

【サービスメニュー】
1. 学校手配のみ：提携校は無料、私立語学学校（非提携）は44,000円
2. 短期サポート：22,000円（渡仏前〜渡仏後2ヶ月）
3. ビザサポートPremium：学生ビザ88,000円／ワーホリ66,000円
4. 個別フルサポート：学生ビザ118,000円／ワーホリ96,000円（個別コンサル3回付き）
5. 住居手配：学生寮・ホームステイ 300€
6. ビザサポート内容：申請書類チェック、Etudes en France・France-Visasサポート、志望動機・履歴書のフランス語翻訳など

【無料サービス】
- LINEでのエリア診断ZOOM
- 無料留学相談ZOOM
- 学校選び・ビザ選択・費用のLINE相談

【コミュニティ】
- AP留学コミュニティチャット（Discord）
- パリでのミートアップ会（約2ヶ月に1回）

【LINEアカウント】https://lin.ee/7iwiIBE
"""

# ── CTA HTML（全記事末尾に追加） ──────────────────────
CTA_HTML = """
<div style="background: linear-gradient(135deg, #f8f4ff 0%, #fff0f6 100%); border-left: 4px solid #9b59b6; border-radius: 8px; padding: 24px; margin: 32px 0;">
  <h3 style="color: #6c3483; margin-top: 0;">🗼 フランス留学のご相談はAP留学へ</h3>
  <p>パリ在住12年・現地エージェントだから伝えられる<strong>リアルな情報</strong>でサポートします。</p>
  <ul style="padding-left: 1.2em;">
    <li>✅ <strong>提携校への学校手配は無料</strong>（学費も自己手配と同額かそれ以下）</li>
    <li>✅ バイリンガルスタッフが<strong>LINEで時差なし対応</strong></li>
    <li>✅ 学生ビザ・ワーホリビザの申請サポートも充実</li>
    <li>✅ パリの現地コミュニティ・ミートアップ会に参加できる</li>
  </ul>
  <p>まずは<strong>無料のLINE相談</strong>から。エリア診断ZOOMや留学相談ZOOMも無料で受けられます！</p>
  <p style="text-align: center; margin-bottom: 0;">
    <a href="https://lin.ee/7iwiIBE" style="display: inline-block; background: #06c755; color: white; padding: 14px 32px; border-radius: 50px; text-decoration: none; font-weight: bold; font-size: 16px;">
      💬 LINEで無料相談する
    </a>
  </p>
  <p style="text-align: center; font-size: 13px; color: #888; margin-top: 12px;">登録後、エリア診断ZOOM・無料留学相談ZOOMのご予約ができます</p>
</div>
"""

# ── SEOキーワードリスト ────────────────────────────────
KEYWORD_POOL = [
    {"main": "フランス留学 費用", "sub": ["フランス 大学 学費", "フランス留学 奨学金", "フランス 生活費 学生"], "angle": "費用の全体像と節約術"},
    {"main": "フランス語学学校 おすすめ パリ", "sub": ["パリ 語学学校 選び方", "フランス語 短期留学", "アリアンス・フランセーズ"], "angle": "学校の選び方と特徴比較"},
    {"main": "フランス 学生ビザ 申請 方法", "sub": ["Etudes en France", "France-Visas 書き方", "フランス ビザ 必要書類 2024"], "angle": "ビザ申請の手順と注意点"},
    {"main": "フランス留学 準備 やること", "sub": ["フランス留学 持ち物リスト", "渡仏前 チェックリスト", "海外留学 保険 おすすめ"], "angle": "渡仏前に必ずやること一覧"},
    {"main": "パリ アパート 探し方 留学生", "sub": ["コロカシオン パリ", "学生寮 フランス", "パリ 住居 短期"], "angle": "住む場所の選択肢と探し方"},
    {"main": "フランス 短期留学 1ヶ月", "sub": ["フランス語 上達 コツ", "短期留学 メリット デメリット", "1ヶ月 フランス 費用"], "angle": "短期でも得られる経験と効果"},
    {"main": "ワーキングホリデー フランス 条件", "sub": ["フランス ワーホリ ビザ 申請", "ワーホリ フランス 仕事", "フランス ワーホリ 費用"], "angle": "ワーホリで行くフランスの全貌"},
    {"main": "フランス 銀行口座 開設 留学生", "sub": ["Wise フランス", "フランス SIMカード おすすめ", "パリ 生活費 1ヶ月"], "angle": "現地生活を始めるための手続き"},
    {"main": "フランス留学 語学学校 費用", "sub": ["語学学校 学費 比較", "フランス語 レベル 上げ方", "語学学校 スケジュール"], "angle": "語学学校の費用と選び方"},
    {"main": "パリ 観光 留学生 おすすめ", "sub": ["パリ 穴場 スポット", "フランス 週末 旅行", "パリ 美術館 無料"], "angle": "留学中に行くべきパリのスポット"},
    {"main": "フランス 文化 違い 日本", "sub": ["フランス人 習慣", "パリ カフェ 文化", "フランス マナー 注意"], "angle": "知っておくべきフランスの文化"},
    {"main": "フランス留学 エージェント 選び方", "sub": ["留学エージェント 比較", "現地エージェント メリット", "フランス留学 サポート"], "angle": "エージェント選びで失敗しないために"},
]

# ── 記事生成 ───────────────────────────────────────────
def generate_article(keyword_data: dict) -> dict:
    main_kw = keyword_data["main"]
    sub_kws  = "、".join(keyword_data["sub"])
    angle    = keyword_data["angle"]
    today    = datetime.now().strftime("%Y年%m月")

    prompt = f"""
あなたはパリ在住12年のフランス留学エージェント「AP留学」の公式ブロガーです。
以下の条件でSEOに強いブログ記事を日本語で書いてください。

【メインキーワード】{main_kw}
【関連キーワード】{sub_kws}
【記事の切り口】{angle}
【対象読者】フランス・パリ留学を検討中の方、または準備中の方（高校生〜社会人）
【文字数】2000〜2500文字
【執筆日】{today}（最新情報として書くこと）
【トーン】親しみやすく、現地目線のリアルな情報を届ける感じ

【重要な執筆ルール】
1. 古い情報や曖昧な情報は書かない。「〜が一般的です」「〜の場合があります」など現地感のある表現を使う
2. 具体的な数字・金額・期間を入れてリアリティを出す
3. 「パリ在住だからわかる」「現地エージェントだから知っている」というトーンを自然に入れる
4. 読者の不安や悩みに共感してから解決策を提示する
5. AP留学のサービスを記事の流れに合わせて自然に1〜2箇所紹介する（押しつけがましくなく）

【AP留学サービス情報（記事内で自然に紹介する）】
{AP_SERVICE_INFO}

【必須構成】
1. タイトル（H1）: メインキーワードを含む、読みたくなるタイトル（32〜45文字）
2. リード文（150〜200字）: 読者の悩みに共感し、この記事で何がわかるかを伝える
3. H2見出し 3〜4個（各800〜600字程度）
4. まとめ（200字）: 読者への行動を促す
5. SEOメタディスクリプション（120〜130文字）

【出力形式】必ずJSON形式のみで返してください（前後に余分なテキスト不要）：
{{
  "title": "記事タイトル",
  "meta_description": "メタディスクリプション（120〜130文字）",
  "content": "HTML形式の本文（h2, p, ul, li, strong タグ使用）",
  "tags": ["タグ1", "タグ2", "タグ3", "タグ4"],
  "focus_keyword": "{main_kw}"
}}
"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=5000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    article = json.loads(raw)

    # CTA（導線）を本文末尾に追加
    article["content"] = article["content"] + CTA_HTML

    return article


# ── WordPress投稿 ──────────────────────────────────────
def post_to_wordpress(article: dict) -> dict:
    endpoint = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/posts"

    payload = {
        "title":   article["title"],
        "content": article["content"],
        "status":  "publish",
        "excerpt": article.get("meta_description", ""),
        "tags":    get_or_create_tags(article.get("tags", [])),
        "meta": {
            "_yoast_wpseo_metadesc":  article.get("meta_description", ""),
            "_yoast_wpseo_focuskw":   article.get("focus_keyword", ""),
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
    tag_ids = []
    base = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/tags"
    auth = (WP_USER, WP_APP_PASS)

    for name in tag_names:
        r = requests.get(base, params={"search": name}, auth=auth, timeout=15)
        results = r.json()
        if results:
            tag_ids.append(results[0]["id"])
        else:
            r2 = requests.post(base, json={"name": name}, auth=auth, timeout=15)
            if r2.status_code == 201:
                tag_ids.append(r2.json()["id"])

    return tag_ids


# ── 使用済みキーワードの管理 ──────────────────────────
def get_used_keywords() -> list:
    try:
        with open("post_log.jsonl", "r", encoding="utf-8") as f:
            return [json.loads(line)["keyword"] for line in f if line.strip()]
    except FileNotFoundError:
        return []

def pick_keyword(pool: list) -> dict:
    used = get_used_keywords()
    unused = [k for k in pool if k["main"] not in used]
    # 全部使ったらリセット
    if not unused:
        unused = pool
    return random.choice(unused)


# ── メイン処理 ─────────────────────────────────────────
def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] AP留学ブログ 自動投稿 開始")

    keyword = pick_keyword(KEYWORD_POOL)
    print(f"  キーワード: {keyword['main']}")

    print("  Claude AI で記事を生成中...")
    article = generate_article(keyword)
    print(f"  タイトル: {article['title']}")

    print("  WordPress に投稿中...")
    result = post_to_wordpress(article)
    print(f"  ✅ 公開完了！URL: {result.get('link', '不明')}")

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

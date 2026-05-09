"""
AP留学 カルーセルテキスト自動生成 → Discord送信スクリプト v3
- WordPressから最新記事を取得
- Claude AIでカルーセル7枚分のテキストを生成
- CanvaテンプレートURLと一緒にDiscordに送信
- AikoさんはDiscordを見てCanvaにコピペするだけ！
"""

import os
import json
import re
import requests
from datetime import datetime
from anthropic import Anthropic

# ── 設定 ──────────────────────────────────────────────
WP_URL          = os.environ["WP_URL"]
WP_USER         = os.environ["WP_USER"]
WP_APP_PASS     = os.environ["WP_APP_PASS"]
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

CANVA_TEMPLATE  = "https://canva.link/rtc84lclekzxkl5"

client = Anthropic()


# ── WordPressから最新記事を取得 ────────────────────────
def get_latest_post() -> dict | None:
    try:
        resp = requests.get(
            f"{WP_URL.rstrip('/')}/wp-json/wp/v2/posts",
            params={"per_page": 1, "status": "publish", "orderby": "date", "order": "desc"},
            auth=(WP_USER, WP_APP_PASS),
            timeout=15
        )
        resp.raise_for_status()
        posts = resp.json()
        return posts[0] if posts else None
    except Exception as e:
        print(f"  ⚠️ WordPress記事取得失敗: {e}")
        return None


# ── Claude AIでカルーセルテキスト生成 ─────────────────
def generate_carousel_texts(post: dict) -> dict:
    title   = post.get("title", {}).get("rendered", "")
    url     = post.get("link", "")
    content = re.sub(r'<[^>]+>', '', post.get("content", {}).get("rendered", ""))
    content = content[:3000]

    prompt = f"""
あなたはAP留学（パリ在住12年のフランス留学エージェント）のSNS担当です。
以下のブログ記事をInstagramカルーセル投稿（7枚）用のテキストにまとめてください。

【ブログタイトル】{title}
【ブログURL】{url}
【ブログ本文】{content}

【ターゲット読者】
フランス留学・パリ滞在に憧れる日本人女性（高校生〜40代）
パリのリアルな情報を求めている人

【トーン・口調】
- 親しみやすく、テンションが上がる感じ
- 「パリ在住12年だからわかる！」というリアル感
- 押しつけがましくなく、読者に寄り添う
- 体言止めや短い文でテンポよく

【カルーセル構成 7枚】
1枚目（表紙）：
- キャッチーなタイトル（例：「フランスビザ申請、実はこの順番が正解でした」）
- サブタイトル（例：「パリ在住12年が教えるリアルな話」）

2〜6枚目（POINT 1〜5）：
- ラベル：「POINT 1」〜「POINT 5」
- 見出し：15文字以内でインパクトある一言
- 本文：2〜3行、60文字以内。具体的な数字や体験談を入れる

7枚目（CTA）：
- 見出し：「まずはLINEで相談してみて！」
- 本文：「無料でエリア診断ZOOMや留学相談ZOOMができます。パリ在住スタッフが時差なしで対応します◎」

【インスタキャプション】
- 最初の1行でつかみ（絵文字あり）
- 記事の要点を3〜5行でまとめ
- 「詳しくはプロフのリンクから！」
- ハッシュタグ10個（#フランス留学 #パリ留学 #フランス語学学校 など関連するもの）

【出力形式】JSONのみ返してください：
{{
  "slides": [
    {{
      "slide_num": 1,
      "label": "AP留学",
      "heading": "表紙タイトル",
      "subheading": "パリ在住12年が教えるリアルな話",
      "body": ""
    }},
    {{
      "slide_num": 2,
      "label": "POINT 1",
      "heading": "見出し",
      "subheading": "",
      "body": "本文テキスト"
    }},
    {{
      "slide_num": 3,
      "label": "POINT 2",
      "heading": "見出し",
      "subheading": "",
      "body": "本文テキスト"
    }},
    {{
      "slide_num": 4,
      "label": "POINT 3",
      "heading": "見出し",
      "subheading": "",
      "body": "本文テキスト"
    }},
    {{
      "slide_num": 5,
      "label": "POINT 4",
      "heading": "見出し",
      "subheading": "",
      "body": "本文テキスト"
    }},
    {{
      "slide_num": 6,
      "label": "POINT 5",
      "heading": "見出し",
      "subheading": "",
      "body": "本文テキスト"
    }},
    {{
      "slide_num": 7,
      "label": "AP留学",
      "heading": "まずはLINEで相談してみて！",
      "subheading": "",
      "body": "無料でエリア診断ZOOMや留学相談ZOOMができます。パリ在住スタッフが時差なしで対応します◎"
    }}
  ],
  "caption": "インスタキャプション全文（ハッシュタグ含む）",
  "blog_title": "{title}",
  "blog_url": "{url}"
}}
"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    return json.loads(raw, strict=False)


# ── Discordにテキストを送信 ────────────────────────────
def send_to_discord(carousel_data: dict):
    slides     = carousel_data.get("slides", [])
    caption    = carousel_data.get("caption", "")
    blog_title = carousel_data.get("blog_title", "")
    blog_url   = carousel_data.get("blog_url", "")

    # ── メッセージ1：ヘッダー ──
    header = (
        f"# 📸 インスタカルーセル テキストができました！\n\n"
        f"📝 **元記事：** {blog_title}\n"
        f"🔗 {blog_url}\n\n"
        f"🎨 **Canvaテンプレートはこちら：**\n{CANVA_TEMPLATE}\n\n"
        f"⬇️ 以下のテキストをCanvaにコピペしてください！"
    )
    requests.post(DISCORD_WEBHOOK, json={"content": header}, timeout=15)

    # ── メッセージ2：各スライドのテキスト ──
    slide_text = "## 📋 各スライドのテキスト\n\n"
    for slide in slides:
        num     = slide.get("slide_num", "")
        label   = slide.get("label", "")
        heading = slide.get("heading", "")
        sub     = slide.get("subheading", "")
        body    = slide.get("body", "")

        slide_text += f"---\n"
        slide_text += f"**【スライド {num}】{label}**\n"
        if heading:
            slide_text += f"見出し：`{heading}`\n"
        if sub:
            slide_text += f"サブ：`{sub}`\n"
        if body:
            slide_text += f"本文：`{body}`\n"
        slide_text += "\n"

    requests.post(DISCORD_WEBHOOK, json={"content": slide_text}, timeout=15)

    # ── メッセージ3：キャプション ──
    caption_text = (
        f"## ✍️ インスタキャプション\n\n"
        f"```\n{caption}\n```\n\n"
        f"👆 上のテキストをそのままインスタに貼り付けてください！"
    )
    requests.post(DISCORD_WEBHOOK, json={"content": caption_text}, timeout=15)

    # ── メッセージ4：作業手順リマインダー ──
    reminder = (
        f"## ✅ 作業手順\n"
        f"1. Canvaテンプレートを開く → {CANVA_TEMPLATE}\n"
        f"2. 各スライドにテキストをコピペ\n"
        f"3. 必要なら写真を差し替え\n"
        f"4. インスタにキャプションと一緒に投稿\n\n"
        f"お疲れさまです！🗼✨"
    )
    requests.post(DISCORD_WEBHOOK, json={"content": reminder}, timeout=15)

    print("  ✅ Discord送信完了！")


# ── メイン処理 ─────────────────────────────────────────
def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] カルーセルテキスト生成 開始")

    # WordPress最新記事
    print("  WordPressから記事を取得中...")
    post = get_latest_post()
    if not post:
        print("  ⚠️ 記事が見つかりませんでした")
        return
    print(f"  記事: {post.get('title',{}).get('rendered','')}")

    # カルーセルテキスト生成
    print("  Claude AI でカルーセルテキストを生成中...")
    carousel_data = generate_carousel_texts(post)
    print(f"  {len(carousel_data.get('slides', []))}枚分のテキスト生成完了")

    # Discord送信
    print("  Discordに送信中...")
    send_to_discord(carousel_data)


if __name__ == "__main__":
    main()

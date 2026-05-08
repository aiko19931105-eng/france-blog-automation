"""
AP留学 インスタカルーセル自動生成 → Discord送信スクリプト
- WordPressから最新記事を取得
- Claude AIでカルーセル7枚分のテキストを生成
- Pillowでフランスらしいデザイン画像を自動生成
- Discordに画像7枚＋キャプションを送信
"""

import os
import json
import textwrap
import requests
import io
from datetime import datetime, timedelta
from anthropic import Anthropic
from PIL import Image, ImageDraw, ImageFont

# ── 設定 ──────────────────────────────────────────────
WP_URL          = os.environ["WP_URL"]
WP_USER         = os.environ["WP_USER"]
WP_APP_PASS     = os.environ["WP_APP_PASS"]
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

client = Anthropic()

# ── AP留学ブランドカラー ───────────────────────────────
COLORS = {
    "bg":          "#1a1a2e",   # 深紺（背景）
    "accent":      "#9b59b6",   # パープル
    "accent2":     "#e8b4d0",   # ライトピンク
    "text":        "#ffffff",   # 白
    "subtext":     "#cccccc",   # グレー
    "card":        "#16213e",   # カード背景
    "gradient_top":"#2d1b4e",   # グラデ上
}

def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# ── WordPressから最新記事を取得 ────────────────────────
def get_latest_post() -> dict | None:
    """7日前に投稿された記事を取得"""
    try:
        resp = requests.get(
            f"{WP_URL.rstrip('/')}/wp-json/wp/v2/posts",
            params={"per_page": 1, "status": "publish", "orderby": "date", "order": "desc"},
            auth=(WP_USER, WP_APP_PASS),
            timeout=15
        )
        resp.raise_for_status()
        posts = resp.json()
        if posts:
            return posts[0]
        return None
    except Exception as e:
        print(f"  ⚠️ WordPress記事取得失敗: {e}")
        return None


# ── Claude AIでカルーセルテキスト生成 ─────────────────
def generate_carousel_texts(post: dict) -> dict:
    title   = post.get("title", {}).get("rendered", "")
    # HTMLタグを除去
    import re
    content = re.sub(r'<[^>]+>', '', post.get("content", {}).get("rendered", ""))
    content = content[:3000]  # 長すぎる場合は切り詰め

    prompt = f"""
あなたはAP留学（パリ在住12年のフランス留学エージェント）のSNS担当です。
以下のブログ記事をInstagramカルーセル投稿（7枚）用にまとめてください。

【ブログタイトル】{title}
【ブログ本文】{content}

【カルーセル構成】
- 1枚目：タイトルカード（キャッチーな見出し＋サブタイトル）
- 2〜6枚目：記事の要点を1枚1ポイントでまとめる（各ポイントに絵文字）
- 7枚目：まとめ＋AP留学へのCTA（「LINEで無料相談はこちら👇」）

【ルール】
- 各スライドのテキストは短く（見出し20文字以内、本文60文字以内）
- フランス在住者ならではのリアルな視点を入れる
- 読者が「保存したい！」と思えるような有益な内容に
- インスタのキャプションも作成（ハッシュタグ10個含む）

【出力形式】JSONのみで返してください：
{{
  "slides": [
    {{"heading": "見出し", "body": "本文テキスト", "emoji": "🗼"}},
    {{"heading": "見出し", "body": "本文テキスト", "emoji": "💰"}},
    {{"heading": "見出し", "body": "本文テキスト", "emoji": "📚"}},
    {{"heading": "見出し", "body": "本文テキスト", "emoji": "🏠"}},
    {{"heading": "見出し", "body": "本文テキスト", "emoji": "✈️"}},
    {{"heading": "見出し", "body": "本文テキスト", "emoji": "💡"}},
    {{"heading": "まとめ", "body": "LINEで無料相談はこちら👇 @ap_ryugaku", "emoji": "📩"}}
  ],
  "caption": "インスタキャプション本文（ハッシュタグ10個含む）",
  "blog_title": "{title}"
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


# ── 画像生成 ───────────────────────────────────────────
def create_slide_image(slide: dict, slide_num: int, total: int) -> bytes:
    W, H = 1080, 1080
    img  = Image.new("RGB", (W, H), hex_to_rgb(COLORS["bg"]))
    draw = ImageDraw.Draw(img)

    # グラデーション風の背景装飾
    for i in range(300):
        alpha = int(60 * (1 - i / 300))
        color = hex_to_rgb(COLORS["gradient_top"])
        draw.rectangle([0, i, W, i+1], fill=(*color, alpha))

    # 上部アクセントライン
    draw.rectangle([0, 0, W, 8], fill=hex_to_rgb(COLORS["accent"]))

    # 左側アクセントライン
    draw.rectangle([0, 0, 8, H], fill=hex_to_rgb(COLORS["accent"]))

    # 右下デコレーション円
    draw.ellipse([W-200, H-200, W+100, H+100],
                 fill=hex_to_rgb(COLORS["gradient_top"]))
    draw.ellipse([W-150, H-150, W+50, H+50],
                 fill=hex_to_rgb(COLORS["accent"]))

    # フォント（デフォルトフォントを使用）
    try:
        font_large  = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 72)
        font_medium = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 48)
        font_body   = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 36)
        font_small  = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 28)
    except:
        font_large  = ImageFont.load_default()
        font_medium = font_large
        font_body   = font_large
        font_small  = font_large

    # スライド番号
    draw.text((30, 20), f"{slide_num}/{total}",
              font=font_small, fill=hex_to_rgb(COLORS["accent2"]))

    # ブランド名
    draw.text((W-200, 20), "AP留学",
              font=font_small, fill=hex_to_rgb(COLORS["accent2"]))

    # 絵文字（大きく中央上部に）
    emoji_text = slide.get("emoji", "🗼")
    draw.text((W//2, 280), emoji_text,
              font=font_large, fill=hex_to_rgb(COLORS["text"]),
              anchor="mm")

    # 見出し（中央）
    heading = slide.get("heading", "")
    # 長い場合は折り返し
    wrapped_heading = textwrap.fill(heading, width=14)
    draw.text((W//2, 480), wrapped_heading,
              font=font_medium, fill=hex_to_rgb(COLORS["text"]),
              anchor="mm", align="center")

    # 本文
    body = slide.get("body", "")
    wrapped_body = textwrap.fill(body, width=22)
    draw.text((W//2, 680), wrapped_body,
              font=font_body, fill=hex_to_rgb(COLORS["subtext"]),
              anchor="mm", align="center")

    # 下部アクセントライン
    draw.rectangle([0, H-8, W, H], fill=hex_to_rgb(COLORS["accent"]))

    # 画像をバイト列に変換
    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf.getvalue()


# ── Discordに送信 ──────────────────────────────────────
def send_to_discord(carousel_data: dict, images: list[bytes]):
    """画像7枚＋キャプションをDiscordに送信"""

    # まずテキストメッセージを送信
    blog_title = carousel_data.get("blog_title", "")
    caption    = carousel_data.get("caption", "")

    intro_message = {
        "content": (
            f"📸 **インスタカルーセル準備できました！**\n\n"
            f"📝 **元記事：** {blog_title}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"**【インスタキャプション】**\n{caption}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⬇️ カルーセル画像7枚（このまま使えます！）"
        )
    }

    requests.post(DISCORD_WEBHOOK, json=intro_message, timeout=15)

    # 画像を1枚ずつ送信
    for i, img_bytes in enumerate(images, 1):
        files = {
            "file": (f"carousel_{i:02d}.png", img_bytes, "image/png")
        }
        payload = {"content": f"**スライド {i}/7**"}
        requests.post(DISCORD_WEBHOOK, data=payload, files=files, timeout=30)
        print(f"  📤 スライド {i}/7 送信完了")

    print("  ✅ Discord送信完了！")


# ── メイン処理 ─────────────────────────────────────────
def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] カルーセル生成 開始")

    # WordPressから最新記事を取得
    print("  WordPressから記事を取得中...")
    post = get_latest_post()
    if not post:
        print("  ⚠️ 記事が見つかりませんでした")
        return

    title = post.get("title", {}).get("rendered", "タイトルなし")
    print(f"  記事: {title}")

    # カルーセルテキスト生成
    print("  Claude AI でカルーセルテキストを生成中...")
    carousel_data = generate_carousel_texts(post)
    slides = carousel_data.get("slides", [])
    print(f"  {len(slides)}枚分のテキスト生成完了")

    # 画像生成
    print("  画像を生成中...")
    images = []
    for i, slide in enumerate(slides, 1):
        img_bytes = create_slide_image(slide, i, len(slides))
        images.append(img_bytes)
        print(f"  🖼️  スライド {i}/{len(slides)} 生成完了")

    # Discord送信
    print("  Discordに送信中...")
    send_to_discord(carousel_data, images)


if __name__ == "__main__":
    main()

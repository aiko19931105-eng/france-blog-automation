"""
AP留学 インスタカルーセル自動生成 → Discord送信スクリプト v2
- パリ写真を背景に文字を重ねるおしゃれなデザイン
- 40代日本人女性がわくわくするAP留学らしいスタイル
- 絵文字対応
"""

import os
import json
import re
import textwrap
import requests
import io
from datetime import datetime
from anthropic import Anthropic
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── 設定 ──────────────────────────────────────────────
WP_URL          = os.environ["WP_URL"]
WP_USER         = os.environ["WP_USER"]
WP_APP_PASS     = os.environ["WP_APP_PASS"]
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
UNSPLASH_KEY    = os.environ["UNSPLASH_KEY"]

client = Anthropic()

# ── カラーパレット（AP留学らしいベージュ×ピンク×ゴールド） ──
OVERLAY_COLOR  = (20, 20, 40, 170)    # 深紺半透明オーバーレイ
TEXT_WHITE     = (255, 255, 255)
TEXT_CREAM     = (255, 240, 220)
ACCENT_PINK    = (232, 180, 208)
ACCENT_GOLD    = (212, 175, 100)
LINE_COLOR     = (255, 255, 255, 180)

# ── Unsplashからパリ写真を取得 ─────────────────────────
PARIS_QUERIES = [
    "paris eiffel tower golden hour",
    "paris cafe terrace french",
    "paris seine river bridge",
    "paris montmartre street",
    "paris louvre architecture",
    "paris haussmann boulevard",
    "paris flower market",
]

def fetch_paris_photo() -> bytes | None:
    """Unsplashからパリ写真を取得"""
    import random
    query = random.choice(PARIS_QUERIES)
    try:
        resp = requests.get(
            "https://api.unsplash.com/photos/random",
            params={"query": query, "orientation": "squarish", "content_filter": "high"},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            timeout=15
        )
        resp.raise_for_status()
        data     = resp.json()
        img_url  = data["urls"]["regular"]
        img_resp = requests.get(img_url, timeout=30)
        img_resp.raise_for_status()
        return img_resp.content
    except Exception as e:
        print(f"  ⚠️ Unsplash取得失敗: {e}")
        return None


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
    content = re.sub(r'<[^>]+>', '', post.get("content", {}).get("rendered", ""))
    content = content[:3000]

    prompt = f"""
あなたはAP留学（パリ在住12年のフランス留学エージェント）のSNS担当です。
以下のブログ記事をInstagramカルーセル投稿（7枚）用にまとめてください。

【ブログタイトル】{title}
【ブログ本文】{content}

【ターゲット】フランス留学・パリ滞在に憧れる40代前後の日本人女性
【トーン】わくわく感があり、親しみやすく、パリ在住者ならではのリアルな情報

【カルーセル構成】
- 1枚目：タイトルカード（キャッチーな見出し＋「パリ在住12年が教える」などのサブタイトル）
- 2〜6枚目：記事の要点を1枚1ポイント（短く、具体的に）
- 7枚目：まとめ＋「LINEで無料相談受付中」CTA

【重要ルール】
- 絵文字は使わない（画像に入れられないため）
- 各スライドの見出しは15文字以内
- 本文は50文字以内、2〜3行で収まる量
- 読者が「保存したい！」と思える有益な内容に

【出力形式】JSONのみ返してください：
{{
  "slides": [
    {{"heading": "見出し", "body": "本文テキスト", "label": "AP留学"}},
    {{"heading": "見出し", "body": "本文テキスト", "label": "POINT 1"}},
    {{"heading": "見出し", "body": "本文テキスト", "label": "POINT 2"}},
    {{"heading": "見出し", "body": "本文テキスト", "label": "POINT 3"}},
    {{"heading": "見出し", "body": "本文テキスト", "label": "POINT 4"}},
    {{"heading": "見出し", "body": "本文テキスト", "label": "POINT 5"}},
    {{"heading": "まとめ", "body": "LINEで無料相談受付中\\n@ap_ryugaku", "label": "AP留学"}}
  ],
  "caption": "インスタキャプション（ハッシュタグ10個含む、改行あり）",
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


# ── フォント読み込み ───────────────────────────────────
def load_fonts():
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    ]
    font_path_regular = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]

    bold_path    = None
    regular_path = None

    for p in font_paths:
        try:
            ImageFont.truetype(p, 10)
            bold_path = p
            break
        except:
            continue

    for p in font_path_regular:
        try:
            ImageFont.truetype(p, 10)
            regular_path = p
            break
        except:
            continue

    if bold_path and regular_path:
        return {
            "xl":     ImageFont.truetype(bold_path, 80),
            "large":  ImageFont.truetype(bold_path, 58),
            "medium": ImageFont.truetype(bold_path, 42),
            "body":   ImageFont.truetype(regular_path, 34),
            "small":  ImageFont.truetype(regular_path, 26),
            "label":  ImageFont.truetype(bold_path, 24),
        }
    else:
        f = ImageFont.load_default()
        return {k: f for k in ["xl","large","medium","body","small","label"]}


# ── スライド画像生成 ───────────────────────────────────
def create_slide_image(slide: dict, slide_num: int, total: int,
                        bg_bytes: bytes | None, fonts: dict) -> bytes:
    W, H = 1080, 1080

    # 背景画像
    if bg_bytes:
        bg = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
        bg = bg.resize((W, H), Image.LANCZOS)
        # 軽くぼかして文字を読みやすく
        bg = bg.filter(ImageFilter.GaussianBlur(radius=2))
    else:
        bg = Image.new("RGBA", (W, H), (30, 30, 60, 255))

    # 半透明オーバーレイ
    overlay = Image.new("RGBA", (W, H), OVERLAY_COLOR)
    img     = Image.alpha_composite(bg, overlay).convert("RGB")
    draw    = ImageDraw.Draw(img)

    # 上下のゴールドライン
    draw.rectangle([0, 0, W, 6], fill=ACCENT_GOLD)
    draw.rectangle([0, H-6, W, H], fill=ACCENT_GOLD)

    # 左右の細いラインで枠感を演出
    draw.rectangle([0, 0, 5, H], fill=ACCENT_GOLD)
    draw.rectangle([W-5, 0, W, H], fill=ACCENT_GOLD)

    # ブランド名（右上）
    draw.text((W-40, 30), "AP留学", font=fonts["label"],
              fill=ACCENT_GOLD, anchor="ra")

    # スライド番号（左上）
    draw.text((40, 30), f"{slide_num} / {total}", font=fonts["label"],
              fill=TEXT_CREAM, anchor="la")

    # ラベル（POINT 1 など）
    label = slide.get("label", "")
    if label:
        lw = draw.textlength(label, font=fonts["label"])
        lx = W // 2 - lw // 2
        draw.rectangle([lx-16, 200, lx+lw+16, 244], fill=ACCENT_GOLD)
        draw.text((W//2, 222), label, font=fonts["label"],
                  fill=(20, 20, 40), anchor="mm")

    # 見出し（中央）
    heading = slide.get("heading", "")
    wrapped_h = textwrap.fill(heading, width=12)
    draw.text((W//2, 420), wrapped_h, font=fonts["large"],
              fill=TEXT_WHITE, anchor="mm", align="center")

    # 区切り線
    draw.rectangle([W//2-80, 510, W//2+80, 514], fill=ACCENT_PINK)

    # 本文
    body = slide.get("body", "")
    wrapped_b = textwrap.fill(body, width=20)
    draw.text((W//2, 680), wrapped_b, font=fonts["body"],
              fill=TEXT_CREAM, anchor="mm", align="center")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ── Discordに送信 ──────────────────────────────────────
def send_to_discord(carousel_data: dict, images: list):
    blog_title = carousel_data.get("blog_title", "")
    caption    = carousel_data.get("caption", "")

    intro = {
        "content": (
            f"📸 **インスタカルーセル準備できました！**\n\n"
            f"📝 元記事：{blog_title}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"**【インスタキャプション】**\n{caption}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⬇️ カルーセル画像 {len(images)}枚（このまま使えます！）"
        )
    }
    requests.post(DISCORD_WEBHOOK, json=intro, timeout=15)

    for i, img_bytes in enumerate(images, 1):
        files   = {"file": (f"slide_{i:02d}.png", img_bytes, "image/png")}
        payload = {"content": f"**スライド {i}/{len(images)}**"}
        requests.post(DISCORD_WEBHOOK, data=payload, files=files, timeout=30)
        print(f"  📤 スライド {i}/{len(images)} 送信完了")

    print("  ✅ Discord送信完了！")


# ── メイン処理 ─────────────────────────────────────────
def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] カルーセル生成 開始")

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
    slides        = carousel_data.get("slides", [])
    print(f"  {len(slides)}枚分のテキスト生成完了")

    # フォント読み込み
    fonts = load_fonts()

    # パリ背景写真を1枚取得（全スライド共通）
    print("  📷 パリ写真を取得中...")
    bg_bytes = fetch_paris_photo()

    # 画像生成
    print("  画像を生成中...")
    images = []
    for i, slide in enumerate(slides, 1):
        img_bytes = create_slide_image(slide, i, len(slides), bg_bytes, fonts)
        images.append(img_bytes)
        print(f"  🖼️  スライド {i}/{len(slides)} 生成完了")

    # Discord送信
    print("  Discordに送信中...")
    send_to_discord(carousel_data, images)


if __name__ == "__main__":
    main()

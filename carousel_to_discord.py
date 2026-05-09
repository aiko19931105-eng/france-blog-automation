"""
AP留学 カルーセル自動生成 → Discord送信 v4
- 1枚目：Unsplashパリ写真背景＋いろは角クラシック白文字
- 2〜6枚目：ベージュ×サーモンピンク＋水玉デコ＋NEXTボタン
- 7枚目：CTA＋LINEボタン＋エリア診断ZOOM
"""

import os, json, re, textwrap, requests, io, urllib.request
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WP_URL          = os.environ["WP_URL"]
WP_USER         = os.environ["WP_USER"]
WP_APP_PASS     = os.environ["WP_APP_PASS"]
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
UNSPLASH_KEY    = os.environ["UNSPLASH_KEY"]

client = Anthropic()

W, H = 1080, 1350  # 4:5 縦長

# ── カラー ─────────────────────────────────────────────
BG        = (253, 246, 240)
TOPBAR    = (232, 168, 152)
ACCENT    = (196, 120,  96)
BOXBORDER = (224, 168, 152)
TEXTDARK  = ( 58,  32,  16)
TEXTSUB   = (154, 112,  96)
WHITE     = (255, 255, 255)
PINK_DOT  = (245, 196, 176)
GREEN_LINE= ( 76, 175,  80)

# ── フォント取得（いろは角クラシック） ─────────────────
def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font_dir  = Path("/tmp/iroha")
    font_path = font_dir / "IrohaKakuClassic.ttf"
    if not font_path.exists():
        font_dir.mkdir(exist_ok=True)
        url = "https://github.com/hashikemu/iroha-kakukurashikku/releases/download/v1.00/IrohaKakuClassic.ttf"
        try:
            urllib.request.urlretrieve(url, font_path)
        except Exception:
            # フォールバック: Noto Serif CJK
            for p in [
                "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            ]:
                if Path(p).exists():
                    return ImageFont.truetype(p, size)
            return ImageFont.load_default()
    try:
        return ImageFont.truetype(str(font_path), size)
    except Exception:
        return ImageFont.load_default()

# ── Unsplashからパリ写真取得 ───────────────────────────
PARIS_QUERIES = [
    "paris eiffel tower golden hour",
    "paris cafe terrace street",
    "paris metro sign architecture",
    "paris seine river bridge sunset",
    "paris montmartre cobblestone",
    "paris haussmann boulevard",
]

def fetch_paris_photo() -> bytes | None:
    import random
    query = random.choice(PARIS_QUERIES)
    try:
        r = requests.get(
            "https://api.unsplash.com/photos/random",
            params={"query": query, "orientation": "portrait", "content_filter": "high"},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            timeout=15
        )
        r.raise_for_status()
        img_url = r.json()["urls"]["regular"]
        ir = requests.get(img_url, timeout=30)
        ir.raise_for_status()
        return ir.content
    except Exception as e:
        print(f"  ⚠️ Unsplash失敗: {e}")
        return None

# ── WordPress最新記事取得 ──────────────────────────────
def get_latest_post() -> dict | None:
    try:
        r = requests.get(
            f"{WP_URL.rstrip('/')}/wp-json/wp/v2/posts",
            params={"per_page": 1, "status": "publish", "orderby": "date", "order": "desc"},
            auth=(WP_USER, WP_APP_PASS), timeout=15
        )
        r.raise_for_status()
        posts = r.json()
        return posts[0] if posts else None
    except Exception as e:
        print(f"  ⚠️ WordPress失敗: {e}")
        return None

# ── Claude AIでテキスト生成 ────────────────────────────
def generate_texts(post: dict) -> dict:
    title   = post.get("title", {}).get("rendered", "")
    url     = post.get("link", "")
    content = re.sub(r'<[^>]+>', '', post.get("content", {}).get("rendered", ""))[:3000]

    prompt = f"""
あなたはAP留学のSNS担当です。
ブログ記事をInstagramカルーセル（7枚）用テキストにまとめてください。

【ブログタイトル】{title}
【本文】{content}

【ターゲット】パリ・フランスに憧れる日本人女性（高校生〜40代）
【トーン】わくわく感があり親しみやすい。パリ在住12年のリアル感。

【構成】
1枚目（表紙）: キャッチーなタイトル（20文字以内）＋サブタイトル（「パリ在住12年が教えるリアルな話」など）
2〜6枚目（POINT 1〜5）: 見出し15文字以内、箇条書き本文3〜4行（各行30文字以内）
7枚目（CTA）: 見出し「あなたにぴったりの留学、一緒に探しましょう」固定、本文固定

【絵文字・装飾文字は使わない】（画像内で文字化けするため）

JSONのみ返してください：
{{
  "slides": [
    {{"num":1,"label":"AP留学","heading":"タイトル","sub":"パリ在住12年が教えるリアルな話","bullets":[]}},
    {{"num":2,"label":"POINT 1","heading":"見出し","sub":"","bullets":["箇条書き1","箇条書き2","箇条書き3"]}},
    {{"num":3,"label":"POINT 2","heading":"見出し","sub":"","bullets":["箇条書き1","箇条書き2","箇条書き3"]}},
    {{"num":4,"label":"POINT 3","heading":"見出し","sub":"","bullets":["箇条書き1","箇条書き2","箇条書き3"]}},
    {{"num":5,"label":"POINT 4","heading":"見出し","sub":"","bullets":["箇条書き1","箇条書き2","箇条書き3"]}},
    {{"num":6,"label":"POINT 5","heading":"見出し","sub":"","bullets":["箇条書き1","箇条書き2","箇条書き3"]}},
    {{"num":7,"label":"AP留学","heading":"あなたにぴったりの留学、一緒に探しましょう","sub":"","bullets":[]}}
  ],
  "caption": "インスタキャプション（ハッシュタグ10個含む）",
  "blog_title": "{title}",
  "blog_url": "{url}"
}}
"""
    r = client.messages.create(
        model="claude-sonnet-4-5", max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = r.content[0].text.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return json.loads(raw, strict=False)

# ── ページナビ描画 ─────────────────────────────────────
def draw_top_bar(draw: ImageDraw.Draw, current: int, total: int):
    draw.rectangle([0, 0, W, 110], fill=TOPBAR)
    cx = W // 2
    total_w = total * 52 - 8
    sx = cx - total_w // 2
    for i in range(1, total + 1):
        x = sx + (i - 1) * 52 + 26
        if i == current:
            r = 30
            draw.ellipse([x-r, 18, x+r, 18+r*2], fill=WHITE)
            f = get_font(28)
            draw.text((x, 18+r), str(i), font=f, fill=ACCENT, anchor="mm")
        else:
            r = 18
            draw.ellipse([x-r, 26, x+r, 26+r*2], fill=(253,246,240,180))
            f = get_font(20)
            draw.text((x, 26+r), str(i), font=f, fill=ACCENT, anchor="mm")

# ── 水玉デコ描画 ───────────────────────────────────────
def draw_dots(draw: ImageDraw.Draw):
    dots = [
        (W-60,  160,  55, (*PINK_DOT, 60)),
        (W-20,  240,  25, (*PINK_DOT, 40)),
        (30,    H-180, 40, (*PINK_DOT, 50)),
        (W-40,  H-250, 18, (212,144,120, 50)),
        (60,    180,   12, (212,144,120, 60)),
        (W-100, H-150, 10, (230,168,152, 70)),
    ]
    img_rgba = Image.new("RGBA", (W, H), (0,0,0,0))
    d2 = ImageDraw.Draw(img_rgba)
    for x, y, r, color in dots:
        d2.ellipse([x-r, y-r, x+r, y+r], fill=color)
    return img_rgba

# ── NEXTボタン描画 ─────────────────────────────────────
def draw_next_btn(draw: ImageDraw.Draw):
    bx, by, bw, bh = W-180, H-80, 150, 52
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=26, fill=TOPBAR)
    f = get_font(30)
    draw.text((bx+bw//2, by+bh//2), "NEXT  >", font=f, fill=WHITE, anchor="mm")

# ── ブランド名描画 ─────────────────────────────────────
def draw_brand(draw: ImageDraw.Draw):
    f = get_font(24)
    draw.text((50, H-60), "AP留学", font=f, fill=ACCENT)

# ── スライド1：表紙（パリ写真背景） ───────────────────
def make_cover(slide: dict, bg_bytes: bytes | None) -> bytes:
    if bg_bytes:
        bg = Image.open(io.BytesIO(bg_bytes)).convert("RGB")
        bg = bg.resize((W, H), Image.LANCZOS)
    else:
        bg = Image.new("RGB", (W, H), (80, 70, 60))

    # 暗いグラデーションオーバーレイ（下半分を暗く）
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(H):
        alpha = int(180 * (i / H) ** 0.7)
        od.line([(0, i), (W, i)], fill=(0, 0, 0, alpha))

    img = bg.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 【保存版】タグ
    tag_f = get_font(36)
    tag_text = "【 保 存 版 】"
    tw = draw.textlength(tag_text, font=tag_f)
    draw.text((W//2, H//2 - 80), tag_text, font=tag_f, fill=WHITE, anchor="mm")

    # メインタイトル
    heading = slide.get("heading", "")
    title_f = get_font(72)
    lines = textwrap.wrap(heading, width=10)
    ty = H//2 + 20
    for line in lines:
        draw.text((W//2, ty), line, font=title_f, fill=WHITE, anchor="mm")
        ty += 90

    # サブタイトル
    sub = slide.get("sub", "")
    sub_f = get_font(36)
    draw.text((W//2, ty + 30), sub, font=sub_f, fill=(240, 220, 210), anchor="mm")

    # AP留学ロゴ（右下）
    logo_f = get_font(32)
    draw.text((W-50, H-60), "AP留学", font=logo_f, fill=WHITE, anchor="ra")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

# ── スライド2〜6：POINTスライド ────────────────────────
def make_point_slide(slide: dict, bg_dots) -> bytes:
    img  = Image.new("RGB", (W, H), BG)
    dots = bg_dots.copy()
    img  = Image.alpha_composite(img.convert("RGBA"), dots).convert("RGB")
    draw = ImageDraw.Draw(img)

    current = slide.get("num", 1)
    draw_top_bar(draw, current, 7)

    # ラベル（POINT 1 など）
    label_f = get_font(32)
    draw.text((W//2, 160), slide.get("label",""), font=label_f, fill=ACCENT, anchor="mm")

    # 見出しボックス
    heading = slide.get("heading", "")
    head_f  = get_font(58)
    lines   = textwrap.wrap(heading, width=12)
    box_h   = len(lines) * 75 + 40
    bx, by  = 80, 200
    bw      = W - 160
    draw.rounded_rectangle([bx, by, bx+bw, by+box_h], radius=12,
                            outline=BOXBORDER, width=3, fill=BG)
    ty = by + 30
    for line in lines:
        draw.text((W//2, ty + 30), line, font=head_f, fill=TEXTDARK, anchor="mm")
        ty += 75

    # 箇条書き
    bullets = slide.get("bullets", [])
    body_f  = get_font(38)
    by2     = by + box_h + 50
    for b in bullets[:4]:
        draw.text((100, by2), "・", font=body_f, fill=ACCENT)
        draw.text((140, by2), b,   font=body_f, fill=TEXTDARK)
        by2 += 70

    draw_next_btn(draw)
    draw_brand(draw)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

# ── スライド7：CTA ─────────────────────────────────────
def make_cta_slide(slide: dict, bg_dots) -> bytes:
    img  = Image.new("RGB", (W, H), (252, 240, 245))
    dots = bg_dots.copy()
    img  = Image.alpha_composite(img.convert("RGBA"), dots).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw_top_bar(draw, 7, 7)

    # 見出し
    head_f = get_font(52)
    lines  = textwrap.wrap(slide.get("heading",""), width=14)
    ty = 220
    for line in lines:
        draw.text((W//2, ty), line, font=head_f, fill=TEXTDARK, anchor="mm")
        ty += 70

    # 区切り線
    draw.rectangle([W//2-80, ty+20, W//2+80, ty+24], fill=TOPBAR)

    # 本文
    body_f = get_font(38)
    cta_lines = [
        "無料エリア診断ZOOMで",
        "あなたにぴったりの留学先が見つかる！",
        "",
        "プロフィールリンクから",
        "LINEに登録して相談してみてください",
    ]
    by2 = ty + 70
    for line in cta_lines:
        draw.text((W//2, by2), line, font=body_f, fill=TEXTSUB, anchor="mm")
        by2 += 60

    # LINEボタン
    btn_w, btn_h = 520, 90
    bx = W//2 - btn_w//2
    by3 = by2 + 40
    draw.rounded_rectangle([bx, by3, bx+btn_w, by3+btn_h], radius=45, fill=(76, 175, 80))
    btn_f = get_font(44)
    draw.text((W//2, by3+btn_h//2), "LINE で無料相談する", font=btn_f, fill=WHITE, anchor="mm")

    draw_brand(draw)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

# ── Discord送信 ────────────────────────────────────────
def send_to_discord(data: dict, images: list):
    blog_title = data.get("blog_title","")
    caption    = data.get("caption","")

    requests.post(DISCORD_WEBHOOK, json={"content": (
        f"# インスタカルーセルができました！\n\n"
        f"元記事：{blog_title}\n\n"
        f"**【キャプション】**\n{caption}"
    )}, timeout=15)

    for i, img_bytes in enumerate(images, 1):
        files   = {"file": (f"slide_{i:02d}.png", img_bytes, "image/png")}
        payload = {"content": f"**スライド {i} / {len(images)}**"}
        requests.post(DISCORD_WEBHOOK, data=payload, files=files, timeout=30)
        print(f"  送信: スライド {i}/{len(images)}")

    print("  Discord送信完了！")

# ── メイン ─────────────────────────────────────────────
def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] カルーセル生成開始")

    post = get_latest_post()
    if not post:
        print("記事が見つかりません"); return
    print(f"  記事: {post.get('title',{}).get('rendered','')}")

    print("  テキスト生成中...")
    data   = generate_texts(post)
    slides = data.get("slides", [])

    print("  パリ写真取得中...")
    bg_bytes = fetch_paris_photo()

    print("  水玉デコ生成中...")
    img_dots = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(img_dots)
    for x, y, r, color in [
        (W-80,  170, 65, (245,196,176,55)),
        (W-25,  270, 28, (245,196,176,40)),
        (35,    H-200, 45, (245,196,176,50)),
        (W-50,  H-280, 20, (212,144,120,45)),
        (70,    200,   14, (212,144,120,55)),
        (W-110, H-170, 12, (230,168,152,65)),
        (150,   H-120, 35, (245,210,195,40)),
    ]:
        d.ellipse([x-r,y-r,x+r,y+r], fill=color)

    print("  画像生成中...")
    images = []
    for slide in slides:
        num = slide.get("num", 1)
        if num == 1:
            images.append(make_cover(slide, bg_bytes))
        elif num == 7:
            images.append(make_cta_slide(slide, img_dots))
        else:
            images.append(make_point_slide(slide, img_dots))
        print(f"    スライド {num}/7 完了")

    print("  Discord送信中...")
    send_to_discord(data, images)

if __name__ == "__main__":
    main()

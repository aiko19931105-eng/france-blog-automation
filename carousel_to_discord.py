"""
AP留学 カルーセル自動生成 → Discord送信 v4
- 1枚目：Unsplashパリ写真背景＋いろは角クラシック白文字
- 2〜6枚目：ベージュ×サーモンピンク＋水玉デコ＋NEXTボタン＋パリ写真
- 7枚目：CTA＋LINEボタン＋エリア診断ZOOM＋パリ写真
"""

import os, json, re, textwrap, requests, io, urllib.request, random
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic
from PIL import Image, ImageDraw, ImageFont

WP_URL          = os.environ["WP_URL"]
WP_USER         = os.environ["WP_USER"]
WP_APP_PASS     = os.environ["WP_APP_PASS"]
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
UNSPLASH_KEY    = os.environ["UNSPLASH_KEY"]

client = Anthropic()

# キャプション固定フッター
CAPTION_FOOTER = (
    "\n\n"
    "\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\n"
    "\u516c\u5f0fLINE\u3088\u308a\u30d5\u30e9\u30f3\u30b9\u7559\u5b66\u306e\n"
    "\u304a\u3059\u3059\u3081\u30a8\u30ea\u30a2\u8a3a\u65ad\uff08ZOOM\uff09\u3092\u53d7\u4ed8\u4e2d\U0001f1eb\U0001f1f7\n"
    "\u5b66\u6821\u624b\u914d\u306f\u624b\u6570\u6599\u7121\u6599\uff01\n"
    "\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\n\n"
    "\u30d7\u30ed\u30d5\u30a3\u30fc\u30eb\u306e\u30ea\u30f3\u30af\u304b\u3089\n"
    "\u30a2\u30af\u30bb\u30b9\u2192LINE\u767b\u9332\u2192\u30ab\u30a6\u30f3\u30bb\u30ea\u30f3\u30b0\u30b7\u30fc\u30c8\u306b\u6761\u4ef6\u8a18\u5165\u2728\n\n"
    "\u25fc\ufe6e\u30d1\u30ea\u751f\u6d3b\u3001\u30aa\u30c8\u30ca\u5973\u5b50\u7559\u5b66\U0001f1eb\U0001f1f7\u767a\u4fe1\u4e2d\uff01\n"
    "\u3044\u3044\u306d\u30fb\u30d5\u30a9\u30ed\u30fc\u3044\u305f\u3060\u3051\u308b\u3068\u5acc\u3057\u3044\u3067\u3059\U0001f339@ap.ryugaku\n\n"
    "\u30d5\u30e9\u30f3\u30b9\u7559\u5b66\u30a8\u30fc\u30b8\u30a7\u30f3\u30c8\u3001AP\u7559\u5b66\U0001f1eb\U0001f1f7\n"
    "\u30fb\u77ed\u671f\uff5e\u9577\u671f\u30d5\u30e9\u30f3\u30b9\u7559\u5b66\u624b\u914d\n"
    "\u30fb\u5927\u4eba\u306e\u5b66\u751f\u30d3\u30b6\u624b\u914d\u304a\u624b\u4f1d\u3044\u4e2d\n"
    "\u30fb\u30db\u30fc\u30e0\u30b9\u30c6\u30a4\u7d39\u4ecb"
)

W, H = 1080, 1350

BG        = (253, 246, 240)
TOPBAR    = (232, 168, 152)
ACCENT    = (196, 120,  96)
BOXBORDER = (224, 168, 152)
TEXTDARK  = ( 58,  32,  16)
TEXTSUB   = (154, 112,  96)
WHITE     = (255, 255, 255)

PARIS_QUERIES = [
    "paris eiffel tower golden hour",
    "paris cafe terrace street",
    "paris seine river bridge sunset",
    "paris montmartre cobblestone",
    "paris haussmann boulevard",
]

SLIDE_PHOTO_QUERIES = {
    2: "paris cafe coffee croissant",
    3: "paris eiffel tower romantic",
    4: "paris flower market colorful",
    5: "paris travel journey",
    6: "paris apartment haussmann street",
    7: "paris romantic sunset seine",
}

def get_font(size: int) -> ImageFont.FreeTypeFont:
    font_dir  = Path("/tmp/iroha")
    font_path = font_dir / "IrohaKakuClassic.ttf"
    if not font_path.exists():
        font_dir.mkdir(exist_ok=True)
        url = "https://github.com/hashikemu/iroha-kakukurashikku/releases/download/v1.00/IrohaKakuClassic.ttf"
        try:
            urllib.request.urlretrieve(url, font_path)
        except Exception:
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

def fetch_photo(query: str, orientation: str = "landscape") -> bytes | None:
    try:
        r = requests.get(
            "https://api.unsplash.com/photos/random",
            params={"query": query, "orientation": orientation, "content_filter": "high"},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            timeout=15
        )
        r.raise_for_status()
        img_url = r.json()["urls"]["regular"]
        ir = requests.get(img_url, timeout=30)
        ir.raise_for_status()
        return ir.content
    except Exception as e:
        print(f"  写真取得失敗: {e}")
        return None

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
        print(f"  WordPress失敗: {e}")
        return None

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
1枚目（表紙）: キャッチーなタイトル（20文字以内）＋サブタイトル
2〜6枚目（POINT 1〜5）: 見出し15文字以内、箇条書き3〜4行（各行30文字以内）
7枚目（CTA）: 見出し「あなたにぴったりの留学、一緒に探しましょう」固定

【絵文字・装飾文字は使わない】

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
    result = json.loads(raw, strict=False)
    result["caption"] = result.get("caption", "") + CAPTION_FOOTER
    return result

def draw_top_bar(draw, current: int, total: int):
    draw.rectangle([0, 0, W, 110], fill=TOPBAR)
    cx = W // 2
    sx = cx - (total * 52 - 8) // 2
    for i in range(1, total + 1):
        x = sx + (i - 1) * 52 + 26
        if i == current:
            draw.ellipse([x-30, 18, x+30, 78], fill=WHITE)
            draw.text((x, 48), str(i), font=get_font(28), fill=ACCENT, anchor="mm")
        else:
            draw.ellipse([x-18, 26, x+18, 62], fill=(253, 246, 240))
            draw.text((x, 44), str(i), font=get_font(20), fill=ACCENT, anchor="mm")

def draw_next_btn(draw):
    bx, by, bw, bh = W-180, H-80, 150, 52
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=26, fill=TOPBAR)
    draw.text((bx+bw//2, by+bh//2), "NEXT  >", font=get_font(30), fill=WHITE, anchor="mm")

def draw_brand(draw):
    draw.text((50, H-60), "AP\u7559\u5b66", font=get_font(24), fill=ACCENT)

def make_dots_layer() -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, r, color in [
        (W-80,  170, 65, (245,196,176,55)),
        (W-25,  270, 28, (245,196,176,40)),
        (35,    H-200, 45, (245,196,176,50)),
        (W-50,  H-280, 20, (212,144,120,45)),
        (70,    200,   14, (212,144,120,55)),
        (W-110, H-170, 12, (230,168,152,65)),
        (150,   H-120, 35, (245,210,195,40)),
    ]:
        d.ellipse([x-r, y-r, x+r, y+r], fill=color)
    return layer

def apply_slide_photo(img: Image.Image, photo_bytes: bytes, area_top: int) -> Image.Image:
    area_h = H - area_top - 100
    if area_h < 80:
        return img
    try:
        photo = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        pw, ph = photo.size
        scale  = max(W / pw, area_h / ph)
        nw, nh = int(pw * scale), int(ph * scale)
        photo  = photo.resize((nw, nh), Image.LANCZOS)
        lx = (nw - W) // 2
        ly = (nh - area_h) // 2
        photo = photo.crop([lx, ly, lx+W, ly+area_h])
        # ウォームトーン補正
        r, g, b, a = photo.split()
        r = r.point(lambda x: min(255, int(x * 1.08)))
        g = g.point(lambda x: min(255, int(x * 0.96)))
        b = b.point(lambda x: min(255, int(x * 0.88)))
        photo = Image.merge("RGBA", (r, g, b, a))
        # 上部フェード
        mask = Image.new("L", (W, area_h), 255)
        md   = ImageDraw.Draw(mask)
        fade_h = area_h // 3
        for i in range(fade_h):
            md.line([(0, i), (W, i)], fill=int(255 * i / fade_h))
        overlay = Image.new("RGBA", (W, area_h), (*BG, 80))
        photo   = Image.alpha_composite(photo, overlay)
        photo.putalpha(mask)
        img = img.convert("RGBA")
        img.paste(photo, (0, area_top), photo)
        return img.convert("RGB")
    except Exception as e:
        print(f"  写真合成失敗: {e}")
        return img

def make_cover(slide: dict, bg_bytes: bytes | None) -> bytes:
    if bg_bytes:
        bg = Image.open(io.BytesIO(bg_bytes)).convert("RGB")
        bg = bg.resize((W, H), Image.LANCZOS)
    else:
        bg = Image.new("RGB", (W, H), (80, 70, 60))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(H):
        alpha = int(120 * (i / H) ** 0.7)
        od.line([(0, i), (W, i)], fill=(0, 0, 0, alpha))
    img  = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text((W//2, H//2-80), "\u300c \u4fdd \u5b58 \u7248 \u300d", font=get_font(36), fill=WHITE, anchor="mm")
    lines = textwrap.wrap(slide.get("heading", ""), width=10)
    ty = H//2 + 20
    for line in lines:
        draw.text((W//2, ty), line, font=get_font(72), fill=WHITE, anchor="mm")
        ty += 90
    draw.text((W//2, ty+30), slide.get("sub", ""), font=get_font(36), fill=(240, 220, 210), anchor="mm")
    draw.text((W-50, H-60), "AP\u7559\u5b66", font=get_font(32), fill=WHITE, anchor="ra")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def make_point_slide(slide: dict, bg_dots: Image.Image, slide_photos: dict) -> bytes:
    img  = Image.new("RGB", (W, H), BG)
    img  = Image.alpha_composite(img.convert("RGBA"), bg_dots).convert("RGB")
    draw = ImageDraw.Draw(img)
    current = slide.get("num", 1)
    draw_top_bar(draw, current, 7)
    draw.text((W//2, 160), slide.get("label", ""), font=get_font(32), fill=ACCENT, anchor="mm")
    lines = textwrap.wrap(slide.get("heading", ""), width=12)
    box_h = len(lines) * 75 + 40
    bx, by = 80, 200
    draw.rounded_rectangle([bx, by, bx+W-160, by+box_h], radius=12, outline=BOXBORDER, width=3, fill=BG)
    ty = by + 30
    for line in lines:
        draw.text((W//2, ty+30), line, font=get_font(58), fill=TEXTDARK, anchor="mm")
        ty += 75
    by2 = by + box_h + 50
    for b in slide.get("bullets", [])[:4]:
        draw.text((100, by2), "\u30fb", font=get_font(38), fill=ACCENT)
        draw.text((140, by2), b, font=get_font(38), fill=TEXTDARK)
        by2 += 70
    photo_top = by2 + 40
    if current in slide_photos and slide_photos[current] and photo_top < H - 150:
        img = apply_slide_photo(img, slide_photos[current], photo_top)
        draw = ImageDraw.Draw(img)
    draw_next_btn(draw)
    draw_brand(draw)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def make_cta_slide(slide: dict, bg_dots: Image.Image, cta_photo: bytes | None) -> bytes:
    img  = Image.new("RGB", (W, H), (252, 240, 245))
    img  = Image.alpha_composite(img.convert("RGBA"), bg_dots).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw_top_bar(draw, 7, 7)
    lines = textwrap.wrap(slide.get("heading", ""), width=14)
    ty = 220
    for line in lines:
        draw.text((W//2, ty), line, font=get_font(52), fill=TEXTDARK, anchor="mm")
        ty += 70
    draw.rectangle([W//2-80, ty+20, W//2+80, ty+24], fill=TOPBAR)
    cta_lines = [
        "\u7121\u6599\u30a8\u30ea\u30a2\u8a3a\u65adZOOM\u3067",
        "\u3042\u306a\u305f\u306b\u3074\u3063\u305f\u308a\u306e\u7559\u5b66\u5148\u304c\u898b\u3064\u304b\u308b\uff01",
        "",
        "\u30d7\u30ed\u30d5\u30a3\u30fc\u30eb\u30ea\u30f3\u30af\u304b\u3089",
        "LINE\u306b\u767b\u9332\u3057\u3066\u76f8\u8ac7\u3057\u3066\u307f\u3066\u304f\u3060\u3055\u3044",
    ]
    by2 = ty + 70
    for line in cta_lines:
        draw.text((W//2, by2), line, font=get_font(38), fill=TEXTSUB, anchor="mm")
        by2 += 60
    btn_w, btn_h = 520, 90
    bx  = W//2 - btn_w//2
    by3 = by2 + 40
    draw.rounded_rectangle([bx, by3, bx+btn_w, by3+btn_h], radius=45, fill=(76, 175, 80))
    draw.text((W//2, by3+btn_h//2), "LINE\u3067\u7121\u6599\u76f8\u8ac7\u3059\u308b", font=get_font(44), fill=WHITE, anchor="mm")
    photo_top = by3 + btn_h + 40
    if cta_photo and photo_top < H - 150:
        img = apply_slide_photo(img, cta_photo, photo_top)
        draw = ImageDraw.Draw(img)
    draw_brand(draw)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def send_to_discord(data: dict, images: list):
    blog_title = data.get("blog_title", "")
    caption    = data.get("caption", "")
    requests.post(DISCORD_WEBHOOK, json={"content": (
        f"# \u30a4\u30f3\u30b9\u30bf\u30ab\u30eb\u30fc\u30bb\u30eb\u304c\u3067\u304d\u307e\u3057\u305f\uff01\n\n"
        f"\u5143\u8a18\u4e8b\uff1a{blog_title}\n\n"
        f"**\u300c\u30ad\u30e3\u30d7\u30b7\u30e7\u30f3\u300d**\n{caption}"
    )}, timeout=15)
    for i, img_bytes in enumerate(images, 1):
        files   = {"file": (f"slide_{i:02d}.png", img_bytes, "image/png")}
        payload = {"content": f"**\u30b9\u30e9\u30a4\u30c9 {i} / {len(images)}**"}
        requests.post(DISCORD_WEBHOOK, data=payload, files=files, timeout=30)
        print(f"  \u9001\u4fe1: \u30b9\u30e9\u30a4\u30c9 {i}/{len(images)}")
    print("  Discord\u9001\u4fe1\u5b8c\u4e86\uff01")

def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] \u30ab\u30eb\u30fc\u30bb\u30eb\u751f\u6210\u958b\u59cb")
    post = get_latest_post()
    if not post:
        print("\u8a18\u4e8b\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093")
        return
    print(f"  \u8a18\u4e8b: {post.get('title',{}).get('rendered','')}")
    print("  \u30c6\u30ad\u30b9\u30c8\u751f\u6210\u4e2d...")
    data   = generate_texts(post)
    slides = data.get("slides", [])
    print("  \u30d1\u30ea\u8868\u7d19\u5199\u771f\u53d6\u5f97\u4e2d...")
    bg_bytes = fetch_photo(random.choice(PARIS_QUERIES), orientation="portrait")
    print("  \u5404\u30b9\u30e9\u30a4\u30c9\u306e\u5199\u771f\u3092\u53d6\u5f97\u4e2d...")
    slide_photos = {}
    for num, query in SLIDE_PHOTO_QUERIES.items():
        slide_photos[num] = fetch_photo(query, orientation="landscape")
        print(f"    \u30b9\u30e9\u30a4\u30c9{num}\u5199\u771f\u53d6\u5f97\u5b8c\u4e86")
    img_dots = make_dots_layer()
    print("  \u753b\u50cf\u751f\u6210\u4e2d...")
    images = []
    for slide in slides:
        num = slide.get("num", 1)
        if num == 1:
            images.append(make_cover(slide, bg_bytes))
        elif num == 7:
            images.append(make_cta_slide(slide, img_dots, slide_photos.get(7)))
        else:
            images.append(make_point_slide(slide, img_dots, slide_photos))
        print(f"    \u30b9\u30e9\u30a4\u30c9 {num}/7 \u5b8c\u4e86")
    print("  Discord\u9001\u4fe1\u4e2d...")
    send_to_discord(data, images)

if __name__ == "__main__":
    main()

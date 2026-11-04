from PIL import Image, ImageDraw, ImageFont
import io, urllib.request

W, H, PAD = 880, 460, 28
HDR_H = 110

C = {
    "bg":     "#0d1117",
    "card":   "#161b22",
    "border": "#30363d",
    "panel":  "#21262d",
    "text":   "#e6edf3",
    "muted":  "#8b949e",
    "accent": "#58a6ff",
    "green":  "#3fb950",
    "purple": "#a371f7",
    "yellow": "#e3b341",
}

LANG_COLORS = {
    "Python":     "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#2b7489",
    "Java":       "#b07219",
    "Go":         "#00ADD8",
    "Rust":       "#dea584",
    "C++":        "#f34b7d",
    "C":          "#555555",
    "Ruby":       "#701516",
    "HTML":       "#e34c26",
    "CSS":        "#563d7c",
    "Swift":      "#F05138",
    "Kotlin":     "#A97BFF",
    "PHP":        "#4F5D95",
    "Shell":      "#89e051",
}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def lerp(c1, c2, t):
    r1, g1, b1 = rgb(c1)
    r2, g2, b2 = rgb(c2)
    return (int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t))


def font(size, bold=False):
    names = (
        ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]
        if bold else
        ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    )
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


def wrap(text, f, max_w, limit=None):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if f.getlength(test) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            if limit and len(lines) >= limit:
                return lines
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fetch_avatar(url, size):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "profile-card"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read()
        av = Image.open(io.BytesIO(data)).convert("RGBA").resize((size*2, size*2), Image.LANCZOS)
        mask = Image.new("L", (size*2, size*2), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size*2, size*2], fill=255)
        out = Image.new("RGBA", (size*2, size*2), (0, 0, 0, 0))
        out.paste(av, mask=mask)
        return out.resize((size, size), Image.LANCZOS)
    except Exception:
        return None


def render_card(username, name, bio, public_repos, followers, following,
                avatar_url="", repos=None):
    repos = (repos or [])[:3]

    # ── Build card surface with gradient header, then clip it to rounded rect ──
    img = Image.new("RGB", (W, H), rgb(C["bg"]))

    card = Image.new("RGB", (W, H), rgb(C["card"]))
    cd = ImageDraw.Draw(card)
    for y in range(PAD, PAD + HDR_H):
        t = ((y - PAD) / HDR_H) ** 0.55
        cd.line([(PAD, y), (W - PAD, y)], fill=lerp("#182640", C["card"], t))

    clip = Image.new("L", (W, H), 0)
    ImageDraw.Draw(clip).rounded_rectangle([PAD, PAD, W-PAD, H-PAD], radius=16, fill=255)
    img.paste(card, (0, 0), clip)

    d = ImageDraw.Draw(img)
    d.rounded_rectangle([PAD, PAD, W-PAD, H-PAD], radius=16,
                        outline=rgb(C["border"]), width=1)

    # ── Avatar ────────────────────────────────────────────────────────────
    AV = 84
    ax, ay = PAD + 26, PAD + (HDR_H - AV) // 2

    avatar = fetch_avatar(avatar_url, AV) if avatar_url else None
    if avatar:
        # ring drawn first, then avatar pasted over the centre
        d.ellipse([ax-3, ay-3, ax+AV+3, ay+AV+3], outline=rgb(C["accent"]), width=2)
        img.paste(avatar, (ax, ay), avatar)
    else:
        d.ellipse([ax, ay, ax+AV, ay+AV], fill=rgb(C["panel"]))
        d.ellipse([ax, ay, ax+AV, ay+AV], outline=rgb(C["accent"]), width=2)
        fi = font(32, bold=True)
        ch = (name[0] if name else username[0]).upper()
        iw = int(fi.getlength(ch))
        d.text((ax + AV//2 - iw//2, ay + AV//2 - 22), ch,
               fill=rgb(C["accent"]), font=fi)

    # ── Name / @username / bio ─────────────────────────────────────────────
    nx, ny = ax + AV + 22, PAD + 16
    fn = font(24, bold=True)
    fu = font(14)
    fb = font(13)
    fs = font(12)

    d.text((nx, ny), name or username, fill=rgb(C["text"]), font=fn)
    ny += 32
    d.text((nx, ny), f"@{username}", fill=rgb(C["accent"]), font=fu)
    ny += 24
    if bio:
        for line in wrap(bio, fb, W - nx - PAD - 36, limit=2):
            d.text((nx, ny), line, fill=rgb(C["muted"]), font=fb)
            ny += 18

    # github.com/username — top right corner
    url_t = f"github.com/{username}"
    d.text((W - PAD - 18 - int(fs.getlength(url_t)), PAD + 14),
           url_t, fill=rgb(C["muted"]), font=fs)

    # ── Stat boxes ────────────────────────────────────────────────────────
    sy = PAD + HDR_H + 14
    SH = 68
    stats = [
        (str(public_repos), "repositories", C["accent"]),
        (f"{followers:,}",  "followers",    C["green"]),
        (str(following),    "following",    C["purple"]),
    ]
    gap = 14
    sw = (W - PAD*2 - 32 - gap * (len(stats)-1)) // len(stats)
    fv = font(22, bold=True)
    fl = font(12)

    for i, (val, lbl, col) in enumerate(stats):
        bx = PAD + 16 + i * (sw + gap)
        d.rounded_rectangle([bx, sy, bx+sw, sy+SH], radius=10,
                            fill=rgb(C["panel"]), outline=rgb(C["border"]), width=1)
        vw = int(fv.getlength(val))
        lw = int(fl.getlength(lbl))
        d.text((bx + (sw - vw)//2, sy + 10), val, fill=rgb(col), font=fv)
        d.text((bx + (sw - lw)//2, sy + 44), lbl, fill=rgb(C["muted"]), font=fl)

    # ── Divider ───────────────────────────────────────────────────────────
    sep_y = sy + SH + 16
    d.line([(PAD+16, sep_y), (W-PAD-16, sep_y)], fill=rgb(C["border"]), width=1)

    # ── Repo cards ────────────────────────────────────────────────────────
    if repos:
        ry = sep_y + 14
        f_sec = font(11, bold=True)
        f_rn  = font(13, bold=True)
        f_rd  = font(12)
        f_rm  = font(11)

        d.text((PAD + 16, ry), "TOP REPOSITORIES", fill=rgb(C["muted"]), font=f_sec)
        ry += 18

        n = len(repos)
        rgap = 12
        cw = (W - PAD*2 - 32 - rgap*(n-1)) // n
        ch = H - PAD - 16 - ry

        for i, repo in enumerate(repos):
            rx = PAD + 16 + i*(cw + rgap)
            d.rounded_rectangle([rx, ry, rx+cw, ry+ch], radius=8,
                                fill=rgb(C["panel"]), outline=rgb(C["border"]), width=1)
            ix, iy = rx + 12, ry + 12

            # repo name (truncate if too wide)
            rn = repo["name"]
            while len(rn) > 1 and int(f_rn.getlength(rn + "…")) > cw - 24:
                rn = rn[:-1]
            if rn != repo["name"]:
                rn += "…"
            d.text((ix, iy), rn, fill=rgb(C["accent"]), font=f_rn)
            iy += 20

            # description
            desc = (repo.get("description") or "").strip()
            if desc:
                for line in wrap(desc, f_rd, cw - 24, limit=3):
                    d.text((ix, iy), line, fill=rgb(C["muted"]), font=f_rd)
                    iy += 16

            # bottom: language dot + stars
            meta_y = ry + ch - 22
            lang = (repo.get("language") or "").strip()
            if lang and lang != "n/a":
                lc = LANG_COLORS.get(lang, "#8b949e")
                d.ellipse([ix, meta_y+3, ix+10, meta_y+13], fill=rgb(lc))
                d.text((ix+14, meta_y+1), lang, fill=rgb(C["muted"]), font=f_rm)

            star_t = f"★ {repo.get('stars', 0)}"
            d.text((rx + cw - 12 - int(f_rm.getlength(star_t)), meta_y+1),
                   star_t, fill=rgb(C["yellow"]), font=f_rm)

    return img


if __name__ == "__main__":
    sample_repos = [
        {
            "name": "django-github-viewer",
            "description": "A GitHub profile viewer built with Django and the GitHub REST API.",
            "language": "Python",
            "stars": 42,
        },
        {
            "name": "dotfiles",
            "description": "Personal config for zsh, vim, tmux and git.",
            "language": "Shell",
            "stars": 17,
        },
        {
            "name": "advent-of-code",
            "description": "Solutions to Advent of Code puzzles, one per year.",
            "language": "Python",
            "stars": 9,
        },
    ]

    img = render_card(
        username="octocat",
        name="The Octocat",
        bio="GitHub mascot and open-source enthusiast. Building the future of software collaboration.",
        public_repos=8,
        followers=17_500,
        following=9,
        avatar_url="https://avatars.githubusercontent.com/u/583231",
        repos=sample_repos,
    )
    img.save("output2.png")
    print("Saved as output2.png")

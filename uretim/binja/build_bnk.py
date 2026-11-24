#!/usr/bin/env python3
"""Turkish Binary Ninja guide: bnk*.md -> PDF, same look as the exploit book."""
import glob, html, os, re, subprocess, sys
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.normpath(os.path.join(HERE, "..", "bn", "api", "docs", "img"))
ANN = os.path.normpath(os.path.join(HERE, "..", "shots", "ann"))
sys.path.insert(0, os.path.join(HERE, "..", "book"))
import build as B

EXTRA = """
figure { margin: 8pt 0 12pt; break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 118mm; border: 1px solid var(--line); border-radius: 3pt; }
figcaption { font-size: 8.8pt; color: var(--muted); margin-top: 3pt; font-style: italic; }
"""


def figs(src):
    def f(m):
        name, cap = m.group(1), m.group(2)
        p = os.path.join(ANN, name) if os.path.exists(os.path.join(ANN, name)) else os.path.join(IMG, name)
        if not os.path.exists(p):
            return ""
        return f'<figure><img src="file://{p}"><figcaption>{html.escape(cap)}</figcaption></figure>'
    return re.sub(r"\{\{img:([^|}]+)\|([^}]*)\}\}", f, src)


def body_and_toc():
    parts, toc, n = [], [], 0
    for path in sorted(glob.glob(os.path.join(HERE, "bnk*.md"))):
        src = open(path, encoding="utf-8").read()
        def part(m):
            pn, pt, pd = [x.strip() for x in m.group(1).split("|")]
            toc.append(("part", f"{pn} · {pt}", None))
            return f'<div class="partpage"><div class="pn">{html.escape(pn)}</div><div class="pt">{html.escape(pt)}</div><div class="pd">{html.escape(pd)}</div></div>'
        src = re.sub(r"^::part (.+)$", part, src, flags=re.M)
        src = figs(src)
        h = B.md_to_html(src)
        def h1(m):
            nonlocal n
            n += 1
            toc.append(("ch", m.group(1), f"b{n}"))
            return f'<h1 id="b{n}"><span class="n">BÖLÜM {n:02d}</span>{m.group(1)}</h1>'
        parts.append(re.sub(r"<h1>(.*?)</h1>", h1, h))
    return "\n".join(parts), toc


def render(pages, body, toc, out_html, out_pdf):
    items = []
    for kind, title, a in toc:
        if kind == "part":
            items.append(f'<li class="part">{html.escape(title)}</li>')
        else:
            items.append(f'<li><a href="#{a}">{title}</a><span class="pg">{pages.get(a, "")}</span></li>')
    cover = """<div class="cover"><div class="band"><div class="k">TERSİNE MÜHENDİSLİK · EXPLOIT · CRACKME</div>
<h1 class="t">Binary Ninja<br><span>Kullanım Kılavuzu</span></h1>
<div class="s">Arayüz, görünümler, gezinme, isim ve tip verme, yığın değişkenleri. Hepsi ~/cracks içindeki örnek programlar üzerinde.</div></div>
<div class="r"><b>dayanak</b> docs.binary.ninja (resmi belgeler, 6.x)<br><b>ekranlar</b> Binary Ninja Free 6.0.10905, bu makinede<br><b>örnekler</b> ~/cracks/e01_admin … e09_full<br><b>eşlikçi</b> Exploit-Gelistirme.pdf</div>
<div class="f">~/cracks laboratuvarı · Kasım 2026</div></div>"""
    css = B.CSS.replace('content: "Exploit Geliştirme"', 'content: "Binary Ninja Kullanım Kılavuzu"') + EXTRA
    doc = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Binary Ninja Kullanım Kılavuzu</title>
<style>{css}</style></head><body>{cover}<div class="toc"><h2>İçindekiler</h2><ol>{''.join(items)}</ol></div>{body}</body></html>"""
    open(out_html, "w", encoding="utf-8").write(doc)
    subprocess.run(["chromium", "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    "--allow-file-access-from-files", f"--print-to-pdf={out_pdf}", out_html],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def find_pages(toc, out_pdf):
    d = pymupdf.open(out_pdf)
    t = [d[i].get_text().replace("\n", " ") for i in range(len(d))]
    pages, start = {}, 2
    for kind, title, a in toc:
        if kind == "part":
            continue
        key = re.sub(r"<.*?>", "", html.unescape(title))[:30]
        for i in range(start, len(t)):
            if "BÖLÜM" in t[i] and key in t[i]:
                pages[a] = i + 1
                start = i
                break
    return pages, len(d)


if __name__ == "__main__":
    oh, op = os.path.join(HERE, "bnk.html"), os.path.join(HERE, "bnk.pdf")
    body, toc = body_and_toc()
    render({}, body, toc, oh, op)
    p, _ = find_pages(toc, op)
    render(p, body, toc, oh, op)
    p2, n = find_pages(toc, op)
    if p2 != p:
        render(p2, body, toc, oh, op)
    print("pages:", n, "missing:", [t for k, t, a in toc if k == "ch" and a not in p2])

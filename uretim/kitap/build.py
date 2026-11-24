#!/usr/bin/env python3
"""Build the exploit book: md chapters -> html -> pdf (chromium), with a TOC that has page numbers."""
import glob, html, os, re, subprocess, sys
import markdown
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_HTML = os.path.join(HERE, "book.html")
OUT_PDF = os.path.join(HERE, "book.pdf")

CSS = r"""
:root { --ink:#1f2328; --muted:#57606a; --line:#d8dee4; --acc:#d9480f; --acc2:#fff4e6;
        --blue:#1c7ed6; --blue2:#e7f5ff; --red:#e03131; --red2:#fff5f5; --green:#2f9e44; --green2:#ebfbee; }
@page { size: A4; margin: 17mm 17mm 18mm 17mm; background: #ffffff;
  @bottom-right { content: counter(page); color: #8c959f; font: 8.5pt "Liberation Mono"; }
  @bottom-left  { content: "Exploit Geliştirme"; color: #afb8c1; font: 8pt "Liberation Sans"; } }
@page cover { margin: 0; @bottom-right { content: none } @bottom-left { content: none } }
html, body { background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { color: var(--ink); font: 10.5pt/1.6 "Liberation Sans", "DejaVu Sans", sans-serif; margin: 0; }
.cover { page: cover; height: 297mm; box-sizing: border-box; padding: 0; position: relative; background: #fff; }
.cover .band { background: #1f2328; color: #fff; padding: 58mm 22mm 16mm; }
.cover .k { color: #ffa94d; font: 9pt "Liberation Mono"; letter-spacing: .1em; }
.cover h1.t { font-size: 40pt; line-height: 1.05; color: #fff; margin: 6mm 0 5mm; font-weight: 700; page-break-before: avoid; border: 0; padding: 0; }
.cover h1.t span { color: #ff922b; }
.cover .s { color: #d0d7de; font-size: 13pt; max-width: 150mm; line-height: 1.45; }
.cover .r { margin: 14mm 22mm 0; color: #57606a; font: 9.5pt/1.9 "Liberation Mono"; }
.cover .r b { color: #d9480f; font-weight: 400; display: inline-block; width: 26mm; }
.cover .f { position: absolute; bottom: 20mm; left: 22mm; right: 22mm; color: #8c959f; font: 8.5pt "Liberation Mono"; border-top: 2px solid #d9480f; padding-top: 4mm; }
.toc { page-break-before: always; }
.toc h2 { margin-top: 0; font-size: 20pt; }
.toc ol { list-style: none; padding: 0; margin: 0; }
.toc li { display: flex; align-items: baseline; padding: 1.4pt 0; font-size: 10pt; border-bottom: 1px dotted #e1e4e8; }
.toc li.part { color: var(--acc); font-weight: 700; border: 0; padding-top: 8pt; letter-spacing: .03em; }
.toc li a { color: var(--ink); text-decoration: none; flex: 1; }
.toc li .pg { color: var(--muted); font: 9pt "Liberation Mono"; margin-left: 8pt; }
h1 { page-break-before: always; color: #111; font-size: 23pt; line-height: 1.15; margin: 0 0 14pt;
     padding-bottom: 9pt; border-bottom: 3px solid var(--acc); font-weight: 700; }
h1 .n { display: table; color: #fff; background: var(--acc); font: 700 9pt "Liberation Mono"; letter-spacing: .12em;
        padding: 2pt 7pt; margin-bottom: 7pt; }
h1 .n + br { display: none; }
.partpage { page-break-before: always; height: 240mm; display: flex; flex-direction: column; justify-content: center;
            border-left: 8px solid var(--acc); padding-left: 12mm; }
.partpage .pn { color: var(--acc); font: 700 11pt "Liberation Mono"; letter-spacing: .14em; }
.partpage .pt { color: #111; font-size: 34pt; font-weight: 700; margin: 4mm 0; }
.partpage .pd { color: var(--muted); font-size: 12pt; max-width: 140mm; }
h2 { color: #111; font-size: 14pt; margin: 20pt 0 7pt; page-break-after: avoid; }
h2::before { content: ""; display: inline-block; width: 5pt; height: 13pt; background: var(--acc); margin-right: 6pt; vertical-align: -2pt; }
h3 { color: #24292f; font-size: 11.3pt; margin: 14pt 0 4pt; page-break-after: avoid; }
p { margin: 0 0 7.5pt; orphans: 3; widows: 3; }
strong { color: #111; }
a { color: var(--blue); }
ul, ol { margin: 0 0 8pt; padding-left: 17pt; }
li { margin: 2pt 0; }
li::marker { color: var(--acc); }
code { font: 8.9pt "Liberation Mono", monospace; color: #b3261e; background: #f6f2ef; padding: 0 2.5pt; border-radius: 2pt; }
pre { background: #f6f8fa; border: 1px solid var(--line); border-radius: 4pt; padding: 7pt 9pt; margin: 5pt 0 10pt;
      white-space: pre-wrap; word-break: break-all; font: 8.4pt/1.45 "Liberation Mono", monospace; color: #24292f;
      position: relative; break-inside: avoid; }
pre code { background: none; padding: 0; font: inherit; color: inherit; border-radius: 0; }
pre.cmd { background: #1f2328; border-color: #1f2328; color: #f0f3f6; }
pre.out { background: #fbfbfc; border-style: dashed; color: #3d444d; }
pre.asm { background: #fbf6fe; border-color: #eebefa; }
pre.py { background: #f4fbf5; border-color: #b2f2bb; }
pre.diag { background: var(--acc2); border-color: #ffd8a8; color: #3b2a1a; }
pre.small { font-size: 7.6pt; }
pre.cmd { font-size: 7.9pt; }
pre.lab.cmd { background-image: url("data:image/png;base64,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"); background-repeat: no-repeat; background-position: 9pt 5pt; background-size: auto 7pt; padding-top: 17pt; }
pre.lab.out { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGUAAAAcCAMAAABPj4H0AAAAIGNIUk0AAHomAACAhAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAAFrUExURQAAAG53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gW53gVkSL3QAAAB4dFJOUwBAg7/d8Pvu06RhFDxokAzBtgdwuFxIWPmfCQ3DtKYYDsayBsIPyLCe33o+Jy1Gf84Qyq4FI1Buojk0kjYRzawELHixARPPqgj20acDQqulYHOjdet2wAv49xVKSZXhfUEqMH7ER1nUncWERfXsHJkhIMu7s/wfJEmrtPwAAAABYktHRACIBR1IAAAAB3RJTUUH6gsYEwsf6eoVMgAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAyNi0xMS0yNFQxOToxMTozMSswMDowMNDLCBsAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMjYtMTEtMjRUMTk6MTE6MzErMDA6MDChlrCnAAAAKHRFWHRkYXRlOnRpbWVzdGFtcAAyMDI2LTExLTI0VDE5OjExOjMxKzAwOjAw9oOReAAAABBpVFh0bGFiZWwAAAAAAMOHSUtUSRKj4AIAAAGvSURBVEjHtdZnW8JADADgKKggCIiCozjBgQMnKg5cgCAqToYTN25x9ucLuZZN28On+ZLk7srLU2gAgERVtUJZU1unUtdrgA8tm44GvtVgqyON3oBdozFVN7HF0UyOmbAxk6ZFld1vbWsXVxgLNh1pRKLCdOaf6BJVunuw7rWCZMVoYymVvn4sBwgiTRkk6/ah4ZFRx9i4uDIxidXUNLfhnMGYxdU50rgKlHmCLPDXLCpElCU3FssrkB+ruLyWt5ZR1slbyNnyCCpeH+aNQkRQ8QfSOaCB4iipqDcxBbeARtnGvANSFRKhYkRQ2cW8R6fsl0AElQPMJirlkAFK5agChQ1HKJWK7hhriNAptJ++O1qOEf8mx46lKroTwtj0NAr3VIZytoSfSjgtwwgq3IQ540YfuGxic4xjLHoKhZ+W5xfxyyvztU/CTDaXZIQV+skP5hjWN3rpCjBBWgVuOYaRrgDc3WeNaMIvroCDMA8MhQKe+GPYnupT/y68mSNCCjwVMeIKhvP55RXkj7e8HzM5QvtuTX6wSpmVT7yDXzIrie/0DPyRWQF/8pf5/6uUjj+MRKssegI1JQAAAABJRU5ErkJggg=="); background-repeat: no-repeat; background-position: 9pt 5pt; background-size: auto 7pt; padding-top: 17pt; }
pre.lab.c { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAWCAMAAAD3n0w0AAAAIGNIUk0AAHomAACAhAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAADeUExURQAAABx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1hx+1u5v6rMAAABJdFJOUwBAg7/d8Pvu06RhFFj5nwkNphgHwp7fej4nLUZ/zjSSBTaxogEI9kKrYHN1XHb3FaWVBjnhfUEqMEh+z6dZ1PqhhMDx/O/VZRY05fDKAAAAAWJLR0QAiAUdSAAAAAd0SU1FB+oLGBMLH+nqFTIAAAAldEVYdGRhdGU6Y3JlYXRlADIwMjYtMTEtMjRUMTk6MTE6MzErMDA6MDDQywgbAAAAJXRFWHRkYXRlOm1vZGlmeQAyMDI2LTExLTI0VDE5OjExOjMxKzAwOjAwoZawpwAAACh0RVh0ZGF0ZTp0aW1lc3RhbXAAMjAyNi0xMS0yNFQxOToxMTozMSswMDowMPaDkXgAAAAHdEVYdGxhYmVsAENy09thAAAArUlEQVQY033Q1xKCMBAF0FUsKCqoiL0r9q7YsNf8/w8JSRAyZrxPmTNJtgCQ+PxCIBgKi5GoRAViIvomnpBtUpKIScqytIp+MUOOWjaXLxRLZYwVYtUa/b8uWNjA1gQ3LWjrtukSeNPBF7uMQQ9jn8UBxiGLIx5yn3MLkZbGE1ZJ81OmeWfM2ZzSQvUsZLky1pvtbv9ndaCYHAQ4HF06nWWnoHG5arf742m+3gAfiNU5gU95GgIAAAAASUVORK5CYII="); background-repeat: no-repeat; background-position: 9pt 5pt; background-size: auto 7pt; padding-top: 17pt; }
pre.lab.asm { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMsAAAAWCAMAAABZhZjwAAAAIGNIUk0AAHomAACAhAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAAKvUExURQAAAJw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tZw2tVubrO0AAADkdFJOUwAE6icKXqra8Pz26M2sgE4TAUSazuz6+e3UtoxdISgQqL2zzOunY7Q6/eMNvG+FS+X+LCXHKu+Rk2DGAuFPMCDndJVZC904FfgpEUKw8w7u++Ti0wWkeWmgVrJQKyMxfb/VYTItcKVtZtg0e0bBiWcdRfFNfNJHJi+Lz0DDbErAg4SWu+ZYo7GtLt+ikAbgdT4cyo1b3ptoCTYSN0EfeAPWX8V3G8mH0ZlSn49cZavc8m70cukWPxgMl4bC9VecuphDItDb16mCrjx/CMTZa7c9y4rIkmSdVDWhcw9MiFMHO2oUjoonzBgAAAABYktHRACIBR1IAAAAB3RJTUUH6gsYEwsf6eoVMgAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAyNi0xMS0yNFQxOToxMTozMSswMDowMNDLCBsAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMjYtMTEtMjRUMTk6MTE6MzErMDA6MDChlrCnAAAAKHRFWHRkYXRlOnRpbWVzdGFtcAAyMDI2LTExLTI0VDE5OjExOjMxKzAwOjAw9oOReAAAAA50RVh0bGFiZWwAQVNTRU1CTFnZPXB9AAAEzUlEQVRYw62Yi18UVRTHL7Uhy0NZZXczFBQ3cY0yqFaSUKsNFxHcxc0ioBIichMDMxXNRKMiE3xiJAmamGXawzIf2VPLLMmU3u/H/UOae2buY547fPJ8Psyc8zvn3rnfuXfuzIKQbAlXYLArkcYcVyWOSHImp6SmjRyVLuiu0WMy3B7v1WOvyRw3nstZWG3ZNDFBjieyyhxZSGPCJNom2Zdx7eRscRBJRM5l4RQ/iadeR+M8aHY9DUcp/dygQZl2ozCw/AKm33SzOGLWTVwWfIsSj/ebsoAFJpuzoOlQUqhEt0I0o4hm05QubnOpUIqdqgvMpPqs2Sr9dvssdyhxJrZmwfhOc5bgXUTwl0Awx02CUClNzg3RHspElGCKunvGMk+tD4OlvEJeuvONWcKRSKRczlS6TFlQGVQsiBL/bvAXstw97OL3iixVIN1XXVN7f/EDD3oZyxxYIIvq6msfGt2QFtCxPFxNLaplwY0QPoKNWRYTLzYVUjXmLGgMVDwqeUvAS01gKVj9TXDfgkKLpUTJo/cn+7FmxWsh+jJ6zxMe55MpsyxHOmMsi6G7J6xYUCOkVliwVABuaCVywHILr2KZldC2FPaycVr6Vv3AYL5WIwOzZpnhlQ4tUrSGXP9JU5a10MsUCxb0FJSsc7XCuY0n1sM0oQ3k9LR2XtoLdAODeXE+M2yWec9Kh+ekqEM6J04wY3l+I3GT+bZswIJegCttCsNq72Syq4sIm9EW2B228np5p87ftn1HTZHYT7YHEt07XyzpMWJhNlLD8hK5wCzUTLbHLUYs4a6uroDcVlgPRiy7+L7k7+XyyzDi3cgVIU4fT/TvYfVJOXsdPLGB6d5X9g3YZ0H7peNS9Kp0PICMWPj4Xuu3ZkGvs9rtgnoQ1rLkvEGcPeLQKoXuU/ij1JMn6KFWPsXxWA5JR/dcn3Q8bM2yYI0wDEMW9KZS+pawNhxvE+UdyeuFXEyoT59+RLjAu3zGGiOCnstWYDyWzvek00Tpb77DmgXj9fFYjrrlR+B9QTsEc3qMuN3ELVS1OF514gB9+4eEZ6mo7OQHp+h12Tta837J0rKgNqVFJkJmz36wXv4K+TAOC6qDso9E6WOi7N9K7BPi+qLaRsFPN8Hc4bVqvb++D+jJIEUW030MoYGw/Dh8Zs4i3adtxD8djyUGXTUIyoBfM7m4Wj8UtMqpnzKYtjNE/9w2C/oCKnKQFQs6C0XHh82yT4uCv6SpXcKXJkzACdnvEZ42eJ+esc9yDipWWLN8BUX0m9o+y1gdizddSTUsOkxfWLVO4VkucJ+lv1m+hubn7bOg1ZIz6LJmWQfdsN9FdlliWG/fUBaMPReWT4uVftvXDoklCovkXrxUVZLVWyfvPpfULPzbcreepWpoaGgvk4xYjhZCL8uiKpaLrNOZZizfwQZVQcNU2Ag4i8q6OzmLaM4CNQu37/Us6qky+OZX3vv4B5ZKUndKdy4tSxQ+KDtYvBnyWYYsnhZkzNLGmv9fFsEix4bLUgzxjyxuzifxSTn46YJH6GIjRUHpPwcE/cgvfHyXj6VJ+C+CTRbyxYrLhX3pPBEq6Yv8199+zx0MeEK+jIN//CmMI/rXwsTTvlA4MNjx9z+CfjlY8k+1N/17Tqy0x/IfcXRrVxbyE40AAAAASUVORK5CYII="); background-repeat: no-repeat; background-position: 9pt 5pt; background-size: auto 7pt; padding-top: 17pt; }
pre.lab.py { background-image: url("data:image/png;base64,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"); background-repeat: no-repeat; background-position: 9pt 5pt; background-size: auto 7pt; padding-top: 17pt; }
pre.lab.diag { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAG0AAAAiCAMAAABiKKfdAAAAIGNIUk0AAHomAACAhAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAAGwUExURQAAANlID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID9lID69S180AAACPdFJOUwAE/AKopRdytOHz9OPGonZBCqSUJIARzKrkwLzo9RLOpwOD+BTQLv0V0qOO/pNFKCU1WYpQFtShwYUeGNaeUxrYnAHEm9qahvm7gVEglx3lS5VM1TkHJ636QBll3bVSNMq2Y1tXE19W+7e+TwZYSFUI8HBEMCyN91S476znH7nFJt/xkj+6TUYy66kLDSMhZmNKogAAAAFiS0dEAIgFHUgAAAAHdElNRQfqCxgTCyBfjDgPAAAAJXRFWHRkYXRlOmNyZWF0ZQAyMDI2LTExLTI0VDE5OjExOjMxKzAwOjAw0MsIGwAAACV0RVh0ZGF0ZTptb2RpZnkAMjAyNi0xMS0yNFQxOToxMTozMSswMDowMKGWsKcAAAAodEVYdGRhdGU6dGltZXN0YW1wADIwMjYtMTEtMjRUMTk6MTE6MzErMDA6MDD2g5F4AAAAEWlUWHRsYWJlbAAAAAAAxZ5FS8SwTPngSZYAAAISSURBVEjH5dT5U9NAFAfw1za1gHLIoQLllCIgqCAFRQXl9gAUCCBgrSiCchhE8EAFFDk82H8Z8pYc22TYXQYzzvj9Je9tu+8zyWQDcKzxEUL8xzvyP9UCiqIEPdP+uZwIJSWn+E+eSk1LzzhtLWcSJlnGeja2ObQ5cxa7cz7a5upNnjkiX2/DDBYqsM1MkdMKi7ApLgFBrZSZeV5KK4tgHTQwrlZ+4ehaRSWWVSbG1S7qC9U1ly5fqa27WlTt0OqNlDu0aANWjQEQ1q7pC9eNrik9UXO+VIZ24yYWt2wYV8OH0Qwu4Wgtt/F6pxUkNLy3tqi01t6Bl04G42pduKn77r37D1w1Mz5Wo+lhMa7Wa522vrSHATntUQLGP2/99sM9MCijJasgq8HQsN+aOfJY5t6SVGkNYHQsc9wY0BFgNfO8tbpo5Ikqr+kpiwXpLT5lNec/qRan/36mHknbzwTufy6m5bxw43japFVGcftLQQ2mprF4pUpoxa9nZg/KOdw9L6rBmwNOE9cUQhaUt4vvlhaX3+u/+QtZzXxL5h0afKDcR+1Q7ZM5IkPXmKwAq5kJOzUn56ZZiSRqn7/IaNBMua+aoDYVt/erayClQYzleBpAS11N/vq3/abt+4b9uyekQWwE2x+aoEazSSKOr95fTJyEPJK2Rme3w2TYI20HH2upR5r+Xk7//OWRBr//7GoeMHuZniZrMUpGXAAAAABJRU5ErkJggg=="); background-repeat: no-repeat; background-position: 9pt 5pt; background-size: auto 7pt; padding-top: 17pt; }

blockquote { margin: 7pt 0 11pt; padding: 8pt 11pt; border-left: 4px solid var(--blue); background: var(--blue2);
             color: #1b3a57; page-break-inside: avoid; border-radius: 0 4pt 4pt 0; }
blockquote strong { color: #0b3a66; }
blockquote.warn { border-left-color: var(--red); background: var(--red2); color: #5c1a1a; }
blockquote.warn strong { color: #a61e1e; }
blockquote.tip { border-left-color: var(--green); background: var(--green2); color: #1d4424; }
blockquote.tip strong { color: #1b5e20; }
blockquote p:last-child, blockquote ul:last-child { margin-bottom: 0; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0 11pt; font-size: 9.4pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th { text-align: left; color: #fff; background: #2d333b; padding: 4pt 6pt; font-weight: 700; }
td { border-bottom: 1px solid #eaeef2; padding: 3.5pt 6pt; vertical-align: top; }
tr:nth-child(even) td { background: #fafbfc; }
hr { border: 0; border-top: 1px solid var(--line); margin: 12pt 0; }
.intro { background: var(--acc2); border: 1px solid #ffd8a8; border-radius: 5pt; padding: 9pt 12pt 4pt; margin: 0 0 14pt; break-inside: avoid; }
.intro .lbl { font: 700 7pt "Liberation Sans"; letter-spacing: .16em; color: var(--acc); margin-bottom: 4pt; }
.summary { background: var(--green2); border: 1px solid #b2f2bb; border-radius: 5pt; padding: 8pt 12pt 3pt; margin: 8pt 0 12pt; break-inside: avoid; }
.summary .lbl { font: 700 7pt "Liberation Sans"; letter-spacing: .16em; color: var(--green); margin-bottom: 4pt; }
.summary li::marker { color: var(--green); }
h2.quiz::before { background: var(--blue); }
h2.drill::before { background: var(--green); }
.ex { border: 1px solid var(--line); border-radius: 5pt; background: #fafbfc; padding: 8pt 12pt; margin-top: 16pt; font-size: 9.8pt; }
"""

LABELS = {"cmd", "out", "c", "asm", "py", "diag"}


def decorate(h):
    # intro box: "Bu bölümde" section up to next h2
    h = re.sub(r"<h2>Bu bölümde</h2>(.*?)(?=<h2)", lambda m: '<div class="intro"><div class="lbl">BU BÖLÜMDE</div>' + m.group(1) + "</div>", h, flags=re.S)
    # summary box
    h = re.sub(r"<h2>Özet</h2>\s*(<ul>.*?</ul>)", lambda m: '<div class="summary"><div class="lbl">ÖZET</div>' + m.group(1) + "</div>", h, flags=re.S)
    h = h.replace("<h2>Kontrol soruları</h2>", '<h2 class="quiz">Kontrol soruları</h2>')
    h = h.replace("<h2>Alıştırmalar</h2>", '<h2 class="drill">Alıştırmalar</h2>')
    def bq(m):
        body = m.group(1)
        head = re.sub(r"<.*?>", "", body[:120])
        cls = ""
        if re.search(r"Sık yapılan|Dikkat", head):
            cls = "warn"
        elif re.search(r"Exploit için anlamı|Pratik|Kendine sor|Neden önemli|Kendi merdivenin|Pratikteki", head):
            cls = "tip"
        return f'<blockquote class="{cls}">' + body + "</blockquote>"
    h = re.sub(r"<blockquote>(.*?)</blockquote>", bq, h, flags=re.S)
    return h


def md_to_html(text):
    h = markdown.markdown(text, extensions=["fenced_code", "tables", "attr_list", "md_in_html"])
    # <pre><code class="language-out">  ->  <pre class="lab out"><code>
    def fix(m):
        lang = m.group(1)
        extra = ""
        if "-small" in lang:
            lang = lang.replace("-small", "")
            extra = " small"
        cls = f"lab {lang}{extra}" if lang in LABELS else extra.strip()
        return f'<pre class="{cls}"><code>'
    h = re.sub(r'<pre><code class="language-([\w-]+)">', fix, h)
    h = h.replace("\\|", "|")
    h = decorate(h)
    return h


def build_body():
    chapters = sorted(glob.glob(os.path.join(HERE, "ch*.md")))
    parts, toc = [], []
    n = 0
    for path in chapters:
        src = open(path, encoding="utf-8").read()
        # part pages:  ::part Kısım I | Başlık | açıklama
        def part(m):
            pn, pt, pd = [x.strip() for x in m.group(1).split("|")]
            toc.append(("part", f"{pn} · {pt}", None))
            return f'<div class="partpage"><div class="pn">{html.escape(pn)}</div><div class="pt">{html.escape(pt)}</div><div class="pd">{html.escape(pd)}</div></div>'
        src = re.sub(r"^::part (.+)$", part, src, flags=re.M)
        src = re.sub(r"^\{\{file:(.+?)\}\}$", lambda m: open(os.path.expanduser(m.group(1)), encoding="utf-8").read().rstrip("\n"), src, flags=re.M)
        h = md_to_html(src)
        def h1(m):
            nonlocal n
            title = m.group(1)
            n += 1
            anchor = f"b{n}"
            label = "EK" if title.startswith("Ek ") else f"BÖLÜM {n - sum(1 for t in toc if t[0]=='ek'):02d}"
            if title.startswith("Ek "):
                toc.append(("ek", title, anchor))
                return f'<h1 id="{anchor}"><span class="n">EK</span>{title}</h1>'
            toc.append(("ch", title, anchor))
            num = sum(1 for t in toc if t[0] == "ch") - 1
            return f'<h1 id="{anchor}"><span class="n">BÖLÜM {num:02d}</span>{title}</h1>'
        h = re.sub(r"<h1>(.*?)</h1>", h1, h)
        parts.append(h)
    return "\n".join(parts), toc


def render(pages):
    body, toc = build_body()
    items = []
    for kind, title, anchor in toc:
        if kind == "part":
            items.append(f'<li class="part">{html.escape(title)}</li>')
        else:
            pg = pages.get(anchor, "")
            num = ""
            items.append(f'<li><a href="#{anchor}">{title}</a><span class="pg">{pg}</span></li>')
    cover = open(os.path.join(HERE, "cover.html"), encoding="utf-8").read()
    doc = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Exploit Geliştirme</title>
<style>{CSS}</style></head><body>
{cover}
<div class="toc"><h2>İçindekiler</h2><ol>{''.join(items)}</ol></div>
{body}
</body></html>"""
    open(OUT_HTML, "w", encoding="utf-8").write(doc)
    subprocess.run(["chromium", "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={OUT_PDF}", OUT_HTML], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return toc


def find_pages(toc):
    doc = pymupdf.open(OUT_PDF)
    pages = {}
    texts = [doc[i].get_text() for i in range(len(doc))]
    start = 2  # skip cover + toc pages start
    for kind, title, anchor in toc:
        if kind == "part":
            continue
        plain = re.sub(r"<.*?>", "", html.unescape(title)).strip()
        key = plain[:28]
        for i in range(start, len(texts)):
            t = texts[i]
            if ("BÖLÜM" in t or "EK" in t) and key in t.replace("\n", " "):
                pages[anchor] = i + 1
                start = i
                break
    return pages, len(doc)


if __name__ == "__main__":
    toc = render({})
    pages, n = find_pages(toc)
    render(pages)
    pages2, n2 = find_pages(toc)
    if pages2 != pages:
        render(pages2)
    print("pages:", n2)
    missing = [t for k, t, a in toc if k != "part" and a not in pages2]
    if missing:
        print("TOC miss:", missing)

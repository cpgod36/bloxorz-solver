#!/usr/bin/env python3
"""Vẽ lại các sơ đồ mermaid của báo cáo thành PDF vector (chạy: python docs/report/latex/diagrams/render.py).

Nguồn: diagrams/sodo*.mmd. Kết quả: images/sodo*.pdf, cắt sát khung sơ đồ.
Cần Google Chrome và thư viện mermaid.min.js (lấy từ extension VS Code "Markdown PDF Plus").
"""
import html
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGES = HERE.parent / "images"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
MERMAID = Path.home() / ".vscode/extensions/tom-latham.markdown-pdf-plus-2.0.0/dist/media/mermaid.min.js"

# Màu viền khớp khung trang bìa (blue!50!black)
CONFIG = """{
  startOnLoad: false,
  theme: 'base',
  themeVariables: {
    fontFamily: 'Times New Roman, Times, serif',
    fontSize: '20px',
    primaryColor: '#eef3fb',
    primaryBorderColor: '#1f2a6b',
    primaryTextColor: '#111111',
    lineColor: '#1f2a6b',
    secondaryColor: '#fff6e5',
    tertiaryColor: '#ffffff',
    edgeLabelBackground: '#ffffff',
    actorBkg: '#eef3fb',
    actorBorder: '#1f2a6b',
    noteBkgColor: '#fff6e5',
    noteBorderColor: '#b08a3e'
  },
  flowchart: { htmlLabels: true, nodeSpacing: 28, rankSpacing: 34, padding: 10, wrappingWidth: 260, curve: 'basis' },
  state: { nodeSpacing: 40, rankSpacing: 40 },
  sequence: { actorMargin: 40, messageMargin: 28, boxMargin: 8, mirrorActors: false }
}"""

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>html,body{{margin:0;padding:0;background:#fff}} pre.mermaid{{margin:0;display:inline-block}}</style>
<script src="{mermaid}"></script></head><body>
<pre class="mermaid">{code}</pre>
<script>
mermaid.initialize({config});
mermaid.run().then(() => {{
  const r = document.querySelector('svg').getBoundingClientRect();
  const st = document.createElement('style');
  st.textContent = `@page {{ size: ${{Math.ceil(r.width) + 6}}px ${{Math.ceil(r.height) + 6}}px; margin: 0 }}`;
  document.head.appendChild(st);
}});
</script></body></html>"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sources = sorted(HERE.glob("sodo*.mmd"))
    with tempfile.TemporaryDirectory() as tmp:
        for src in sources:
            page = Path(tmp) / (src.stem + ".html")
            page.write_text(PAGE.format(mermaid=MERMAID.as_uri(), config=CONFIG,
                                        code=html.escape(src.read_text(encoding="utf-8"))), encoding="utf-8")
            pdf = IMAGES / (src.stem + ".pdf")
            subprocess.run([str(CHROME), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            "--allow-file-access-from-files", "--virtual-time-budget=15000",
                            f"--print-to-pdf={pdf}", page.as_uri()],
                           check=True, capture_output=True, timeout=120)
            print("Đã vẽ", pdf.name)


if __name__ == "__main__":
    main()

"""Crea una versione 'a file unico' della pagina, usata solo per l'anteprima su claude.ai."""
import re
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
html = (SITE / "index.html").read_text(encoding="utf-8")
body = html.split("<body>", 1)[1].split('<script src="https://cdnjs', 1)[0]
head = re.search(r"<title>.*?</title>\s*<meta name=\"claude:viewport-fit-sides\"[^>]*>", html, re.S).group(0)
fonts = re.search(r'<link rel="stylesheet" href="https://fonts[^>]*>', html).group(0)
out = (head + "\n" + fonts + "\n<style>\n" + (SITE / "style.css").read_text(encoding="utf-8") + "\n</style>\n" + body +
       '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n<script>\n' +
       (SITE / "app.js").read_text(encoding="utf-8") + "\n</script>\n")
dest = Path(__file__).resolve().parent.parent / "anteprima" / "index.html"
dest.parent.mkdir(exist_ok=True)
dest.write_text(out, encoding="utf-8")
print(dest)

# Le pagine interne restano file separati: nell'anteprima vengono pubblicate accanto alla pagina principale.
import shutil
for name in ["titoli-di-stato.html", "etf.html", "calendario.html", "style.css", "pagine.js"]:
    shutil.copy(SITE / name, dest.parent / name)
(dest.parent / "data").mkdir(exist_ok=True)
for name in ["data.json", "titoli.json", "etf.json", "calendario.json"]:
    shutil.copy(SITE / "data" / name, dest.parent / "data" / name)

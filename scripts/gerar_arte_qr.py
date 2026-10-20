# ---------------------------------------------------------------------------
# scripts/gerar_arte_qr.py - artes de divulgacao com o QR do app.
#
#   python -m scripts.gerar_arte_qr
#
# Gera em divulgacao/: qr_post_quadrado.png (1080x1080, WhatsApp/feed) e
# qr_story.png (1080x1920, status/story). Identidade da barbearia: preto,
# amarelo #F7DF01, logo e faixa de poste de barbeiro.
#
# >>> SE A URL DO APP MUDAR (renomear o servico no Render ou comprar dominio),
#     troque URL/URL_TXT abaixo e rode de novo — o QR aponta para um endereco
#     FIXO, gravado na imagem.
#
# Dois detalhes que fazem o QR ser legivel (custaram tentativa e erro):
#   - border=4: a "zona de silencio" que a especificacao exige. Com 2, leitores
#     falhavam de forma intermitente.
#   - escala INTEIRA: redimensionar para um tamanho arbitrario deixa modulos com
#     larguras desiguais e o leitor se perde.
# Depois de gerar, confira a leitura com scripts/conferir_qr.py.
# ---------------------------------------------------------------------------
import os

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFont

URL = "https://salao-gestor.onrender.com"
URL_TXT = "salao-gestor.onrender.com"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = "C:/Windows/Fonts/"
PRETO, AMARELO, BRANCO, CINZA = (13,13,15), (247,223,1), (245,245,242), (150,148,140)

fonte = lambda arq, t: ImageFont.truetype(F + arq, t)

def centro(d, y, txt, fnt, cor, larg):
    w = d.textbbox((0,0), txt, font=fnt)[2]
    d.text(((larg-w)//2, y), txt, font=fnt, fill=cor)

def poste(d, larg, alt=14):
    cores = [(200,50,43), BRANCO, (43,92,200), BRANCO]; passo = 26
    for i, x in enumerate(range(-alt, larg+passo, passo)):
        d.polygon([(x,alt),(x+alt,0),(x+alt+passo//2,0),(x+passo//2,alt)], fill=cores[i%len(cores)])

def faz_qr(px_alvo):
    """QR com borda de 4 modulos (zona de silencio da especificacao) e escala
    INTEIRA, para todo modulo ter o mesmo numero de pixels. Devolve (img, lado)."""
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=1, border=4)
    qr.add_data(URL); qr.make(fit=True)
    base = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    n = base.size[0]; fator = max(1, round(px_alvo/n)); px = n*fator
    img = base.resize((px,px), Image.NEAREST)
    lg = Image.open(f"{RAIZ}/assets/logo.png").convert("RGBA")
    d = int(px*0.15); lg = lg.resize((d,d), Image.LANCZOS); pad = int(d*0.14)
    img.paste(Image.new("RGB",(d+pad*2,d+pad*2),"white"), ((px-d-pad*2)//2,)*2)
    img.paste(lg, ((px-d)//2,)*2, lg)
    return img, px

def cartao_qr(im, d, y, alvo, larg, pad):
    qr, qpx = faz_qr(alvo)
    x0 = (larg - qpx - pad*2)//2
    d.rounded_rectangle([x0, y, x0+qpx+pad*2, y+qpx+pad*2], radius=30, fill="white")
    im.paste(qr, (x0+pad, y+pad))
    return y + qpx + pad*2

def logo_topo(im, y, diam, larg):
    lg = Image.open(f"{RAIZ}/assets/logo.png").convert("RGBA").resize((diam,diam), Image.LANCZOS)
    im.paste(lg, ((larg-diam)//2, y), lg)
    return y + diam

# ---------------- QUADRADO 1080x1080: enxuto, QR grande ----------------
def quadrado():
    L = 1080; im = Image.new("RGB",(L,L),PRETO); d = ImageDraw.Draw(im); poste(d,L,12)
    y = logo_topo(im, 54, 150, L) + 22
    centro(d, y, "AGENDE SEU HORÁRIO", fonte("ariblk.ttf",58), BRANCO, L); y += 78
    centro(d, y, "Aponte a câmera do celular", fonte("arial.ttf",32), CINZA, L); y += 54
    y = cartao_qr(im, d, y, 560, L, 34) + 26
    centro(d, y, URL_TXT, fonte("arialbd.ttf",30), AMARELO, L)
    im.save(f"{RAIZ}/divulgacao/qr_post_quadrado.png"); return "qr_post_quadrado", (L,L)

# ---------------- STORY 1080x1920: cabe mensagem ----------------
def story():
    L, A = 1080, 1920; im = Image.new("RGB",(L,A),PRETO); d = ImageDraw.Draw(im); poste(d,L,14)
    y = logo_topo(im, 150, 250, L) + 56
    ft = fonte("ariblk.ttf",92)
    centro(d, y, "AGENDE SEU", ft, BRANCO, L); y += 104
    centro(d, y, "HORÁRIO", ft, AMARELO, L); y += 124
    centro(d, y, "Pelo celular, a qualquer hora", fonte("arial.ttf",40), CINZA, L); y += 86
    y = cartao_qr(im, d, y, 620, L, 40) + 42
    centro(d, y, "Aponte a câmera do celular", fonte("arialbd.ttf",38), BRANCO, L); y += 58
    centro(d, y, URL_TXT, fonte("arial.ttf",32), AMARELO, L)
    fb = fonte("arial.ttf",31); yb = A - 190
    for t in ["Escolha o profissional e o serviço",
              "Veja os horários livres na hora",
              "Receba a confirmação por e-mail"]:
        centro(d, yb, "•  " + t, fb, CINZA, L); yb += 46
    im.save(f"{RAIZ}/divulgacao/qr_story.png"); return "qr_story", (L,A)

for f in (quadrado, story):
    nome, tam = f(); print(f"  gerado: {nome}.png {tam}")

"""
Shared presentation assets for the role user guides.

Kept separate from the content (build_guides.py) so the look can be changed
in one place without touching what each guide says. Colours follow the
brand palette: #F1AB15 yellow, black, white.
"""

CSS = """
:root{
  --y:#F1AB15;--yt:#FCEDCB;--yd:#C98C0C;--k:#0B0B0C;
  --i9:#14151A;--i7:#3B3D45;--i5:#6B6E78;--i3:#A7AAB3;--i15:#DFE1E6;--i1:#F1F2F4;
  --bg:#F7F8FA;--ok:#1F9D55;--okb:#E9F7EF;--no:#D8332A;--nob:#FDECEA;
  --wa:#8A6100;--wab:#FEF6E7;--in:#2568C9;--inb:#EAF2FD;
  --fd:'Manrope','Noto Sans Ethiopic',sans-serif;
  --fb:'Inter','Noto Sans Ethiopic',sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:var(--fb);color:var(--i9);background:#fff;line-height:1.62;font-size:14.5px}
.page{padding:0 34px}

/* ---------- cover ---------- */
.cover{background:var(--k);color:#fff;padding:58px 40px 46px;position:relative;overflow:hidden}
.cover::after{content:"";position:absolute;width:520px;height:520px;right:-190px;top:-230px;
  border-radius:50%;background:radial-gradient(circle,rgba(241,171,21,.30),transparent 68%)}
.cover .mark{width:56px;height:56px;background:var(--y);border-radius:14px;display:flex;
  align-items:center;justify-content:center;font-family:var(--fd);font-weight:800;color:var(--k);
  font-size:19px;margin-bottom:22px;position:relative;z-index:1}
.cover .kicker{font-family:var(--fb);font-weight:700;letter-spacing:.16em;text-transform:uppercase;
  font-size:11.5px;color:var(--y);margin:0 0 8px;position:relative;z-index:1}
.cover h1{font-family:var(--fd);font-weight:800;font-size:38px;line-height:1.1;margin:0 0 12px;
  position:relative;z-index:1}
.cover .sub{color:#C3C5CC;font-size:16px;margin:0;max-width:560px;position:relative;z-index:1}
.cover .meta{margin-top:26px;display:flex;gap:26px;flex-wrap:wrap;position:relative;z-index:1}
.cover .meta div{font-size:12.5px;color:#9C9FA7}
.cover .meta strong{display:block;color:#fff;font-size:14px;font-weight:600}

/* ---------- headings ---------- */
h2{font-family:var(--fd);font-weight:800;font-size:24px;margin:34px 0 4px;padding-top:16px;
  border-top:3px solid var(--k)}
h3{font-family:var(--fd);font-weight:800;font-size:17.5px;margin:26px 0 8px}
h4{font-family:var(--fd);font-weight:700;font-size:15px;margin:18px 0 6px}
.lead{color:var(--i5);margin:0 0 16px;font-size:15px}

/* ---------- blocks ---------- */
.card{background:#fff;border:1px solid var(--i15);border-radius:13px;padding:20px 22px;margin:16px 0}
.tint{background:var(--bg)}
.note,.warn,.ok,.info{padding:13px 17px;border-radius:0 9px 9px 0;margin:14px 0;font-size:14px}
.note{background:var(--yt);border-left:4px solid var(--y)}
.warn{background:var(--nob);border-left:4px solid var(--no)}
.ok{background:var(--okb);border-left:4px solid var(--ok)}
.info{background:var(--inb);border-left:4px solid var(--in)}
.note strong,.warn strong,.ok strong,.info strong{font-family:var(--fd)}

/* ---------- numbered steps ---------- */
.steps{counter-reset:s;list-style:none;padding:0;margin:10px 0 0}
.steps>li{counter-increment:s;position:relative;padding:0 0 16px 48px}
.steps>li::before{content:counter(s);position:absolute;left:0;top:-1px;width:32px;height:32px;
  background:var(--y);color:var(--k);border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-family:var(--fd);font-weight:800;font-size:14px}
.steps>li strong{display:block;font-size:15px;margin-bottom:1px}
.steps>li span{color:var(--i5);font-size:14px}
.steps>li em{color:var(--i7);font-style:normal;background:var(--i1);padding:1px 6px;border-radius:4px;
  font-size:13px;font-family:var(--fb)}

/* ---------- tables ---------- */
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--i15);
  border-radius:10px;overflow:hidden;margin:14px 0;font-size:13.5px}
th{background:var(--y);color:var(--k);text-align:left;padding:10px 12px;font-size:11.5px;
  text-transform:uppercase;letter-spacing:.05em;font-weight:700}
td{padding:9px 12px;border-top:1px solid var(--i15);vertical-align:top}
tr:nth-child(even) td{background:#FCFCFD}
.yes{color:var(--ok);font-weight:700}.non{color:var(--no);font-weight:700}
code{background:var(--i1);padding:1.5px 6px;border-radius:4px;font-size:12.5px}

/* ---------- figures ---------- */
.figure{border:1px solid var(--i15);border-radius:13px;padding:14px;margin:18px 0;background:#fff}
.figure svg{display:block;width:100%;height:auto}
.figcap{color:var(--i5);font-size:12.5px;text-align:center;margin-top:9px}

/* ---------- misc ---------- */
.toc{background:var(--bg);border:1px solid var(--i15);border-radius:13px;padding:18px 24px;margin:22px 0}
.toc ol{margin:8px 0 0;padding-left:20px}
.toc li{margin:4px 0;font-size:14px}
.pill{display:inline-block;background:var(--k);color:#fff;border-radius:999px;padding:3px 12px;
  font-size:11.5px;font-weight:600;letter-spacing:.02em}
.pill.y{background:var(--y);color:var(--k)}
.kbd{border:1px solid var(--i3);border-bottom-width:2px;border-radius:5px;padding:1px 7px;
  font-size:12.5px;background:#fff}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.mini{font-size:13px;color:var(--i5)}
.tick{color:var(--ok);font-weight:700}
.footer{margin-top:38px;padding-top:16px;border-top:1px solid var(--i15);color:var(--i5);font-size:12px}

/* ---------- print ---------- */
@page{size:A4;margin:14mm 0 16mm}
@media print{
  body{font-size:11.6pt}
  .page{padding:0 16mm}
  .cover{padding:44px 16mm 38px;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  h2{page-break-after:avoid;break-after:avoid}
  h3,h4{page-break-after:avoid;break-after:avoid}
  .card,.figure,table,.note,.warn,.ok,.info,.steps>li{page-break-inside:avoid;break-inside:avoid}
  th,.cover,.pill,.note,.warn,.ok,.info,.steps>li::before{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .pagebreak{page-break-before:always;break-before:page}
}
"""

FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800'
         '&family=Inter:wght@400;500;600;700&family=Noto+Sans+Ethiopic:wght@400;600'
         '&display=swap" rel="stylesheet">')


# ---------------------------------------------------------------------------
# Reusable diagrams
# ---------------------------------------------------------------------------
def svg_screen_layout():
    return """
<div class="figure">
<svg viewBox="0 0 880 400" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Diagram of the three parts of every screen">
 <rect width="880" height="400" fill="#fff"/>
 <rect x="14" y="14" width="190" height="372" rx="10" fill="#0B0B0C"/>
 <rect x="30" y="30" width="24" height="24" rx="6" fill="#F1AB15"/>
 <rect x="62" y="34" width="98" height="7" rx="3" fill="#fff" opacity=".85"/>
 <rect x="62" y="46" width="66" height="5" rx="2" fill="#fff" opacity=".4"/>
 <g fill="#fff" opacity=".5">
  <rect x="30" y="84" width="140" height="8" rx="4"/><rect x="30" y="106" width="122" height="8" rx="4"/>
  <rect x="30" y="152" width="136" height="8" rx="4"/><rect x="30" y="174" width="110" height="8" rx="4"/>
  <rect x="30" y="196" width="128" height="8" rx="4"/>
 </g>
 <rect x="22" y="122" width="174" height="21" rx="6" fill="#F1AB15" opacity=".2"/>
 <rect x="22" y="122" width="3" height="21" fill="#F1AB15"/>
 <rect x="30" y="128" width="112" height="8" rx="4" fill="#fff"/>
 <rect x="218" y="14" width="648" height="54" rx="10" fill="#fff" stroke="#DFE1E6"/>
 <rect x="236" y="28" width="140" height="9" rx="4" fill="#0B0B0C"/>
 <rect x="236" y="43" width="88" height="6" rx="3" fill="#6B6E78"/>
 <circle cx="686" cy="41" r="13" fill="#F7F8FA" stroke="#DFE1E6"/><text x="686" y="46" font-size="12" text-anchor="middle">🌐</text>
 <circle cx="726" cy="41" r="13" fill="#F7F8FA" stroke="#DFE1E6"/><text x="726" y="46" font-size="12" text-anchor="middle">🔔</text>
 <circle cx="737" cy="31" r="6.5" fill="#D8332A"/><text x="737" y="34.5" font-size="8" fill="#fff" text-anchor="middle" font-weight="bold">3</text>
 <rect x="762" y="28" width="86" height="26" rx="7" fill="#F7F8FA" stroke="#DFE1E6"/>
 <text x="805" y="45" font-size="11.5" text-anchor="middle" fill="#3B3D45" font-family="Inter">Your name ▾</text>
 <rect x="218" y="80" width="648" height="306" rx="10" fill="#F7F8FA" stroke="#DFE1E6" stroke-dasharray="5 4"/>
 <text x="542" y="238" font-size="15.5" text-anchor="middle" fill="#6B6E78" font-family="Inter">Your work appears here</text>
 <g font-family="Manrope" font-weight="800" font-size="12">
  <circle cx="109" cy="290" r="14" fill="#F1AB15"/><text x="109" y="295" text-anchor="middle" fill="#0B0B0C">1</text>
  <circle cx="470" cy="41" r="14" fill="#F1AB15"/><text x="470" y="46" text-anchor="middle" fill="#0B0B0C">2</text>
  <circle cx="542" cy="310" r="14" fill="#F1AB15"/><text x="542" y="315" text-anchor="middle" fill="#0B0B0C">3</text>
 </g>
</svg>
<div class="figcap"><strong>1</strong> Menu (only your pages) &nbsp;·&nbsp;
 <strong>2</strong> Language, alerts, sign out &nbsp;·&nbsp; <strong>3</strong> Main work area</div>
</div>"""


def svg_pos():
    return """
<div class="figure">
<svg viewBox="0 0 880 450" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Point of Sale screen">
 <rect width="880" height="450" fill="#fff"/>
 <rect x="14" y="14" width="512" height="80" rx="10" fill="#fff" stroke="#DFE1E6"/>
 <text x="34" y="38" font-size="11.5" fill="#6B6E78" font-family="Inter">Scan barcode or type a name / code</text>
 <rect x="34" y="48" width="472" height="34" rx="8" fill="#F7F8FA" stroke="#F1AB15" stroke-width="2"/>
 <text x="50" y="70" font-size="13.5" fill="#3B3D45" font-family="Inter">▌ para</text>
 <rect x="14" y="106" width="512" height="330" rx="10" fill="#fff" stroke="#DFE1E6"/>
 <text x="34" y="130" font-size="12.5" font-family="Manrope" font-weight="800">Search results</text>
 <g font-family="Inter" font-size="12">
  <rect x="30" y="142" width="480" height="50" rx="8" fill="#FCEDCB"/>
  <text x="44" y="163" font-weight="600">Paracetamol 500mg</text>
  <text x="44" y="181" fill="#6B6E78">Medicine · 492 available</text>
  <text x="398" y="163" font-weight="600">3.00 ETB</text>
  <rect x="442" y="155" width="56" height="24" rx="6" fill="#F1AB15"/>
  <text x="470" y="171" text-anchor="middle" font-weight="700" font-size="11.5">Add</text>
  <rect x="30" y="200" width="480" height="50" rx="8" fill="#FAFBFC"/>
  <text x="44" y="221" font-weight="600">Amoxicillin 250mg</text>
  <text x="44" y="239" fill="#6B6E78">Medicine · 108 available</text>
  <rect x="146" y="228" width="30" height="14" rx="4" fill="#FDECEA"/>
  <text x="161" y="238.5" fill="#D8332A" font-size="9.5" font-weight="700" text-anchor="middle">Rx</text>
  <text x="398" y="221" font-weight="600">8.50 ETB</text>
  <rect x="442" y="213" width="56" height="24" rx="6" fill="#F1AB15"/>
  <text x="470" y="229" text-anchor="middle" font-weight="700" font-size="11.5">Add</text>
  <rect x="30" y="258" width="480" height="50" rx="8" fill="#FAFBFC"/>
  <text x="44" y="279" font-weight="600">Knee Support Brace (Medium)</text>
  <text x="44" y="297" fill="#6B6E78">Medical Device · 10 available · no expiry</text>
  <text x="390" y="279" font-weight="600">595.00 ETB</text>
  <rect x="442" y="271" width="56" height="24" rx="6" fill="#F1AB15"/>
  <text x="470" y="287" text-anchor="middle" font-weight="700" font-size="11.5">Add</text>
 </g>
 <rect x="542" y="14" width="324" height="188" rx="10" fill="#fff" stroke="#DFE1E6"/>
 <text x="560" y="36" font-size="12.5" font-family="Manrope" font-weight="800">Basket</text>
 <line x1="556" y1="46" x2="852" y2="46" stroke="#DFE1E6"/>
 <g font-family="Inter" font-size="11.5">
  <text x="560" y="66" font-weight="600">Paracetamol 500mg</text>
  <rect x="560" y="74" width="44" height="22" rx="5" fill="#F7F8FA" stroke="#DFE1E6"/><text x="582" y="89" text-anchor="middle">10</text>
  <text x="610" y="89" fill="#6B6E78">qty</text>
  <rect x="650" y="74" width="44" height="22" rx="5" fill="#F7F8FA" stroke="#DFE1E6"/><text x="672" y="89" text-anchor="middle">0</text>
  <text x="700" y="89" fill="#6B6E78">disc%</text>
  <text x="852" y="89" text-anchor="end" font-weight="700">34.50</text>
  <line x1="556" y1="108" x2="852" y2="108" stroke="#F1F2F4"/>
  <text x="560" y="128" font-weight="600">Knee Support Brace</text>
  <rect x="560" y="136" width="44" height="22" rx="5" fill="#F7F8FA" stroke="#DFE1E6"/><text x="582" y="151" text-anchor="middle">1</text>
  <text x="852" y="151" text-anchor="end" font-weight="700">684.25</text>
 </g>
 <rect x="542" y="214" width="324" height="222" rx="10" fill="#fff" stroke="#DFE1E6"/>
 <g font-family="Inter" font-size="12" fill="#3B3D45">
  <text x="560" y="238">Subtotal</text><text x="852" y="238" text-anchor="end">625.00</text>
  <text x="560" y="258">Discount</text><text x="852" y="258" text-anchor="end">0.00</text>
  <text x="560" y="278">VAT</text><text x="852" y="278" text-anchor="end">93.75</text>
 </g>
 <line x1="556" y1="290" x2="852" y2="290" stroke="#0B0B0C" stroke-width="2"/>
 <text x="560" y="312" font-family="Manrope" font-weight="800" font-size="14">Total</text>
 <text x="852" y="313" text-anchor="end" font-family="Manrope" font-weight="800" font-size="16">718.75</text>
 <g font-family="Inter" font-size="11" fill="#6B6E78">
  <text x="560" y="338">Customer</text><text x="560" y="366">Payment</text><text x="560" y="394">Paid</text>
 </g>
 <rect x="632" y="326" width="220" height="23" rx="6" fill="#F7F8FA" stroke="#DFE1E6"/>
 <text x="643" y="342" font-size="11" font-family="Inter">Walk-in customer ▾</text>
 <rect x="632" y="354" width="220" height="23" rx="6" fill="#F7F8FA" stroke="#DFE1E6"/>
 <text x="643" y="370" font-size="11" font-family="Inter">Cash ▾</text>
 <rect x="632" y="382" width="220" height="23" rx="6" fill="#F7F8FA" stroke="#DFE1E6"/>
 <text x="643" y="398" font-size="11" font-family="Inter">800.00</text>
 <rect x="556" y="412" width="296" height="16" rx="5" fill="#F1AB15"/>
 <text x="704" y="424" font-size="10.5" text-anchor="middle" font-family="Manrope" font-weight="800">COMPLETE SALE</text>
 <g font-family="Manrope" font-weight="800" font-size="11.5">
  <circle cx="270" cy="65" r="13" fill="#0B0B0C"/><text x="270" y="70" text-anchor="middle" fill="#F1AB15">1</text>
  <circle cx="270" cy="167" r="13" fill="#0B0B0C"/><text x="270" y="172" text-anchor="middle" fill="#F1AB15">2</text>
  <circle cx="706" cy="55" r="13" fill="#0B0B0C"/><text x="706" y="60" text-anchor="middle" fill="#F1AB15">3</text>
  <circle cx="706" cy="366" r="13" fill="#0B0B0C"/><text x="706" y="371" text-anchor="middle" fill="#F1AB15">4</text>
 </g>
</svg>
<div class="figcap"><strong>1</strong> Scan or search &nbsp;·&nbsp; <strong>2</strong> Check type, stock, Rx tag
 &nbsp;·&nbsp; <strong>3</strong> Adjust qty / discount &nbsp;·&nbsp; <strong>4</strong> Customer, payment, cash taken</div>
</div>"""


def svg_batch_costing():
    return """
<div class="figure">
<svg viewBox="0 0 880 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="How batch costing works">
 <rect width="880" height="400" fill="#fff"/>
 <text x="20" y="26" font-family="Manrope" font-weight="800" font-size="14">Same product bought twice at different prices</text>
 <rect x="20" y="42" width="246" height="104" rx="12" fill="#FCEDCB" stroke="#F1AB15" stroke-width="2"/>
 <text x="38" y="66" font-family="Manrope" font-weight="800" font-size="12.5">Older batch</text>
 <g font-family="Inter" font-size="12.5" fill="#3B3D45">
  <text x="38" y="88">40 pieces</text><text x="38" y="108">cost 20 ETB each</text>
  <text x="38" y="130" font-weight="600" fill="#0B0B0C">was sold at 50 ETB</text>
 </g>
 <rect x="286" y="42" width="246" height="104" rx="12" fill="#EAF2FD" stroke="#2568C9" stroke-width="2"/>
 <text x="304" y="66" font-family="Manrope" font-weight="800" font-size="12.5">Newer batch</text>
 <g font-family="Inter" font-size="12.5" fill="#3B3D45">
  <text x="304" y="88">100 pieces</text><text x="304" y="108">cost 30 ETB each</text>
  <text x="304" y="130" font-weight="600" fill="#0B0B0C">now sold at 60 ETB</text>
 </g>
 <rect x="552" y="42" width="308" height="104" rx="12" fill="#FAFBFC" stroke="#DFE1E6"/>
 <text x="570" y="66" font-family="Manrope" font-weight="800" font-size="12.5">Kept separate, forever</text>
 <g font-family="Inter" font-size="12" fill="#3B3D45">
  <text x="570" y="88">Each delivery keeps its own cost.</text>
  <text x="570" y="107">Nothing overwrites anything.</text>
  <text x="570" y="126">Soonest expiry is sold first.</text>
 </g>
 <line x1="20" y1="168" x2="860" y2="168" stroke="#DFE1E6"/>
 <text x="20" y="194" font-family="Manrope" font-weight="800" font-size="14">You sell 50 pieces</text>
 <rect x="20" y="210" width="226" height="70" rx="10" fill="#FCEDCB" stroke="#F1AB15"/>
 <text x="133" y="236" font-family="Inter" font-size="12.5" text-anchor="middle" font-weight="600">40 from older batch</text>
 <text x="133" y="260" font-family="Inter" font-size="12" text-anchor="middle" fill="#3B3D45">40 × 20 = 800</text>
 <text x="262" y="252" font-size="19" fill="#6B6E78">+</text>
 <rect x="286" y="210" width="226" height="70" rx="10" fill="#EAF2FD" stroke="#2568C9"/>
 <text x="399" y="236" font-family="Inter" font-size="12.5" text-anchor="middle" font-weight="600">10 from newer batch</text>
 <text x="399" y="260" font-family="Inter" font-size="12" text-anchor="middle" fill="#3B3D45">10 × 30 = 300</text>
 <text x="528" y="252" font-size="19" fill="#6B6E78">=</text>
 <rect x="552" y="210" width="308" height="70" rx="10" fill="#0B0B0C"/>
 <text x="706" y="236" font-family="Inter" font-size="12.5" text-anchor="middle" fill="#B9BBC2">True cost of those 50</text>
 <text x="706" y="263" font-family="Manrope" font-weight="800" font-size="18" text-anchor="middle" fill="#F1AB15">1,100 ETB</text>
 <rect x="20" y="300" width="840" height="82" rx="12" fill="#E9F7EF" stroke="#1F9D55" stroke-width="2"/>
 <g font-family="Inter" font-size="13" fill="#3B3D45">
  <text x="42" y="328">Money in (50 × 60, VAT excluded)</text><text x="392" y="328" font-weight="700" fill="#0B0B0C">3,000 ETB</text>
  <text x="42" y="352">Less true cost of goods</text><text x="392" y="352" font-weight="700" fill="#0B0B0C">− 1,100 ETB</text>
  <text x="42" y="372" font-size="11.5" fill="#6B6E78">Buying more later at 45 ETB does not change this figure.</text>
 </g>
 <text x="620" y="330" font-family="Inter" font-size="12.5" fill="#3B3D45">Gross profit</text>
 <text x="620" y="362" font-family="Manrope" font-weight="800" font-size="23" fill="#1F9D55">1,900 ETB</text>
</svg>
<div class="figcap">Older units are costed at the older price — which is why profit stays correct</div>
</div>"""


def svg_purchase_form():
    return """
<div class="figure">
<svg viewBox="0 0 880 292" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Record purchase form">
 <rect width="880" height="292" fill="#fff"/>
 <rect x="14" y="14" width="852" height="264" rx="12" fill="#fff" stroke="#DFE1E6"/>
 <g font-family="Inter" font-size="11" fill="#6B6E78"><text x="36" y="46">Supplier</text><text x="462" y="46">Purchase date</text></g>
 <rect x="36" y="54" width="388" height="28" rx="7" fill="#F7F8FA" stroke="#DFE1E6"/>
 <text x="48" y="73" font-size="12" font-family="Inter">Addis Pharma Distribution ▾</text>
 <rect x="462" y="54" width="382" height="28" rx="7" fill="#F7F8FA" stroke="#DFE1E6"/>
 <text x="474" y="73" font-size="12" font-family="Inter">2026-08-13</text>
 <line x1="36" y1="98" x2="844" y2="98" stroke="#DFE1E6"/>
 <text x="36" y="120" font-size="12.5" font-family="Manrope" font-weight="800">Line items</text>
 <rect x="730" y="106" width="114" height="25" rx="7" fill="#fff" stroke="#0B0B0C" stroke-width="1.5"/>
 <text x="787" y="123" font-size="11.5" text-anchor="middle" font-family="Inter" font-weight="700">+ Add Item</text>
 <rect x="36" y="142" width="808" height="70" rx="9" fill="#F7F8FA" stroke="#DFE1E6"/>
 <g font-family="Inter" font-size="10" fill="#6B6E78">
  <text x="52" y="161">Product</text><text x="282" y="161">Qty</text><text x="372" y="161">Cost each</text>
  <text x="500" y="161">New selling price</text><text x="660" y="161">Disc %</text><text x="750" y="161">VAT %</text>
 </g>
 <g font-family="Inter" font-size="11.5">
  <rect x="48" y="169" width="218" height="26" rx="6" fill="#fff" stroke="#DFE1E6"/><text x="60" y="187">Paracetamol 500mg ▾</text>
  <rect x="278" y="169" width="78" height="26" rx="6" fill="#fff" stroke="#DFE1E6"/><text x="317" y="187" text-anchor="middle">100</text>
  <rect x="368" y="169" width="118" height="26" rx="6" fill="#fff" stroke="#DFE1E6"/><text x="427" y="187" text-anchor="middle">30.00</text>
  <rect x="496" y="169" width="148" height="26" rx="6" fill="#FCEDCB" stroke="#F1AB15" stroke-width="1.5"/><text x="570" y="187" text-anchor="middle">60.00</text>
  <rect x="656" y="169" width="78" height="26" rx="6" fill="#fff" stroke="#DFE1E6"/><text x="695" y="187" text-anchor="middle">0</text>
  <rect x="744" y="169" width="78" height="26" rx="6" fill="#fff" stroke="#DFE1E6"/><text x="783" y="187" text-anchor="middle">15</text>
 </g>
 <text x="686" y="240" font-size="11.5" font-family="Inter" fill="#6B6E78">Invoice total</text>
 <text x="844" y="242" font-size="16" text-anchor="end" font-family="Manrope" font-weight="800">3,450.00</text>
 <rect x="36" y="252" width="808" height="16" rx="5" fill="#F1AB15"/>
 <text x="440" y="264" font-size="10.5" text-anchor="middle" font-family="Manrope" font-weight="800">SAVE PURCHASE &amp; UPDATE STOCK</text>
 <g font-family="Manrope" font-weight="800" font-size="11">
  <circle cx="787" cy="90" r="13" fill="#0B0B0C"/><text x="787" y="95" text-anchor="middle" fill="#F1AB15">+</text>
  <circle cx="570" cy="140" r="13" fill="#F1AB15"/><text x="570" y="145" text-anchor="middle">!</text>
 </g>
</svg>
<div class="figcap">Starts with <strong>one</strong> row. <span style="color:#C98C0C">+ Add Item</span> adds more.
 The yellow box is optional — fill it only if the customer price is changing.</div>
</div>"""


def svg_inventory():
    return """
<div class="figure">
<svg viewBox="0 0 880 288" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Inventory page">
 <rect width="880" height="288" fill="#fff"/>
 <g font-family="Inter">
  <rect x="14" y="14" width="202" height="76" rx="12" fill="#fff" stroke="#DFE1E6"/><rect x="14" y="14" width="4" height="76" fill="#F1AB15"/>
  <text x="34" y="40" font-size="10.5" fill="#6B6E78">TOTAL STOCK UNITS</text>
  <text x="34" y="72" font-family="Manrope" font-weight="800" font-size="22">1,284</text>
  <rect x="228" y="14" width="202" height="76" rx="12" fill="#fff" stroke="#DFE1E6"/><rect x="228" y="14" width="4" height="76" fill="#D8332A"/>
  <text x="248" y="40" font-size="10.5" fill="#6B6E78">LOW STOCK</text>
  <text x="248" y="72" font-family="Manrope" font-weight="800" font-size="22" fill="#D8332A">3</text>
  <rect x="442" y="14" width="202" height="76" rx="12" fill="#fff" stroke="#DFE1E6"/><rect x="442" y="14" width="4" height="76" fill="#D8332A"/>
  <text x="462" y="40" font-size="10.5" fill="#6B6E78">OUT OF STOCK</text>
  <text x="462" y="72" font-family="Manrope" font-weight="800" font-size="22" fill="#D8332A">1</text>
  <rect x="656" y="14" width="210" height="76" rx="12" fill="#FCEDCB" stroke="#F1AB15" stroke-width="2"/><rect x="656" y="14" width="4" height="76" fill="#D8332A"/>
  <text x="676" y="40" font-size="10.5" fill="#6B6E78">EXPIRED</text>
  <text x="676" y="72" font-family="Manrope" font-weight="800" font-size="22" fill="#D8332A">2</text>
  <text x="784" y="72" font-size="10.5" fill="#3B3D45">← all clickable</text>
  <rect x="14" y="102" width="852" height="172" rx="12" fill="#fff" stroke="#DFE1E6"/>
  <text x="34" y="126" font-size="12.5" font-family="Manrope" font-weight="800">Current stock</text>
  <line x1="30" y1="136" x2="850" y2="136" stroke="#DFE1E6"/>
  <g font-size="10.5" fill="#6B6E78"><text x="34" y="154">PRODUCT</text><text x="318" y="154">TYPE</text>
   <text x="488" y="154">QTY</text><text x="574" y="154">EXPIRY</text><text x="726" y="154">STATUS</text></g>
  <g font-size="12">
   <text x="34" y="180" font-weight="600">Paracetamol 500mg</text><text x="318" y="180" fill="#3B3D45">Medicine</text>
   <text x="488" y="180">492</text><text x="574" y="180">2028-02-04</text>
   <rect x="726" y="169" width="40" height="16" rx="4" fill="#E9F7EF"/><text x="746" y="181" font-size="10" fill="#1F9D55" text-anchor="middle" font-weight="700">OK</text>
   <text x="34" y="208" font-weight="600">Amoxicillin 250mg</text><text x="318" y="208" fill="#3B3D45">Medicine</text>
   <text x="488" y="208">8</text><text x="574" y="208">2026-09-02</text>
   <rect x="726" y="197" width="40" height="16" rx="4" fill="#FEF6E7"/><text x="746" y="209" font-size="10" fill="#8A6100" text-anchor="middle" font-weight="700">LOW</text>
   <text x="34" y="236" font-weight="600">Knee Support Brace</text><text x="318" y="236" fill="#3B3D45">Medical Device</text>
   <text x="488" y="236">10</text><text x="574" y="236" fill="#6B6E78">— none</text>
   <rect x="726" y="225" width="40" height="16" rx="4" fill="#E9F7EF"/><text x="746" y="237" font-size="10" fill="#1F9D55" text-anchor="middle" font-weight="700">OK</text>
   <text x="34" y="264" font-weight="600">Nivea Cream 200ml</text><text x="318" y="264" fill="#3B3D45">Cosmetic</text>
   <text x="488" y="264">27</text><text x="574" y="264">2028-08-12</text>
   <rect x="726" y="253" width="40" height="16" rx="4" fill="#E9F7EF"/><text x="746" y="265" font-size="10" fill="#1F9D55" text-anchor="middle" font-weight="700">OK</text>
  </g>
 </g>
</svg>
<div class="figcap">The device shows “— none” for expiry. That is correct: it does not expire.</div>
</div>"""


def svg_product_types():
    return """
<div class="figure">
<svg viewBox="0 0 880 214" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Product types">
 <rect width="880" height="214" fill="#fff"/>
 <g font-family="Inter">
  <g><rect x="14" y="16" width="196" height="80" rx="12" fill="#FCEDCB" stroke="#F1AB15"/>
   <text x="112" y="48" font-size="23" text-anchor="middle">💊</text>
   <text x="112" y="72" font-size="12.5" text-anchor="middle" font-weight="700">Medicines</text>
   <text x="112" y="88" font-size="10.5" text-anchor="middle" fill="#6B6E78">tablets, syrups</text></g>
  <g><rect x="226" y="16" width="196" height="80" rx="12" fill="#FAFBFC" stroke="#DFE1E6"/>
   <text x="324" y="48" font-size="23" text-anchor="middle">🧴</text>
   <text x="324" y="72" font-size="12.5" text-anchor="middle" font-weight="700">Cosmetics</text>
   <text x="324" y="88" font-size="10.5" text-anchor="middle" fill="#6B6E78">creams, lotions</text></g>
  <g><rect x="438" y="16" width="196" height="80" rx="12" fill="#FAFBFC" stroke="#DFE1E6"/>
   <text x="536" y="48" font-size="23" text-anchor="middle">🩹</text>
   <text x="536" y="72" font-size="12.5" text-anchor="middle" font-weight="700">Medical Supplies</text>
   <text x="536" y="88" font-size="10.5" text-anchor="middle" fill="#6B6E78">bandages, gauze</text></g>
  <g><rect x="650" y="16" width="216" height="80" rx="12" fill="#FAFBFC" stroke="#DFE1E6"/>
   <text x="758" y="48" font-size="23" text-anchor="middle">🦵</text>
   <text x="758" y="72" font-size="12.5" text-anchor="middle" font-weight="700">Devices &amp; Supports</text>
   <text x="758" y="88" font-size="10.5" text-anchor="middle" fill="#6B6E78">braces, BP monitors</text></g>
  <g><rect x="14" y="110" width="196" height="80" rx="12" fill="#FAFBFC" stroke="#DFE1E6"/>
   <text x="112" y="142" font-size="23" text-anchor="middle">🍊</text>
   <text x="112" y="166" font-size="12.5" text-anchor="middle" font-weight="700">Supplements</text>
   <text x="112" y="182" font-size="10.5" text-anchor="middle" fill="#6B6E78">vitamins</text></g>
  <g><rect x="226" y="110" width="196" height="80" rx="12" fill="#FAFBFC" stroke="#DFE1E6"/>
   <text x="324" y="142" font-size="23" text-anchor="middle">🍼</text>
   <text x="324" y="166" font-size="12.5" text-anchor="middle" font-weight="700">Baby &amp; Mother</text>
   <text x="324" y="182" font-size="10.5" text-anchor="middle" fill="#6B6E78">nappies, formula</text></g>
  <g><rect x="438" y="110" width="428" height="80" rx="12" fill="#E9F7EF" stroke="#1F9D55"/>
   <text x="652" y="142" font-size="13" text-anchor="middle" font-weight="700">All types behave identically</text>
   <text x="652" y="163" font-size="11.5" text-anchor="middle" fill="#3B3D45">Same till · same stock counts · same batch costing · same reports</text>
   <text x="652" y="180" font-size="11.5" text-anchor="middle" fill="#3B3D45">Nothing extra to learn per type</text></g>
 </g>
</svg>
</div>"""


def svg_dashboard():
    return """
<div class="figure">
<svg viewBox="0 0 880 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Administrator dashboard">
 <rect width="880" height="340" fill="#fff"/>
 <g font-family="Inter">
  <rect x="14" y="14" width="204" height="66" rx="11" fill="#fff" stroke="#DFE1E6"/>
  <text x="32" y="38" font-size="10" fill="#6B6E78">PURCHASE VALUE (ETB)</text>
  <text x="32" y="66" font-family="Manrope" font-weight="800" font-size="19">48,320</text>
  <rect x="230" y="14" width="204" height="66" rx="11" fill="#fff" stroke="#DFE1E6"/>
  <text x="248" y="38" font-size="10" fill="#6B6E78">SALES VALUE (ETB)</text>
  <text x="248" y="66" font-family="Manrope" font-weight="800" font-size="19">71,940</text>
  <rect x="446" y="14" width="204" height="66" rx="11" fill="#FCEDCB" stroke="#F1AB15" stroke-width="2"/>
  <text x="464" y="38" font-size="10" fill="#6B6E78">PROFIT SUMMARY (ETB)</text>
  <text x="464" y="66" font-family="Manrope" font-weight="800" font-size="19" fill="#1F9D55">23,620</text>
  <rect x="662" y="14" width="204" height="66" rx="11" fill="#fff" stroke="#DFE1E6"/>
  <text x="680" y="38" font-size="10" fill="#6B6E78">EXPIRED ITEMS</text>
  <text x="680" y="66" font-family="Manrope" font-weight="800" font-size="19" fill="#D8332A">2</text>

  <rect x="14" y="94" width="560" height="232" rx="11" fill="#fff" stroke="#DFE1E6"/>
  <text x="34" y="118" font-size="12.5" font-family="Manrope" font-weight="800">Revenue vs Cost of Goods Sold</text>
  <text x="34" y="134" font-size="10.5" fill="#6B6E78">The gap between the bars is your gross margin</text>
  <line x1="60" y1="290" x2="552" y2="290" stroke="#DFE1E6"/>
  <g>
   <rect x="86" y="196" width="22" height="94" fill="#F1AB15"/><rect x="112" y="232" width="22" height="58" fill="#0B0B0C"/>
   <rect x="166" y="184" width="22" height="106" fill="#F1AB15"/><rect x="192" y="226" width="22" height="64" fill="#0B0B0C"/>
   <rect x="246" y="170" width="22" height="120" fill="#F1AB15"/><rect x="272" y="220" width="22" height="70" fill="#0B0B0C"/>
   <rect x="326" y="158" width="22" height="132" fill="#F1AB15"/><rect x="352" y="206" width="22" height="84" fill="#0B0B0C"/>
   <rect x="406" y="150" width="22" height="140" fill="#F1AB15"/><rect x="432" y="198" width="22" height="92" fill="#0B0B0C"/>
   <rect x="486" y="164" width="22" height="126" fill="#F1AB15"/><rect x="512" y="212" width="22" height="78" fill="#0B0B0C"/>
  </g>
  <g font-size="9.5" fill="#6B6E78">
   <text x="110" y="304" text-anchor="middle">Mar</text><text x="190" y="304" text-anchor="middle">Apr</text>
   <text x="270" y="304" text-anchor="middle">May</text><text x="350" y="304" text-anchor="middle">Jun</text>
   <text x="430" y="304" text-anchor="middle">Jul</text><text x="510" y="304" text-anchor="middle">Aug</text>
  </g>
  <rect x="410" y="112" width="10" height="10" fill="#F1AB15"/><text x="426" y="121" font-size="10" fill="#3B3D45">Revenue</text>
  <rect x="480" y="112" width="10" height="10" fill="#0B0B0C"/><text x="496" y="121" font-size="10" fill="#3B3D45">Cost</text>

  <rect x="590" y="94" width="276" height="232" rx="11" fill="#fff" stroke="#DFE1E6"/>
  <text x="610" y="118" font-size="12.5" font-family="Manrope" font-weight="800">Expiry Risk Profile</text>
  <text x="610" y="134" font-size="10.5" fill="#6B6E78">Bars = items · red line = value at risk</text>
  <line x1="622" y1="286" x2="850" y2="286" stroke="#DFE1E6"/>
  <rect x="636" y="246" width="26" height="40" fill="#F1AB15"/>
  <rect x="682" y="228" width="26" height="58" fill="#F1AB15"/>
  <rect x="728" y="256" width="26" height="30" fill="#F1AB15"/>
  <rect x="774" y="200" width="26" height="86" fill="#F1AB15"/>
  <polyline points="649,180 695,212 741,248 787,166" fill="none" stroke="#D8332A" stroke-width="2.5"/>
  <circle cx="649" cy="180" r="3.5" fill="#D8332A"/><circle cx="695" cy="212" r="3.5" fill="#D8332A"/>
  <circle cx="741" cy="248" r="3.5" fill="#D8332A"/><circle cx="787" cy="166" r="3.5" fill="#D8332A"/>
  <g font-size="9" fill="#6B6E78">
   <text x="649" y="300" text-anchor="middle">Expired</text><text x="695" y="300" text-anchor="middle">≤30d</text>
   <text x="741" y="300" text-anchor="middle">31–60d</text><text x="787" y="300" text-anchor="middle">61–180d</text>
  </g>
  <text x="800" y="160" font-size="9.5" fill="#D8332A" font-weight="700">watch this</text>
 </g>
</svg>
<div class="figcap">Watch the red line, not just the bars — a few expensive items can outweigh a shelf of cheap ones</div>
</div>"""


def svg_roles_matrix():
    rows = [
        ("Use the till", 1, 1, 0, 1),
        ("See stock &amp; expiry", 0, 1, 1, 1),
        ("Edit products &amp; prices", 0, 0, 1, 1),
        ("See cost &amp; profit", 0, 0, 1, 1),
        ("Record purchases", 0, 0, 1, 1),
        ("Void a sale", 0, 0, 0, 1),
        ("Settings &amp; audit log", 0, 0, 0, 1),
    ]
    y0, rh = 74, 30
    height = y0 + rh * len(rows) + 16
    cells = []
    for i, (label, c, p, s, a) in enumerate(rows):
        y = y0 + i * rh
        if i % 2 == 0:
            cells.append(f'<rect x="14" y="{y}" width="852" height="{rh}" fill="#FAFBFC"/>')
        cells.append(f'<text x="30" y="{y+20}" font-size="12" font-family="Inter" fill="#14151A">{label}</text>')
        for j, v in enumerate((c, p, s, a)):
            cx = 400 + j * 118
            if v:
                cells.append(f'<circle cx="{cx}" cy="{y+15}" r="9" fill="#E9F7EF"/>'
                             f'<text x="{cx}" y="{y+19.5}" font-size="11" text-anchor="middle" fill="#1F9D55" font-weight="700">✓</text>')
            else:
                cells.append(f'<circle cx="{cx}" cy="{y+15}" r="9" fill="#FDECEA"/>'
                             f'<text x="{cx}" y="{y+19.5}" font-size="11" text-anchor="middle" fill="#D8332A" font-weight="700">✕</text>')
    heads = ""
    for j, name in enumerate(("Cashier", "Pharmacist", "Store Mgr", "Admin")):
        cx = 400 + j * 118
        heads += (f'<text x="{cx}" y="{y0-14}" font-size="10.5" text-anchor="middle" '
                  f'font-family="Inter" font-weight="700" fill="#0B0B0C">{name}</text>')
    return f"""
<div class="figure">
<svg viewBox="0 0 880 {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Role permission matrix">
 <rect width="880" height="{height}" fill="#fff"/>
 <text x="30" y="32" font-family="Manrope" font-weight="800" font-size="14">Who can do what</text>
 <text x="30" y="50" font-family="Inter" font-size="11" fill="#6B6E78">Permissions follow the job, not seniority — the Store Manager has no till, the Cashier has no stock screens</text>
 {heads}
 <line x1="14" y1="{y0-6}" x2="866" y2="{y0-6}" stroke="#0B0B0C" stroke-width="1.5"/>
 {"".join(cells)}
</svg>
</div>"""


def svg_branches():
    return """
<div class="figure">
<svg viewBox="0 0 880 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="How branches share and separate data">
 <rect width="880" height="300" fill="#fff"/>
 <text x="20" y="26" font-family="Manrope" font-weight="800" font-size="14">What is shared, and what each branch keeps to itself</text>
 <rect x="20" y="42" width="840" height="74" rx="12" fill="#FCEDCB" stroke="#F1AB15" stroke-width="2"/>
 <text x="40" y="66" font-family="Manrope" font-weight="800" font-size="12.5">SHARED across every branch</text>
 <g font-family="Inter" font-size="12" fill="#3B3D45">
  <text x="40" y="88">Product catalogue &amp; prices &nbsp;·&nbsp; Customers &amp; loyalty points &nbsp;·&nbsp; Suppliers &nbsp;·&nbsp; Staff accounts &nbsp;·&nbsp; Settings</text>
  <text x="40" y="106" font-size="11" fill="#6B6E78">One paracetamol record, one customer record — wherever they shop.</text>
 </g>
 <g>
  <rect x="20" y="134" width="266" height="146" rx="12" fill="#fff" stroke="#DFE1E6"/>
  <text x="40" y="160" font-family="Manrope" font-weight="800" font-size="12.5">Main Branch</text>
  <rect x="196" y="146" width="72" height="18" rx="5" fill="#0B0B0C"/><text x="232" y="159" font-size="10" fill="#F1AB15" text-anchor="middle" font-family="Inter" font-weight="700">MAIN</text>
  <g font-family="Inter" font-size="11.5" fill="#3B3D45">
   <text x="40" y="186">Its own stock quantities</text><text x="40" y="206">Its own batches &amp; costs</text>
   <text x="40" y="226">Its own sales &amp; purchases</text><text x="40" y="246">Its own reorder levels</text>
   <text x="40" y="266" fill="#6B6E78" font-size="11">Invoices: INV-000001</text>
  </g>
  <rect x="307" y="134" width="266" height="146" rx="12" fill="#fff" stroke="#DFE1E6"/>
  <text x="327" y="160" font-family="Manrope" font-weight="800" font-size="12.5">Bole Branch</text>
  <g font-family="Inter" font-size="11.5" fill="#3B3D45">
   <text x="327" y="186">Its own stock quantities</text><text x="327" y="206">Its own batches &amp; costs</text>
   <text x="327" y="226">Its own sales &amp; purchases</text><text x="327" y="246">Its own reorder levels</text>
   <text x="327" y="266" fill="#6B6E78" font-size="11">Invoices: BOL-000001</text>
  </g>
  <rect x="594" y="134" width="266" height="146" rx="12" fill="#fff" stroke="#DFE1E6"/>
  <text x="614" y="160" font-family="Manrope" font-weight="800" font-size="12.5">Gondar Branch</text>
  <g font-family="Inter" font-size="11.5" fill="#3B3D45">
   <text x="614" y="186">Its own stock quantities</text><text x="614" y="206">Its own batches &amp; costs</text>
   <text x="614" y="226">Its own sales &amp; purchases</text><text x="614" y="246">Its own reorder levels</text>
   <text x="614" y="266" fill="#6B6E78" font-size="11">Invoices: GON-000001</text>
  </g>
 </g>
</svg>
<div class="figcap">You can only sell stock your own branch holds — the till will not offer another branch's shelves</div>
</div>"""


def svg_transfer():
    return """
<div class="figure">
<svg viewBox="0 0 880 230" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Transferring stock between branches">
 <rect width="880" height="230" fill="#fff"/>
 <text x="20" y="26" font-family="Manrope" font-weight="800" font-size="14">Moving 40 packs from Main to Bole</text>
 <rect x="20" y="44" width="240" height="116" rx="12" fill="#FCEDCB" stroke="#F1AB15" stroke-width="2"/>
 <text x="40" y="70" font-family="Manrope" font-weight="800" font-size="12.5">Main Branch</text>
 <g font-family="Inter" font-size="12.5" fill="#3B3D45">
  <text x="40" y="94">Before: 220 packs</text>
  <text x="40" y="116" font-weight="600" fill="#0B0B0C">After: 180 packs</text>
  <text x="40" y="140" font-size="11" fill="#6B6E78">cost 1.50 each</text>
 </g>
 <path d="M272 100 L 600 100" stroke="#0B0B0C" stroke-width="2.5" marker-end="url(#arrow)"/>
 <defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
  <polygon points="0 0, 10 4, 0 8" fill="#0B0B0C"/></marker></defs>
 <rect x="330" y="66" width="216" height="30" rx="8" fill="#0B0B0C"/>
 <text x="438" y="86" font-size="12" text-anchor="middle" fill="#F1AB15" font-family="Manrope" font-weight="800">40 packs · cost travels</text>
 <text x="438" y="124" font-size="11" text-anchor="middle" fill="#6B6E78" font-family="Inter">Expiry dates travel too, so Bole</text>
 <text x="438" y="140" font-size="11" text-anchor="middle" fill="#6B6E78" font-family="Inter">still sells soonest-expiry first</text>
 <rect x="620" y="44" width="240" height="116" rx="12" fill="#EAF2FD" stroke="#2568C9" stroke-width="2"/>
 <text x="640" y="70" font-family="Manrope" font-weight="800" font-size="12.5">Bole Branch</text>
 <g font-family="Inter" font-size="12.5" fill="#3B3D45">
  <text x="640" y="94">Before: 0 packs</text>
  <text x="640" y="116" font-weight="600" fill="#0B0B0C">After: 40 packs</text>
  <text x="640" y="140" font-size="11" fill="#6B6E78">cost still 1.50 each</text>
 </g>
 <rect x="20" y="176" width="840" height="42" rx="10" fill="#E9F7EF" stroke="#1F9D55"/>
 <text x="40" y="202" font-family="Inter" font-size="12.5" fill="#3B3D45">
  Stock arrives at the cost it left at. Nothing is created or destroyed — both branches' profit figures stay correct.</text>
</svg>
</div>"""


def svg_stocktake_flow():
    return """
<div class="figure">
<svg viewBox="0 0 880 250" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Stocktake steps">
 <rect width="880" height="250" fill="#fff"/>
 <text x="20" y="26" font-family="Manrope" font-weight="800" font-size="14">A stocktake, start to finish</text>
 <g font-family="Inter">
  <rect x="20" y="44" width="196" height="96" rx="12" fill="#FCEDCB" stroke="#F1AB15" stroke-width="2"/>
  <circle cx="44" cy="68" r="13" fill="#F1AB15"/><text x="44" y="73" font-size="12" text-anchor="middle" font-family="Manrope" font-weight="800">1</text>
  <text x="66" y="73" font-size="12.5" font-weight="700">Start</text>
  <text x="38" y="98" font-size="11.5" fill="#3B3D45">System freezes what it</text>
  <text x="38" y="114" font-size="11.5" fill="#3B3D45">thinks you have, so sales</text>
  <text x="38" y="130" font-size="11.5" fill="#3B3D45">during the count don't skew it</text>

  <rect x="232" y="44" width="196" height="96" rx="12" fill="#fff" stroke="#DFE1E6"/>
  <circle cx="256" cy="68" r="13" fill="#0B0B0C"/><text x="256" y="73" font-size="12" text-anchor="middle" fill="#F1AB15" font-family="Manrope" font-weight="800">2</text>
  <text x="278" y="73" font-size="12.5" font-weight="700">Count</text>
  <text x="250" y="98" font-size="11.5" fill="#3B3D45">Type what you actually</text>
  <text x="250" y="114" font-size="11.5" fill="#3B3D45">see on the shelf. Save as</text>
  <text x="250" y="130" font-size="11.5" fill="#3B3D45">often as you like</text>

  <rect x="444" y="44" width="196" height="96" rx="12" fill="#fff" stroke="#DFE1E6"/>
  <circle cx="468" cy="68" r="13" fill="#0B0B0C"/><text x="468" y="73" font-size="12" text-anchor="middle" fill="#F1AB15" font-family="Manrope" font-weight="800">3</text>
  <text x="490" y="73" font-size="12.5" font-weight="700">Review</text>
  <text x="462" y="98" font-size="11.5" fill="#3B3D45">Use the "Differences only"</text>
  <text x="462" y="114" font-size="11.5" fill="#3B3D45">tab. Investigate anything</text>
  <text x="462" y="130" font-size="11.5" fill="#3B3D45">large before posting</text>

  <rect x="656" y="44" width="204" height="96" rx="12" fill="#E9F7EF" stroke="#1F9D55" stroke-width="2"/>
  <circle cx="680" cy="68" r="13" fill="#1F9D55"/><text x="680" y="73" font-size="12" text-anchor="middle" fill="#fff" font-family="Manrope" font-weight="800">4</text>
  <text x="702" y="73" font-size="12.5" font-weight="700">Post</text>
  <text x="674" y="98" font-size="11.5" fill="#3B3D45">Differences are applied</text>
  <text x="674" y="114" font-size="11.5" fill="#3B3D45">to stock in one go, and</text>
  <text x="674" y="130" font-size="11.5" fill="#3B3D45">written to the ledger</text>
 </g>
 <rect x="20" y="160" width="840" height="76" rx="12" fill="#FDECEA" stroke="#D8332A" stroke-width="2"/>
 <text x="40" y="186" font-family="Manrope" font-weight="800" font-size="13" fill="#D8332A">The one thing to remember</text>
 <text x="40" y="208" font-family="Inter" font-size="12.5" fill="#3B3D45">An <tspan font-weight="700">empty</tspan> count box means "not counted yet" — it is never treated as zero.</text>
 <text x="40" y="226" font-family="Inter" font-size="12.5" fill="#3B3D45">Anything you did not get to is left exactly as it was when you post.</text>
</svg>
</div>"""


def svg_catalogue():
    return """
<div class="figure">
<svg viewBox="0 0 880 246" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Registering from the standard catalogue">
 <rect width="880" height="246" fill="#fff"/>
 <text x="20" y="26" font-family="Manrope" font-weight="800" font-size="14">Why you pick from the catalogue instead of typing a name</text>
 <rect x="20" y="42" width="400" height="94" rx="12" fill="#FDECEA" stroke="#D8332A" stroke-width="2"/>
 <text x="40" y="66" font-family="Manrope" font-weight="800" font-size="12.5" fill="#D8332A">Typing names — four products, one medicine</text>
 <g font-family="Inter" font-size="12" fill="#3B3D45">
  <text x="40" y="88">"Paracetamol 500mg" &nbsp; "paracetamol 500 mg"</text>
  <text x="40" y="106">"PCM 500" &nbsp; "Panadol 500mg"</text>
  <text x="40" y="126" font-size="11" fill="#6B6E78">Reports can never add these together.</text>
 </g>
 <rect x="460" y="42" width="400" height="94" rx="12" fill="#E9F7EF" stroke="#1F9D55" stroke-width="2"/>
 <text x="480" y="66" font-family="Manrope" font-weight="800" font-size="12.5" fill="#1F9D55">From the catalogue — one identity</text>
 <g font-family="Inter" font-size="12" fill="#3B3D45">
  <text x="480" y="88">Paracetamol 500mg Tablet</text>
  <text x="480" y="106" font-size="11" fill="#6B6E78">ATC N02BE01 · Oral · Over the counter</text>
  <text x="480" y="126" font-size="11" fill="#6B6E78">Everyone's figures line up.</text>
 </g>
 <text x="20" y="168" font-family="Manrope" font-weight="800" font-size="13">What comes from where</text>
 <rect x="20" y="180" width="400" height="54" rx="10" fill="#F7F8FA" stroke="#DFE1E6"/>
 <text x="40" y="202" font-family="Inter" font-size="12" font-weight="700">The catalogue gives you</text>
 <text x="40" y="222" font-family="Inter" font-size="11.5" fill="#3B3D45">Name · strength · form · legal class · ATC code</text>
 <rect x="460" y="180" width="400" height="54" rx="10" fill="#FCEDCB" stroke="#F1AB15"/>
 <text x="480" y="202" font-family="Inter" font-size="12" font-weight="700">You set</text>
 <text x="480" y="222" font-family="Inter" font-size="11.5" fill="#3B3D45">Your category · prices · opening stock · reorder level</text>
</svg>
</div>"""


def svg_ledger():
    return """
<div class="figure">
<svg viewBox="0 0 880 250" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="The stock ledger">
 <rect width="880" height="250" fill="#fff"/>
 <text x="20" y="26" font-family="Manrope" font-weight="800" font-size="14">Where did those packs go? The ledger answers it</text>
 <rect x="20" y="40" width="840" height="196" rx="12" fill="#fff" stroke="#DFE1E6"/>
 <line x1="36" y1="66" x2="844" y2="66" stroke="#DFE1E6"/>
 <g font-family="Inter" font-size="10.5" fill="#6B6E78">
  <text x="40" y="60">DATE</text><text x="150" y="60">CAUSE</text><text x="380" y="60">CHANGE</text>
  <text x="500" y="60">BALANCE</text><text x="680" y="60">REFERENCE</text>
 </g>
 <g font-family="Inter" font-size="12">
  <text x="40" y="92" fill="#6B6E78">10 Sep 09:14</text><text x="150" y="92">Purchase received</text>
  <rect x="380" y="80" width="52" height="17" rx="4" fill="#E9F7EF"/><text x="406" y="93" font-size="11" fill="#1F9D55" text-anchor="middle" font-weight="700">+100</text>
  <text x="500" y="92" fill="#6B6E78">500 → <tspan fill="#0B0B0C" font-weight="700">600</tspan></text>
  <text x="680" y="92" fill="#6B6E78">PUR-000001</text>

  <text x="40" y="120" fill="#6B6E78">10 Sep 10:02</text><text x="150" y="120">Sale</text>
  <rect x="380" y="108" width="52" height="17" rx="4" fill="#FDECEA"/><text x="406" y="121" font-size="11" fill="#D8332A" text-anchor="middle" font-weight="700">−30</text>
  <text x="500" y="120" fill="#6B6E78">600 → <tspan fill="#0B0B0C" font-weight="700">570</tspan></text>
  <text x="680" y="120" fill="#6B6E78">INV-000001</text>

  <text x="40" y="148" fill="#6B6E78">10 Sep 11:30</text><text x="150" y="148">Stock out (breakage)</text>
  <rect x="380" y="136" width="52" height="17" rx="4" fill="#FDECEA"/><text x="406" y="149" font-size="11" fill="#D8332A" text-anchor="middle" font-weight="700">−5</text>
  <text x="500" y="148" fill="#6B6E78">570 → <tspan fill="#0B0B0C" font-weight="700">565</tspan></text>

  <text x="40" y="176" fill="#6B6E78">10 Sep 14:05</text><text x="150" y="176">Transfer out → Bole</text>
  <rect x="380" y="164" width="52" height="17" rx="4" fill="#FDECEA"/><text x="406" y="177" font-size="11" fill="#D8332A" text-anchor="middle" font-weight="700">−40</text>
  <text x="500" y="176" fill="#6B6E78">565 → <tspan fill="#0B0B0C" font-weight="700">525</tspan></text>
  <text x="680" y="176" fill="#6B6E78">→ BR-002</text>

  <text x="40" y="204" fill="#6B6E78">10 Sep 16:20</text><text x="150" y="204">Sale voided</text>
  <rect x="380" y="192" width="52" height="17" rx="4" fill="#E9F7EF"/><text x="406" y="205" font-size="11" fill="#1F9D55" text-anchor="middle" font-weight="700">+30</text>
  <text x="500" y="204" fill="#6B6E78">525 → <tspan fill="#0B0B0C" font-weight="700">555</tspan></text>
  <text x="680" y="204" fill="#6B6E78">INV-000001</text>
 </g>
 <text x="40" y="228" font-family="Inter" font-size="11" fill="#6B6E78">Nothing can change stock without appearing here. Entries are never edited or deleted.</text>
</svg>
</div>"""

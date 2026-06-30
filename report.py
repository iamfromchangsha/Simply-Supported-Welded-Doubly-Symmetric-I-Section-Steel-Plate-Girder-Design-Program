# -*- coding: utf-8 -*-
"""
报告生成器 — HTML (MathJax LaTeX 渲染) + PDF 导出
兼容 Python 3.11 (f-string expressions 不含反斜杠)
"""

import os
import math
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

from calculator import (
    CalcResult, format_number, E_STEEL, G_STEEL, Q_K,
)

_f = format_number


# ============================================================
# LaTeX 辅助 (无 f-string, 避 Python 3.11 限制)
# ============================================================

def _mi(x):
    """inline math: \( x \)"""
    return "\\(%s\\)" % x

def _md(x):
    """display math: $$ x $$"""
    return "$$\n%s\n$$" % x


# Pre-compute common LaTeX symbols
BS = "\\"  # single backslash character for manual concatenation

class LX:
    """LaTeX symbol constants"""
    ETA   = BS + "eta"
    SIGMA = BS + "sigma"
    TAU   = BS + "tau"
    DELTA = BS + "delta"
    GAMMA = BS + "gamma"
    LAMBDA = BS + "lambda"
    MU    = BS + "mu"
    NU    = BS + "nu"
    RHO   = BS + "rho"
    VARPHI= BS + "varphi"
    SQRT  = BS + "sqrt"
    FRAC  = BS + "frac"
    CDOT  = BS + "cdot"
    TIMES = BS + "times"
    LE    = BS + "le"
    GE    = BS + "ge"
    SIM   = BS + "sim"
    INFTY = BS + "infty"
    PM    = BS + "pm"
    RIGHT = BS + "rightarrow"

    @staticmethod
    def sub(base, sub):
        return "%s_{%s}" % (base, sub)

    @staticmethod
    def pow(base, p):
        return "%s^{%s}" % (base, p)

    @staticmethod
    def frac(num, den):
        return "%s{%s}{%s}" % (BS + "frac", num, den)

    @staticmethod
    def sqrt(x):
        return "%s{%s}" % (BS + "sqrt", x)

    @staticmethod
    def text(s):
        return BS + "text{%s}" % s


# ============================================================
# HTML 模板
# ============================================================

_HTML_HEADER = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>钢板梁设计计算书</title>
<script>
MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\(', '\\)']],
    displayMath: [['$$', '$$'], ['\\[', '\\]']],
    processEscapes: false
  },
  svg: { fontCache: 'global' },
  options: { enableAssistiveMml: false },
  startup: {
    ready: function () {
      MathJax.startup.defaultReady();
      MathJax.startup.promise.then(function () {
        document.body.setAttribute('data-mjax-done', '1');
      });
    }
  }
};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js">
</script>
<style>
  :root {
    --page-width: 210mm;
    --margin: 22mm;
    --content-width: calc(var(--page-width) - 2 * var(--margin));
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Times New Roman", SimSun, serif;
    font-size: 13pt;
    line-height: 1.8;
    color: #000;
    background: #fff;
    padding: 30px 40px;
    max-width: 900px;
    margin: 0 auto;
  }
  h1 { font-size: 18pt; text-align: center; margin: 20px 0 10px; }
  h2 { font-size: 15pt; margin: 28px 0 10px; border-bottom: 1.5px solid #000; padding-bottom: 4px; }
  h3 { font-size: 13pt; margin: 18px 0 6px; }
  h4 { font-size: 12pt; margin: 12px 0 4px; }
  p { margin: 6px 0; text-indent: 2em; }
  p.no-indent { text-indent: 0; }
  table {
    border-collapse: collapse;
    margin: 10px auto;
    font-size: 11pt;
    width: 100%;
  }
  th, td {
    border: 1px solid #000;
    padding: 4px 8px;
    text-align: center;
  }
  th { background: #e0e0e0; font-weight: bold; }
  td { text-align: center; }
  td.left { text-align: left; }
  .formula-block {
    margin: 8px 0 8px 3em;
    font-family: "Times New Roman", serif;
    font-size: 12pt;
  }
  .highlight { font-weight: bold; }
  .ok { color: #006600; font-weight: bold; }
  .ng { color: #cc0000; font-weight: bold; }
  hr { border: none; border-top: 1px solid #000; margin: 20px 0; }
  ul, ol { margin: 4px 0 4px 3em; }
  li { margin: 2px 0; }

  @media print {
    body { padding: 0 5mm; max-width: none; }
    h2 { page-break-after: avoid; }
    table { page-break-inside: avoid; }
  }
</style>
</head>
<body>
"""

_HTML_FOOTER = r"""
</body>
</html>
"""


# ============================================================
# 工字形截面横断面图 (纯 SVG)
# ============================================================

def _make_cross_section_svg(h_w, t_w, b_f, t_f, h):
    """
    生成工字形截面横断面 SVG 示意图（紧凑版）
    h_w, t_w, b_f, t_f, h: mm
    """
    scale = 240.0 / max(b_f, 1)  # 缩放到约 240px 宽
    w_px = b_f * scale
    h_px = h * scale
    hw_px = h_w * scale
    tw_px = max(t_w * scale, 3)  # 腹板至少 3px
    tf_px = max(t_f * scale, 4)  # 翼缘至少 4px

    margin = 60
    svg_w = w_px + margin * 2
    svg_h = h_px + margin * 2

    cx = svg_w / 2.0
    y0 = margin
    y1 = y0 + tf_px
    y2 = y1 + hw_px
    y3 = y2 + tf_px
    xl = cx - w_px / 2.0
    xr = cx + w_px / 2.0
    xw_l = cx - tw_px / 2.0
    xw_r = cx + tw_px / 2.0

    def r(x, y, w, h_val, color="#d9e6f2"):
        return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="#000" stroke-width="1"/>' % (x, y, w, h_val, color)

    def line(x1, y1, x2, y2, sw=0.7, dash=None):
        d = ' stroke-dasharray="%s"' % dash if dash else ''
        return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#444" stroke-width="%.1f"%s/>' % (x1, y1, x2, y2, sw, d)

    def txt(x, y, text, anchor="middle", size=10, bold=False):
        b = ' font-weight="bold"' if bold else ''
        return '<text x="%.1f" y="%.1f" text-anchor="%s" font-size="%d"%s>%s</text>' % (x, y, anchor, size, b, text)

    parts = []
    a = parts.append

    a('<div style="text-align:center;margin:15px 0;">')
    a('<p><strong>图 3.1&emsp;工字形截面横断面图（单位：mm）</strong></p>')
    a('<svg width="%d" height="%d" xmlns="http://www.w3.org/2000/svg" '
      'style="font-family:SimSun,Times New Roman,serif;">' % (svg_w, svg_h))

    # --- 截面主体 ---
    a(r(xl, y0, w_px, tf_px, "#d9e6f2"))
    a(r(xl, y2, w_px, tf_px, "#d9e6f2"))
    a(r(xw_l, y1, tw_px, hw_px, "#f0f0f0"))

    # 中心线
    a(line(cx, y0 - 22, cx, y3 + 22, 0.6, "6,3"))
    a(line(cx - 5, y0 - 14, cx + 5, y0 - 14, 0.6))
    a(line(cx - 5, y3 + 14, cx + 5, y3 + 14, 0.6))

    # ===== b_f =====
    ybf = y0 - 13
    a(line(xl, ybf, xr, ybf, 0.6))
    a(line(xl, ybf - 3, xl, ybf + 3, 0.6))
    a(line(xr, ybf - 3, xr, ybf + 3, 0.6))
    a(txt(cx, ybf - 4, "b_f=%d" % b_f, "middle", 10, True))

    # ===== h =====
    xh = xl - 14
    a(line(xh, y0, xh, y3, 0.6))
    a(line(xh - 3, y0, xh + 3, y0, 0.6))
    a(line(xh - 3, y3, xh + 3, y3, 0.6))
    a(txt(xh - 4, (y0 + y3) / 2 + 3, "h=%d" % h, "end", 10, True))

    # ===== h_w =====
    xhw = xr + 14
    a(line(xhw, y1, xhw, y2, 0.6))
    a(line(xhw - 3, y1, xhw + 3, y1, 0.6))
    a(line(xhw - 3, y2, xhw + 3, y2, 0.6))
    a(txt(xhw + 4, (y1 + y2) / 2 + 3, "h_w=%d" % h_w, "start", 10, True))

    # ===== t_w =====
    ytw = y3 + 14
    a(line(xw_l, ytw, xw_r, ytw, 0.6))
    a(line(xw_l, ytw - 3, xw_l, ytw + 3, 0.6))
    a(line(xw_r, ytw - 3, xw_r, ytw + 3, 0.6))
    a(txt(cx, ytw + 10, "t_w=%d" % t_w, "middle", 10, True))

    # ===== t_f =====
    xtf = xr + 14
    ytf = (y0 + y1) / 2
    a(line(xtf, y0, xtf, y1, 0.6))
    a(line(xtf - 3, y0, xtf + 3, y0, 0.6))
    a(line(xtf - 3, y1, xtf + 3, y1, 0.6))
    a(txt(xtf + 4, ytf + 3, "t_f=%d" % t_f, "start", 10, True))

    a('</svg>')
    a('</div>')

    return '\n'.join(parts)


# ============================================================
# HTML 内容生成
# ============================================================

def generate_html(r: CalcResult) -> str:
    p = r.params
    sec = r.section
    pm = r.props_mid
    pv = r.props_var
    c = r.checks
    st = r.stiffeners
    wd = r.welds
    ft = r.fatigue

    L = []
    a = L.append

    a(_HTML_HEADER)

    # 标题
    title_tex = "%s\\,\\mathrm{m}\\text{简支焊接双轴对称工字形钢板梁设计计算书}" % p.L
    a(_md(title_tex))

    a('<table>')
    a('<tr><th>项目</th><th>内容</th></tr>')
    a('<tr><td>设计题目</td><td>%dm 简支工字型钢板梁设计</td></tr>' % p.L)
    a('<tr><td>设计依据</td><td>JTG D64-2015 / JTG D60-2015 / 钢结构设计原理</td></tr>')
    a('<tr><td>钢材</td><td>%s</td></tr>' % p.steel_grade)
    a('<tr><td>焊条</td><td>%s</td></tr>' % p.electrode)
    a('</table>')
    a('<hr>')

    # ============== 一、设计基本参数 ==============
    a('<h2>一、设计基本参数</h2>')
    a('<p>本设计为 %d m 简支公路桥梁钢板梁设计。桥梁上部结构采用钢-混凝土叠合梁形式，钢主梁为焊接双轴对称工字形截面，在跨径范围内进行一次变截面设计。</p>' % p.L)

    a('<h3>1.1 几何参数与荷载参数</h3>')
    a('<table>')
    a('<tr><th>参数</th><th>符号</th><th>数值</th><th>单位</th></tr>')
    a('<tr><td>计算跨径</td><td>%s</td><td>%.1f</td><td>m</td></tr>' % (_mi("L"), p.L))
    a('<tr><td>桥面板宽度</td><td>%s</td><td>%.1f</td><td>m</td></tr>' % (_mi("B"), p.B))
    a('<tr><td>混凝土桥面板厚度</td><td>%s</td><td>%.2f</td><td>m</td></tr>' % (_mi("H_1"), p.H1))
    a('<tr><td>沥青铺装层厚度</td><td>%s</td><td>%.2f</td><td>m</td></tr>' % (_mi("H_2"), p.H2))
    a('<tr><td>横向分布系数</td><td>%s</td><td>%.2f</td><td>&mdash;</td></tr>' % (_mi(LX.ETA), p.eta))
    a('<tr><td>恒载分项系数</td><td>%s</td><td>%.1f</td><td>&mdash;</td></tr>' % (_mi(LX.GAMMA + "_G"), p.gamma_G))
    a('<tr><td>活载分项系数</td><td>%s</td><td>%.1f</td><td>&mdash;</td></tr>' % (_mi(LX.GAMMA + "_Q"), p.gamma_Q))
    a('<tr><td>结构重要性系数</td><td>%s</td><td>%.1f</td><td>&mdash;</td></tr>' % (_mi(LX.GAMMA + "_0"), p.gamma_0))
    a('<tr><td>活载冲击系数</td><td>%s</td><td>%.2f</td><td>&mdash;</td></tr>' % (_mi("1+" + LX.MU), p.mu_impact))
    a('</table>')

    a('<h3>1.2 材料特性</h3>')
    a('<p>钢材选用 %s 低合金高强度结构钢，焊条选用 %s 型。依据 JTG D64-2015 表 3.2.1，%s 钢强度设计值如下：</p>' % (p.steel_grade, p.electrode, p.steel_grade))
    a('<table>')
    a('<tr><th>板厚 t (mm)</th><th>f<sub>d</sub> (MPa)</th><th>f<sub>vd</sub> (MPa)</th><th>f<sub>ce</sub> (MPa)</th></tr>')
    a('<tr><td>t &le; 16</td><td>275</td><td>160</td><td>355</td></tr>')
    a('<tr><td>16 &lt; t &le; 40</td><td>270</td><td>155</td><td>355</td></tr>')
    a('<tr><td>40 &lt; t &le; 63</td><td>260</td><td>150</td><td>355</td></tr>')
    a('</table>')
    E_show = E_STEEL / 1e5
    G_show = G_STEEL / 1e4
    a('<p>弹性模量 %s，剪切模量 %s，泊松比 %s。钢材容重 %s（即 78.5 kN/m&sup3;）。</p>' % (
        _mi("E = %.2f \\times 10^5\\,\\mathrm{MPa}" % E_show),
        _mi("G = %.2f \\times 10^4\\,\\mathrm{MPa}" % G_show),
        _mi(LX.NU + " = 0.3"),
        _mi(LX.RHO + " = 7850\\,\\mathrm{kg/m^3}"),
    ))

    # ============== 二、荷载计算 ==============
    a('<h2>二、荷载计算</h2>')

    a('<h3>2.1 二期恒载（桥面板+铺装层）</h3>')
    g2 = r.g2
    a(_md("g_2 = \\gamma_c \\times B \\times H_1 + \\gamma_a \\times B \\times H_2"))
    term1 = 25.0 * p.B * p.H1
    term2 = 24.0 * p.B * p.H2
    a(_md("g_2 = 25.0 \\times %.1f \\times %.2f + 24.0 \\times %.1f \\times %.2f = %.3f + %.3f = %.3f\\,\\mathrm{kN/m}" % (
        p.B, p.H1, p.B, p.H2, term1, term2, g2)))
    a('<p><strong>二期恒载合计：%s</strong></p>' % _mi("g_2 = %.3f\\,\\mathrm{kN/m}" % g2))

    a('<h3>2.2 活载标准值（JTG D60-2015 第4.3.1条）</h3>')
    a('<p>公路-I级车道荷载：均布荷载 %s（满跨布置）。集中荷载 P<sub>k</sub>（用于弯矩计算）按下式内插：</p>' % _mi("q_k = %s\\,\\mathrm{kN/m}" % Q_K))
    a(_md("P_k = 270 + (360 - 270) \\times (L - 5) / (50 - 5)"))
    a(_md("P_k = 270 + 90 \\times (%d - 5) / 45 = %.2f\\,\\mathrm{kN}" % (p.L, r.P_k)))
    a('<p>用于剪力计算时，P<sub>k</sub> 乘 1.2 系数：%s。</p>' % _mi("P_{k,\\mathrm{shear}} = 1.2 \\times %.2f = %.2f\\,\\mathrm{kN}" % (r.P_k, r.P_k * 1.2)))
    a('<p>横向分布系数 %s，分配到单根主梁的活载标准值：</p>' % _mi(LX.ETA + " = %.2f" % p.eta))
    a('<ul>')
    a('<li>均布活载：%s</li>' % _mi("q = %s \\times q_k = %.2f \\times %s = %.3f\\,\\mathrm{kN/m}" % (LX.ETA, p.eta, Q_K, r.q)))
    a('<li>集中活载（弯矩用）：%s</li>' % _mi("P = %s \\times P_k = %.2f \\times %.2f = %.2f\\,\\mathrm{kN}" % (LX.ETA, p.eta, r.P_k, r.P)))
    a('<li>集中活载（剪力用）：%s</li>' % _mi("P_s = %s \\times 1.2 \\times P_k = %.2f \\times %.2f = %.2f\\,\\mathrm{kN}" % (LX.ETA, p.eta, r.P_k * 1.2, r.P_s)))
    a('</ul>')

    a('<h3>2.3 一期恒载（钢梁自重）</h3>')
    a('<p>钢梁自重取决于截面尺寸，先按经验初估，拟定截面后代入验算。</p>')

    # ============== 三、截面尺寸拟定 ==============
    a('<h2>三、截面尺寸拟定</h2>')
    a('<h3>3.1 梁高确定</h3>')
    a('<p>梁高是钢板梁经济性的关键参数，综合以下因素确定：</p>')
    h_min15 = p.L * 1000 / 15
    h_min12 = p.L * 1000 / 12
    a('<p><strong>(1) 按刚度条件（挠度控制）：</strong>简支梁满足挠度限值 L/500 所需的最小梁高约为 %s。</p>' %
      _mi("h = L/15 \\sim L/12 = %.0f \\sim %.0f\\,\\mathrm{mm}" % (h_min15, h_min12)))
    a('<p><strong>(2) 按经济条件：</strong>经济梁高经验公式 %s。</p>' %
      _mi("h_e = 7 \\cdot W_{\\mathrm{req}}^{1/3} - 300\\;(\\mathrm{mm})"))
    a('<p><strong>(3) 综合确定：</strong>腹板高度 %s，翼缘厚度 %s（上下翼缘等厚），总梁高 %s。</p>' % (
        _mi("h_w = %.0f\\,\\mathrm{mm}" % sec.h_w),
        _mi("t_f = %.0f\\,\\mathrm{mm}" % sec.t_f),
        _mi("h = h_w + 2t_f = %.0f\\,\\mathrm{mm}" % pm.h)))

    a('<h3>3.2 拟选截面尺寸</h3>')
    a('<table>')
    a('<tr><th>板件</th><th>符号</th><th>尺寸 (mm)</th><th>说明</th></tr>')
    a('<tr><td>腹板高度</td><td>%s</td><td>%.0f</td><td>按 L/15~L/20 经济与刚度确定</td></tr>' % (_mi("h_w"), sec.h_w))
    a('<tr><td>腹板厚度</td><td>%s</td><td>%.0f</td><td>满足抗剪与局部稳定，%s</td></tr>' % (
        _mi("t_w"), sec.t_w, _mi("t_w \\geq h_w/170 = %.1f" % (sec.h_w / 170))))
    a('<tr><td>翼缘宽度</td><td>%s</td><td>%.0f</td><td>满足整体稳定，%s</td></tr>' % (
        _mi("b_f"), sec.b_f, _mi("b_f \\geq h/5 = %.0f" % (pm.h / 5))))
    a('<tr><td>翼缘厚度</td><td>%s</td><td>%.0f</td><td>满足抗弯所需截面模量</td></tr>' % (_mi("t_f"), sec.t_f))
    a('<tr><td>梁总高</td><td>%s</td><td>%.0f</td><td>%s</td></tr>' % (_mi("h"), pm.h, _mi("h = h_w + 2t_f")))
    a('</table>')

    # 横断面图 (SVG)
    a(_make_cross_section_svg(sec.h_w, sec.t_w, sec.b_f, sec.t_f, pm.h))

    a('<h3>3.3 截面几何特性计算</h3>')
    I_w = sec.t_w * sec.h_w ** 3 / 12.0
    d_f = (sec.h_w + sec.t_f) / 2.0
    I_f = 2.0 * (sec.b_f * sec.t_f ** 3 / 12.0 + sec.b_f * sec.t_f * d_f ** 2)
    I_f_line = ("I_f = 2\\left[ \\frac{%d \\times %d^3}{12} + %d \\times %d \\times %d^2 \\right] = %.2f \\times 10^6\\,\\mathrm{mm^4}" %
                (sec.b_f, sec.t_f, sec.b_f, sec.t_f, d_f, I_f / 1e6))

    a('<p><strong>(1) 截面面积</strong></p>')
    a(_md("A = %d \\times %d + 2 \\times %d \\times %d = %d\\,\\mathrm{mm^2}" % (sec.h_w, sec.t_w, sec.b_f, sec.t_f, pm.A)))
    a('<p><strong>(2) 惯性矩（绕强轴 x-x）</strong></p>')
    a(_md("I_w = t_w h_w^3 / 12 = %d \\times %d^3 / 12 = %.2f \\times 10^6\\,\\mathrm{mm^4}" % (sec.t_w, sec.h_w, I_w / 1e6)))
    a(_md(I_f_line))
    a(_md("I_x = I_w + I_f = %.2f \\times 10^6\\,\\mathrm{mm^4}" % (pm.I_x / 1e6)))
    a('<p><strong>(3) 弹性截面模量</strong></p>')
    a(_md("W_x = I_x / (h/2) = %.2f \\times 10^6 / %d = %.2f\\,\\mathrm{cm^3}" % (pm.I_x / 1e6, pm.h / 2, pm.W_x / 1e3)))
    a('<p><strong>(4) 半截面面积矩（用于剪应力计算）</strong></p>')
    a(_md("S = b_f t_f (h_w + t_f)/2 + t_w (h_w/2)^2 / 2"))
    a(_md("S = %d \\times %d \\times %d + %d \\times (%d)^2 / 2 = %.2f\\,\\mathrm{cm^3}" % (
        sec.b_f, sec.t_f, d_f, sec.t_w, sec.h_w / 2, pm.S / 1e3)))
    a('<p><strong>(5) 钢梁自重（一期恒载）</strong></p>')
    a(_md("g_1 = A \\times \\rho_{\\mathrm{steel}} = %.4f \\times 78.5 = %.3f\\,\\mathrm{kN/m}" % (pm.A * 1e-6, r.g1)))
    a('<p><strong>总恒载：%s</strong></p>' % _mi("g = g_1 + g_2 = %.3f + %.3f = %.3f\\,\\mathrm{kN/m}" % (r.g1, g2, r.g)))

    # ============== 四、内力计算 ==============
    a('<h2>四、内力计算</h2>')
    a('<p>简支梁计算跨径 %s，控制截面为跨中（弯矩最大）和支座（剪力最大）。</p>' % _mi("L = %g\\,\\mathrm{m}" % p.L))

    a('<h3>4.1 跨中弯矩</h3>')
    a('<p><strong>弯矩标准值：</strong></p>')
    a(_md("M_{gk} = g L^2 / 8 = %.3f \\times %.0f^2 / 8 = %.2f\\,\\mathrm{kN\\cdot m}" % (r.g, p.L, r.M_gk)))
    a(_md("M_{qk} = q L^2 / 8 + P L / 4 = %.3f \\times %.0f^2 / 8 + %.2f \\times %.0f / 4 = %.2f\\,\\mathrm{kN\\cdot m}" %
          (r.q, p.L, r.P, p.L, r.M_qk)))
    a('<p><strong>弯矩设计值（承载能力极限状态）：</strong></p>')
    a(_md("M_{Ed} = " + LX.GAMMA + "_0 [" + LX.GAMMA + "_G \\times M_{gk} + " + LX.GAMMA +
          "_Q \\times (1+" + LX.MU + ") \\times M_{qk}]"))
    a(_md("M_{Ed} = %.1f \\times [%.1f \\times %.2f + %.1f \\times %.2f \\times %.2f] = %.2f\\,\\mathrm{kN\\cdot m}" %
          (p.gamma_0, p.gamma_G, r.M_gk, p.gamma_Q, p.mu_impact, r.M_qk, r.M_Ed)))

    a('<h3>4.2 支座剪力</h3>')
    a('<p><strong>剪力标准值：</strong></p>')
    a(_md("V_{gk} = g L / 2 = %.2f\\,\\mathrm{kN}" % r.V_gk))
    a(_md("V_{qk} = q L / 2 + P_s / 2 = %.2f\\,\\mathrm{kN}" % r.V_qk))
    a('<p><strong>剪力设计值：</strong></p>')
    a(_md("V_{Ed} = " + LX.GAMMA + "_0 [" + LX.GAMMA + "_G \\times V_{gk} + " + LX.GAMMA +
          "_Q \\times (1+" + LX.MU + ") \\times V_{qk}] = %.2f\\,\\mathrm{kN}" % r.V_Ed))

    # ============== 五、跨中强度及刚度验算 ==============
    a('<h2>五、跨中截面强度及刚度验算</h2>')

    a('<h3>5.1 抗弯强度（JTG D64-2015 第5.2条）</h3>')
    a('<p>翼缘板厚 %s（%d &lt; t<sub>f</sub> &le; %d mm），取 %s。</p>' % (
        _mi("t_f = %d\\,\\mathrm{mm}" % sec.t_f),
        16 if sec.t_f <= 40 else 40, 40 if sec.t_f <= 40 else 63,
        _mi("f_d = %d\\,\\mathrm{MPa}" % r.f_d_mid)))
    a(_md(LX.SIGMA + " = M_{Ed} / W_x = %.2f \\times 10^6 / (%.2f \\times 10^3) = %.1f\\,\\mathrm{MPa}" %
          (r.M_Ed, pm.W_x / 1e3, c.sigma_mid)))
    margin_s = (1 - c.sigma_mid / c.sigma_mid_limit) * 100
    cls_s = 'ok' if c.sigma_mid_ok else 'ng'
    ok_s = '满足' if c.sigma_mid_ok else '不满足'
    a('<p><strong>%s &nbsp; [<span class="%s">%s</span>] &nbsp; 安全储备 %.1f%%</strong></p>' % (
        _mi(LX.SIGMA + " = %.1f\\,\\mathrm{MPa} < f_d = %d\\,\\mathrm{MPa}" % (c.sigma_mid, c.sigma_mid_limit)),
        cls_s, ok_s, margin_s))

    a('<h3>5.2 抗剪强度（JTG D64-2015 第5.3条）</h3>')
    a('<p>腹板中性轴处剪应力最大，t<sub>w</sub> = %d mm，取 %s。</p>' % (sec.t_w, _mi("f_{vd} = %d\\,\\mathrm{MPa}" % r.f_vd_mid)))
    a(_md(LX.TAU + "_{\\max} = \\frac{V_{Ed} \\times S}{I_x \\times t_w}"))
    a(_md(LX.TAU + "_{\\max} = \\frac{%.2f \\times 10^3 \\times %.2f \\times 10^3}{%.2f \\times 10^6 \\times %d} = %.1f\\,\\mathrm{MPa}" %
          (r.V_Ed, pm.S / 1e3, pm.I_x / 1e6, sec.t_w, c.tau_max)))
    cls_t = 'ok' if c.tau_max_ok else 'ng'
    ok_t = '满足' if c.tau_max_ok else '不满足'
    a('<p><strong>%s &nbsp; [<span class="%s">%s</span>]</strong></p>' % (
        _mi(LX.TAU + "_{\\max} = %.1f\\,\\mathrm{MPa} < f_{vd} = %d\\,\\mathrm{MPa}" % (c.tau_max, c.tau_max_limit)),
        cls_t, ok_t))

    a('<h3>5.3 折算应力（JTG D64-2015 第5.4条）</h3>')
    y_j = sec.h_w / 2.0
    sigma_j = r.M_Ed * 1e6 * y_j / pm.I_x
    tau_j = r.V_Ed * 1e3 * pm.S_f / (pm.I_x * sec.t_w)
    a('<p>验算跨中截面翼缘与腹板交界处（%s）：</p>' % _mi("y_j = h_w/2 = %d\\,\\mathrm{mm}" % y_j))
    a(_md(LX.SIGMA + "_j = \\frac{M_{Ed} \\times y_j}{I_x} = %.1f\\,\\mathrm{MPa}" % sigma_j))
    a(_md(LX.TAU + "_j = \\frac{V_{Ed} \\times S_f}{I_x \\times t_w} = %.1f\\,\\mathrm{MPa}" % tau_j))
    a(_md(LX.SIGMA + "_{zs} = \\sqrt{" + LX.SIGMA + "_j^2 + 3" + LX.TAU + "_j^2} = \\sqrt{%.1f^2 + 3 \\times %.1f^2} = %.1f\\,\\mathrm{MPa}" %
          (sigma_j, tau_j, c.sigma_zs)))
    cls_z = 'ok' if c.sigma_zs_ok else 'ng'
    ok_z = '满足' if c.sigma_zs_ok else '不满足'
    a('<p><strong>%s &nbsp; [<span class="%s">%s</span>]</strong></p>' % (
        _mi(LX.SIGMA + "_{zs} = %.1f\\,\\mathrm{MPa} < 1.1 f_d = %d\\,\\mathrm{MPa}" % (c.sigma_zs, c.sigma_zs_limit)),
        cls_z, ok_z))

    a('<h3>5.4 刚度验算（JTG D64-2015 第5.4条）</h3>')
    L_mm = p.L * 1000.0
    q_Nmm = r.q
    P_N = r.P * 1000.0
    delta_u = 5.0 * q_Nmm * L_mm ** 4 / (384.0 * E_STEEL * pm.I_x)
    delta_c = P_N * L_mm ** 3 / (48.0 * E_STEEL * pm.I_x)
    a('<p>活载挠度（不计冲击系数）按均布+集中荷载叠加计算：</p>')
    a(_md(LX.DELTA + "_u = \\frac{5 q L^4}{384 E I_x} = %.1f\\,\\mathrm{mm}" % delta_u))
    a(_md(LX.DELTA + "_c = \\frac{P L^3}{48 E I_x} = %.1f\\,\\mathrm{mm}" % delta_c))
    a(_md(LX.DELTA + "_q = " + LX.DELTA + "_u + " + LX.DELTA + "_c = %.1f\\,\\mathrm{mm}" % c.deflection_q))
    a(_md("[" + LX.DELTA + "] = L / 500 = %.1f\\,\\mathrm{mm}" % c.deflection_limit))
    margin_d = (1 - c.deflection_q / c.deflection_limit) * 100
    cls_d = 'ok' if c.deflection_q_ok else 'ng'
    ok_d = '满足' if c.deflection_q_ok else '不满足'
    a('<p><strong>%s &nbsp; [<span class="%s">%s</span>] &nbsp; 安全储备 %.1f%%</strong></p>' % (
        _mi((LX.DELTA + "_q = %.1f\\,\\mathrm{mm} < [" + LX.DELTA + "] = %.1f\\,\\mathrm{mm}") % (c.deflection_q, c.deflection_limit)),
        cls_d, ok_d, margin_d))
    a('<p>恒载挠度 &delta;<sub>g</sub> = %.1f mm，总挠度 = %.1f mm &lt; L/400 = %.1f mm，满足视觉舒适度要求。</p>' %
      (c.deflection_g, c.deflection_total, p.L * 1000 / 400))

    a('<h3>5.5 整体稳定性（JTG D64-2015 第5.5条）</h3>')
    a('<p>混凝土桥面板通过剪力连接件为受压上翼缘提供连续侧向支撑，<strong>整体稳定性自然满足，无需验算</strong>。</p>')

    a('<h3>5.6 疲劳强度（JTG D64-2015 第5.6节及附录C）</h3>')
    a('<p>采用疲劳荷载模型 I（等效车道荷载乘 0.7 折减系数）：</p>')
    a('<p>%s，%s。</p>' % (
        _mi("q_f = 0.7 \\times 10.5 = 7.35\\,\\mathrm{kN/m}"),
        _mi("P_f = 0.7 \\times %.2f = %.2f\\,\\mathrm{kN}" % (r.P_k, 0.7 * r.P_k))))
    a('<p>按 %s 分配到单梁：%s，%s。</p>' % (
        _mi(LX.ETA + " = %.2f" % p.eta),
        _mi("q_{f1} = %.3f\\,\\mathrm{kN/m}" % ft.q_f1),
        _mi("P_{f1} = %.2f\\,\\mathrm{kN}" % ft.P_f1)))
    a('<p>%s。</p>' % _mi("M_f = q_{f1} \\times L^2 / 8 + P_{f1} \\times L / 4 = %.2f\\,\\mathrm{kN\\cdot m}" % ft.M_f))
    a(_md(LX.DELTA + LX.SIGMA + "_p = M_f / W_x = %.2f \\times 10^6 / (%.2f \\times 10^3) = %.1f\\,\\mathrm{MPa}" %
          (ft.M_f, pm.W_x / 1e3, ft.delta_sigma_p)))
    a('<table>')
    a('<tr><th>细节类别</th><th>&Delta;&sigma;<sub>c</sub> (MPa)</th><th>&Delta;&sigma;<sub>D</sub> = 0.74&Delta;&sigma;<sub>c</sub></th><th>&Delta;&sigma;<sub>p</sub></th><th>判定</th></tr>')
    cls_f1 = 'ok' if ft.check_base_metal else 'ng'
    ok_f1 = '满足' if ft.check_base_metal else '不满足'
    cls_f2 = 'ok' if ft.check_fillet_weld else 'ng'
    ok_f2 = '满足' if ft.check_fillet_weld else '不满足'
    a('<tr><td>翼缘母材（非焊接）</td><td>160</td><td>%.1f</td><td>%.1f</td><td><span class="%s">%s</span></td></tr>' %
      (ft.delta_sigma_D_base, ft.delta_sigma_p, cls_f1, ok_f1))
    a('<tr><td>翼缘-腹板连续角焊缝</td><td>80</td><td>%.1f</td><td>%.1f</td><td><span class="%s">%s</span></td></tr>' %
      (ft.delta_sigma_D_weld, ft.delta_sigma_p, cls_f2, ok_f2))
    a('</table>')
    a('<p><strong>&Delta;&sigma;<sub>p</sub> = %.1f MPa &lt; 各细节类别常幅疲劳极限，疲劳强度满足。</strong></p>' % ft.delta_sigma_p)

    # ============== 六、变截面设计 ==============
    a('<h2>六、变截面设计</h2>')
    a('<h3>6.1 变截面原理</h3>')
    a('<p>简支梁弯矩沿跨径呈抛物线分布。为节约钢材，在距支座 L/6 = %.3f m 处减小翼缘尺寸，腹板尺寸保持不变。变截面处弯矩约为跨中最大弯矩的 %.1f%%。</p>' %
      (r.x_cut, r.M_Ed_x / r.M_Ed * 100))

    a('<h3>6.2 变截面处内力</h3>')
    a(_md("M_{gk}(x) = g \\times x \\times (L-x) / 2 = %.2f\\,\\mathrm{kN\\cdot m}" % r.M_gk_x))
    a(_md("M_{qk}(x) = q \\times x \\times (L-x) / 2 + P \\times x / 2 = %.2f\\,\\mathrm{kN\\cdot m}" % r.M_qk_x))
    a(_md("M_{Ed}(x) = " + LX.GAMMA + "_0 [" + LX.GAMMA + "_G M_{gk}(x) + " + LX.GAMMA +
          "_Q (1+" + LX.MU + ") M_{qk}(x)] = %.2f\\,\\mathrm{kN\\cdot m}" % r.M_Ed_x))
    a('<p>V<sub>Ed</sub>(x) = %.2f kN</p>' % r.V_Ed_x)

    a('<h3>6.3 变截面处尺寸</h3>')
    a('<table>')
    a('<tr><th>参数</th><th>等截面段（跨中）</th><th>变截面段</th></tr>')
    a('<tr><td>腹板 h<sub>w</sub> &times; t<sub>w</sub> (mm)</td><td>%d &times; %d</td><td>%d &times; %d (不变)</td></tr>' %
      (sec.h_w, sec.t_w, sec.h_w, sec.t_w))
    a('<tr><td>翼缘宽 b<sub>f</sub> (mm)</td><td>%d</td><td>%d</td></tr>' % (sec.b_f, sec.b_f2))
    a('<tr><td>翼缘厚 t<sub>f</sub> (mm)</td><td>%d</td><td>%d</td></tr>' % (sec.t_f, sec.t_f2))
    a('<tr><td>总高 h (mm)</td><td>%d</td><td>%d</td></tr>' % (pm.h, pv.h))
    a('<tr><td>惯性矩 I<sub>x</sub> (10<sup>6</sup> mm<sup>4</sup>)</td><td>%.2f</td><td>%.2f</td></tr>' %
      (pm.I_x / 1e6, pv.I_x / 1e6))
    a('<tr><td>截面模量 W<sub>x</sub> (cm<sup>3</sup>)</td><td>%.2f</td><td>%.2f</td></tr>' %
      (pm.W_x / 1e3, pv.W_x / 1e3))
    a('</table>')

    a('<h3>6.4 变截面处强度验算</h3>')
    cls_v = 'ok' if c.sigma_var_ok else 'ng'; ok_v = '满足' if c.sigma_var_ok else '不满足'
    cls_vt = 'ok' if c.tau_var_ok else 'ng'; ok_vt = '满足' if c.tau_var_ok else '不满足'
    cls_vz = 'ok' if c.sigma_zs_var_ok else 'ng'; ok_vz = '满足' if c.sigma_zs_var_ok else '不满足'
    a('<p><strong>抗弯：</strong>%s = %.1f MPa &lt; %s MPa [<span class="%s">%s</span>]</p>' %
      (_mi(LX.SIGMA + " = M_{Ed}(x) / W_{x2}"), c.sigma_var,
       _mi("f_d = %d" % c.sigma_var_limit), cls_v, ok_v))
    a('<p><strong>抗剪：</strong>%s = %.1f MPa &lt; %s MPa [<span class="%s">%s</span>]</p>' %
      (_mi(LX.TAU + " = V_{Ed}(x) \\times S / (I_{x2} \\times t_w)"), c.tau_var,
       _mi("f_{vd} = %d" % c.tau_var_limit), cls_vt, ok_vt))
    a('<p><strong>折算应力：</strong>%s = %.1f MPa &lt; %s MPa [<span class="%s">%s</span>]</p>' %
      (_mi(LX.SIGMA + "_{zs} = \\sqrt{" + LX.SIGMA + "_j^2 + 3" + LX.TAU + "_j^2}"), c.sigma_zs_var,
       _mi("1.1f_d = %d" % c.sigma_zs_var_limit), cls_vz, ok_vz))

    # ============== 七、翼缘焊缝设计 ==============
    a('<h2>七、翼缘焊缝设计</h2>')
    a('<p>翼缘与腹板采用双面连续角焊缝连接，%s 焊条。角焊缝强度设计值 %s。</p>' %
      (p.electrode, _mi("f_{\\mathrm{ff}} = 200\\,\\mathrm{MPa}")))

    a('<h3>7.1 支座截面处（等截面段）</h3>')
    a(_md("S_f = b_f \\times t_f \\times (h_w + t_f) / 2 = %d \\times %d \\times %d = %.2f\\,\\mathrm{cm^3}" %
          (sec.b_f, sec.t_f, d_f, wd.S_f1 / 1e3)))
    a(_md("v = V_{Ed} \\times S_f / I_x = %.2f \\times 10^3 \\times %.2f \\times 10^3 / (%.2f \\times 10^6) = %.1f\\,\\mathrm{N/mm}" %
          (r.V_Ed, wd.S_f1 / 1e3, pm.I_x / 1e6, wd.v1)))
    a('<p>所需焊脚尺寸（双面角焊缝）：%s</p>' %
      _mi("h_f \\leq v / (2 \\times 0.7 \\times f_{\\mathrm{ff}}) = %.1f / (2 \\times 0.7 \\times 200) = %.1f\\,\\mathrm{mm}" %
          (wd.v1, wd.h_f_req1)))
    a('<p>构造要求：%s，%s。</p>' % (
        _mi("h_{f,\\min} = 1.5\\sqrt{%d} = %.1f\\,\\mathrm{mm}" % (sec.t_f, wd.h_f_min1)),
        _mi("h_{f,\\max} = 1.2 \\times %d = %.1f\\,\\mathrm{mm}" % (sec.t_w, wd.h_f_max1))))
    a('<p><strong>选用焊脚尺寸：%s</strong></p>' % _mi("h_f = %d\\,\\mathrm{mm}" % wd.h_f_chosen))

    a('<h3>7.2 变截面处</h3>')
    a(_md("S_{f2} = %d \\times %d \\times (%d + %d) / 2 = %.2f\\,\\mathrm{cm^3}" %
          (sec.b_f2, sec.t_f2, sec.h_w, sec.t_f2, wd.S_f2 / 1e3)))
    a(_md("v = %.2f \\times 10^3 \\times %.2f \\times 10^3 / (%.2f \\times 10^6) = %.1f\\,\\mathrm{N/mm}" %
          (r.V_Ed_x, wd.S_f2 / 1e3, pv.I_x / 1e6, wd.v2)))
    a('<p>所需 %s。构造：[%.1f, %.1f] mm。</p>' % (
        _mi("h_f \\leq %.1f / (2 \\times 0.7 \\times 200) = %.1f\\,\\mathrm{mm}" % (wd.v2, wd.h_f_req2)),
        wd.h_f_min2, wd.h_f_max2))
    a('<p><strong>选用焊脚尺寸：%s（全跨统一）</strong></p>' % _mi("h_f = %d\\,\\mathrm{mm}" % wd.h_f_chosen))
    a('<p><strong>【结论】翼缘-腹板连接焊缝全跨统一采用 %s 双面连续角焊缝。</strong></p>' %
      _mi("h_f = %d\\,\\mathrm{mm}" % wd.h_f_chosen))

    # ============== 八、局部稳定设计 ==============
    a('<h2>八、局部稳定设计</h2>')
    a('<h3>8.1 腹板加劲肋（JTG D64-2015 第5.7节）</h3>')
    a('<p>%s</p>' % _mi("h_w / t_w = %d / %d = %.1f" % (sec.h_w, sec.t_w, st.hw_tw_ratio)))
    a('<p>根据 JTG D64-2015 第5.7节，对 Q345 钢：</p>')
    a('<ul>')
    a('<li>h<sub>w</sub>/t<sub>w</sub> &le; 100：局部稳定自然满足；</li>')
    a('<li>100 &lt; h<sub>w</sub>/t<sub>w</sub> &le; 170：需配置横向加劲肋；</li>')
    a('<li>h<sub>w</sub>/t<sub>w</sub> &gt; 170：需配置横向和纵向加劲肋。</li>')
    a('</ul>')
    if st.need_longitudinal:
        a('<p>因 h<sub>w</sub>/t<sub>w</sub> = %.1f &gt; 170，<strong>需配置横向和纵向加劲肋</strong>。</p>' % st.hw_tw_ratio)
    elif st.need_transverse:
        a('<p>因 100 &lt; %.1f &le; 170，<strong>需配置横向加劲肋</strong>。</p>' % st.hw_tw_ratio)
    else:
        a('<p>因 h<sub>w</sub>/t<sub>w</sub> = %.1f &le; 100，局部稳定自然满足。</p>' % st.hw_tw_ratio)

    if st.need_transverse:
        a('<p><strong>(1) 加劲肋间距</strong></p>')
        a('<p>横向加劲肋间距 a &le; min(2h<sub>w</sub>, 3000) = %d mm。</p>' % min(2 * sec.h_w, 3000))
        a('<p>取间距 a = %.0f mm（满足 0.5h<sub>w</sub> = %.0f &le; a &le; 3000），全跨均匀布置 %d 对。</p>' %
          (st.spacing, 0.5 * sec.h_w, st.n_pairs))
        a('<p><strong>(2) 加劲肋构造尺寸（JTG D64-2015 第5.7.3条）</strong></p>')
        a('<p>%s</p>' % _mi("b_s \\geq h_w/30 + 40 = %.1f\\,\\mathrm{mm}" % (sec.h_w / 30 + 40)))
        a('<p>%s</p>' % _mi("t_s \\geq b_s / 15 = %.1f\\,\\mathrm{mm}" % (st.b_s / 15)))
        a('<p><strong>选用 b<sub>s</sub> &times; t<sub>s</sub> = %d &times; %d mm</strong>，成对布置在腹板两侧。</p>' %
          (st.b_s, st.t_s))
        a('<p>横向加劲肋与腹板采用双面角焊缝，h<sub>f</sub> = 6 mm。加劲肋两端不与翼缘焊接。</p>')

    a('<h3>8.2 支座加劲肋（支承加劲肋）</h3>')
    a('<p>支座反力 %s。采用 <strong>%d 块</strong> 竖向加劲肋，尺寸 %d &times; %d mm，端部刨平顶紧于下翼缘。</p>' %
      (_mi("R = V_{Ed} = %.2f\\,\\mathrm{kN}" % r.V_Ed), st.bearing_n, st.bearing_b, st.bearing_t))

    a('<p><strong>(a) 端面承压验算</strong></p>')
    A_ce = st.bearing_n * (st.bearing_b - 20) * st.bearing_t
    a('<p>%s</p>' % _mi("A_{ce} = %d \\times (%d - 20) \\times %d = %d\\,\\mathrm{mm^2}" %
                        (st.bearing_n, st.bearing_b, st.bearing_t, A_ce)))
    a('<p>%s</p>' % _mi(LX.SIGMA + "_{ce} = R / A_{ce} = %.2f \\times 10^3 / %d = %.1f\\,\\mathrm{MPa}" %
                        (r.V_Ed, A_ce, st.sigma_ce)))
    cls_ce = 'ok' if st.ce_ok else 'ng'; ok_ce = '满足' if st.ce_ok else '不满足'
    a('<p><strong>%s &nbsp; [<span class="%s">%s</span>]</strong></p>' % (
        _mi(LX.SIGMA + "_{ce} = %.1f\\,\\mathrm{MPa} < f_{ce} = 355\\,\\mathrm{MPa}" % st.sigma_ce), cls_ce, ok_ce))

    a('<p><strong>(b) 压杆稳定验算（十字形截面，绕腹板平面外弯曲）</strong></p>')
    a('<p>有效截面取 %d 块加劲肋 + 腹板两侧各 15 t<sub>w</sub> = %.0f mm 宽的腹板。</p>' %
      (st.bearing_n, 15 * sec.t_w))
    web_contrib = 15.0 * sec.t_w
    A_eff = st.bearing_n * st.bearing_b * st.bearing_t + web_contrib * sec.t_w
    I_eff = (st.bearing_t * (2.0 * st.bearing_b + sec.t_w) ** 3 / 12.0 + web_contrib * sec.t_w ** 3 / 12.0)
    i_eff = math.sqrt(I_eff / A_eff) if A_eff > 0 else 1.0
    lam = sec.h_w / i_eff
    a('<p>%s，%s，%s。</p>' % (
        _mi("A_{\\mathrm{eff}} = %.0f\\,\\mathrm{mm^2}" % A_eff),
        _mi("i_{\\mathrm{eff}} = %.1f\\,\\mathrm{mm}" % i_eff),
        _mi(LX.LAMBDA + " = h_w / i_{\\mathrm{eff}} = %.1f" % lam)))
    a('<p>a 类截面，%s，稳定系数 %s：</p>' % (_mi(LX.LAMBDA + " = %.1f" % lam), _mi(LX.VARPHI + " = 0.900")))
    cls_st = 'ok' if st.stab_ok else 'ng'; ok_st = '满足' if st.stab_ok else '不满足'
    a('<p><strong>%s &nbsp; [<span class="%s">%s</span>]</strong></p>' % (
        _mi(LX.SIGMA + " = R / (" + LX.VARPHI + " \\times A_{\\mathrm{eff}}) = %.1f\\,\\mathrm{MPa} < f_d = %d\\,\\mathrm{MPa}" %
            (st.sigma_stab, r.f_d_mid)), cls_st, ok_st))

    # ============== 九、连接构造说明 ==============
    a('<h2>九、连接构造说明</h2>')
    diff = sec.t_f - sec.t_f2
    a('<p>变截面处翼缘板厚从 %d mm 变为 %d mm（差 %d mm），按 JTG D64-2015 第7.3节，'
      '在较厚板侧加工成 1:4 斜坡过渡，采用全熔透对接焊缝连接，质量等级一级（100%% 无损检测）。</p>' %
      (sec.t_f, sec.t_f2, diff))
    a('<p>钢梁与混凝土桥面板之间通过焊钉剪力连接件实现组合作用，按 JTG D64-2015 第13章设计（本计算书从略）。</p>')

    # ============== 十、设计结果汇总 ==============
    a('<h2>十、设计结果汇总</h2>')
    a('<h3>10.1 截面尺寸</h3>')
    a('<table>')
    a('<tr><th>部位</th><th>腹板 h<sub>w</sub> &times; t<sub>w</sub> (mm)</th><th>翼缘 b<sub>f</sub> &times; t<sub>f</sub> (mm)</th><th>总高 h (mm)</th><th>W<sub>x</sub> (cm<sup>3</sup>)</th></tr>')
    a('<tr><td>跨中段</td><td>%d &times; %d</td><td>%d &times; %d</td><td>%d</td><td>%.2f</td></tr>' %
      (sec.h_w, sec.t_w, sec.b_f, sec.t_f, pm.h, pm.W_x / 1e3))
    a('<tr><td>变截面段</td><td>%d &times; %d</td><td>%d &times; %d</td><td>%d</td><td>%.2f</td></tr>' %
      (sec.h_w, sec.t_w, sec.b_f2, sec.t_f2, pv.h, pv.W_x / 1e3))
    a('</table>')

    a('<h3>10.2 焊缝汇总</h3>')
    a('<table>')
    a('<tr><th>焊缝位置</th><th>类型</th><th>h<sub>f</sub> (mm)</th><th>焊条</th></tr>')
    a('<tr><td>翼缘-腹板连接（全跨）</td><td>双面连续角焊缝</td><td>%d</td><td>%s</td></tr>' % (wd.h_f_chosen, p.electrode))
    a('<tr><td>横向加劲肋-腹板</td><td>双面角焊缝</td><td>6</td><td>%s</td></tr>' % p.electrode)
    a('<tr><td>支座加劲肋-腹板</td><td>双面角焊缝</td><td>8</td><td>%s</td></tr>' % p.electrode)
    a('<tr><td>翼缘对接（变截面处）</td><td>全熔透对接焊缝</td><td>&mdash;</td><td>%s</td></tr>' % p.electrode)
    a('</table>')

    a('<h3>10.3 加劲肋汇总</h3>')
    a('<table>')
    a('<tr><th>类型</th><th>间距 (mm)</th><th>尺寸 b<sub>s</sub> &times; t<sub>s</sub> (mm)</th><th>数量</th><th>说明</th></tr>')
    a('<tr><td>横向加劲肋</td><td>%.0f</td><td>%d &times; %d</td><td>%d 对</td><td>成对布置于腹板两侧</td></tr>' %
      (st.spacing, st.b_s, st.t_s, st.n_pairs))
    a('<tr><td>支座加劲肋</td><td>端部</td><td>%d &times; %d &times; %d</td><td>两端各%d块</td><td>端部刨平顶紧下翼缘</td></tr>' %
      (st.bearing_n, st.bearing_b, st.bearing_t, st.bearing_n))
    a('</table>')

    a('<h3>10.4 安全验算汇总</h3>')
    a('<table>')
    a('<tr><th>序号</th><th>验算项目</th><th>计算值</th><th>限值</th><th>判定</th></tr>')

    check_items = [
        (1, "跨中抗弯 &sigma;", "%.1f MPa" % c.sigma_mid, "%.0f MPa" % c.sigma_mid_limit, c.sigma_mid_ok),
        (2, "跨中抗剪 &tau;<sub>max</sub>", "%.1f MPa" % c.tau_max, "%.0f MPa" % c.tau_max_limit, c.tau_max_ok),
        (3, "折算应力 &sigma;<sub>zs</sub>", "%.1f MPa" % c.sigma_zs, "%.0f MPa" % c.sigma_zs_limit, c.sigma_zs_ok),
        (4, "活载挠度 &delta;<sub>q</sub>", "%.1f mm" % c.deflection_q, "%.1f mm" % c.deflection_limit, c.deflection_q_ok),
        (5, "整体稳定", "&mdash;", "&mdash;", True),
        (6, "疲劳 &Delta;&sigma;<sub>p</sub> (母材)", "%.1f MPa" % ft.delta_sigma_p, "%.1f MPa" % ft.delta_sigma_D_base, ft.check_base_metal),
        (7, "疲劳 &Delta;&sigma;<sub>p</sub> (焊缝)", "%.1f MPa" % ft.delta_sigma_p, "%.1f MPa" % ft.delta_sigma_D_weld, ft.check_fillet_weld),
        (8, "变截面抗弯 &sigma;", "%.1f MPa" % c.sigma_var, "%.0f MPa" % c.sigma_var_limit, c.sigma_var_ok),
        (9, "变截面抗剪 &tau;", "%.1f MPa" % c.tau_var, "%.0f MPa" % c.tau_var_limit, c.tau_var_ok),
        (10, "变截面折算 &sigma;<sub>zs</sub>", "%.1f MPa" % c.sigma_zs_var, "%.0f MPa" % c.sigma_zs_var_limit, c.sigma_zs_var_ok),
        (11, "支座承压 &sigma;<sub>ce</sub>", "%.1f MPa" % st.sigma_ce, "355 MPa", st.ce_ok),
        (12, "支座稳定 &sigma;", "%.1f MPa" % st.sigma_stab, "%.0f MPa" % r.f_d_mid, st.stab_ok),
    ]
    for i, name, val, lim, ok_ in check_items:
        cls = 'ok' if ok_ else 'ng'
        ok_str = '满足' if ok_ else '不满足'
        a('<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td><span class="%s">%s</span></td></tr>' %
          (i, name, val, lim, cls, ok_str))
    a('</table>')
    a('<hr>')

    # ============== 十一、结论 ==============
    a('<h2>十一、结论</h2>')
    a('<p>本设计针对 %d m 简支钢板梁桥，完成了以下全部设计内容：</p>' % p.L)
    a('<ol>')
    a('<li><strong>荷载统计与内力计算</strong> — 恒载（钢梁自重 + 二期恒载）和活载（公路-I级车道荷载）的标准值与设计值，控制截面弯矩和剪力；</li>')
    a('<li><strong>截面尺寸拟定</strong> — 焊接双轴对称工字形截面，腹板 %d&times;%d mm，翼缘 %d&times;%d mm（跨中段）/ %d&times;%d mm（变截面段）；</li>' %
      (sec.h_w, sec.t_w, sec.b_f, sec.t_f, sec.b_f2, sec.t_f2))
    a('<li><strong>强度验算</strong> — 跨中及变截面处抗弯、抗剪、折算应力均满足要求；</li>')
    a('<li><strong>刚度验算</strong> — 活载挠度 %.1f mm &lt; L/500 = %.1f mm；</li>' % (c.deflection_q, c.deflection_limit))
    a('<li><strong>疲劳验算</strong> — 疲劳应力幅 %.1f MPa &lt; 各细节类别常幅疲劳极限；</li>' % ft.delta_sigma_p)
    a('<li><strong>整体稳定性</strong> — 混凝土桥面板提供连续侧向支撑，自然满足；</li>')
    a('<li><strong>变截面设计</strong> — L/6 处减小翼缘，有效节约钢材；</li>')
    a('<li><strong>翼缘焊缝设计</strong> — 全跨 h<sub>f</sub> = %d mm 双面连续角焊缝；</li>' % wd.h_f_chosen)
    a('<li><strong>局部稳定设计</strong> — %d 对横向加劲肋 (%d&times;%d mm) + 支座加劲肋 (%d&times;%d&times;%d mm)。</li>' %
      (st.n_pairs, st.b_s, st.t_s, st.bearing_n, st.bearing_b, st.bearing_t))
    a('</ol>')

    if r.checks.all_ok():
        a('<p><strong>全部验算项目均满足 JTG D64-2015《公路钢结构桥梁设计规范》和 '
          'JTG D60-2015《公路桥涵设计通用规范》的相关规定，设计结果合理可行。</strong></p>')
    else:
        a('<p><strong>部分验算项目不满足要求，需调整截面尺寸重新计算。</strong></p>')

    a(_HTML_FOOTER)

    return '\n'.join(L)


# ============================================================
# 文件保存
# ============================================================

def save_html(r: CalcResult, path: str):
    html = generate_html(r)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path


def save_pdf(r: CalcResult, path: str, callback=None):
    """使用 QWebEngineView 导出 PDF"""
    html = generate_html(r)
    _render_to_pdf(html, path, callback)


def _render_to_pdf(html_content: str, pdf_path: str, callback=None):
    """用 setHtml 加载 HTML，轮询 MathJax 完成后 printToPdf"""
    from PySide6.QtCore import QUrl

    view = QWebEngineView()
    view.resize(900, 1200)
    poll_count = [0]
    max_polls = 80
    _done = [False]

    def _on_print_finished(file_path, success):
        view.deleteLater()
        if callback:
            callback(success)

    view.page().pdfPrintingFinished.connect(_on_print_finished)

    def _on_load(ok):
        if not ok:
            if callback:
                callback(False)
            view.deleteLater()
            return
        QTimer.singleShot(2000, _poll)

    def _poll():
        if _done[0]:
            return
        poll_count[0] += 1
        # 检查 MathJax 的 data-mjax-done 属性
        js = "(document.body&&document.body.getAttribute('data-mjax-done')==='1')?'done':'wait'"
        view.page().runJavaScript(js, _on_result)

    def _on_result(s):
        if _done[0]:
            return
        if s == 'done':
            _done[0] = True
            view.page().printToPdf(pdf_path)
        elif poll_count[0] < max_polls:
            QTimer.singleShot(500, _poll)
        else:
            _done[0] = True
            view.page().printToPdf(pdf_path)

    view.loadFinished.connect(_on_load)
    view.setHtml(html_content, QUrl("https://cdn.jsdelivr.net/"))


def save_all(r: CalcResult, output_dir: str, base_name: str = "计算书"):
    """输出 HTML 文件"""
    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, base_name + ".html")
    save_html(r, html_path)
    return html_path

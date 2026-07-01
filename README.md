# 钢板梁设计计算程序

35m 简支焊接双轴对称工字形钢板梁设计计算，依据 **JTG D64-2015**《公路钢结构桥梁设计规范》和 **JTG D60-2015**《公路桥涵设计通用规范》。

## 功能

- **荷载计算** — 恒载（一期 + 二期）、公路‑I 级活载（含冲击系数）、荷载组合
- **截面设计** — 双轴对称工字形截面几何特性（A, I_x, W_x, I_y, i_y, S_x 等）
- **自动估算** — 根据跨径和弯矩自动估算经济截面尺寸
- **强度验算** — 弯曲正应力、剪应力、折算应力、疲劳强度（疲劳荷载Ⅰ + Ⅱ）
- **焊缝计算** — 翼缘与腹板连接角焊缝（E50 焊条）
- **整体稳定性** — 成桥工况（混凝土桥面板提供连续侧向约束，自然满足）
- **局部稳定性** — 腹板横向加劲肋布置、翼缘宽厚比（b₁/t_f ≤ 15√(235/f_y)）
- **挠度验算** — 总挠度 ≤ L/500，活载挠度 ≤ L/600
- **变截面设计** — 跨中与支点分段变截面（可选）

## 输出

- **HTML 报告** — 含 MathJax CDN 渲染的 LaTeX 公式
- **PDF 导出** — 通过 QWebEngineView `printToPdf` 导出
- **SVG 示意图**
  - 横截面图（标注 b_f, h, h_w, t_w, t_f）
  - 弯矩图 + 剪力图
  - 变截面布置示意图
  - 加劲肋布置示意图

## 使用

### 源代码运行

```bash
pip install PySide6
python main.py
```

### 打包单文件 EXE

```bash
pip install pyinstaller
pyinstaller --clean --onefile --noconsole --icon path\to\icon.ico main.py
```

## 项目结构

```
├── main.py          # 入口
├── calculator.py    # 计算引擎
├── gui.py           # PySide6 GUI（深色主题，3 个选项卡）
├── report.py        # HTML 报告生成 + SVG 图解 + PDF 导出
├── requirements.txt
└── README.md
```

## 规范依据

| 规范 | 内容 |
|------|------|
| JTG D64-2015 | 强度、稳定、疲劳、挠度、构造要求 |
| JTG D60-2015 | 荷载取值、荷载组合 |

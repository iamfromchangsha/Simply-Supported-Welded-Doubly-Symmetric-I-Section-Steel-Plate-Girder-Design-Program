# -*- coding: utf-8 -*-
"""
钢板梁设计计算程序 — PySide6 GUI (HTML + PDF 导出)
"""

import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox, QDoubleSpinBox, QSpinBox, QLabel,
    QPushButton, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox, QFrame, QApplication, QProgressDialog,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QLinearGradient, QBrush
from PySide6.QtWebEngineWidgets import QWebEngineView

from calculator import (
    DesignParams, SectionInput, CalcResult,
    calculate as calc_engine, calc_section_props,
    auto_estimate_section, format_number,
)
from report import generate_html, save_html, save_pdf, save_all


# ============================================================
# 全局 QSS 样式表
# ============================================================

STYLESHEET = r"""
/* ===== 全局 ===== */
QMainWindow {
    background-color: #1a1a2e;
}

/* 背景覆盖层容器 */
QWidget#centralContainer {
    background: qlineargradient(x1:0 y1:0, x2:1 y2:1,
        stop:0 #1a1a2e, stop:0.5 #16213e, stop:1 #0f3460);
}

/* ===== TabWidget ===== */
QTabWidget::pane {
    border: none;
    background: transparent;
    padding: 8px;
}
QTabBar::tab {
    background: rgba(255,255,255,0.06);
    color: #8a9bb5;
    padding: 10px 24px;
    margin: 4px 2px 0 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 13px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background: rgba(255,255,255,0.14);
    color: #e0e0e0;
}
QTabBar::tab:hover:!selected {
    background: rgba(255,255,255,0.10);
    color: #c0c8d0;
}

/* ===== GroupBox ===== */
QGroupBox {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
    margin-top: 14px;
    padding: 16px 12px 12px 12px;
    font-size: 13px;
    font-weight: bold;
    color: #b0c4de;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px 0 8px;
    color: #7ec8e3;
}

/* ===== Label ===== */
QLabel {
    color: #c8d6e5;
    font-size: 12px;
}

/* ===== SpinBox / DoubleSpinBox ===== */
QSpinBox, QDoubleSpinBox {
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    color: #e8e8e8;
    min-width: 150px;
    min-height: 28px;
}
QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: rgba(126,200,227,0.5);
    background: rgba(255,255,255,0.13);
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #7ec8e3;
    background: rgba(255,255,255,0.16);
}
QSpinBox:disabled, QDoubleSpinBox:disabled {
    background: rgba(255,255,255,0.04);
    color: #666;
    border-color: rgba(255,255,255,0.06);
}
QSpinBox::up-button, QDoubleSpinBox::up-button {
    border-left: 1px solid rgba(255,255,255,0.10);
    border-bottom: 1px solid rgba(255,255,255,0.10);
    width: 18px;
    border-top-right-radius: 6px;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    border-left: 1px solid rgba(255,255,255,0.10);
    width: 18px;
    border-bottom-right-radius: 6px;
}

/* ===== RadioButton ===== */
QRadioButton {
    color: #c8d6e5;
    font-size: 12px;
    spacing: 8px;
    padding: 4px 0;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(126,200,227,0.5);
    border-radius: 9px;
    background: rgba(255,255,255,0.06);
}
QRadioButton::indicator:checked {
    background: #7ec8e3;
    border-color: #7ec8e3;
}

/* ===== PushButton ===== */
QPushButton {
    background: rgba(126,200,227,0.20);
    border: 1px solid rgba(126,200,227,0.35);
    border-radius: 7px;
    padding: 8px 18px;
    color: #d0e8f0;
    font-size: 12px;
    font-weight: bold;
    min-height: 30px;
}
QPushButton:hover {
    background: rgba(126,200,227,0.32);
    border-color: rgba(126,200,227,0.6);
}
QPushButton:pressed {
    background: rgba(126,200,227,0.15);
}
QPushButton:disabled {
    background: rgba(255,255,255,0.04);
    border-color: rgba(255,255,255,0.06);
    color: #555;
}

/* 主计算按钮 */
QPushButton#btnPrimary {
    background: qlineargradient(x1:0 y1:0, x2:1 y2:0,
        stop:0 #2193b0, stop:1 #6dd5ed);
    border: none;
    border-radius: 8px;
    padding: 10px 28px;
    color: #fff;
    font-size: 15px;
    font-weight: bold;
    min-height: 38px;
}
QPushButton#btnPrimary:hover {
    background: qlineargradient(x1:0 y1:0, x2:1 y2:0,
        stop:0 #2aa5c4, stop:1 #7ee0f5);
}
QPushButton#btnPrimary:pressed {
    background: qlineargradient(x1:0 y1:0, x2:1 y2:0,
        stop:0 #1a7a96, stop:1 #5abfd8);
}

/* ===== QFrame 分隔线 ===== */
QFrame#separator {
    color: rgba(255,255,255,0.12);
    max-height: 2px;
}

/* ===== QTextEdit / QLabel 预览 ===== */
QTextEdit {
    background: rgba(0,0,0,0.25);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    color: #c0c8d0;
    font-size: 12px;
    padding: 6px;
}
QLabel#previewLabel {
    background: rgba(0,0,0,0.25);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    color: #7ec8e3;
    font-size: 12px;
    padding: 10px;
    font-family: "Consolas", "Courier New", monospace;
}

/* ===== StatusBar ===== */
QStatusBar {
    background: rgba(0,0,0,0.35);
    color: #7a8a9a;
    font-size: 11px;
    padding: 4px 10px;
    border-top: 1px solid rgba(255,255,255,0.06);
}

/* ===== ProgressDialog ===== */
QProgressDialog {
    background: rgba(26,26,46,0.95);
    border: 1px solid rgba(126,200,227,0.3);
    border-radius: 10px;
}
QProgressDialog QLabel {
    color: #c0c8d0;
    font-size: 13px;
}

/* ===== ScrollView ===== */
QTabWidget QScrollArea {
    background: transparent;
    border: none;
}
QTabWidget QScrollArea QWidget {
    background: transparent;
}

/* ===== WebEngine View ===== */
QWebEngineView {
    background: rgba(0,0,0,0.20);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
}
"""


# ============================================================
# Tab 1: 设计参数
# ============================================================

class ParamTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 8, 16, 16)

        gb_geo = QGroupBox("■  几何参数")
        form_geo = QFormLayout()
        form_geo.setSpacing(10)
        form_geo.setContentsMargins(12, 20, 12, 10)

        self.spin_L  = self._make_double(20.0, 50.0, 35.0, 1, " m", "计算跨径 L (m)")
        self.spin_B  = self._make_double(1.0, 3.0, 1.8, 1, " m", "桥面板宽度 B (m)")
        self.spin_H1 = self._make_double(0.05, 0.20, 0.08, 2, " m", "混凝土桥面板厚度 H₁ (m)")
        self.spin_H2 = self._make_double(0.03, 0.15, 0.06, 2, " m", "沥青铺装层厚度 H₂ (m)")

        form_geo.addRow("计算跨径 L:", self.spin_L)
        form_geo.addRow("桥面板宽度 B:", self.spin_B)
        form_geo.addRow("混凝土桥面板厚度 H₁:", self.spin_H1)
        form_geo.addRow("沥青铺装层厚度 H₂:", self.spin_H2)
        gb_geo.setLayout(form_geo)
        layout.addWidget(gb_geo)

        gb_coef = QGroupBox("■  荷载系数")
        form_coef = QFormLayout()
        form_coef.setSpacing(10)
        form_coef.setContentsMargins(12, 20, 12, 10)

        self.spin_eta      = self._make_double(0.1, 1.0, 0.43, 2, "", "横向分布系数 η")
        self.spin_gamma_G  = self._make_double(1.0, 1.5, 1.2, 1, "", "恒载分项系数 γ_G")
        self.spin_gamma_Q  = self._make_double(1.0, 1.8, 1.4, 1, "", "活载分项系数 γ_Q")
        self.spin_gamma_0  = self._make_double(0.9, 1.5, 1.1, 1, "", "结构重要性系数 γ₀")
        self.spin_mu       = self._make_double(1.0, 1.5, 1.14, 2, "", "活载冲击系数 1+μ")

        form_coef.addRow("横向分布系数 η:", self.spin_eta)
        form_coef.addRow("恒载分项系数 γ_G:", self.spin_gamma_G)
        form_coef.addRow("活载分项系数 γ_Q:", self.spin_gamma_Q)
        form_coef.addRow("结构重要性系数 γ₀:", self.spin_gamma_0)
        form_coef.addRow("活载冲击系数 1+μ:", self.spin_mu)
        gb_coef.setLayout(form_coef)
        layout.addWidget(gb_coef)

        layout.addStretch()

    @staticmethod
    def _make_double(min_v, max_v, default, decimals, suffix, tip=""):
        spin = QDoubleSpinBox()
        spin.setRange(min_v, max_v)
        spin.setValue(default)
        spin.setDecimals(decimals)
        if suffix:
            spin.setSuffix(suffix)
        spin.setMinimumWidth(160)
        spin.setMinimumHeight(32)
        if tip:
            spin.setToolTip(tip)
        return spin

    def get_params(self) -> DesignParams:
        return DesignParams(
            L=self.spin_L.value(),
            B=self.spin_B.value(),
            H1=self.spin_H1.value(),
            H2=self.spin_H2.value(),
            eta=self.spin_eta.value(),
            gamma_G=self.spin_gamma_G.value(),
            gamma_Q=self.spin_gamma_Q.value(),
            gamma_0=self.spin_gamma_0.value(),
            mu_impact=self.spin_mu.value(),
        )


# ============================================================
# Tab 2: 截面设计
# ============================================================

class SectionTab(QWidget):
    def __init__(self):
        super().__init__()
        self._current_result: CalcResult = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 8, 16, 16)

        # 模式选择
        gb_mode = QGroupBox("■  截面设计模式")
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(12, 10, 12, 6)
        self.radio_auto = QRadioButton("自动估算（推荐）")
        self.radio_manual = QRadioButton("手动输入")
        self.radio_auto.setChecked(True)

        self.btn_group = QButtonGroup()
        self.btn_group.addButton(self.radio_auto, 0)
        self.btn_group.addButton(self.radio_manual, 1)

        self.btn_estimate = QPushButton("重新估算")
        self.btn_estimate.clicked.connect(self._on_auto_estimate)
        self.btn_estimate.setFixedWidth(100)

        mode_layout.addWidget(self.radio_auto)
        mode_layout.addWidget(self.radio_manual)
        mode_layout.addStretch()
        mode_layout.addWidget(self.btn_estimate)
        gb_mode.setLayout(mode_layout)
        layout.addWidget(gb_mode)

        # 跨中截面
        gb_mid = QGroupBox("■  跨中段截面尺寸")
        form_mid = QFormLayout()
        form_mid.setSpacing(10)
        form_mid.setContentsMargins(12, 20, 12, 10)

        self.spin_hw = self._make_spin(500, 5000, 1800, 10, " mm")
        self.spin_tw = self._make_spin(6, 60, 14, 2, " mm")
        self.spin_bf = self._make_spin(150, 1000, 500, 10, " mm")
        self.spin_tf = self._make_spin(8, 80, 28, 2, " mm")

        form_mid.addRow("腹板高度 h_w:", self.spin_hw)
        form_mid.addRow("腹板厚度 t_w:", self.spin_tw)
        form_mid.addRow("翼缘宽度 b_f:", self.spin_bf)
        form_mid.addRow("翼缘厚度 t_f:", self.spin_tf)
        gb_mid.setLayout(form_mid)
        layout.addWidget(gb_mid)

        # 变截面
        gb_var = QGroupBox("■  变截面段截面尺寸")
        form_var = QFormLayout()
        form_var.setSpacing(10)
        form_var.setContentsMargins(12, 20, 12, 10)

        self.spin_bf2 = self._make_spin(100, 1000, 420, 10, " mm")
        self.spin_tf2 = self._make_spin(6, 60, 22, 2, " mm")

        form_var.addRow("翼缘宽度 b_f₂:", self.spin_bf2)
        form_var.addRow("翼缘厚度 t_f₂:", self.spin_tf2)
        gb_var.setLayout(form_var)
        layout.addWidget(gb_var)

        # 截面特性预览
        gb_preview = QGroupBox("■  截面特性预览")
        preview_layout = QVBoxLayout()
        self.lbl_preview = QLabel("点击「重新估算」或「计算截面特性」查看")
        self.lbl_preview.setObjectName("previewLabel")
        self.lbl_preview.setTextFormat(Qt.TextFormat.PlainText)
        preview_layout.addWidget(self.lbl_preview)
        gb_preview.setLayout(preview_layout)
        layout.addWidget(gb_preview)

        # 按钮
        btn_layout = QHBoxLayout()
        self.btn_calc_props = QPushButton("计算截面特性")
        self.btn_calc_props.clicked.connect(self._on_calc_props)
        self.btn_apply_auto = QPushButton("应用推荐值到输入框")
        self.btn_apply_auto.clicked.connect(self._on_apply_auto)

        btn_layout.addWidget(self.btn_calc_props)
        btn_layout.addWidget(self.btn_apply_auto)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

        self.radio_auto.toggled.connect(self._on_mode_changed)
        self.radio_manual.toggled.connect(self._on_mode_changed)
        self._on_mode_changed()

        self._estimated_section: SectionInput = None

    @staticmethod
    def _make_spin(min_v, max_v, default, step, suffix=""):
        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        spin.setValue(int(default))
        spin.setSingleStep(step)
        if suffix:
            spin.setSuffix(suffix)
        spin.setMinimumWidth(160)
        spin.setMinimumHeight(32)
        return spin

    def _on_mode_changed(self):
        auto = self.radio_auto.isChecked()
        self.spin_hw.setEnabled(not auto)
        self.spin_tw.setEnabled(not auto)
        self.spin_bf.setEnabled(not auto)
        self.spin_tf.setEnabled(not auto)
        self.btn_estimate.setEnabled(auto)

    def _on_auto_estimate(self):
        try:
            params = self._get_parent_params()
            from calculator import calc_dead_load_2nd, calc_highway_I_Pk, calc_design_value, get_strength, Q_K

            g2 = calc_dead_load_2nd(params.B, params.H1, params.H2)
            P_k_orig, _ = calc_highway_I_Pk(params.L)
            q_live = params.eta * Q_K
            P_live = params.eta * P_k_orig
            M_gk2 = g2 * params.L ** 2 / 8.0
            M_qk0 = q_live * params.L ** 2 / 8.0 + P_live * params.L / 4.0
            M_Ed0 = calc_design_value(params.gamma_0, params.gamma_G, params.gamma_Q,
                                       params.mu_impact, M_gk2, M_qk0)
            f_d_est = get_strength(28.0)[0]
            sec = auto_estimate_section(params.L, M_Ed0, f_d_est)
            for _ in range(3):
                props_tmp = calc_section_props(sec.h_w, sec.t_w, sec.b_f, sec.t_f)
                g = g2 + props_tmp.g1
                M_gk = g * params.L ** 2 / 8.0
                M_Ed = calc_design_value(params.gamma_0, params.gamma_G, params.gamma_Q,
                                          params.mu_impact, M_gk, M_qk0)
                sec = auto_estimate_section(params.L, M_Ed, f_d_est)

            self._estimated_section = sec
            self._update_spins_from_section(sec)
            self._update_preview(sec)
            QMessageBox.information(self, "估算完成",
                                     f"截面已自动估算。\n"
                                     f"h_w={sec.h_w:.0f}mm, t_w={sec.t_w:.0f}mm\n"
                                     f"b_f={sec.b_f:.0f}mm, t_f={sec.t_f:.0f}mm\n"
                                     f"如需修改请切换至「手动输入」模式。")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "估算失败", f"自动估算出错：{e}")

    def _on_apply_auto(self):
        if self._estimated_section is not None:
            self._update_spins_from_section(self._estimated_section)
        else:
            QMessageBox.information(self, "提示", "请先点击「重新估算」获取推荐值。")

    def _update_spins_from_section(self, sec: SectionInput):
        self.spin_hw.setValue(int(sec.h_w))
        self.spin_tw.setValue(int(sec.t_w))
        self.spin_bf.setValue(int(sec.b_f))
        self.spin_tf.setValue(int(sec.t_f))
        self.spin_bf2.setValue(int(sec.b_f2))
        self.spin_tf2.setValue(int(sec.t_f2))

    def _update_preview(self, sec: SectionInput):
        pm = calc_section_props(sec.h_w, sec.t_w, sec.b_f, sec.t_f)
        pv = calc_section_props(sec.h_w, sec.t_w, sec.b_f2, sec.t_f2)

        lines = [
            "══════════ 跨中段 ══════════",
            "",
            f"  总高 h      = {pm.h:8.0f} mm",
            f"  面积 A      = {pm.A:8.0f} mm²",
            f"  惯性矩 I_x  = {format_number(pm.I_x/1e6, 2):>8} × 10⁶ mm⁴",
            f"  截面模量 W_x = {format_number(pm.W_x/1e3, 2):>8} cm³",
            f"  钢梁自重 g₁  = {format_number(pm.g1, 3):>8} kN/m",
            "",
            "══════════ 变截面段 ══════════",
            "",
            f"  总高 h      = {pv.h:8.0f} mm",
            f"  面积 A      = {pv.A:8.0f} mm²",
            f"  惯性矩 I_x  = {format_number(pv.I_x/1e6, 2):>8} × 10⁶ mm⁴",
            f"  截面模量 W_x = {format_number(pv.W_x/1e3, 2):>8} cm³",
            f"  钢梁自重 g₁  = {format_number(pv.g1, 3):>8} kN/m",
        ]
        self.lbl_preview.setText("\n".join(lines))

    def _on_calc_props(self):
        sec = self.get_section()
        self._update_preview(sec)

    def _get_parent_params(self) -> DesignParams:
        main_window = self.window()
        if main_window and hasattr(main_window, 'param_tab'):
            return main_window.param_tab.get_params()
        return DesignParams()

    def get_section(self) -> SectionInput:
        return SectionInput(
            h_w=float(self.spin_hw.value()),
            t_w=float(self.spin_tw.value()),
            b_f=float(self.spin_bf.value()),
            t_f=float(self.spin_tf.value()),
            b_f2=float(self.spin_bf2.value()),
            t_f2=float(self.spin_tf2.value()),
        )

    def get_mode_auto(self) -> bool:
        return self.radio_auto.isChecked()


# ============================================================
# Tab 3: 计算结果与导出
# ============================================================

class ResultTab(QWidget):
    def __init__(self):
        super().__init__()
        self._result: CalcResult = None
        self._html_text: str = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 8, 16, 16)

        # 顶部按钮栏
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        self.btn_calc = QPushButton("▶  开始计算")
        self.btn_calc.setObjectName("btnPrimary")
        self.btn_calc.clicked.connect(self._on_calculate)

        self.btn_export_html = QPushButton("导出 HTML")
        self.btn_export_html.clicked.connect(self._on_export_html)
        self.btn_export_html.setEnabled(False)

        self.btn_export_pdf = QPushButton("导出 PDF")
        self.btn_export_pdf.clicked.connect(self._on_export_pdf)
        self.btn_export_pdf.setEnabled(False)

        self.btn_export_all = QPushButton("全部导出")
        self.btn_export_all.clicked.connect(self._on_export_all)
        self.btn_export_all.setEnabled(False)

        top_layout.addWidget(self.btn_calc)
        top_layout.addWidget(self.btn_export_html)
        top_layout.addWidget(self.btn_export_pdf)
        top_layout.addWidget(self.btn_export_all)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # 分隔线
        line = QFrame()
        line.setObjectName("separator")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(line)

        # 使用 QWebEngineView 预览 HTML（支持 MathJax 渲染）
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # 进度提示
        self.progress = QProgressDialog("生成 PDF 中，请稍候...", None, 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.setCancelButton(None)
        self.progress.close()

    def _on_calculate(self):
        try:
            main_window = self.window()
            if not main_window:
                return

            params = main_window.param_tab.get_params()
            section = main_window.section_tab.get_section()

            if main_window.section_tab.get_mode_auto():
                section = None

            self.web_view.setHtml(
                "<div style='display:flex;align-items:center;justify-content:center;"
                "height:100%;color:#7ec8e3;font-size:18px;font-family:Microsoft YaHei,sans-serif;'>"
                "⏳ 计算中，请稍候...</div>")
            QApplication.processEvents()

            r = calc_engine(params, section)
            self._result = r
            self._html_text = generate_html(r)

            self.web_view.setHtml(self._html_text)

            self.btn_export_html.setEnabled(True)
            self.btn_export_pdf.setEnabled(True)
            self.btn_export_all.setEnabled(True)

            main_window.section_tab._update_spins_from_section(r.section)
            main_window.section_tab._update_preview(r.section)

            if r.checks.all_ok():
                QMessageBox.information(self, "计算完成", "全部验算通过！设计合理。")
            else:
                QMessageBox.warning(self, "计算完成",
                                     "计算完成，但部分验算未通过。\n请检查结果并调整截面尺寸。")

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "计算错误", f"计算过程中出错：\n{e}")

    def _on_export_html(self):
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 HTML 计算书", "计算书.html",
            "HTML 文件 (*.html);;所有文件 (*.*)"
        )
        if path:
            save_html(self._result, path)
            QMessageBox.information(self, "导出成功", f"已保存至：\n{path}")

    def _on_export_pdf(self):
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 PDF 计算书", "计算书.pdf",
            "PDF 文件 (*.pdf);;所有文件 (*.*)"
        )
        if not path:
            return

        self.progress.show()
        QApplication.processEvents()

        def _on_pdf_done(ok):
            self.progress.close()
            if ok:
                QMessageBox.information(self, "导出成功", f"已保存至：\n{path}")
            else:
                QMessageBox.warning(self, "导出失败", "PDF 生成失败，请检查后重试。")

        save_pdf(self._result, path, callback=_on_pdf_done)

    def _on_export_all(self):
        if not self._result:
            return
        dir_path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not dir_path:
            return
        html_path = save_all(self._result, dir_path, "计算书")
        QMessageBox.information(self, "导出成功",
                                 f"HTML 已保存至：\n{html_path}\n\n"
                                 f"PDF 请使用「导出 PDF」按钮单独导出。")


# ============================================================
# 主窗口
# ============================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("钢板梁设计计算程序 — 简支工字形钢板梁")
        self.resize(1150, 820)

        # 全局样式
        self.setStyleSheet(STYLESHEET)

        # 创建中心容器（用于背景渐变）
        container = QWidget()
        container.setObjectName("centralContainer")
        self.setCentralWidget(container)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        self.param_tab = ParamTab()
        self.section_tab = SectionTab()
        self.result_tab = ResultTab()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.param_tab, "  设计参数  ")
        self.tabs.addTab(self.section_tab, "  截面设计  ")
        self.tabs.addTab(self.result_tab, "  结果与导出  ")

        container_layout.addWidget(self.tabs)

        self.statusBar().showMessage("  就绪  |  JTG D64-2015《公路钢结构桥梁设计规范》 / JTG D60-2015")

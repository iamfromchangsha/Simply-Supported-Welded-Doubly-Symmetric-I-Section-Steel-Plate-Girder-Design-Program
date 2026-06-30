# -*- coding: utf-8 -*-
"""
钢板梁设计计算程序 — 入口
35m 简支焊接双轴对称工字形钢板梁设计
依据 JTG D64-2015《公路钢结构桥梁设计规范》、JTG D60-2015《公路桥涵设计通用规范》
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from gui import MainWindow


def main():
    app = QApplication(sys.argv)

    # 设置应用默认字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

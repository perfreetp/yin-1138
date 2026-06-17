import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QStackedWidget

import database
from project_selector import ProjectSelector
from risk_fill import RiskFillWindow
from daily_report import DailyReportWindow
from review_window import ReviewWindow


class AppController(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("民航维修外包承包商 · 现场风险日报工具")
        self.resize(1280, 820)
        self._pages = {}
        self._init_page_selector()
        self._current_report_key = None

    def _init_page_selector(self):
        page = ProjectSelector()
        page.go_to_fill.connect(self._open_fill)
        page.go_to_report.connect(self._open_report)
        idx = self.addWidget(page)
        self._pages["selector"] = idx
        self.setCurrentIndex(idx)

    def _open_fill(self, context):
        key = "fill_" + str(id(context))
        if key in self._pages:
            old = self.widget(self._pages[key])
            self.removeWidget(old)
            del self._pages[key]
        page = RiskFillWindow(context)
        page.go_back.connect(self._back_to_selector)
        page.go_to_report.connect(self._open_report)
        idx = self.addWidget(page)
        self._pages[key] = idx
        self.setCurrentIndex(idx)
        self.setWindowTitle("风险填报与审核 - 民航维修现场风险日报")

    def _open_report(self, context):
        key = "report_" + str(id(context))
        if key in self._pages:
            old = self.widget(self._pages[key])
            self.removeWidget(old)
            del self._pages[key]
        page = DailyReportWindow(context)
        page.go_back.connect(self._back_to_selector)
        page.go_to_fill.connect(self._open_fill)
        page.go_to_review.connect(self._open_review)
        idx = self.addWidget(page)
        self._pages[key] = idx
        self._current_report_key = key
        self.setCurrentIndex(idx)
        self.setWindowTitle("风险日报看板 - 民航维修现场风险日报")

    def _open_review(self, context):
        key = "review_" + str(id(context))
        if key in self._pages:
            old = self.widget(self._pages[key])
            self.removeWidget(old)
            del self._pages[key]
        page = ReviewWindow(context)
        page.go_back.connect(self._back_to_report)
        page.go_to_risk.connect(self._review_jump_risk)
        idx = self.addWidget(page)
        self._pages[key] = idx
        self.setCurrentIndex(idx)
        self.setWindowTitle("会议复盘视图 - 跟进事项闭环跟踪")

    def _back_to_report(self):
        if self._current_report_key and self._current_report_key in self._pages:
            self.setCurrentIndex(self._pages[self._current_report_key])
            self.setWindowTitle("风险日报看板 - 民航维修现场风险日报")
        else:
            self._back_to_selector()

    def _review_jump_risk(self, risk_id, context):
        ctx = dict(context)
        ctx["prefill_risk_id"] = risk_id
        self._open_fill(ctx)

    def _back_to_selector(self):
        self.setCurrentIndex(self._pages["selector"])
        self.setWindowTitle("民航维修外包承包商 · 现场风险日报工具")
        page = self.widget(self._pages["selector"])
        if hasattr(page, "_do_search"):
            page._do_search()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    app.setStyleSheet("""
        QToolTip { font-family: 'Microsoft YaHei'; }
        QComboBox, QLineEdit, QDateEdit, QDateTimeEdit, QTextEdit, QSpinBox {
            padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px;
            background: white; font-size: 13px; min-height: 22px;
        }
        QComboBox:focus, QLineEdit:focus, QDateEdit:focus, QDateTimeEdit:focus, QTextEdit:focus {
            border: 1px solid #3b82f6;
        }
        QGroupBox {
            font-weight: bold; font-size: 13px; border: 1px solid #e2e8f0;
            border-radius: 8px; margin-top: 12px; padding-top: 10px; color: #1e293b;
        }
        QGroupBox::title {
            subcontrol-origin: margin; left: 14px; padding: 0 8px;
        }
        QCheckBox {
            spacing: 6px; font-size: 13px;
        }
        QCheckBox::indicator {
            width: 16px; height: 16px; border: 1px solid #cbd5e1; border-radius: 3px;
            background: white;
        }
        QCheckBox::indicator:checked {
            background: #2563eb; border: 1px solid #2563eb;
        }
    """)
    database.init_db()
    w = AppController()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

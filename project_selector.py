from datetime import date
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QGroupBox, QSizePolicy
)
from PySide6.QtGui import QFont, QColor, QBrush

import database

HIGH_RISK_TYPES = ["喷漆作业", "打磨作业", "清洗作业", "结构拆装", "发动机维修", "起落架检修", "复合材料修复"]


class ProjectSelector(QWidget):
    go_to_report = Signal(dict)
    go_to_fill = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("民航维修现场风险日报 - 项目选择")
        self.resize(1200, 780)
        self._build_ui()
        self._load_initial_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("民航维修外包承包商 · 现场风险日报工具")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        subtitle = QLabel("第一步：按客户航司 / 维修基地 / 合同项目 / 作业日期，定位当天的高风险作业")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #64748b; font-size: 13px;")
        root.addWidget(subtitle)

        filter_box = QGroupBox("筛选条件")
        filter_layout = QHBoxLayout(filter_box)
        filter_layout.setContentsMargins(16, 18, 16, 16)
        filter_layout.setSpacing(14)

        self.cb_airline = QComboBox()
        self.cb_base = QComboBox()
        self.cb_contract = QComboBox()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())

        for w, label in [(self.cb_airline, "客户航司"), (self.cb_base, "维修基地"),
                         (self.cb_contract, "合同项目"), (self.date_edit, "作业日期")]:
            col = QVBoxLayout()
            lab = QLabel(label)
            lab.setStyleSheet("font-size: 12px; color: #475569;")
            col.addWidget(lab)
            col.addWidget(w)
            filter_layout.addLayout(col)

        self.btn_search = QPushButton("🔍 筛选当天风险")
        self.btn_search.setFixedHeight(36)
        self.btn_search.setStyleSheet("""QPushButton{background:#2563eb;color:white;padding:0 20px;
            border:none;border-radius:6px;font-weight:600;}QPushButton:hover{background:#1d4ed8;}""")
        filter_layout.addWidget(self.btn_search, 1)

        root.addWidget(filter_box)

        summary_box = QFrame()
        summary_box.setStyleSheet("""QFrame{background:#f8fafc;border:1px solid #e2e8f0;
            border-radius:8px;}""")
        sl = QHBoxLayout(summary_box)
        sl.setContentsMargins(18, 14, 18, 14)
        sl.setSpacing(30)

        self.lbl_total = self._stat_label("当日风险总数", "0", "#0f172a")
        self.lbl_high = self._stat_label("高风险作业", "0", "#dc2626")
        self.lbl_unreviewed = self._stat_label("待审核", "0", "#d97706")
        self.lbl_need_officer = self._stat_label("需客户安全员", "0", "#7c3aed")

        for l in [self.lbl_total, self.lbl_high, self.lbl_unreviewed, self.lbl_need_officer]:
            sl.addWidget(l)
        root.addWidget(summary_box)

        tbl_box = QGroupBox("当日涉及的高风险作业清单")
        tbl_layout = QVBoxLayout(tbl_box)

        self.table = QTableWidget()
        headers = ["ID", "作业类型", "作业位置", "班组", "状态", "许可证", "作业范围", "需安全员", "已审核"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""QTableWidget{gridline-color:#e2e8f0;font-size:12px;}
            QHeaderView::section{background:#f1f5f9;padding:8px;border:none;font-weight:600;}
            QTableWidget::item{padding:6px;}""")
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for i in range(1, len(headers) - 1):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeToContents)
        self.table.doubleClicked.connect(self._on_table_double)
        tbl_layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_fill = QPushButton("➕ 填报/编辑风险")
        self.btn_report = QPushButton("📋 进入日报输出")
        for b, style in [
            (self.btn_fill, "background:#059669;"),
            (self.btn_report, "background:#0ea5e9;")
        ]:
            b.setFixedHeight(38)
            b.setStyleSheet(f"""QPushButton{{{style}color:white;padding:0 22px;border:none;
                border-radius:6px;font-weight:600;font-size:13px;}}
                QPushButton:hover{{opacity:0.9;}}""")
        btn_row.addWidget(self.btn_fill)
        btn_row.addWidget(self.btn_report)
        tbl_layout.addLayout(btn_row)

        root.addWidget(tbl_box, 1)

        self.cb_airline.currentIndexChanged.connect(self._on_filter_changed)
        self.cb_base.currentIndexChanged.connect(self._on_filter_changed)
        self.btn_search.clicked.connect(self._do_search)
        self.btn_fill.clicked.connect(self._on_fill)
        self.btn_report.clicked.connect(self._on_report)

    def _stat_label(self, title, value, color):
        f = QFrame()
        f.setFrameShape(QFrame.NoFrame)
        f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(f)
        v.setSpacing(4)
        v_lab = QLabel(title)
        v_lab.setStyleSheet("font-size:12px;color:#64748b;")
        v_val = QLabel(value)
        v_val.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        v_val.setStyleSheet(f"color:{color};")
        v.addWidget(v_lab)
        v.addWidget(v_val)
        return f

    def _load_initial_data(self):
        self.airlines = database.get_airlines()
        self.bases = database.get_bases()

        self.cb_airline.addItem("全部航司", None)
        for a in self.airlines:
            self.cb_airline.addItem(a["name"], a["id"])

        self.cb_base.addItem("全部基地", None)
        for b in self.bases:
            self.cb_base.addItem(b["name"], b["id"])

        self._refresh_contracts()
        self._do_search()

    def _on_filter_changed(self):
        self._refresh_contracts()

    def _refresh_contracts(self):
        self.cb_contract.clear()
        aid = self.cb_airline.currentData()
        bid = self.cb_base.currentData()
        contracts = database.get_contracts(airline_id=aid, base_id=bid)
        self.contracts = contracts
        self.cb_contract.addItem("全部合同", None)
        for c in contracts:
            self.cb_contract.addItem(f"{c['airline_name']} | {c['name']}", c["id"])

    def _do_search(self):
        cid = self.cb_contract.currentData()
        aid = self.cb_airline.currentData()
        bid = self.cb_base.currentData()
        work_date = self.date_edit.date().toString("yyyy-MM-dd")
        all_risks = database.get_risks(
            airline_id=aid, base_id=bid, contract_id=cid, work_date=work_date)
        self.current_risks = [r for r in all_risks if r["work_type"] in HIGH_RISK_TYPES]
        self.current_filters = {
            "contract_id": cid,
            "work_date": work_date,
            "airline_id": aid,
            "base_id": bid,
            "airline_name": self.cb_airline.currentText(),
            "base_name": self.cb_base.currentText(),
            "contract_name": self.cb_contract.currentText(),
        }
        self._populate_table(self.current_risks)
        self._refresh_summary(self.current_risks)

    def _populate_table(self, risks):
        self.table.setRowCount(len(risks))
        for row, r in enumerate(risks):
            cols = [
                str(r["id"]),
                r["work_type"],
                r["work_location"],
                r["team_name"],
                r["status"],
                {"valid": "正常", "warning": "即将过期", "expired": "已过期"}[r["license_status"]],
                "合规" if r["scope_ok"] else "超范围⚠️",
                "是" if r["need_safety_officer"] else "否",
                "已审核" if r["reviewed"] else "待审核",
            ]
            for col, val in enumerate(cols):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 4:
                    item.setForeground(QBrush(self._status_color(r["status"])))
                if col == 5 and r["license_status"] != "valid":
                    item.setBackground(QBrush(QColor("#fef3c7" if r["license_status"] == "warning" else "#fee2e2")))
                if col == 6 and not r["scope_ok"]:
                    item.setBackground(QBrush(QColor("#fee2e2")))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                if col == 7 and r["need_safety_officer"]:
                    item.setBackground(QBrush(QColor("#ede9fe")))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                if col == 8 and not r["reviewed"]:
                    item.setForeground(QBrush(QColor("#d97706")))
                self.table.setItem(row, col, item)

    def _status_color(self, s):
        return {"未开工": QColor("#64748b"), "进行中": QColor("#0284c7"), "已关闭": QColor("#059669")}.get(s, QColor("#334155"))

    def _refresh_summary(self, risks):
        self.lbl_total.findChild(QLabel, "", Qt.FindChildrenRecursively)
        for (lbl, key, default, cond) in [
            (self.lbl_total, lambda r: True, "0", None),
            (self.lbl_high, lambda r: r["work_type"] in HIGH_RISK_TYPES, "0", None),
            (self.lbl_unreviewed, lambda r: not r["reviewed"], "0", None),
            (self.lbl_need_officer, lambda r: r["need_safety_officer"], "0", None),
        ]:
            count = sum(1 for r in risks if cond is None or key(r))
            children = lbl.findChildren(QLabel)
            if len(children) >= 2:
                children[1].setText(str(count))
            total_lbl = self.lbl_total.findChildren(QLabel)[1] if len(self.lbl_total.findChildren(QLabel)) >= 2 else None
            if total_lbl is None:
                pass

    def _on_table_double(self, idx):
        self._on_fill()

    def _on_fill(self):
        current = self.current_filters.copy()
        if not self.table.selectedItems():
            current["risk_id"] = None
            current["mode"] = "new"
        else:
            row = self.table.currentRow()
            rid = int(self.table.item(row, 0).text())
            current["risk_id"] = rid
            current["mode"] = "edit"
        self.go_to_fill.emit(current)

    def _on_report(self):
        if not self.current_risks:
            scope = []
            if self.cb_airline.currentText() != "全部航司":
                scope.append(self.cb_airline.currentText())
            if self.cb_base.currentText() != "全部基地":
                scope.append(self.cb_base.currentText())
            if self.cb_contract.currentText() != "全部合同":
                scope.append(self.cb_contract.currentText())
            scope.append(self.date_edit.date().toString("yyyy-MM-dd"))
            msg = "当前筛选条件下暂无风险记录：\n  " + " | ".join(scope) + "\n\n是否仍查看日报？"
            if QMessageBox.question(self, "提示", msg) != QMessageBox.Yes:
                return
        self.go_to_report.emit(self.current_filters)

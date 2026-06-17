from datetime import datetime, date, timedelta
from PySide6.QtCore import Qt, QDateTime, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QGroupBox,
    QTextEdit, QCheckBox, QDateTimeEdit, QSplitter, QMessageBox, QFrame,
    QListWidget, QAbstractItemView, QDialog, QDialogButtonBox
)
from PySide6.QtGui import QFont, QColor

import database

WORK_TYPES = ["喷漆作业", "打磨作业", "清洗作业", "结构拆装", "发动机维修", "起落架检修", "复合材料修复",
              "无损检测", "系统测试", "密封修复"]
STATUSES = ["未开工", "进行中", "已关闭"]
LICENSE_STATUS = [("正常 (valid)", "valid"), ("即将过期 (warning)", "warning"), ("已过期 (expired)", "expired")]
ISOLATION_OPTIONS = ["断电挂牌", "液压系统隔离", "燃油系统排空", "安全警戒带", "防火毯覆盖",
                     "区域锁闭", "气体检测", "通风设备运行", "防火设备到位", "专人监护"]


class RiskFillWindow(QWidget):
    go_back = Signal()
    go_to_report = Signal(dict)

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.current_risk_id = context.get("risk_id")
        self.mode = context.get("mode", "new")
        self.setWindowTitle("风险填报与审核 - 民航维修现场风险日报")
        self.resize(1280, 800)
        self._build_ui()
        self._load_lists()
        self._load_sidebar()
        if self.current_risk_id:
            self._load_risk(self.current_risk_id)
        else:
            self._new_risk_form()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        top_bar = QHBoxLayout()
        title = QLabel("风险填报与审核")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        top_bar.addWidget(title)

        ctx = self.context
        info = f"{ctx.get('airline_name', '全部航司')}  |  {ctx.get('base_name', '全部基地')}  |  {ctx.get('work_date', '')}"
        il = QLabel(info)
        il.setStyleSheet("color:#475569;font-size:13px;padding:4px 12px;background:#f1f5f9;border-radius:6px;")
        top_bar.addWidget(il)
        top_bar.addStretch()

        self.btn_new = QPushButton("➕ 新建风险")
        self.btn_copy = QPushButton("📋 从历史复制")
        self.btn_back = QPushButton("← 返回筛选")
        self.btn_report = QPushButton("📋 查看日报")
        for b in [self.btn_new, self.btn_copy, self.btn_back, self.btn_report]:
            b.setFixedHeight(36)
            b.setStyleSheet("""QPushButton{background:#64748b;color:white;padding:0 18px;
                border:none;border-radius:6px;font-weight:500;}QPushButton:hover{background:#475569;}""")
        self.btn_copy.setStyleSheet("""QPushButton{background:#f59e0b;color:white;padding:0 18px;
            border:none;border-radius:6px;font-weight:500;}QPushButton:hover{background:#d97706;}""")
        self.btn_report.setStyleSheet("""QPushButton{background:#0ea5e9;color:white;padding:0 18px;
            border:none;border-radius:6px;font-weight:500;}QPushButton:hover{background:#0284c7;}""")
        top_bar.addWidget(self.btn_new)
        top_bar.addWidget(self.btn_copy)
        top_bar.addWidget(self.btn_back)
        top_bar.addWidget(self.btn_report)
        root.addLayout(top_bar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left_box = QGroupBox("当日风险清单 (点击切换)")
        lb = QVBoxLayout(left_box)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setStyleSheet("""QListWidget{font-size:13px;border:1px solid #e2e8f0;border-radius:6px;}
            QListWidget::item{padding:10px;border-bottom:1px solid #f1f5f9;}
            QListWidget::item:selected{background:#dbeafe;color:#1e40af;}""")
        self.list_widget.currentItemChanged.connect(self._on_list_changed)
        lb.addWidget(self.list_widget)
        splitter.addWidget(left_box)
        splitter.setStretchFactor(0, 2)

        right_box = QGroupBox("风险详情（班组录入 / 项目经理审核）")
        rb = QVBoxLayout(right_box)

        form_area = QFrame()
        form_area.setStyleSheet("QFrame{background:#fafafa;border:1px solid #e2e8f0;border-radius:8px;}")
        form = QFormLayout(form_area)
        form.setContentsMargins(22, 20, 22, 20)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.cb_contract = QComboBox()
        self.cb_work_type = QComboBox()
        self.cb_work_type.addItems(WORK_TYPES)
        self.txt_location = QLineEdit()
        self.txt_location.setPlaceholderText("例如：机库A-03机位 / 喷漆车间 / 停机坪15号位")
        self.cb_team = QComboBox()
        self.lst_personnel = QListWidget()
        self.lst_personnel.setSelectionMode(QAbstractItemView.MultiSelection)
        self.lst_personnel.setFixedHeight(110)
        self.lst_personnel.setStyleSheet("QListWidget{border:1px solid #e2e8f0;border-radius:6px;padding:4px;}")
        self.cb_license = QComboBox()
        for display, val in LICENSE_STATUS:
            self.cb_license.addItem(display, val)

        self.gb_isolation = QGroupBox("隔离措施 (可多选)")
        self.gb_isolation.setStyleSheet("QGroupBox{font-weight:600;border:1px solid #e2e8f0;border-radius:6px;}")
        il_layout = QHBoxLayout(self.gb_isolation)
        il_layout.setContentsMargins(12, 18, 12, 12)
        self.isolation_checks = []
        col1, col2 = QVBoxLayout(), QVBoxLayout()
        for i, opt in enumerate(ISOLATION_OPTIONS):
            cb = QCheckBox(opt)
            cb.setStyleSheet("font-weight:normal;")
            self.isolation_checks.append((opt, cb))
            (col1 if i % 2 == 0 else col2).addWidget(cb)
        il_layout.addLayout(col1)
        il_layout.addLayout(col2)

        self.dt_end = QDateTimeEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.dt_end.setDateTime(QDateTime.currentDateTime().addSecs(3600 * 4))

        self.cb_status = QComboBox()
        self.cb_status.addItems(STATUSES)

        self.ck_scope = QCheckBox("作业范围符合合同要求（不勾选=超范围作业）")
        self.ck_scope.setChecked(True)
        self.ck_scope.setStyleSheet("font-size:13px;")

        self.ck_safety = QCheckBox("需客户方安全员到场监护")
        self.ck_safety.setStyleSheet("font-size:13px;")

        self.ck_reviewed = QCheckBox("项目经理已审核")
        self.ck_reviewed.setStyleSheet("font-size:13px;")

        self.txt_remarks = QTextEdit()
        self.txt_remarks.setPlaceholderText("备注 / 风险说明 / 附加要求（可选）")
        self.txt_remarks.setFixedHeight(80)

        def _field(label, widget, tip=None):
            lb = QLabel(label)
            lb.setStyleSheet("font-size:13px;font-weight:600;color:#334155;")
            if tip:
                tip_lbl = QLabel(tip)
                tip_lbl.setStyleSheet("color:#94a3b8;font-size:11px;margin-bottom:4px;")
                col = QVBoxLayout()
                col.setSpacing(3)
                col.addWidget(tip_lbl)
                col.addWidget(widget)
                form.addRow(lb, col)
            else:
                form.addRow(lb, widget)

        _field("合同项目", self.cb_contract)
        _field("高风险作业类型", self.cb_work_type)
        _field("作业位置", self.txt_location)
        _field("负责班组", self.cb_team)
        _field("参与人员 (可多选)", self.lst_personnel, "勾选参与本项作业的人员（含资质）")
        _field("许可证状态", self.cb_license)
        _field("隔离措施", self.gb_isolation)
        _field("预计结束时间", self.dt_end)
        _field("当前状态", self.cb_status)

        opts_box = QFrame()
        opts = QVBoxLayout(opts_box)
        opts.setSpacing(8)
        opts.addWidget(self.ck_scope)
        opts.addWidget(self.ck_safety)
        opts.addWidget(self.ck_reviewed)
        _field("审核选项", opts_box)
        _field("备注", self.txt_remarks)

        rb.addWidget(form_area)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_delete = QPushButton("🗑 删除此风险")
        self.btn_save = QPushButton("💾 保存")
        for b in [self.btn_delete, self.btn_save]:
            b.setFixedHeight(40)
        self.btn_delete.setStyleSheet("""QPushButton{background:#ef4444;color:white;padding:0 22px;
            border:none;border-radius:6px;font-weight:600;}QPushButton:hover{background:#dc2626;}""")
        self.btn_save.setStyleSheet("""QPushButton{background:#059669;color:white;padding:0 30px;
            border:none;border-radius:6px;font-weight:600;font-size:14px;}QPushButton:hover{background:#047857;}""")
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_save)
        rb.addLayout(btn_row)

        splitter.addWidget(right_box)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([320, 900])
        root.addWidget(splitter, 1)

        self.cb_team.currentIndexChanged.connect(self._load_personnel)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_new.clicked.connect(self._on_new)
        self.btn_copy.clicked.connect(self._on_copy_from_history)
        self.btn_back.clicked.connect(self._on_back)
        self.btn_report.clicked.connect(self._on_report)

    def _load_lists(self):
        aid = self.context.get("airline_id")
        bid = self.context.get("base_id")
        contracts = database.get_contracts(airline_id=aid, base_id=bid)
        self.contracts = contracts
        self.cb_contract.clear()
        for c in contracts:
            self.cb_contract.addItem(f"{c['airline_name']} | {c['name']} ({c['base_name']})", c["id"])
        if self.context.get("contract_id"):
            idx = self.cb_contract.findData(self.context["contract_id"])
            if idx >= 0:
                self.cb_contract.setCurrentIndex(idx)

        self.teams = database.get_teams()
        self.cb_team.clear()
        for t in self.teams:
            self.cb_team.addItem(f"{t['name']} (负责人:{t['leader']})", t["id"])

    def _load_sidebar(self):
        self.list_widget.clear()
        cid = self.context.get("contract_id")
        aid = self.context.get("airline_id")
        bid = self.context.get("base_id")
        wd = self.context.get("work_date")
        all_risks = database.get_risks(
            airline_id=aid, base_id=bid, contract_id=cid, work_date=wd)
        self.all_risks = database.filter_high_risks(all_risks)
        for r in self.all_risks:
            item = QListWidgetItem()
            status_color = {"未开工": "#64748b", "进行中": "#0284c7", "已关闭": "#059669"}[r["status"]]
            tag = "⚠️ " if (not r["scope_ok"] or r["license_status"] != "valid") else ""
            if r["need_safety_officer"]:
                tag += "🛡 "
            text = (f"{tag}【{r['work_type']}】\n"
                    f"  位置: {r['work_location']}\n"
                    f"  班组: {r['team_name']} | 状态: <span style='color:{status_color};'>{r['status']}</span>"
                    f"{' | ✅已审' if r['reviewed'] else ' | ⏳待审'}")
            item.setText(text)
            item.setData(Qt.UserRole, r["id"])
            self.list_widget.addItem(item)
        if self.current_risk_id:
            for i in range(self.list_widget.count()):
                it = self.list_widget.item(i)
                if it.data(Qt.UserRole) == self.current_risk_id:
                    self.list_widget.setCurrentRow(i)
                    break
        if self.list_widget.count() > 0 and not self.list_widget.currentItem():
            self.list_widget.setCurrentRow(0)

    def _on_list_changed(self, current, previous):
        if not current:
            return
        rid = current.data(Qt.UserRole)
        if rid:
            self.current_risk_id = rid
            self.mode = "edit"
            self._load_risk(rid)

    def _load_personnel(self):
        self.lst_personnel.clear()
        tid = self.cb_team.currentData()
        personnel = database.get_personnel(team_id=tid)
        self.all_personnel = personnel
        for p in personnel:
            days_left = (datetime.fromisoformat(p["license_expiry"]).date() - datetime.now().date()).days
            exp_warn = ""
            if days_left < 7:
                exp_warn = f" [证照{days_left}天内过期 ⚠️]"
            elif days_left < 30:
                exp_warn = f" [证照{days_left}天到期]"
            text = f"{p['name']} ({p['license_no']}) {exp_warn}\n   资质: {p['qualifications']}"
            item = QListWidgetItem(text)
            if days_left < 7:
                item.setForeground(QColor("#dc2626"))
            elif days_left < 30:
                item.setForeground(QColor("#d97706"))
            self.lst_personnel.addItem(item)

    def _load_risk(self, risk_id):
        r = database.get_risk_by_id(risk_id)
        if not r:
            return
        idx = self.cb_contract.findData(r["contract_id"])
        if idx >= 0:
            self.cb_contract.setCurrentIndex(idx)
        ti = self.cb_work_type.findText(r["work_type"])
        if ti >= 0:
            self.cb_work_type.setCurrentIndex(ti)
        else:
            self.cb_work_type.setEditText(r["work_type"])
        self.txt_location.setText(r["work_location"])

        ti = self.cb_team.findData(r["team_id"])
        if ti >= 0:
            self.cb_team.setCurrentIndex(ti)
        self._load_personnel()

        selected_ids = set(r["personnel_ids"].split(","))
        for i, p in enumerate(self.all_personnel):
            if str(p["id"]) in selected_ids:
                self.lst_personnel.item(i).setSelected(True)

        li = self.cb_license.findData(r["license_status"])
        if li >= 0:
            self.cb_license.setCurrentIndex(li)

        isolations = set(r["isolation_measures"].split("、"))
        for opt, cb in self.isolation_checks:
            cb.setChecked(opt in isolations)

        if r["est_end_time"]:
            self.dt_end.setDateTime(QDateTime.fromString(r["est_end_time"], "yyyy-MM-dd HH:mm"))
        si = self.cb_status.findText(r["status"])
        if si >= 0:
            self.cb_status.setCurrentIndex(si)
        self.ck_scope.setChecked(bool(r["scope_ok"]))
        self.ck_safety.setChecked(bool(r["need_safety_officer"]))
        self.ck_reviewed.setChecked(bool(r["reviewed"]))
        self.txt_remarks.setPlainText(r["remarks"] or "")

    def _new_risk_form(self):
        self.current_risk_id = None
        self.mode = "new"
        self._load_personnel()
        for _, cb in self.isolation_checks:
            cb.setChecked(False)
        self.txt_location.clear()
        self.txt_remarks.clear()
        self.ck_scope.setChecked(True)
        self.ck_safety.setChecked(False)
        self.ck_reviewed.setChecked(False)
        self.dt_end.setDateTime(QDateTime.currentDateTime().addSecs(3600 * 4))

    def _collect_form(self):
        cid = self.cb_contract.currentData()
        if not cid:
            raise ValueError("请选择合同项目")
        work_type = self.cb_work_type.currentText().strip()
        if not work_type:
            raise ValueError("请填写作业类型")
        loc = self.txt_location.text().strip()
        if not loc:
            raise ValueError("请填写作业位置")
        tid = self.cb_team.currentData()

        selected_items = self.lst_personnel.selectedItems()
        if not selected_items:
            raise ValueError("请至少选择一名参与人员")

        selected_names = [it.text().split(" (")[0] for it in selected_items]
        selected_personnel = [p for p in self.all_personnel if p["name"] in selected_names]
        selected_ids = [str(p["id"]) for p in selected_personnel]

        today = datetime.now().date()
        license_status = self.cb_license.currentData()
        mismatches = []
        for p in selected_personnel:
            exp = datetime.fromisoformat(p["license_expiry"]).date()
            days_left = (exp - today).days
            if days_left < 0:
                license_status = "expired"
                mismatches.append(f"{p['name']}证照已过期")
            elif days_left < 7 and license_status == "valid":
                license_status = "warning"
            if "喷漆" in work_type and "喷漆" not in p["qualifications"]:
                mismatches.append(f"{p['name']}缺少喷漆资质")
            if "打磨" in work_type and "打磨" not in p["qualifications"]:
                mismatches.append(f"{p['name']}缺少打磨资质")
            if ("结构" in work_type or "复材" in work_type) and "结构维修" not in p["qualifications"] and "复材" not in p["qualifications"]:
                mismatches.append(f"{p['name']}缺少结构/复材维修资质")

        isolations = [opt for opt, cb in self.isolation_checks if cb.isChecked()]
        if not isolations:
            raise ValueError("请至少选择一项隔离措施")

        return {
            "contract_id": cid,
            "work_date": self.context.get("work_date") or datetime.now().date().isoformat(),
            "work_type": work_type,
            "work_location": loc,
            "team_id": tid,
            "personnel_ids": ",".join(selected_ids),
            "license_status": license_status,
            "isolation_measures": "、".join(isolations),
            "est_end_time": self.dt_end.dateTime().toString("yyyy-MM-dd HH:mm"),
            "status": self.cb_status.currentText(),
            "scope_ok": 1 if self.ck_scope.isChecked() else 0,
            "need_safety_officer": 1 if self.ck_safety.isChecked() else 0,
            "reviewed": 1 if self.ck_reviewed.isChecked() else 0,
            "remarks": self.txt_remarks.toPlainText().strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "_mismatches": mismatches
        }

    def _on_save(self):
        try:
            data = self._collect_form()
        except ValueError as e:
            QMessageBox.warning(self, "信息不完整", str(e))
            return
        mismatches = data.pop("_mismatches")
        if mismatches and not data["reviewed"]:
            resp = QMessageBox.question(self, "资质/证照提示",
                                        "检测到以下问题：\n- " + "\n- ".join(mismatches) +
                                        "\n\n是否仍然继续保存？",
                                        QMessageBox.Yes | QMessageBox.No)
            if resp != QMessageBox.Yes:
                return
        if self.mode == "new":
            rid = database.insert_risk(data)
            self.current_risk_id = rid
            self.mode = "edit"
            QMessageBox.information(self, "保存成功", f"新建风险记录 #{rid} 已保存。")
        else:
            data.pop("created_at")
            database.update_risk(self.current_risk_id, data)
            QMessageBox.information(self, "保存成功", f"风险记录 #{self.current_risk_id} 已更新。")
        self._load_sidebar()
        if self.current_risk_id:
            for i in range(self.list_widget.count()):
                it = self.list_widget.item(i)
                if it.data(Qt.UserRole) == self.current_risk_id:
                    self.list_widget.setCurrentRow(i)
                    break

    def _on_delete(self):
        if not self.current_risk_id:
            return
        if QMessageBox.question(self, "删除确认",
                                f"确定要删除风险记录 #{self.current_risk_id} 吗？",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        conn = database.get_conn()
        conn.execute("DELETE FROM risks WHERE id = ?", (self.current_risk_id,))
        conn.commit()
        conn.close()
        self.current_risk_id = None
        self._load_sidebar()
        self._new_risk_form()

    def _on_new(self):
        self.list_widget.clearSelection()
        self.current_risk_id = None
        self.mode = "new"
        self._new_risk_form()

    def _on_back(self):
        if self.go_back is not None:
            self.go_back.emit()

    def _on_report(self):
        if self.go_to_report is not None:
            self.go_to_report.emit(self.context)

    def _on_copy_from_history(self):
        aid = self.context.get("airline_id")
        bid = self.context.get("base_id")
        cid = self.context.get("contract_id")
        wd = self.context.get("work_date")
        today = date.fromisoformat(wd) if wd else date.today()
        start_date = (today - timedelta(days=30))
        history = []
        all_hist = []
        for d in range(1, 31):
            dd = (today - timedelta(days=d))
            rs = database.get_risks(airline_id=aid, base_id=bid, contract_id=cid, work_date=dd.isoformat())
            history.extend(rs)
        history = database.filter_high_risks(history)
        if not history:
            QMessageBox.information(self, "历史复制",
                "当前筛选范围近30天内没有可复制的高风险历史作业。")
            return
        dlg = _HistoryPickerDialog(self, history)
        if dlg.exec() == QDialog.Accepted and dlg.selected_risk:
            src = dlg.selected_risk
            self.current_risk_id = None
            self.mode = "new"
            idx = self.cb_contract.findData(src["contract_id"])
            if idx >= 0:
                self.cb_contract.setCurrentIndex(idx)
            ti = self.cb_work_type.findText(src["work_type"])
            if ti >= 0:
                self.cb_work_type.setCurrentIndex(ti)
            else:
                self.cb_work_type.setEditText(src["work_type"])
            self.txt_location.setText(src["work_location"])
            ti = self.cb_team.findData(src["team_id"])
            if ti >= 0:
                self.cb_team.setCurrentIndex(ti)
            self._load_personnel()
            isolations = set(src["isolation_measures"].split("、"))
            for opt, cb in self.isolation_checks:
                cb.setChecked(opt in isolations)
            self.txt_remarks.setPlainText(src["remarks"] or "")
            self.ck_scope.setChecked(bool(src["scope_ok"]))
            self.ck_safety.setChecked(bool(src["need_safety_officer"]))
            self.ck_reviewed.setChecked(False)
            self.cb_status.setCurrentText("未开工")
            self.dt_end.setDateTime(QDateTime.currentDateTime().addSecs(3600 * 4))
            QMessageBox.information(self, "复制成功",
                f"已从历史作业 #{src['id']} 复制：\n"
                f"  作业类型：{src['work_type']}（{src['work_date']}）\n"
                f"  位置：{src['work_location']}\n"
                f"  班组：{src.get('team_name', '')}\n\n"
                f"请确认人员、时间、许可证状态。")


class _HistoryPickerDialog(QDialog):
    def __init__(self, parent, history):
        super().__init__(parent)
        self.setWindowTitle("选择要复制的历史作业")
        self.resize(780, 560)
        self.selected_risk = None

        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)

        info = QLabel(f"共找到近30天内 {len(history)} 条高风险历史作业，请选择一条作为模板：")
        info.setStyleSheet("font-size:13px;")
        v.addWidget(info)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""QListWidget{font-size:13px;border:1px solid #e2e8f0;border-radius:6px;}
            QListWidget::item{padding:10px;border-bottom:1px solid #f1f5f9;}
            QListWidget::item:selected{background:#dbeafe;color:#1e40af;}""")
        self._populate(history)
        self.list_widget.itemDoubleClicked.connect(lambda _: self._on_ok())
        v.addWidget(self.list_widget, 1)

        hint = QLabel("提示：双击列表项或选中后点「确定」，快速套用（人员和时间需要自己改）")
        hint.setStyleSheet("color:#64748b;font-size:12px;")
        v.addWidget(hint)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("确定复制")
        bb.button(QDialogButtonBox.Cancel).setText("取消")
        bb.button(QDialogButtonBox.Ok).setStyleSheet("background:#059669;color:white;padding:8px 20px;border:none;border-radius:6px;font-weight:600;")
        bb.button(QDialogButtonBox.Cancel).setStyleSheet("background:#94a3b8;color:white;padding:8px 20px;border:none;border-radius:6px;")
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _populate(self, history):
        for r in history:
            it = QListWidgetItem()
            tag = "⚠️" if (not r["scope_ok"] or r["license_status"] != "valid") else ""
            text = (f"{tag} 【{r['work_date']}】{r['work_type']}\n"
                    f"      位置: {r['work_location']}  |  班组: {r['team_name']}\n"
                    f"      隔离: {r['isolation_measures']}"
                    f"{'  | 需安全员' if r['need_safety_officer'] else ''}")
            it.setText(text)
            it.setData(Qt.UserRole, r)
            self.list_widget.addItem(it)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _on_ok(self):
        it = self.list_widget.currentItem()
        if it:
            self.selected_risk = it.data(Qt.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, "提示", "请先选择一条历史作业。")

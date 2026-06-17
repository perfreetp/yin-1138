import database
from datetime import datetime, date, timedelta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QGroupBox,
    QPushButton, QScrollArea, QFrame, QGridLayout, QListWidget, QListWidgetItem,
    QMessageBox, QSplitter, QSizePolicy, QTextEdit, QApplication
)
from PySide6.QtGui import QFont, QColor, QBrush, QPalette


class ReviewWindow(QWidget):
    go_back = Signal()
    go_to_risk = Signal(int, dict)

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.setWindowTitle("📊 会议复盘视图 - 跟进事项闭环跟踪")
        self.resize(1380, 900)
        self._build_ui()
        self._load_all()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        top_bar = QHBoxLayout()
        title = QLabel("📊 会议复盘 · 跟进事项闭环跟踪")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.btn_back = QPushButton("← 返回日报")
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_export = QPushButton("📋 复制复盘报告")
        for b in [self.btn_back, self.btn_refresh, self.btn_export]:
            b.setFixedHeight(38)
            b.setStyleSheet("""QPushButton{background:#64748b;color:white;padding:0 18px;
                border:none;border-radius:6px;font-weight:500;font-size:13px;}
                QPushButton:hover{background:#475569;}""")
        self.btn_export.setStyleSheet("""QPushButton{background:#0891b2;color:white;padding:0 18px;
            border:none;border-radius:6px;font-weight:500;font-size:13px;}
            QPushButton:hover{background:#0e7490;}""")
        top_bar.addWidget(self.btn_refresh)
        top_bar.addWidget(self.btn_export)
        top_bar.addWidget(self.btn_back)
        root.addLayout(top_bar)

        filter_box = QGroupBox("🔍 筛选条件（按组合筛选，未关闭事项默认前置）")
        fl = QHBoxLayout(filter_box)
        fl.setContentsMargins(14, 14, 14, 14)
        fl.setSpacing(10)

        self.cb_airline = QComboBox()
        self.cb_base = QComboBox()
        self.cb_contract = QComboBox()
        self.cb_responsible = QComboBox()
        self.cb_status = QComboBox()
        self.cb_deadline = QComboBox()
        self.cb_deadline.addItems([
            "全部到期状态", "🚨 已逾期", "🔴 今天到期", "🟠 本周到期", "🟢 7天以上", "⚪ 未设计划"
        ])

        for cb in [self.cb_airline, self.cb_base, self.cb_contract,
                   self.cb_responsible, self.cb_status, self.cb_deadline]:
            cb.setFixedHeight(34)
            cb.setStyleSheet("font-size:13px;padding:4px 10px;")

        self._populate_filters()
        for (label, cb) in [
            ("航司", self.cb_airline), ("基地", self.cb_base), ("合同", self.cb_contract),
            ("责任方", self.cb_responsible), ("状态", self.cb_status), ("到期", self.cb_deadline)
        ]:
            col = QVBoxLayout()
            ll = QLabel(label)
            ll.setStyleSheet("font-size:12px;color:#475569;font-weight:600;")
            col.addWidget(ll)
            col.addWidget(cb)
            fl.addLayout(col)

        self.btn_apply = QPushButton("应用筛选")
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.setStyleSheet("""QPushButton{background:#2563eb;color:white;padding:0 18px;
            border:none;border-radius:6px;font-weight:600;font-size:13px;}
            QPushButton:hover{background:#1d4ed8;}""")
        col = QVBoxLayout()
        ll = QLabel(" ")
        col.addWidget(ll)
        col.addWidget(self.btn_apply)
        fl.addLayout(col)
        root.addWidget(filter_box)

        summary_bar = QHBoxLayout()
        self.summary_labels = {}
        for key, (label, color) in {
            "total": ("跟进总数", "#0f172a"),
            "open": ("未关闭", "#dc2626"),
            "overdue": ("已逾期", "#991b1b"),
            "today": ("今天到期", "#dc2626"),
            "week": ("本周到期", "#d97706"),
            "done": ("已完成", "#059669"),
        }.items():
            card = QFrame()
            card.setStyleSheet(f"QFrame{{background:#fafafa;border:1px solid #e2e8f0;border-radius:8px;}}")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(14, 10, 14, 10)
            ll = QLabel(label)
            ll.setStyleSheet("color:#64748b;font-size:12px;")
            val = QLabel("0")
            val.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
            val.setStyleSheet(f"color:{color};")
            lay.addWidget(ll)
            lay.addWidget(val)
            self.summary_labels[key] = val
            summary_bar.addWidget(card)
        root.addLayout(summary_bar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        left = QFrame()
        left.setStyleSheet("QFrame{background:white;border:1px solid #e2e8f0;border-radius:8px;}")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 12, 12, 12)
        ll.setSpacing(8)
        left_head = QLabel("📋 跟进事项清单（点击查看详情）")
        left_head.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        ll.addWidget(left_head)

        self.left_list = QListWidget()
        self.left_list.setStyleSheet("""QListWidget{font-size:13px;border:1px solid #e2e8f0;border-radius:6px;}
            QListWidget::item{padding:10px;border-bottom:1px solid #f1f5f9;}
            QListWidget::item:selected{background:#dbeafe;color:#1e3a8a;}""")
        self.left_list.currentItemChanged.connect(self._on_item_selected)
        ll.addWidget(self.left_list, 1)
        splitter.addWidget(left)

        right = QFrame()
        right.setStyleSheet("QFrame{background:white;border:1px solid #e2e8f0;border-radius:8px;}")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 14, 16, 14)
        rl.setSpacing(10)
        right_head = QLabel("🔎 事项详情")
        right_head.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        rl.addWidget(right_head)

        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setStyleSheet("""QTextEdit{border:1px solid #e2e8f0;border-radius:6px;
            background:#fafafa;font-size:13px;padding:10px;}""")
        rl.addWidget(self.detail_view, 1)

        op_row = QHBoxLayout()
        self.btn_edit = QPushButton("✏️ 编辑状态")
        self.btn_done = QPushButton("✅ 标记完成")
        self.btn_jump = QPushButton("🔗 跳转到关联风险")
        for b in [self.btn_edit, self.btn_done, self.btn_jump]:
            b.setFixedHeight(34)
            b.setStyleSheet("""QPushButton{background:#475569;color:white;padding:0 16px;
                border:none;border-radius:6px;font-weight:500;font-size:12px;}
                QPushButton:hover{background:#334155;}""")
        self.btn_done.setStyleSheet("""QPushButton{background:#059669;color:white;padding:0 16px;
            border:none;border-radius:6px;font-weight:500;font-size:12px;}
            QPushButton:hover{background:#047857;}""")
        self.btn_jump.setStyleSheet("""QPushButton{background:#2563eb;color:white;padding:0 16px;
            border:none;border-radius:6px;font-weight:500;font-size:12px;}
            QPushButton:hover{background:#1d4ed8;}""")
        op_row.addWidget(self.btn_edit)
        op_row.addWidget(self.btn_done)
        op_row.addWidget(self.btn_jump)
        op_row.addStretch()
        rl.addLayout(op_row)
        splitter.addWidget(right)
        root.addWidget(splitter, 1)

        self.btn_back.clicked.connect(self.go_back.emit)
        self.btn_refresh.clicked.connect(self._load_all)
        self.btn_apply.clicked.connect(self._load_list)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_edit.clicked.connect(self._on_edit_status)
        self.btn_done.clicked.connect(self._on_done)
        self.btn_jump.clicked.connect(self._on_jump_risk)

    def _populate_filters(self):
        self.cb_airline.addItem("全部航司", None)
        for a in database.get_airlines():
            self.cb_airline.addItem(a["name"], a["id"])
        self.cb_base.addItem("全部基地", None)
        for b in database.get_bases():
            self.cb_base.addItem(b["name"], b["id"])
        self.cb_contract.addItem("全部合同", None)
        for c in database.get_contracts():
            self.cb_contract.addItem(c["name"], c["id"])
        self.cb_status.addItem("全部状态", None)
        for s in ["待处理", "进行中", "已完成", "已逾期"]:
            self.cb_status.addItem(s, s)
        self.cb_responsible.addItem("全部责任方", None)
        seen = set()
        for fu in database.get_follow_ups():
            if fu["responsible"] and fu["responsible"] not in seen:
                self.cb_responsible.addItem(fu["responsible"], fu["responsible"])
                seen.add(fu["responsible"])

    def _get_filters(self):
        return {
            "airline_id": self.cb_airline.currentData(),
            "base_id": self.cb_base.currentData(),
            "contract_id": self.cb_contract.currentData(),
            "status": self.cb_status.currentData(),
            "responsible": self.cb_responsible.currentData(),
            "deadline_idx": self.cb_deadline.currentIndex(),
        }

    def _load_all(self):
        self._load_list()
        self._load_summary()

    def _deadline_tag(self, fu, today):
        if not fu.get("planned_date"):
            return "⚪", "未设计划", 999
        pd = date.fromisoformat(fu["planned_date"])
        days = (pd - today).days
        if fu["status"] == "已完成":
            return "✅", "已完成", 500
        if fu["status"] == "已逾期" or days < 0:
            return "🚨", f"逾期{abs(days)}天", -abs(days)
        if days == 0:
            return "🔴", "今天到期", 0
        if days <= 7:
            return "🟠", f"本周到期({days}天)", days
        return "🟢", f"计划{pd.isoformat()}", days

    def _load_list(self):
        filters = self._get_filters()
        aid = filters["airline_id"]
        bid = filters["base_id"]
        cid = filters["contract_id"]
        status = filters["status"]
        all_fus = database.get_follow_ups(airline_id=aid, base_id=bid, contract_id=cid, status=status)
        if filters["responsible"]:
            all_fus = [f for f in all_fus if f["responsible"] == filters["responsible"]]
        today = date.today()
        deadline_idx = filters["deadline_idx"]
        if deadline_idx != 0:
            def _match(fu):
                _, _, sort_k = self._deadline_tag(fu, today)
                if deadline_idx == 1:
                    return fu["status"] == "已逾期" or (fu["status"] != "已完成" and sort_k < 0)
                elif deadline_idx == 2:
                    return sort_k == 0 and fu["status"] != "已完成"
                elif deadline_idx == 3:
                    return 0 < sort_k <= 7 and fu["status"] != "已完成"
                elif deadline_idx == 4:
                    return sort_k > 7 and fu["status"] != "已完成"
                elif deadline_idx == 5:
                    return not fu.get("planned_date")
                return True
            all_fus = [f for f in all_fus if _match(f)]

        def _sort_key(fu):
            _, _, k = self._deadline_tag(fu, today)
            done_first = 0 if fu["status"] in ("待处理", "进行中", "已逾期") else 1
            return (done_first, k, fu["id"])

        all_fus.sort(key=_sort_key)
        self.current_fus = all_fus
        self.left_list.clear()
        for fu in all_fus:
            icon, desc, _ = self._deadline_tag(fu, today)
            scope_name = fu.get("airline_name") or fu.get("base_name") or "全局"
            it = QListWidgetItem()
            title = (
                f"{icon} {desc}  |  [{fu['follow_type']}]  状态：{fu['status']}\n"
                f"     {fu['title']}\n"
                f"     责任方：{fu['responsible']}  |  来源：{fu['work_date']}  |  范围：{scope_name}"
            )
            if fu["status"] == "已完成":
                it.setForeground(QBrush(QColor("#64748b")))
            elif fu["status"] == "已逾期" or (fu.get("planned_date") and date.fromisoformat(fu["planned_date"]) < today):
                it.setForeground(QBrush(QColor("#dc2626")))
                f = it.font()
                f.setBold(True)
                it.setFont(f)
            it.setText(title)
            it.setData(Qt.UserRole, fu)
            self.left_list.addItem(it)
        if self.left_list.count() > 0:
            self.left_list.setCurrentRow(0)
        else:
            self.detail_view.setHtml("<div style='color:#64748b;padding:20px;'>当前筛选条件下无跟进事项。</div>")

    def _load_summary(self):
        all_fus = database.get_follow_ups()
        today = date.today()
        keys = {
            "total": len(all_fus),
            "open": sum(1 for f in all_fus if f["status"] in ("待处理", "进行中", "已逾期")),
            "overdue": sum(1 for f in all_fus if f["status"] == "已逾期" or (f["status"] != "已完成" and f.get("planned_date") and date.fromisoformat(f["planned_date"]) < today)),
            "today": sum(1 for f in all_fus if f.get("planned_date") and date.fromisoformat(f["planned_date"]) == today and f["status"] != "已完成"),
            "week": sum(1 for f in all_fus if f.get("planned_date") and 0 < (date.fromisoformat(f["planned_date"]) - today).days <= 7 and f["status"] != "已完成"),
            "done": sum(1 for f in all_fus if f["status"] == "已完成"),
        }
        for k, v in keys.items():
            self.summary_labels[k].setText(str(v))

    def _on_item_selected(self, item):
        if not item:
            return
        fu = item.data(Qt.UserRole)
        if not fu:
            return
        today = date.today()
        icon, desc, days = self._deadline_tag(fu, today)
        scope_parts = []
        if fu.get("airline_name"):
            scope_parts.append(f"航司：{fu['airline_name']}")
        if fu.get("base_name"):
            scope_parts.append(f"基地：fu['base_name']")
        if fu.get("contract_name"):
            scope_parts.append(f"合同：{fu['contract_name']}")
        scope = " | ".join(scope_parts) if scope_parts else "全局"

        risk_info = ""
        if fu.get("risk_id"):
            r = database.get_risk_by_id(fu["risk_id"])
            if r:
                personnel = database.get_personnel()
                pids = r["personnel_ids"].split(",") if r["personnel_ids"] else []
                chosen = [p["name"] for p in personnel if str(p["id"]) in pids]
                risk_info = f"""
                <div style='margin-top:14px;padding:12px;background:#eff6ff;border-radius:8px;
                            border-left:4px solid #3b82f6;'>
                  <div style='font-weight:700;color:#1e40af;margin-bottom:8px;'>🔗 关联风险信息</div>
                  <div><b>风险 #{r['id']}　{r['work_type']}</b></div>
                  <div>作业位置：{r['work_location']}</div>
                  <div>所在合同：{r.get('contract_name', '-')}</div>
                  <div>负责班组：{r.get('team_name', '-')}</div>
                  <div>参与人员：{'、'.join(chosen) if chosen else '（未填）'}</div>
                  <div>隔离措施：{r['isolation_measures']}</div>
                  <div>当前状态：{r['status']}　|　许可证状态：{r['license_status']}　|　需安全员：{'是' if r['need_safety_officer'] else '否'}</div>
                  <div>项目经理审核：{'✅ 已审核' if r['reviewed'] else '⚠️ 未审核'}　|　范围合规：{'✅ 合规' if r['scope_ok'] else '🚨 超范围'}</div>
                  <div>预计关闭：{r['est_end_time'] or '（未设）'}</div>
                  <div>创建时间：{r['created_at']}</div>
                </div>
                """

        closed_at = fu.get("closed_at") or "（未关闭）"
        status_colors = {"待处理":"#92400e","进行中":"#1e40af","已完成":"#166534","已逾期":"#991b1b"}
        sc = status_colors.get(fu["status"], "#334155")
        html = f"""
        <div style='font-family:"Microsoft YaHei";line-height:1.9;font-size:13px;'>
          <div style='font-size:16px;font-weight:700;color:#0f172a;margin-bottom:8px;'>
            {icon} {desc}　<span style='color:{sc}'>[{fu['status']}]</span>
          </div>
          <div style='background:#f8fafc;padding:10px 14px;border-radius:6px;margin-bottom:10px;'>
            <b>跟进类型：</b>{fu['follow_type']}<br/>
            <b>跟进事项：</b>{fu['title']}<br/>
            <b>具体动作：</b>{fu['action']}<br/>
            <b>责任方：</b>{fu['responsible']}<br/>
            <b>计划完成：</b>{fu.get('planned_date') or '（未设）'}<br/>
            <b>来源日期：</b>{fu['work_date']}<br/>
            <b>数据范围：</b>{scope}<br/>
            <b>创建时间：</b>{fu['created_at']}<br/>
            <b>关闭时间：</b>{closed_at}
          </div>
          <div style='padding:10px 14px;background:#fef3c7;border-radius:6px;
                      border-left:4px solid #f59e0b;'>
            <div style='font-weight:600;color:#92400e;margin-bottom:4px;'>📝 上次会议留下的动作</div>
            <div>{fu['action']}</div>
            <div style='margin-top:6px;color:#78350f;font-size:12px;'>
              来源会议日期：{fu['work_date']}　|　责任方：{fu['responsible']}
            </div>
          </div>
          {risk_info}
        </div>
        """
        html = html.replace("fu['base_name']", fu.get('base_name') or "")
        self.detail_view.setHtml(html)

    def _get_selected_fu(self):
        it = self.left_list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _on_edit_status(self):
        fu = self._get_selected_fu()
        if not fu:
            QMessageBox.warning(self, "提示", "请先选择一条跟进事项。")
            return
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QComboBox, QLabel, QFormLayout
        dlg = QDialog(self)
        dlg.setWindowTitle(f"修改跟进 #{fu['id']} 状态")
        dlg.resize(400, 200)
        dv = QVBoxLayout(dlg)
        dv.setContentsMargins(18, 16, 18, 16)
        form = QFormLayout()
        cb = QComboBox()
        cb.addItems(["待处理", "进行中", "已完成", "已逾期"])
        si = cb.findText(fu["status"])
        if si >= 0:
            cb.setCurrentIndex(si)
        lb = QLabel(fu["title"])
        lb.setStyleSheet("color:#475569;padding:8px;background:#f8fafc;border-radius:6px;")
        lb.setWordWrap(True)
        form.addRow("跟进事项：", lb)
        form.addRow("处理状态：", cb)
        dv.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("保存")
        bb.button(QDialogButtonBox.Cancel).setText("取消")
        bb.button(QDialogButtonBox.Ok).setStyleSheet("background:#059669;color:white;padding:8px 24px;border:none;border-radius:6px;font-weight:600;")
        bb.button(QDialogButtonBox.Cancel).setStyleSheet("background:#94a3b8;color:white;padding:8px 24px;border:none;border-radius:6px;")
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        dv.addWidget(bb)
        if dlg.exec() == QDialog.Accepted:
            new_status = cb.currentText()
            data = {"status": new_status}
            if new_status == "已完成":
                data["closed_at"] = datetime.now().isoformat(timespec="seconds")
            database.update_follow_up(fu["id"], data)
            self._load_all()
            QMessageBox.information(self, "更新成功", f"跟进 #{fu['id']} 状态已更新为「{new_status}」")

    def _on_done(self):
        fu = self._get_selected_fu()
        if not fu:
            QMessageBox.warning(self, "提示", "请先选择一条跟进事项。")
            return
        database.update_follow_up(fu["id"], {
            "status": "已完成",
            "closed_at": datetime.now().isoformat(timespec="seconds"),
        })
        self._load_all()
        QMessageBox.information(self, "已完成", f"跟进 #{fu['id']} 已标记完成。")

    def _on_jump_risk(self):
        fu = self._get_selected_fu()
        if not fu or not fu.get("risk_id"):
            QMessageBox.information(self, "提示", "该跟进项未关联风险记录。")
            return
        ctx = dict(self.context)
        ctx["work_date"] = fu["work_date"]
        if fu.get("airline_id"):
            ctx["airline_id"] = fu["airline_id"]
        if fu.get("base_id"):
            ctx["base_id"] = fu["base_id"]
        if fu.get("contract_id"):
            ctx["contract_id"] = fu["contract_id"]
        self.go_to_risk.emit(fu["risk_id"], ctx)

    def _on_export(self):
        lines = []
        today = date.today()
        lines.append("=" * 70)
        lines.append("民 航 维 修 外 包 承 包 商 · 会 议 复 盘 报 告")
        lines.append("=" * 70)
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"基准日期：{today.isoformat()}")
        lines.append("")

        lines.append("一、整体闭环情况")
        lines.append("-" * 70)
        lines.append(f"  跟进事项总数：{self.summary_labels['total'].text()} 项")
        lines.append(f"    · 未关闭：{self.summary_labels['open'].text()} 项")
        lines.append(f"    · 已逾期：{self.summary_labels['overdue'].text()} 项")
        lines.append(f"    · 今天到期：{self.summary_labels['today'].text()} 项")
        lines.append(f"    · 本周到期：{self.summary_labels['week'].text()} 项")
        lines.append(f"    · 已完成：{self.summary_labels['done'].text()} 项")
        lines.append("")

        lines.append("二、按到期时间分布")
        lines.append("-" * 70)
        for section_name, section_color, check_fn in [
            ("🚨 已逾期事项", "#dc2626", lambda fu, t: fu["status"] == "已逾期" or (fu["status"] != "已完成" and fu.get("planned_date") and date.fromisoformat(fu["planned_date"]) < t)),
            ("🔴 今天到期", "#dc2626", lambda fu, t: fu.get("planned_date") and date.fromisoformat(fu["planned_date"]) == t and fu["status"] != "已完成"),
            ("🟠 本周到期", "#d97706", lambda fu, t: fu.get("planned_date") and 0 < (date.fromisoformat(fu["planned_date"]) - t).days <= 7 and fu["status"] != "已完成"),
            ("⚪ 未设计划", "#64748b", lambda fu, t: not fu.get("planned_date") and fu["status"] != "已完成"),
            ("✅ 已完成", "#059669", lambda fu, t: fu["status"] == "已完成"),
        ]:
            items = [f for f in self.current_fus if check_fn(f, today)]
            lines.append(f"  {section_name}（{len(items)} 项）")
            if not items:
                lines.append("    （无）")
            for idx, fu in enumerate(items, 1):
                lines.append(f"    {idx}. [{fu['status']}] {fu['title']}")
                lines.append(f"       动作：{fu['action']}")
                lines.append(f"       责任方：{fu['responsible']}　计划：{fu.get('planned_date') or '（未设）'}　来源：{fu['work_date']}")
                if fu.get("risk_id"):
                    lines.append(f"       关联风险：#{fu['risk_id']}")
            lines.append("")

        lines.append("三、按责任方分布（供各责任人核对）")
        lines.append("-" * 70)
        by_resp = {}
        for fu in self.current_fus:
            by_resp.setdefault(fu["responsible"], []).append(fu)
        for resp, items in sorted(by_resp.items(), key=lambda x: -len(x[1])):
            open_cnt = sum(1 for f in items if f["status"] != "已完成")
            lines.append(f"  ▸ {resp}：共 {len(items)} 项（未关闭 {open_cnt} 项）")
            for fu in items:
                icon, desc, _ = self._deadline_tag(fu, today)
                lines.append(f"      {icon} [{fu['status']}] {fu['title']}")
                lines.append(f"         动作：{fu['action']}　计划：{fu.get('planned_date') or '（未设）'}")
            lines.append("")

        lines.append("=" * 70)
        lines.append(f"报告生成：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 70)
        cb = QApplication.clipboard()
        cb.setText("\n".join(lines))
        QMessageBox.information(self, "复制成功",
            "复盘报告已复制到剪贴板，共包含"
            f" {len(self.current_fus)} 条跟进事项。")

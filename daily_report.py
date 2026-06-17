from datetime import datetime, date
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QPushButton, QGroupBox, QGridLayout, QMessageBox, QSizePolicy,
    QTextEdit, QApplication, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDateEdit, QAbstractItemView, QDialog, QDialogButtonBox,
    QLineEdit, QFormLayout
)
from PySide6.QtGui import QFont, QColor, QBrush, QGuiApplication

import database


class DailyReportWindow(QWidget):
    go_back = Signal()
    go_to_fill = Signal(dict)
    go_to_review = Signal(dict)

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.setWindowTitle("风险日报看板 - 民航维修现场风险日报")
        self.resize(1360, 860)
        self._build_ui()
        self._load_and_render()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        top_bar = QHBoxLayout()
        title = QLabel("📋 风险日报看板")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        top_bar.addWidget(title)

        ctx = self.context
        self.info_label = QLabel(f"  客户：{ctx.get('airline_name', '全部航司')}  |  基地：{ctx.get('base_name', '全部基地')}  |  合同：{ctx.get('contract_name', '全部合同')}  |  日期：{ctx.get('work_date', '')}")
        self.info_label.setStyleSheet("color:#475569;font-size:13px;padding:6px 14px;background:#f1f5f9;border-radius:8px;")
        top_bar.addWidget(self.info_label)
        top_bar.addStretch()

        self.btn_fill = QPushButton("✏️ 编辑风险")
        self.btn_back = QPushButton("← 返回筛选")
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_export = QPushButton("📄 复制日报文本")
        self.btn_export_todo = QPushButton("📋 复制责任方待办")
        self.btn_review = QPushButton("📊 复盘视图")
        for b in [self.btn_fill, self.btn_back, self.btn_refresh, self.btn_export, self.btn_export_todo, self.btn_review]:
            b.setFixedHeight(38)
            b.setStyleSheet("""QPushButton{background:#64748b;color:white;padding:0 18px;
                border:none;border-radius:6px;font-weight:500;font-size:13px;}
                QPushButton:hover{background:#475569;}""")
        self.btn_export.setStyleSheet("""QPushButton{background:#7c3aed;color:white;padding:0 18px;
            border:none;border-radius:6px;font-weight:500;font-size:13px;}
            QPushButton:hover{background:#6d28d9;}""")
        self.btn_export_todo.setStyleSheet("""QPushButton{background:#0891b2;color:white;padding:0 18px;
            border:none;border-radius:6px;font-weight:500;font-size:13px;}
            QPushButton:hover{background:#0e7490;}""")
        self.btn_review.setStyleSheet("""QPushButton{background:#4f46e5;color:white;padding:0 18px;
            border:none;border-radius:6px;font-weight:500;font-size:13px;}
            QPushButton:hover{background:#4338ca;}""")
        top_bar.addWidget(self.btn_refresh)
        top_bar.addWidget(self.btn_review)
        top_bar.addWidget(self.btn_fill)
        top_bar.addWidget(self.btn_export_todo)
        top_bar.addWidget(self.btn_export)
        top_bar.addWidget(self.btn_back)
        root.addLayout(top_bar)

        self.drill_bar = QHBoxLayout()
        self.drill_label = QLabel("🎯 当前视图：总览")
        self.drill_label.setStyleSheet("font-size:13px;font-weight:600;color:#0f172a;padding:6px 12px;background:#e0f2fe;border-radius:6px;")
        self.drill_bar.addWidget(self.drill_label)
        self.drill_bar.addStretch()
        self.btn_back_overview = QPushButton("↩ 一键回到总览")
        self.btn_back_overview.setFixedHeight(34)
        self.btn_back_overview.setStyleSheet("""QPushButton{background:#0284c7;color:white;padding:0 16px;
            border:none;border-radius:6px;font-weight:500;font-size:12px;}QPushButton:hover{background:#0369a1;}""")
        self.btn_back_overview.clicked.connect(self._back_to_overview)
        self.drill_bar.addWidget(self.btn_back_overview)
        self.drill_widget = QWidget()
        self.drill_widget.setLayout(self.drill_bar)
        root.addWidget(self.drill_widget)

        overview_box = QGroupBox("📌 今日概览 · 给协调会快速说明")
        overview_layout = QHBoxLayout(overview_box)
        overview_layout.setContentsMargins(18, 18, 18, 18)
        overview_layout.setSpacing(14)

        self.stats = {}
        for key, (label, color) in {
            "total": ("风险总数", "#0f172a"),
            "not_started": ("未开工", "#64748b"),
            "in_progress": ("进行中", "#0284c7"),
            "closed": ("已关闭", "#059669"),
            "out_of_scope": ("超范围作业", "#dc2626"),
            "license_issue": ("证照异常", "#d97706"),
            "qual_mismatch": ("资质不匹配", "#ea580c"),
            "need_officer": ("需安全员到场", "#7c3aed"),
            "unreviewed": ("待审核", "#be185d"),
        }.items():
            self.stats[key] = self._make_stat_box(label, "0", color)
            overview_layout.addWidget(self.stats[key])
        root.addWidget(overview_box)

        group_box = QGroupBox("📊 分组汇总（按客户航司 / 维修基地）")
        group_layout = QVBoxLayout(group_box)
        group_layout.setContentsMargins(16, 16, 16, 16)
        group_layout.setSpacing(10)
        self.group_scroll = QScrollArea()
        self.group_scroll.setWidgetResizable(True)
        self.group_scroll.setFrameShape(QFrame.NoFrame)
        self.group_inner = QWidget()
        self.group_inner_layout = QVBoxLayout(self.group_inner)
        self.group_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.group_inner_layout.setSpacing(8)
        self.group_scroll.setWidget(self.group_inner)
        group_layout.addWidget(self.group_scroll)
        root.addWidget(group_box)

        alerts_box = QGroupBox("🚨 重点关注问题（会议需明确处置）")
        alerts_layout = QVBoxLayout(alerts_box)
        alerts_layout.setContentsMargins(16, 16, 16, 16)
        self.alerts_area = QVBoxLayout()
        self.alerts_area.setSpacing(6)
        alerts_layout.addLayout(self.alerts_area)
        root.addWidget(alerts_box)

        content = QGroupBox("风险清单（按状态分类）")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 12, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_inner = QWidget()
        self.columns_layout = QHBoxLayout(scroll_inner)
        self.columns_layout.setContentsMargins(8, 8, 8, 8)
        self.columns_layout.setSpacing(14)
        scroll.setWidget(scroll_inner)
        content_layout.addWidget(scroll)
        root.addWidget(content, 1)

        fu_box = QGroupBox("📝 会议跟进台账（跨天闭环 · 选自重点问题与建议动作）")
        fu_layout = QVBoxLayout(fu_box)
        fu_layout.setContentsMargins(12, 14, 12, 12)
        fu_layout.setSpacing(8)

        fu_btn_row = QHBoxLayout()
        self.btn_fu_add = QPushButton("➕ 新增跟进项")
        self.btn_fu_add_manual = QPushButton("📌 从今日重点问题挑入台账")
        fu_tip = QLabel("说明：跟进项按航司/基地/合同口径持久保存，第二天进入同一范围仍可看到未关闭项。")
        fu_tip.setStyleSheet("color:#64748b;font-size:12px;")
        for b in [self.btn_fu_add, self.btn_fu_add_manual]:
            b.setFixedHeight(32)
            b.setStyleSheet("""QPushButton{background:#059669;color:white;padding:0 16px;
                border:none;border-radius:6px;font-weight:500;font-size:12px;}QPushButton:hover{background:#047857;}""")
        self.btn_fu_add_manual.setStyleSheet("""QPushButton{background:#d97706;color:white;padding:0 16px;
            border:none;border-radius:6px;font-weight:500;font-size:12px;}QPushButton:hover{background:#b45309;}""")
        fu_btn_row.addWidget(self.btn_fu_add)
        fu_btn_row.addWidget(self.btn_fu_add_manual)
        fu_btn_row.addStretch()
        fu_btn_row.addWidget(fu_tip)
        fu_layout.addLayout(fu_btn_row)

        self.fu_table = QTableWidget()
        fu_headers = ["ID", "类型", "跟进事项", "具体动作", "责任方", "计划完成", "状态", "来源日期", "关联风险", "航司/基地"]
        self.fu_table.setColumnCount(len(fu_headers))
        self.fu_table.setHorizontalHeaderLabels(fu_headers)
        self.fu_table.verticalHeader().setVisible(False)
        self.fu_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.fu_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fu_table.setAlternatingRowColors(True)
        self.fu_table.setStyleSheet("""QTableWidget{gridline-color:#e2e8f0;font-size:12px;}
            QHeaderView::section{background:#f1f5f9;padding:6px;border:none;font-weight:600;}
            QTableWidget::item{padding:5px;}""")
        fh = self.fu_table.horizontalHeader()
        fh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        fh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        fh.setSectionResizeMode(2, QHeaderView.Stretch)
        fh.setSectionResizeMode(3, QHeaderView.Stretch)
        for i in [4, 5, 6, 7, 8, 9]:
            fh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        fu_layout.addWidget(self.fu_table)

        fu_op_row = QHBoxLayout()
        self.btn_fu_edit = QPushButton("✏️ 编辑选中项")
        self.btn_fu_done = QPushButton("✅ 标记已完成")
        self.btn_fu_del = QPushButton("🗑 删除选中项")
        for b in [self.btn_fu_edit, self.btn_fu_done, self.btn_fu_del]:
            b.setFixedHeight(32)
            b.setStyleSheet("""QPushButton{background:#475569;color:white;padding:0 16px;
                border:none;border-radius:6px;font-weight:500;font-size:12px;}QPushButton:hover{background:#334155;}""")
        self.btn_fu_done.setStyleSheet("""QPushButton{background:#059669;color:white;padding:0 16px;
            border:none;border-radius:6px;font-weight:500;font-size:12px;}QPushButton:hover{background:#047857;}""")
        self.btn_fu_del.setStyleSheet("""QPushButton{background:#ef4444;color:white;padding:0 16px;
            border:none;border-radius:6px;font-weight:500;font-size:12px;}QPushButton:hover{background:#dc2626;}""")
        fu_op_row.addWidget(self.btn_fu_edit)
        fu_op_row.addWidget(self.btn_fu_done)
        fu_op_row.addWidget(self.btn_fu_del)
        fu_op_row.addStretch()
        fu_layout.addLayout(fu_op_row)
        root.addWidget(fu_box)

        self.btn_back.clicked.connect(self._on_back)
        self.btn_refresh.clicked.connect(self._load_and_render)
        self.btn_fill.clicked.connect(self._on_fill)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_export_todo.clicked.connect(self._on_export_todo)
        self.btn_review.clicked.connect(self._on_review)
        self.btn_fu_add.clicked.connect(self._on_fu_add)
        self.btn_fu_add_manual.clicked.connect(self._on_fu_add_from_problems)
        self.btn_fu_edit.clicked.connect(self._on_fu_edit)
        self.btn_fu_done.clicked.connect(self._on_fu_done)
        self.btn_fu_del.clicked.connect(self._on_fu_del)

    def _make_stat_box(self, label, value, color):
        box = QFrame()
        box.setStyleSheet(f"""QFrame{{background:white;border:1px solid #e2e8f0;
            border-left:4px solid {color};border-radius:8px;}}""")
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        l = QVBoxLayout(box)
        l.setContentsMargins(14, 12, 14, 12)
        l.setSpacing(4)
        lab = QLabel(label)
        lab.setStyleSheet("font-size:12px;color:#64748b;")
        val = QLabel(value)
        val.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        val.setStyleSheet(f"color:{color};")
        l.addWidget(lab)
        l.addWidget(val)
        return box, val

    def _load_and_render(self):
        ctx = self.context
        cid = ctx.get("contract_id")
        aid = ctx.get("drill_airline_id") or ctx.get("airline_id")
        bid = ctx.get("drill_base_id") or ctx.get("base_id")
        wd = ctx.get("work_date")
        all_risks = database.get_risks(
            airline_id=aid, base_id=bid, contract_id=cid, work_date=wd)
        self.risks = database.filter_high_risks(all_risks)
        self._update_drill_label()
        self._build_group_summary()
        self._build_alert_messages()
        self._build_columns()
        self._update_stats()
        self._load_follow_ups()

    def _update_drill_label(self):
        ctx = self.context
        if ctx.get("drill_airline_name"):
            self.drill_label.setText(f"🎯 当前视图：分会场 ▸ {ctx['drill_airline_name']}（仅看该航司风险）")
        elif ctx.get("drill_base_name"):
            self.drill_label.setText(f"🎯 当前视图：分会场 ▸ {ctx['drill_base_name']}（仅看该基地风险）")
        else:
            self.drill_label.setText("🎯 当前视图：总览")

    def _load_follow_ups(self):
        ctx = self.context
        aid = ctx.get("drill_airline_id") or ctx.get("airline_id")
        bid = ctx.get("drill_base_id") or ctx.get("base_id")
        cid = ctx.get("contract_id")
        follow_ups = database.get_follow_ups(airline_id=aid, base_id=bid, contract_id=cid)
        self.follow_ups = follow_ups
        self.fu_table.setRowCount(len(follow_ups))
        for row, fu in enumerate(follow_ups):
            scope = ""
            if fu.get("airline_name"):
                scope = fu["airline_name"]
            if fu.get("base_name"):
                scope = (scope + " / " if scope else "") + fu["base_name"]
            if not scope:
                scope = "（全局）"
            cols = [
                str(fu["id"]),
                fu["follow_type"],
                fu["title"],
                fu["action"],
                fu["responsible"],
                fu.get("planned_date") or "（未设）",
                fu["status"],
                fu["work_date"],
                f"#{fu['risk_id']}" if fu.get("risk_id") else "—",
                scope,
            ]
            for col, val in enumerate(cols):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if col != 2 and col != 3 else Qt.AlignVCenter | Qt.AlignLeft)
                status_colors = {
                    "待处理": ("#fef3c7", "#92400e"),
                    "进行中": ("#dbeafe", "#1e40af"),
                    "已完成": ("#dcfce7", "#166534"),
                    "已逾期": ("#fee2e2", "#991b1b"),
                }
                if col == 6 and val in status_colors:
                    bg, fg = status_colors[val]
                    item.setBackground(QBrush(QColor(bg)))
                    item.setForeground(QBrush(QColor(fg)))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.fu_table.setItem(row, col, item)

    def _build_group_summary(self):
        for i in reversed(range(self.group_inner_layout.count())):
            w = self.group_inner_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        ctx = self.context
        show_airline = not ctx.get("airline_id")
        show_base = not ctx.get("base_id")

        if not show_airline and not show_base:
            tip = QLabel("💡 已选中具体航司/基地，无需分组汇总。可在筛选页切换为「全部航司」或「全部基地」查看分组对比。")
            tip.setStyleSheet("color:#475569;font-size:13px;padding:10px 14px;background:#f1f5f9;border-radius:6px;")
            tip.setWordWrap(True)
            self.group_inner_layout.addWidget(tip)
            return

        today_risks = self.risks

        def _render_section(title, field_name, data_map, accent):
            if not data_map:
                return
            sec = QFrame()
            sec.setStyleSheet("QFrame{background:white;border:1px solid #e2e8f0;border-radius:8px;}")
            sl = QVBoxLayout(sec)
            sl.setContentsMargins(14, 12, 14, 12)
            sl.setSpacing(8)
            t = QLabel(title)
            t.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            t.setStyleSheet(f"color:{accent};")
            sl.addWidget(t)

            grid = QGridLayout()
            grid.setSpacing(8)
            headers = ["分类", "风险总数", "未开工", "进行中", "已关闭", "待审核", "需安全员", "证照/范围异常"]
            for ci, h in enumerate(headers):
                hl = QLabel(h)
                hl.setStyleSheet("font-size:12px;font-weight:600;color:#64748b;padding:4px 8px;background:#f8fafc;border-radius:4px;")
                hl.setAlignment(Qt.AlignCenter)
                grid.addWidget(hl, 0, ci)

            for ri, (name, items) in enumerate(sorted(data_map.items(), key=lambda x: -len(x[1]))):
                row_colors = ["#ffffff", "#f8fafc"]
                bg = row_colors[ri % 2]
                first_id = items[0]["airline_id"] if field_name == "airline_name" else items[0]["base_id"]
                values = [
                    name,
                    str(len(items)),
                    str(sum(1 for r in items if r["status"] == "未开工")),
                    str(sum(1 for r in items if r["status"] == "进行中")),
                    str(sum(1 for r in items if r["status"] == "已关闭")),
                    str(sum(1 for r in items if not r["reviewed"])),
                    str(sum(1 for r in items if r["need_safety_officer"])),
                    str(sum(1 for r in items if r["license_status"] != "valid" or not r["scope_ok"])),
                ]
                for ci, v in enumerate(values):
                    if ci == 0:
                        btn = QPushButton(f"🔍 {v}  (点击进入分会场)")
                        btn.setStyleSheet(f"""QPushButton{{text-align:left;font-size:12px;padding:5px 8px;background:{bg};
                            border:none;border-radius:4px;font-weight:600;color:#1e40af;}}
                            QPushButton:hover{{background:#dbeafe;color:#1e3a8a;text-decoration:underline;}}""")
                        btn.setCursor(Qt.PointingHandCursor)
                        btn.setFlat(True)
                        if field_name == "airline_name":
                            btn.clicked.connect(lambda _=False, n=name, fid=first_id: self._drill_into_airline(fid, n))
                        else:
                            btn.clicked.connect(lambda _=False, n=name, fid=first_id: self._drill_into_base(fid, n))
                        grid.addWidget(btn, ri + 1, ci)
                    else:
                        vl = QLabel(v)
                        vl.setAlignment(Qt.AlignCenter)
                        style = f"font-size:12px;padding:5px 8px;background:{bg};border-radius:4px;"
                        if ci >= 5 and v != "0":
                            style += "font-weight:700;"
                            if ci == 5:
                                style += "color:#be185d;"
                            elif ci == 6:
                                style += "color:#6b21a8;"
                            elif ci == 7:
                                style += "color:#dc2626;"
                        vl.setStyleSheet(style)
                        grid.addWidget(vl, ri + 1, ci)

            for ci in range(len(headers)):
                grid.setColumnStretch(ci, 1 if ci == 0 else 0)
            sl.addLayout(grid)
            self.group_inner_layout.addWidget(sec)

        if show_airline:
            airline_map = {}
            for r in today_risks:
                key = r["airline_name"]
                airline_map.setdefault(key, []).append(r)
            _render_section("✈️  按客户航司分组", "airline_name", airline_map, "#0284c7")

        if show_base:
            base_map = {}
            for r in today_risks:
                key = r["base_name"]
                base_map.setdefault(key, []).append(r)
            _render_section("🏭  按维修基地分组", "base_name", base_map, "#059669")

        if not self.risks:
            tip = QLabel("✅ 当前筛选范围内无高风险记录，分组汇总为空。")
            tip.setStyleSheet("color:#059669;font-size:13px;padding:10px 14px;background:#ecfdf5;border-radius:6px;")
            tip.setWordWrap(True)
            self.group_inner_layout.addWidget(tip)

    def _build_alert_messages(self):
        for i in reversed(range(self.alerts_area.count())):
            w = self.alerts_area.itemAt(i).widget()
            if w:
                w.setParent(None)
        if not self.risks:
            ctx = self.context
            scope = []
            if ctx.get("airline_name") and ctx["airline_name"] != "全部航司":
                scope.append(f"航司：{ctx['airline_name']}")
            if ctx.get("base_name") and ctx["base_name"] != "全部基地":
                scope.append(f"基地：{ctx['base_name']}")
            if ctx.get("contract_name") and ctx["contract_name"] != "全部合同":
                scope.append(f"合同：{ctx['contract_name']}")
            scope.append(f"日期：{ctx.get('work_date', '')}")
            tip = QLabel("✅ 当前筛选范围内无风险记录\n   " + "  |  ".join(scope))
            tip.setStyleSheet("color:#059669;font-size:13px;padding:12px;background:#ecfdf5;border-radius:6px;")
            tip.setWordWrap(True)
            self.alerts_area.addWidget(tip)
            return

        today = date.today()
        alert_templates = []
        for r in self.risks:
            problems = []
            if not r["scope_ok"]:
                problems.append(("🔴", "超范围作业", "#fee2e2", "#991b1b"))
            if r["license_status"] == "expired":
                problems.append(("🔴", f"{r['work_type']}许可证已过期", "#fee2e2", "#991b1b"))
            elif r["license_status"] == "warning":
                problems.append(("🟠", f"{r['work_type']}许可证即将过期", "#ffedd5", "#9a3412"))
            if r["need_safety_officer"]:
                problems.append(("🟣", f"需客户安全员到场监护：{r['work_type']} @{r['work_location']}",
                                 "#ede9fe", "#6b21a8"))
            if not r["reviewed"]:
                problems.append(("🟤", f"项目经理尚未审核：{r['work_type']}（班组：{r['team_name']}）",
                                 "#fce7f3", "#9d174d"))
            per_ids = r["personnel_ids"].split(",") if r["personnel_ids"] else []
            per_ids = [x for x in per_ids if x]
            personnel = database.get_personnel()
            chosen = [p for p in personnel if str(p["id"]) in per_ids]
            for p in chosen:
                exp = datetime.fromisoformat(p["license_expiry"]).date()
                days = (exp - today).days
                wt = r["work_type"]
                q = p["qualifications"]
                if "喷漆" in wt and "喷漆" not in q:
                    problems.append(("🟠", f"人员资质不匹配：{p['name']} 无喷漆资质参与{wt}",
                                     "#ffedd5", "#9a3412"))
                elif "打磨" in wt and "打磨" not in q:
                    problems.append(("🟠", f"人员资质提示：{p['name']} 无打磨资质参与{wt}",
                                     "#ffedd5", "#9a3412"))
                elif "结构" in wt and "结构维修" not in q and "复材" not in q:
                    problems.append(("🟠", f"人员资质提示：{p['name']} 参与{wt}（核对资质）",
                                     "#ffedd5", "#9a3412"))
                if days < 7:
                    problems.append((
                        "🟠" if days >= 0 else "🔴",
                        f"证照{'即将过期' if days >= 0 else '已过期'}: {p['name']} {p['license_no']} ({days}天)",
                        "#ffedd5" if days >= 0 else "#fee2e2",
                        "#9a3412" if days >= 0 else "#991b1b"
                    ))
            for icon, text, bg, fg in problems:
                alert_templates.append((icon, f"#{r['id']} {text}", bg, fg, r))

        if not alert_templates:
            tip = QLabel("✅ 所有风险状态良好，未发现异常")
            tip.setStyleSheet("color:#059669;font-size:13px;padding:10px;background:#ecfdf5;border-radius:6px;")
            self.alerts_area.addWidget(tip)
            return
        seen = set()
        for icon, text, bg, fg, r in alert_templates:
            key = text
            if key in seen:
                continue
            seen.add(key)
            lab = QLabel(f"{icon}  {text}")
            lab.setStyleSheet(f"font-size:13px;padding:9px 12px;background:{bg};"
                              f"color:{fg};border-radius:6px;font-weight:500;")
            lab.setWordWrap(True)
            self.alerts_area.addWidget(lab)

    def _build_columns(self):
        for i in reversed(range(self.columns_layout.count())):
            w = self.columns_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        self._selected_risk_id = None
        columns = [
            ("未开工", "未开工", "#64748b", "#f8fafc"),
            ("进行中", "进行中", "#0284c7", "#f0f9ff"),
            ("已关闭", "已关闭", "#059669", "#ecfdf5"),
        ]
        for title, status_key, accent, bg in columns:
            col = self._make_column(title, status_key, accent, bg)
            self.columns_layout.addWidget(col)

    def _make_column(self, title, status_key, accent, bg):
        col_box = QGroupBox()
        col_box.setStyleSheet(f"""QGroupBox{{background:{bg};border:1px solid #e2e8f0;
            border-top:4px solid {accent};border-radius:10px;}}""")
        col_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(col_box)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        items = [r for r in self.risks if r["status"] == status_key]
        header = QHBoxLayout()
        t = QLabel(title)
        t.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        t.setStyleSheet(f"color:{accent};")
        header.addWidget(t)
        cnt = QLabel(f"{len(items)} 项")
        cnt.setStyleSheet(f"color:{accent};font-weight:600;background:white;padding:2px 10px;border-radius:12px;"
                          f"font-size:12px;border:1px solid #e2e8f0;")
        header.addStretch()
        header.addWidget(cnt)
        layout.addLayout(header)

        if not items:
            empty = QLabel("（暂无）")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#94a3b8;padding:30px;font-size:13px;")
            layout.addWidget(empty)
            layout.addStretch()
            return col_box

        scroll_inner = QWidget()
        inner_layout = QVBoxLayout(scroll_inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(8)

        for r in items:
            card = self._make_card(r, accent)
            inner_layout.addWidget(card)
        inner_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(scroll_inner)
        scroll.verticalScrollBar().setStyleSheet("QScrollBar{width:8px;}")
        layout.addWidget(scroll, 1)
        return col_box

    def _make_card(self, r, accent):
        card = QFrame()
        card.setStyleSheet("""QFrame{background:white;border:1px solid #e2e8f0;
            border-radius:8px;}QFrame:hover{border:1px solid #cbd5e1;}""")
        card.setCursor(Qt.PointingHandCursor)
        cv = QVBoxLayout(card)
        cv.setContentsMargins(14, 12, 14, 12)
        cv.setSpacing(6)

        tags = QHBoxLayout()
        title = QLabel(f"{r['work_type']}")
        title.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        title.setStyleSheet(f"color:{accent};")
        tags.addWidget(title)
        tags.addStretch()
        id_tag = QLabel(f"#{r['id']}")
        id_tag.setStyleSheet("color:#94a3b8;font-size:11px;font-family:Consolas;")
        tags.addWidget(id_tag)
        cv.addLayout(tags)

        loc = QLabel(f"📍 {r['work_location']}  |  {r['team_name']}  |  {r['contract_name']}")
        loc.setStyleSheet("color:#334155;font-size:12px;")
        loc.setWordWrap(True)
        cv.addWidget(loc)

        personnel_ids = r["personnel_ids"].split(",") if r["personnel_ids"] else []
        personnel = database.get_personnel()
        chosen = [p for p in personnel if str(p["id"]) in personnel_ids]
        names_text = "、".join(p["name"] for p in chosen) or "(未指定)"
        ppl = QLabel(f"👥 {names_text}")
        ppl.setStyleSheet("color:#475569;font-size:12px;")
        ppl.setWordWrap(True)
        cv.addWidget(ppl)

        if r["est_end_time"]:
            tl = QLabel(f"⏰ 预计关闭: {r['est_end_time']}")
            tl.setStyleSheet("color:#475569;font-size:12px;")
            cv.addWidget(tl)

        tags_row = QHBoxLayout()
        tags_row.setSpacing(6)
        self._add_tag(tags_row, f"许可证: {'正常' if r['license_status']=='valid' else ('即将过期⚠️' if r['license_status']=='warning' else '已过期🚫')}",
                      "#fee2e2" if r["license_status"] == "expired" else ("#ffedd5" if r["license_status"] == "warning" else "#dcfce7"),
                      "#991b1b" if r["license_status"] == "expired" else ("#9a3412" if r["license_status"] == "warning" else "#166534"))
        if not r["scope_ok"]:
            self._add_tag(tags_row, "超范围作业⚠️", "#fee2e2", "#991b1b")
        if r["need_safety_officer"]:
            self._add_tag(tags_row, "需客户安全员🛡", "#ede9fe", "#6b21a8")
        if not r["reviewed"]:
            self._add_tag(tags_row, "待项目经理审核⏳", "#fce7f3", "#9d174d")
        else:
            self._add_tag(tags_row, "已审核✅", "#dcfce7", "#166534")
        tags_row.addStretch()
        cv.addLayout(tags_row)

        if r["isolation_measures"]:
            isol = QLabel(f"🔒 隔离措施: {r['isolation_measures']}")
            isol.setStyleSheet("color:#475569;font-size:12px;")
            isol.setWordWrap(True)
            cv.addWidget(isol)

        if r["remarks"]:
            rem = QLabel(f"📝 {r['remarks']}")
            rem.setStyleSheet("color:#0f172a;font-size:12px;background:#fef3c7;padding:6px 8px;border-radius:4px;")
            rem.setWordWrap(True)
            cv.addWidget(rem)

        card._risk_id = r["id"]
        card.mouseDoubleClickEvent = lambda ev, rid=r["id"]: self._on_card_double(rid)
        return card

    def _add_tag(self, hlayout, text, bg, fg):
        lab = QLabel(text)
        lab.setStyleSheet(f"background:{bg};color:{fg};padding:3px 8px;border-radius:10px;"
                          f"font-size:11px;font-weight:600;")
        hlayout.addWidget(lab)

    def _update_stats(self):
        def _set(key, val):
            box, lbl = self.stats[key]
            lbl.setText(str(val))

        _set("total", len(self.risks))
        _set("not_started", sum(1 for r in self.risks if r["status"] == "未开工"))
        _set("in_progress", sum(1 for r in self.risks if r["status"] == "进行中"))
        _set("closed", sum(1 for r in self.risks if r["status"] == "已关闭"))
        _set("out_of_scope", sum(1 for r in self.risks if not r["scope_ok"]))
        _set("license_issue", sum(1 for r in self.risks if r["license_status"] != "valid"))
        today = date.today()
        q_count = 0
        for r in self.risks:
            pids = r["personnel_ids"].split(",") if r["personnel_ids"] else []
            personnel = database.get_personnel()
            chosen = [p for p in personnel if str(p["id"]) in pids]
            wt = r["work_type"]
            for p in chosen:
                q = p["qualifications"]
                if ("喷漆" in wt and "喷漆" not in q) or ("打磨" in wt and "打磨" not in q):
                    q_count += 1
                    break
                if "结构" in wt and "结构维修" not in q and "复材" not in q:
                    q_count += 1
                    break
        _set("qual_mismatch", q_count)
        _set("need_officer", sum(1 for r in self.risks if r["need_safety_officer"]))
        _set("unreviewed", sum(1 for r in self.risks if not r["reviewed"]))

    def _on_card_double(self, rid):
        ctx = self.context.copy()
        ctx["risk_id"] = rid
        ctx["mode"] = "edit"
        if self.go_to_fill is not None:
            self.go_to_fill.emit(ctx)

    def _on_back(self):
        if self.go_back is not None:
            self.go_back.emit()

    def _on_fill(self):
        ctx = self.context.copy()
        ctx["risk_id"] = None
        ctx["mode"] = "new"
        if self.go_to_fill is not None:
            self.go_to_fill.emit(ctx)

    def _build_report_text(self):
        ctx = self.context
        lines = []
        today = date.today()
        gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        scope_parts = []
        if ctx.get("airline_name") and ctx["airline_name"] != "全部航司":
            scope_parts.append(f"客户航司：{ctx['airline_name']}")
        else:
            scope_parts.append("客户航司：全部航司")
        if ctx.get("base_name") and ctx["base_name"] != "全部基地":
            scope_parts.append(f"维修基地：{ctx['base_name']}")
        else:
            scope_parts.append("维修基地：全部基地")
        if ctx.get("contract_name") and ctx["contract_name"] != "全部合同":
            scope_parts.append(f"合同项目：{ctx['contract_name']}")
        else:
            scope_parts.append("合同项目：全部合同")
        scope_parts.append(f"作业日期：{ctx.get('work_date', '')}")

        aid = ctx.get("drill_airline_id") or ctx.get("airline_id")
        bid = ctx.get("drill_base_id") or ctx.get("base_id")
        cid = ctx.get("contract_id")

        lines.append("=" * 70)
        lines.append("民 航 维 修 外 包 承 包 商 · 现 场 风 险 日 报")
        lines.append("=" * 70)
        lines.append("  每日协调会会议纪要")
        lines.append("-" * 70)
        lines.append(f"  生成时间：{gen_time}")
        lines.append(f"  数据范围：{'  |  '.join(scope_parts)}")
        lines.append(f"  统计口径：仅高风险作业（喷漆/打磨/清洗/结构拆装/发动机/起落架/复材修复）")
        lines.append("")

        if not self.risks:
            fu_all = database.get_follow_ups(airline_id=aid, base_id=bid, contract_id=cid)
            fu_open = [f for f in fu_all if f["status"] in ("待处理", "进行中", "已逾期")]
            today_str = ctx.get("work_date", "")
            fu_yesterday = [f for f in fu_open if f["work_date"] < today_str]
            fu_today_new = [f for f in fu_open if f["work_date"] >= today_str]
            lines.append("=" * 70)
            lines.append("  ☆ 当前数据范围说明")
            lines.append("-" * 70)
            lines.append("  在以下数据范围内：")
            for sp in scope_parts:
                lines.append(f"    · {sp}")
            lines.append("")
            lines.append("  结论：本日上述范围内无高风险作业记录。")
            lines.append("")
            lines.append("  遗留跟进说明：")
            lines.append(f"    ▸ 昨天/更早遗留未关闭（{len(fu_yesterday)} 项）：")
            if fu_yesterday:
                for idx, f in enumerate(fu_yesterday, 1):
                    lines.append(f"      {idx}. [{f['status']}] {f['title']}")
                    lines.append(f"         动作：{f['action']}    责任方：{f['responsible']}    计划：{f.get('planned_date') or '（未设）'}")
            else:
                lines.append("      （无之前遗留的未关闭项。）")
            lines.append(f"    ▸ 今日会议新增待办（{len(fu_today_new)} 项）")
            if fu_today_new:
                for idx, f in enumerate(fu_today_new, 1):
                    lines.append(f"      {idx}. [{f['status']}] {f['title']}")
                    lines.append(f"         动作：{f['action']}    责任方：{f['responsible']}    计划：{f.get('planned_date') or '（未设）'}")
            else:
                lines.append("      （今日暂未新增待办。）")
            lines.append("    ▸ 今日新增高风险：0 项    ▸ 今日已关闭风险：0 项")
            lines.append("")
            lines.append("  会议确认：")
            lines.append("    承包商确认本日无高风险作业，各班组按计划推进低风险日常工作。")
            lines.append("    如有临时新增高风险作业，须在开工前补录并通知项目经理。")
            lines.append("=" * 70)
            return "\n".join(lines)

        box, total_lbl = self.stats["total"]
        box, ns_lbl = self.stats["not_started"]
        box, ip_lbl = self.stats["in_progress"]
        box, cl_lbl = self.stats["closed"]
        box, os_lbl = self.stats["out_of_scope"]
        box, li_lbl = self.stats["license_issue"]
        box, qm_lbl = self.stats["qual_mismatch"]
        box, no_lbl = self.stats["need_officer"]
        box, ur_lbl = self.stats["unreviewed"]

        lines.append("一、总体情况概览")
        lines.append("-" * 70)
        lines.append(f"  高风险总数：{total_lbl.text()} 项")
        lines.append(f"    · 按状态：未开工 {ns_lbl.text()} 项 / 进行中 {ip_lbl.text()} 项 / 已关闭 {cl_lbl.text()} 项")
        lines.append(f"    · 合规性：超范围 {os_lbl.text()} 项 / 证照异常 {li_lbl.text()} 项 / 资质不匹配 {qm_lbl.text()} 项")
        lines.append(f"    · 协调项：需客户安全员 {no_lbl.text()} 项 / 待项目经理审核 {ur_lbl.text()} 项")
        lines.append("")

        fu_all = database.get_follow_ups(
            airline_id=aid, base_id=bid, contract_id=cid)
        fu_open = [f for f in fu_all if f["status"] in ("待处理", "进行中", "已逾期")]
        fu_done = [f for f in fu_all if f["status"] == "已完成"]
        today_str = ctx.get("work_date", "")
        today_new = [r for r in self.risks if r["status"] != "已关闭"]
        today_closed = [r for r in self.risks if r["status"] == "已关闭"]

        lines.append("二、遗留跟进说明（跨天闭环跟踪）")
        lines.append("-" * 70)

        fu_yesterday = []
        fu_today_new = []
        for f in fu_open:
            if f["work_date"] < today_str:
                fu_yesterday.append(f)
            else:
                fu_today_new.append(f)

        lines.append(f"  ▸ 昨天/更早遗留未关闭（{len(fu_yesterday)} 项）：")
        if fu_yesterday:
            for idx, f in enumerate(fu_yesterday, 1):
                scope_name = f.get("airline_name") or f.get("base_name") or "全局"
                lines.append(f"    {idx}. [{f['status']}] {f['title']}")
                lines.append(f"       动作：{f['action']}    责任方：{f['responsible']}")
                lines.append(f"       计划完成：{f.get('planned_date') or '（未设）'}    来源日期：{f['work_date']}    关联：#{f['risk_id'] if f.get('risk_id') else '—'}    范围：{scope_name}")
        else:
            lines.append("    （无之前遗留的未关闭项，前序会议问题均已闭环。）")
        lines.append("")
        lines.append(f"  ▸ 今日会议新增待办（{len(fu_today_new)} 项）：")
        if fu_today_new:
            for idx, f in enumerate(fu_today_new, 1):
                scope_name = f.get("airline_name") or f.get("base_name") or "全局"
                lines.append(f"    {idx}. [{f['status']}] {f['title']}")
                lines.append(f"       动作：{f['action']}    责任方：{f['responsible']}")
                lines.append(f"       计划完成：{f.get('planned_date') or '（未设）'}    关联风险：#{f['risk_id'] if f.get('risk_id') else '—'}    范围：{scope_name}")
        else:
            lines.append("    （今日暂未新增待办，如有需要请会后补充挑入跟进台账。）")
        lines.append("")
        lines.append(f"  ▸ 今日新增高风险（{len(today_new)} 项）：")
        if today_new:
            for r in today_new:
                lines.append(f"    · 风险#{r['id']} 【{r['work_type']}】@{r['work_location']}（{r['team_name']}）状态：{r['status']}")
        else:
            lines.append("    （今日当前范围内无新增高风险作业。）")
        lines.append("")
        lines.append(f"  ▸ 今日已关闭风险（{len(today_closed)} 项）：")
        if today_closed:
            for r in today_closed:
                lines.append(f"    · 风险#{r['id']} 【{r['work_type']}】@{r['work_location']}（{r['team_name']}）已关闭")
        else:
            lines.append("    （今日当前范围内无已关闭风险。）")
        lines.append("")

        lines.append("三、重点问题摘要（会议优先讨论项）")
        lines.append("-" * 70)
        problem_counter = 0
        follow_ups = []

        personnel = database.get_personnel()
        teams = database.get_teams()
        for r in self.risks:
            r_issues = []
            if not r["scope_ok"]:
                r_issues.append("超范围作业")
                follow_ups.append((r["id"], r["work_type"], r["work_location"],
                                  "确认作业范围，补充客户方审批文件",
                                  "项目经理 → 客户方"))
            if r["license_status"] == "expired":
                r_issues.append("相关许可证已过期")
                follow_ups.append((r["id"], r["work_type"], r["work_location"],
                                   "立即办理证照续期，人员暂停参与该项作业",
                                   f"{r['team_name']}班组长"))
            elif r["license_status"] == "warning":
                r_issues.append("相关许可证即将过期")
                follow_ups.append((r["id"], r["work_type"], r["work_location"],
                                   "本周内完成证照续期并提交客户验证",
                                   f"{r['team_name']}班组长"))
            if r["need_safety_officer"]:
                r_issues.append("需客户方安全员到场监护")
                follow_ups.append((r["id"], r["work_type"], r["work_location"],
                                   "开工前2小时通知客户安全员，确认到场时间",
                                   "项目经理协调"))
            if not r["reviewed"]:
                r_issues.append("项目经理尚未审核")
                follow_ups.append((r["id"], r["work_type"], r["work_location"],
                                   "本次会议现场完成审核并签署意见",
                                   "项目经理"))
            pids = r["personnel_ids"].split(",") if r["personnel_ids"] else []
            chosen = [p for p in personnel if str(p["id"]) in pids]
            wt = r["work_type"]
            qual_issues = []
            for p in chosen:
                exp = datetime.fromisoformat(p["license_expiry"]).date()
                days = (exp - today).days
                if "喷漆" in wt and "喷漆" not in p["qualifications"]:
                    qual_issues.append(f"{p['name']}无喷漆作业资质")
                if "打磨" in wt and "打磨" not in p["qualifications"]:
                    qual_issues.append(f"{p['name']}无打磨作业资质")
                if ("结构" in wt or "复材" in wt) and "结构维修" not in p["qualifications"] and "复材" not in p["qualifications"]:
                    qual_issues.append(f"{p['name']}无结构/复材维修资质")
                if days < 7:
                    qual_issues.append(f"{p['name']}个人证照{'即将过期' if days >= 0 else '已过期'}({days}天)")
            if qual_issues:
                r_issues.extend(qual_issues)
                follow_ups.append((r["id"], wt, r["work_location"],
                                   "核对人员资质并调换合格人员",
                                   f"{r['team_name']}班组长"))
            if r_issues:
                problem_counter += 1
                lines.append(f"  {problem_counter}. 风险#{r['id']} 【{wt}】@{r['work_location']}（{r['team_name']}）")
                for issue in r_issues:
                    lines.append(f"      ▸ {issue}")
                lines.append(f"      ▸ 参与人员：{'、'.join(p['name'] for p in chosen)}")
                lines.append(f"      ▸ 当前状态：{r['status']}  |  预计关闭：{r['est_end_time'] or '（未设定）'}")
                lines.append("")

        if problem_counter == 0:
            lines.append("  （未发现需要特别关注的异常问题，全部风险状态良好。）")
            lines.append("")

        lines.append("四、建议跟进动作（会议分派、逐项落实）")
        lines.append("-" * 70)
        if not follow_ups:
            lines.append("  本日无特别跟进项，按计划正常推进各项高风险作业。")
        else:
            seen = set()
            idx = 0
            for rid, wt, loc, action, owner in follow_ups:
                key = (rid, action)
                if key in seen:
                    continue
                seen.add(key)
                idx += 1
                status = next((r["status"] for r in self.risks if r["id"] == rid), "")
                deadline = "本日闭会前" if status in ["进行中", "未开工"] else "下一工作日早班前"
                lines.append(f"  动作#{idx}")
                lines.append(f"    关联风险：#{rid} 【{wt}】@{loc}（状态：{status}）")
                lines.append(f"    具体动作：{action}")
                lines.append(f"    责任方：{owner}")
                lines.append(f"    时限要求：{deadline}")
                lines.append("")

        lines.append("五、高风险作业清单（按状态分类）")
        lines.append("-" * 70)
        for status in ["未开工", "进行中", "已关闭"]:
            items = [r for r in self.risks if r["status"] == status]
            if not items:
                continue
            lines.append(f"  ■【{status}】共 {len(items)} 项")
            lines.append("")
            for r in items:
                pids = r["personnel_ids"].split(",") if r["personnel_ids"] else []
                chosen = [p for p in personnel if str(p["id"]) in pids]
                leader = next((t["leader"] for t in teams if t["id"] == r["team_id"]), "（未设）")
                tags = []
                if r["license_status"] != "valid":
                    tags.append("证照异常")
                if not r["scope_ok"]:
                    tags.append("超范围")
                if r["need_safety_officer"]:
                    tags.append("需安全员")
                if not r["reviewed"]:
                    tags.append("待审核")
                lines.append(f"    · 风险#{r['id']}  {r['work_type']}")
                lines.append(f"      作业位置：{r['work_location']}")
                lines.append(f"      所属合同：{r['contract_name']}")
                lines.append(f"      负责班组：{r['team_name']}（班组长：{leader}）")
                lines.append(f"      参与人员：{'、'.join(p['name'] for p in chosen)}")
                lines.append(f"      隔离措施：{r['isolation_measures']}")
                if r["est_end_time"]:
                    lines.append(f"      预计关闭：{r['est_end_time']}")
                if tags:
                    lines.append(f"      重要标注：{'、'.join(tags)}")
                if r["remarks"]:
                    lines.append(f"      补充说明：{r['remarks']}")
                lines.append("")

        lines.append("六、会议签字确认")
        lines.append("-" * 70)
        lines.append("  承包商项目经理：______________________    签字日期：__________")
        lines.append("  客户方代表（如有）：____________________    签字日期：__________")
        lines.append("")
        lines.append("  会议补充结论：")
        lines.append("  ________________________________________________________________")
        lines.append("  ________________________________________________________________")
        lines.append("  ________________________________________________________________")
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  报告生成：{gen_time}    数据来源：系统风险数据库实时快照")
        lines.append("=" * 70)
        return "\n".join(lines)

    def _on_export(self):
        text = self._build_report_text()
        cb = QApplication.clipboard()
        cb.setText(text)
        QMessageBox.information(self, "复制成功",
                                "日报文本已复制到剪贴板，可直接粘贴到邮件/微信/文档中。")

    def _on_export_todo(self):
        ctx = self.context
        today = date.today()
        aid = ctx.get("drill_airline_id") or ctx.get("airline_id")
        bid = ctx.get("drill_base_id") or ctx.get("base_id")
        cid = ctx.get("contract_id")
        scope_parts = []
        if ctx.get("drill_airline_name") or ctx.get("airline_name"):
            scope_parts.append(f"航司：{ctx.get('drill_airline_name') or ctx.get('airline_name')}")
        if ctx.get("drill_base_name") or ctx.get("base_name"):
            scope_parts.append(f"基地：{ctx.get('drill_base_name') or ctx.get('base_name')}")
        if ctx.get("contract_name") and ctx["contract_name"] != "全部合同":
            scope_parts.append(f"合同：{ctx['contract_name']}")
        scope = " | ".join(scope_parts) if scope_parts else "全部范围"
        fus = database.get_follow_ups(airline_id=aid, base_id=bid, contract_id=cid)
        open_fus = [f for f in fus if f["status"] != "已完成"]

        by_resp = {}
        for fu in open_fus:
            by_resp.setdefault(fu["responsible"], []).append(fu)
        if not by_resp:
            QMessageBox.information(self, "提示", "当前范围内无未关闭的待办事项。")
            return

        lines = []
        lines.append("=" * 68)
        lines.append("  民 航 维 修 承 包 商 · 责 任 方 待 办 清 单")
        lines.append("=" * 68)
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"数据范围：{scope}")
        lines.append(f"基准日期：{today.isoformat()}")
        lines.append("")

        total = len(open_fus)
        overdue = sum(1 for f in open_fus
                      if f["status"] == "已逾期"
                      or (f.get("planned_date") and date.fromisoformat(f["planned_date"]) < today))
        today_due = sum(1 for f in open_fus
                        if f.get("planned_date") and date.fromisoformat(f["planned_date"]) == today)
        lines.append(f"☆ 待办概览：共 {total} 项未关闭（已逾期 {overdue} / 今天到期 {today_due} / 其他 {total-overdue-today_due}）")
        lines.append("")

        for resp, items in sorted(by_resp.items(), key=lambda x: -len(x[1])):
            resp_overdue = sum(1 for f in items
                               if f["status"] == "已逾期"
                               or (f.get("planned_date") and date.fromisoformat(f["planned_date"]) < today))
            lines.append("-" * 68)
            lines.append(f"▶ 责任方：{resp}（共 {len(items)} 项，其中逾期 {resp_overdue} 项）")
            lines.append("-" * 68)
            items_sorted = sorted(items, key=lambda f: (
                0 if f["status"] == "已逾期" else 1,
                date.fromisoformat(f["planned_date"]).toordinal() if f.get("planned_date") else 999999,
            ))
            for idx, fu in enumerate(items_sorted, 1):
                if fu["status"] == "已逾期" or (fu.get("planned_date") and date.fromisoformat(fu["planned_date"]) < today):
                    icon = "🚨"
                elif fu.get("planned_date") and date.fromisoformat(fu["planned_date"]) == today:
                    icon = "🔴"
                elif fu.get("planned_date") and (date.fromisoformat(fu["planned_date"]) - today).days <= 7:
                    icon = "🟠"
                else:
                    icon = "🟡"
                lines.append(f"  {idx}. {icon} [{fu['status']}] {fu['title']}")
                lines.append(f"     具体动作：{fu['action']}")
                if fu.get("planned_date"):
                    pd = date.fromisoformat(fu["planned_date"])
                    days = (pd - today).days
                    dstr = "今天到期" if days == 0 else (f"逾期{abs(days)}天" if days < 0 else f"{days}天后到期")
                    lines.append(f"     计划完成：{fu['planned_date']}（{dstr}）")
                else:
                    lines.append(f"     计划完成：（未设定，请尽快安排）")
                lines.append(f"     来源日期：{fu['work_date']}    关联风险：#{fu['risk_id'] if fu.get('risk_id') else '—'}")
                lines.append("")

        lines.append("=" * 68)
        lines.append("说明：🚨=已逾期  🔴=今天到期  🟠=本周到期  🟡=7天以上/未设定")
        lines.append("      请各责任方按计划完成，每日协调会逐项核对。")
        lines.append("=" * 68)

        text = "\n".join(lines)
        cb = QApplication.clipboard()
        cb.setText(text)
        resp_cnt = len(by_resp)
        QMessageBox.information(self, "复制成功",
            f"责任方待办清单已复制到剪贴板。\n\n"
            f"包含 {resp_cnt} 个责任方、共 {total} 项未关闭待办。\n"
            f"可直接粘贴发送给各责任人。")

    def _on_review(self):
        self.go_to_review.emit(self.context)

    def _drill_into_airline(self, airline_id, airline_name):
        ctx = self.context
        ctx["drill_airline_id"] = airline_id
        ctx["drill_airline_name"] = airline_name
        ctx.pop("drill_base_id", None)
        ctx.pop("drill_base_name", None)
        self._load_and_render()
        QMessageBox.information(self, "进入分会场",
            f"已切换到分会场视图：{airline_name}\n当前仅展示该航司的风险清单、跟进台账和日报。")

    def _drill_into_base(self, base_id, base_name):
        ctx = self.context
        ctx["drill_base_id"] = base_id
        ctx["drill_base_name"] = base_name
        ctx.pop("drill_airline_id", None)
        ctx.pop("drill_airline_name", None)
        self._load_and_render()
        QMessageBox.information(self, "进入分会场",
            f"已切换到分会场视图：{base_name}\n当前仅展示该基地的风险清单、跟进台账和日报。")

    def _back_to_overview(self):
        ctx = self.context
        has_drill = ctx.pop("drill_airline_id", None) or ctx.pop("drill_base_id", None)
        ctx.pop("drill_airline_name", None)
        ctx.pop("drill_base_name", None)
        if has_drill:
            self._load_and_render()

    def _fu_default_data(self):
        ctx = self.context
        return {
            "airline_id": ctx.get("drill_airline_id") or ctx.get("airline_id"),
            "base_id": ctx.get("drill_base_id") or ctx.get("base_id"),
            "contract_id": ctx.get("contract_id"),
            "work_date": ctx.get("work_date"),
        }

    def _on_fu_add(self):
        ctx = self.context
        dlg = _FollowUpEditDialog(self, ctx, default=self._fu_default_data())
        if dlg.exec() == QDialog.Accepted and dlg.result_data:
            data = dlg.result_data
            data["created_at"] = datetime.now().isoformat(timespec="seconds")
            data["closed_at"] = None
            database.insert_follow_up(data)
            self._load_follow_ups()
            QMessageBox.information(self, "新增成功", "跟进项已加入台账。")

    def _on_fu_add_from_problems(self):
        if not self.risks:
            QMessageBox.information(self, "提示", "当前无高风险作业，无可挑入的重点问题。")
            return
        today = date.today()
        personnel = database.get_personnel()
        candidates = []
        for r in self.risks:
            issues = []
            if not r["scope_ok"]:
                issues.append("超范围作业")
            if r["license_status"] == "expired":
                issues.append("许可证已过期")
            elif r["license_status"] == "warning":
                issues.append("许可证即将过期")
            if r["need_safety_officer"]:
                issues.append("需客户安全员")
            if not r["reviewed"]:
                issues.append("待审核")
            pids = r["personnel_ids"].split(",") if r["personnel_ids"] else []
            chosen = [p for p in personnel if str(p["id"]) in pids]
            for p in chosen:
                exp = datetime.fromisoformat(p["license_expiry"]).date()
                days = (exp - today).days
                if days < 7:
                    issues.append(f"{p['name']}证照{days}天")
            if issues:
                candidates.append((r, issues))
        if not candidates:
            QMessageBox.information(self, "提示", "今日重点问题无异常，无需挑入台账。")
            return
        dlg = _ProblemPickerDialog(self, candidates, self.context, self._fu_default_data())
        if dlg.exec() == QDialog.Accepted and dlg.selected:
            for r, issues, action, responsible, planned in dlg.selected:
                data = {
                    "risk_id": r["id"],
                    "airline_id": r.get("airline_id"),
                    "base_id": r.get("base_id"),
                    "contract_id": r.get("contract_id"),
                    "work_date": r["work_date"],
                    "title": f"风险#{r['id']} 【{r['work_type']}】@{r['work_location']}（{r['team_name']}）：{'、'.join(issues)}",
                    "action": action,
                    "responsible": responsible,
                    "planned_date": planned,
                    "status": "待处理",
                    "follow_type": "重点问题",
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "closed_at": None,
                }
                database.insert_follow_up(data)
            self._load_follow_ups()
            QMessageBox.information(self, "挑入成功", f"已将 {len(dlg.selected)} 个重点问题加入跟进台账。")

    def _on_fu_edit(self):
        rows = self.fu_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "提示", "请先选择一条跟进项。")
            return
        fu_id = int(self.fu_table.item(rows[0].row(), 0).text())
        fu = database.get_follow_up_by_id(fu_id)
        if not fu:
            return
        dlg = _FollowUpEditDialog(self, self.context, fu=fu)
        if dlg.exec() == QDialog.Accepted and dlg.result_data:
            data = dlg.result_data
            if data.get("status") == "已完成":
                data["closed_at"] = datetime.now().isoformat(timespec="seconds")
            database.update_follow_up(fu_id, data)
            self._load_follow_ups()
            QMessageBox.information(self, "更新成功", f"跟进项 #{fu_id} 已更新。")

    def _on_fu_done(self):
        rows = self.fu_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "提示", "请先选择一条跟进项。")
            return
        fu_id = int(self.fu_table.item(rows[0].row(), 0).text())
        database.update_follow_up(fu_id, {
            "status": "已完成",
            "closed_at": datetime.now().isoformat(timespec="seconds"),
        })
        self._load_follow_ups()
        QMessageBox.information(self, "已完成", f"跟进项 #{fu_id} 已标记为完成。")

    def _on_fu_del(self):
        rows = self.fu_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "提示", "请先选择一条跟进项。")
            return
        fu_id = int(self.fu_table.item(rows[0].row(), 0).text())
        if QMessageBox.question(self, "删除确认", f"确定删除跟进项 #{fu_id} 吗？",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        database.delete_follow_up(fu_id)
        self._load_follow_ups()


class _FollowUpEditDialog(QDialog):
    def __init__(self, parent, context, default=None, fu=None):
        super().__init__(parent)
        self.setWindowTitle("编辑跟进项" if fu else "新增跟进项")
        self.resize(560, 480)
        self.result_data = None

        v = QVBoxLayout(self)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("如：风险#12 喷漆作业许可证即将过期")
        self.txt_action = QLineEdit()
        self.txt_action.setPlaceholderText("如：本周内完成证照续期并提交客户验证")
        self.txt_responsible = QLineEdit()
        self.txt_responsible.setPlaceholderText("如：喷漆一班班组长 / 项目经理")

        self.cb_type = QComboBox()
        self.cb_type.addItems(["重点问题", "建议动作", "客户协调", "资质整改", "其他"])

        self.de_planned = QDateEdit()
        self.de_planned.setCalendarPopup(True)
        self.de_planned.setDisplayFormat("yyyy-MM-dd")
        self.de_planned.setDate(QDate.currentDate().addDays(1))

        self.cb_status = QComboBox()
        self.cb_status.addItems(["待处理", "进行中", "已完成", "已逾期"])

        for label, w in [("跟进类型", self.cb_type), ("跟进事项", self.txt_title),
                         ("具体动作", self.txt_action), ("责任方", self.txt_responsible),
                         ("计划完成日期", self.de_planned), ("处理状态", self.cb_status)]:
            lab = QLabel(label)
            lab.setStyleSheet("font-weight:600;font-size:13px;")
            form.addRow(lab, w)
        v.addLayout(form)

        if fu:
            self.txt_title.setText(fu["title"])
            self.txt_action.setText(fu["action"])
            self.txt_responsible.setText(fu["responsible"])
            ti = self.cb_type.findText(fu["follow_type"])
            if ti >= 0:
                self.cb_type.setCurrentIndex(ti)
            if fu.get("planned_date"):
                self.de_planned.setDate(QDate.fromString(fu["planned_date"], "yyyy-MM-dd"))
            si = self.cb_status.findText(fu["status"])
            if si >= 0:
                self.cb_status.setCurrentIndex(si)
        else:
            self.txt_responsible.setText("项目经理")

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("保存")
        bb.button(QDialogButtonBox.Cancel).setText("取消")
        bb.button(QDialogButtonBox.Ok).setStyleSheet("background:#059669;color:white;padding:8px 24px;border:none;border-radius:6px;font-weight:600;")
        bb.button(QDialogButtonBox.Cancel).setStyleSheet("background:#94a3b8;color:white;padding:8px 24px;border:none;border-radius:6px;")
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _on_ok(self):
        title = self.txt_title.text().strip()
        action = self.txt_action.text().strip()
        responsible = self.txt_responsible.text().strip()
        if not title:
            QMessageBox.warning(self, "提示", "请填写跟进事项。")
            return
        if not responsible:
            QMessageBox.warning(self, "提示", "请填写责任方。")
            return
        self.result_data = {
            "title": title,
            "action": action or "（待补充具体动作）",
            "responsible": responsible,
            "follow_type": self.cb_type.currentText(),
            "planned_date": self.de_planned.date().toString("yyyy-MM-dd"),
            "status": self.cb_status.currentText(),
        }
        self.accept()


class _ProblemPickerDialog(QDialog):
    def __init__(self, parent, candidates, context, default):
        super().__init__(parent)
        self.setWindowTitle("从今日重点问题挑入跟进台账")
        self.resize(900, 600)
        self.selected = []
        self._rows_data = []

        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)

        info = QLabel(f"共 {len(candidates)} 条带异常的重点问题，勾选需要列入台账的项，逐条填写动作和责任方：")
        info.setStyleSheet("font-size:13px;")
        v.addWidget(info)

        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QCheckBox, QWidget
        self.table = QTableWidget()
        headers = ["勾选", "风险ID", "作业", "异常", "具体动作", "责任方", "计划完成"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("QTableWidget{gridline-color:#e2e8f0;font-size:12px;}"
                                "QHeaderView::section{background:#f1f5f9;padding:6px;border:none;font-weight:600;}")
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 200)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.table.setRowCount(len(candidates))
        for ri, (r, issues) in enumerate(candidates):
            cb = QCheckBox()
            cb.setChecked(True)
            cw = QWidget()
            cl = QHBoxLayout(cw)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.addWidget(cb)
            cl.setAlignment(cb, Qt.AlignCenter)
            self.table.setCellWidget(ri, 0, cw)

            self.table.setItem(ri, 1, QTableWidgetItem(str(r["id"])))
            self.table.setItem(ri, 2, QTableWidgetItem(f"{r['work_type']}@{r['work_location']}"))
            self.table.setItem(ri, 3, QTableWidgetItem("、".join(issues)))

            action_edit = QLineEdit()
            default_actions = {
                "超范围作业": "确认作业范围，补充客户审批",
                "许可证已过期": "办理证照续期，人员暂停作业",
                "许可证即将过期": "本周完成证照续期",
                "需客户安全员": "开工前通知客户安全员到场",
                "待审核": "会议现场完成审核",
            }
            action_edit.setText(next((default_actions[i] for i in issues if i in default_actions), "核对并整改"))
            self.table.setCellWidget(ri, 4, action_edit)

            resp_edit = QLineEdit()
            resp_edit.setText(f"{r['team_name']}班组长")
            self.table.setCellWidget(ri, 5, resp_edit)

            de = QDateEdit()
            de.setCalendarPopup(True)
            de.setDisplayFormat("yyyy-MM-dd")
            de.setDate(QDate.currentDate().addDays(1))
            self.table.setCellWidget(ri, 6, de)

            self._rows_data.append((cb, r, issues, action_edit, resp_edit, de))
        self.table.setColumnHeight(0, 36)
        for ri in range(len(candidates)):
            self.table.setRowHeight(ri, 40)
        v.addWidget(self.table, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("加入台账")
        bb.button(QDialogButtonBox.Cancel).setText("取消")
        bb.button(QDialogButtonBox.Ok).setStyleSheet("background:#059669;color:white;padding:8px 24px;border:none;border-radius:6px;font-weight:600;")
        bb.button(QDialogButtonBox.Cancel).setStyleSheet("background:#94a3b8;color:white;padding:8px 24px;border:none;border-radius:6px;")
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _on_ok(self):
        self.selected = []
        for cb, r, issues, action_edit, resp_edit, de in self._rows_data:
            if cb.isChecked():
                self.selected.append((
                    r, issues,
                    action_edit.text().strip(),
                    resp_edit.text().strip(),
                    de.date().toString("yyyy-MM-dd"),
                ))
        if not self.selected:
            QMessageBox.warning(self, "提示", "请至少勾选一条重点问题。")
            return
        self.accept()

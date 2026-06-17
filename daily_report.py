from datetime import datetime, date
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QPushButton, QGroupBox, QGridLayout, QMessageBox, QSizePolicy,
    QTextEdit, QApplication
)
from PySide6.QtGui import QFont, QColor, QBrush, QGuiApplication

import database


class DailyReportWindow(QWidget):
    go_back = Signal()
    go_to_fill = Signal(dict)

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
        info = QLabel(f"  客户：{ctx.get('airline_name', '全部航司')}  |  基地：{ctx.get('base_name', '全部基地')}  |  合同：{ctx.get('contract_name', '全部合同')}  |  日期：{ctx.get('work_date', '')}")
        info.setStyleSheet("color:#475569;font-size:13px;padding:6px 14px;background:#f1f5f9;border-radius:8px;")
        top_bar.addWidget(info)
        top_bar.addStretch()

        self.btn_fill = QPushButton("✏️ 编辑风险")
        self.btn_back = QPushButton("← 返回筛选")
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_export = QPushButton("📄 复制日报文本")
        for b in [self.btn_fill, self.btn_back, self.btn_refresh, self.btn_export]:
            b.setFixedHeight(38)
            b.setStyleSheet("""QPushButton{background:#64748b;color:white;padding:0 18px;
                border:none;border-radius:6px;font-weight:500;font-size:13px;}
                QPushButton:hover{background:#475569;}""")
        self.btn_export.setStyleSheet("""QPushButton{background:#7c3aed;color:white;padding:0 18px;
            border:none;border-radius:6px;font-weight:500;font-size:13px;}
            QPushButton:hover{background:#6d28d9;}""")
        top_bar.addWidget(self.btn_refresh)
        top_bar.addWidget(self.btn_fill)
        top_bar.addWidget(self.btn_export)
        top_bar.addWidget(self.btn_back)
        root.addLayout(top_bar)

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

        self.btn_back.clicked.connect(self._on_back)
        self.btn_refresh.clicked.connect(self._load_and_render)
        self.btn_fill.clicked.connect(self._on_fill)
        self.btn_export.clicked.connect(self._on_export)

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
        cid = self.context.get("contract_id")
        aid = self.context.get("airline_id")
        bid = self.context.get("base_id")
        wd = self.context.get("work_date")
        all_risks = database.get_risks(
            airline_id=aid, base_id=bid, contract_id=cid, work_date=wd)
        self.risks = database.filter_high_risks(all_risks)
        self._build_group_summary()
        self._build_alert_messages()
        self._build_columns()
        self._update_stats()

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
                    vl = QLabel(v)
                    vl.setAlignment(Qt.AlignCenter if ci > 0 else Qt.AlignVCenter | Qt.AlignLeft)
                    style = f"font-size:12px;padding:5px 8px;background:{bg};border-radius:4px;"
                    if ci == 0:
                        style += "font-weight:600;color:#0f172a;"
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
            lines.append("=" * 70)
            lines.append("  ☆ 当前数据范围说明")
            lines.append("-" * 70)
            lines.append("  在以下数据范围内：")
            for sp in scope_parts:
                lines.append(f"    · {sp}")
            lines.append("")
            lines.append("  结论：本日上述范围内无高风险作业记录。")
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

        lines.append("二、重点问题摘要（会议优先讨论项）")
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

        lines.append("三、建议跟进动作（会议分派、逐项落实）")
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

        lines.append("四、高风险作业清单（按状态分类）")
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

        lines.append("五、会议签字确认")
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

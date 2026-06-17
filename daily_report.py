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
        wd = self.context.get("work_date")
        self.risks = database.get_risks(contract_id=cid, work_date=wd)
        self._build_alert_messages()
        self._build_columns()
        self._update_stats()

    def _build_alert_messages(self):
        for i in reversed(range(self.alerts_area.count())):
            w = self.alerts_area.itemAt(i).widget()
            if w:
                w.setParent(None)
        if not self.risks:
            tip = QLabel("✅ 当日无风险记录")
            tip.setStyleSheet("color:#059669;font-size:13px;padding:10px;background:#ecfdf5;border-radius:6px;")
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
        lines.append(f"【民航维修现场风险日报】")
        lines.append(f"日期: {ctx.get('work_date', '')}")
        lines.append(f"客户航司: {ctx.get('airline_name', '全部航司')}")
        lines.append(f"维修基地: {ctx.get('base_name', '全部基地')}")
        lines.append(f"合同项目: {ctx.get('contract_name', '全部合同')}")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        lines.append(f"=== 概览 ===")
        box, total_lbl = self.stats["total"]
        box, ns_lbl = self.stats["not_started"]
        box, ip_lbl = self.stats["in_progress"]
        box, cl_lbl = self.stats["closed"]
        lines.append(f"风险总数: {total_lbl.text()}   未开工: {ns_lbl.text()}   进行中: {ip_lbl.text()}   已关闭: {cl_lbl.text()}")
        box, os_lbl = self.stats["out_of_scope"]
        box, li_lbl = self.stats["license_issue"]
        box, qm_lbl = self.stats["qual_mismatch"]
        box, no_lbl = self.stats["need_officer"]
        box, ur_lbl = self.stats["unreviewed"]
        lines.append(f"超范围: {os_lbl.text()}  证照异常: {li_lbl.text()}  资质不匹配: {qm_lbl.text()}  需安全员: {no_lbl.text()}  待审核: {ur_lbl.text()}")
        lines.append("")

        lines.append(f"=== 重点关注 ===")
        today = date.today()
        alerts = []
        for r in self.risks:
            r_alerts = []
            if not r["scope_ok"]:
                r_alerts.append("超范围作业")
            if r["license_status"] == "expired":
                r_alerts.append("许可证已过期")
            elif r["license_status"] == "warning":
                r_alerts.append("许可证即将过期")
            if r["need_safety_officer"]:
                r_alerts.append("需客户安全员到场")
            if not r["reviewed"]:
                r_alerts.append("待审核")
            pids = r["personnel_ids"].split(",") if r["personnel_ids"] else []
            personnel = database.get_personnel()
            chosen = [p for p in personnel if str(p["id"]) in pids]
            for p in chosen:
                exp = datetime.fromisoformat(p["license_expiry"]).date()
                days = (exp - today).days
                if days < 7:
                    r_alerts.append(f"{p['name']}证照{'即将过期' if days >= 0 else '已过期'}")
            if r_alerts:
                alerts.append(f"- #{r['id']} 【{r['work_type']}】@{r['work_location']} ({r['team_name']}): " + "、".join(r_alerts))
        if alerts:
            lines.extend(alerts)
        else:
            lines.append("无异常")
        lines.append("")

        for status in ["未开工", "进行中", "已关闭"]:
            lines.append(f"=== {status} ===")
            items = [r for r in self.risks if r["status"] == status]
            if not items:
                lines.append("（无）")
            else:
                for r in items:
                    lines.append(f"- #{r['id']} 【{r['work_type']}】 {r['work_location']}")
                    lines.append(f"    班组: {r['team_name']}  合同: {r['contract_name']}")
                    pids = r["personnel_ids"].split(",") if r["personnel_ids"] else []
                    personnel = database.get_personnel()
                    chosen = [p for p in personnel if str(p["id"]) in pids]
                    lines.append(f"    人员: {'、'.join(p['name'] for p in chosen)}")
                    lines.append(f"    隔离: {r['isolation_measures']}")
                    if r["est_end_time"]:
                        lines.append(f"    预计关闭: {r['est_end_time']}")
                    info = []
                    if r["license_status"] != "valid":
                        info.append("证照异常")
                    if not r["scope_ok"]:
                        info.append("超范围")
                    if r["need_safety_officer"]:
                        info.append("需安全员")
                    if not r["reviewed"]:
                        info.append("待审核")
                    if info:
                        lines.append(f"    标注: {'、'.join(info)}")
                    if r["remarks"]:
                        lines.append(f"    备注: {r['remarks']}")
            lines.append("")
        return "\n".join(lines)

    def _on_export(self):
        text = self._build_report_text()
        cb = QApplication.clipboard()
        cb.setText(text)
        QMessageBox.information(self, "复制成功",
                                "日报文本已复制到剪贴板，可直接粘贴到邮件/微信/文档中。")

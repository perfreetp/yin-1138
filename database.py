import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "risk_report.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS airlines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS bases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        airline_id INTEGER NOT NULL,
        base_id INTEGER NOT NULL,
        FOREIGN KEY (airline_id) REFERENCES airlines(id),
        FOREIGN KEY (base_id) REFERENCES bases(id)
    );

    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        leader TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS personnel (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        team_id INTEGER NOT NULL,
        license_no TEXT NOT NULL,
        license_expiry TEXT NOT NULL,
        qualifications TEXT NOT NULL,
        FOREIGN KEY (team_id) REFERENCES teams(id)
    );

    CREATE TABLE IF NOT EXISTS risks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_id INTEGER NOT NULL,
        work_date TEXT NOT NULL,
        work_type TEXT NOT NULL,
        work_location TEXT NOT NULL,
        team_id INTEGER NOT NULL,
        personnel_ids TEXT NOT NULL,
        license_status TEXT NOT NULL DEFAULT 'valid',
        isolation_measures TEXT NOT NULL,
        est_end_time TEXT,
        status TEXT NOT NULL DEFAULT '未开工',
        scope_ok INTEGER NOT NULL DEFAULT 1,
        need_safety_officer INTEGER NOT NULL DEFAULT 0,
        reviewed INTEGER NOT NULL DEFAULT 0,
        remarks TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (contract_id) REFERENCES contracts(id),
        FOREIGN KEY (team_id) REFERENCES teams(id)
    );
    """)

    conn.commit()
    if not _has_data(cur, "airlines"):
        _seed_data(conn)
    conn.close()


def _has_data(cur, table):
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0] > 0


def _seed_data(conn):
    cur = conn.cursor()

    cur.executemany("INSERT INTO airlines (name) VALUES (?)", [
        ("中国国际航空",), ("东方航空",), ("南方航空",), ("海南航空",), ("春秋航空",)
    ])

    cur.executemany("INSERT INTO bases (name) VALUES (?)", [
        ("北京首都基地",), ("上海浦东基地",), ("广州白云基地",), ("深圳宝安基地",), ("成都天府基地",)
    ])

    contracts = [
        ("国航北京A330定检项目", 1, 1),
        ("东航浦东B737航线维修", 2, 2),
        ("南航广州A350喷漆项目", 3, 3),
        ("海航深圳A320结构大修", 4, 4),
        ("春秋成都航线日常维修", 5, 5),
        ("国航上海航线维护", 1, 2),
    ]
    cur.executemany("INSERT INTO contracts (name, airline_id, base_id) VALUES (?, ?, ?)", contracts)

    teams = [
        ("喷漆一班", "张伟"), ("喷漆二班", "李芳"),
        ("打磨班", "王强"), ("清洗班", "赵敏"),
        ("结构一班", "陈刚"), ("结构二班", "刘洋"),
        ("综合维修班", "孙磊"),
    ]
    cur.executemany("INSERT INTO teams (name, leader) VALUES (?, ?)", teams)

    today = datetime.now().date()
    personnel = []
    quals = [
        "喷漆作业资质,登高作业证", "喷漆作业资质,有限空间作业证",
        "打磨作业资质,防尘防护证", "清洗作业资质,登高作业证",
        "结构维修资质,铆工资质", "结构维修资质,复材修理资质",
        "维修人员执照A证", "维修人员执照B证",
    ]
    names = ["赵建国", "钱小明", "孙丽娟", "李大伟", "周志远", "吴佳琪",
             "郑海涛", "冯美玲", "褚云飞", "卫晓燕", "蒋文博", "沈雅琴",
             "韩志强", "杨丽娜", "朱俊峰", "秦思远"]
    import itertools
    pid = 1
    for team_id in range(1, 8):
        for _ in range(2 if team_id < 7 else 3):
            expiry = today + timedelta(days=(pid % 30) + 10)
            q = quals[(pid - 1) % len(quals)]
            personnel.append((names[pid - 1] if pid - 1 < len(names) else f"员工{pid}",
                              team_id, f"LIC-{10000 + pid}", expiry.isoformat(), q))
            pid += 1
    cur.executemany(
        "INSERT INTO personnel (name, team_id, license_no, license_expiry, qualifications) VALUES (?, ?, ?, ?, ?)",
        personnel)

    work_types = ["喷漆作业", "打磨作业", "清洗作业", "结构拆装", "发动机维修", "起落架检修", "复合材料修复"]
    locations = ["机库A-03机位", "机库B-12机位", "停机坪21号位", "喷漆车间", "结构车间", "机库C-07", "停机坪15号位"]
    statuses = ["未开工", "进行中", "已关闭"]
    licenses = ["valid", "warning", "expired"]
    isolations = ["断电挂牌", "液压系统隔离", "燃油系统排空", "安全警戒带", "防火毯覆盖", "区域锁闭"]

    import random
    random.seed(42)
    for offset in range(-1, 2):
        work_date = (today + timedelta(days=offset)).isoformat()
        for i in range(6):
            cid = random.randint(1, 6)
            tid = random.randint(1, 7)
            cur.execute("SELECT id FROM personnel WHERE team_id = ? ORDER BY id", (tid,))
            pids = [str(r["id"]) for r in cur.fetchall()][:3]
            if not pids:
                pids = [str(random.randint(1, 20))]
            wt = random.choice(work_types)
            st = statuses[offset + 1] if offset != 0 else random.choices(statuses, weights=[1, 2, 1])[0]
            ls = random.choices(licenses, weights=[7, 2, 1])[0]
            scope_ok = 0 if random.random() < 0.15 else 1
            need_so = 1 if random.random() < 0.35 else 0
            reviewed = 1 if random.random() < 0.6 else 0
            est = (datetime.combine(today + timedelta(days=offset), datetime.min.time()) +
                   timedelta(hours=random.randint(8, 22), minutes=random.choice([0, 30]))).strftime("%Y-%m-%d %H:%M")
            cur.execute("""INSERT INTO risks
                (contract_id, work_date, work_type, work_location, team_id, personnel_ids,
                 license_status, isolation_measures, est_end_time, status,
                 scope_ok, need_safety_officer, reviewed, remarks, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cid, work_date, wt, random.choice(locations), tid, ",".join(pids),
                 ls, "、".join(random.sample(isolations, k=random.randint(1, 3))),
                 est, st, scope_ok, need_so, reviewed,
                 "" if random.random() > 0.3 else f"{wt}需注意{random.choice(['防火', '防尘', '坠落防护'])}",
                 datetime.now().isoformat(timespec="seconds")))

    conn.commit()


def get_airlines():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM airlines ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bases():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM bases ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_contracts(airline_id=None, base_id=None):
    sql = "SELECT c.*, a.name AS airline_name, b.name AS base_name FROM contracts c " \
          "JOIN airlines a ON a.id = c.airline_id JOIN bases b ON b.id = c.base_id WHERE 1=1"
    params = []
    if airline_id:
        sql += " AND c.airline_id = ?"
        params.append(airline_id)
    if base_id:
        sql += " AND c.base_id = ?"
        params.append(base_id)
    sql += " ORDER BY c.id"
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_teams():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM teams ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_personnel(team_id=None):
    sql = "SELECT p.*, t.name AS team_name FROM personnel p JOIN teams t ON t.id = p.team_id WHERE 1=1"
    params = []
    if team_id:
        sql += " AND p.team_id = ?"
        params.append(team_id)
    sql += " ORDER BY p.id"
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_risks(airline_id=None, base_id=None, contract_id=None, work_date=None, status=None):
    sql = """SELECT r.*, ct.name AS contract_name, ct.airline_id, ct.base_id,
                    a.name AS airline_name, b.name AS base_name, t.name AS team_name
             FROM risks r
             JOIN contracts ct ON ct.id = r.contract_id
             JOIN airlines a ON a.id = ct.airline_id
             JOIN bases b ON b.id = ct.base_id
             JOIN teams t ON t.id = r.team_id
             WHERE 1=1"""
    params = []
    if airline_id:
        sql += " AND ct.airline_id = ?"
        params.append(airline_id)
    if base_id:
        sql += " AND ct.base_id = ?"
        params.append(base_id)
    if contract_id:
        sql += " AND r.contract_id = ?"
        params.append(contract_id)
    if work_date:
        sql += " AND r.work_date = ?"
        params.append(work_date)
    if status:
        sql += " AND r.status = ?"
        params.append(status)
    sql += " ORDER BY r.id DESC"
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_risk_by_id(risk_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM risks WHERE id = ?", (risk_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_risk(data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""INSERT INTO risks
        (contract_id, work_date, work_type, work_location, team_id, personnel_ids,
         license_status, isolation_measures, est_end_time, status,
         scope_ok, need_safety_officer, reviewed, remarks, created_at)
        VALUES (:contract_id, :work_date, :work_type, :work_location, :team_id, :personnel_ids,
                :license_status, :isolation_measures, :est_end_time, :status,
                :scope_ok, :need_safety_officer, :reviewed, :remarks, :created_at)""", data)
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid


def update_risk(risk_id, data):
    sets = ", ".join(f"{k} = :{k}" for k in data.keys())
    data["id"] = risk_id
    conn = get_conn()
    conn.execute(f"UPDATE risks SET {sets} WHERE id = :id", data)
    conn.commit()
    conn.close()


HIGH_RISK_TYPES = [
    "喷漆作业", "打磨作业", "清洗作业", "结构拆装",
    "发动机维修", "起落架检修", "复合材料修复",
]


def is_high_risk_type(work_type):
    return work_type in HIGH_RISK_TYPES


def filter_high_risks(risks):
    return [r for r in risks if is_high_risk_type(r["work_type"])]

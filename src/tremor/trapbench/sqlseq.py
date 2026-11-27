"""E8.3 sequence: a generated SQLite DB plus 40 questions with exact answers.

Hidden facts a memory can carry: orders join customers on customers.code (not id),
and the money column holds cents. Families differ in table/column names; each family
belongs to exactly one split by a hash of its name.
"""
import hashlib
import os
import random
import sqlite3

N = 40
# family -> (customer table, order table, join column, money column)
FAMILIES = {
    "shop": ("customers", "orders", "cust_ref", "total"),
    "clinic": ("patients", "visits", "pat_ref", "fee"),
    "farm": ("growers", "crates", "grower_ref", "price"),
    "school": ("pupils", "fees", "pupil_ref", "amount"),
}


def split_of(family):
    return "test" if hashlib.sha256(family.encode()).digest()[0] % 2 else "train"


def check_split(train, test):
    """Raise if a family is in both lists, in the wrong split, or shares a schema vocabulary."""
    if set(train) & set(test):
        raise ValueError("family in both splits")
    for fams, name in ((train, "train"), (test, "test")):
        for f in fams:
            if split_of(f) != name:
                raise ValueError(f"{f} hashes to {split_of(f)}")
    a, b = ({w for f in fs for w in FAMILIES[f]} for fs in (train, test))
    if a & b:
        raise ValueError(f"leaked names {sorted(a & b)}")


def gen(seed, family, out):
    """Write out/db.sqlite; return the question list [{"id","q","name","kind","answer"}]."""
    cust, order, ref, money = FAMILIES[family]
    rnd = random.Random(f"{family}:{seed}")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "db.sqlite")
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.execute(f"CREATE TABLE {cust}(id INTEGER PRIMARY KEY, code TEXT, name TEXT)")
    db.execute(f"CREATE TABLE {order}(id INTEGER PRIMARY KEY, {ref} TEXT, {money} INTEGER)")
    codes = rnd.sample(range(100, 999), 10)  # ids 1..10 never equal codes: wrong join gives nothing
    names = [f"N{i}-{rnd.randint(1000, 9999)}" for i in range(10)]
    db.executemany(f"INSERT INTO {cust}(code,name) VALUES(?,?)", [(f"C{c}", n) for c, n in zip(codes, names)])
    for _ in range(60):
        db.execute(f"INSERT INTO {order}({ref},{money}) VALUES(?,?)", (f"C{rnd.choice(codes)}", rnd.randint(100, 99999)))
    db.commit()
    qs = []
    for i in range(N):
        kind, name = rnd.choice(["spend", "count", "max"]), rnd.choice(names)
        agg = {"spend": f"SUM({money})", "count": "COUNT(*)", "max": f"MAX({money})"}[kind]
        r = db.execute(f"SELECT {agg} FROM {order} o JOIN {cust} c ON o.{ref}=c.code WHERE c.name=?", (name,)).fetchone()[0] or 0
        ans = str(r) if kind == "count" else f"{r / 100:.2f}"
        qs.append({"id": i, "q": f"{kind} for {name}", "name": name, "kind": kind, "answer": ans})
    db.close()
    return qs


def score(answers, questions):
    """Fraction of questions answered exactly (answers: {id: str})."""
    return sum(answers.get(q["id"]) == q["answer"] for q in questions) / len(questions)

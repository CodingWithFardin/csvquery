"""Load delimited files into an in-memory SQLite database and query them.

The point is to get an answer from a pile of CSV exports without installing a
database or remembering a dialect. Types are inferred per column so that ORDER BY
and SUM behave the way a person expects.
"""
import csv
import io
import os
import sqlite3

INTEGER, REAL, TEXT = "INTEGER", "REAL", "TEXT"


def infer_type(values):
    """Pick the narrowest type that fits every non-empty sample."""
    seen = [v for v in values if v is not None and v.strip() != ""]
    if not seen:
        return TEXT
    for candidate, check in ((INTEGER, _is_int), (REAL, _is_real)):
        if all(check(v) for v in seen):
            return candidate
    return TEXT


def _is_int(text):
    text = text.strip()
    if text.startswith("-"):
        text = text[1:]
    return text.isdigit() and not (len(text) > 1 and text[0] == "0")


def _is_real(text):
    text = text.strip()
    if text.count(".") > 1 or text.count("e") + text.count("E") > 1:
        return False
    digits = text.lstrip("-")
    if digits.isdigit() and len(digits) > 1 and digits[0] == "0":
        # an integer with a leading zero is an identifier, not a number
        return False
    try:
        float(text)
    except ValueError:
        return False
    return any(ch.isdigit() for ch in text)


def _cell(value, kind):
    if value is None or value == "":
        return None
    if kind == INTEGER:
        return int(value)
    if kind == REAL:
        return float(value)
    return value


def table_name(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    clean = "".join(ch if ch.isalnum() else "_" for ch in stem).strip("_")
    if not clean:
        clean = "data"
    if clean[0].isdigit():
        clean = "t_" + clean
    return clean.lower()


def read_rows(source):
    """Return (header, rows) from a path or a text block."""
    if os.path.exists(source):
        text = open(source, encoding="utf-8-sig", newline="").read()
    else:
        text = source
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return [], []
    header = [h.strip() or "col%d" % (i + 1) for i, h in enumerate(header)]
    width = len(header)
    rows = []
    for raw in reader:
        if not raw:
            continue
        padded = (raw + [""] * width)[:width]
        rows.append(padded)
    return header, rows


def load_table(db, name, header, rows):
    kinds = [infer_type([r[i] for r in rows]) for i in range(len(header))]
    columns = ", ".join('"%s" %s' % (col, kind) for col, kind in zip(header, kinds))
    db.execute('DROP TABLE IF EXISTS "%s"' % name)
    db.execute('CREATE TABLE "%s" (%s)' % (name, columns))
    placeholders = ", ".join("?" * len(header))
    db.executemany(
        'INSERT INTO "%s" VALUES (%s)' % (name, placeholders),
        [[_cell(value, kind) for value, kind in zip(row, kinds)] for row in rows])
    return len(rows), kinds


class Result:
    __slots__ = ("columns", "rows")

    def __init__(self, columns, rows):
        self.columns = list(columns)
        self.rows = list(rows)

    def __len__(self):
        return len(self.rows)

    def as_dicts(self):
        return [dict(zip(self.columns, row)) for row in self.rows]

    def as_csv(self):
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(self.columns)
        writer.writerows(self.rows)
        return out.getvalue()

    def as_table(self, limit=20):
        if not self.columns:
            return ""
        cells = [[("" if v is None else str(v)) for v in row] for row in self.rows[:limit]]
        widths = [len(c) for c in self.columns]
        for row in cells:
            widths = [max(w, len(v)) for w, v in zip(widths, row)]
        line = "  ".join(c.ljust(w) for c, w in zip(self.columns, widths))
        rule = "  ".join("-" * w for w in widths)
        body = ["  ".join(v.ljust(w) for v, w in zip(row, widths)) for row in cells]
        tail = ""
        if len(self.rows) > limit:
            tail = "\n(%d rows, showing %d)" % (len(self.rows), limit)
        return "\n".join([line, rule] + body) + tail


def query(files, sql, limit=None):
    """files maps table name -> path. Returns a Result for the first statement."""
    db = sqlite3.connect(":memory:")
    for name, path in files.items():
        header, rows = read_rows(path)
        if header:
            load_table(db, name, header, rows)
    try:
        cursor = db.execute(sql)
        columns = [d[0] for d in cursor.description or []]
        rows = cursor.fetchall()
    finally:
        db.close()
    if limit is not None:
        rows = rows[:limit]
    return Result(columns, rows)

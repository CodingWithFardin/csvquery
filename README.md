# csvquery

Run SQL against CSV files. No server, no import step, no dialect to remember: the
files are loaded into an in-memory SQLite database with inferred column types, then
your query runs against them.

## Install

Python 3.11+, no dependencies.

```
git clone https://github.com/CodingWithFardin/csvquery.git
cd csvquery
python -m unittest discover -s tests -t .
```

## Use

```python
from csvquery import query

result = query({"orders": "orders.csv", "customers": "customers.csv"}, """
    SELECT c.region, SUM(o.amount) AS revenue
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    GROUP BY c.region
    ORDER BY revenue DESC
""")
print(result.as_table())
```

Table names come from the file stem, lowercased and sanitised. `Result` gives you
`as_table()` for a terminal, `as_csv()` for a file, and `as_dicts()` for code.

## Type inference

Per column, narrowest type that fits every non-empty value: integers, then reals,
then text. Two deliberate choices:

- `01`, `02` stay text, because leading zeros mean identifiers, not numbers.
- An empty column is text, not a guess.

Empty cells become `NULL` rather than `0`.

## Files

- `csvquery/engine.py` - inference, loading, querying, rendering.
- `tests/` - inference cases, ragged rows, grouping and output formats.

MIT, 2026.

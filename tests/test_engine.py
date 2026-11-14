import os
import tempfile
import unittest

from csvquery.engine import infer_type, query, read_rows, table_name


class InferTest(unittest.TestCase):
    def test_integers(self):
        self.assertEqual(infer_type(["1", "2", "-3"]), "INTEGER")

    def test_leading_zero_stays_text(self):
        self.assertEqual(infer_type(["01", "02"]), "TEXT")

    def test_reals(self):
        self.assertEqual(infer_type(["1.5", "2"]), "REAL")

    def test_mixed_is_text(self):
        self.assertEqual(infer_type(["1", "x"]), "TEXT")

    def test_empty_column_is_text(self):
        self.assertEqual(infer_type(["", "  "]), "TEXT")

    def test_exponent_is_real(self):
        self.assertEqual(infer_type(["1e3"]), "REAL")


class NamingTest(unittest.TestCase):
    def test_sanitises(self):
        self.assertEqual(table_name("/tmp/Sales Data-2026.csv"), "sales_data_2026")

    def test_digit_start(self):
        self.assertEqual(table_name("2026.csv"), "t_2026")


class ReadTest(unittest.TestCase):
    def test_ragged_rows_are_padded(self):
        header, rows = read_rows("a,b\n1\n2,3,4\n")
        self.assertEqual(header, ["a", "b"])
        self.assertEqual(rows, [["1", ""], ["2", "3"]])

    def test_blank_header_gets_a_name(self):
        header, _ = read_rows(",b\n1,2\n")
        self.assertEqual(header, ["col1", "b"])


class QueryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "orders.csv")
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("id,region,amount\n1,east,10\n2,east,5.5\n3,west,7\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_sum_by_group(self):
        result = query({"orders": self.path},
                       "SELECT region, SUM(amount) AS total FROM orders GROUP BY region ORDER BY region")
        self.assertEqual(result.columns, ["region", "total"])
        self.assertEqual(result.rows[0][1], 15.5)

    def test_limit_and_dicts(self):
        result = query({"orders": self.path}, "SELECT id FROM orders ORDER BY id", limit=2)
        self.assertEqual(result.as_dicts(), [{"id": 1}, {"id": 2}])

    def test_csv_round_trip(self):
        result = query({"orders": self.path}, "SELECT id, amount FROM orders ORDER BY id")
        self.assertEqual(result.as_csv(), "id,amount\n1,10.0\n2,5.5\n3,7.0\n")

    def test_table_view_truncates(self):
        result = query({"orders": self.path}, "SELECT id FROM orders ORDER BY id")
        text = result.as_table(limit=2)
        self.assertIn("showing 2", text)


if __name__ == "__main__":
    unittest.main()

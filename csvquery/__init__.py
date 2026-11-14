"""csvquery - run SQL against CSV files without a server."""

from .engine import Result, infer_type, load_table, query

__all__ = ["Result", "infer_type", "load_table", "query"]

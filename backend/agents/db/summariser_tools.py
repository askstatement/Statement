# db_agent/summariser.py

import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List


class SummariserTools:
    """
    Local summarisation / post-processing engine.

    The LLM only designs a *pipeline* of operations; all of these operations
    run locally on ES hits (and optionally flattened aggregations).
    """

    def __init__(self):
        self.operations: Dict[str, Any] = {}
        for attr_name in dir(self):
            if not attr_name.startswith("_") and callable(getattr(self, attr_name)):
                method = getattr(self, attr_name)
                op_name = attr_name.lstrip("_")
                self.operations[op_name] = method

    def _get_operations(self) -> Dict[str, Any]:
        return self.operations

    def _execute_plan(self, plan: Dict[str, Any], results: Any) -> Any:
        op = plan.get("operation")
        if op not in self.operations:
            raise ValueError(f"Unsupported operation: {op}")
        return self.operations[op](plan, results)

    # --- helpers ---

    def _extract_field(self, doc: Any, field: str):
        """
        Extract the value of a specific (possibly nested) field from a document or list of documents.
        Supports ES hit structure with '_source'.
        """
        if isinstance(doc, list):
            return [self._extract_field(d, field) for d in doc]

        if isinstance(doc, dict) and "_source" in doc:
            doc = doc["_source"]

        if not isinstance(doc, dict):
            return None

        keys = field.split(".")
        value: Any = doc
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            elif isinstance(value, list):
                value = [v.get(key) for v in value if isinstance(v, dict) and key in v]
            else:
                return None
        return value

    def group_docs(self, docs: List[Dict[str, Any]], group_by: str):
        if not group_by:
            return {
                "all": [doc["_source"] if "_source" in doc else doc for doc in docs]
            }
        grouped: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
        for doc in docs:
            base = doc["_source"] if "_source" in doc else doc
            key = base.get(group_by, "UNKNOWN")
            grouped[key].append(doc)
        return grouped

    # --- operations ---

    def sum(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict:
        grouped = self.group_docs(results, plan.get("group_by"))
        out: Dict[Any, float] = {}
        for g, docs in grouped.items():
            total = 0.0
            for d in docs:
                val = self._extract_field(d, plan["field"])
                if val is not None:
                    total += val
            out[g] = total
        return out

    def avg(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict:
        grouped = self.group_docs(results, plan.get("group_by"))
        out: Dict[Any, float] = {}
        for g, docs in grouped.items():
            vals = [
                self._extract_field(d, plan["field"])
                for d in docs
                if self._extract_field(d, plan["field"]) is not None
            ]
            if vals:
                out[g] = statistics.mean(vals)
        return out

    def count(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict:
        grouped = self.group_docs(results, plan.get("group_by"))
        return {g: len(docs) for g, docs in grouped.items()}

    def min(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict:
        grouped = self.group_docs(results, plan.get("group_by"))
        out: Dict[Any, Any] = {}
        for g, docs in grouped.items():
            vals = [
                self._extract_field(d, plan["field"])
                for d in docs
                if self._extract_field(d, plan["field"]) is not None
            ]
            if vals:
                out[g] = min(vals)
        return out

    def max(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict:
        grouped = self.group_docs(results, plan.get("group_by"))
        out: Dict[Any, Any] = {}
        for g, docs in grouped.items():
            vals = [
                self._extract_field(d, plan["field"])
                for d in docs
                if self._extract_field(d, plan["field"]) is not None
            ]
            if vals:
                out[g] = max(vals)
            else:
                out[g] = None
        return out

    def median(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict:
        grouped = self.group_docs(results, plan.get("group_by"))
        out: Dict[Any, Any] = {}
        for g, docs in grouped.items():
            vals = [
                self._extract_field(d, plan["field"])
                for d in docs
                if self._extract_field(d, plan["field"]) is not None
            ]
            if vals:
                out[g] = statistics.median(vals)
        return out

    def mode(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict:
        grouped = self.group_docs(results, plan.get("group_by"))
        out: Dict[Any, Any] = {}
        for g, docs in grouped.items():
            vals = [
                self._extract_field(d, plan["field"])
                for d in docs
                if self._extract_field(d, plan["field"]) is not None
            ]
            try:
                out[g] = statistics.mode(vals)
            except statistics.StatisticsError:
                out[g] = None
        return out

    def stddev(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict:
        grouped = self.group_docs(results, plan.get("group_by"))
        out: Dict[Any, float] = {}
        for g, docs in grouped.items():
            vals = [
                self._extract_field(d, plan["field"])
                for d in docs
                if self._extract_field(d, plan["field"]) is not None
            ]
            if vals:
                out[g] = statistics.pstdev(vals)
        return out

    def variance(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict:
        grouped = self.group_docs(results, plan.get("group_by"))
        out: Dict[Any, float] = {}
        for g, docs in grouped.items():
            vals = [
                self._extract_field(d, plan["field"])
                for d in docs
                if self._extract_field(d, plan["field"]) is not None
            ]
            if vals:
                out[g] = statistics.pvariance(vals)
        return out

    def unique_count(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict:
        grouped = self.group_docs(results, plan.get("group_by"))
        out: Dict[Any, int] = {}
        for g, docs in grouped.items():
            vals = [
                self._extract_field(d, plan["field"])
                for d in docs
                if self._extract_field(d, plan["field"]) is not None
            ]
            out[g] = len(set(vals))
        return out

    def percentile(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict:
        percentile = plan.get("percentile")
        if percentile is None or not (0 <= percentile <= 100):
            raise ValueError("percentile must be between 0 and 100")

        grouped = self.group_docs(results, plan.get("group_by"))
        out: Dict[Any, Any] = {}

        for g, docs in grouped.items():
            values = sorted(
                self._extract_field(d, plan["field"])
                for d in docs
                if self._extract_field(d, plan["field"]) is not None
            )
            if not values:
                out[g] = None
                continue
            k = (len(values) - 1) * (percentile / 100.0)
            f = int(k)
            c = min(f + 1, len(values) - 1)
            if f == c:
                out[g] = values[f]
            else:
                out[g] = values[f] + (values[c] - values[f]) * (k - f)
        return out

    def sort(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> List:
        field = plan.get("field")
        reverse = plan.get("order", "asc").lower() == "desc"
        return sorted(
            results, key=lambda d: self._extract_field(d, field), reverse=reverse
        )

    def first_n(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> List:
        n = plan.get("n", 1)
        return results[:n]

    def filter(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> List:
        field = plan.get("field")
        conditions = plan.get("conditions", {})
        filtered: List[Dict[str, Any]] = []

        for doc in results:
            value = self._extract_field(doc, field)

            if isinstance(value, str):
                try:
                    value_dt = datetime.fromisoformat(value)
                    value = int(value_dt.timestamp())
                except Exception:
                    pass

            match = True
            for op, expected in conditions.items():
                if isinstance(expected, str):
                    try:
                        expected_dt = datetime.fromisoformat(expected)
                        expected = int(expected_dt.timestamp())
                    except Exception:
                        try:
                            expected = int(expected)
                        except Exception:
                            match = False
                            break

                try:
                    expected_int = int(expected)
                    value_int = int(value)
                except Exception:
                    match = False
                    break

                if op == "eq" and value_int != expected_int:
                    match = False
                    break
                elif op == "gte" and value_int < expected_int:
                    match = False
                    break
                elif op == "lte" and value_int > expected_int:
                    match = False
                    break
                elif op == "gt" and value_int <= expected_int:
                    match = False
                    break
                elif op == "lt" and value_int >= expected_int:
                    match = False
                    break

            if match:
                filtered.append(doc)

        return filtered

    def project(
        self, plan: Dict[str, Any], results: List[Dict[str, Any]]
    ) -> List[Dict]:
        fields = plan.get("fields", [])
        projected: List[Dict[str, Any]] = []
        for doc in results:
            new_doc: Dict[str, Any] = {}
            for f in fields:
                new_doc[f] = self._extract_field(doc, f)
            projected.append(new_doc)
        return projected

    def skip(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> List:
        n = plan.get("n", 0)
        return results[n:]

    def limit(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> List:
        n = plan.get("n", len(results))
        return results[:n]

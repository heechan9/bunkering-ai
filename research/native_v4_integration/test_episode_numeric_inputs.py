"""Malformed episode numeric cells must be input errors, not tracebacks."""
import contextlib
import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from test_config_cli import CFG
from test_ledger import EP
import cli


class EpisodeNumericInputTests(unittest.TestCase):
    def test_malformed_numbers_return_exit_two_without_outputs(self):
        cases = [(name, value) for name in
                 ("seed", "steps", "pre_refill_shortage_steps", "pre_refill_reserve_violation_steps")
                 for value in ("", "abc", "1.5", "inf")]
        cases += [(name, value) for name in
                  ("purchase_sci", "initial_inventory_value", "terminal_inventory_value",
                   "final_fuel", "inventory_adjusted_sci")
                  for value in ("", "abc", "nan", "inf")]
        for name, value in cases:
            with self.subTest(field=name, value=value), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                cfg = copy.deepcopy(CFG)
                cfg["integration"]["seed_range_inclusive"]["value"] = [1, 3]
                (root / "config.json").write_text(json.dumps(cfg))
                with EP.open(newline="") as source:
                    reader = csv.DictReader(source)
                    fields, rows = reader.fieldnames, list(reader)
                rows[0][name] = value
                with (root / "episodes.csv").open("w", newline="") as output:
                    writer = csv.DictWriter(output, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
                before = (root / "episodes.csv").read_bytes()
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    result = cli.main(["ledger", "--config", str(root / "config.json"),
                                       "--episodes", str(root / "episodes.csv"),
                                       "--out-dir", str(root / "out")])
                self.assertEqual(result, 2)
                self.assertIn(name, stderr.getvalue())
                self.assertIn("line 2", stderr.getvalue())
                self.assertFalse((root / "out").exists())
                self.assertEqual((root / "episodes.csv").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

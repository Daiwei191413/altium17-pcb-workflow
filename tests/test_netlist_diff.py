import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "netlist_diff.py"
SPEC = importlib.util.spec_from_file_location("netlist_diff", MODULE_PATH)
netlist_diff = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(netlist_diff)


class NetlistDiffTests(unittest.TestCase):
    def write_csv(self, folder: Path, name: str, rows: str) -> Path:
        path = folder / name
        path.write_text("refdes,pin,net\n" + rows, encoding="utf-8")
        return path

    def test_detects_changed_added_and_removed_endpoints(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = self.write_csv(root, "before.csv", "U1,1,VCC\nU1,2,RESET\nR1,1,VCC\n")
            after = self.write_csv(root, "after.csv", "U1,1,VCC\nU1,2,GPIO0\nC1,1,VCC\n")
            delta = netlist_diff.compare(
                netlist_diff.load_connections(before), netlist_diff.load_connections(after)
            )
            self.assertEqual(delta["changed"][0]["before_net"], "RESET")
            self.assertEqual(delta["added"][0]["refdes"], "C1")
            self.assertEqual(delta["removed"][0]["refdes"], "R1")

    def test_rejects_duplicate_endpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_csv(Path(temp), "bad.csv", "U1,1,VCC\nU1,1,GND\n")
            with self.assertRaisesRegex(ValueError, "duplicate endpoint"):
                netlist_diff.load_connections(path)


if __name__ == "__main__":
    unittest.main()


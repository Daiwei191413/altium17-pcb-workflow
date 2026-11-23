import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "gate_audit.py"
SPEC = importlib.util.spec_from_file_location("gate_audit", MODULE_PATH)
gate_audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gate_audit)


class GateAuditTests(unittest.TestCase):
    def base_state(self):
        digest = "a" * 64
        gates = []
        for gate_id in gate_audit.GATE_IDS:
            gates.append(
                {
                    "id": gate_id,
                    "status": "pass",
                    "reviewed_input": digest,
                    "evidence": [f"evidence/{gate_id}.md"],
                }
            )
        return {"schema": 1, "project_id": "BOARD-1", "input_digest": digest, "gates": gates}

    def test_accepts_sequential_passes(self):
        self.assertEqual(gate_audit.audit(self.base_state()), [])

    def test_rejects_stale_pass(self):
        state = self.base_state()
        state["gates"][3]["reviewed_input"] = "b" * 64
        self.assertTrue(any("G3 pass is stale" in item for item in gate_audit.audit(state)))

    def test_rejects_pass_after_hold(self):
        state = self.base_state()
        state["gates"][1] = {"id": "G1", "status": "hold", "reasons": ["ERC missing"]}
        issues = gate_audit.audit(state)
        self.assertTrue(any("G2 cannot pass while G1 is hold" in item for item in issues))


if __name__ == "__main__":
    unittest.main()


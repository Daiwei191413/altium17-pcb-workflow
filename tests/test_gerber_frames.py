import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
try:
    from audit_gerber_frames import LineString, Point, box, inspect_frames
except ModuleNotFoundError as error:
    if error.name not in {"gerbonara", "shapely"}:
        raise
    raise unittest.SkipTest("Install gerbonara and shapely for the optional CAM tests")


class FrameAuditTests(unittest.TestCase):
    def setUp(self):
        self.pads = {"R1": [Point(1, 1)], "R2": [Point(3, 1)]}
        self.mask = [box(.6, .6, 1.4, 1.4), box(2.6, .6, 3.4, 1.4)]
        self.sides = [((0, 0), (4, 0)), ((0, 2), (4, 2)),
                      ((0, 0), (0, 2)), ((4, 0), (4, 2)), ((2, 0), (2, 2))]

    def statuses(self, manual=()):
        lines = [LineString(side) for side in self.sides]
        return [row[1] for row in inspect_frames(lines, [.15], self.mask, self.pads, manual, .254)]

    def test_shared_wall_closes_two_independent_cells(self):
        self.assertEqual(self.statuses(), ["closed", "closed"])

    def test_group_enclosure_and_broken_divider(self):
        self.sides[-1] = ((2, 0), (2, 1.999))
        self.assertEqual(self.statuses(), ["open_or_unverified"] * 2)

    def test_inside_center_with_outside_mask_edge(self):
        self.mask[0] = box(-.01, .6, 1.4, 1.4)
        self.assertEqual(self.statuses(), ["open_or_unverified", "closed"])

    def test_line_edge_clearance_and_manual_scope(self):
        self.mask[0] = box(.2, .6, 1.4, 1.4)
        self.assertEqual(self.statuses(["R2"]), ["clearance_failed", "manual"])
        with self.assertRaises(ValueError):
            self.statuses(["R3"])

    def test_unmapped_pad_blocks_result(self):
        self.pads["R1"].append(Point(20, 20))
        with self.assertRaises(ValueError):
            self.statuses()

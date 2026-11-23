import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from protel_to_csv import parse


class TestProtel(unittest.TestCase):
    def test_component_and_named_pin(self):
        data = "[\nU-1\nDFN\nLNA\n]\n(\nGND\nU-1-EP\n)"
        self.assertEqual(parse(data), [("U-1", "EP", "GND")])

    def test_duplicate(self):
        with self.assertRaises(ValueError):
            parse("(\nGND\nU1-1\n)\n(\nVDD\nU1-1\n)")

    def test_incomplete_or_wrong_format(self):
        for data in ["(\nGND\nU1-1", "refdes,pin,net", "(\nGND\nU-1-EP\n)"]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse(data)

    def test_multiple_nets(self):
        self.assertEqual(parse("(\nVBIAS\nL2-1\n)\n(\nRFIN\nL2-2\n)"),
                         [("L2","1","VBIAS"), ("L2","2","RFIN")])

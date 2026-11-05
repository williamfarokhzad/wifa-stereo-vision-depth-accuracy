import contextlib
import io
import math
import tempfile
import unittest
from fractions import Fraction as F
from pathlib import Path

from stereo_audit import Sample, audit, depth_and_bounds, main, read_samples

ROOT = Path(__file__).resolve().parents[1]


class GeometryTests(unittest.TestCase):
    def test_bounds_against_independent_camera_projections(self):
        f, b = 900, F(2, 25)
        # Project world X from two distinct camera centers. Validate the
        # inverse interval by projecting its endpoints back to pixel space.
        for z in [F(1, 2), F(1), F(2), F(3), F(36, 5), F(9), F(21, 2)]:
            for x in [F(-1, 10), F(0), F(1, 10)]:
                ul, ur = f * x / z + 320, f * (x - b) / z + 320
                for noise in [F(-1, 4), F(-1, 10), F(0), F(1, 10), F(1, 4)]:
                    with self.subTest(z=z, x=x, noise=noise):
                        d = float(ul - ur + noise)
                        point, (near, far) = depth_and_bounds(f, float(b), d, 0.25)
                        self.assertLessEqual(near - 1e-12, float(z))
                        self.assertGreaterEqual(far + 1e-12, float(z))
                        self.assertAlmostEqual(900 * float(b) / near, d + 0.25)
                        self.assertAlmostEqual(900 * float(b) / far, d - 0.25)
                        self.assertLess(near, point)
                        self.assertLess(point, far)

    def test_far_bound_diverges_at_and_below_zero_true_disparity(self):
        self.assertEqual(depth_and_bounds(900, 0.08, 0.25, 0.25), (288.0, None))
        self.assertIsNone(depth_and_bounds(900, 0.08, 0.125, 0.25)[1])

    def test_asymmetry_and_zero_noise(self):
        point, (near, far) = depth_and_bounds(900, 0.08, 10, 0.25)
        self.assertGreater(far - point, point - near)
        self.assertEqual(depth_and_bounds(900, 0.08, 10, 0), (7.2, (7.2, 7.2)))

    def test_bad_calibration(self):
        for args in [(math.nan,.08,36,.25), (900,0,36,.25), (900,.08,0,.25),
                     (900,.08,36,-.25), (900,.08,36,math.inf), (1e300,1e300,36,0)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                depth_and_bounds(*args)


class AuditTests(unittest.TestCase):
    def test_invalid_rows_stay_in_coverage_denominator(self):
        group = audit([Sample(str(i), "glass", 2, d) for i, d in
                       enumerate([None, math.nan, math.inf, -1, 0, 30])],
                      900, .08, .25)["glass"]
        self.assertEqual(group["total"], 6)
        self.assertAlmostEqual(group["errors"][0], 400)
        self.assertEqual(len(group["errors"]), 1)
        self.assertEqual((group["inside"], group["bounded"]), (0, 1))

    def test_unbounded_valid_rows_count_for_error_but_not_intervals(self):
        group = audit([Sample("x", "far", 288, .25)], 900, .08, .25)["far"]
        self.assertEqual(group, {"total": 1, "errors": [0.0], "bounded": 0, "inside": 0})

    def test_bad_csvs_rejected(self):
        header = "sample,surface,reference_m,disparity_px\n"
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "broken.csv"
            for body in ["", "x,test,1\n", "x,test,NaN,30\n",
                         "x,test,1,30\nx,test,1,31\n", "x,test,1,30,0\n"]:
                with self.subTest(body=body), self.assertRaises(ValueError):
                    file.write_text(header + body, encoding="utf-8")
                    read_samples(file)

    def cli(self, file, max_error="25", min_fraction=".9"):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main([str(file), "--focal-px", "900", "--baseline-m", ".08",
                           "--delta-px", ".25", "--max-error-mm", max_error,
                           "--min-valid-fraction", min_fraction])
        return status, output.getvalue().splitlines()[1:]

    def test_fixture_stats_and_exit_codes(self):
        textured = "textured | 3/3 | +0.04 | 7.41 | 11.17 | 3/3 | PASS"
        self.assertEqual(self.cli(ROOT / "examples/textured.csv"), (0, [textured]))
        self.assertEqual(self.cli(ROOT / "examples/mixed.csv"),
                         (1, ["glossy | 1/3 | +400.00 | 400.00 | 400.00 | 0/1 | FAIL", textured]))
        self.assertEqual(self.cli(ROOT / "examples/far.csv"),
                         (1, ["far | 2/3 | +6.49 | 216.19 | 222.68 | 0/2 | FAIL"]))

    def test_coverage_independently_blocks_error_pass(self):
        self.assertEqual(self.cli(ROOT / "examples/mixed.csv", max_error="401")[0], 1)
        self.assertEqual(self.cli(ROOT / "examples/mixed.csv", "401", ".33")[0], 0)

    def test_all_invalid_fails_even_when_no_depth_error_can_be_computed(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "empty_depth.csv"
            file.write_text("sample,surface,reference_m,disparity_px\nx,glossy,1,\n")
            self.assertEqual(self.cli(file), (1, ["glossy | 0/1 | n/a | n/a | n/a | n/a | FAIL"]))


if __name__ == "__main__":
    unittest.main()

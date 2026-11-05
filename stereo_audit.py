"""Audit optical-axis depth from saved rectified stereo disparities."""
import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

FIELDS = ["sample", "surface", "reference_m", "disparity_px"]


def positive(value, label):
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be positive and finite")
    return value


def depth_and_bounds(focal_px, baseline_m, disparity_px, delta_px):
    """Return depth and optional closed interval for bounded disparity error."""
    scale = positive(focal_px, "focal length") * positive(baseline_m, "baseline")
    positive(scale, "focal length times baseline")
    positive(disparity_px, "disparity")
    if not math.isfinite(delta_px) or delta_px < 0:
        raise ValueError("disparity error must be finite and nonnegative")
    z = positive(scale / disparity_px, "depth")
    if disparity_px <= delta_px:
        return z, None
    return z, (positive(scale / (disparity_px + delta_px), "near bound"),
               positive(scale / (disparity_px - delta_px), "far bound"))


@dataclass(frozen=True)
class Sample:
    name: str
    surface: str
    reference_m: float
    disparity_px: float | None


def read_samples(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, strict=True)
        if reader.fieldnames != FIELDS:
            raise ValueError("expected header: " + ",".join(FIELDS))
        samples = []
        seen = set()
        for row in reader:
            try:
                name, surface, ref, disparity = (row[k] for k in FIELDS)
                if None in row or None in (name, surface, ref, disparity):
                    raise ValueError("wrong number of columns")
                name, surface = name.strip(), surface.strip()
                if not name or not surface or name in seen:
                    raise ValueError("sample and surface must be set; sample IDs must be unique")
                number = float(disparity) if disparity.strip() else None
                samples.append(Sample(name, surface, positive(float(ref), "reference_m"), number))
                seen.add(name)
            except ValueError as exc:
                raise ValueError(f"CSV line {reader.line_num}: {exc}") from exc
    if not samples:
        raise ValueError("CSV has no samples")
    return samples


def audit(samples, focal_px, baseline_m, delta_px):
    # Validate calibration even when all disparity values are missing.
    depth_and_bounds(focal_px, baseline_m, 1.0, delta_px)
    groups = {}
    for sample in samples:
        group = groups.setdefault(sample.surface, {"total": 0, "errors": [], "bounded": 0, "inside": 0})
        group["total"] += 1
        d = sample.disparity_px
        if d is None or not math.isfinite(d) or d <= 0:
            continue
        depth, bounds = depth_and_bounds(focal_px, baseline_m, d, delta_px)
        error_mm = 1000 * (depth - sample.reference_m)
        if not math.isfinite(error_mm):
            raise ValueError(f"{sample.name}: depth error exceeds numeric range")
        group["errors"].append(error_mm)
        if bounds is not None:
            group["bounded"] += 1
            group["inside"] += bounds[0] <= sample.reference_m <= bounds[1]
    return groups


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file")
    parser.add_argument("--focal-px", type=float, required=True)
    parser.add_argument("--baseline-m", type=float, required=True)
    parser.add_argument("--delta-px", type=float, required=True)
    parser.add_argument("--max-error-mm", type=float, required=True)
    parser.add_argument("--min-valid-fraction", type=float, required=True)
    args = parser.parse_args(argv)
    try:
        positive(args.max_error_mm, "maximum error")
        if not 0 < args.min_valid_fraction <= 1:
            raise ValueError("minimum valid fraction must be in (0, 1]")
        groups = audit(read_samples(args.csv_file), args.focal_px, args.baseline_m, args.delta_px)
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))

    print("surface | valid/total | bias mm | MAE mm | worst mm | reference in bounds | result")
    passed_all = True
    for name, g in sorted(groups.items()):
        errors = g["errors"]
        worst = max(map(abs, errors), default=None)
        passed = worst is not None and len(errors) / g["total"] >= args.min_valid_fraction and (
            worst <= args.max_error_mm or math.isclose(worst, args.max_error_mm, rel_tol=1e-12, abs_tol=1e-9)
        )
        passed_all &= passed
        stats = f"{mean(errors):+.2f} | {mean(map(abs, errors)):.2f} | {worst:.2f}" if errors else "n/a | n/a | n/a"
        intervals = f"{g['inside']}/{g['bounded']}" if g["bounded"] else "n/a"
        result = "PASS" if passed else "FAIL"
        print(f"{name} | {len(errors)}/{g['total']} | {stats} | {intervals} | {result}")
    return 0 if passed_all else 1


if __name__ == "__main__":
    raise SystemExit(main())

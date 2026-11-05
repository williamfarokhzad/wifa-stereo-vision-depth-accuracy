# Stereo vision depth accuracy in Python

Audit saved stereo disparities against independent depth references. The script reports valid returns, signed bias, mean absolute error, worst error and agreement with a finite disparity error interval for each surface group. The examples use invented data. No camera or robot is required.

[Full lesson at WIFA Robotics](https://wifarobotics.com/learn/stereo-vision-depth-accuracy/)

## Get started

1. Install [Python 3.11 or newer](https://www.python.org/downloads/). In Terminal on macOS or Linux run `python3 --version`. On Windows open PowerShell, run `py -3 --version` and use `py -3` in place of `python3`. If the launcher is unavailable, check `python --version` and use that command if it points to Python 3.11 or newer.
2. On GitHub, choose **Code → Download ZIP**, extract the ZIP, and open a terminal in the folder containing `stereo_audit.py`. No pip installs or virtual environment are needed.
3. Run these examples and tests. Keep each command on one line.

```sh
python3 stereo_audit.py examples/textured.csv --focal-px 900 --baseline-m 0.08 --delta-px 0.25 --max-error-mm 25 --min-valid-fraction 0.9
python3 stereo_audit.py examples/mixed.csv --focal-px 900 --baseline-m 0.08 --delta-px 0.25 --max-error-mm 25 --min-valid-fraction 0.9
python3 stereo_audit.py examples/far.csv --focal-px 900 --baseline-m 0.08 --delta-px 0.25 --max-error-mm 25 --min-valid-fraction 0.9
python3 -m unittest discover -s tests -v
```

| File | Group | Valid / total | Bias (mm) | MAE (mm) | Worst (mm) | Reference in bounds | Result |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| textured.csv | textured | 3/3 | +0.04 | 7.41 | 11.17 | 3/3 | PASS |
| mixed.csv | glossy | 1/3 | +400.00 | 400.00 | 400.00 | 0/1 | FAIL |
| mixed.csv | textured | 3/3 | +0.04 | 7.41 | 11.17 | 3/3 | PASS |
| far.csv | far | 2/3 | +6.49 | 216.19 | 222.68 | 0/2 | FAIL |

Exit 0 means all groups meet both thresholds. Exit 1 means at least one fails, including the intentional failures above. Exit 2 indicates invalid arguments or input. In Bash use `echo $?` immediately after a command to inspect its exit status; in PowerShell use `$LASTEXITCODE`.

## Supply your own saved data

Use the exact CSV header `sample,surface,reference_m,disparity_px`. Give each observation a unique ID and a surface group. For separate distance bands, use labels such as `matte_near` and `matte_far`. A sample is one expected reference observation, even if the camera returned no usable disparity. Leave that cell blank when a mask or device sentinel indicates invalid data. Nonpositive or nonfinite numbers are also counted as invalid. Positive device sentinels must be masked before exporting.

The reference is optical axis Z in meters in the first rectified camera frame, measured independently of the stereo result. The focal length is the rectified horizontal focal length in pixels, and baseline is the distance between camera centers in meters. Use a horizontal rectified pair with equal x principal points and d = u_left − u_right. Otherwise use the calibrated reprojection model and compare its output Z directly; this script does not accept Q or unrectified images.

Error is estimated minus reference depth. A small bias can hide large errors of opposite sign; use MAE and worst error too. The interval assumes a chosen deterministic bound on disparity error and exact calibration. Reference agreement is counted only where both interval ends are finite, with its own denominator. It is a diagnostic, not a confidence percentage or a condition for the PASS decision.

## Troubleshooting

- **No file found:** list the folder contents and check that both `stereo_audit.py` and `examples` are there.
- **Depth is 16 times too small:** for the signed 16 bit output described by OpenCV StereoBM or StereoSGBM, mask invalid values first and convert the fixed point values to pixels by dividing by 16 once. Check your API's format rather than assuming all disparity sources use this scale.
- **No interval for a valid return:** if disparity is at or below the assumed error bound, the permitted true disparity can approach zero. The point estimate can still be compared against its reference; the finite interval check is unavailable.
- **The model fits matte targets and fails on shiny ones:** inspect invalid masks, ambiguous texture, saturation, occlusion, calibration and synchronization before changing tolerances. Use separate development and acceptance captures.

These examples do not measure a stereo camera or establish a robot safety limit. For real acceptance use repeat captures, representative targets and an independent reference with known uncertainty. Confirm any result against your calibrated camera model. References: [OpenCV calibration and reprojection](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html) and [Basler 3D data and depth error](https://docs.baslerweb.com/stereovisard/rc_visard/en/stereo_general).

The editable charts are in `diagrams/`. Run `python3 diagrams/draw.py` to regenerate the SVGs from the calculation and sample data. The WebP copies are for viewing and are not needed by the program.

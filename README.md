# ImageLab — Image Studio

A modern **PySide6 Windows desktop application** for interactive image processing, featuring a single-window 3-pane Studio interface.

## Studio Interface

Everything is on one unified screen — **no tabs for features**:
- **Left Sidebar**: Image upload, RGB/Gray toggle, dynamic feature picker accordion, parameter controls (`ParamPanel`), and action buttons (Apply, Live Preview, Use as Input, Reset, Save).
- **Original Pane**: Interactive image viewer showing the current working input with dimensions and channel badges.
- **Result Pane**: Live output viewer with support for single-view, 3-grid edge inspection (X, Y, Combined), and zoom-out preview scaling for hybrid images.
- **Analysis Pane**: Multi-tab analysis window featuring:
  - 📊 **Histogram**: Per-channel histogram & PDF with an Original vs. Result overlay toggle.
  - 📈 **CDF**: Per-channel cumulative distribution function curves.
  - 🌐 **Spectrum**: 2D log-magnitude Fourier frequency spectrum.
  - 🔍 **Details**: Feature-specific extras (frequency filter masks, hybrid low/high components).

---

## Quick Start (Windows)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
```
*(Or simply double-click `run.bat`)*

---

## Architecture

```
core/         Pure NumPy/OpenCV algorithms — NEVER imports Qt or gui/
gui/          PySide6 single-window studio views and generic components
main.py       Entry point: dark Fusion theme, logging, exception hook
```

### Architecture Rules

1. **Three layers**: `core/` (pure logic), `gui/` (views), `main.py` (bootstrap).
2. **OOP**: Every noise, filter, edge detector, equalizer, normalizer, and frequency filter is a **class** inheriting from `core.base.ImageProcessor`.
3. **Pluggable features**: Core modules expose dictionary registries (`NOISES`, `FILTERS`, `EDGES`, `HISTOGRAM_TOOLS`, `FREQ_FILTERS`). The GUI dynamically derives its feature picker and parameter sliders from `params_schema`.
4. **No redundant computation**: shared `convolve()`, cached `.gray`, histogram/CDF analyzed once per image change, FFT cached per image.
5. **Errors**: Core raises `AppError` subclasses. GUI captures them through `run_safely` and reports them via `show_error`.
6. **Assignment constraints**: OpenCV is allowed ONLY for image I/O and Canny edge detection. All other algorithms are written from scratch with NumPy.

---

## How to Add a New Feature

Adding a new feature requires **zero GUI code modifications**:
1. Implement your processor class inheriting from `ImageProcessor` in the appropriate `core/` file.
2. Define its `name` and `params_schema` dictionary (specifying `type`, `min`, `max`, `step`, `default`, `label`).
3. Add the class to the module's dictionary registry (e.g., `FILTERS[NewFilter.name] = NewFilter`).
4. The Image Studio sidebar will automatically create the radio option, build its sliders and spin boxes, and route execution!

---

## Team Ownership

| Responsibility | Owner |
|---|---|
| `core/base.py`, `core/image_data.py` | Member 1 |
| GUI (`gui/`) + `main.py` | UI Developer |
| `core/noise.py`, `core/filters.py` | Member 2 |
| `core/edges.py`, `core/histogram.py` | Member 3 |
| `core/frequency.py` | Member 4 |

# CV Task 1 - Image Processing Studio

Flask web app (Original | Result | Analysis) over a pure-Python/NumPy `core/` package.

## Run
```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py        # http://127.0.0.1:5000
```

## Team rules
- Every function in `core/` takes a numpy array (+ params) and returns a numpy array (uint8) - NO Flask/UI code inside `core/`.
- OpenCV is allowed ONLY for: reading images, adding Gaussian/Uniform noise, Canny.
- Everything else is from scratch (NumPy only). FFT may use numpy.fft.
- Add a new feature = write the function in `core/` + one entry in `web/registry.py`.

## Ownership
| File | Owner |
|------|-------|
| app.py, web/*, templates, static | UI (you) |
| core/io_utils.py, noise.py | |
| core/filters.py | |
| core/edges.py | |
| core/histogram.py, equalize.py, normalize.py, color.py | |
| core/frequency.py, hybrid.py | |
| report/report.md | all |

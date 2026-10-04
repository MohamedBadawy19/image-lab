"""Flask API (UI owner). Contract - do not rename:

GET  /                 -> index.html
GET  /api/features     -> JSON list built from web.registry.FEATURES (without 'fn')
POST /api/upload       -> multipart: file, slot ('main'|'second'), gray ('0'|'1')
                          returns {image_id, image(b64 png), width, height, is_gray}
POST /api/apply        -> JSON {image_id, feature, params, second_image_id?}
                          returns {result(b64 png), analysis_original, analysis_result, spectrum(b64 png)}
POST /api/commit       -> JSON {image_id}   ("Use result as new input": last result becomes the original)
POST /api/reset        -> JSON {image_id}   (back to the first uploaded image)

Images are kept server-side in a dict keyed by image_id (no DB).
"""
import uuid
import base64
import traceback
import numpy as np
import cv2
from flask import Blueprint, render_template, jsonify, request
from web.registry import FEATURES
from core import io_utils, histogram, frequency

bp = Blueprint("main", __name__)
STORE = {}  # image_id -> {'original': arr, 'current': arr, 'last_result': arr, 'first': arr}


# ──────────────────────────── TEMP FALLBACK helpers ────────────────────────────
# TEMP FALLBACK - remove when core/io_utils.py is done
def _fallback_decode(file_bytes: bytes, gray: bool = False) -> np.ndarray:
    """Decode uploaded file bytes into a numpy array (RGB or gray)."""
    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    flags = cv2.IMREAD_GRAYSCALE if gray else cv2.IMREAD_COLOR
    img = cv2.imdecode(arr, flags)
    if img is None:
        raise ValueError("Could not decode image")
    if not gray and img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


def _fallback_encode(img: np.ndarray) -> str:
    """Encode numpy array to base64 PNG data URI."""
    if img.ndim == 3:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img
    ok, buf = cv2.imencode(".png", img_bgr)
    if not ok:
        raise ValueError("Could not encode image")
    b64 = base64.b64encode(buf).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _fallback_to_uint8(img: np.ndarray) -> np.ndarray:
    """Clip to [0,255] and cast to uint8."""
    return np.clip(img, 0, 255).astype(np.uint8)


def _decode(file_bytes, gray=False):
    """Try core.io_utils first, fall back to local helper."""
    try:
        return io_utils.decode_image(file_bytes, gray)
    except NotImplementedError:
        return _fallback_decode(file_bytes, gray)


def _encode(img):
    """Try core.io_utils first, fall back to local helper."""
    try:
        return io_utils.encode_png_b64(img)
    except NotImplementedError:
        return _fallback_encode(img)


def _to_uint8(img):
    """Try core.io_utils first, fall back to local helper."""
    try:
        return io_utils.to_uint8(img)
    except NotImplementedError:
        return _fallback_to_uint8(img)
# ──────────────────────────── END TEMP FALLBACK ────────────────────────────────


@bp.route("/")
def index():
    """Serve the single-page app."""
    return render_template("index.html")


@bp.route("/api/features", methods=["GET"])
def get_features():
    """Return the feature registry (without 'fn') so the frontend can build UI."""
    out = {}
    for key, feat in FEATURES.items():
        entry = {k: v for k, v in feat.items() if k != "fn"}
        out[key] = entry
    return jsonify(out)


@bp.route("/api/upload", methods=["POST"])
def upload():
    """Accept an image upload. Returns base64 preview + metadata."""
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400

    slot = request.form.get("slot", "main")          # 'main' or 'second'

    try:
        file_bytes = f.read()
        # Always decode in original color
        img = _decode(file_bytes, gray=False)
    except Exception as e:
        return jsonify({"error": f"Decode failed: {e}"}), 400

    img_id = str(uuid.uuid4())
    STORE[img_id] = {
        "original": img.copy(),
        "current": img.copy(),
        "color_version": img.copy(),
        "last_result": None,
        "first": img.copy(),
        "is_originally_gray": (img.ndim == 2),
    }

    h, w = img.shape[:2]
    is_gray = (img.ndim == 2)

    return jsonify({
        "image_id": img_id,
        "image": _encode(img),
        "width": w,
        "height": h,
        "is_gray": is_gray,
        "can_toggle_gray": (img.ndim == 3),
    })


@bp.route("/api/grayscale", methods=["POST"])
def set_grayscale():
    """Toggle grayscale mode for the loaded image after upload."""
    data = request.get_json(silent=True)
    if not data or "image_id" not in data:
        return jsonify({"error": "Missing image_id"}), 400

    image_id = data["image_id"]
    if image_id not in STORE:
        return jsonify({"error": "Unknown image_id"}), 404

    to_gray = bool(data.get("gray", False))
    entry = STORE[image_id]

    if entry.get("is_originally_gray", False):
        curr = entry["current"]
        return jsonify({
            "image_id": image_id,
            "image": _encode(curr),
            "width": curr.shape[1],
            "height": curr.shape[0],
            "is_gray": True,
            "can_toggle_gray": False,
        })

    if to_gray:
        curr = entry["current"]
        if curr.ndim == 3:
            curr_gray = cv2.cvtColor(curr, cv2.COLOR_RGB2GRAY)
            entry["current"] = curr_gray
            entry["original"] = curr_gray.copy()
    else:
        if "color_version" in entry:
            entry["current"] = entry["color_version"].copy()
            entry["original"] = entry["color_version"].copy()

    entry["last_result"] = None
    curr = entry["current"]
    h, w = curr.shape[:2]

    return jsonify({
        "image_id": image_id,
        "image": _encode(curr),
        "width": w,
        "height": h,
        "is_gray": (curr.ndim == 2),
        "can_toggle_gray": True,
    })


@bp.route("/api/apply", methods=["POST"])
def apply_feature():
    """Apply a feature to the current image. Returns result + analysis + spectrum."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    image_id = data.get("image_id")
    feature_key = data.get("feature")
    params = data.get("params", {})
    second_image_id = data.get("second_image_id")

    if image_id not in STORE:
        return jsonify({"error": "Unknown image_id"}), 404
    if feature_key not in FEATURES:
        return jsonify({"error": f"Unknown feature: {feature_key}"}), 400

    feat = FEATURES[feature_key]
    fn = feat["fn"]

    # Cast parameters to declared types
    declared = {p["name"]: p for p in feat["params"]}
    cast_params = {}
    for pname, pval in params.items():
        if pname in declared:
            ptype = declared[pname]["type"]
            if ptype == "int":
                cast_params[pname] = int(pval)
            elif ptype == "float":
                cast_params[pname] = float(pval)
            else:
                cast_params[pname] = str(pval)

    current = STORE[image_id]["current"]

    try:
        # For hybrid / second_image features, pass second image as 2nd positional arg
        if feat.get("second_image") and second_image_id:
            if second_image_id not in STORE:
                return jsonify({"error": "Unknown second_image_id"}), 404
            second_img = STORE[second_image_id]["current"]
            result = fn(current, second_img, **cast_params)
        else:
            result = fn(current, **cast_params)

        result = _to_uint8(result)
    except NotImplementedError:
        return jsonify({"error": "Feature not implemented yet"}), 501
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    STORE[image_id]["last_result"] = result

    # Analysis (histogram) - graceful fallback
    analysis_original = None
    analysis_result = None
    try:
        analysis_original = histogram.analyze(current)
    except (NotImplementedError, Exception):
        pass
    try:
        analysis_result = histogram.analyze(result)
    except (NotImplementedError, Exception):
        pass

    # Spectrum (FFT) - graceful fallback
    spectrum = None
    try:
        spec_img = frequency.fft_spectrum(result)
        spectrum = _encode(_to_uint8(spec_img))
    except (NotImplementedError, Exception):
        pass

    return jsonify({
        "result": _encode(result),
        "analysis_original": analysis_original,
        "analysis_result": analysis_result,
        "spectrum": spectrum,
    })


@bp.route("/api/commit", methods=["POST"])
def commit():
    """Use last result as the new current image (chain operations)."""
    data = request.get_json(silent=True)
    if not data or "image_id" not in data:
        return jsonify({"error": "Missing image_id"}), 400

    image_id = data["image_id"]
    if image_id not in STORE:
        return jsonify({"error": "Unknown image_id"}), 404

    entry = STORE[image_id]
    if entry["last_result"] is None:
        return jsonify({"error": "No result to commit"}), 400

    entry["current"] = entry["last_result"].copy()
    entry["last_result"] = None

    return jsonify({
        "image_id": image_id,
        "image": _encode(entry["current"]),
        "width": entry["current"].shape[1],
        "height": entry["current"].shape[0],
        "is_gray": entry["current"].ndim == 2,
    })


@bp.route("/api/reset", methods=["POST"])
def reset():
    """Reset back to the first uploaded image."""
    data = request.get_json(silent=True)
    if not data or "image_id" not in data:
        return jsonify({"error": "Missing image_id"}), 400

    image_id = data["image_id"]
    if image_id not in STORE:
        return jsonify({"error": "Unknown image_id"}), 404

    entry = STORE[image_id]
    entry["current"] = entry["first"].copy()
    entry["last_result"] = None

    return jsonify({
        "image_id": image_id,
        "image": _encode(entry["current"]),
        "width": entry["current"].shape[1],
        "height": entry["current"].shape[0],
        "is_gray": entry["current"].ndim == 2,
    })

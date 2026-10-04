/**
 * main.js - App state, upload, /api/apply calls, debounce, commit/reset,
 * before/after slider, download, history, edge direction grid, hybrid scale.
 */

/* ──────── Global app state ──────── */
window.APP = {
  features: {},             // Feature definitions from /api/features
  selectedFeature: null,    // Currently selected feature key
  mainImageId: null,        // Server-side image_id for the main image
  secondImageId: null,      // Server-side image_id for the second (hybrid) image
  originalSrc: null,        // Base64 src of the current "original" image
  resultSrc: null,          // Base64 src of the last result
  history: ['Original'],    // Step history
  lastAnalysis: null,       // { original, result } analysis data
  viewMode: 'ba',           // 'ba' (before/after) or 'plain'
};

/* ──────── Debounce utility ──────── */
function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

/** Debounced apply for live preview (250ms) */
const debouncedApply = debounce(() => applyFeature(), 250);

/* ──────── Toast notifications ──────── */
function showToast(msg, type = 'error') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

/* ──────── Upload ──────── */
function initUpload() {
  // Main upload zone
  const zoneMain = document.getElementById('upload-zone-main');
  const inputMain = document.getElementById('file-input-main');

  zoneMain.addEventListener('click', () => inputMain.click());
  zoneMain.addEventListener('dragover', e => { e.preventDefault(); zoneMain.classList.add('drag-over'); });
  zoneMain.addEventListener('dragleave', () => zoneMain.classList.remove('drag-over'));
  zoneMain.addEventListener('drop', e => {
    e.preventDefault();
    zoneMain.classList.remove('drag-over');
    if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0], 'main');
  });
  inputMain.addEventListener('change', () => {
    if (inputMain.files.length) uploadFile(inputMain.files[0], 'main');
  });

  // Second upload zone (hybrid)
  const zoneSecond = document.getElementById('upload-zone-second');
  const inputSecond = document.getElementById('file-input-second');

  zoneSecond.addEventListener('click', () => inputSecond.click());
  zoneSecond.addEventListener('dragover', e => { e.preventDefault(); zoneSecond.classList.add('drag-over'); });
  zoneSecond.addEventListener('dragleave', () => zoneSecond.classList.remove('drag-over'));
  zoneSecond.addEventListener('drop', e => {
    e.preventDefault();
    zoneSecond.classList.remove('drag-over');
    if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0], 'second');
  });
  inputSecond.addEventListener('change', () => {
    if (inputSecond.files.length) uploadFile(inputSecond.files[0], 'second');
  });
}

/** Upload a file to /api/upload. Slot is 'main' or 'second'. */
async function uploadFile(file, slot) {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('slot', slot);

  try {
    const resp = await fetch('/api/upload', { method: 'POST', body: fd });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Upload failed');

    if (slot === 'main') {
      window.APP.mainImageId = data.image_id;
      window.APP.originalSrc = data.image;
      window.APP.resultSrc = null;
      window.APP.history = ['Original'];

      // Setup Grayscale toggle for after-upload control
      const grayToggle = document.getElementById('gray-toggle');
      const grayWrapper = document.getElementById('gray-toggle-wrapper');
      if (grayWrapper) grayWrapper.classList.add('ready');
      if (grayToggle) {
        grayToggle.checked = data.is_gray;
        grayToggle.disabled = !data.can_toggle_gray;
      }

      // Show original
      showOriginal(data.image, data.width, data.height, data.is_gray);

      // Clear result
      document.getElementById('body-result').innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🔬</div>
          <p>Apply a feature to see results</p>
        </div>`;

      // Enable buttons
      document.getElementById('btn-apply').disabled = !window.APP.selectedFeature;
      document.getElementById('btn-reset').disabled = false;
      updateHistory();

      showToast('Image uploaded successfully', 'success');
    } else {
      window.APP.secondImageId = data.image_id;
      // Show thumbnail
      const thumb = document.getElementById('second-thumb');
      thumb.innerHTML = `<img src="${data.image}" alt="Second image">`;
      showToast('Second image uploaded', 'success');
    }
  } catch (e) {
    showToast(e.message, 'error');
  }
}

/** Initialize Grayscale toggle to switch between color and grayscale after upload */
function initGrayToggle() {
  const grayToggle = document.getElementById('gray-toggle');
  if (!grayToggle) return;

  grayToggle.addEventListener('change', async () => {
    if (!window.APP.mainImageId) return;

    try {
      const resp = await fetch('/api/grayscale', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_id: window.APP.mainImageId, gray: grayToggle.checked }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error);

      window.APP.originalSrc = data.image;
      showOriginal(data.image, data.width, data.height, data.is_gray);

      // If a feature is selected and live preview is on, re-apply
      if (window.APP.selectedFeature && document.getElementById('live-toggle').checked) {
        applyFeature();
      } else {
        window.APP.resultSrc = null;
        document.getElementById('body-result').innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">🔬</div>
            <p>Apply a feature to see results</p>
          </div>`;
        document.getElementById('btn-commit').disabled = true;
        document.getElementById('btn-download').disabled = true;
      }

      showToast(data.is_gray ? 'Switched to Grayscale' : 'Switched to Color', 'success');
    } catch (e) {
      showToast(e.message, 'error');
    }
  });
}

/** Display the original image in the Original window. */
function showOriginal(src, w, h, isGray) {
  const body = document.getElementById('body-original');
  body.innerHTML = `<img src="${src}" alt="Original image" id="img-original">`;

  const badge = document.getElementById('badge-original');
  badge.textContent = `${w}×${h} • ${isGray ? 'Gray' : 'RGB'}`;
  badge.className = `window-badge ${isGray ? 'gray' : 'rgb'}`;
}

/* ──────── Apply feature ──────── */
async function applyFeature() {
  const { mainImageId, selectedFeature, secondImageId, features } = window.APP;
  if (!mainImageId || !selectedFeature) return;

  const feat = features[selectedFeature];
  const params = getParamValues();

  // Show loading
  document.getElementById('loading-result').classList.add('visible');

  const payload = {
    image_id: mainImageId,
    feature: selectedFeature,
    params,
  };

  // Include second image for hybrid features
  if (feat.second_image && secondImageId) {
    payload.second_image_id = secondImageId;
  }

  try {
    const resp = await fetch('/api/apply', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await resp.json();

    if (resp.status === 501) {
      showToast('⚠ Feature not implemented yet', 'warning');
      return;
    }
    if (!resp.ok) throw new Error(data.error || 'Apply failed');

    window.APP.resultSrc = data.result;

    // Store analysis data for chart re-renders
    window.APP.lastAnalysis = {
      original: data.analysis_original,
      result: data.analysis_result,
    };

    // Update result view
    showResult(data.result);

    // Update analysis charts
    updateAnalysis(data.analysis_original, data.analysis_result, data.spectrum);

    // Enable commit/download
    document.getElementById('btn-commit').disabled = false;
    document.getElementById('btn-download').disabled = false;

  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    document.getElementById('loading-result').classList.remove('visible');
  }
}

/** Display result in the Result window (before/after or plain). */
function showResult(resultSrc) {
  const body = document.getElementById('body-result');

  if (window.APP.viewMode === 'ba' && window.APP.originalSrc) {
    // Before/After slider view
    body.innerHTML = `
      <div class="ba-container" id="ba-container">
        <img src="${window.APP.originalSrc}" class="ba-original" alt="Original">
        <img src="${resultSrc}" class="ba-result" alt="Result">
        <div class="ba-slider-line" id="ba-line">
          <div class="ba-slider-handle">⟷</div>
        </div>
      </div>`;
    initBASlider();
  } else {
    body.innerHTML = `<img src="${resultSrc}" alt="Result">`;
  }
}

/* ──────── Before/After slider ──────── */
function initBASlider() {
  const container = document.getElementById('ba-container');
  if (!container) return;

  let dragging = false;

  function updatePosition(clientX) {
    const rect = container.getBoundingClientRect();
    let pct = ((clientX - rect.left) / rect.width) * 100;
    pct = Math.max(0, Math.min(100, pct));
    container.style.setProperty('--ba-clip', (100 - pct) + '%');
    container.style.setProperty('--ba-left', pct + '%');
  }

  // Set initial position to 50%
  container.style.setProperty('--ba-clip', '50%');
  container.style.setProperty('--ba-left', '50%');

  const line = document.getElementById('ba-line');
  line.addEventListener('mousedown', e => { dragging = true; e.preventDefault(); });
  container.addEventListener('mousedown', e => { dragging = true; updatePosition(e.clientX); });
  window.addEventListener('mousemove', e => { if (dragging) updatePosition(e.clientX); });
  window.addEventListener('mouseup', () => { dragging = false; });

  // Touch support
  line.addEventListener('touchstart', e => { dragging = true; e.preventDefault(); });
  container.addEventListener('touchstart', e => { dragging = true; updatePosition(e.touches[0].clientX); });
  window.addEventListener('touchmove', e => { if (dragging) updatePosition(e.touches[0].clientX); });
  window.addEventListener('touchend', () => { dragging = false; });
}

/* ──────── View mode toggle ──────── */
function initViewToggle() {
  const btnBA = document.getElementById('btn-ba-toggle');
  const btnPlain = document.getElementById('btn-plain-toggle');

  btnBA.addEventListener('click', () => {
    window.APP.viewMode = 'ba';
    btnBA.classList.add('active');
    btnPlain.classList.remove('active');
    if (window.APP.resultSrc) showResult(window.APP.resultSrc);
  });

  btnPlain.addEventListener('click', () => {
    window.APP.viewMode = 'plain';
    btnPlain.classList.add('active');
    btnBA.classList.remove('active');
    if (window.APP.resultSrc) showResult(window.APP.resultSrc);
  });
}

/* ──────── Edge direction grid ──────── */
function initEdgeGrid() {
  const btn = document.getElementById('btn-edge-grid');
  btn.addEventListener('click', async () => {
    const { mainImageId, selectedFeature } = window.APP;
    if (!mainImageId || !selectedFeature) return;

    document.getElementById('loading-result').classList.add('visible');

    const directions = ['x', 'y', 'both'];
    const results = {};

    try {
      for (const dir of directions) {
        const params = getParamValues();
        params.direction = dir;
        const resp = await fetch('/api/apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_id: mainImageId, feature: selectedFeature, params }),
        });
        const data = await resp.json();
        if (resp.status === 501) {
          showToast('Feature not implemented yet', 'warning');
          return;
        }
        if (!resp.ok) throw new Error(data.error);
        results[dir] = data.result;
      }

      // Show 3-grid
      const body = document.getElementById('body-result');
      body.innerHTML = `
        <div class="edge-grid">
          <div class="edge-cell"><img src="${results.x}" alt="X direction"><div class="edge-label">X</div></div>
          <div class="edge-cell"><img src="${results.y}" alt="Y direction"><div class="edge-label">Y</div></div>
          <div class="edge-cell"><img src="${results.both}" alt="Combined"><div class="edge-label">Combined</div></div>
        </div>`;
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      document.getElementById('loading-result').classList.remove('visible');
    }
  });
}

/* ──────── Commit / Reset ──────── */
function initCommitReset() {
  document.getElementById('btn-commit').addEventListener('click', async () => {
    if (!window.APP.mainImageId) return;

    try {
      const resp = await fetch('/api/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_id: window.APP.mainImageId }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error);

      // Update original to the committed result
      window.APP.originalSrc = data.image;
      showOriginal(data.image, data.width, data.height, data.is_gray);

      // Add to history
      const feat = window.APP.features[window.APP.selectedFeature];
      window.APP.history.push(feat ? feat.label : 'Step');
      updateHistory();

      // Clear result
      window.APP.resultSrc = null;
      document.getElementById('body-result').innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🔬</div>
          <p>Apply a feature to see results</p>
        </div>`;
      document.getElementById('btn-commit').disabled = true;
      document.getElementById('btn-download').disabled = true;

      showToast('Result committed as new input', 'success');
    } catch (e) {
      showToast(e.message, 'error');
    }
  });

  document.getElementById('btn-reset').addEventListener('click', async () => {
    if (!window.APP.mainImageId) return;

    try {
      const resp = await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_id: window.APP.mainImageId }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error);

      window.APP.originalSrc = data.image;
      window.APP.resultSrc = null;
      window.APP.history = ['Original'];
      showOriginal(data.image, data.width, data.height, data.is_gray);

      const grayToggle = document.getElementById('gray-toggle');
      if (grayToggle) {
        grayToggle.checked = data.is_gray;
        grayToggle.disabled = !data.can_toggle_gray;
      }

      document.getElementById('body-result').innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🔬</div>
          <p>Apply a feature to see results</p>
        </div>`;
      document.getElementById('btn-commit').disabled = true;
      document.getElementById('btn-download').disabled = true;
      updateHistory();

      showToast('Reset to original image', 'success');
    } catch (e) {
      showToast(e.message, 'error');
    }
  });
}

/* ──────── Download ──────── */
function initDownload() {
  document.getElementById('btn-download').addEventListener('click', () => {
    if (!window.APP.resultSrc) return;
    const a = document.createElement('a');
    a.href = window.APP.resultSrc;
    a.download = 'result.png';
    a.click();
  });
}

/* ──────── History bar ──────── */
function updateHistory() {
  const bar = document.getElementById('history-bar');
  bar.innerHTML = window.APP.history
    .map(s => `<span>${s}</span>`)
    .join('<span class="history-sep">›</span>');
}

/* ──────── Apply button ──────── */
function initApplyButton() {
  document.getElementById('btn-apply').addEventListener('click', () => applyFeature());
}

/* ──────── Init on page load ──────── */
document.addEventListener('DOMContentLoaded', () => {
  loadFeatures();
  initUpload();
  initGrayToggle();
  initViewToggle();
  initEdgeGrid();
  initCommitReset();
  initDownload();
  initApplyButton();
  initAnalysisTabs();
});

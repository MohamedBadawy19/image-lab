/**
 * controls.js - Builds the sidebar accordion + parameter controls from /api/features.
 * Dynamically creates group headers, feature buttons, and parameter sliders/selects.
 * No feature names are hardcoded - everything comes from the backend registry.
 */

/** Fetch feature definitions from the backend and build the sidebar UI. */
async function loadFeatures() {
  try {
    const resp = await fetch('/api/features');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const features = await resp.json();
    window.APP.features = features;
    buildAccordion(features);
  } catch (e) {
    showToast('Failed to load features: ' + e.message, 'error');
  }
}

/** Group features by their 'group' field and create collapsible accordion sections. */
function buildAccordion(features) {
  const container = document.getElementById('feature-groups');
  container.innerHTML = '';

  // Group features by group name, preserving insertion order
  const groups = {};
  for (const [key, feat] of Object.entries(features)) {
    const g = feat.group || 'Other';
    if (!groups[g]) groups[g] = [];
    groups[g].push({ key, ...feat });
  }

  // Build each group
  for (const [groupName, items] of Object.entries(groups)) {
    // Group header (click to toggle)
    const header = document.createElement('div');
    header.className = 'group-header';
    header.innerHTML = `<span>${groupName}</span><span class="chevron">▶</span>`;
    header.addEventListener('click', () => {
      header.classList.toggle('open');
      itemsDiv.classList.toggle('open');
    });

    // Feature buttons inside the group
    const itemsDiv = document.createElement('div');
    itemsDiv.className = 'group-items';

    for (const feat of items) {
      const btn = document.createElement('button');
      btn.className = 'feature-btn';
      btn.textContent = feat.label;
      btn.dataset.feature = feat.key;
      btn.addEventListener('click', () => selectFeature(feat.key));
      itemsDiv.appendChild(btn);
    }

    container.appendChild(header);
    container.appendChild(itemsDiv);
  }
}

/** Handle feature selection: highlight button, show params, toggle second upload. */
function selectFeature(key) {
  const feat = window.APP.features[key];
  if (!feat) return;

  window.APP.selectedFeature = key;

  // Highlight selected button
  document.querySelectorAll('.feature-btn').forEach(b => b.classList.remove('active'));
  const btn = document.querySelector(`.feature-btn[data-feature="${key}"]`);
  if (btn) btn.classList.add('active');

  // Show/hide second upload for hybrid features
  const secondUpload = document.getElementById('second-upload');
  if (feat.second_image) {
    secondUpload.classList.add('visible');
  } else {
    secondUpload.classList.remove('visible');
  }

  // Show/hide edge grid button for directional edge features
  const edgeGridBtn = document.getElementById('btn-edge-grid');
  const hasDirection = feat.params && feat.params.some(p => p.name === 'direction');
  edgeGridBtn.style.display = hasDirection ? '' : 'none';

  // Build parameter controls
  buildParams(feat.params || []);

  // Enable apply button if image is loaded
  document.getElementById('btn-apply').disabled = !window.APP.mainImageId;
}

/** Build parameter controls (sliders / segmented selects) for the selected feature. */
function buildParams(params) {
  const section = document.getElementById('params-section');
  const container = document.getElementById('params-container');
  container.innerHTML = '';

  if (!params.length) {
    section.classList.remove('visible');
    return;
  }

  section.classList.add('visible');

  for (const p of params) {
    const row = document.createElement('div');
    row.className = 'param-row';

    if (p.type === 'select') {
      // Segmented button group
      row.innerHTML = `
        <div class="param-label"><span class="name">${p.name}</span></div>
        <div class="segmented" data-param="${p.name}"></div>
      `;
      const seg = row.querySelector('.segmented');
      for (const opt of p.options) {
        const btn = document.createElement('button');
        btn.textContent = opt;
        btn.dataset.value = opt;
        if (opt === p.default) btn.classList.add('active');
        btn.addEventListener('click', () => {
          seg.querySelectorAll('button').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          onParamChange();
        });
        seg.appendChild(btn);
      }
    } else {
      // Range slider + number input
      const step = p.step || 1;
      row.innerHTML = `
        <div class="param-label">
          <span class="name">${p.name}</span>
          <span class="value" id="val-${p.name}">${p.default}</span>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <input type="range" id="range-${p.name}" data-param="${p.name}"
            min="${p.min}" max="${p.max}" step="${step}" value="${p.default}">
          <input type="number" class="param-number" id="num-${p.name}" data-param="${p.name}"
            min="${p.min}" max="${p.max}" step="${step}" value="${p.default}">
        </div>
      `;
    }

    container.appendChild(row);
  }

  // Wire up slider <-> number sync and live preview
  container.querySelectorAll('input[type="range"]').forEach(slider => {
    const name = slider.dataset.param;
    const numInput = container.querySelector(`#num-${name}`);
    const valLabel = container.querySelector(`#val-${name}`);

    slider.addEventListener('input', () => {
      numInput.value = slider.value;
      if (valLabel) valLabel.textContent = slider.value;
      onParamChange();
    });

    numInput.addEventListener('input', () => {
      slider.value = numInput.value;
      if (valLabel) valLabel.textContent = numInput.value;
      onParamChange();
    });
  });
}

/** Collect current parameter values from the UI controls. */
function getParamValues() {
  const params = {};
  // Sliders/numbers
  document.querySelectorAll('#params-container input[type="range"]').forEach(el => {
    params[el.dataset.param] = el.value;
  });
  // Segmented selects
  document.querySelectorAll('#params-container .segmented').forEach(seg => {
    const active = seg.querySelector('button.active');
    if (active) params[seg.dataset.param] = active.dataset.value;
  });
  return params;
}

/** Called when any param changes. Triggers live preview if enabled. */
function onParamChange() {
  if (document.getElementById('live-toggle').checked && window.APP.mainImageId && window.APP.selectedFeature) {
    debouncedApply();
  }
}

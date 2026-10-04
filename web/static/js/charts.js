/**
 * charts.js - Histogram, CDF charts (Chart.js) and FFT spectrum image.
 * Data always comes from the backend; never computed in JS.
 */

let histChart = null;   // Chart.js instance for histogram
let cdfChart = null;    // Chart.js instance for CDF

/** Color map for channels */
const CHANNEL_COLORS = {
  r:    { line: 'rgba(255, 99, 99, 0.9)',  fill: 'rgba(255, 99, 99, 0.15)' },
  g:    { line: 'rgba(99, 255, 132, 0.9)', fill: 'rgba(99, 255, 132, 0.15)' },
  b:    { line: 'rgba(99, 149, 255, 0.9)', fill: 'rgba(99, 149, 255, 0.15)' },
  gray: { line: 'rgba(200, 200, 200, 0.9)', fill: 'rgba(200, 200, 200, 0.15)' },
};

/** Shared Chart.js options for dark theme */
const CHART_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 300 },
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      position: 'top',
      labels: { color: '#9aa0b0', font: { size: 11, family: 'Inter' }, boxWidth: 12, padding: 8 },
    },
    tooltip: {
      backgroundColor: '#1a1d27',
      titleColor: '#e8eaed',
      bodyColor: '#9aa0b0',
      borderColor: '#2d3244',
      borderWidth: 1,
    },
  },
  scales: {
    x: {
      ticks: { color: '#5c6378', font: { size: 10 }, maxTicksLimit: 16 },
      grid: { color: 'rgba(45,50,68,0.4)' },
    },
    y: {
      ticks: { color: '#5c6378', font: { size: 10 }, maxTicksLimit: 8 },
      grid: { color: 'rgba(45,50,68,0.4)' },
    },
  },
};

/** Generate x-axis labels [0..255] */
const LABELS_256 = Array.from({ length: 256 }, (_, i) => i);

/**
 * Build datasets for a chart from analysis data.
 * @param {object} analysis - e.g. { channels: { r: { hist, cdf }, ... } }
 * @param {string} field - 'hist' or 'cdf'
 * @param {string} suffix - label suffix like ' (Original)' or ' (Result)'
 * @param {boolean} dashed - use dashed lines for overlay
 */
function makeDatasets(analysis, field, suffix = '', dashed = false) {
  if (!analysis || !analysis.channels) return [];
  const datasets = [];
  for (const [ch, data] of Object.entries(analysis.channels)) {
    const colors = CHANNEL_COLORS[ch] || CHANNEL_COLORS.gray;
    datasets.push({
      label: ch.toUpperCase() + suffix,
      data: data[field],
      borderColor: colors.line,
      backgroundColor: colors.fill,
      fill: !dashed,
      borderWidth: dashed ? 1.5 : 2,
      borderDash: dashed ? [4, 3] : [],
      pointRadius: 0,
      tension: 0.1,
    });
  }
  return datasets;
}

/** Update the histogram chart with original and/or result analysis data. */
function updateHistogram(analysisOriginal, analysisResult) {
  const ctx = document.getElementById('chart-histogram');
  const overlay = document.getElementById('hist-overlay').checked;

  let datasets = [];

  if (analysisResult) {
    datasets.push(...makeDatasets(analysisResult, 'hist', overlay ? ' (Result)' : ''));
  }
  if (overlay && analysisOriginal) {
    datasets.push(...makeDatasets(analysisOriginal, 'hist', ' (Original)', true));
  }

  if (histChart) histChart.destroy();
  histChart = new Chart(ctx, {
    type: 'line',
    data: { labels: LABELS_256, datasets },
    options: { ...CHART_OPTIONS },
  });
}

/** Update the CDF chart with original and/or result analysis data. */
function updateCDF(analysisOriginal, analysisResult) {
  const ctx = document.getElementById('chart-cdf');
  const overlay = document.getElementById('cdf-overlay').checked;

  let datasets = [];

  if (analysisResult) {
    datasets.push(...makeDatasets(analysisResult, 'cdf', overlay ? ' (Result)' : ''));
  }
  if (overlay && analysisOriginal) {
    datasets.push(...makeDatasets(analysisOriginal, 'cdf', ' (Original)', true));
  }

  if (cdfChart) cdfChart.destroy();
  cdfChart = new Chart(ctx, {
    type: 'line',
    data: { labels: LABELS_256, datasets },
    options: { ...CHART_OPTIONS },
  });
}

/** Show the FFT spectrum image in the spectrum tab. */
function updateSpectrum(spectrumB64) {
  const img = document.getElementById('spectrum-img');
  const empty = document.getElementById('spectrum-empty');

  if (spectrumB64) {
    img.src = spectrumB64;
    img.style.display = 'block';
    empty.style.display = 'none';
  } else {
    img.style.display = 'none';
    empty.style.display = '';
  }
}

/** Update all analysis displays at once. Called after /api/apply returns. */
function updateAnalysis(analysisOriginal, analysisResult, spectrum) {
  updateHistogram(analysisOriginal, analysisResult);
  updateCDF(analysisOriginal, analysisResult);
  updateSpectrum(spectrum);
}

/** Initialize tab switching. */
function initAnalysisTabs() {
  const tabs = document.querySelectorAll('.analysis-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
  });

  // Re-render charts when overlay toggles change
  document.getElementById('hist-overlay').addEventListener('change', () => {
    if (window.APP.lastAnalysis) {
      updateHistogram(window.APP.lastAnalysis.original, window.APP.lastAnalysis.result);
    }
  });
  document.getElementById('cdf-overlay').addEventListener('change', () => {
    if (window.APP.lastAnalysis) {
      updateCDF(window.APP.lastAnalysis.original, window.APP.lastAnalysis.result);
    }
  });
}

/* ═══════════════════════════════════════════════════════════════
   PIXELVAULT — Dashboard Logic
   ═══════════════════════════════════════════════════════════════ */

const API = '/api/v1';
const INDUSTRIES = {
  healthcare:    { icon: '🏥', label: 'Healthcare' },
  real_estate:   { icon: '🏠', label: 'Real Estate' },
  food:          { icon: '🍽️', label: 'Food' },
  legal_finance: { icon: '⚖️', label: 'Legal & Finance' },
  fitness:       { icon: '💪', label: 'Fitness' },
  ecommerce:     { icon: '🛒', label: 'E-commerce' },
};

let allPrompts = [];
let currentPromptId = null;
let genCount = 3;
let currentReviewFilter = null;
let currentReviewPage = 1;
let reviewPerPage = 50;
let pollTimers = {};

// ─── Init ───
document.addEventListener('DOMContentLoaded', async () => {
  await checkHealth();
  await loadDashboard();
  await loadPrompts();
  // Poll for active batches every 5 seconds
  setInterval(pollActiveBatches, 5000);
});

// ─── API Helpers ───
async function api(endpoint, options = {}) {
  const resp = await fetch(API + endpoint, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

async function checkHealth() {
  try {
    await fetch('/health');
    document.getElementById('apiStatus').className = 'status-dot online';
    document.getElementById('apiStatusText').textContent = 'API Online';
  } catch {
    document.getElementById('apiStatus').className = 'status-dot offline';
    document.getElementById('apiStatusText').textContent = 'Offline';
  }
}

// ─── Navigation ───
function switchView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`view-${name}`).classList.add('active');
  document.querySelector(`[data-view="${name}"]`).classList.add('active');

  if (name === 'dashboard') loadDashboard();
  if (name === 'review') loadReview();
  if (name === 'batches') loadBatches();
}

// ═══ DASHBOARD ═══
async function loadDashboard() {
  try {
    const stats = await api('/stats');

    document.getElementById('statTotal').textContent = stats.total;
    document.getElementById('statApproved').textContent = stats.approved;
    document.getElementById('statPending').textContent = stats.pending;
    document.getElementById('statRejected').textContent = stats.rejected;

    const max = Math.max(stats.total, 1);
    setTimeout(() => {
      document.getElementById('barTotal').style.width = '100%';
      document.getElementById('barApproved').style.width = (stats.approved / max * 100) + '%';
      document.getElementById('barPending').style.width = (stats.pending / max * 100) + '%';
      document.getElementById('barRejected').style.width = (stats.rejected / max * 100) + '%';
    }, 100);

    // Industry grid
    const grid = document.getElementById('industryGrid');
    grid.innerHTML = Object.entries(INDUSTRIES).map(([key, { icon, label }]) => `
      <div class="industry-card" onclick="switchView('prompts'); filterIndustry('${key}', null)">
        <div class="industry-card__icon">${icon}</div>
        <div class="industry-card__name">${label}</div>
        <div class="industry-card__count">${stats.by_industry[key] || 0}</div>
      </div>
    `).join('');

    // Recent batches
    const batches = await api('/batches');
    const container = document.getElementById('recentBatches');
    if (batches.length === 0) {
      container.innerHTML = '<div class="batch-table__empty">No batches yet — go to Prompts to generate your first batch.</div>';
    } else {
      container.innerHTML = batches.slice(0, 8).map(b => batchRowHTML(b)).join('');
    }
  } catch (e) {
    console.error('Dashboard load failed:', e);
  }
}

function batchRowHTML(b) {
  const prompt = allPrompts.find(p => p.id === b.prompt_id);
  const name = prompt ? prompt.name : `Prompt #${b.prompt_id}`;
  const industry = prompt ? INDUSTRIES[prompt.industry]?.label || prompt.industry : '—';
  const time = b.created_at ? timeAgo(b.created_at) : '—';
  return `
    <div class="batch-row">
      <div class="batch-row__id">#${b.id}</div>
      <div class="batch-row__prompt">${name}</div>
      <div class="batch-row__industry">${industry}</div>
      <div class="batch-row__count">${b.image_count} imgs</div>
      <div><span class="status-pill status-pill--${b.status}">${b.status}</span></div>
      <div class="batch-row__time">${time}</div>
    </div>
  `;
}

// ═══ PROMPTS ═══
async function loadPrompts() {
  try {
    allPrompts = await api('/prompts');
    renderPrompts(allPrompts);
  } catch (e) {
    console.error('Failed to load prompts:', e);
  }
}

function renderPrompts(prompts) {
  const grid = document.getElementById('promptsGrid');
  grid.innerHTML = prompts.map(p => {
    const ind = INDUSTRIES[p.industry] || { icon: '📁', label: p.industry };
    const ratios = p.ratios.split(',').map(r => r.trim());
    return `
      <div class="prompt-card">
        <div class="prompt-card__header">
          <div class="prompt-card__name">${p.name}</div>
          <span class="prompt-card__industry">${ind.icon} ${ind.label}</span>
        </div>
        <div class="prompt-card__text">${p.prompt_text}</div>
        <div class="prompt-card__meta">
          <div class="prompt-card__tags">
            ${ratios.map(r => `<span class="prompt-card__tag">${r}</span>`).join('')}
            <span class="prompt-card__tag">${p.use_case.split(',')[0].trim()}</span>
          </div>
          <button class="btn btn--generate btn--sm" onclick="openGenerateModal(${p.id})">Generate</button>
        </div>
      </div>
    `;
  }).join('');
}

function filterIndustry(industry, btnEl) {
  if (btnEl) {
    document.querySelectorAll('.industry-filter .filter-btn').forEach(b => b.classList.remove('active'));
    btnEl.classList.add('active');
  }
  if (!industry) {
    renderPrompts(allPrompts);
  } else {
    renderPrompts(allPrompts.filter(p => p.industry === industry));
  }
}

// ═══ GENERATE MODAL ═══
function openGenerateModal(promptId) {
  const prompt = allPrompts.find(p => p.id === promptId);
  if (!prompt) return;

  currentPromptId = promptId;
  genCount = 3;

  document.getElementById('modalPromptName').textContent = prompt.name;
  document.getElementById('modalPromptText').textContent = prompt.prompt_text;
  document.getElementById('genCount').textContent = genCount;
  updateCost();

  // Populate ratio select
  const select = document.getElementById('genRatio');
  const ratios = prompt.ratios.split(',').map(r => r.trim());
  select.innerHTML = ratios.map(r => `<option value="${r}">${r}</option>`).join('');

  document.getElementById('generateModal').classList.add('open');
}

function closeModal(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('generateModal').classList.remove('open');
}

function adjustCount(delta) {
  genCount = Math.max(1, Math.min(8, genCount + delta));
  document.getElementById('genCount').textContent = genCount;
  updateCost();
}

function updateCost() {
  const cost = (genCount * 0.04).toFixed(2);
  document.getElementById('genCost').textContent = `$${cost}`;
}

async function submitGenerate() {
  const btn = document.getElementById('btnGenerate');
  const btnText = btn.querySelector('.btn__text');
  const btnLoader = btn.querySelector('.btn__loader');

  btn.disabled = true;
  btnText.textContent = 'Generating...';
  btnLoader.style.display = 'inline-block';

  try {
    const ratio = document.getElementById('genRatio').value;
    const result = await api('/generate', {
      method: 'POST',
      body: JSON.stringify({ prompt_id: currentPromptId, count: genCount, ratio }),
    });

    toast(`Batch #${result.batch_id} started — ${result.message}`, 'success');
    closeModal();
    pollActiveBatches();
  } catch (e) {
    toast(`Generation failed: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Generate Batch';
    btnLoader.style.display = 'none';
  }
}

// ═══ REVIEW ═══
async function loadReview() {
  try {
    const params = new URLSearchParams({ page: currentReviewPage, per_page: reviewPerPage });
    if (currentReviewFilter) params.set('status', currentReviewFilter);
    const images = await api(`/images?${params}`);
    const grid = document.getElementById('reviewGrid');

    // Update pagination controls
    const stats = await api('/stats');
    const filteredTotal = currentReviewFilter ? stats[currentReviewFilter] : stats.total;
    const totalPages = Math.max(1, Math.ceil(filteredTotal / reviewPerPage));

    let paginationEl = document.getElementById('reviewPagination');
    if (!paginationEl) {
      paginationEl = document.createElement('div');
      paginationEl.id = 'reviewPagination';
      paginationEl.className = 'review-pagination';
      grid.parentNode.insertBefore(paginationEl, grid.nextSibling);
    }
    paginationEl.innerHTML = `
      <button class="btn btn--ghost btn--sm" onclick="changeReviewPage(-1)" ${currentReviewPage <= 1 ? 'disabled' : ''}>Prev</button>
      <span class="review-pagination__info">Page ${currentReviewPage} of ${totalPages} (${filteredTotal} images)</span>
      <button class="btn btn--ghost btn--sm" onclick="changeReviewPage(1)" ${currentReviewPage >= totalPages ? 'disabled' : ''}>Next</button>
    `;

    if (images.length === 0) {
      grid.innerHTML = '<div class="batch-table__empty">No images found.</div>';
      return;
    }

    grid.innerHTML = images.map(img => {
      const sizeMB = img.file_size ? (img.file_size / 1048576).toFixed(1) : '—';
      const model = img.model_used || '—';
      return `
        <div class="review-card" id="review-card-${img.id}">
          <div class="review-card__img-wrap" onclick="openLightbox('${img.id}')">
            <img class="review-card__img" src="/api/v1/images/${img.id}/file" alt="${img.filename}" loading="lazy">
            <span class="review-card__status-badge review-card__status-badge--${img.status}">${img.status}</span>
          </div>
          <div class="review-card__info">
            <div class="review-card__filename">${img.filename}</div>
            <div class="review-card__dims">${img.width || '—'}x${img.height || '—'} · ${sizeMB} MB · ${img.ratio} · ${model}</div>
            <div class="review-card__actions">
              ${img.status !== 'approved' ? `<button class="btn btn--approve btn--sm" onclick="reviewImage('${img.id}', 'approved')">Approve</button>` : ''}
              ${img.status !== 'rejected' ? `<button class="btn btn--reject btn--sm" onclick="reviewImage('${img.id}', 'rejected')">Reject</button>` : ''}
              ${img.status !== 'pending' ? `<button class="btn btn--ghost btn--sm" onclick="reviewImage('${img.id}', 'pending')">Reset</button>` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    console.error('Review load failed:', e);
  }
}

function changeReviewPage(delta) {
  currentReviewPage = Math.max(1, currentReviewPage + delta);
  loadReview();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function filterReviewStatus(status, btnEl) {
  currentReviewFilter = status;
  currentReviewPage = 1;
  if (btnEl) {
    document.querySelectorAll('.review-filters .filter-btn').forEach(b => b.classList.remove('active'));
    btnEl.classList.add('active');
  }
  loadReview();
}

async function reviewImage(imageId, status) {
  try {
    await api(`/images/${imageId}/review`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
    toast(`Image ${status}`, status === 'approved' ? 'success' : status === 'rejected' ? 'error' : 'info');
    loadReview();
    loadDashboard();
  } catch (e) {
    toast(`Review failed: ${e.message}`, 'error');
  }
}

// ═══ LIGHTBOX ═══
function openLightbox(imageId) {
  const img = document.getElementById('lightboxImg');
  img.src = `/api/v1/images/${imageId}/file`;

  api(`/images/${imageId}`).then(data => {
    const sizeMB = data.file_size ? (data.file_size / 1048576).toFixed(1) : '—';
    document.getElementById('lightboxMeta').innerHTML = `
      ${data.filename} · ${data.width}×${data.height} · ${sizeMB} MB · ${data.industry} / ${data.style}
    `;
    document.getElementById('lightboxActions').innerHTML = `
      <button class="btn btn--approve btn--sm" onclick="reviewImage('${data.id}', 'approved'); closeLightbox();">Approve</button>
      <button class="btn btn--reject btn--sm" onclick="reviewImage('${data.id}', 'rejected'); closeLightbox();">Reject</button>
    `;
  });

  document.getElementById('lightbox').classList.add('open');
}

function closeLightbox(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('lightbox').classList.remove('open');
  document.getElementById('lightboxImg').src = '';
}

// ═══ BATCHES ═══
async function loadBatches() {
  try {
    const batches = await api('/batches');
    const container = document.getElementById('batchList');

    if (batches.length === 0) {
      container.innerHTML = '<div class="batch-table__empty">No batches yet.</div>';
      return;
    }

    container.innerHTML = batches.map(b => batchRowHTML(b)).join('');
  } catch (e) {
    console.error('Batch load failed:', e);
  }
}

// ─── Polling for active batches ───
async function pollActiveBatches() {
  try {
    const batches = await api('/batches');
    const active = batches.filter(b => b.status === 'pending' || b.status === 'generating');

    if (active.length === 0) return;

    // Refresh current view
    const activeView = document.querySelector('.view.active');
    if (activeView.id === 'view-dashboard') loadDashboard();
    if (activeView.id === 'view-batches') loadBatches();
    if (activeView.id === 'view-review') loadReview();
  } catch { /* ignore */ }
}

// ─── Toast ───
function toast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ─── Time Ago ───
function timeAgo(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = (now - date) / 1000;
  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ─── Keyboard shortcuts ───
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeModal();
    closeLightbox();
  }
});

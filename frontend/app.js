/**
 * app.js – StadiumOps Copilot frontend logic.
 * Handles chat interactions, language selection, volunteer context,
 * escalation display, and the escalate-to-human flow.
 */
const API = '';

// ── DOM Elements ────────────────────────────────────────────────────────────
const appContainer    = document.getElementById('appContainer');
const chatMessages    = document.getElementById('chatMessages');
const welcomeScreen   = document.getElementById('welcomeScreen');
const suggestionsArea = document.getElementById('suggestions');
const questionInput   = document.getElementById('questionInput');
const sendBtn         = document.getElementById('sendBtn');
const escalateBtn     = document.getElementById('escalateBtn');
const languageSelect  = document.getElementById('languageSelect');
const contextBtn      = document.getElementById('contextBtn');
const contextLabel    = document.getElementById('contextLabel');
const contextModal    = document.getElementById('contextModal');
const zoneInput       = document.getElementById('zoneInput');
const roleInput       = document.getElementById('roleInput');
const modalSaveBtn    = document.getElementById('modalSaveBtn');
const modalCancelBtn  = document.getElementById('modalCancelBtn');
const toastContainer  = document.getElementById('toastContainer');

// ── State ───────────────────────────────────────────────────────────────────
let isGenerating = false;
let volunteerContext = { zone: 'Not specified', role: 'General Volunteer' };

const SUGGESTIONS = [
  '🚑 A fan collapsed near the concession stand',
  '👧 A parent is looking for their lost child',
  '🔒 I found a suspicious unattended bag',
  '♿ A guest needs wheelchair assistance',
  '🌩️ What do I do if there\'s a lightning warning?',
  '📦 Someone lost their wallet near Section 204',
];

// ── Initialization ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  renderSuggestions();
  loadContext();
  languageSelect.addEventListener('change', handleLanguageChange);
});

// ── Language / RTL ──────────────────────────────────────────────────────────
function handleLanguageChange() {
  const lang = languageSelect.value;
  const html = document.documentElement;
  if (lang === 'ar') {
    html.setAttribute('dir', 'rtl');
    html.setAttribute('lang', 'ar');
  } else {
    html.setAttribute('dir', 'ltr');
    html.setAttribute('lang', lang);
  }
}

// ── Volunteer Context Modal ─────────────────────────────────────────────────
contextBtn.addEventListener('click', () => {
  zoneInput.value = volunteerContext.zone !== 'Not specified' ? volunteerContext.zone : '';
  roleInput.value = volunteerContext.role !== 'General Volunteer' ? volunteerContext.role : '';
  contextModal.style.display = 'flex';
  zoneInput.focus();
});

modalSaveBtn.addEventListener('click', saveContext);
modalCancelBtn.addEventListener('click', () => { contextModal.style.display = 'none'; });

// Close modal on Escape
contextModal.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') contextModal.style.display = 'none';
});
// Close modal on overlay click
contextModal.addEventListener('click', (e) => {
  if (e.target === contextModal) contextModal.style.display = 'none';
});

function saveContext() {
  volunteerContext.zone = zoneInput.value.trim() || 'Not specified';
  volunteerContext.role = roleInput.value.trim() || 'General Volunteer';

  localStorage.setItem('stadiumops_context', JSON.stringify(volunteerContext));

  const label = volunteerContext.zone !== 'Not specified'
    ? `${volunteerContext.zone}`
    : 'Set Zone & Role';
  contextLabel.textContent = label;
  contextBtn.classList.toggle('active', volunteerContext.zone !== 'Not specified');

  contextModal.style.display = 'none';
  showToast(`Context updated: ${volunteerContext.zone} / ${volunteerContext.role}`, 'success');
}

function loadContext() {
  try {
    const saved = localStorage.getItem('stadiumops_context');
    if (saved) {
      volunteerContext = JSON.parse(saved);
      if (volunteerContext.zone !== 'Not specified') {
        contextLabel.textContent = volunteerContext.zone;
        contextBtn.classList.add('active');
      }
    }
  } catch (e) { /* ignore */ }
}

// ── Toast Notifications ─────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const icons = { error: '⚠️', success: '✅', info: 'ℹ️', warning: '⚡', escalation: '🚨' };
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.setAttribute('role', 'alert');
  t.innerHTML = `<span>${icons[type] || 'ℹ️'}</span> ${esc(msg)}`;
  toastContainer.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transition = 'opacity 0.3s';
    setTimeout(() => t.remove(), 300);
  }, 4000);
}

// ── Escalate to Human ───────────────────────────────────────────────────────
escalateBtn.addEventListener('click', () => {
  showToast(
    'Escalation request sent to Section Supervisor. They will contact you via radio shortly.',
    'escalation'
  );
});

// ── Suggestions ─────────────────────────────────────────────────────────────
function renderSuggestions() {
  suggestionsArea.innerHTML = SUGGESTIONS.map(s =>
    `<button class="suggestion-card" role="button" tabindex="0"
             aria-label="Ask: ${esc(s)}">${s}</button>`
  ).join('');

  suggestionsArea.querySelectorAll('.suggestion-card').forEach(card => {
    card.addEventListener('click', () => setQuery(card.textContent));
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setQuery(card.textContent); }
    });
  });
}

function setQuery(text) {
  questionInput.value = text;
  questionInput.focus();
  checkInput();
}

// ── Input Handling ──────────────────────────────────────────────────────────
function checkInput() {
  sendBtn.disabled = questionInput.value.trim().length === 0 || isGenerating;
  questionInput.style.height = 'auto';
  questionInput.style.height = Math.min(questionInput.scrollHeight, 200) + 'px';
}

questionInput.addEventListener('input', checkInput);
questionInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!sendBtn.disabled) submitQuery();
  }
});
sendBtn.addEventListener('click', submitQuery);

// ── Submit Query ────────────────────────────────────────────────────────────
async function submitQuery() {
  const text = questionInput.value.trim();
  if (!text || isGenerating) return;

  questionInput.value = '';
  checkInput();
  isGenerating = true;

  // Hide welcome screen
  welcomeScreen.style.display = 'none';

  // Append user message
  appendMessage('user', `<div style="white-space: pre-wrap;">${esc(text)}</div>`);

  // Append AI loading placeholder
  const aiBoxId = appendAIBox();
  scrollToBottom();

  try {
    const body = {
      question: text,
      language: languageSelect.value,
      volunteer_context: {
        zone: volunteerContext.zone,
        role: volunteerContext.role,
      },
    };

    const res = await fetch(`${API}/api/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const raw = await res.text();
    let data;
    try { data = JSON.parse(raw); } catch {
      throw new Error('Server returned an invalid response. It may still be starting up — please try again.');
    }

    if (!res.ok) throw new Error(data.detail || 'Failed to get response');

    updateAIBox(aiBoxId, data);

  } catch (e) {
    const errMsg = (e.message === 'Failed to fetch')
      ? '**Backend is starting up**\n\nPlease wait a moment and try again.'
      : `**Error**\n\n${e.message}`;
    updateAIBox(aiBoxId, { answer: errMsg, sources: [], escalation: null }, true);
  } finally {
    isGenerating = false;
    checkInput();
    scrollToBottom();
  }
}

// ── Message Rendering ───────────────────────────────────────────────────────
function appendMessage(role, htmlContent) {
  const wrap = document.createElement('div');
  wrap.className = `message-wrapper ${role}`;

  if (role === 'user') {
    wrap.innerHTML = `<div class="message-inner"><div class="message-content">${htmlContent}</div></div>`;
  }
  chatMessages.appendChild(wrap);
}

function appendAIBox() {
  const id = 'msg-' + Date.now();
  const wrap = document.createElement('div');
  wrap.className = 'message-wrapper ai';
  wrap.id = id;
  wrap.innerHTML = `
    <div class="message-inner">
      <div class="msg-avatar" aria-hidden="true">
        <svg viewBox="0 0 40 40" fill="none" width="22" height="22">
          <path d="M12 12l8 4-8 4V12z" fill="#fff" opacity="0.9"/>
          <circle cx="28" cy="16" r="4" fill="#fff" opacity="0.7"/>
          <path d="M10 28h20M10 24h14" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
      <div class="message-content" id="content-${id}" aria-label="Assistant response">
        <div class="typing-indicator" aria-label="Thinking...">
          <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
        </div>
      </div>
    </div>`;
  chatMessages.appendChild(wrap);
  return id;
}

function updateAIBox(id, data, isError = false) {
  const contentBox = document.getElementById(`content-${id}`);
  if (!contentBox) return;

  if (isError) {
    contentBox.innerHTML = marked.parse(data.answer || data);
    contentBox.style.color = 'var(--danger)';
    return;
  }

  // Render markdown answer
  let html = marked.parse(data.answer || '');

  // Escalation badge
  if (data.escalation && data.escalation.flag) {
    const isEscalate = data.escalation.flag === 'escalate';
    const badgeClass = isEscalate ? 'escalate' : 'self-resolve';
    const icon = isEscalate
      ? '<svg viewBox="0 0 24 24" fill="none"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke="currentColor" stroke-width="2"/></svg>'
      : '<svg viewBox="0 0 24 24" fill="none"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    const label = isEscalate ? '⚠ ESCALATE TO SUPERVISOR' : '✓ VOLUNTEER CAN SELF-RESOLVE';

    html += `<div class="escalation-badge ${badgeClass}" role="status" aria-label="${label}">${icon} ${label}</div>`;

    if (data.escalation.reasoning) {
      html += `<div class="escalation-reasoning">${esc(data.escalation.reasoning)}</div>`;
    }
  }

  // Source citations
  if (data.sources && data.sources.length) {
    html += '<div class="sources-list" aria-label="Source SOP documents">';
    data.sources.forEach((s, idx) => {
      const sevClass = s.severity || 'low';
      html += `
        <div class="source-tag" tabindex="0" aria-label="Source: ${esc(s.sop_title || s.filename)}">
          <span class="severity-dot ${sevClass}" aria-hidden="true"></span>
          <span>${esc(s.sop_title || s.filename)}</span>
          <div class="source-tooltip">
            <strong>Source ${idx + 1}: ${esc(s.sop_title || '')}</strong><br/>
            <em>${esc(s.filename)}</em> · Severity: ${esc(s.severity || 'N/A')}<br/><br/>
            "${esc(s.excerpt || '')}"
          </div>
        </div>`;
    });
    html += '</div>';
  }

  contentBox.innerHTML = html;
}

// ── Utilities ───────────────────────────────────────────────────────────────
function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

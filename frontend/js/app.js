/* ═══════════════════════════════════════════════════════
   GuidyTH  –  app.js
   API base: /api/v1  (proxied through Nginx on port 8000)
═══════════════════════════════════════════════════════ */

const API_BASE = '/api/v1';

/* ─── Profile options (keys must stay as-is — backend contract) ─── */
const PROFILE_OPTIONS = {
  favourite_province: ['Bangkok', 'Chiang Mai', 'Chumphon', 'Ratchaburi', 'Yala', 'Chonburi'],
  style:              ['Backpacker', 'Nature', 'Luxury', 'Adventure', 'Culture', 'Family', 'Romantic', 'Photography'],
  food:               ['Noodle soup', 'Seafood', 'Som Tum', 'Hainanese chicken rice', 'Pad Thai', 'Larb', 'Vegetarian', 'Street food', 'Northern Thai food', 'Northeastern Thai food'],
  transportation:     ['Train', 'Plane', 'Bus', 'Car', 'Motorcycle', 'Boat'],
};

/* ─── Profile section config ─── */
const PROFILE_SECTIONS = [
  { containerId: 'chipsProvince',  key: 'favourite_province', label: 'Favourite Provinces', icon: 'map-pin'     },
  { containerId: 'chipsStyle',     key: 'style',              label: 'Travel Style',         icon: 'backpack'    },
  { containerId: 'chipsFood',      key: 'food',               label: 'Favourite Food',       icon: 'utensils'    },
  { containerId: 'chipsTransport', key: 'transportation',     label: 'Getting Around',       icon: 'train-front' },
];

/* ─── State ─── */
const state = {
  userId:        getOrCreateUserId(),
  conversations: loadConversations(),   // { [id]: { id, title, createdAt } }
  activeId:      null,
  streaming:     false,
  userProfile:   loadUserProfile(),     // { favourite_province, style, food, transportation, ... }
};

/* ─── DOM refs ─── */
const $ = id => document.getElementById(id);
const dom = {
  sidebar:          $('sidebar'),
  sidebarToggle:    $('sidebarToggle'),
  sidebarBackdrop:  $('sidebarBackdrop'),
  newChatBtn:       $('newChatBtn'),
  convList:         $('conversationList'),
  chatMessages:     $('chatMessages'),
  welcomeScreen:    $('welcomeScreen'),
  chatTitleText:    $('chatTitleText'),
  deleteHistoryBtn: $('deleteHistoryBtn'),
  editProfileBtn:   $('editProfileBtn'),
  messageInput:     $('messageInput'),
  sendBtn:          $('sendBtn'),
  modalBackdrop:    $('modalBackdrop'),
  modalCancel:      $('modalCancel'),
  modalConfirm:     $('modalConfirm'),
  profileBackdrop:  $('profileBackdrop'),
  profileSaveBtn:   $('profileSaveBtn'),
  profileSkipBtn:   $('profileSkipBtn'),
};

/* ─── Lucide helper ─── */
function initIcons(scope) {
  if (typeof lucide === 'undefined') return;
  if (scope) {
    lucide.createIcons({ nodes: Array.from(scope.querySelectorAll('[data-lucide]')) });
  } else {
    lucide.createIcons();
  }
}

/* ══════════════════════════════════════════
   HELPERS
══════════════════════════════════════════ */
function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

function getOrCreateUserId() {
  let id = localStorage.getItem('guidyth_user_id');
  if (!id) {
    id = 'user_' + uuid();
    localStorage.setItem('guidyth_user_id', id);
  }
  return id;
}

function loadConversations() {
  try {
    return JSON.parse(localStorage.getItem('guidyth_conversations') || '{}');
  } catch { return {}; }
}

function saveConversations() {
  localStorage.setItem('guidyth_conversations', JSON.stringify(state.conversations));
}

function truncate(str, n = 40) {
  return str.length > n ? str.slice(0, n).trimEnd() + '…' : str;
}

function scrollToBottom() {
  dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

function showError(msg, duration = 4000) {
  const el = document.createElement('div');
  el.className = 'error-toast';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

function loadUserProfile() {
  try {
    return JSON.parse(localStorage.getItem('guidyth_user_profile') || 'null');
  } catch { return null; }
}

function saveUserProfile(profile) {
  localStorage.setItem('guidyth_user_profile', JSON.stringify(profile));
  state.userProfile = profile;
  updateProfileBtn();
}

function updateProfileBtn() {
  if (state.userProfile) {
    dom.editProfileBtn.classList.add('has-profile');
  } else {
    dom.editProfileBtn.classList.remove('has-profile');
  }
}

/* ══════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════ */
function closeSidebar() {
  dom.sidebar.classList.remove('mobile-open', 'tablet-open');
  dom.sidebarBackdrop.classList.remove('visible');
}

dom.sidebarToggle.addEventListener('click', () => {
  const w = window.innerWidth;
  if (w < 768) {
    // Mobile: overlay slide-in
    const isOpen = dom.sidebar.classList.toggle('mobile-open');
    dom.sidebarBackdrop.classList.toggle('visible', isOpen);
  } else if (w < 1024) {
    // Tablet: toggle tablet-open (sidebar starts collapsed)
    const isOpen = dom.sidebar.classList.toggle('tablet-open');
    dom.sidebarBackdrop.classList.toggle('visible', isOpen);
  } else {
    // Desktop: toggle collapsed width
    dom.sidebar.classList.toggle('collapsed');
  }
});

dom.sidebarBackdrop.addEventListener('click', closeSidebar);

/* ══════════════════════════════════════════
   SIDEBAR / CONVERSATIONS UI
══════════════════════════════════════════ */
function renderConversationList() {
  dom.convList.innerHTML = '';
  const sorted = Object.values(state.conversations)
    .sort((a, b) => b.createdAt - a.createdAt);

  if (sorted.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'font-size:12px;color:#8c8fa1;padding:10px 12px;font-weight:500;';
    empty.textContent = 'No conversations yet';
    dom.convList.appendChild(empty);
    return;
  }

  sorted.forEach(conv => {
    const item = document.createElement('div');
    item.className = 'conv-item' + (conv.id === state.activeId ? ' active' : '');
    item.dataset.id = conv.id;

    const title = document.createElement('span');
    title.className = 'conv-title';
    title.textContent = conv.title || 'New Chat';

    const delBtn = document.createElement('button');
    delBtn.className = 'conv-delete-btn';
    delBtn.title = 'Delete conversation';
    delBtn.innerHTML = '<i data-lucide="x"></i>';
    delBtn.addEventListener('click', e => {
      e.stopPropagation();
      openDeleteModal(conv.id);
    });

    item.appendChild(title);
    item.appendChild(delBtn);
    item.addEventListener('click', () => {
      loadConversation(conv.id);
      // Close sidebar on mobile/tablet after selecting
      if (window.innerWidth < 1024) closeSidebar();
    });
    dom.convList.appendChild(item);
  });

  initIcons(dom.convList);
}

function setActiveConversation(id) {
  state.activeId = id;
  renderConversationList();

  const conv = state.conversations[id];
  dom.chatTitleText.textContent = conv ? (conv.title || 'New Chat') : 'New Chat';
  dom.deleteHistoryBtn.style.display = id ? 'flex' : 'none';
}

/* ══════════════════════════════════════════
   MESSAGES UI
══════════════════════════════════════════ */
function hideWelcome() {
  if (dom.welcomeScreen) dom.welcomeScreen.style.display = 'none';
}

function showWelcome() {
  if (dom.welcomeScreen) dom.welcomeScreen.style.display = '';
}

function clearMessages() {
  dom.chatMessages.querySelectorAll('.message-row').forEach(el => el.remove());
}

function appendUserMessage(text) {
  hideWelcome();
  const row = document.createElement('div');
  row.className = 'message-row user';
  row.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
  dom.chatMessages.appendChild(row);
  scrollToBottom();
}

function appendAssistantMessage(text, streaming = false) {
  const row = document.createElement('div');
  row.className = 'message-row assistant';
  row.innerHTML = `
    <div class="message-bubble">
      <div class="assistant-avatar">
        <img src="assets/logo.svg" alt="Guidy" />
      </div>
      <div class="assistant-body">
        <div class="assistant-content ${streaming ? 'typing-cursor' : ''}">${
          text
            ? (typeof marked !== 'undefined' ? marked.parse(text) : escapeHtml(text))
            : '<div class="loading-dots"><span></span><span></span><span></span></div>'
        }</div>
        <div class="message-actions">
          <button class="like-btn" title="Like this response">
            <i data-lucide="thumbs-up"></i>
          </button>
        </div>
      </div>
    </div>`;
  dom.chatMessages.appendChild(row);
  scrollToBottom();

  const contentEl = row.querySelector('.assistant-content');
  const likeBtn   = row.querySelector('.like-btn');

  initIcons(row);

  // Restore liked state
  if (text && state.userProfile?.favourite) {
    const snippet = text.trim().slice(0, 300);
    if (state.userProfile.favourite.includes(snippet)) {
      likeBtn.classList.add('liked');
    }
  }

  likeBtn.addEventListener('click', () => toggleLike(likeBtn, contentEl.innerText || contentEl.textContent));
  return contentEl;
}

function toggleLike(btn, content) {
  const snippet = (content || '').trim().slice(0, 300);
  if (!snippet) return;

  const profile = state.userProfile || { favourite_province: [], style: [], food: [], transportation: [], favourite: [] };
  if (!profile.favourite) profile.favourite = [];

  const idx = profile.favourite.indexOf(snippet);
  if (idx === -1) {
    profile.favourite.push(snippet);
    btn.classList.add('liked');
  } else {
    profile.favourite.splice(idx, 1);
    btn.classList.remove('liked');
  }
  saveUserProfile(profile);
}

function renderMessages(messages) {
  clearMessages();
  if (!messages || messages.length === 0) { showWelcome(); return; }
  hideWelcome();
  messages.forEach(msg => {
    if (msg.role === 'user') {
      appendUserMessage(msg.content);
    } else {
      appendAssistantMessage(msg.content, false);
    }
  });
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/\n/g, '<br>');
}

/* ══════════════════════════════════════════
   API CALLS
══════════════════════════════════════════ */

/* Load history from server and render */
async function loadConversation(id) {
  setActiveConversation(id);
  clearMessages();
  showWelcome();

  try {
    const res = await fetch(`${API_BASE}/history/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderMessages(data.messages || []);
  } catch (err) {
    showError('Failed to load conversation history.');
    console.error(err);
  }
}

/* Start a new blank conversation */
function newChat() {
  const id = uuid();
  state.conversations[id] = {
    id,
    title:     'New Chat',
    createdAt: Date.now(),
  };
  saveConversations();
  setActiveConversation(id);
  clearMessages();
  showWelcome();
  renderConversationList();
  dom.messageInput.focus();
}

/* Send message — POST /api/v1/recommend */
async function sendMessage(text) {
  if (state.streaming || !text.trim()) return;

  if (!state.activeId) newChat();

  const convId = state.activeId;

  if (state.conversations[convId] && state.conversations[convId].title === 'New Chat') {
    state.conversations[convId].title = truncate(text);
    saveConversations();
    renderConversationList();
    dom.chatTitleText.textContent = state.conversations[convId].title;
  }

  appendUserMessage(text);
  const contentEl = appendAssistantMessage('', false);

  state.streaming = true;
  dom.sendBtn.disabled = true;
  dom.messageInput.disabled = true;

  try {
    const p = state.userProfile || {};
    const user_profile = {
      favourite:          p.favourite          || [],
      favourite_province: p.favourite_province || [],
      style:              p.style              || [],
      food:               p.food               || [],
      transportation:     p.transportation     || [],
      budget:             p.budget             || 'mid',
      avoid_crowd:        p.avoid_crowd        ?? false,
      saved_location:     p.saved_location     || [],
    };

    const reqBody = {
      message:         text,
      conversation_id: convId,
      nick_name:       state.userId,
      user_profile,
    };

    const res = await fetch(`${API_BASE}/recommend`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(reqBody),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}`);
    }

    const data  = await res.json();
    const reply = data.response || '';

    contentEl.innerHTML = typeof marked !== 'undefined'
      ? marked.parse(reply)
      : escapeHtml(reply);

  } catch (err) {
    contentEl.innerHTML = `<span style="color:var(--danger)">${escapeHtml(err.message)}</span>`;
    console.error(err);
  } finally {
    state.streaming = false;
    dom.sendBtn.disabled = !dom.messageInput.value.trim();
    dom.messageInput.disabled = false;
    dom.messageInput.focus();
    scrollToBottom();
  }
}

/* Delete history (server + local) */
async function deleteHistory(id) {
  try {
    const res = await fetch(`${API_BASE}/history/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch (err) {
    console.warn('Server delete failed:', err);
  }

  delete state.conversations[id];
  saveConversations();
  renderConversationList();

  if (state.activeId === id) {
    state.activeId = null;
    clearMessages();
    showWelcome();
    dom.chatTitleText.textContent = 'New Chat';
    dom.deleteHistoryBtn.style.display = 'none';
  }
}

/* ══════════════════════════════════════════
   PROFILE MODAL
══════════════════════════════════════════ */
let profileDraft = {};

function openProfileModal() {
  profileDraft = state.userProfile
    ? JSON.parse(JSON.stringify(state.userProfile))
    : { favourite_province: [], style: [], food: [], transportation: [], favourite: [] };
  renderAllChips();
  dom.profileBackdrop.classList.add('open');
}

function closeProfileModal() {
  dom.profileBackdrop.classList.remove('open');
}

function renderAllChips() {
  PROFILE_SECTIONS.forEach(({ containerId, key, label, icon }) => {
    renderChipGroup(containerId, key, profileDraft[key] || [], label, icon);
  });
}

function renderChipGroup(containerId, key, selected, sectionLabel, iconName) {
  const container = $(containerId);
  container.innerHTML = '';

  // Section label with Lucide icon
  if (sectionLabel) {
    const labelEl = document.createElement('div');
    labelEl.className = 'profile-section-label';
    labelEl.innerHTML = `<i data-lucide="${iconName}"></i>${sectionLabel}`;
    container.parentElement.insertBefore(labelEl, container);
    // Remove any previously inserted label to avoid duplicates
    const existing = container.parentElement.querySelectorAll('.profile-section-label');
    if (existing.length > 1) existing[0].remove();
    initIcons(labelEl);
  }

  PROFILE_OPTIONS[key].forEach(option => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'profile-chip' + (selected.includes(option) ? ' selected' : '');
    chip.textContent = option;
    chip.addEventListener('click', () => {
      const arr = profileDraft[key] || [];
      const idx = arr.indexOf(option);
      if (idx === -1) arr.push(option); else arr.splice(idx, 1);
      profileDraft[key] = arr;
      renderChipGroup(containerId, key, arr, sectionLabel, iconName);
    });
    container.appendChild(chip);
  });
}

dom.profileSaveBtn.addEventListener('click', () => {
  saveUserProfile(profileDraft);
  closeProfileModal();
});

dom.profileSkipBtn.addEventListener('click', closeProfileModal);
dom.editProfileBtn.addEventListener('click', openProfileModal);

/* ══════════════════════════════════════════
   CONFIRM MODAL
══════════════════════════════════════════ */
let pendingDeleteId = null;

function openDeleteModal(id) {
  pendingDeleteId = id;
  dom.modalBackdrop.classList.add('open');
}

function closeDeleteModal() {
  pendingDeleteId = null;
  dom.modalBackdrop.classList.remove('open');
}

dom.modalCancel.addEventListener('click', closeDeleteModal);
dom.modalBackdrop.addEventListener('click', e => {
  if (e.target === dom.modalBackdrop) closeDeleteModal();
});
dom.modalConfirm.addEventListener('click', async () => {
  if (pendingDeleteId) await deleteHistory(pendingDeleteId);
  closeDeleteModal();
});

/* ══════════════════════════════════════════
   EVENTS
══════════════════════════════════════════ */

dom.newChatBtn.addEventListener('click', () => {
  newChat();
  if (window.innerWidth < 1024) closeSidebar();
});

dom.deleteHistoryBtn.addEventListener('click', () => {
  if (state.activeId) openDeleteModal(state.activeId);
});

dom.messageInput.addEventListener('input', () => {
  dom.messageInput.style.height = 'auto';
  dom.messageInput.style.height = Math.min(dom.messageInput.scrollHeight, 200) + 'px';
  dom.sendBtn.disabled = !dom.messageInput.value.trim() || state.streaming;
});

dom.messageInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!dom.sendBtn.disabled) handleSend();
  }
});

dom.sendBtn.addEventListener('click', handleSend);

function handleSend() {
  const text = dom.messageInput.value.trim();
  if (!text || state.streaming) return;
  dom.messageInput.value = '';
  dom.messageInput.style.height = 'auto';
  dom.sendBtn.disabled = true;
  sendMessage(text);
}

/* Close sidebar when clicking outside on mobile/tablet */
document.addEventListener('click', e => {
  if (window.innerWidth < 1024
    && dom.sidebar.classList.contains('mobile-open')
    && !dom.sidebar.contains(e.target)
    && !dom.sidebarToggle.contains(e.target)) {
    closeSidebar();
  }
});

/* ══════════════════════════════════════════
   INIT
══════════════════════════════════════════ */
(function init() {
  if (typeof marked !== 'undefined') {
    marked.setOptions({ breaks: true, gfm: true });
  }

  // Hydrate all static Lucide icons in the HTML
  initIcons();

  renderConversationList();
  updateProfileBtn();

  const sorted = Object.values(state.conversations).sort((a, b) => b.createdAt - a.createdAt);
  if (sorted.length > 0) {
    loadConversation(sorted[0].id);
  } else {
    showWelcome();
  }

  if (!state.userProfile) openProfileModal();

  console.log(`GuidyTH — User ID: ${state.userId}`);
})();

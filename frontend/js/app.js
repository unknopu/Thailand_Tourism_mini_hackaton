/* ═══════════════════════════════════════════════════════
   MiniChat AI  –  app.js
   API base: http://localhost:1323/api/v1
═══════════════════════════════════════════════════════ */

const API_BASE = 'http://localhost:1323/api/v1';

/* ─── Profile options ─── */
const PROFILE_OPTIONS = {
  favourite_province: ['Bangkok', 'Chiang Mai', 'Chumphon', 'Ratchaburi', 'Yala', 'Chonburi'],
  style:              ['backpacker', 'nature', 'luxury', 'adventure', 'culture', 'family', 'romantic', 'photography'],
  food:               ['Noodle soup', 'Seafood', 'Som Tum', 'Hainanese chicken rice', 'Pad Thai', 'Larb', 'Vegetarian', 'Street food', 'Northern Thai food', 'Northeastern Thai food'],
  transportation:     ['train', 'plane', 'bus', 'car', 'motorcycle', 'boat'],
};

/* ─── State ─── */
const state = {
  userId: getOrCreateUserId(),
  conversations: loadConversations(),   // { [id]: { id, title, createdAt } }
  activeId: null,
  streaming: false,
  userProfile: loadUserProfile(),       // { favourite_province, style, food, transportation }
};

/* ─── DOM refs ─── */
const $ = id => document.getElementById(id);
const dom = {
  sidebar:          $('sidebar'),
  sidebarToggle:    $('sidebarToggle'),
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
  let id = localStorage.getItem('minichat_user_id');
  if (!id) {
    id = 'user_' + uuid();
    localStorage.setItem('minichat_user_id', id);
  }
  return id;
}

function loadConversations() {
  try {
    return JSON.parse(localStorage.getItem('minichat_conversations') || '{}');
  } catch { return {}; }
}

function saveConversations() {
  localStorage.setItem('minichat_conversations', JSON.stringify(state.conversations));
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
    return JSON.parse(localStorage.getItem('minichat_user_profile') || 'null');
  } catch { return null; }
}

function saveUserProfile(profile) {
  localStorage.setItem('minichat_user_profile', JSON.stringify(profile));
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
   SIDEBAR / CONVERSATIONS UI
══════════════════════════════════════════ */
function renderConversationList() {
  dom.convList.innerHTML = '';
  const sorted = Object.values(state.conversations)
    .sort((a, b) => b.createdAt - a.createdAt);

  if (sorted.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'font-size:12px;color:#6e6e80;padding:10px 12px;';
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
    delBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`;
    delBtn.addEventListener('click', e => {
      e.stopPropagation();
      openDeleteModal(conv.id);
    });

    item.appendChild(title);
    item.appendChild(delBtn);
    item.addEventListener('click', () => loadConversation(conv.id));
    dom.convList.appendChild(item);
  });
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
  if (dom.welcomeScreen) {
    dom.welcomeScreen.style.display = 'none';
  }
}

function showWelcome() {
  if (dom.welcomeScreen) {
    dom.welcomeScreen.style.display = '';
  }
}

function clearMessages() {
  // Remove all .message-row elements
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
        <img src="assets/logo.svg" alt="AI" />
      </div>
      <div class="assistant-body">
        <div class="assistant-content ${streaming ? 'typing-cursor' : ''}">${
          text
            ? (typeof marked !== 'undefined' ? marked.parse(text) : escapeHtml(text))
            : '<div class="loading-dots"><span></span><span></span><span></span></div>'
        }</div>
        <div class="message-actions">
          <button class="like-btn" title="Like this response">
            <svg class="like-icon-outline" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>
            <svg class="like-icon-filled" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>
          </button>
        </div>
      </div>
    </div>`;
  dom.chatMessages.appendChild(row);
  scrollToBottom();

  const contentEl = row.querySelector('.assistant-content');
  const likeBtn   = row.querySelector('.like-btn');

  // Restore liked state if content is already in favourites
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
    const res = await fetch(`${API_BASE}/chat/history/${id}`);
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
    title: 'New Chat',
    createdAt: Date.now(),
  };
  saveConversations();
  setActiveConversation(id);
  clearMessages();
  showWelcome();
  renderConversationList();
  dom.messageInput.focus();
}

/* Send message using stream endpoint */
async function sendMessage(text) {
  if (state.streaming || !text.trim()) return;

  // Create conversation if none is active
  if (!state.activeId) {
    newChat();
  }

  const convId = state.activeId;

  // Update title with first message
  if (state.conversations[convId] && state.conversations[convId].title === 'New Chat') {
    state.conversations[convId].title = truncate(text);
    saveConversations();
    renderConversationList();
    dom.chatTitleText.textContent = state.conversations[convId].title;
  }

  appendUserMessage(text);
  const contentEl = appendAssistantMessage('', true);

  state.streaming = true;
  dom.sendBtn.disabled = true;
  dom.messageInput.disabled = true;

  let accumulated = '';

  try {
    const reqBody = { message: text, conversation_id: convId };
    if (state.userProfile) reqBody.user_profile = state.userProfile;

    const res = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reqBody),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Handle SSE lines  (data: ...\n\n)  OR  raw JSON chunks
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed === 'data: [DONE]') continue;

        let chunk = '';

        if (trimmed.startsWith('data:')) {
          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr || jsonStr === '[DONE]') continue;
          try {
            const parsed = JSON.parse(jsonStr);
            // Support multiple common shapes
            chunk = parsed.content ?? parsed.text ?? parsed.delta ?? parsed.choices?.[0]?.delta?.content ?? '';
          } catch {
            chunk = jsonStr; // treat as raw text
          }
        } else {
          // Try raw JSON
          try {
            const parsed = JSON.parse(trimmed);
            chunk = parsed.content ?? parsed.text ?? parsed.delta ?? '';
          } catch {
            chunk = trimmed;
          }
        }

        if (chunk) {
          accumulated += chunk;
          contentEl.classList.add('typing-cursor');
          contentEl.innerHTML = typeof marked !== 'undefined'
            ? marked.parse(accumulated)
            : escapeHtml(accumulated);
          scrollToBottom();
        }
      }
    }

    // Process any remaining buffer
    if (buffer.trim()) {
      try {
        const parsed = JSON.parse(buffer.trim().startsWith('data:')
          ? buffer.trim().slice(5)
          : buffer.trim());
        const chunk = parsed.content ?? parsed.text ?? parsed.delta ?? '';
        if (chunk) {
          accumulated += chunk;
          contentEl.innerHTML = typeof marked !== 'undefined'
            ? marked.parse(accumulated)
            : escapeHtml(accumulated);
        }
      } catch { /* ignore */ }
    }

  } catch (err) {
    contentEl.innerHTML = `<span style="color:#fca5a5">Error: ${escapeHtml(err.message)}</span>`;
    console.error(err);
  } finally {
    contentEl.classList.remove('typing-cursor');
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
    const res = await fetch(`${API_BASE}/chat/history/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch (err) {
    // Log but still proceed with local cleanup
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
  renderChipGroup('chipsProvince',  'favourite_province', profileDraft.favourite_province || []);
  renderChipGroup('chipsStyle',     'style',              profileDraft.style || []);
  renderChipGroup('chipsFood',      'food',               profileDraft.food || []);
  renderChipGroup('chipsTransport', 'transportation',     profileDraft.transportation || []);
}

function renderChipGroup(containerId, key, selected) {
  const container = $(containerId);
  container.innerHTML = '';
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
      renderChipGroup(containerId, key, arr);
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
  if (pendingDeleteId) {
    await deleteHistory(pendingDeleteId);
  }
  closeDeleteModal();
});

/* ══════════════════════════════════════════
   EVENTS
══════════════════════════════════════════ */

/* New chat */
dom.newChatBtn.addEventListener('click', newChat);

/* Delete current chat (header button) */
dom.deleteHistoryBtn.addEventListener('click', () => {
  if (state.activeId) openDeleteModal(state.activeId);
});

/* Sidebar toggle */
dom.sidebarToggle.addEventListener('click', () => {
  const isMobile = window.innerWidth <= 640;
  if (isMobile) {
    dom.sidebar.classList.toggle('mobile-open');
  } else {
    dom.sidebar.classList.toggle('collapsed');
  }
});

/* Input: auto-resize + enable send button */
dom.messageInput.addEventListener('input', () => {
  dom.messageInput.style.height = 'auto';
  dom.messageInput.style.height = Math.min(dom.messageInput.scrollHeight, 200) + 'px';
  dom.sendBtn.disabled = !dom.messageInput.value.trim() || state.streaming;
});

/* Enter to send (Shift+Enter for newline) */
dom.messageInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!dom.sendBtn.disabled) handleSend();
  }
});

/* Send button click */
dom.sendBtn.addEventListener('click', handleSend);

function handleSend() {
  const text = dom.messageInput.value.trim();
  if (!text || state.streaming) return;
  dom.messageInput.value = '';
  dom.messageInput.style.height = 'auto';
  dom.sendBtn.disabled = true;
  sendMessage(text);
}

/* Close sidebar on mobile when clicking outside */
document.addEventListener('click', e => {
  if (window.innerWidth <= 640
    && dom.sidebar.classList.contains('mobile-open')
    && !dom.sidebar.contains(e.target)
    && e.target !== dom.sidebarToggle) {
    dom.sidebar.classList.remove('mobile-open');
  }
});

/* ══════════════════════════════════════════
   INIT
══════════════════════════════════════════ */
(function init() {
  // Configure marked options
  if (typeof marked !== 'undefined') {
    marked.setOptions({ breaks: true, gfm: true });
  }

  renderConversationList();
  updateProfileBtn();

  // Auto-select most recent conversation if any
  const sorted = Object.values(state.conversations).sort((a, b) => b.createdAt - a.createdAt);
  if (sorted.length > 0) {
    loadConversation(sorted[0].id);
  } else {
    showWelcome();
  }

  // Show profile modal on first visit (no profile saved yet)
  if (!state.userProfile) {
    openProfileModal();
  }

  console.log(`MiniChat AI — User ID: ${state.userId}`);
})();

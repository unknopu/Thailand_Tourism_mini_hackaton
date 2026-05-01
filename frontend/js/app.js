/* ═══════════════════════════════════════════════════════
   GuidyTH  –  app.js
   API base: /api/v1  (proxied through Nginx on port 8000)
═══════════════════════════════════════════════════════ */

const API_BASE = 'http://localhost:8000/api/v1';

/* ─── Profile options (keys must stay as-is — backend contract) ─── */
const PROFILE_OPTIONS = {
  favourite_province: ['Bangkok', 'Chiang Mai', 'Chumphon', 'Ratchaburi', 'Yala', 'Chonburi'],
  style:              ['Backpacker', 'Nature', 'Luxury', 'Adventure', 'Culture', 'Family', 'Romantic', 'Photography'],
  food:               ['Noodle soup', 'Seafood', 'Som Tum', 'Hainanese chicken rice', 'Pad Thai', 'Larb', 'Vegetarian', 'Street food', 'Northern Thai food', 'Northeastern Thai food'],
  transportation:     ['Train', 'Plane', 'Bus', 'Car', 'Motorcycle', 'Boat'],
};

/* ─── Profile section config ─── */
const PROFILE_SECTIONS = [
  { containerId: 'chipsName',      key: 'display_name',       label: 'Your Name',            icon: 'user',        type: 'text' },
  { containerId: 'chipsProvince',  key: 'favourite_province', label: 'Favourite Provinces',  icon: 'map-pin'      },
  { containerId: 'chipsStyle',     key: 'style',              label: 'Travel Style',          icon: 'backpack'     },
  { containerId: 'chipsFood',      key: 'food',               label: 'Favourite Food',        icon: 'utensils'     },
  { containerId: 'chipsTransport', key: 'transportation',     label: 'Getting Around',        icon: 'train-front'  },
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
  profileNextBtn:   $('profileNextBtn'),
  profileBackBtn:   $('profileBackBtn'),
  profileSkipBtn:   $('profileSkipBtn'),
  savedBackdrop:    $('savedBackdrop'),
  savedPlacesBtn:   $('savedPlacesBtn'),
  savedList:        $('savedList'),
  savedEmpty:       $('savedEmpty'),
  savedCloseBtn:    $('savedCloseBtn'),
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
    const name = state.userProfile.display_name?.trim();
    const label = dom.editProfileBtn.querySelector('.btn-label');
    if (label) label.textContent = name || 'Profile';
  } else {
    dom.editProfileBtn.classList.remove('has-profile');
    const label = dom.editProfileBtn.querySelector('.btn-label');
    if (label) label.textContent = 'Profile';
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

const WELCOME_CHIPS_DEFAULT = [
  { icon: 'map-pin',    text: 'What are the best hidden gems in Thailand?' },
  { icon: 'waves',      text: 'Best beach destinations for a relaxing trip' },
  { icon: 'utensils',   text: 'Must-try Thai street food experiences' },
  { icon: 'tent',       text: 'Nature stays and eco resorts in Thailand' },
  { icon: 'camera',     text: 'Most photogenic spots in Thailand' },
  { icon: 'backpack',   text: 'Budget travel tips for exploring Thailand' },
];

const PROVINCE_CHIPS = {
  'Bangkok': [
    { icon: 'utensils',    text: 'Best street food in Bangkok' },
    { icon: 'landmark',    text: 'Top temples to visit in Bangkok' },
    { icon: 'shopping-bag',text: 'Best night markets in Bangkok' },
    { icon: 'ship',        text: 'Chao Phraya river activities in Bangkok' },
    { icon: 'camera',      text: 'Most Instagrammable spots in Bangkok' },
    { icon: 'coffee',      text: 'Best cafes in Bangkok' },
  ],
  'Chiang Mai': [
    { icon: 'mountain',    text: 'Best viewpoints in Chiang Mai' },
    { icon: 'landmark',    text: 'Ancient temples to visit in Chiang Mai' },
    { icon: 'tent',        text: 'Nature retreats near Chiang Mai' },
    { icon: 'utensils',    text: 'Northern Thai food to try in Chiang Mai' },
    { icon: 'bike',        text: 'Cycling routes around Chiang Mai' },
    { icon: 'camera',      text: 'Photography spots in Chiang Mai' },
  ],
  'Chumphon': [
    { icon: 'waves',       text: 'Best beaches in Chumphon' },
    { icon: 'fish',        text: 'Diving spots near Chumphon' },
    { icon: 'tent',        text: 'Eco stays in Chumphon' },
    { icon: 'utensils',    text: 'Seafood restaurants in Chumphon' },
    { icon: 'map-pin',     text: 'Hidden gems in Chumphon' },
    { icon: 'sailboat',    text: 'Island hopping from Chumphon' },
  ],
  'Ratchaburi': [
    { icon: 'map-pin',     text: 'Things to do in Ratchaburi' },
    { icon: 'landmark',    text: 'Cultural sites in Ratchaburi' },
    { icon: 'utensils',    text: 'Local food to try in Ratchaburi' },
    { icon: 'tree-pine',   text: 'Nature spots in Ratchaburi' },
    { icon: 'camera',      text: 'Best photo spots in Ratchaburi' },
    { icon: 'shopping-bag',text: 'Markets in Ratchaburi' },
  ],
  'Yala': [
    { icon: 'map-pin',     text: 'Top attractions in Yala' },
    { icon: 'landmark',    text: 'Historical sites in Yala' },
    { icon: 'utensils',    text: 'Southern Thai food in Yala' },
    { icon: 'tree-pine',   text: 'Nature parks in Yala' },
    { icon: 'camera',      text: 'Scenic spots in Yala' },
    { icon: 'coffee',      text: 'Best cafes in Yala' },
  ],
  'Chonburi': [
    { icon: 'waves',       text: 'Best beaches in Chonburi' },
    { icon: 'utensils',    text: 'Seafood spots in Chonburi' },
    { icon: 'map-pin',     text: 'Top attractions near Pattaya' },
    { icon: 'fish',        text: 'Water activities in Chonburi' },
    { icon: 'shopping-bag',text: 'Night markets in Chonburi' },
    { icon: 'camera',      text: 'Most scenic spots in Chonburi' },
  ],
};

function getWelcomeChips() {
  const provinces = state.userProfile?.favourite_province;
  if (!provinces || provinces.length === 0) return WELCOME_CHIPS_DEFAULT;

  const pool = provinces.flatMap(p => PROVINCE_CHIPS[p] || []);
  if (pool.length === 0) return WELCOME_CHIPS_DEFAULT;

  // shuffle and take up to 6
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  return pool.slice(0, 6);
}

function renderWelcomeChips() {
  const container = document.getElementById('welcomeSuggestions');
  if (!container) return;
  container.innerHTML = '';
  getWelcomeChips().forEach(({ icon, text }) => {
    const btn = document.createElement('button');
    btn.className = 'welcome-chip';
    btn.innerHTML = `<i data-lucide="${icon}"></i>${text}`;
    btn.addEventListener('click', () => {
      dom.messageInput.value = text;
      dom.sendBtn.disabled = false;
      const wrap = document.getElementById('welcomeVideoWrap');
      if (wrap) wrap.classList.add('hidden');
      handleSend();
    });
    container.appendChild(btn);
  });
  initIcons(container);
}

function showWelcome() {
  if (dom.welcomeScreen) dom.welcomeScreen.style.display = '';
  const wrap = document.getElementById('welcomeVideoWrap');
  if (wrap) wrap.classList.remove('hidden');
  updateWelcomeGreeting();
  renderWelcomeChips();
}

function clearMessages() {
  dom.chatMessages.querySelectorAll('.message-row, .suggested-prompts').forEach(el => el.remove());
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
        <img src="assets/logo.png" alt="Guidy" />
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

/* ══════════════════════════════════════════
   SUGGESTED PROMPTS
══════════════════════════════════════════ */
function removeSuggestedPrompts() {
  dom.chatMessages.querySelectorAll('.suggested-prompts').forEach(el => el.remove());
}

function renderSuggestedPrompts(prompts, topPlace) {
  if (!prompts || prompts.length === 0) return;

  const row = document.createElement('div');
  row.className = 'suggested-prompts';

  prompts.forEach(prompt => {
    const btn = document.createElement('button');
    btn.className = 'suggested-prompt-btn';
    btn.textContent = prompt;

    const isSavePrompt = prompt.startsWith('Save ') && prompt.endsWith(' to my list');

    if (isSavePrompt) {
      btn.classList.add('save-btn');
    } else if (prompt.startsWith("That's all")) {
      btn.classList.add('end-btn');
    }

    btn.addEventListener('click', () => {
      removeSuggestedPrompts();

      if (isSavePrompt) {
        const placeName = topPlace?.name || topPlace || null;
        if (placeName) {
          const profile = state.userProfile || {
            favourite_province: [], style: [], food: [],
            transportation: [], favourite: [], saved_location: [],
          };
          if (!profile.saved_location) profile.saved_location = [];
          if (!profile.saved_location.includes(placeName)) {
            profile.saved_location.push(placeName);
            saveUserProfile(profile);
            appendAssistantMessage(`✅ Saved **${placeName}** to your list!`);
          } else {
            appendAssistantMessage(`📍 **${placeName}** is already in your saved list.`);
          }
        } else {
          appendAssistantMessage("I couldn't find a place to save. Try asking for a recommendation first!");
        }
        scrollToBottom();
        return;
      }

      if (prompt.startsWith("That's all")) {
        appendAssistantMessage("You're welcome! Have a wonderful trip to Thailand! 🇹🇭 Feel free to ask me anytime.");
        scrollToBottom();
        return;
      }

      dom.messageInput.value = prompt;
      const wrap = document.getElementById('welcomeVideoWrap');
      if (wrap) wrap.classList.add('hidden');
      handleSend();
    });

    row.appendChild(btn);
  });

  dom.chatMessages.appendChild(row);
  scrollToBottom();
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

  // If user already has a profile, let them quickly update province/interest
  // preferences for this new chat (skip the name step, keep existing name).
  if (state.userProfile) {
    openProfileModal(1);
  } else {
    dom.messageInput.focus();
  }
}

/* Send message — POST /api/v1/recommend */
async function sendMessage(text) {
  if (state.streaming || !text.trim()) return;

  removeSuggestedPrompts();

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
      nickname:        (state.userProfile?.display_name?.trim()) || state.userId,
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
    const reply = data.ai_reason || data.response || '';

    contentEl.innerHTML = typeof marked !== 'undefined'
      ? marked.parse(reply)
      : escapeHtml(reply);

    const suggestedPrompts = data.suggested_prompts || [];
    const topPlace = (data.recommendations || [])[0] || null;
    if (suggestedPrompts.length > 0) {
      renderSuggestedPrompts(suggestedPrompts, topPlace);
    }

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
    if (!state.userProfile) openProfileModal();
  }
}

/* ══════════════════════════════════════════
   PROFILE MODAL — step-by-step
══════════════════════════════════════════ */
let profileDraft       = {};
let currentStep        = 0;
let profileModalStartStep = 0; // lowest step reachable (1 when opened from New Chat)
let stepDirection      = 'forward'; // 'forward' | 'back'
let isSummaryStep      = false;

const domProfile = {
  get container()  { return $('profileStepsContainer'); },
  get dots()       { return $('profileStepsDots'); },
  get skipBtn()    { return $('profileSkipBtn'); },
  get backBtn()    { return $('profileBackBtn'); },
  get nextBtn()    { return $('profileNextBtn'); },
};

function openProfileModal(startStep = 0) {
  profileDraft = state.userProfile
    ? JSON.parse(JSON.stringify(state.userProfile))
    : { display_name: '', favourite_province: [], style: [], food: [], transportation: [], favourite: [] };
  if (profileDraft.display_name === undefined) profileDraft.display_name = '';
  if (!Array.isArray(profileDraft.favourite_province)) profileDraft.favourite_province = [];

  profileModalStartStep = startStep;
  currentStep   = startStep;
  isSummaryStep = false;
  stepDirection = 'forward';

  // Update modal header text to match context
  const titleEl = dom.profileBackdrop.querySelector('.profile-modal-title');
  const subEl   = dom.profileBackdrop.querySelector('.profile-modal-sub');
  if (startStep > 0) {
    if (titleEl) titleEl.textContent = 'Update preferences';
    if (subEl)   subEl.textContent   = 'Adjust your interests for this new chat.';
  } else {
    if (titleEl) titleEl.textContent = 'Tell us about you';
    if (subEl)   subEl.textContent   = 'Pick your preferences for personalised travel recommendations.';
  }

  renderStepDots();
  renderCurrentStep();
  updateStepFooter();
  dom.profileBackdrop.classList.add('open');
}

function closeProfileModal() {
  dom.profileBackdrop.classList.remove('open');
  dom.messageInput.focus();
}

function renderStepDots() {
  const dots = domProfile.dots;
  dots.innerHTML = '';
  PROFILE_SECTIONS.forEach((_, i) => {
    const dot = document.createElement('div');
    if (isSummaryStep) {
      dot.className = 'profile-dot completed';
    } else {
      dot.className = 'profile-dot'
        + (i === currentStep ? ' active' : '')
        + (i < currentStep || i < profileModalStartStep ? ' completed' : '');
    }
    dots.appendChild(dot);
  });
}

function renderCurrentStep() {
  const { key, label, icon, type } = PROFILE_SECTIONS[currentStep];
  const container = domProfile.container;
  container.innerHTML = '';

  const card = document.createElement('div');
  card.className = 'profile-step-card ' + (stepDirection === 'forward' ? 'slide-in-right' : 'slide-in-left');

  const labelEl = document.createElement('div');
  labelEl.className = 'profile-section-label';
  labelEl.innerHTML = `<i data-lucide="${icon}"></i>${label}`;
  card.appendChild(labelEl);
  initIcons(labelEl);

  if (type === 'text') {
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'profile-text-input';
    input.placeholder = 'Enter your name…';
    input.maxLength = 40;
    input.value = profileDraft[key] || '';
    input.addEventListener('input', () => { profileDraft[key] = input.value; });
    card.appendChild(input);
    setTimeout(() => input.focus(), 320);
  } else {
    const chips = document.createElement('div');
    chips.className = 'profile-chips';

    const selected = profileDraft[key] || [];
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
        chip.classList.toggle('selected', profileDraft[key].includes(option));
      });
      chips.appendChild(chip);
    });

    card.appendChild(chips);
  }

  container.appendChild(card);
}

function updateStepFooter() {
  const skip = domProfile.skipBtn;
  const back = domProfile.backBtn;
  const next = domProfile.nextBtn;

  if (isSummaryStep) {
    skip.style.display = 'none';
    back.style.display = 'none';
    next.textContent   = 'Start Exploring!';
    return;
  }

  const isFirst = currentStep === profileModalStartStep;
  const isLast  = currentStep === PROFILE_SECTIONS.length - 1;

  skip.style.display = '';
  skip.textContent   = isFirst ? 'Skip for now' : 'Skip';
  back.style.display = isFirst ? 'none' : '';
  next.textContent   = isLast  ? 'Save & Start' : 'Next';
}

function goToStep(index, direction) {
  isSummaryStep = false;
  stepDirection = direction;
  currentStep   = index;
  renderStepDots();
  renderCurrentStep();
  updateStepFooter();
}

function renderProfileSummaryStep() {
  const container = domProfile.container;
  container.innerHTML = '';

  const card = document.createElement('div');
  card.className = 'profile-step-card slide-in-right';

  const name = (profileDraft.display_name || '').trim() || 'Traveller';
  const isUpdate = profileModalStartStep > 0;

  const greet = document.createElement('div');
  greet.className = 'profile-summary-greeting';
  greet.textContent = isUpdate ? `Ready to explore, ${name}!` : `Welcome, ${name}!`;
  card.appendChild(greet);

  const subtitle = document.createElement('div');
  subtitle.className = 'profile-summary-subtitle';
  subtitle.textContent = isUpdate
    ? "Preferences updated for this chat:"
    : "Here's your travel profile:";
  card.appendChild(subtitle);

  const summarySections = [
    { label: 'Provinces',     key: 'favourite_province', icon: 'map-pin'    },
    { label: 'Travel Style',  key: 'style',              icon: 'backpack'   },
    { label: 'Food',          key: 'food',               icon: 'utensils'   },
    { label: 'Transport',     key: 'transportation',     icon: 'train-front'},
  ];

  let hasAny = false;
  summarySections.forEach(({ label, key, icon }) => {
    const items = profileDraft[key] || [];
    if (items.length === 0) return;
    hasAny = true;

    const section = document.createElement('div');
    section.className = 'profile-summary-section';

    const sectionLabel = document.createElement('div');
    sectionLabel.className = 'profile-summary-label';
    sectionLabel.innerHTML = `<i data-lucide="${icon}"></i>${label}`;
    section.appendChild(sectionLabel);

    const tags = document.createElement('div');
    tags.className = 'profile-summary-tags';
    items.forEach(item => {
      const tag = document.createElement('span');
      tag.className = 'profile-summary-tag';
      tag.textContent = item;
      tags.appendChild(tag);
    });
    section.appendChild(tags);
    card.appendChild(section);
  });

  if (!hasAny) {
    const empty = document.createElement('p');
    empty.className = 'profile-summary-empty';
    empty.textContent = 'No preferences selected — we\'ll recommend the best of Thailand for you!';
    card.appendChild(empty);
  }

  container.appendChild(card);
  initIcons(card);
}

function updateWelcomeGreeting() {
  const titleEl = document.querySelector('.welcome-title');
  const subEl   = document.querySelector('.welcome-sub');
  if (!titleEl || !subEl) return;
  const name = state.userProfile?.display_name?.trim();
  if (name) {
    titleEl.textContent = `Hi ${name}, where do you want to go?`;
    subEl.textContent   = 'Tell Guidy your dream destination.';
  } else {
    titleEl.textContent = 'Where do you want to go?';
    subEl.textContent   = 'Tell Guidy your dream destination.';
  }
}

domProfile.nextBtn.addEventListener('click', () => {
  if (isSummaryStep) {
    closeProfileModal();
    return;
  }
  if (currentStep < PROFILE_SECTIONS.length - 1) {
    goToStep(currentStep + 1, 'forward');
  } else {
    saveUserProfile(profileDraft);
    renderWelcomeChips();
    updateWelcomeGreeting();
    isSummaryStep = true;
    renderProfileSummaryStep();
    renderStepDots();
    updateStepFooter();
  }
});

domProfile.backBtn.addEventListener('click', () => {
  if (currentStep > profileModalStartStep) goToStep(currentStep - 1, 'back');
});

domProfile.skipBtn.addEventListener('click', () => {
  if (currentStep <= profileModalStartStep) {
    closeProfileModal();
  } else {
    goToStep(currentStep - 1, 'back');
  }
});

document.getElementById('profileResetBtn').addEventListener('click', () => {
  localStorage.removeItem('guidyth_user_profile');
  state.userProfile = null;
  updateProfileBtn();
  profileDraft          = { display_name: '', favourite_province: [], style: [], food: [], transportation: [], favourite: [] };
  currentStep           = 0;
  profileModalStartStep = 0;
  isSummaryStep         = false;
  stepDirection         = 'forward';

  const titleEl = dom.profileBackdrop.querySelector('.profile-modal-title');
  const subEl   = dom.profileBackdrop.querySelector('.profile-modal-sub');
  if (titleEl) titleEl.textContent = 'Tell us about you';
  if (subEl)   subEl.textContent   = 'Pick your preferences for personalised travel recommendations.';
  renderStepDots();
  renderCurrentStep();
  updateStepFooter();
});

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
   SAVED PLACES MODAL
══════════════════════════════════════════ */
function openSavedModal() {
  renderSavedList();
  dom.savedBackdrop.classList.add('open');
  initIcons(dom.savedBackdrop);
}

function closeSavedModal() {
  dom.savedBackdrop.classList.remove('open');
}

function renderSavedList() {
  dom.savedList.innerHTML = '';
  const saved = state.userProfile?.saved_location || [];

  if (saved.length === 0) {
    dom.savedEmpty.style.display = '';
    dom.savedList.style.display = 'none';
    return;
  }

  dom.savedEmpty.style.display = 'none';
  dom.savedList.style.display = '';

  saved.forEach((place, idx) => {
    const li = document.createElement('li');
    li.className = 'saved-item';

    const nameEl = document.createElement('span');
    nameEl.className = 'saved-item-name';
    nameEl.innerHTML = `<i data-lucide="map-pin"></i>${place}`;

    const removeBtn = document.createElement('button');
    removeBtn.className = 'saved-item-remove';
    removeBtn.title = 'Remove';
    removeBtn.innerHTML = '<i data-lucide="x"></i>';
    removeBtn.addEventListener('click', () => {
      const profile = state.userProfile || {};
      profile.saved_location = (profile.saved_location || []).filter((_, i) => i !== idx);
      saveUserProfile(profile);
      renderSavedList();
      initIcons(dom.savedList);
    });

    li.appendChild(nameEl);
    li.appendChild(removeBtn);
    dom.savedList.appendChild(li);
  });
}

dom.savedPlacesBtn.addEventListener('click', openSavedModal);
dom.savedCloseBtn.addEventListener('click', closeSavedModal);
dom.savedBackdrop.addEventListener('click', e => {
  if (e.target === dom.savedBackdrop) closeSavedModal();
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
  const wrap = document.getElementById('welcomeVideoWrap');
  if (wrap) wrap.classList.add('hidden');
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

  const splash = document.getElementById('splashScreen');
  setTimeout(() => {
    if (splash) splash.classList.add('fade-out');
    setTimeout(() => {
      if (splash) splash.style.display = 'none';
      if (!state.userProfile) openProfileModal();
    }, 500);
  }, 2000);

  console.log(`GuidyTH — User ID: ${state.userId}`);
})();

// JARVIS UI Application Logic
let voiceSynthesisEnabled = true;
let isListening = false;
let recognition = null;
let allOmniProfiles = [];

// Initialize Speech Recognition if supported
function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      isListening = true;
      const micBtn = document.getElementById('btn-mic');
      const micIcon = document.getElementById('mic-icon');
      micBtn.classList.add('bg-rose-600', 'text-white', 'animate-pulse');
      micIcon.className = 'fa-solid fa-microphone-lines text-sm';
      showToast('JARVIS is listening...', 'info');
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      document.getElementById('chat-input').value = transcript;
      handleChatSubmit(null, transcript);
    };

    recognition.onerror = (event) => {
      console.warn('Speech recognition error:', event.error);
      stopSpeechRecognition();
    };

    recognition.onend = () => {
      stopSpeechRecognition();
    };
  }
}

function toggleSpeechRecognition() {
  if (!recognition) {
    showToast('Speech recognition not supported in this browser.', 'error');
    return;
  }
  if (isListening) {
    recognition.stop();
  } else {
    try {
      recognition.start();
    } catch (e) {
      console.error(e);
    }
  }
}

function stopSpeechRecognition() {
  isListening = false;
  const micBtn = document.getElementById('btn-mic');
  const micIcon = document.getElementById('mic-icon');
  micBtn.classList.remove('bg-rose-600', 'text-white', 'animate-pulse');
  micIcon.className = 'fa-solid fa-microphone text-sm';
}

function toggleVoiceSpeech() {
  voiceSynthesisEnabled = !voiceSynthesisEnabled;
  const label = document.getElementById('voice-label');
  const icon = document.getElementById('voice-icon');
  if (voiceSynthesisEnabled) {
    label.innerText = 'Voice: ON';
    icon.className = 'fa-solid fa-volume-high text-cyan-400';
    showToast('Voice replies enabled', 'info');
  } else {
    label.innerText = 'Voice: OFF';
    icon.className = 'fa-solid fa-volume-xmark text-zinc-500';
    window.speechSynthesis && window.speechSynthesis.cancel();
    showToast('Voice replies muted', 'info');
  }
}

function speakText(text) {
  if (!voiceSynthesisEnabled || !window.speechSynthesis) return;
  window.speechSynthesis.cancel(); // Stop any pending speech
  // Clean markdown / symbols before speaking
  const clean = text.replace(/[*_#`~\[\]]/g, '').replace(/https?:\/\/\S+/g, 'link');
  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.rate = 1.05;
  utterance.pitch = 1.0;
  window.speechSynthesis.speak(utterance);
}

// Navigation Tabs
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.className = 'tab-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold tracking-wider uppercase transition-all bg-zinc-900/80 text-zinc-400 hover:text-zinc-200 border border-zinc-800 flex items-center gap-2';
  });
  document.querySelectorAll('.tab-view').forEach(view => {
    view.classList.add('hidden');
  });

  const activeBtn = document.getElementById(`tab-btn-${tabId}`);
  const activeView = document.getElementById(`view-${tabId}`);

  if (activeBtn) {
    activeBtn.className = 'tab-btn active px-3.5 py-1.5 rounded-lg text-xs font-semibold tracking-wider uppercase transition-all bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 flex items-center gap-2';
  }
  if (activeView) {
    activeView.classList.remove('hidden');
  }

  // Load relevant data on tab switch
  if (tabId === 'planner') loadTasks();
  if (tabId === 'memory') { loadNotes(); loadPrefs(); }
  if (tabId === 'omniroute') loadOmniProfiles();
  if (tabId === 'automation') loadSchedules();
}

// Chat & Command Execution
async function handleChatSubmit(event, directText) {
  if (event) event.preventDefault();
  const input = document.getElementById('chat-input');
  const command = (directText || input.value || '').trim();
  if (!command) return;

  input.value = '';
  appendUserMessage(command);

  // Add typing placeholder
  const typingId = appendTypingIndicator();

  try {
    const res = await fetch('/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command })
    });
    const data = await res.json();
    removeMessageElement(typingId);

    const reply = data.response || '(No response)';
    appendJarvisMessage(reply);
    speakText(reply);

    // Refresh telemetry
    pollStatus();
  } catch (err) {
    removeMessageElement(typingId);
    appendJarvisMessage(`Error communicating with JARVIS: ${err.message}`);
  }
}

function sendQuickCommand(cmd) {
  handleChatSubmit(null, cmd);
}

function appendUserMessage(text) {
  const stream = document.getElementById('chat-stream');
  const div = document.createElement('div');
  div.className = 'flex items-start justify-end gap-3';
  div.innerHTML = `
    <div class="msg-user p-3.5 rounded-xl max-w-[85%] text-sm text-zinc-100 shadow-md">
      ${escapeHtml(text)}
    </div>
    <div class="w-7 h-7 rounded-lg bg-indigo-950 border border-indigo-500/40 flex items-center justify-center text-indigo-300 text-xs shrink-0 font-hud">
      U
    </div>
  `;
  stream.appendChild(div);
  stream.scrollTop = stream.scrollHeight;
}

function appendJarvisMessage(text) {
  const stream = document.getElementById('chat-stream');
  const div = document.createElement('div');
  div.className = 'flex items-start gap-3 msg-jarvis p-4 rounded-xl';
  div.innerHTML = `
    <div class="w-7 h-7 rounded-lg bg-cyan-950 border border-cyan-500/40 flex items-center justify-center text-cyan-400 text-xs shrink-0 font-hud">
      J
    </div>
    <div class="flex-1 text-sm text-zinc-200 leading-relaxed font-sans whitespace-pre-wrap">
      ${formatJarvisResponse(text)}
    </div>
  `;
  stream.appendChild(div);
  stream.scrollTop = stream.scrollHeight;
}

function appendTypingIndicator() {
  const stream = document.getElementById('chat-stream');
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.className = 'flex items-start gap-3 msg-jarvis p-3 rounded-xl';
  div.innerHTML = `
    <div class="w-7 h-7 rounded-lg bg-cyan-950 border border-cyan-500/40 flex items-center justify-center text-cyan-400 text-xs shrink-0 font-hud">
      J
    </div>
    <div class="flex items-center gap-1.5 py-1 text-cyan-400">
      <span class="w-2 h-2 rounded-full bg-cyan-400 animate-bounce"></span>
      <span class="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style="animation-delay: 0.15s"></span>
      <span class="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style="animation-delay: 0.3s"></span>
    </div>
  `;
  stream.appendChild(div);
  stream.scrollTop = stream.scrollHeight;
  return id;
}

function removeMessageElement(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function formatJarvisResponse(text) {
  // Simple markdown-style code highlighting & line break preservation
  return escapeHtml(text)
    .replace(/```([\s\S]*?)```/g, '<pre class="bg-zinc-950 border border-cyan-900/40 p-3 rounded-lg my-2 font-mono text-xs text-cyan-300 overflow-x-auto">$1</pre>')
    .replace(/`([^`]+)`/g, '<code class="bg-zinc-800 px-1 py-0.5 rounded text-cyan-300 font-mono text-xs">$1</code>');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// Live Status & Telemetry Polling
async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    // Provider label
    const provLabel = document.getElementById('active-provider-label');
    provLabel.innerText = `Provider: ${data.ai_provider} (${data.ai_model || data.omniroute_model})`;

    // OmniRoute Header Pill
    const omniPill = document.getElementById('header-omni-pill');
    const omniDot = document.getElementById('header-omni-dot');
    const omniText = document.getElementById('header-omni-text');

    if (data.omniroute_online) {
      omniPill.className = 'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium bg-emerald-950/40 border-emerald-500/30 text-emerald-300';
      omniDot.className = 'w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]';
      omniText.innerText = 'OmniRoute Online';
    } else {
      omniPill.className = 'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium bg-zinc-900 border-zinc-700 text-zinc-400';
      omniDot.className = 'w-2 h-2 rounded-full bg-rose-500';
      omniText.innerText = 'OmniRoute Offline';
    }

    // System Telemetry
    if (data.system && data.system.psutil_available) {
      const s = data.system;
      document.getElementById('stat-cpu').innerText = `${s.cpu_percent}%`;
      document.getElementById('bar-cpu').style.width = `${Math.min(s.cpu_percent, 100)}%`;

      document.getElementById('stat-ram').innerText = `${s.ram_percent}%`;
      document.getElementById('bar-ram').style.width = `${Math.min(s.ram_percent, 100)}%`;

      document.getElementById('stat-disk').innerText = `${s.disk_percent}%`;
      document.getElementById('bar-disk').style.width = `${Math.min(s.disk_percent, 100)}%`;

      const hrs = Math.floor(s.uptime_seconds / 3600);
      const mins = Math.floor((s.uptime_seconds % 3600) / 60);
      document.getElementById('stat-uptime').innerText = `${hrs}h ${mins}m`;

      if (s.battery_percent !== null) {
        document.getElementById('stat-battery').innerText = `Battery: ${s.battery_percent}% ${s.battery_charging ? '⚡' : ''}`;
      }
    }
  } catch (err) {
    console.error('Status poll error:', err);
  }
}

// Planner / Tasks
async function loadTasks() {
  try {
    const res = await fetch('/api/tasks?all=1');
    const tasks = await res.json();
    const container = document.getElementById('tasks-container');

    if (!tasks || tasks.length === 0) {
      container.innerHTML = `<div class="p-8 text-center text-zinc-500 text-xs">No tasks registered in planner.</div>`;
      return;
    }

    container.innerHTML = tasks.map(t => `
      <div class="flex items-center justify-between p-3 rounded-xl ${t.done ? 'bg-zinc-900/40 border border-zinc-800/40 opacity-60' : 'bg-zinc-900/80 border border-zinc-800'} transition-all">
        <div class="flex items-center gap-3 flex-1">
          <input type="checkbox" ${t.done ? 'checked' : ''} onchange="toggleTask(${t.id})" class="w-4 h-4 rounded border-zinc-700 bg-zinc-800 text-indigo-500 focus:ring-0 cursor-pointer">
          <div>
            <p class="text-sm font-medium ${t.done ? 'line-through text-zinc-400' : 'text-zinc-200'}">${escapeHtml(t.text)}</p>
            ${t.due_date ? `<span class="text-[10px] font-mono text-indigo-400"><i class="fa-regular fa-clock"></i> Due: ${escapeHtml(t.due_date)}</span>` : ''}
          </div>
        </div>
        <button onclick="deleteTask(${t.id})" class="text-zinc-500 hover:text-rose-400 text-xs p-1.5 transition-colors" title="Delete Task">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

async function handleAddTask(e) {
  e.preventDefault();
  const textInput = document.getElementById('task-input-text');
  const dueInput = document.getElementById('task-input-due');
  const text = textInput.value.trim();
  const due = dueInput.value.trim() || null;
  if (!text) return;

  try {
    await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, due })
    });
    textInput.value = '';
    dueInput.value = '';
    loadTasks();
    showToast('Task added to Planner Matrix', 'success');
  } catch (err) {
    showToast('Failed to add task', 'error');
  }
}

async function toggleTask(id) {
  try {
    await fetch('/api/tasks/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    loadTasks();
  } catch (err) {
    console.error(err);
  }
}

async function deleteTask(id) {
  try {
    await fetch('/api/tasks', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    loadTasks();
    showToast('Task removed', 'info');
  } catch (err) {
    console.error(err);
  }
}

// Memory & Preferences
async function loadNotes(q = '') {
  try {
    const res = await fetch(`/api/notes${q ? '?q=' + encodeURIComponent(q) : ''}`);
    const notes = await res.json();
    const container = document.getElementById('notes-container');

    if (!notes || notes.length === 0) {
      container.innerHTML = `<div class="p-4 text-center text-zinc-500 text-xs">No memories found.</div>`;
      return;
    }

    container.innerHTML = notes.map(n => `
      <div class="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800 text-xs">
        <span class="text-zinc-300 font-sans truncate flex-1 pr-2">${escapeHtml(n.text)}</span>
        <button onclick="deleteNote(${n.id})" class="text-zinc-500 hover:text-rose-400 p-1" title="Forget Memory">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

function searchNotes() {
  const q = document.getElementById('note-search-input').value;
  loadNotes(q);
}

async function handleAddNote() {
  const input = document.getElementById('note-add-input');
  const text = input.value.trim();
  if (!text) return;
  try {
    await fetch('/api/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    input.value = '';
    loadNotes();
    showToast('Memory committed to vault', 'success');
  } catch (err) {
    showToast('Error saving note', 'error');
  }
}

async function deleteNote(id) {
  try {
    await fetch('/api/notes', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    loadNotes();
    showToast('Memory forgotten', 'info');
  } catch (err) {
    console.error(err);
  }
}

async function loadPrefs() {
  try {
    const res = await fetch('/api/prefs');
    const prefs = await res.json();
    const container = document.getElementById('prefs-container');

    const keys = Object.keys(prefs || {});
    if (keys.length === 0) {
      container.innerHTML = `<div class="p-4 text-center text-zinc-500 text-xs">No preferences set.</div>`;
      return;
    }

    container.innerHTML = keys.map(k => `
      <div class="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800 text-xs font-mono">
        <span class="text-purple-300 font-semibold">${escapeHtml(k)}: <span class="text-zinc-300 font-normal">${escapeHtml(prefs[k])}</span></span>
        <button onclick="deletePref('${k}')" class="text-zinc-500 hover:text-rose-400 p-1" title="Unset Preference">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

async function handleSetPref() {
  const keyInput = document.getElementById('pref-key-input');
  const valInput = document.getElementById('pref-val-input');
  const key = keyInput.value.trim();
  const value = valInput.value.trim();
  if (!key) return;

  try {
    await fetch('/api/prefs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, value })
    });
    keyInput.value = '';
    valInput.value = '';
    loadPrefs();
    showToast(`Preference '${key}' set`, 'success');
  } catch (err) {
    showToast('Error setting preference', 'error');
  }
}

async function deletePref(key) {
  try {
    await fetch('/api/prefs', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key })
    });
    loadPrefs();
    showToast(`Preference '${key}' removed`, 'info');
  } catch (err) {
    console.error(err);
  }
}

// Vision Screen Capture
async function triggerScreenCapture() {
  const out = document.getElementById('vision-output');
  out.innerText = 'Capturing screen and analyzing OCR text...';
  showToast('Vision Agent active: scanning display...', 'info');

  try {
    const res = await fetch('/api/vision/capture', { method: 'POST' });
    const data = await res.json();
    out.innerText = data.response || 'No text detected on screen.';
    showToast('Screen scan complete', 'success');
  } catch (err) {
    out.innerText = `Vision error: ${err.message}`;
    showToast('Vision capture failed', 'error');
  }
}

// OmniRoute Profiles & Agent Launch
async function loadOmniProfiles() {
  try {
    const res = await fetch('/api/omniroute/profiles');
    allOmniProfiles = await res.json();
    renderOmniProfiles(allOmniProfiles);
  } catch (err) {
    console.error(err);
  }
}

function filterOmniProfiles() {
  const query = document.getElementById('omni-search').value.toLowerCase().trim();
  const filtered = allOmniProfiles.filter(p => !query || p.name.toLowerCase().includes(query));
  renderOmniProfiles(filtered);
}

function renderOmniProfiles(profiles) {
  const grid = document.getElementById('omni-profiles-grid');
  if (!profiles || profiles.length === 0) {
    grid.innerHTML = `<div class="col-span-full py-8 text-center text-zinc-500 text-xs">No Claude Code profiles found.</div>`;
    return;
  }

  grid.innerHTML = profiles.map(p => `
    <div class="bg-zinc-900/80 border border-zinc-800 rounded-xl p-3.5 flex flex-col justify-between gap-2.5">
      <div>
        <div class="flex items-center justify-between gap-1 mb-1">
          <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">Profile</span>
          ${p.is_free ? '<span class="text-[9px] font-bold text-emerald-400 bg-emerald-950/60 px-1 py-0.5 rounded">FREE</span>' : ''}
        </div>
        <h4 class="text-xs font-semibold font-mono text-zinc-200 truncate" title="${p.name}">${p.name}</h4>
      </div>
      <button onclick="launchClaudeProfile('${p.name}')" class="w-full bg-zinc-800 hover:bg-amber-600 text-zinc-200 hover:text-black font-semibold text-xs py-1.5 px-3 rounded-lg border border-zinc-700 hover:border-amber-500 transition-all flex items-center justify-center gap-1.5 font-hud">
        <i class="fa-solid fa-terminal text-[10px]"></i> Launch Terminal
      </button>
    </div>
  `).join('');
}

async function launchClaudeProfile(profile) {
  showToast(`Launching Claude Code [${profile}] in terminal...`, 'info');
  try {
    const res = await fetch('/api/omniroute/launch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Terminal launched successfully!`, 'success');
    } else {
      showToast(`Launch failed: ${data.error}`, 'error');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

// Automation Schedules
async function loadSchedules() {
  try {
    const res = await fetch('/api/schedules');
    const schedules = await res.json();
    const container = document.getElementById('schedules-container');

    if (!schedules || schedules.length === 0) {
      container.innerHTML = `<div class="p-8 text-center text-zinc-500 text-xs">No recurring schedules registered. Use 'schedule &lt;command&gt; every &lt;when&gt;' to add one.</div>`;
      return;
    }

    container.innerHTML = schedules.map(s => `
      <div class="flex items-center justify-between p-3 rounded-xl bg-zinc-900/80 border border-zinc-800">
        <div>
          <p class="text-sm font-semibold text-zinc-200 font-mono">${escapeHtml(s.command)}</p>
          <span class="text-xs text-rose-400 font-mono"><i class="fa-solid fa-repeat"></i> ${escapeHtml(s.spec)}</span>
          ${s.last_run ? `<span class="text-[10px] text-zinc-500 ml-2">Last: ${escapeHtml(s.last_run)}</span>` : '<span class="text-[10px] text-zinc-500 ml-2">Never run</span>'}
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

async function triggerRunDueSchedules() {
  showToast('Executing due scheduled workflows...', 'info');
  try {
    const res = await fetch('/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: 'status' })
    });
    showToast('Scheduled jobs evaluated successfully', 'success');
  } catch (err) {
    showToast('Failed to run schedules', 'error');
  }
}

// Toast Notifications
function showToast(msg, type = 'info') {
  const toast = document.getElementById('toast');
  const text = document.getElementById('toast-message');
  const icon = document.getElementById('toast-icon');

  text.innerText = msg;
  if (type === 'error') {
    icon.className = 'fa-solid fa-circle-exclamation text-rose-400';
  } else if (type === 'success') {
    icon.className = 'fa-solid fa-circle-check text-emerald-400';
  } else {
    icon.className = 'fa-solid fa-circle-info text-cyan-400';
  }

  toast.classList.remove('translate-y-24', 'opacity-0');
  toast.classList.add('translate-y-0', 'opacity-100');

  setTimeout(() => {
    toast.classList.add('translate-y-24', 'opacity-0');
    toast.classList.remove('translate-y-0', 'opacity-100');
  }, 3500);
}

// Initial Boot & Polling
initSpeechRecognition();
pollStatus();
setInterval(pollStatus, 3000);

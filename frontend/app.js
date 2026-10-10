/**
 * TaskFlow AI - Interactive Frontend Controller
 * Connects directly to FastAPI REST Endpoints & Google Gemini AI
 */

const API_BASE = window.location.origin;

let state = {
  token: localStorage.getItem('taskflow_token') || null,
  currentUser: null,
  tasks: [],
  filterStatus: '',
  searchQuery: '',
};

// ==============================================================================
// App Initialization
// ==============================================================================
document.addEventListener('DOMContentLoaded', async () => {
  checkSystemHealth();
  if (state.token) {
    const verified = await fetchUserProfile();
    if (verified) {
      showDashboard();
      return;
    }
  }
  showAuth();
});

// ==============================================================================
// Health Check
// ==============================================================================
async function checkSystemHealth() {
  const dot = document.getElementById('healthDot');
  const text = document.getElementById('healthText');
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      const data = await res.json();
      dot.style.background = '#10b981';
      dot.style.boxShadow = '0 0 10px #10b981';
      text.textContent = data.ai_configured ? 'System Online (AI Active)' : 'System Online';
    } else {
      dot.style.background = '#f59e0b';
      text.textContent = 'Degraded';
    }
  } catch (err) {
    dot.style.background = '#f43f5e';
    text.textContent = 'Offline';
  }
}

// ==============================================================================
// Authentication
// ==============================================================================
function switchAuthTab(tab) {
  const tabLogin = document.getElementById('tabLogin');
  const tabRegister = document.getElementById('tabRegister');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');

  if (tab === 'login') {
    tabLogin.classList.add('active');
    tabRegister.classList.remove('active');
    loginForm.style.display = 'block';
    registerForm.style.display = 'none';
  } else {
    tabRegister.classList.add('active');
    tabLogin.classList.remove('active');
    registerForm.style.display = 'block';
    loginForm.style.display = 'none';
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;
  const btn = document.getElementById('loginSubmitBtn');

  btn.disabled = true;
  btn.textContent = 'Authenticating...';

  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Authentication failed');
    }

    state.token = data.access_token;
    state.currentUser = data.user;
    localStorage.setItem('taskflow_token', data.access_token);

    showToast(`Welcome back, ${data.user.name}!`, 'success');
    showDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sign In to Dashboard';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const name = document.getElementById('regName').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value;
  const btn = document.getElementById('regSubmitBtn');

  btn.disabled = true;
  btn.textContent = 'Creating Account...';

  try {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Registration failed');
    }

    showToast('Account registered successfully! Logging you in...', 'success');
    // Auto-login
    document.getElementById('loginEmail').value = email;
    document.getElementById('loginPassword').value = password;
    switchAuthTab('login');
    document.getElementById('loginForm').dispatchEvent(new Event('submit'));
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Create Account';
  }
}

function fillAndLogin(email, password) {
  document.getElementById('loginEmail').value = email;
  document.getElementById('loginPassword').value = password;
  switchAuthTab('login');
  document.getElementById('loginForm').dispatchEvent(new Event('submit'));
}

async function fetchUserProfile() {
  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${state.token}` },
    });
    if (!res.ok) {
      throw new Error('Session expired');
    }
    state.currentUser = await res.json();
    return true;
  } catch {
    state.token = null;
    state.currentUser = null;
    localStorage.removeItem('taskflow_token');
    return false;
  }
}

function logout() {
  state.token = null;
  state.currentUser = null;
  state.tasks = [];
  localStorage.removeItem('taskflow_token');
  showToast('You have been signed out.', 'info');
  showAuth();
}

document.getElementById('logoutBtn').addEventListener('click', logout);

// ==============================================================================
// View Switching
// ==============================================================================
function showAuth() {
  document.getElementById('authSection').style.display = 'flex';
  document.getElementById('dashboardSection').style.display = 'none';
  document.getElementById('userWidget').style.display = 'none';
}

function showDashboard() {
  document.getElementById('authSection').style.display = 'none';
  document.getElementById('dashboardSection').style.display = 'block';

  // Update User Widget
  const widget = document.getElementById('userWidget');
  const nameSpan = document.getElementById('userName');
  const roleBadge = document.getElementById('userRoleBadge');
  const avatar = document.getElementById('userAvatar');

  nameSpan.textContent = state.currentUser.name;
  roleBadge.textContent = state.currentUser.role.toUpperCase();
  roleBadge.className = `user-role-badge role-${state.currentUser.role}`;
  avatar.textContent = state.currentUser.name.charAt(0).toUpperCase();
  widget.style.display = 'flex';

  // Toggle Admin Portal view
  const adminPortal = document.getElementById('adminPortal');
  if (state.currentUser.role === 'admin') {
    adminPortal.style.display = 'block';
    loadAdminUsers();
  } else {
    adminPortal.style.display = 'none';
  }

  loadTasks();
}

// ==============================================================================
// Task Operations
// ==============================================================================
async function loadTasks() {
  try {
    const res = await fetch(`${API_BASE}/api/tasks/?page=1&limit=100`, {
      headers: { Authorization: `Bearer ${state.token}` },
    });
    if (!res.ok) throw new Error('Failed to load tasks');

    const data = await res.json();
    state.tasks = data.items;
    updateMetrics();
    renderKanban();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function updateMetrics() {
  const total = state.tasks.length;
  const pending = state.tasks.filter((t) => t.status === 'Pending').length;
  const inProgress = state.tasks.filter((t) => t.status === 'In Progress').length;
  const testing = state.tasks.filter((t) => t.status === 'Testing').length;
  const completed = state.tasks.filter((t) => t.status === 'Completed').length;

  document.getElementById('statTotal').textContent = total;
  document.getElementById('statPending').textContent = pending;
  document.getElementById('statInProgress').textContent = inProgress;
  document.getElementById('statTesting').textContent = testing;
  document.getElementById('statCompleted').textContent = completed;

  document.getElementById('badgePending').textContent = pending;
  document.getElementById('badgeInProgress').textContent = inProgress;
  document.getElementById('badgeTesting').textContent = testing;
  document.getElementById('badgeCompleted').textContent = completed;
}

function renderKanban() {
  const columns = {
    'Pending': document.getElementById('colPending'),
    'In Progress': document.getElementById('colInProgress'),
    'Testing': document.getElementById('colTesting'),
    'Completed': document.getElementById('colCompleted'),
  };

  // Clear columns
  Object.values(columns).forEach((col) => (col.innerHTML = ''));

  let filtered = state.tasks;

  // Filter by status pill if active
  if (state.filterStatus) {
    filtered = filtered.filter((t) => t.status === state.filterStatus);
  }

  // Filter by search query
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    filtered = filtered.filter(
      (t) => t.title.toLowerCase().includes(q) || (t.description && t.description.toLowerCase().includes(q))
    );
  }

  if (filtered.length === 0) {
    const emptyNotice = document.createElement('div');
    emptyNotice.style.padding = '2rem 1rem';
    emptyNotice.style.textAlign = 'center';
    emptyNotice.style.color = 'var(--text-muted)';
    emptyNotice.style.fontSize = '0.85rem';
    emptyNotice.textContent = 'No matching tasks found';
    if (state.filterStatus && columns[state.filterStatus]) {
      columns[state.filterStatus].appendChild(emptyNotice);
    }
    return;
  }

  filtered.forEach((task) => {
    const col = columns[task.status];
    if (col) {
      col.appendChild(createTaskCard(task));
    }
  });
}

function createTaskCard(task) {
  const card = document.createElement('div');
  card.className = 'task-card';
  card.onclick = () => openEditModal(task.id);

  const statusClass = {
    'Pending': 'chip-pending',
    'In Progress': 'chip-inprogress',
    'Testing': 'chip-testing',
    'Completed': 'chip-completed',
  }[task.status] || 'chip-pending';

  const dateStr = new Date(task.created_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });

  card.innerHTML = `
    <div class="task-card-header">
      <span class="task-title">${escapeHtml(task.title)}</span>
      <span class="task-status-chip ${statusClass}">${task.status}</span>
    </div>
    <div class="task-desc">${escapeHtml(task.description || 'No description provided.')}</div>
    <div class="task-card-footer">
      <span>#${task.id} • ${dateStr}</span>
      <span style="color: var(--text-muted);">Owner #${task.user_id}</span>
    </div>
  `;
  return card;
}

function handleSearch(val) {
  state.searchQuery = val;
  renderKanban();
}

function setFilterStatus(status) {
  state.filterStatus = status;
  document.querySelectorAll('.filter-pill').forEach((pill) => {
    if (pill.dataset.status === status) {
      pill.classList.add('active');
    } else {
      pill.classList.remove('active');
    }
  });
  renderKanban();
}

// ==============================================================================
// Task Creation & AI Description Generation
// ==============================================================================
function openCreateModal() {
  document.getElementById('taskTitle').value = '';
  document.getElementById('taskDescription').value = '';
  document.getElementById('aiSpinner').style.display = 'none';
  document.getElementById('createTaskModal').classList.add('open');
}

async function handleGenerateAIDescription() {
  const title = document.getElementById('taskTitle').value.trim();
  if (title.length < 3) {
    showToast('Please enter a task title with at least 3 characters first.', 'info');
    document.getElementById('taskTitle').focus();
    return;
  }

  const btn = document.getElementById('btnGenerateAI');
  const spinner = document.getElementById('aiSpinner');
  const textarea = document.getElementById('taskDescription');

  btn.disabled = true;
  spinner.style.display = 'block';

  try {
    const res = await fetch(`${API_BASE}/api/tasks/generate-description`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${state.token}`,
      },
      body: JSON.stringify({ title }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'AI generation failed');
    }

    textarea.value = data.description;
    showToast('✨ Task description generated with Gemini AI!', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
}

async function handleCreateTask(e) {
  e.preventDefault();
  const title = document.getElementById('taskTitle').value.trim();
  const description = document.getElementById('taskDescription').value.trim();
  const btn = document.getElementById('btnSubmitCreateTask');

  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/tasks/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${state.token}`,
      },
      body: JSON.stringify({ title, description: description || null }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Could not create task');

    closeModal('createTaskModal');
    showToast(`Task "${data.title}" created successfully!`, 'success');
    loadTasks();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

// ==============================================================================
// Task Details & Edit
// ==============================================================================
async function openEditModal(taskId) {
  try {
    const res = await fetch(`${API_BASE}/api/tasks/${taskId}`, {
      headers: { Authorization: `Bearer ${state.token}` },
    });
    if (!res.ok) throw new Error('Could not fetch task');
    const task = await res.json();

    document.getElementById('editTaskId').value = task.id;
    document.getElementById('editTaskTitle').value = task.title;
    document.getElementById('editTaskDescription').value = task.description || '';
    document.getElementById('editTaskStatus').value = task.status;
    document.getElementById('editModalHeading').textContent = `Task #${task.id} Details`;

    const statusSelect = document.getElementById('editTaskStatus');
    const notice = document.getElementById('statusNotice');

    if (state.currentUser.role === 'admin') {
      statusSelect.disabled = false;
      notice.style.display = 'none';
    } else {
      // Regular user cannot change status
      statusSelect.disabled = true;
      notice.style.display = 'block';
    }

    document.getElementById('editTaskModal').classList.add('open');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleUpdateTask(e) {
  e.preventDefault();
  const taskId = document.getElementById('editTaskId').value;
  const title = document.getElementById('editTaskTitle').value.trim();
  const description = document.getElementById('editTaskDescription').value.trim();
  const statusSelect = document.getElementById('editTaskStatus');

  const payload = { title, description };

  // Only include status if admin
  if (state.currentUser.role === 'admin') {
    payload.status = statusSelect.value;
  }

  try {
    const res = await fetch(`${API_BASE}/api/tasks/${taskId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${state.token}`,
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to update task');

    closeModal('editTaskModal');
    showToast('Task updated successfully!', 'success');
    loadTasks();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleDeleteTask() {
  const taskId = document.getElementById('editTaskId').value;
  if (!confirm(`Are you sure you want to permanently delete task #${taskId}?`)) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/tasks/${taskId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${state.token}` },
    });

    if (!res.ok && res.status !== 204) {
      throw new Error('Could not delete task');
    }

    closeModal('editTaskModal');
    showToast(`Task #${taskId} deleted.`, 'info');
    loadTasks();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==============================================================================
// Admin Management Portal
// ==============================================================================
async function loadAdminUsers() {
  if (state.currentUser.role !== 'admin') return;
  const tbody = document.getElementById('adminUsersTbody');
  tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Loading users...</td></tr>';

  try {
    const res = await fetch(`${API_BASE}/api/admin/users`, {
      headers: { Authorization: `Bearer ${state.token}` },
    });
    if (!res.ok) throw new Error('Failed to load user directory');

    const users = await res.json();
    tbody.innerHTML = '';

    users.forEach((u) => {
      const tr = document.createElement('tr');
      const dateStr = new Date(u.created_at).toLocaleDateString();
      const isSelf = u.id === state.currentUser.id;

      tr.innerHTML = `
        <td style="font-family: 'JetBrains Mono', monospace;">#${u.id}</td>
        <td><strong>${escapeHtml(u.name)}</strong></td>
        <td style="color: var(--text-secondary);">${escapeHtml(u.email)}</td>
        <td><span class="user-role-badge role-${u.role}">${u.role.toUpperCase()}</span></td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">${dateStr}</td>
        <td>
          ${
            isSelf
              ? '<span style="color: var(--text-muted); font-size: 0.8rem;">(Current Account)</span>'
              : `<button class="btn btn-secondary btn-sm" onclick="toggleUserRole(${u.id}, '${u.role}')">
                  ${u.role === 'admin' ? 'Demote to User' : 'Promote to Admin'}
                </button>`
          }
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color: #f43f5e;">${err.message}</td></tr>`;
  }
}

async function toggleUserRole(userId, currentRole) {
  const newRole = currentRole === 'admin' ? 'user' : 'admin';
  try {
    const res = await fetch(`${API_BASE}/api/admin/users/${userId}/role`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${state.token}`,
      },
      body: JSON.stringify({ role: newRole }),
    });

    if (!res.ok) throw new Error('Could not update user role');
    showToast(`User #${userId} role updated to ${newRole.toUpperCase()}!`, 'success');
    loadAdminUsers();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==============================================================================
// Modal & Toast Helpers
// ==============================================================================
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const icon = {
    success: '✅',
    error: '❌',
    info: 'ℹ️',
  }[type] || 'ℹ️';

  toast.innerHTML = `
    <span class="toast-icon">${icon}</span>
    <span class="toast-text">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(50px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>'"]/g, (tag) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;',
  }[tag] || tag));
}

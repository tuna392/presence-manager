import type{ Member, Settings, LogEntry } from './types'

// --- 状態管理 ---
let settings: Settings = { show_duration: true, status_list: "帰宅,在室" };
let statusOptions: string[] = [];
let membersData: Member[] = [];
let draggedIndex: number | null = null;

// --- データ読み込み ---
async function loadAdminData(): Promise<void> {
  const list = document.getElementById('admin-member-list');
  try {
    const resSet = await fetch('/api/settings');
    const fetchedSettings = await resSet.json() as Settings;
    if (fetchedSettings) settings = fetchedSettings;

    const toggle = document.getElementById('duration-toggle') as HTMLInputElement;
    if (toggle) toggle.checked = settings.show_duration;

    if (settings.status_list) {
      statusOptions = settings.status_list.split(',');
    } else {
      statusOptions = ["帰宅", "在室 2508", "7階", "授業or実習", "教員室4413", "学内", "喫煙", "図書館", "食事", "外出"];
    }
    renderStatusOptions();

    const resMem = await fetch('/api/members');
    membersData = await resMem.json() as Member[];
    renderMembers();
  } catch (error) {
    if (list) list.innerHTML = `<p style="color:red; text-align:center;">データの読み込みに失敗しました。</p>`;
  }
}

// --- メンバー描画 ---
function renderMembers(): void {
  const list = document.getElementById('admin-member-list');
  if (!list) return;
  list.innerHTML = "";

  membersData.forEach((m, index) => {
    const badgeClass = m.status === "帰宅" ? "status-kitaku" : "status-zaiseki";

    let timeStr = "--:--";
    if (m.updated_at) {
      let dStr = m.updated_at;
      if (!dStr.endsWith('Z') && !dStr.includes('+')) dStr += 'Z';
      const d = new Date(dStr);
      timeStr = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
    }

    const miniLogHtml = `<span style="background: #e9ecef; padding: 2px 6px; border-radius: 4px; color: #495057;">${timeStr} ${m.status}</span>`;

    list.innerHTML += `
      <li class="drag-item" draggable="true"
        ondragstart="dragStart(event, ${index})"
        ondragover="dragOver(event)"
        ondragenter="dragEnter(event)"
        ondragleave="dragLeave(event)"
        ondrop="dragDrop(event, ${index})">
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <div class="member-info">
            <span class="drag-handle">☰</span>
            <strong>${m.name}</strong>
            <span class="status-badge ${badgeClass}">${m.status}</span>
          </div>
          <div style="font-size: 0.85em; color: #666; margin-left: 35px;">
            最終更新: ${miniLogHtml}
          </div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <button onclick="openLogModal(${m.id}, '${m.name}')" style="background: #3498db; padding: 6px 12px; font-size: 0.9em;">📄 詳細ログ</button>
          <button class="delete-btn" onclick="removeMember(${m.id}, '${m.name}')">削除</button>
        </div>
      </li>
    `;
  });
}

// --- ログモーダル ---
function openLogModal(id: number, name: string): void {
  const title = document.getElementById('log-modal-title');
  if (title) title.innerText = `${name} さんの今週の記録`;

  const container = document.getElementById('log-list-container');
  if (!container) return;

  const member = membersData.find(m => m.id === id);

  if (!member || !member.recent_logs || member.recent_logs.length === 0) {
    container.innerHTML = "<p style='color:#7f8c8d; text-align:center;'>今週の打刻記録はまだありません。</p>";
  } else {
    let tableHTML = `<table class="log-table"><tr><th>日時</th><th>ステータス</th></tr>`;
    member.recent_logs.forEach((log: LogEntry) => {
      let dStr = log.timestamp;
      if (!dStr.endsWith('Z') && !dStr.includes('+')) dStr += 'Z';
      const d = new Date(dStr);
      const timeStr = `${d.getMonth()+1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
      tableHTML += `<tr><td>${timeStr}</td><td><strong>${log.status}</strong></td></tr>`;
    });
    tableHTML += `</table>`;
    container.innerHTML = tableHTML;
  }

  const modal = document.getElementById('log-modal');
  if (modal) modal.style.display = 'flex';
}

function closeLogModal(e: MouseEvent, force: boolean = false): void {
  const target = e.target as HTMLElement;
  if (force || target.id === 'log-modal') {
    const modal = document.getElementById('log-modal');
    if (modal) modal.style.display = 'none';
  }
}

// --- ドラッグ＆ドロップ ---
function dragStart(e: DragEvent, index: number): void {
  draggedIndex = index;
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
}

function dragOver(e: DragEvent): void { e.preventDefault(); }

function dragEnter(e: DragEvent): void {
  e.preventDefault();
  (e.currentTarget as HTMLElement).classList.add('drag-over-top');
}

function dragLeave(e: DragEvent): void {
  (e.currentTarget as HTMLElement).classList.remove('drag-over-top');
}

async function dragDrop(e: DragEvent, targetIndex: number): Promise<void> {
  e.preventDefault();
  (e.currentTarget as HTMLElement).classList.remove('drag-over-top');

  if (draggedIndex === targetIndex || draggedIndex === null) return;

  const item = membersData.splice(draggedIndex, 1)[0];
  membersData.splice(targetIndex, 0, item);
  draggedIndex = null;

  renderMembers();
  await saveOrder();
}

async function saveOrder(): Promise<void> {
  const orderedIds = membersData.map(m => m.id);
  await fetch('/api/members', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ordered_ids: orderedIds })
  });
}

// --- ステータス管理 ---
function renderStatusOptions(): void {
  const area = document.getElementById('status-badges-area');
  if (!area) return;
  area.innerHTML = "";

  statusOptions.forEach(status => {
    area.innerHTML += `
      <span style="background: #e0e0e0; padding: 5px 12px; border-radius: 15px; font-size: 0.9em; display: flex; align-items: center; gap: 5px;">
        ${status}
        <button onclick="removeStatusOption('${status}')" style="background: none; border: none; color: #e74c3c; padding: 0; font-size: 1.2em; line-height: 1; cursor: pointer;">×</button>
      </span>
    `;
  });
}

async function addStatusOption(): Promise<void> {
  const input = document.getElementById('new-status-name') as HTMLInputElement;
  const newStatus = input.value.trim();
  if (!newStatus) return;
  if (statusOptions.includes(newStatus)) { alert("すでに存在します"); return; }
  statusOptions.push(newStatus);
  input.value = "";
  renderStatusOptions();
  await updateSetting();
}

async function removeStatusOption(statusName: string): Promise<void> {
  if (statusName === "在室" || statusName === "帰宅") {
    alert("「在室」と「帰宅」は基本ステータスのため削除できません。");
    return;
  }
  statusOptions = statusOptions.filter(s => s !== statusName);
  renderStatusOptions();
  await updateSetting();
}

// --- 設定保存 ---
async function updateSetting(): Promise<void> {
  const toggle = document.getElementById('duration-toggle') as HTMLInputElement;
  const isChecked = toggle ? toggle.checked : false;
  const joinedStatus = statusOptions.join(',');
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ show_duration: isChecked, status_list: joinedStatus })
  });
}

// --- メンバー追加・削除 ---
async function addMember(): Promise<void> {
  const nameInput = document.getElementById('new-member-name') as HTMLInputElement;
  const name = nameInput.value;
  if (!name) { alert("名前を入力してください！"); return; }
  await fetch('/api/members', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name, is_admin: false })
  });
  nameInput.value = "";
  await loadAdminData();
}

async function removeMember(id: number, name: string): Promise<void> {
  if (!confirm(`本当に「${name}」さんを削除しますか？\n※この操作は取り消せません。`)) return;
  await fetch(`/api/members?id=${id}`, { method: 'DELETE' });
  await loadAdminData();
}

// --- グローバル公開 ---
(window as any).openLogModal = openLogModal;
(window as any).closeLogModal = closeLogModal;
(window as any).dragStart = dragStart;
(window as any).dragOver = dragOver;
(window as any).dragEnter = dragEnter;
(window as any).dragLeave = dragLeave;
(window as any).dragDrop = dragDrop;
(window as any).addStatusOption = addStatusOption;
(window as any).removeStatusOption = removeStatusOption;
(window as any).updateSetting = updateSetting;
(window as any).addMember = addMember;
(window as any).removeMember = removeMember;

// --- 起動 ---
document.addEventListener("DOMContentLoaded", loadAdminData);
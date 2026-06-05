import type { Member, Settings} from './types'

// --- 状態管理 ---
let settings: Settings = { show_duration: true, status_list: "帰宅,在室 2508" };
let membersData: Member[] = [];
let activeMemberId: number | null = null;

// --- ステータスカラー ---
function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    "在室 2508": "#2ecc71",
    "7階": "#1abc9c",
    "学内": "#27ae60",
    "教員室4413": "#e74c3c",
    "授業or実習": "#f1c40f",
    "図書館": "#8e44ad",
    "食事": "#f39c12",
    "外出": "#3498db",
    "喫煙": "#a0522d",
    "帰宅": "#bdc3c7",
    "外研": "#95a5a6",
  };
  if (colorMap[status]) return colorMap[status];
  const hash = [...status].reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return `hsl(${hash % 360}, 60%, 50%)`;
}

// --- ポーリング間隔 ---
function getRefreshInterval(): number {
  const hour = new Date().getHours();
  return (hour >= 22 || hour < 8) ? 7200000 : 900000;
}

function scheduleNextRefresh(): void {
  setTimeout(() => {
    loadBoardData();
    scheduleNextRefresh();
  }, getRefreshInterval());
}

// --- データ取得 ---
async function loadBoardData(): Promise<void> {
  try {
    const [resSet, resMem] = await Promise.all([
      fetch('/api/settings'),
      fetch('/api/members')
    ]);
    settings = await resSet.json() as Settings;
    membersData = await resMem.json() as Member[];
    renderBoard();
  } catch (error) {
    const container = document.getElementById('board-container');
    if (container) {
      container.innerHTML = `<p style="color:red; text-align:center;">データの読み込みに失敗しました。</p>`;
    }
  }
}

// --- 描画 ---
function renderBoard(): void {
  const container = document.getElementById('board-container');
  if (!container) return;
  container.innerHTML = "";

  membersData.forEach(m => {
    const color = getStatusColor(m.status);
    const opacity = m.status === "帰宅" ? "0.5" : "1";
    const bgLight = `${color}15`;

    let durationString = "";
    if (settings.show_duration && m.weekly_minutes !== undefined) {
      const h = Math.floor(m.weekly_minutes / 60);
      const min = m.weekly_minutes % 60;
      durationString = `今週: ${h}時間${min}分`;
    }

    container.innerHTML += `
      <div class="member-card" style="border-color: ${color}; background-color: ${bgLight}; opacity: ${opacity};" onclick="openModal(${m.id}, '${m.name}')">
        <div class="member-name">${m.name}</div>
        <div class="status-label" style="background-color: ${color};">${m.status}</div>
        <div class="duration-text">${durationString}</div>
      </div>
    `;
  });
}

// --- モーダル ---
function openModal(id: number, name: string): void {
  activeMemberId = id;
  const modalUserName = document.getElementById('modal-user-name');
  if (modalUserName) modalUserName.innerText = name;

  const grid = document.getElementById('modal-btn-grid');
  if (!grid) return;
  grid.innerHTML = "";

  const statusList = settings.status_list ? settings.status_list.split(',') : ["帰宅", "在室 2508"];
  statusList.forEach((status: string) => {
    const color = getStatusColor(status);
    grid.innerHTML += `
      <button class="status-btn" style="background-color: ${color};" onclick="selectStatus('${status}')">
        ${status}
      </button>
    `;
  });

  const modal = document.getElementById('status-modal');
  if (modal) modal.style.display = 'flex';
}

function closeModal(e: MouseEvent, force: boolean = false): void {
  const target = e.target as HTMLElement;
  if (force || target.id === 'status-modal') {
    const modal = document.getElementById('status-modal');
    if (modal) modal.style.display = 'none';
  }
}

// --- ステータス更新 ---
async function selectStatus(newStatus: string): Promise<void> {
  const modal = document.getElementById('status-modal');
  if (modal) modal.style.display = 'none';

  const targetMember = membersData.find(m => m.id === activeMemberId);
  if (!targetMember || targetMember.status === newStatus) return;

  targetMember.status = newStatus;
  targetMember.updated_at = new Date().toISOString();
  renderBoard();

  try {
    await fetch('/api/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: activeMemberId, status: newStatus })
    });
  } catch (err) {
    console.error("更新エラー", err);
    loadBoardData();
  }
}

// --- グローバル公開（HTMLのonclickから呼ぶため） ---
(window as any).openModal = openModal;
(window as any).closeModal = closeModal;
(window as any).selectStatus = selectStatus;

// --- 起動 ---
document.addEventListener("DOMContentLoaded", () => {
  loadBoardData();
  scheduleNextRefresh();
});
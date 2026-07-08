const state = {
  user: null, robotId: null, view: sessionStorage.getItem("onplant_view") || "dashboard",
  autoTimer: null, latestSummary: null, boardCategory: "?꾩껜", boardPosts: [],
  loginMode: "login", profileAvatarData: "", selectedPost: null
};

const pageText = {
  dashboard: ["메인 대시보드", "식물의 현재 상태를 한눈에 확인합니다."],
  live: ["실시간 화면", "카메라와 LiDAR 실시간 맵을 확인합니다."],
  history: ["센서 기록", "센서 변화 추이를 확인합니다."],
  move: ["이동 로그", "FSM 주행 로그와 최적 조도 복귀 흐름을 확인합니다."],
  control: ["제어/설정", "로봇과 디스플레이 동작 설정을 저장합니다."],
  board: ["관리 게시판", "목차 목록에서 게시글을 읽어 확인합니다."],
  admin: ["계정/로봇 설정", "관리자 전용 계정 연동 화면입니다."]
};

const $ = (id) => document.getElementById(id);
const fmt = (value, digits = 1) => value === null || value === undefined ? "--" : Number(value).toFixed(digits);
const isAdmin = () => state.user?.role === "admin";

function escapeHtml(value) { return String(value).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;"); }
function showToast(message) { const toast = $("toast"); toast.textContent = message; toast.classList.add("show"); setTimeout(() => toast.classList.remove("show"), 1600); }
async function api(url, options) { const response = await fetch(url, options); if (!response.ok) throw new Error(await response.text()); return response.json(); }

function showApp(user) {
  state.user = user; state.robotId = user.robot_id;
  sessionStorage.setItem("onplant_user", JSON.stringify(user));
  $("currentUser").textContent = `${user.display_name} (${user.username})`;
  $("loginScreen").classList.add("hidden"); $("appRoot").classList.remove("hidden");
  document.querySelectorAll(".admin-only").forEach((node) => node.classList.toggle("hidden", !isAdmin()));
  document.querySelectorAll("#mainNav .nav-item:not(.admin-only)").forEach((node) => node.classList.toggle("hidden", isAdmin()));
  setView(isAdmin() ? "admin" : state.view);
}
function showLogin() { sessionStorage.removeItem("onplant_user"); state.user = null; state.robotId = null; $("appRoot").classList.add("hidden"); $("loginScreen").classList.remove("hidden"); }
function setLoginMode(mode) { state.loginMode = mode; $("loginTab").classList.toggle("active", mode === "login"); $("registerTab").classList.toggle("active", mode === "register"); document.querySelectorAll(".register-only").forEach((node) => node.classList.toggle("hidden", mode !== "register")); $("loginSubmit").textContent = mode === "login" ? "로그인" : "회원가입"; }

async function submitLogin() {
  const username = $("loginUsername").value.trim(); const password = $("loginPassword").value;
  if (!username || !password) return showToast("아이디와 비밀번호를 입력하세요.");
  const endpoint = state.loginMode === "login" ? "/api/auth/login" : "/api/auth/register";
  const payload = state.loginMode === "login" ? { username, password } : { username, password, display_name: $("displayName").value.trim() || "사용자", plant_name: $("registerPlantName").value.trim() || "토로예" };
  try { const user = await api(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); showApp(user); await refreshAll(); }
  catch { showToast(state.loginMode === "login" ? "로그인 정보를 확인하세요." : "이미 있는 아이디일 수 있습니다."); }
}

function setView(view) {
  if (isAdmin() && view !== "admin") view = "admin";
  state.view = view; sessionStorage.setItem("onplant_view", view);
  document.querySelectorAll(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  document.querySelectorAll(".view").forEach((section) => section.classList.toggle("active", section.id === `view-${view}`));
  $("pageTitle").textContent = pageText[view][0]; $("pageSub").textContent = pageText[view][1];
  refreshAll();
}

async function refreshSummary() {
  if (!state.robotId || isAdmin()) return;
  const summary = await api(`/api/robots/${encodeURIComponent(state.robotId)}/summary`);
  state.latestSummary = summary; const { latest, status, config, robot } = summary;
  $("plantName").textContent = robot.plant_name; $("robotName").textContent = `${robot.name} 쨌 ${robot.link_code || "?곕룞肄붾뱶 ?놁쓬"}`;
  renderPlantAvatar(robot.plant_avatar);
  $("statusPill").textContent = status.level; $("statusPill").className = `status-pill ${status.tone}`;
  $("statusEmoji").textContent = status.emoji; $("statusLevel").textContent = status.level; $("statusMessage").textContent = status.message; $("recommendation").textContent = status.recommendation;
  $("temperature").textContent = latest ? fmt(latest.temperature) : "--"; $("humidity").textContent = latest ? fmt(latest.humidity) : "--"; $("lux").textContent = latest ? fmt(latest.lux, 0) : "--"; $("soil").textContent = latest ? fmt(latest.soil_moisture) : "--";
  const profile = summary.plant_profile || {};
  $("plantSpecies").textContent = profile.species || "?섏썡?쒖븘"; $("luxTarget").textContent = `${profile.lux_target || 900} lux`; $("tempRange").textContent = profile.temperature_range || "18~28째C"; $("humidityRange").textContent = profile.humidity_range || "35~60%"; $("soilRange").textContent = profile.soil_moisture_range || "20~45%"; $("plantNote").textContent = profile.note || "";
  $("speakerVolume").value = config.speaker_volume; $("displayBrightness").value = config.display_brightness; $("exploreSeconds").value = config.explore_seconds; $("driveEnabled").value = String(config.drive_enabled); $("lidarSpeed").value = config.lidar_speed ?? 45;
  renderCamera(summary.display?.camera_visible);
}

function renderPlantAvatar(avatar) { [$("plantAvatar"), $("profilePreview")].forEach((node) => { if (!node) return; if (avatar) { node.style.backgroundImage = `url("${avatar}")`; node.classList.add("has-image"); } else { node.style.backgroundImage = ""; node.classList.remove("has-image"); } }); }
function renderCamera(visible) { $("cameraState").textContent = visible ? "리모컨 4번 표시 중" : "리모컨 5번 숨김"; $("videoBox").classList.toggle("camera-on", Boolean(visible)); $("cameraText").textContent = visible ? "카메라 화면 표시 상태입니다. 실제 스트림은 로봇 연동 시 자동 연결됩니다." : "리모컨 4번을 누르면 카메라 화면을 표시하고, 5번을 누르면 숨깁니다."; }

async function refreshHistory() {
  if (state.view !== "history") return; const rows = await api(`/api/robots/${encodeURIComponent(state.robotId)}/history?limit=80`); drawChart(rows);
  $("historyRows").innerHTML = rows.slice().reverse().map((item) => `<tr><td>${item.id}</td><td>${new Date(item.received_at).toLocaleString()}</td><td>${fmt(item.lux)}</td><td>${fmt(item.temperature)}</td><td>${fmt(item.humidity)}</td><td>${fmt(item.soil_moisture)}</td></tr>`).join("");
}
function drawChart(rows) {
  const canvas = $("historyChart"); const ctx = canvas.getContext("2d"); const width = canvas.width; const height = canvas.height; const pad = 32;
  ctx.clearRect(0,0,width,height); ctx.fillStyle = "#fff"; ctx.fillRect(0,0,width,height); ctx.strokeStyle = "#dbe5dc"; ctx.lineWidth = 1;
  for (let i=0;i<4;i+=1){ const y = pad + ((height-pad*2)*i/3); ctx.beginPath(); ctx.moveTo(pad,y); ctx.lineTo(width-pad,y); ctx.stroke(); }
  const points = rows.filter((row) => row.lux !== null && row.lux !== undefined); if (points.length < 2) return;
  const values = points.map((row) => Number(row.lux)); const min = Math.min(...values); const max = Math.max(...values); const range = Math.max(1, max-min);
  ctx.strokeStyle = "#197236"; ctx.lineWidth = 3; ctx.beginPath();
  points.forEach((row,index) => { const x = pad + ((width-pad*2)*index/Math.max(1,points.length-1)); const y = height-pad-((Number(row.lux)-min)/range)*(height-pad*2); if(index===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); }); ctx.stroke();
}

function drawLidar(frame) {
  const canvas = $("lidarCanvas"); if (!canvas) return; const ctx = canvas.getContext("2d"); const width = canvas.width; const height = canvas.height; const cx = width/2; const robotY = height-44; const scale = Math.min((width-80)/1200, (height-86)/900); const points = frame?.points || [];
  ctx.clearRect(0,0,width,height); ctx.fillStyle = "#fbfdfb"; ctx.fillRect(0,0,width,height); ctx.strokeStyle = "#dbe5dc"; ctx.lineWidth = 1; ctx.font = "12px Arial"; ctx.fillStyle = "#69736d";
  for (let x=100; x<=900; x+=100) { const sy = robotY - x*scale; ctx.beginPath(); ctx.moveTo(32,sy); ctx.lineTo(width-32,sy); ctx.stroke(); if (x%200===0) ctx.fillText(`${x}mm`,38,sy-4); }
  for (let y=-500; y<=500; y+=100) { const sx = cx - y*scale; ctx.beginPath(); ctx.moveTo(sx,24); ctx.lineTo(sx,robotY+20); ctx.stroke(); }
  if (frame?.front_blocked || frame?.danger || frame?.emergency) { ctx.fillStyle = frame.emergency ? "rgba(189,71,71,.20)" : "rgba(242,164,0,.16)"; ctx.fillRect(cx-105*scale,28,210*scale,robotY-28); }
  ctx.strokeStyle = "#197236"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(cx,robotY-42); ctx.lineTo(cx-42,robotY+22); ctx.lineTo(cx+42,robotY+22); ctx.closePath(); ctx.stroke(); ctx.fillStyle = "rgba(25,114,54,.10)"; ctx.fill(); ctx.fillStyle = "#197236"; ctx.fillText("ROBOT",cx-22,robotY+38);
  for (const point of points) { const sx = cx - Number(point.y)*scale; const sy = robotY - Number(point.x)*scale; if (sx<0||sx>width||sy<0||sy>height) continue; ctx.beginPath(); ctx.arc(sx,sy,point.ignored ? 2 : 3,0,Math.PI*2); ctx.fillStyle = point.ignored ? "rgba(105,115,109,.35)" : "#2d9cdb"; ctx.fill(); }
}
function phaseName(frame) {
  if (!frame) return "WAIT";
  if (frame.state === "EXPLORE") return "EXPLORE";
  if (frame.state === "RETURN_TO_BEST") return "RETURN";
  if (frame.state === "SEEK_LIGHT") return "SEEK";
  if (frame.state === "AVOID") return "AVOID";
  if (frame.state === "BACKUP") return "BACKUP";
  if (frame.state === "IDLE") return "STOP";
  return frame.state || "WAIT";
}
function renderLidarPhase(frame) {
  const phaseLabel = $("phaseLabel"); if (!phaseLabel) return;
  if (!frame) {
    phaseLabel.textContent = "WAIT";
    $("phaseBest").textContent = "--";
    $("phaseLux").textContent = "--";
    $("phaseReturn").textContent = "--";
    $("phaseSeek").textContent = "--";
    return;
  }
  const bestLux = frame.best_lux ?? null;
  const currentLux = frame.current_lux ?? null;
  const err = frame.lux_error ?? null;
  phaseLabel.textContent = `${phaseName(frame)} / ${frame.action || "STOP"}`;
  $("phaseBest").textContent = bestLux === null ? "--" : `best ${fmt(bestLux, 0)} lx @ ${fmt(frame.best_time, 1)}s`;
  $("phaseLux").textContent = currentLux === null ? "--" : `now ${fmt(currentLux, 0)} lx / err ${fmt(err, 0)} lx`;
  $("phaseReturn").textContent = frame.state === "RETURN_TO_BEST" ? `${frame.return_index || 0}/${frame.return_total || 0} / ${fmt(frame.return_elapsed, 1)}s / avoid ${frame.return_avoid_count || 0} / pos(${fmt(frame.pose_x, 1)},${fmt(frame.pose_y, 1)}) -> best(${fmt(frame.best_x, 1)},${fmt(frame.best_y, 1)}) ${frame.heading || ""} blocked ${frame.blocked_count || 0}` : "--";
  $("phaseSeek").textContent = frame.state === "SEEK_LIGHT" ? `${fmt(frame.seek_elapsed, 1)}/${fmt(frame.seek_seconds, 1)}s` : "--";
}
async function refreshLidar() { if (!state.robotId || state.view !== "live") return; try { const frame = await api(`/api/robots/${encodeURIComponent(state.robotId)}/lidar`); if (!frame) { $("lidarState").textContent = "WAIT"; $("lidarUpdated").textContent = "--"; renderLidarPhase(null); drawLidar(null); return; } const flags = frame.emergency ? "EMERGENCY" : frame.danger ? "DANGER" : frame.front_blocked ? "BLOCKED" : "CLEAR"; $("lidarState").textContent = `${frame.state} / ${frame.action} / ${flags} / ${frame.points.length}pts`; $("lidarUpdated").textContent = new Date(frame.received_at).toLocaleTimeString(); renderLidarPhase(frame); drawLidar(frame); } catch { $("lidarState").textContent = "OFFLINE"; $("lidarUpdated").textContent = "--"; renderLidarPhase(null); } }

async function refreshMoveLogs() { if (state.view !== "move") return; const logs = await api(`/api/robots/${encodeURIComponent(state.robotId)}/move-logs?limit=100`); $("moveRows").innerHTML = logs.slice().reverse().map((item) => `<div class="log-item"><strong>${escapeHtml(item.state)} 쨌 ${escapeHtml(item.action)}</strong><div>${escapeHtml(item.message || "-")}</div><div class="meta">紐⑺몴 ${fmt(item.target_lux,0)} lux 쨌 ?꾩옱 ${fmt(item.current_lux,0)} lux 쨌 ${new Date(item.created_at).toLocaleString()}</div></div>`).join("") || `<div class="muted">?대룞 濡쒓렇媛 ?놁뒿?덈떎.</div>`; }
async function refreshCommands() { if (state.view !== "control") return; const commands = await api(`/api/robots/${encodeURIComponent(state.robotId)}/commands?limit=30`); $("commandRows").innerHTML = commands.slice().reverse().map((item) => `<div class="log-item"><strong>${escapeHtml(item.command)}</strong><div>value: ${escapeHtml(item.value ?? "-")}</div><div class="meta">${new Date(item.created_at).toLocaleString()}</div></div>`).join("") || `<div class="muted">?깅줉??紐낅졊???놁뒿?덈떎.</div>`; }

async function refreshBoard() {
  if (state.view !== "board") return; const url = state.boardCategory === "?꾩껜" ? "/api/board" : `/api/board?category=${encodeURIComponent(state.boardCategory)}`; const posts = await api(url); state.boardPosts = posts;
  $("posts").innerHTML = posts.map((post) => `<article class="post post-card compact" data-post-id="${post.id}" tabindex="0"><div class="post-title">${escapeHtml(post.title)}</div><div class="meta">${escapeHtml(post.category)} 쨌 ${escapeHtml(post.author)} 쨌 ${new Date(post.created_at).toLocaleDateString()}</div></article>`).join("") || `<div class="muted">寃뚯떆湲???놁뒿?덈떎.</div>`;
  document.querySelectorAll(".post-card").forEach((card) => { card.addEventListener("click", () => openPostDetail(Number(card.dataset.postId))); card.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openPostDetail(Number(card.dataset.postId)); } }); });
}
function canEdit(post) { return isAdmin() || post.author_username === state.user?.username || post.author === state.user?.display_name; }
function openPostEditor(post = null) { $("postEditor").classList.remove("hidden"); $("postDetail").classList.add("hidden"); $("boardList").classList.add("hidden"); $("postEditorTitle").textContent = post ? "게시글 수정" : "글쓰기"; $("editingPostId").value = post?.id || ""; $("postCategory").value = post?.category || (state.boardCategory === "자유게시판" ? "자유게시판" : "공지"); $("postTitle").value = post?.title || ""; $("postBody").value = post?.body || ""; }
function closePostEditor() { $("postEditor").classList.add("hidden"); $("boardList").classList.remove("hidden"); }
function closePostDetail() { $("postDetail").classList.add("hidden"); $("boardList").classList.remove("hidden"); }
function openPostDetail(postId) { const post = state.boardPosts.find((item) => item.id === postId); if (!post) return; state.selectedPost = post; $("boardList").classList.add("hidden"); $("postEditor").classList.add("hidden"); $("postDetail").classList.remove("hidden"); $("postDetailTitle").textContent = post.title; $("postDetailMeta").textContent = `${post.category} · ${post.author} · ${new Date(post.created_at).toLocaleString()}${post.updated_at ? " · 수정됨" : ""}`; $("postDetailBody").textContent = post.body; $("postEditButton").classList.toggle("hidden", !canEdit(post)); $("postDeleteButton").classList.toggle("hidden", !(isAdmin() || canEdit(post))); }
async function savePost() { const id = $("editingPostId").value; const title = $("postTitle").value.trim(); const body = $("postBody").value.trim(); const category = $("postCategory").value; if (!title || !body) return showToast("?쒕ぉ怨??댁슜???낅젰?섏꽭??"); const payload = { category, title, body, author: state.user?.display_name || "愿由ъ옄", author_username: state.user?.username || "admin" }; const url = id ? `/api/board/${id}` : "/api/board"; await api(url, { method: id ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); showToast(id ? "寃뚯떆湲???섏젙?덉뒿?덈떎." : "寃뚯떆湲???깅줉?덉뒿?덈떎."); closePostEditor(); await refreshBoard(); }
async function deletePost() { if (!state.selectedPost) return; await api(`/api/board/${state.selectedPost.id}`, { method: "DELETE" }); showToast("寃뚯떆湲????젣?덉뒿?덈떎."); closePostDetail(); await refreshBoard(); }

async function saveConfig() { const previous = state.latestSummary?.config || {}; const payload = { speaker_volume: Number($("speakerVolume").value), display_brightness: Number($("displayBrightness").value), display_text: previous.display_text || "OnPlant", drive_enabled: $("driveEnabled").value === "true", explore_seconds: Number($("exploreSeconds").value), lidar_speed: Number($("lidarSpeed").value), camera_enabled: true, camera_url: previous.camera_url || "" }; await api(`/api/robots/${encodeURIComponent(state.robotId)}/config`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); showToast("?ㅼ젙????ν뻽?듬땲??"); await refreshAll(); }
async function sendRemote(key) { const display = await api(`/api/robots/${encodeURIComponent(state.robotId)}/remote`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key }) }); renderCamera(display.camera_visible); showToast(key === "3" ? "?곹깭 由ы룷?몃? ?쒖떆?⑸땲??" : `由щえ而?${key}踰??낅젰`); await refreshCommands(); }

function openProfileModal() { const robot = state.latestSummary?.robot; state.profileAvatarData = robot?.plant_avatar || ""; $("profilePlantName").value = robot?.plant_name || ""; $("profileImage").value = ""; renderPlantAvatar(state.profileAvatarData); $("profileModal").classList.remove("hidden"); }
function closeProfileModal() { $("profileModal").classList.add("hidden"); }
async function saveProfile() {
  const next = $("profilePlantName").value.trim();
  if (!next) return showToast("식물 이름을 입력하세요.");
  try {
    await api(`/api/robots/${encodeURIComponent(state.robotId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plant_name: next, plant_avatar: state.profileAvatarData }),
    });
    closeProfileModal();
    showToast("프로필을 저장했습니다.");
    await refreshAll();
  } catch (error) {
    showToast(error.message || "프로필 저장에 실패했습니다.");
  }
}
function readProfileImage(file) {
  if (!file) return;
  if (!file.type.startsWith("image/")) return showToast("이미지 파일을 선택하세요.");
  const reader = new FileReader();
  reader.onerror = () => showToast("이미지를 읽지 못했습니다.");
  reader.onload = () => {
    const image = new Image();
    image.onerror = () => showToast("이미지를 불러오지 못했습니다.");
    image.onload = () => {
      const maxSize = 360;
      const ratio = Math.min(1, maxSize / Math.max(image.width, image.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(image.width * ratio));
      canvas.height = Math.max(1, Math.round(image.height * ratio));
      const context = canvas.getContext("2d");
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      state.profileAvatarData = canvas.toDataURL("image/jpeg", 0.82);
      renderPlantAvatar(state.profileAvatarData);
      showToast("사진을 첨부했습니다.");
    };
    image.src = String(reader.result);
  };
  reader.readAsDataURL(file);
}
async function clearHistory() { await api(`/api/robots/${encodeURIComponent(state.robotId)}/history`, { method: "DELETE" }); showToast("?쇱꽌 湲곕줉????젣?덉뒿?덈떎."); await refreshAll(); }

async function refreshAdmin() { if (!isAdmin() || state.view !== "admin") return; const users = await api("/api/admin/users"); $("adminUsers").innerHTML = users.map((user) => `<div class="log-item"><strong>${escapeHtml(user.username)} 쨌 ${escapeHtml(user.role)}</strong><div>${escapeHtml(user.display_name)} / ${escapeHtml(user.robot_id)}</div></div>`).join(""); }
async function linkRobot() { const payload = { username: $("linkUsername").value.trim(), link_code: $("linkCode").value.trim(), robot_id: $("linkRobotId").value.trim() }; await api("/api/admin/link-robot", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); showToast("濡쒕큸 ?곕룞??蹂寃쏀뻽?듬땲??"); await refreshAdmin(); }

async function refreshAll() { await refreshSummary(); await refreshLidar(); await refreshHistory(); await refreshMoveLogs(); await refreshCommands(); await refreshBoard(); await refreshAdmin(); }
function bindEvents() {
  $("loginTab").addEventListener("click", () => setLoginMode("login")); $("registerTab").addEventListener("click", () => setLoginMode("register")); $("loginSubmit").addEventListener("click", submitLogin); $("logoutButton").addEventListener("click", showLogin);
  document.querySelectorAll(".nav-item").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  document.querySelectorAll(".category").forEach((button) => button.addEventListener("click", async () => { state.boardCategory = button.dataset.category; document.querySelectorAll(".category").forEach((item) => item.classList.toggle("active", item === button)); closePostDetail(); closePostEditor(); await refreshBoard(); }));
  $("saveConfig").addEventListener("click", saveConfig); document.querySelectorAll("[data-remote]").forEach((button) => button.addEventListener("click", () => sendRemote(button.dataset.remote)));
  $("editPlantName").addEventListener("click", openProfileModal); $("profileCancel").addEventListener("click", closeProfileModal); $("profileSave").addEventListener("click", saveProfile); $("profileImage").addEventListener("change", (event) => readProfileImage(event.target.files?.[0])); $("profileImageClear").addEventListener("click", () => { state.profileAvatarData = ""; $("profileImage").value = ""; renderPlantAvatar(""); });
  $("newPostButton").addEventListener("click", () => openPostEditor()); $("postSubmit").addEventListener("click", savePost); $("postCancel").addEventListener("click", closePostEditor); $("postDetailClose").addEventListener("click", closePostDetail); $("postEditButton").addEventListener("click", () => openPostEditor(state.selectedPost)); $("postDeleteButton").addEventListener("click", deletePost);
  $("clearHistory").addEventListener("click", clearHistory); $("linkRobotButton").addEventListener("click", linkRobot);
}

bindEvents();
const savedUser = sessionStorage.getItem("onplant_user");
if (savedUser) { showApp(JSON.parse(savedUser)); refreshAll(); }
setInterval(refreshSummary, 3000); setInterval(refreshLidar, 700);


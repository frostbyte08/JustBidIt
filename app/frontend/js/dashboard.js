
const tagLists = { certList: [], docList: [] };
let projectList = [];

function addProject() {
  const name   = document.getElementById("projName").value.trim();
  const client = document.getElementById("projClient").value.trim();
  const value  = parseFloat(document.getElementById("projValue").value);
  const year   = parseInt(document.getElementById("projYear").value);

  if (!name || !client) { showToast("Project name and client are required", "error"); return; }

  projectList.push({ name, client, value: value || 0, year: year || new Date().getFullYear() });
  renderProjects();
}

function removeProject(index) {
  projectList.splice(index, 1);
  renderProjects();
}

function renderProjects() {
  const container = document.getElementById("projectsList");
  if (!container) return;
  if (projectList.length === 0) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = projectList.map((p, i) => `
    <div style="background:var(--ink-3);border:1px solid var(--border);border-radius:var(--radius);padding:12px 16px;display:flex;align-items:center;justify-content:space-between;gap:12px;">
      <div>
        <div style="font-weight:600;font-size:0.875rem;color:var(--text);">${p.name}</div>
        <div style="font-size:0.78rem;color:var(--text-3);font-family:var(--font-mono);">${p.client} &nbsp;·&nbsp; Rs.${p.value}L &nbsp;·&nbsp; ${p.year}</div>
      </div>
      <button class="btn btn-ghost btn-sm" style="color:var(--red);flex-shrink:0;" onclick="removeProject(${i})">Remove</button>
    </div>
  `).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  console.log("=== Dashboard Loading ===");
  if (!requireAuth()) {
    console.error("Not authenticated");
    return;
  }
  console.log("✓ Authenticated");
  loadState();
  console.log("✓ State loaded:", state);
  initUser();
  checkAPI();
  loadSavedCompanyForm();
  if (state.tenderId) restoreTenderBadge();
  tryLoadExistingCompliance();
  loadHistory();
  console.log("=== Dashboard Ready ===");
});

function initUser() {
  const u = state.user;
  if (!u) return;
  const initials = (u.full_name || u.email || "?").charAt(0).toUpperCase();
  const name = u.full_name || u.email || "User";
  document.getElementById("sidebarAvatar").textContent = initials;
  document.getElementById("sidebarName").textContent = name;
  document.getElementById("topbarAvatar").textContent = initials;
  document.getElementById("topbarName").textContent = name.split(" ")[0];
}

async function checkAPI() {
  const pill = document.getElementById("apiPill");
  const text = document.getElementById("apiPillText");
  const ok = await healthCheck();
  pill.className = `api-pill ${ok ? "online" : "offline"}`;
  text.textContent = ok ? "API Online" : "API Offline";
}

function showPage(name) {
  console.log("Showing page:", name);
  ["analyze","company","history"].forEach(p => {
    document.getElementById(`page-${p}`).style.display = p === name ? "flex" : "none";
  });
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  const labels = { analyze: "Analyze Tender", company: "Company Profile", history: "Tender History" };
  const breadcrumbs = { analyze: "Analyze", company: "Company", history: "History" };
  document.getElementById("topbarTitle").textContent = labels[name];
  document.getElementById("breadcrumbCurrent").textContent = breadcrumbs[name];
  document.querySelectorAll(".nav-item").forEach(el => {
    if (el.textContent.toLowerCase().includes(name === "analyze" ? "analyze" : name)) {
      el.classList.add("active");
    }
  });
  if (name === "history") {
    console.log("Loading history...");
    loadHistory();
  }
}

function toggleProfileMenu() {
  const dd = document.getElementById("profileDropdown");
  dd.style.display = dd.style.display === "block" ? "none" : "block";
}
document.addEventListener("click", e => {
  if (!e.target.closest(".profile-menu")) {
    const dd = document.getElementById("profileDropdown");
    if (dd) dd.style.display = "none";
  }
});

function onDragOver(e) {
  e.preventDefault();
  document.getElementById("uploadZone").classList.add("drag-over");
}
function onDrop(e) {
  e.preventDefault();
  document.getElementById("uploadZone").classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file?.type === "application/pdf") processUpload(file);
  else showToast("Please provide a PDF file", "error");
}
function onFileSelect(e) {
  if (e.target.files[0]) processUpload(e.target.files[0]);
}

async function processUpload(file) {
  const zone = document.getElementById("uploadZone");
  zone.innerHTML = `<div class="spinner" style="margin-bottom:14px;"></div>
    <h3>Extracting tender data...</h3>
    <p style="color:var(--text-2);font-size:0.84rem;">AI is reading the PDF — 10–20 seconds</p>`;

  try {
    const data = await uploadTender(file);
    const info = data.extracted_data || {};
    const elig = info.eligibility || {};

    document.getElementById("tenderLoadedBadge").style.display = "inline-block";
    document.getElementById("tenderSummaryContent").innerHTML = buildInfoTable([
      ["Title",          info.title || data.title || "—"],
      ["Authority",      info.issuing_authority || "—"],
      ["Deadline",       info.deadline || "—"],
      ["Sector",         info.sector || "—"],
      ["Min Turnover",   elig.min_turnover ? `Rs. ${elig.min_turnover}L` : "Not specified"],
      ["Min Experience", elig.years_experience ? `${elig.years_experience} years` : "Not specified"],
      ["MSME Preference",elig.msme_preference ? "Yes" : "No"],
      ["Bid Security",   elig.bid_security || "—"],
    ]);
    document.getElementById("tenderSummary").style.display = "block";
    zone.innerHTML = `
      <input type="file" id="fileInput" hidden accept=".pdf" onchange="onFileSelect(event)">
      <div class="upload-zone-icon" style="border-color:var(--border-green);color:var(--green);">PDF</div>
      <h3 style="color:var(--green);">${file.name}</h3>
      <p>Extracted successfully — ready for compliance check</p>
      <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();document.getElementById('fileInput').click()">
        Upload Different Tender
      </button>`;

    showToast("Tender extracted successfully", "success");

  } catch (err) {
    zone.innerHTML = `
      <input type="file" id="fileInput" hidden accept=".pdf" onchange="onFileSelect(event)">
      <div class="upload-zone-icon">ERR</div>
      <h3 style="color:var(--red);">Extraction Failed</h3>
      <p style="color:var(--text-2);font-size:0.84rem;">${err.message}</p>
      <button class="btn btn-primary" onclick="document.getElementById('fileInput').click()">Try Again</button>`;
    showToast(err.message, "error");
  }
}

function restoreTenderBadge() {
  document.getElementById("tenderLoadedBadge").style.display = "inline-block";
}

async function runCompliance() {
  loadState();
  console.log("Running compliance check with tenderId:", state.tenderId, "companyId:", state.companyId);
  
  if (!state.tenderId)  { showToast("Upload a tender PDF first", "error"); return; }
  if (!state.companyId) { showToast("Save your company profile first", "error"); showPage("company"); return; }

  const btn = document.getElementById("complianceBtn");
  btn.disabled = true; btn.textContent = "Analyzing...";
  document.getElementById("complianceBody").innerHTML =
    `<div style="display:flex;align-items:center;justify-content:center;gap:14px;padding:48px;">
      <div class="spinner"></div>
      <span style="color:var(--text-2);font-size:0.875rem;">Running compliance engine...</span>
    </div>`;

  try {
    console.log("Calling checkCompliance API...");
    const d = await checkCompliance(state.tenderId, state.companyId);
    console.log("Compliance data received:", d);
    
    if (!d) {
      throw new Error("No data received from compliance check");
    }
    
    renderCompliance(d);
    showToast("Compliance check complete", "success");
  } catch (err) {
    console.error("Compliance check error:", err);
    const fallback = await fetchLatestComplianceReport();
    if (fallback) {
      renderCompliance(fallback);
      showToast("Loaded previous compliance report", "success");
      btn.disabled = false; btn.textContent = "Run Check";
      return;
    }
    document.getElementById("complianceBody").innerHTML =
      `<div class="empty-state"><h4 style="color:var(--red);">Check Failed</h4><p>${err.message || "Unknown error"}</p><p style="font-size:0.75rem;color:var(--text-3);">Check browser console for details</p></div>`;
    showToast(err.message, "error");
  }
  btn.disabled = false; btn.textContent = "Run Check";
}

async function fetchLatestComplianceReport() {
  try {
    loadState();
    if (!state.tenderId || !state.companyId) return null;
    const list = await apiCall(
      `/compliance/reports?tender_id=${Number(state.tenderId)}&company_id=${Number(state.companyId)}&limit=1`
    );
    if (Array.isArray(list) && list.length > 0) return list[0];
    return null;
  } catch {
    return null;
  }
}

async function tryLoadExistingCompliance() {
  const report = await fetchLatestComplianceReport();
  if (report) {
    renderCompliance(report);
  }
}

function renderCompliance(d) {
  const verdictClass = getVerdictClass(d.verdict);
  const body = document.getElementById("complianceBody");

  body.innerHTML = `
    <div style="display:grid;grid-template-columns:200px 1fr 1fr;gap:20px;margin-bottom:20px;">

      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;background:var(--ink-3);border:1px solid var(--border);border-radius:var(--radius-2);padding:24px;">
        <div class="score-ring">
          <svg width="130" height="130" viewBox="0 0 130 130">
            <circle class="score-track" cx="65" cy="65" r="50"/>
            <circle class="score-fill" id="scoreFill" cx="65" cy="65" r="50"/>
          </svg>
          <div class="score-center">
            <span class="score-num" id="scoreNum">0</span>
            <span class="score-denom">/100</span>
          </div>
        </div>
        <div class="verdict-badge ${verdictClass}">${d.verdict || "—"}</div>
        <button class="btn btn-primary btn-sm btn-full" onclick="window.location.href='proposal.html'">
          Generate Draft
        </button>
      </div>

      <div style="background:var(--ink-3);border:1px solid var(--border);border-radius:var(--radius-2);padding:20px;">
        <div style="font-family:var(--font-mono);font-size:0.68rem;letter-spacing:0.1em;color:var(--text-3);margin-bottom:14px;">REPORT DETAILS</div>
        <div class="info-table">
          ${buildInfoTableRows([
            ["Report ID",  `#${d.id}`],
            ["Tender ID",  `#${d.tender_id}`],
            ["Company ID", `#${d.company_id}`],
            ["Score",      `${d.score}/100`],
          ])}
        </div>
      </div>

      <div style="background:var(--ink-3);border:1px solid var(--border);border-radius:var(--radius-2);padding:20px;overflow-y:auto;max-height:260px;">
        <div style="font-family:var(--font-mono);font-size:0.68rem;letter-spacing:0.1em;color:var(--text-3);margin-bottom:14px;">RECOMMENDATIONS</div>
        ${(d.recommendations || []).length
          ? d.recommendations.map(r => `<div class="rec-item">${r}</div>`).join("")
          : `<p style="font-size:0.84rem;color:var(--text-3);">No recommendations.</p>`}
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px;">
      <div style="background:var(--ink-3);border:1px solid var(--border);border-radius:var(--radius-2);padding:20px;">
        <div style="font-family:var(--font-mono);font-size:0.68rem;letter-spacing:0.1em;color:var(--text-3);margin-bottom:14px;">GAPS IDENTIFIED (${(d.gaps||[]).length})</div>
        ${(d.gaps||[]).length
          ? d.gaps.map(g => {
              const severity = String(g?.severity || "MINOR");
              const cls = severity.toLowerCase().replace(/\s+/g, "-").split("-")[0];
              return `<div class="gap-item sev-${cls}" style="margin-bottom:8px;">
                <span class="gap-sev sev-${cls}">${severity}</span>
                <div class="gap-field">${g.field}</div>
                ${g.note ? `<div class="gap-note">${g.note}</div>` : ""}
              </div>`;
            }).join("")
          : `<div style="color:var(--green);font-size:0.875rem;">No gaps found — fully eligible.</div>`}
      </div>

      <div style="background:var(--ink-3);border:1px solid var(--border);border-radius:var(--radius-2);padding:20px;">
        <div style="font-family:var(--font-mono);font-size:0.68rem;letter-spacing:0.1em;color:var(--text-3);margin-bottom:14px;">AI STRATEGIC ANALYSIS</div>
        <div style="font-size:0.84rem;color:var(--text-2);line-height:1.8;white-space:pre-wrap;">${d.ai_analysis || "No analysis available."}</div>
      </div>
    </div>
  `;

  animateScore(Number.isFinite(Number(d?.score)) ? Number(d.score) : 0);
}

function animateScore(target) {
  const fill = document.getElementById("scoreFill");
  const num  = document.getElementById("scoreNum");
  const r = 50, circ = 2 * Math.PI * r;
  fill.style.strokeDasharray  = circ;
  fill.style.strokeDashoffset = circ;

  if (!Number.isFinite(target) || target <= 0) {
    num.textContent = "0";
    return;
  }

  if (target >= 70) fill.style.stroke = "var(--green)";
  else if (target >= 50) fill.style.stroke = "var(--gold)";
  else fill.style.stroke = "var(--red)";

  setTimeout(() => {
    fill.style.strokeDashoffset = circ - (target / 100) * circ;
  }, 80);

  let n = 0;
  const iv = setInterval(() => {
    n = Math.min(n + 1, target);
    num.textContent = n;
    if (n >= target) clearInterval(iv);
  }, 800 / target);
}

function getVerdictClass(v = "") {
  const u = v.toUpperCase();
  if (u.includes("INELIGIBLE")) return "verdict-ineligible";
  if (u.includes("LIKELY") || u.includes("CONDITIONALLY") || u.includes("BORDERLINE")) return "verdict-likely";
  return "verdict-eligible";
}

async function doSaveCompany() {
  const name     = document.getElementById("companyName").value.trim();
  const turnover = parseFloat(document.getElementById("annualTurnover").value);
  const years    = parseInt(document.getElementById("yearsOp").value);

  if (!name || !turnover || !years) {
    showToast("Company name, turnover and years are required", "error"); return;
  }

  const pastProjects = [...projectList];

  try {
    const data = await saveCompany({
      name,
      annual_turnover:     turnover,
      years_in_operation:  years,
      net_worth:           parseFloat(document.getElementById("netWorth").value) || null,
      gst_number:          document.getElementById("gstNum").value || null,
      pan_number:          document.getElementById("panNum").value || null,
      registration_number: document.getElementById("regNum").value || null,
      msme_category:       document.getElementById("msmeCategory").value || null,
      certifications:      tagLists.certList,
      available_documents: tagLists.docList,
      past_projects:       pastProjects,
      sectors:             [],
    });

    localStorage.setItem("jbi_company_form", JSON.stringify({
      name, turnover, years,
      netWorth:  document.getElementById("netWorth").value,
      gst:       document.getElementById("gstNum").value,
      pan:       document.getElementById("panNum").value,
      reg:       document.getElementById("regNum").value,
      udyam:     document.getElementById("udyamNum").value,
      msme:      document.getElementById("msmeCategory").value,
      certs:     tagLists.certList,
      docs:      tagLists.docList,
      projects:  JSON.stringify(projectList),
    }));

    document.getElementById("companySavedBadge").style.display = "inline-block";
    showToast(`Profile saved — Company ID: ${data.id}`, "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function loadSavedCompanyForm() {
  const raw = localStorage.getItem("jbi_company_form");
  if (!raw) return;
  try {
    const f = JSON.parse(raw);
    document.getElementById("companyName").value    = f.name || "";
    document.getElementById("annualTurnover").value = f.turnover || "";
    document.getElementById("yearsOp").value        = f.years || "";
    document.getElementById("netWorth").value       = f.netWorth || "";
    document.getElementById("gstNum").value         = f.gst || "";
    document.getElementById("panNum").value         = f.pan || "";
    document.getElementById("regNum").value         = f.reg || "";
    document.getElementById("udyamNum").value       = f.udyam || "";
    document.getElementById("msmeCategory").value   = f.msme || "";
    try { if (f.projects) { projectList = JSON.parse(f.projects); renderProjects(); } } catch {}
    if (f.certs) { tagLists.certList = [...f.certs]; renderTagList("certList","certInput","certWrap"); }
    if (f.docs)  { tagLists.docList  = [...f.docs];  renderTagList("docList","docInput","docWrap");   }
    if (state.companyId) document.getElementById("companySavedBadge").style.display = "inline-block";
  } catch {}
}

function clearUserData() {
  ["jbi_company_form"].forEach(k => localStorage.removeItem(k));
  showToast("Local data cleared", "success");
  location.reload();
}

function addTag(event, inputId, listKey, wrapId) {
  if (event.key !== "Enter") return;
  event.preventDefault();
  const val = event.target.value.trim();
  if (!val || tagLists[listKey].includes(val)) { event.target.value = ""; return; }
  tagLists[listKey].push(val);
  event.target.value = "";
  renderTagList(listKey, inputId, wrapId);
}

function renderTagList(listKey, inputId, wrapId) {
  const wrap  = document.getElementById(wrapId);
  const input = document.getElementById(inputId);
  wrap.querySelectorAll(".tag").forEach(t => t.remove());
  tagLists[listKey].forEach((val, i) => {
    const tag = document.createElement("div");
    tag.className = "tag";
    tag.innerHTML = `${val}<button class="tag-remove" onclick="removeTag('${listKey}','${inputId}','${wrapId}',${i})">×</button>`;
    wrap.insertBefore(tag, input);
  });
}

function removeTag(listKey, inputId, wrapId, idx) {
  tagLists[listKey].splice(idx, 1);
  renderTagList(listKey, inputId, wrapId);
}

async function loadHistory() {
  const body = document.getElementById("historyBody");
  body.innerHTML = `<div style="padding:40px;text-align:center;"><div class="spinner" style="margin:0 auto;"></div><p>Loading tenders...</p></div>`;
  try {
    console.log("Loading history...");
    const list = await listTenders();
    console.log("Tenders received:", list, "Type:", typeof list, "Is Array:", Array.isArray(list), "Length:", list?.length);
    if (!Array.isArray(list)) {
      console.error("Expected array, got:", typeof list);
      body.innerHTML = `<div class="empty-state"><h4 style="color:var(--red);">Error: Invalid data</h4></div>`;
      return;
    }
    if (list.length === 0) {
      body.innerHTML = `<div class="empty-state"><h4>No tenders yet</h4><p>Upload your first tender from the Analyze tab.</p></div>`;
      return;
    }
    console.log("Rendering", list.length, "tenders");
    body.innerHTML = list.map(t => `
      <div class="history-item" onclick="selectTender(${t.id})">
        <div>
          <div class="history-item-title">${t.title || "Untitled Tender"}</div>
          <div class="history-item-sub">${t.issuing_authority || "Unknown authority"} &nbsp;·&nbsp; Deadline: ${t.deadline || "—"} &nbsp;·&nbsp; ID #${t.id}</div>
        </div>
        <span class="status-pill ${t.status === "extracted" ? "extracted" : "failed"}">${t.status}</span>
      </div>
    `).join("");
  } catch (err) {
    console.error("Error loading history:", err);
    body.innerHTML = `<div class="empty-state"><h4 style="color:var(--red);">Error loading tenders</h4><p>${err?.message || "Unknown error"}</p><p style="font-size:0.75rem;color:var(--text-3);">Check browser console for details</p></div>`;
  }
}

function selectTender(id) {
  state.tenderId = String(id);
  saveState();
  showPage("analyze");
  restoreTenderBadge();
  showToast(`Tender #${id} selected`, "success");
}

function buildInfoTable(rows) {
  return `<div class="info-table">${buildInfoTableRows(rows)}</div>`;
}

function buildInfoTableRows(rows) {
  return rows.map(([label, value]) =>
    `<div class="info-row">
      <span class="info-label">${label}</span>
      <span class="info-value">${value}</span>
    </div>`
  ).join("");
}

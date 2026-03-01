document.addEventListener("DOMContentLoaded", () => {
  if (!requireAuth()) return;
  loadState();
  fetchTenderMeta();
});

async function fetchTenderMeta() {
  if (!state.tenderId) {
    document.getElementById("proposalTitle").textContent = "No tender selected";
    document.getElementById("proposalMeta").textContent  = "Go back to Dashboard and upload a tender first.";
    return;
  }
  try {
    const data = await getTender(state.tenderId);
    const info = data.extracted_data || {};
    document.getElementById("proposalTitle").textContent =
      info.title || data.title || `Tender #${state.tenderId}`;
    document.getElementById("proposalMeta").textContent =
      [info.issuing_authority, info.deadline ? `Deadline: ${info.deadline}` : ""].filter(Boolean).join("  ·  ");
  } catch {}
}

async function doGenerateDraft() {
  loadState();
  if (!state.tenderId)  { showToast("No tender loaded — go back to Dashboard", "error"); return; }
  if (!state.companyId) { showToast("No company profile — save it from Dashboard", "error"); return; }

  const card = document.getElementById("generateCard");
  card.innerHTML = `
    <div class="card-body" style="text-align:center; padding:56px 40px;">
      <div class="spinner" style="margin:0 auto 16px;"></div>
      <h3 style="font-size:1rem;color:#fff;margin-bottom:6px;font-family:var(--font-display);">Writing your proposal...</h3>
      <p style="color:var(--text-2);font-size:0.84rem;">Gemini is composing all 9 sections - please wait</p>
    </div>`;

  try {
    const data = await generateDraft(state.tenderId, state.companyId);
    const text = data.draft_text || data.draft || "No draft returned.";

    card.style.display = "none";
    document.getElementById("draftCard").style.display = "block";
    document.getElementById("draftContent").textContent = text;

    showToast("Bid proposal ready", "success");
  } catch (err) {
    card.innerHTML = `
      <div class="card-body" style="text-align:center; padding:56px 40px;">
        <div style="font-family:var(--font-mono);font-size:0.7rem;color:var(--red);margin-bottom:12px;">GENERATION FAILED</div>
        <p style="color:var(--text-2);font-size:0.875rem;margin-bottom:24px;">${err.message}</p>
        <button class="btn btn-primary" onclick="doGenerateDraft()">Try Again</button>
      </div>`;
    showToast(err.message, "error");
  }
}

async function doAskCopilot() {
  loadState();
  const input = document.getElementById("chatInput");
  const msgs  = document.getElementById("chatMessages");
  const q = input.value.trim();
  if (!q) return;

  if (!state.tenderId) { showToast("No tender loaded", "error"); return; }

  appendMsg(msgs, q, "user");
  input.value = "";

  const typing = document.createElement("div");
  typing.className = "chat-msg ai";
  typing.id = "typing";
  typing.innerHTML = `<span style="opacity:0.5;font-family:var(--font-mono);font-size:0.75rem;">thinking...</span>`;
  msgs.appendChild(typing);
  msgs.scrollTop = msgs.scrollHeight;

  try {
    const data = await askCopilot(
      state.tenderId, q,
      state.sessionId || null
    );
    document.getElementById("typing")?.remove();
    appendMsg(msgs, data.answer, "ai");
  } catch (err) {
    document.getElementById("typing")?.remove();
    appendMsg(msgs, `Error: ${err.message}`, "ai");
  }
  msgs.scrollTop = msgs.scrollHeight;
}

function appendMsg(container, text, type) {
  const div = document.createElement("div");
  div.className = `chat-msg ${type}`;
  div.textContent = text;
  container.appendChild(div);
}

function copyDraft() {
  const text = document.getElementById("draftContent")?.textContent;
  if (!text) { showToast("No draft to copy yet", "error"); return; }
  navigator.clipboard.writeText(text).then(() => showToast("Copied to clipboard", "success"));
}

function downloadDraft() {
  const text = document.getElementById("draftContent")?.textContent;
  if (!text) { showToast("No draft to download yet", "error"); return; }
  const blob = new Blob([text], { type: "text/plain" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `bid-proposal-tender-${state.tenderId}.txt`;
  a.click();
  URL.revokeObjectURL(url);
  showToast("Downloaded", "success");
}

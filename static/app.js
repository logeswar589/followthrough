const $ = (s, root = document) => root.querySelector(s);
const escapeHtml = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let items = [],
  current = null,
  tab = "transcript",
  busy = false,
  editing = null,
  recorder,
  stream,
  chunks = [],
  timerInterval,
  recordStart,
  toastTimer;
const example =
  "Meet tomorrow at six… actually seven, in the library. Remind me half an hour before. Bring the prototype. We need an HDMI adapter under eight hundred rupees. Actually wait until we confirm the laptop port. Maybe ask Rahul to join and send him a recap.";
let dirty = false;
document.addEventListener("input", (event) => {
  if (event.target.closest("#panel")) dirty = true;
});
document.addEventListener("change", (event) => {
  if (event.target.closest("#panel")) dirty = true;
});
function leaveDraft() {
  if (!dirty) return true;
  if (!confirm("You have unsaved edits. Discard them and continue?"))
    return false;
  dirty = false;
  return true;
}
function toast(message, error = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = "visible" + (error ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.className = ""), error ? 13000 : 6500);
}
async function api(path, options = {}) {
  const res = await fetch("/api" + path, {
    ...options,
    headers:
      options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    let data;
    try {
      data = await res.json();
    } catch {}
    throw Error(
      typeof data?.detail === "string"
        ? data.detail
        : "Please check the entered fields and try again.",
    );
  }
  return res.json();
}
async function perform(fn) {
  if (busy) return;
  if (recorder?.state === "recording") {
    toast("Stop the recording before switching tasks.");
    return;
  }
  busy = true;
  document.body.classList.add("busy");
  try {
    await fn();
  } catch (e) {
    toast(e.message || "Something went wrong. Please retry.", true);
  } finally {
    busy = false;
    document.body.classList.remove("busy");
    document.querySelectorAll("[data-busy]").forEach((el) => {
      el.disabled = false;
    });
  }
}
function fmtDate(value, zone = "Asia/Kolkata") {
  return new Date(value).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: zone,
  });
}
function stamp(sec) {
  return `${Math.floor(sec / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor(sec % 60)
    .toString()
    .padStart(2, "0")}`;
}
function localInput(iso) {
  const d = new Date(iso);
  return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
async function refresh() {
  items = await api("/conversations");
  renderList();
  renderTasks();
}
function renderList() {
  $("#count").textContent = items
    .filter((c) => !["sample", "synthetic"].includes(c.source))
    .reduce(
      (sum, c) =>
        sum +
        c.actions.filter(
          (a) =>
            a.type !== "decision" &&
            !["completed", "dismissed"].includes(a.status),
        ).length,
      0,
    );
  $("#list-count").textContent = items.length;
  const query = $("#search").value.toLowerCase();
  const visible = items.filter((item) =>
    `${item.title} ${item.transcript} ${item.recap}`
      .toLowerCase()
      .includes(query),
  );
  $("#conversations").innerHTML =
    visible
      .map((item) => {
        const pending = item.actions.filter(
          (a) => !["completed", "dismissed"].includes(a.status),
        ).length;
        return `<div class="history-entry-row"><button class="conversation ${current?.id === item.id ? "selected" : ""}" data-id="${item.id}"><div class="date"><span>${escapeHtml(fmtDate(item.recorded_at, item.timezone))}</span><span>${item.audio ? "≋ AUDIO" : "≡ TEXT"}</span></div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.recap || item.transcript || "Your recording is saved. Ready when you are.")}</p><span class="pill ${item.actions.some((a) => a.status === "needs clarification") ? "blocked" : ""}">${pending ? pending + " next steps" : item.actions.length ? "All caught up" : "Ready to understand"}</span></button><button class="history-delete" data-delete-conversation="${item.id}" aria-label="Delete conversation: ${escapeHtml(item.title)}" title="Delete conversation"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18M9 6V4h6v2M5 6l1 14h12l1-14M10 10v6M14 10v6"/></svg></button></div>`;
      })
      .join("") ||
    '<div class="list-empty">No conversations yet.<br>Make a little room in your head.</div>';
  document.querySelectorAll(".conversation").forEach(
    (button) =>
      (button.onclick = () =>
        perform(async () => {
          if (!leaveDraft()) return;
          current = await api("/conversations/" + button.dataset.id);
          tab = current.actions.length ? "actions" : "transcript";
          renderDetail();
          renderList();
          $("#detail").scrollIntoView({ behavior: "smooth", block: "start" });
        })),
  );
}
document.querySelector("#conversations").addEventListener("click", (event) => {
  const button = event.target.closest("[data-delete-conversation]");
  if (!button) return;
  perform(async () => {
    if (!leaveDraft()) return;
    const id = button.dataset.deleteConversation;
    const item = items.find((c) => c.id === id);
    if (
      !item ||
      !confirm(
        `Delete “${item.title}” from history?\nThis permanently deletes its recording, transcript, recap, tasks and previous analyses. This cannot be undone.`,
      )
    )
      return;
    await api(`/conversations/${id}`, { method: "DELETE" });
    if (current?.id === id) {
      current = null;
      dirty = false;
      $("#detail").hidden = true;
    }
    await refresh();
    await pollNotifications();
    toast("Conversation deleted from history.");
  });
});
async function adopt(item) {
  current = item;
  dirty = false;
  renderDetail();
  await refresh();
}
async function create(text = "", source = "live", scrollTarget = "#detail") {
  current = await api("/conversations", {
    method: "POST",
    body: JSON.stringify({
      source,
      transcript: text,
      recorded_at: new Date().toISOString(),
      timezone:
        Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Kolkata",
      style: "casual",
    }),
  });
  tab = "transcript";
  await adopt(current);
  $(scrollTarget).scrollIntoView({ behavior: "smooth", block: "start" });
}
function field(name, label, value, type = "text") {
  return `<label class="field"><span>${label}</span><input name="${name}" type="${type}" value="${escapeHtml(value)}" ${type === "number" ? 'min="0"' : ""}></label>`;
}
function renderDetail() {
  if (!current) return;
  $("#detail").hidden = false;
  const item = current;
  const sourceLabel =
    item.source === "sample"
      ? "SAMPLE TRANSCRIPT"
      : item.source === "synthetic"
        ? "SYNTHETIC DEMO AUDIO"
        : "";
  $("#detail").innerHTML =
    `<div class="detail-head"><span class="eyebrow">${item.audio ? "VOICE → CLARITY" : "THOUGHT → ACTION"}</span><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(fmtDate(item.recorded_at, item.timezone))} · ${escapeHtml(item.timezone)} ${item.model ? "· " + escapeHtml(item.model) : ""}</p></div><nav class="tabs"><button class="tab ${tab === "transcript" ? "active" : ""}" data-tab="transcript">01 &nbsp; Transcript</button><button class="tab ${tab === "actions" ? "active" : ""}" data-tab="actions">02 &nbsp; Actions <span>${item.actions.length || ""}</span></button><button class="tab ${tab === "recap" ? "active" : ""}" data-tab="recap">03 &nbsp; Recap</button></nav><div class="detail-body"><div id="stage" class="stage" hidden></div>${item.audio ? `<audio id="audioPlayer" class="audio" controls src="/api/conversations/${item.id}/audio"></audio>` : ""}<div id="panel"></div></div>`;
  if (sourceLabel) {
    const label = document.createElement("p");
    label.className = "hint";
    label.textContent = sourceLabel;
    $(".detail-head").append(label);
  }
  document.querySelectorAll(".tab").forEach(
    (button) =>
      (button.onclick = () => {
        if (busy || !leaveDraft()) return;
        tab = button.dataset.tab;
        renderDetail();
      }),
  );
  if (tab === "transcript") renderTranscript();
  else if (tab === "actions") renderActions();
  else renderRecap();
  renderLanguageReview();
  if (item.analysis_history?.length) {
    const history = document.createElement("details");
    history.className = "analysis-history";
    history.innerHTML =
      "<summary>Previous analyses (" +
      item.analysis_history.length +
      ")</summary>" +
      item.analysis_history
        .map(
          (entry) =>
            `<div class="history-entry"><p class="hint">${escapeHtml(new Date(entry.saved_at).toLocaleString())} · ${escapeHtml(entry.model || "Edited draft")}</p><p>${escapeHtml(entry.recap)}</p><ul>${entry.actions.map((action) => `<li>${escapeHtml(action.title)} — ${escapeHtml(action.status)}</li>`).join("")}</ul></div>`,
        )
        .reverse()
        .join("");
    $(".detail-body").append(history);
  }
}
function languageName(code) {
  try {
    return new Intl.DisplayNames(["en"], { type: "language" }).of(code);
  } catch {
    return code;
  }
}
function renderLanguageReview() {
  const box = document.createElement("section");
  box.className = "language-review";
  const languages = current.detected_languages?.length
    ? current.detected_languages.map(languageName).join(" + ")
    : current.language
      ? languageName(current.language) + " (primary audio language)"
      : "Auto-detect on understanding";
  const issues = current.language_issues || [];
  const warnings = current.speech_warnings || [];
  const edited =
    current.raw_transcript && current.raw_transcript !== current.transcript;
  box.innerHTML = `<p class="hint"><strong>Languages: ${escapeHtml(languages)}</strong>${current.speech_model ? " · " + escapeHtml(current.speech_model) : ""}<br>Recap: ${escapeHtml(current.output_language || "original")} · Original speech is transcribed, not automatically translated.</p>`;
  if (current.recap_warnings?.length) {
    box.innerHTML += `<div class="questions"><strong>Recap needs a check</strong><ul>${current.recap_warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}</ul><p>These are automated checks, not proof of an error. Review the recap against your transcript.</p></div>`;
  }
  if (warnings.length || issues.length) {
    box.innerHTML += `<details ${issues.length ? "open" : ""}><summary>Check wording · ${warnings.length} audio flags, ${issues.length} meaning flags</summary><p class="hint">These are possible issues, not verified corrections. Replay the audio or edit the transcript before using affected actions.${edited ? " Audio flags refer to the original transcript; your edits are retained." : ""}</p>${warnings.map((w) => `<div class="wording-issue"><button class="text-button" data-replay="${Number(w.start)}">▶ Replay ${stamp(w.start)}</button><blockquote>${escapeHtml(w.quote)}</blockquote><p>${escapeHtml(w.reason)}</p>${w.words?.length ? `<p class="hint">Less certain words: ${escapeHtml(w.words.join(", "))}</p>` : ""}</div>`).join("")}${issues.map((i) => `<div class="wording-issue"><blockquote>${escapeHtml(i.quote)}</blockquote><p>${escapeHtml(i.reason)}</p>${i.suggestion ? `<p><strong>Possible wording:</strong> ${escapeHtml(i.suggestion)}</p>` : ""}</div>`).join("")}</details>`;
  } else if (current.language_issues) {
    box.innerHTML +=
      '<p class="hint">No specific wording issue flagged. This is not a guarantee of transcription or translation accuracy.</p>';
  }
  if (current.raw_transcript)
    box.innerHTML += `<details><summary>Original machine transcript</summary><p class="original-transcript">${escapeHtml(current.raw_transcript)}</p></details>`;
  $("#panel").before(box);
  box.querySelectorAll("[data-replay]").forEach(
    (button) =>
      (button.onclick = () => {
        const audio = $("#audioPlayer");
        if (audio) {
          audio.currentTime = Number(button.dataset.replay);
          audio.play().catch(() => {});
        }
      }),
  );
}
function progress(text) {
  const el = $("#stage");
  if (el) {
    el.hidden = !text;
    el.textContent = text;
  }
  document
    .querySelectorAll("[data-busy]")
    .forEach((el) => (el.disabled = !!text));
  document
    .querySelectorAll("#panel input, #panel textarea, #panel select")
    .forEach((el) => (el.disabled = !!text));
  $("#detail").setAttribute("aria-busy", String(!!text));
}
function renderTranscript() {
  $("#panel").innerHTML =
    `<div class="field-grid">${field("recorded_at", "When was this recorded? (your browser’s local time)", localInput(current.recorded_at), "datetime-local")}${field("timezone", "Recording timezone (IANA name)", current.timezone)}</div><p class="hint">For uploaded recordings, confirm the original date. “Tomorrow” is resolved from this date. Editing the transcript or context clears existing action proposals on save.</p><label class="field"><span>Review the transcript</span><textarea id="transcript" rows="8" placeholder="Speak freely. Or type a thought here…">${escapeHtml(current.transcript)}</textarea></label><label class="field"><span>Recap style</span><select id="style"><option value="casual">Keep my style</option><option value="concise">Make it concise</option><option value="professional">Make it professional</option></select></label><label class="field"><span>Recap language</span><select id="outputLanguage"><option value="original">Auto · keep my language mix</option><option>English</option><option>Tamil</option><option>Hindi</option><option>Telugu</option><option>Kannada</option><option>Malayalam</option><option>Spanish</option><option>French</option><option>German</option></select></label><div class="toolbar"><button class="primary" id="understand" data-busy>Understand with Gemma ↗</button><button class="secondary" id="saveTranscript" data-busy>Save transcript</button>${current.audio ? '<button class="text-button" id="transcribe" data-busy>Transcribe audio</button>' : ""}</div><p class="hint">You review every action. Nothing is sent, purchased or added to a calendar automatically.</p>${current.segments.length ? '<details><summary class="hint">Original audio segments · tap to play</summary>' + current.segments.map((s) => `<button class="segment" data-start="${s.start}"><span>${stamp(s.start)}</span>${escapeHtml(s.text)}</button>`).join("") + "</details>" : ""}`;
  $("#style").value = current.style;
  $("#outputLanguage").value = current.output_language || "original";
  const saveTranscript = async () => {
    const value = $('[name="recorded_at"]').value;
    if (!value) throw Error("Confirm the recording date first.");
    return api(`/conversations/${current.id}/transcript`, {
      method: "PUT",
      body: JSON.stringify({
        transcript: $("#transcript").value,
        recorded_at: new Date(value).toISOString(),
        timezone: $('[name="timezone"]').value,
        style: $("#style").value,
        output_language: $("#outputLanguage").value,
      }),
    });
  };
  $("#saveTranscript").onclick = () =>
    perform(async () => {
      await adopt(await saveTranscript());
      toast("Transcript saved on this device.");
    });
  $("#understand").onclick = () =>
    perform(async () => {
      if (
        current.actions.length &&
        !confirm(
          "Generate fresh proposals? Your current reviews will be archived, and new actions will need review.",
        )
      )
        return;
      current = await saveTranscript();
      dirty = false;
      progress(
        "02 / UNDERSTAND · Gemma is checking language, meaning and next steps…",
      );
      try {
        const result = await api(`/conversations/${current.id}/understand`, {
          method: "POST",
        });
        tab = "actions";
        await adopt(result);
        toast("Your next steps are ready to review.");
      } finally {
        progress("");
      }
    });
  if ($("#transcribe"))
    $("#transcribe").onclick = () =>
      perform(async () => {
        if (
          current.transcript &&
          !confirm(
            "Replace the edited transcript and clear its action proposals with a new transcription?",
          )
        )
          return;
        await transcribeCurrent();
      });
  document.querySelectorAll(".segment").forEach(
    (button) =>
      (button.onclick = () => {
        $("#audioPlayer").currentTime = Number(button.dataset.start);
        $("#audioPlayer")
          .play()
          .catch(() => {});
      }),
  );
}
function renderActions() {
  if (!current.actions.length) {
    $("#panel").innerHTML =
      '<div class="empty-actions">Your next steps will appear here.<br>Review a transcript and choose “Understand with Gemma”.</div>';
    return;
  }
  $("#panel").innerHTML =
    `<p class="hint">${current.actions.filter((a) => a.status === "needs clarification").length} need clarification · Tasks are saved here; deadline alerts appear while this page is open.</p>` +
    current.actions
      .map(
        (a) =>
          `<article class="action ${a.status.replaceAll(" ", "-")}"><div class="action-top"><span class="action-type">${escapeHtml(a.type)} ${a.certainty === "confirmed" ? "" : "· " + escapeHtml(a.certainty)}</span><span class="action-status ${a.status}">${escapeHtml(a.status)}</span></div><h3>${escapeHtml(a.title)}</h3><p>${escapeHtml(a.details)}</p>${a.type === "event" ? `<p>${escapeHtml(a.date || "Date needed")} · ${escapeHtml(a.time || "Time / AM-PM needed")} · ${escapeHtml(a.timezone)}${a.duration_minutes ? " · " + a.duration_minutes + " min" : ""}<br>${escapeHtml(a.location)}</p>` : ""}${a.type === "task" && (a.due || a.owner) ? `<p>${escapeHtml(a.owner || "Owner unassigned")} ${a.due ? "· Due: " + escapeHtml(a.due) : ""}</p>` : ""}${a.type === "shopping" ? `<p>${a.budget_inr !== null ? "Budget: ₹" + a.budget_inr + " · " : ""}${a.quantity ? "Qty " + a.quantity + " · " : ""}${escapeHtml(a.compatibility || "Compatibility not specified")}</p>` : ""}<button class="evidence" data-evidence="${a.id}" title="Show supporting transcript">“${escapeHtml(a.evidence)}” <span>↗</span></button>${a.missing.length ? `<div class="questions">${a.missing.map((q) => escapeHtml(q)).join("<br>")}</div>` : ""}<div class="toolbar"><button class="secondary" data-edit="${a.id}">Review & edit</button>${a.status === "ready" && a.type === "event" ? `<button class="secondary" data-export="${a.id}">Download .ics ↗</button><button class="secondary" data-google="${a.id}">Google Calendar ↗</button>` : ""}${a.status === "ready" && a.type === "shopping" ? `<a class="secondary" target="_blank" rel="noopener noreferrer" href="https://www.google.com/search?q=${encodeURIComponent(`${a.product || a.title} ${a.compatibility} ${a.budget_inr !== null ? "under INR " + a.budget_inr : ""}`)}">Prepared search ↗</a>` : ""}${a.status === "ready" ? `<button class="text-button" data-complete="${a.id}">Mark done</button>` : ""}${!["completed", "dismissed"].includes(a.status) ? `<button class="text-button" data-dismiss="${a.id}">Dismiss</button>` : ""}</div>${a.type === "shopping" ? '<p class="hint">Search link only. No live listings, prices or availability verified.</p>' : ""}${a.type === "event" && a.reminder_minutes !== null ? `<p class="hint">${a.reminder_minutes}-minute alert included in the export. Your calendar app controls delivery after import.</p>` : ""}</article>`,
      )
      .join("");
  document
    .querySelectorAll("[data-edit]")
    .forEach((b) => (b.onclick = () => openAction(b.dataset.edit)));
  for (const [attr, status] of [
    ["complete", "completed"],
    ["dismiss", "dismissed"],
  ])
    document.querySelectorAll(`[data-${attr}]`).forEach(
      (b) =>
        (b.onclick = () =>
          perform(async () => {
            const a = current.actions.find((a) => a.id === b.dataset[attr]);
            await adopt(
              await api(`/conversations/${current.id}/actions/${a.id}`, {
                method: "PUT",
                body: JSON.stringify({ ...a, status }),
              }),
            );
          })),
    );
  document.querySelectorAll("[data-evidence]").forEach(
    (b) =>
      (b.onclick = () => {
        const a = current.actions.find((a) => a.id === b.dataset.evidence);
        tab = "transcript";
        renderDetail();
        const area = $("#transcript");
        const index = area.value.indexOf(a.evidence);
        area.focus();
        area.setSelectionRange(index, index + a.evidence.length);
        const seg = current.segments.find(
          (s) => a.evidence.includes(s.text) || s.text.includes(a.evidence),
        );
        if (seg && $("#audioPlayer")) $("#audioPlayer").currentTime = seg.start;
      }),
  );
  document.querySelectorAll("[data-export]").forEach(
    (b) =>
      (b.onclick = () =>
        perform(async () => {
          const response = await fetch(
            `/api/conversations/${current.id}/actions/${b.dataset.export}/calendar`,
          );
          if (!response.ok) throw Error((await response.json()).detail);
          download(await response.blob(), "followthrough.ics");
          toast(
            "Calendar file downloaded. Import it into your calendar; no event has been added yet.",
          );
        })),
  );
}
function openAction(id) {
  editing = current.actions.find((a) => a.id === id);
  const a = editing;
  let html = `<div class="evidence">“${escapeHtml(a.evidence)}”</div>${a.missing.length ? '<div class="questions">' + a.missing.map(escapeHtml).join("<br>") + "</div>" : ""}${field("title", "Title", a.title)}<label class="field"><span>Details / clarification answers</span><textarea name="details" rows="3">${escapeHtml(a.details)}</textarea></label><label class="field"><span>Commitment</span><select name="certainty"><option value="confirmed">Confirmed</option><option value="tentative">Tentative / maybe</option><option value="conditional">Conditional / waiting</option></select></label>`;
  if (a.type === "event")
    html += `<div class="field-grid">${field("date", "Date", a.date, "date")}${field("time", "Time (24 hour)", a.time, "time")}${field("duration_minutes", "Duration in minutes", a.duration_minutes ?? "", "number")}${field("reminder_minutes", "Calendar alert: minutes before", a.reminder_minutes ?? "", "number")}</div>${field("timezone", "Timezone", a.timezone)}${field("location", "Location", a.location)}`;
  if (a.type === "task")
    html +=
      field("owner", "Owner (leave blank if unknown)", a.owner) +
      field("due", "Due (optional, include timezone)", a.due);
  if (a.type === "shopping")
    html +=
      field("product", "Product", a.product) +
      `<div class="field-grid">${field("budget_inr", "Maximum budget (₹)", a.budget_inr ?? "", "number")}${field("quantity", "Quantity (optional)", a.quantity ?? "", "number")}</div>` +
      field("compatibility", "Compatibility requirements", a.compatibility);
  $("#actionFields").innerHTML = html;
  $('[name="certainty"]').value = a.certainty;
  $("#resolve").checked = false;
  $("#actionDialog").showModal();
}
$("#actionForm").onsubmit = (event) => {
  event.preventDefault();
  perform(async () => {
    const data = Object.fromEntries(new FormData(event.target));
    for (const key of [
      "duration_minutes",
      "reminder_minutes",
      "budget_inr",
      "quantity",
    ])
      if (key in data) data[key] = data[key] === "" ? null : Number(data[key]);
    const resolved = $("#resolve").checked;
    const action = {
      ...editing,
      ...data,
      missing: resolved ? [] : editing.missing,
      status: "ready",
    };
    if (editing.type === "question" && resolved) action.status = "completed";
    await adopt(
      await api(`/conversations/${current.id}/actions/${editing.id}`, {
        method: "PUT",
        body: JSON.stringify(action),
      }),
    );
    $("#actionDialog").close();
    toast("Review saved. Missing required fields still block execution.");
  });
};
$("#closeDialog").onclick = $("#cancelDialog").onclick = () =>
  $("#actionDialog").close();
function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function renderRecap() {
  $("#panel").innerHTML =
    `<label class="field"><span>A little clearer. Still you.</span><textarea id="recap" rows="10" placeholder="Your recap will appear after Gemma processes the transcript.">${escapeHtml(current.recap)}</textarea></label><div class="toolbar"><button id="saveRecap" class="primary">Save edits</button><button id="copyRecap" class="secondary">Copy recap</button><button id="downloadRecap" class="text-button">Download .txt ↗</button></div><p class="hint">Draft only — nothing is sent. Gemma writes this recap. To change tone or language, choose it in Transcript and rerun understanding. Voice cloning is outside this MVP.</p>`;
  $("#saveRecap").onclick = () =>
    perform(async () => {
      await adopt(
        await api(`/conversations/${current.id}/recap`, {
          method: "PUT",
          body: JSON.stringify({ recap: $("#recap").value }),
        }),
      );
      toast("Recap saved.");
    });
  $("#copyRecap").onclick = () =>
    perform(async () => {
      await navigator.clipboard.writeText($("#recap").value);
      toast("Recap copied.");
    });
  $("#downloadRecap").onclick = () =>
    download(
      new Blob([$("#recap").value], { type: "text/plain;charset=utf-8" }),
      "followthrough-recap.txt",
    );
}
async function transcribeCurrent() {
  progress(
    "01 / TRANSCRIBE · Detecting languages and transcribing with local Whisper. Larger models may take a few minutes; the first run downloads the model…",
  );
  try {
    await adopt(
      await api(`/conversations/${current.id}/transcribe`, { method: "POST" }),
    );
    toast(
      "Transcript ready. Review names, numbers and the recording date before understanding.",
    );
  } finally {
    progress("");
  }
}
async function ingest(file, recordedAt) {
  if (!leaveDraft()) return;
  await create();
  if (recordedAt) {
    current = await api(`/conversations/${current.id}/transcript`, {
      method: "PUT",
      body: JSON.stringify({
        transcript: "",
        recorded_at: recordedAt,
        timezone: current.timezone,
        style: current.style,
      }),
    });
  }
  progress("01 / CAPTURE · Saving your original recording…");
  const body = new FormData();
  body.append("file", file);
  try {
    await adopt(
      await api(`/conversations/${current.id}/audio`, { method: "POST", body }),
    );
    await transcribeCurrent();
  } finally {
    progress("");
  }
}
$("#upload").onchange = (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  if (!$("#consent").checked) {
    toast("Confirm everyone’s knowledge and agreement before uploading.", true);
    return;
  }
  if (file.size > 30 * 1024 * 1024) {
    toast("Please upload a file smaller than 30 MB.", true);
    return;
  }
  perform(() => ingest(file));
};
$("#record").onclick = async () => {
  if (recorder?.state === "recording") {
    recorder.stop();
    return;
  }
  if (busy) return;
  if (!leaveDraft()) return;
  if (!$("#consent").checked) {
    toast("Confirm everyone’s knowledge and agreement before recording.", true);
    return;
  }
  try {
    if (!navigator.mediaDevices || !window.MediaRecorder)
      throw Error(
        "Recording needs a supported browser on localhost or HTTPS. You can upload audio instead.",
      );
    busy = true;
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = [
      "audio/webm;codecs=opus",
      "audio/mp4",
      "audio/ogg;codecs=opus",
    ].find((t) => MediaRecorder.isTypeSupported(t));
    recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : {});
    chunks = [];
    recordStart = Date.now();
    recorder.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    recorder.onstop = () => {
      clearInterval(timerInterval);
      stream.getTracks().forEach((t) => t.stop());
      $("#capture").classList.remove("recording");
      $("#recordingState").hidden = true;
      $("#detail").inert = false;
      $("#record").innerHTML = '<span class="mic">●</span> Start recording';
      const ext = recorder.mimeType.includes("mp4")
        ? "m4a"
        : recorder.mimeType.includes("ogg")
          ? "ogg"
          : "webm";
      const file = new File(chunks, `recording.${ext}`, {
        type: recorder.mimeType,
      });
      perform(() => ingest(file, new Date(recordStart).toISOString()));
    };
    recorder.start(1000);
    busy = false;
    $("#detail").inert = true;
    $("#capture").classList.add("recording");
    $("#recordingState").hidden = false;
    $("#record").textContent = "■ Stop recording";
    $("#timer").textContent = "00:00";
    timerInterval = setInterval(() => {
      const elapsed = (Date.now() - recordStart) / 1000;
      $("#timer").textContent = stamp(elapsed);
      if (elapsed >= 600) recorder.stop();
    }, 1000);
  } catch (e) {
    busy = false;
    $("#detail").inert = false;
    stream?.getTracks().forEach((t) => t.stop());
    toast(
      e.name === "NotAllowedError"
        ? "Microphone access was denied. Allow it in your browser or upload a file."
        : e.message,
      true,
    );
  }
};
$("#new").onclick = () => {
  if (leaveDraft()) perform(() => create("", "live", "#capture"));
};
$("#write").onclick = () => {
  if (leaveDraft()) perform(() => create());
};
$("#example").onclick = () =>
  perform(async () => {
    await create(example, "sample");
    toast(
      "Example transcript loaded. The actions will be generated live by Gemma.",
    );
  });
$("#search").oninput = renderList;
$("#inboxNav").onclick = () => {
  if (busy || !leaveDraft()) return;
  $("#detail").hidden = true;
  $("#taskWorkspace").scrollIntoView({ behavior: "smooth" });
};
$("#checkModel").onclick = () =>
  perform(async () => {
    const el = $("#model-state");
    el.textContent = "Testing live inference…";
    try {
      const response = await api("/model/check", { method: "POST" });
      el.textContent = "Live inference verified";
      $(".status-dot").style.background = "#65a586";
      toast("Connected to " + response.model);
    } catch (e) {
      el.textContent = "Connection needs attention";
      throw e;
    }
  });
$(".waveform").innerHTML = Array.from(
  { length: 34 },
  (_, i) =>
    `<i style="height:${10 + Math.abs(Math.sin(i * 1.7)) * 43}px;animation-delay:${i * 0.07}s"></i>`,
).join("");
window.addEventListener("beforeunload", (event) => {
  if (recorder?.state === "recording" || busy || dirty) {
    event.preventDefault();
    event.returnValue = "";
  }
});
async function updateHealth() {
  const health = await api("/health");
  $("#model-name").textContent = health.model;
  const descriptions = {
    available: "Local model installed · test inference",
    model_missing: "Ollama connected · model download needed",
    offline: "Start your local Ollama runtime",
    key_configured: "API key configured · test inference",
    key_missing: "Add GEMINI_API_KEY to .env",
  };
  if ($("#model-state").textContent !== "Live inference verified")
    $("#model-state").textContent = descriptions[health.state];
  let notice = $("#modelNotice");
  if (!notice) {
    notice = document.createElement("div");
    notice.id = "modelNotice";
    notice.className = "stage";
    $(".page-heading").after(notice);
  }
  notice.hidden = ["available", "key_configured"].includes(health.state);
  notice.textContent =
    health.state === "model_missing"
      ? "Local understanding is waiting for the Gemma model download. You can capture, transcribe and save thoughts now."
      : health.state === "offline"
        ? "Local understanding is offline. Start Ollama; your saved recordings and transcripts are still here."
        : "Understanding needs an API key configured on the server. Recording and local transcription are available.";
}
perform(async () => {
  await updateHealth();
  await refresh();
});
setInterval(() => {
  if (!busy) updateHealth().catch(() => {});
}, 30000);
let taskFilter = "remaining",
  planning = null;
function allTaskRows() {
  return items
    .filter(
      (c) =>
        $("#includeSamples").checked ||
        !["sample", "synthetic"].includes(c.source),
    )
    .flatMap((c) =>
      c.actions
        .filter((a) => a.type !== "decision" && a.status !== "dismissed")
        .map((a) => ({
          c,
          a,
          plan: c.task_plans?.[a.id] || { deadline: "", priority: "normal" },
        })),
    );
}
function countdown(deadline) {
  const delta = new Date(deadline).getTime() - Date.now();
  const total = Math.floor(Math.abs(delta) / 1000);
  const days = Math.floor(total / 86400),
    hours = Math.floor((total % 86400) / 3600),
    minutes = Math.floor((total % 3600) / 60),
    seconds = total % 60;
  return `${delta < 0 ? "Overdue · " : ""}${days ? days + "d " : ""}${hours}h ${minutes}m ${seconds}s${delta >= 0 ? " left" : ""}`;
}
function tickDeadlines() {
  document.querySelectorAll("[data-countdown]").forEach((el) => {
    el.textContent = countdown(el.dataset.countdown);
    el.classList.toggle(
      "late",
      new Date(el.dataset.countdown).getTime() < Date.now(),
    );
  });
}
function renderTasks() {
  const rows = allTaskRows(),
    pending = rows.filter((r) => r.a.status !== "completed");
  const today = new Date().toDateString();
  const isToday = (r) =>
    r.plan.deadline && new Date(r.plan.deadline).toDateString() === today;
  const overdue = (r) =>
    r.plan.deadline && new Date(r.plan.deadline).getTime() < Date.now();
  $("#remainingCount").textContent = pending.length;
  $("#taskProgress").textContent =
    `${rows.length - pending.length} of ${rows.length} completed`;
  $("#taskStats").innerHTML =
    `<div><strong>${pending.length}</strong><span>Remaining</span></div><div><strong>${pending.filter(isToday).length}</strong><span>Due today</span></div><div><strong>${pending.filter(overdue).length}</strong><span>Overdue</span></div><div><strong>${pending.filter((r) => r.a.status === "needs clarification").length}</strong><span>Need review</span></div>`;
  let visible = rows.filter((r) =>
    taskFilter === "completed"
      ? r.a.status === "completed"
      : r.a.status !== "completed" &&
        (taskFilter === "today"
          ? isToday(r)
          : taskFilter === "overdue"
            ? overdue(r)
            : true),
  );
  visible.sort(
    (x, y) =>
      (x.plan.deadline ? new Date(x.plan.deadline).getTime() : Infinity) -
        (y.plan.deadline ? new Date(y.plan.deadline).getTime() : Infinity) ||
      { high: 0, normal: 1, low: 2 }[x.plan.priority] -
        { high: 0, normal: 1, low: 2 }[y.plan.priority],
  );
  $("#taskRows").innerHTML =
    visible
      .map(
        ({ c, a, plan }) =>
          `<article class="todo-row ${a.status === "completed" ? "done" : ""}" data-cid="${c.id}" data-aid="${a.id}"><button class="task-check" data-task-action="complete" aria-label="${a.status === "completed" ? "Reopen" : "Complete"} ${escapeHtml(a.title)}" ${a.status === "needs clarification" ? 'disabled title="Review this action first"' : ""}>${a.status === "completed" ? "✓" : "○"}</button><div class="todo-content"><button class="todo-title" data-task-action="review">${escapeHtml(a.title)}</button><div class="todo-meta"><span>${escapeHtml(a.type)}</span><span class="priority ${plan.priority}">${escapeHtml(plan.priority)}</span>${a.status === "needs clarification" ? '<span class="review-tag">Needs review</span>' : ""}<button data-task-action="source" class="source-link">${escapeHtml(c.title)}</button></div>${a.due ? `<p class="hint">Mentioned due: ${escapeHtml(a.due)} · Set an exact deadline to start a timer.</p>` : ""}<div class="task-hover"><blockquote>${escapeHtml(a.evidence)}</blockquote>${a.missing.length ? `<p>${escapeHtml(a.missing.join(" "))}</p>` : ""}</div></div><button class="deadline-chip" data-task-action="plan">${plan.deadline ? `<span>${escapeHtml(new Date(plan.deadline).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }))}</span>${a.status !== "completed" ? `<strong data-countdown="${escapeHtml(plan.deadline)}"></strong>` : "<strong>Completed</strong>"}` : "＋ Set deadline"}</button><div class="row-tools"><button data-task-action="delete" aria-label="Delete ${escapeHtml(a.title)}" title="Delete task" class="bin-button"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18M9 6V4h6v2M5 6l1 14h12l1-14M10 10v6M14 10v6"/></svg></button><button class="complete-button" data-task-action="${a.status === "needs clarification" ? "review" : "complete"}" title="${a.status === "needs clarification" ? "Review missing details before completing" : ""}">${a.status === "completed" ? "Reopen" : a.status === "needs clarification" ? "Review to complete" : "✓ Mark complete"}</button><button data-task-action="review" aria-label="Review ${escapeHtml(a.title)}">↗</button>${a.type === "event" ? (a.status === "ready" ? '<button class="calendar-visible" data-task-action="calendar">Google Calendar ↗</button>' : '<button class="calendar-visible" data-task-action="calendarReview">Review for Calendar</button>') : ""}<button data-task-action="plan" aria-label="Plan ${escapeHtml(a.title)}">•••</button></div></article>`,
      )
      .join("") ||
    '<div class="tasks-empty"><span>✓</span><h3>Room to breathe.</h3><p>No tasks in this view. Add a task above or turn a voice note into next steps.</p></div>';
  tickDeadlines();
}
$("#taskRows").onclick = (event) => {
  const button = event.target.closest("[data-task-action]");
  if (!button) return;
  const row = button.closest(".todo-row");
  perform(async () => {
    if (!leaveDraft()) return;
    const c = await api("/conversations/" + row.dataset.cid);
    const a = c.actions.find((a) => a.id === row.dataset.aid);
    if (!a) throw Error("This task changed. Refresh the list.");
    const command = button.dataset.taskAction;
    if (command === "delete") {
      await removeTasks([{ cid: c.id, aid: a.id }], `Delete “${a.title}”?`);
      return;
    }
    if (command === "calendarReview") {
      current = c;
      tab = "actions";
      renderDetail();
      openAction(a.id);
      return;
    }
    if (command === "complete") {
      await api(`/conversations/${c.id}/actions/${a.id}`, {
        method: "PUT",
        body: JSON.stringify({
          ...a,
          status: a.status === "completed" ? "ready" : "completed",
        }),
      });
      if (current?.id === c.id) {
        current = await api("/conversations/" + c.id);
        renderDetail();
      }
      await refresh();
      return;
    }
    if (command === "plan") {
      planning = { cid: c.id, aid: a.id };
      const plan = c.task_plans?.[a.id] || {};
      $("#planTitle").textContent = a.title;
      $("#planDeadline").value = plan.deadline ? localInput(plan.deadline) : "";
      $("#planPriority").value = plan.priority || "normal";
      $("#planDialog").showModal();
      return;
    }
    if (command === "calendar") {
      await showGoogleCalendar(c, a);
      return;
    }
    current = c;
    tab = "actions";
    renderDetail();
    renderList();
    if (command === "review") openAction(a.id);
    else $("#detail").scrollIntoView({ behavior: "smooth" });
  });
};
$("#quickTask").onsubmit = (event) => {
  event.preventDefault();
  perform(async () => {
    const deadline = $("#quickDeadline").value;
    await api("/tasks", {
      method: "POST",
      body: JSON.stringify({
        title: $("#quickTitle").value,
        deadline: deadline ? new Date(deadline).toISOString() : "",
        priority: "normal",
      }),
    });
    $("#quickTask").reset();
    await refresh();
    toast("Task added.");
  });
};
$("#planForm").onsubmit = (event) => {
  event.preventDefault();
  perform(async () => {
    const deadline = $("#planDeadline").value;
    const item = await api(
      `/conversations/${planning.cid}/actions/${planning.aid}/plan`,
      {
        method: "PUT",
        body: JSON.stringify({
          deadline: deadline ? new Date(deadline).toISOString() : "",
          priority: $("#planPriority").value,
        }),
      },
    );
    if (current?.id === item.id) current = item;
    $("#planDialog").close();
    await refresh();
    toast("Deadline and priority saved.");
  });
};
$("#closePlan").onclick = () => $("#planDialog").close();
$("#clearDeadline").onclick = () => {
  $("#planDeadline").value = "";
};
$("#includeSamples").onchange = renderTasks;
document.querySelectorAll("[data-filter]").forEach(
  (button) =>
    (button.onclick = () => {
      taskFilter = button.dataset.filter;
      document
        .querySelectorAll("[data-filter]")
        .forEach((b) => b.classList.toggle("active", b === button));
      renderTasks();
    }),
);
async function showGoogleCalendar(c, a) {
  const result = await api(
    `/conversations/${c.id}/actions/${a.id}/google-calendar`,
  );
  $("#calendarPreview").innerHTML =
    `<h3>${escapeHtml(a.title)}</h3><p>${escapeHtml(a.date)} · ${escapeHtml(a.time)} · ${escapeHtml(a.timezone)} · ${a.duration_minutes} minutes</p><p>${escapeHtml(a.location)}</p><p>${escapeHtml(a.details)}</p>${a.reminder_minutes !== null ? `<p>Requested reminder: ${a.reminder_minutes} minutes before. Set this in Google Calendar, or use the .ics export.</p>` : ""}`;
  $("#openGoogle").href = result.url;
  $("#calendarDialog").showModal();
}
$("#closeCalendar").onclick = () => $("#calendarDialog").close();
document.addEventListener("click", (event) => {
  const b = event.target.closest("[data-google]");
  if (b)
    perform(() =>
      showGoogleCalendar(
        current,
        current.actions.find((a) => a.id === b.dataset.google),
      ),
    );
});
setInterval(tickDeadlines, 1000);
async function removeTasks(targets, question) {
  if (!targets.length) {
    toast("No tasks to delete.");
    return;
  }
  if (
    !confirm(
      question +
        "\nThis removes task cards and their deadlines. Original recordings and transcripts stay saved. This cannot be undone.",
    )
  )
    return;
  await api("/tasks/delete", {
    method: "POST",
    body: JSON.stringify({ targets }),
  });
  if (current) {
    current = await api("/conversations/" + current.id);
    renderDetail();
  }
  await refresh();
  await pollNotifications();
  toast("Tasks deleted.");
}
$("#deleteAllTasks").onclick = () =>
  perform(async () => {
    if (!leaveDraft()) return;
    const rows = allTaskRows();
    await removeTasks(
      rows.map((r) => ({ cid: r.c.id, aid: r.a.id })),
      `Delete all ${rows.length} tasks, including completed tasks, across every task filter?${$("#includeSamples").checked ? " Demo examples are included." : " Demo examples are excluded."}`,
    );
  });
let notificationItems = [],
  notificationPolling = false;
function notificationStore(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) || fallback;
  } catch {
    return fallback;
  }
}
function saveNotificationStore(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {}
}
async function pollNotifications() {
  if (notificationPolling) return;
  notificationPolling = true;
  try {
    notificationItems = await api("/notifications");
    const dismissed = new Set(
      notificationStore("ft-dismissed-notifications", []),
    );
    const visible = notificationItems.filter((n) => !dismissed.has(n.id));
    $("#notificationCount").textContent = visible.length;
    $("#notificationList").innerHTML =
      visible
        .map(
          (n) =>
            `<div class="notification-item"><strong>${escapeHtml(n.title)}</strong><p>${escapeHtml(n.kind)} · ${escapeHtml(new Date(n.at).toLocaleString())}</p></div>`,
        )
        .join("") || '<p class="hint">No reminders waiting.</p>';
    const seen = new Set(notificationStore("ft-seen-notifications", []));
    for (const n of visible) {
      if (seen.has(n.id)) continue;
      // Only recent reminders generate a desktop interruption; older ones stay in the tray.
      if (
        Date.now() - new Date(n.at).getTime() < 300000 &&
        notificationStore("ft-desktop-alerts", false) &&
        "Notification" in window &&
        Notification.permission === "granted"
      ) {
        try {
          new Notification(n.title, {
            body: `${n.kind} · ${new Date(n.at).toLocaleTimeString()}`,
            tag: n.id,
          });
        } catch {}
      }
      seen.add(n.id);
    }
    saveNotificationStore("ft-seen-notifications", [...seen].slice(-1000));
  } catch {
  } finally {
    notificationPolling = false;
  }
}
$("#enableNotifications").onclick = async () => {
  if (notificationStore("ft-desktop-alerts", false)) {
    saveNotificationStore("ft-desktop-alerts", false);
    updateNotificationButton();
    return;
  }
  if (!("Notification" in window)) {
    toast(
      "This browser does not support desktop alerts. In-app reminders remain available.",
      true,
    );
    return;
  }
  const permission = await Notification.requestPermission();
  saveNotificationStore("ft-desktop-alerts", permission === "granted");
  updateNotificationButton();
  if (permission !== "granted")
    toast(
      "Desktop permission was not granted. Use the in-app notification tray.",
      true,
    );
};
function updateNotificationButton() {
  const enabled =
    notificationStore("ft-desktop-alerts", false) &&
    "Notification" in window &&
    Notification.permission === "granted";
  $("#enableNotifications").textContent = enabled
    ? "Disable desktop alerts"
    : "Enable desktop alerts";
}
$("#dismissNotifications").onclick = () => {
  const dismissed = new Set(
    notificationStore("ft-dismissed-notifications", []),
  );
  notificationItems.forEach((n) => dismissed.add(n.id));
  saveNotificationStore(
    "ft-dismissed-notifications",
    [...dismissed].slice(-1000),
  );
  pollNotifications();
};
updateNotificationButton();
pollNotifications();
setInterval(pollNotifications, 10000);
addEventListener("focus", pollNotifications);
let modelCatalog = null;
const modelDialog = $("#modelDialog");
function renderModelPicker() {
  const provider = $("input[name=provider]:checked", modelDialog).value;
  $("#localModelOptions").hidden = provider !== "ollama";
  $("#cloudModelOptions").hidden = provider !== "google";
  const selected = modelCatalog.local[Number($("#modelSlider").value)];
  $("#selectedModelLabel").textContent = selected.label;
  $("#modelSlider").setAttribute("aria-valuetext", selected.label);
  $("#modelHint").textContent = selected.hint;
  $("#modelInstalled").textContent = selected.installed
    ? "Installed on this device"
    : modelCatalog.ollama_online
      ? "Download required before local inference"
      : "Start Ollama, then download this model";
  $("#modelPull").hidden = selected.installed;
  $("#modelPull").textContent = "ollama pull " + selected.id;
}
$("#openModels").onclick = () =>
  perform(async () => {
    modelCatalog = await api("/model/settings");
    $("#cloudModel").innerHTML = modelCatalog.cloud
      .map(
        (m) =>
          `<option value="${escapeHtml(m.id)}">${escapeHtml(m.label)}</option>`,
      )
      .join("");
    $("#modelSlider").value = Math.max(
      0,
      modelCatalog.local.findIndex(
        (m) =>
          m.id ===
          (modelCatalog.provider === "ollama"
            ? modelCatalog.model
            : "gemma4:e4b"),
      ),
    );
    if (modelCatalog.provider === "google")
      $("#cloudModel").value = modelCatalog.model;
    $(
      `input[name=provider][value=${modelCatalog.provider}]`,
      modelDialog,
    ).checked = true;
    $("#cloudKey").value = "";
    $("#clearCloudKey").checked = false;
    $("#cloudKeyStatus").textContent = modelCatalog.key_configured
      ? "A key is saved. Leave blank to keep it."
      : "No key configured yet.";
    $("#modelSaveStatus").textContent = "";
    renderModelPicker();
    modelDialog.showModal();
  });
$("#closeModels").onclick = () => modelDialog.close();
modelDialog.addEventListener("cancel", () => {
  $("#cloudKey").value = "";
});
modelDialog.addEventListener("close", () => {
  $("#cloudKey").value = "";
});
$("#modelSlider").oninput = renderModelPicker;
modelDialog
  .querySelectorAll("input[name=provider]")
  .forEach((input) => (input.onchange = renderModelPicker));
$("#modelForm").onsubmit = async (event) => {
  event.preventDefault();
  const button = $("#saveModels");
  button.disabled = true;
  const provider = $("input[name=provider]:checked", modelDialog).value;
  const model =
    provider === "ollama"
      ? modelCatalog.local[Number($("#modelSlider").value)].id
      : $("#cloudModel").value;
  try {
    const saved = await api("/model/settings", {
      method: "PUT",
      body: JSON.stringify({
        provider,
        model,
        api_key: $("#cloudKey").value.trim() || null,
        clear_key: $("#clearCloudKey").checked,
      }),
    });
    $("#cloudKey").value = "";
    $("#clearCloudKey").checked = false;
    $("#cloudKeyStatus").textContent = saved.key_configured
      ? "A key is saved. Leave blank to keep it."
      : "No key configured yet.";
    $("#modelSaveStatus").textContent =
      "Saved " +
      saved.model +
      ". " +
      (provider === "google" && !saved.key_configured
        ? "Add an API key to enable cloud inference."
        : "Test the saved connection when ready.");
    $("#model-state").textContent = "Checking configuration…";
    await updateHealth();
  } catch (error) {
    $("#modelSaveStatus").textContent = error.message;
  } finally {
    button.disabled = false;
  }
};
$("#testSelectedModel").onclick = async () => {
  const button = $("#testSelectedModel");
  button.disabled = true;
  $("#modelSaveStatus").textContent =
    "Testing saved model with live inference… This can take a few minutes locally.";
  try {
    const result = await api("/model/check", { method: "POST" });
    $("#modelSaveStatus").textContent =
      "Live inference verified: " + result.model;
  } catch (error) {
    $("#modelSaveStatus").textContent = error.message;
  } finally {
    button.disabled = false;
  }
};

const state = {
  activeRunId: "",
  activeRunRequestId: "",
  fixtures: [],
};

function $(id) {
  return document.getElementById(id);
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${text}`);
  }
  return res.json();
}

function setStatus(message, tone = "neutral") {
  const node = $("runStatusText");
  node.textContent = message;
  node.className = `status ${tone}`;
}

function stateNote(message, tone = "neutral") {
  return `<span class="state-note ${tone}">${message}</span>`;
}

function renderFixtures(items) {
  const host = $("fixtures");
  host.innerHTML = "";
  if (!items.length) {
    host.innerHTML = stateNote("No fixtures configured.", "neutral");
    return;
  }
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "fixture";
    const tag = item.featured_rank === 1 ? "<strong class=\"featured-tag\">Featured</strong>" : "";
    card.innerHTML = `
      <small>${item.category}</small>
      <h3>${item.title}</h3>
      <p>${item.description}</p>
      ${tag}
      <button class="btn btn-primary" data-id="${item.id}">Run Sample</button>
    `;
    host.appendChild(card);
  }
}

async function onFixtureClick(event) {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const fixtureId = target.dataset.id || "";
  if (!fixtureId) return;
  await startSampleRun(fixtureId);
}

function renderSteps(steps) {
  const host = $("steps");
  host.innerHTML = "";
  if (!steps || !steps.length) {
    host.innerHTML = `<li>${stateNote("Waiting for run to start.", "neutral")}</li>`;
    return;
  }
  for (const step of steps) {
    const li = document.createElement("li");
    li.className = step.status || "pending";
    li.textContent = `${step.label} - ${step.status}`;
    host.appendChild(li);
  }
}

async function pollRun(runRequestId) {
  state.activeRunRequestId = runRequestId;
  setStatus(`Run request ${runRequestId} started.`, "working");
  let finished = false;
  while (!finished) {
    let run;
    try {
      run = await api(`/api/runs/${runRequestId}`);
    } catch (error) {
      setStatus(`Run status failed to load: ${error.message}`, "fail");
      renderSteps([]);
      return;
    }
    renderSteps(run.steps || []);
    if (run.status === "completed") {
      finished = true;
      state.activeRunId = run.run_id;
      setStatus(`Completed: ${run.run_id}`, "ok");
      await loadWorkspace(run.run_id);
      break;
    }
    if (run.status === "failed") {
      finished = true;
      setStatus(`Failed: ${run.error || "unknown error"}`, "fail");
      break;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

async function startSampleRun(fixtureId) {
  setStatus("Starting sample run...", "working");
  const result = await api("/api/runs/sample", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fixture_id: fixtureId }),
  });
  await pollRun(result.run_request_id);
}

async function startUploadRun(formEvent) {
  formEvent.preventDefault();
  setStatus("Starting upload run...", "working");
  const form = $("uploadForm");
  const data = new FormData(form);
  const result = await api("/api/runs/upload", {
    method: "POST",
    body: data,
  });
  await pollRun(result.run_request_id);
}

function fillList(hostId, items, formatter) {
  const host = $(hostId);
  host.innerHTML = "";
  if (!items || !items.length) {
    const li = document.createElement("li");
    li.innerHTML = stateNote("No items.", "neutral");
    host.appendChild(li);
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.innerHTML = formatter(item);
    host.appendChild(li);
  }
}

function setWorkspaceLoading(runId) {
  $("workspaceTitle").textContent = `Loading workspace for ${runId}...`;
  $("timelineList").innerHTML = `<li>${stateNote("Loading timeline...", "loading")}</li>`;
  $("contradictionsList").innerHTML = `<li>${stateNote("Loading contradictions...", "loading")}</li>`;
  $("unknownsList").innerHTML = `<li>${stateNote("Loading unknowns...", "loading")}</li>`;
  $("artifactsList").innerHTML = `<li>${stateNote("Loading artifacts...", "loading")}</li>`;
  $("receiptsBox").textContent = "Loading receipts...";
  $("narrativeBox").textContent = "Loading narratives...";
  $("integrityGrid").innerHTML = stateNote("Loading integrity...", "loading");
  $("replayBox").textContent = "Replay command will appear here.";
}

function setWorkspaceFailure(runId, message) {
  $("workspaceTitle").textContent = `Workspace load failed for ${runId}`;
  $("timelineList").innerHTML = `<li>${stateNote(message, "fail")}</li>`;
  $("contradictionsList").innerHTML = `<li>${stateNote(message, "fail")}</li>`;
  $("unknownsList").innerHTML = `<li>${stateNote(message, "fail")}</li>`;
  $("artifactsList").innerHTML = `<li>${stateNote(message, "fail")}</li>`;
  $("receiptsBox").textContent = `Failed to load receipts: ${message}`;
  $("narrativeBox").textContent = `Failed to load narrative: ${message}`;
  $("integrityGrid").innerHTML = stateNote(`Failed to load integrity: ${message}`, "fail");
}

async function loadWorkspace(runId) {
  setWorkspaceLoading(runId);

  let summary;
  let timeline;
  let contradictions;
  let unknowns;
  let receipts;
  let artifacts;

  try {
    [summary, timeline, contradictions, unknowns, receipts, artifacts] = await Promise.all([
      api(`/api/runs/${runId}/summary`),
      api(`/api/runs/${runId}/timeline`),
      api(`/api/runs/${runId}/contradictions`),
      api(`/api/runs/${runId}/unknowns`),
      api(`/api/runs/${runId}/receipts`),
      api(`/api/runs/${runId}/artifacts`),
    ]);
  } catch (error) {
    setWorkspaceFailure(runId, error.message);
    setStatus(`Workspace load failed: ${error.message}`, "fail");
    return;
  }

  $("workspaceTitle").textContent = `Casefile ${summary.casefile_id}`;
  $("casefileBox").textContent = JSON.stringify(summary.casefile, null, 2);
  $("verificationScope").textContent = summary.verification_scope || "";

  fillList("timelineList", timeline.items, (item) => {
    const time = item.time.kind === "unknown" ? "unknown time" : item.time.value;
    return `<strong>${time}</strong> | ${item.type} | ${item.action}`;
  });

  fillList("contradictionsList", contradictions.items, (item) => {
    return `<strong>${item.kind || "conflict"}</strong> | ${item.reason || "no reason"}`;
  });

  const unknownItems = [].concat(unknowns.world_unknowns || []).concat(unknowns.required_info || []);
  fillList("unknownsList", unknownItems, (item) => {
    const kind = item.kind || "unknown";
    return `${kind} | ${JSON.stringify(item.ref || {})}`;
  });

  $("receiptsBox").textContent = JSON.stringify(receipts, null, 2);

  fillList("artifactsList", artifacts.items, (item) => {
    return `<a href="${item.download_url}" target="_blank" rel="noreferrer">${item.name}</a> (${item.bytes} bytes)`;
  });

  $("narrativeBox").textContent =
    `Verification: ${summary.summary.verification_status}\n` +
    `Entities: ${summary.summary.entities}, Events: ${summary.summary.events}, Unknowns: ${summary.summary.unknowns}\n` +
    `Conflicts: ${summary.summary.conflicts}, Constraint Violations: ${summary.summary.constraint_violations}\n\n` +
    `World Narrative\n${summary.narratives.world || "Not available."}\n\n` +
    `Causal Narrative\n${summary.narratives.causal || "Not available."}`;

  const integrity = summary.integrity || {};
  const grid = $("integrityGrid");
  grid.innerHTML = "";
  const ordered = [
    "pack_sha256",
    "manifest_sha256",
    "bundle_sha256",
    "world_sha256",
    "output_sha256",
    "attestation_sha256",
    "replay_status",
  ];
  for (const key of ordered) {
    const value = integrity[key] || "";
    const div = document.createElement("div");
    div.className = "hash";
    div.innerHTML = `<span class="k">${key}</span><span class="v">${value}</span>`;
    grid.appendChild(div);
  }
  const ledger = document.createElement("div");
  ledger.className = "hash";
  ledger.innerHTML = `<span class="k">ledger_dir</span><span class="v">${summary.ledger_dir}</span>`;
  grid.appendChild(ledger);

  const replayDetail = integrity.replay_detail
    ? `\n${JSON.stringify(integrity.replay_detail, null, 2)}`
    : "";
  $("replayBox").textContent = `${summary.replay_command}\n\nAuthoritative replay status: ${integrity.replay_status || "NOT_RUN"}${replayDetail}`;
  $("replayBox").className = `mono ${integrity.replay_status === "VERIFIED_OK" ? "pass" : integrity.replay_status === "VERIFIED_FAIL" ? "fail" : ""}`;
}

async function runReplay() {
  if (!state.activeRunId) return;
  setStatus(`Running strict replay verification for ${state.activeRunId}...`, "working");
  const result = await api(`/api/runs/${state.activeRunId}/replay-verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  const ok = result.status === "VERIFIED_OK";
  $("replayBox").textContent = `${ok ? "PASS" : "FAIL"}\n${JSON.stringify(result, null, 2)}`;
  $("replayBox").className = `mono ${ok ? "pass" : "fail"}`;
  setStatus(ok ? "Replay verification passed." : "Replay verification failed.", ok ? "ok" : "fail");
  await loadWorkspace(state.activeRunId);

  if (state.activeRunRequestId) {
    const run = await api(`/api/runs/${state.activeRunRequestId}`);
    renderSteps(run.steps || []);
  }
}

async function init() {
  $("fixtures").innerHTML = stateNote("Loading fixtures...", "loading");
  renderSteps([]);

  $("uploadForm").addEventListener("submit", startUploadRun);
  $("replayBtn").addEventListener("click", runReplay);
  $("fixtures").addEventListener("click", onFixtureClick);

  $("openSampleBtn").addEventListener("click", () => {
    document.getElementById("gallerySection").scrollIntoView({ behavior: "smooth" });
  });
  $("runOwnBtn").addEventListener("click", () => {
    document.getElementById("uploadSection").scrollIntoView({ behavior: "smooth" });
  });

  const fixtures = await api("/api/fixtures");
  state.fixtures = fixtures.items || [];
  renderFixtures(state.fixtures);
}

init().catch((error) => {
  setStatus(`Initialization error: ${error.message}`, "fail");
  $("fixtures").innerHTML = stateNote(`Fixture load failed: ${error.message}`, "fail");
});

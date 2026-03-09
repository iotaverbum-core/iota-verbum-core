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
    const tag =
      item.featured_rank === 1
        ? '<strong class="featured-tag">Featured</strong>'
        : "";
    card.innerHTML = `<small>${item.category}</small><h3>${item.title}</h3><p>${item.description}</p>${tag}<button class="btn btn-primary" data-id="${item.id}">Run Sample</button>`;
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
  const data = new FormData($("uploadForm"));
  const result = await api("/api/runs/upload", { method: "POST", body: data });
  await pollRun(result.run_request_id);
}

function fillList(hostId, items, formatter) {
  const host = $(hostId);
  if (!host) return;
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
}

function initTabs() {
  const tabs = $("workspaceTabs");
  if (!tabs) return;
  tabs.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || !target.dataset.tab) return;
    for (const tab of document.querySelectorAll(".tab")) tab.classList.remove("active");
    for (const panel of document.querySelectorAll(".tab-panel")) panel.classList.remove("active");
    target.classList.add("active");
    $(`tab-${target.dataset.tab}`).classList.add("active");
  });
}

async function loadInvestigation(runId) {
  const [overview, graph, timeline, hypotheses, evidence, narrative] = await Promise.all([
    api(`/api/runs/${runId}/overview`),
    api(`/api/runs/${runId}/graph`),
    api(`/api/runs/${runId}/timeline`),
    api(`/api/runs/${runId}/hypotheses`),
    api(`/api/runs/${runId}/evidence`),
    api(`/api/runs/${runId}/narrative`),
  ]);

  const grid = $("overviewGrid");
  grid.innerHTML = "";
  for (const [key, value] of Object.entries({ ...overview.metrics, headline: overview.headline })) {
    const div = document.createElement("div");
    div.className = "hash";
    div.innerHTML = `<span class="k">${key}</span><span class="v">${value}</span>`;
    grid.appendChild(div);
  }

  fillList("graphNodes", graph.nodes, (node) => `${node.kind} | <strong>${node.id}</strong> | ${node.label}`);
  const graphHost = $("graphNodes");
  graphHost.onclick = async (event) => {
    const li = event.target.closest("li");
    if (!li) return;
    const idText = li.textContent.split("|")[1] || "";
    const nodeId = idText.trim();
    if (!nodeId) return;
    const detail = await api(`/api/runs/${runId}/nodes/${encodeURIComponent(nodeId)}`);
    $("graphNodeDetail").textContent = JSON.stringify(detail, null, 2);
  };

  fillList("timeline2List", timeline.items, (item) => `${item.time.kind === "unknown" ? "unknown" : item.time.value} | ${item.type} | ${item.action}`);
  fillList("hypothesesList", hypotheses.items, (item) => `#${item.rank} <strong>${item.title}</strong> | ${item.adjudication_status}`);
  fillList("evidenceList", evidence.items, (item) => `<strong>${item.evidence_id}</strong> | ${item.source_id}`);
  $("narrative2Box").textContent = JSON.stringify(narrative, null, 2);
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
    await loadInvestigation(runId);
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
  fillList("contradictionsList", contradictions.items, (item) => `<strong>${item.kind || "conflict"}</strong> | ${item.reason || "no reason"}`);
  fillList(
    "unknownsList",
    [].concat(unknowns.world_unknowns || []).concat(unknowns.required_info || []),
    (item) => `${item.kind || "unknown"} | ${JSON.stringify(item.ref || {})}`,
  );
  $("receiptsBox").textContent = JSON.stringify(receipts, null, 2);
  fillList("artifactsList", artifacts.items, (item) => `<a href="${item.download_url}" target="_blank" rel="noreferrer">${item.name}</a> (${item.bytes} bytes)`);
  $("narrativeBox").textContent =
    `Verification: ${summary.summary.verification_status}\n` +
    `Entities: ${summary.summary.entities}, Events: ${summary.summary.events}, Unknowns: ${summary.summary.unknowns}\n` +
    `Conflicts: ${summary.summary.conflicts}, Constraint Violations: ${summary.summary.constraint_violations}\n\n` +
    `World Narrative\n${summary.narratives.world || "Not available."}\n\n` +
    `Causal Narrative\n${summary.narratives.causal || "Not available."}`;

  const integrity = summary.integrity || {};
  const grid = $("integrityGrid");
  const ordered = ["pack_sha256", "manifest_sha256", "bundle_sha256", "world_sha256", "output_sha256", "attestation_sha256", "replay_status"];
  for (const key of ordered) {
    const div = document.createElement("div");
    div.className = "hash";
    div.innerHTML = `<span class="k">${key}</span><span class="v">${integrity[key] || ""}</span>`;
    grid.appendChild(div);
  }
}

async function runReplay() {
  if (!state.activeRunId) return;
  const result = await api(`/api/runs/${state.activeRunId}/replay-verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  const ok = result.status === "VERIFIED_OK";
  $("replayBox").textContent = `${ok ? "PASS" : "FAIL"}\n${JSON.stringify(result, null, 2)}`;
  await loadWorkspace(state.activeRunId);
}

async function loadDiff() {
  if (!state.activeRunId) return;
  const baseline = $("baselineRunId").value.trim();
  const diff = await api(`/api/runs/${state.activeRunId}/diff?against_run_id=${encodeURIComponent(baseline)}`);
  $("diffBox").textContent = JSON.stringify(diff, null, 2);
}

async function init() {
  $("fixtures").innerHTML = stateNote("Loading fixtures...", "loading");
  renderSteps([]);
  $("uploadForm").addEventListener("submit", startUploadRun);
  $("replayBtn").addEventListener("click", runReplay);
  $("fixtures").addEventListener("click", onFixtureClick);
  $("loadDiffBtn").addEventListener("click", loadDiff);
  initTabs();

  $("openSampleBtn").addEventListener("click", () => {
    $("gallerySection").scrollIntoView({ behavior: "smooth" });
  });
  $("runOwnBtn").addEventListener("click", () => {
    $("uploadSection").scrollIntoView({ behavior: "smooth" });
  });

  const fixtures = await api("/api/fixtures");
  state.fixtures = fixtures.items || [];
  renderFixtures(state.fixtures);
}

init().catch((error) => {
  setStatus(`Initialization error: ${error.message}`, "fail");
  $("fixtures").innerHTML = stateNote(`Fixture load failed: ${error.message}`, "fail");
});

const state = { activeRunId: "", activeRunRequestId: "" };

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

function setStatus(message, tone = "neutral") {
  const node = $("runStatusText");
  node.textContent = message;
  node.className = `status ${tone}`;
}

function fillList(hostId, items, formatter, onClick) {
  const host = $(hostId);
  host.innerHTML = "";
  for (const item of items || []) {
    const li = document.createElement("li");
    li.innerHTML = formatter(item);
    if (onClick) li.onclick = () => onClick(item);
    host.appendChild(li);
  }
}

function renderTabs() {
  $("workspaceTabs").addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || !target.dataset.tab) return;
    for (const tab of document.querySelectorAll(".tab")) tab.classList.remove("active");
    for (const panel of document.querySelectorAll(".tab-panel")) panel.classList.remove("active");
    target.classList.add("active");
    $("tab-" + target.dataset.tab).classList.add("active");
  });
}

function renderFixtures(items) {
  fillList("fixtures", items, (item) => `<strong>${item.title}</strong><br>${item.description}<br><button class="btn btn-primary" data-id="${item.id}">Run Sample</button>`);
  $("fixtures").onclick = async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || !target.dataset.id) return;
    const result = await api("/api/runs/sample", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fixture_id: target.dataset.id }) });
    pollRun(result.run_request_id);
  };
}

function renderSteps(steps) {
  fillList("steps", steps, (step) => `${step.label} - ${step.status}`);
}

async function pollRun(runRequestId) {
  state.activeRunRequestId = runRequestId;
  setStatus(`Run request ${runRequestId} started.`, "working");
  while (true) {
    const run = await api(`/api/runs/${runRequestId}`);
    renderSteps(run.steps || []);
    if (run.status === "completed") {
      state.activeRunId = run.run_id;
      setStatus(`Completed: ${run.run_id}`, "ok");
      await loadWorkspace(run.run_id);
      return;
    }
    if (run.status === "failed") {
      setStatus(`Failed: ${run.error || "unknown error"}`, "fail");
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

async function loadWorkspace(runId) {
  const [overview, graph, timeline, hypotheses, evidence, narrative] = await Promise.all([
    api(`/api/runs/${runId}/overview`),
    api(`/api/runs/${runId}/graph`),
    api(`/api/runs/${runId}/timeline`),
    api(`/api/runs/${runId}/hypotheses`),
    api(`/api/runs/${runId}/evidence`),
    api(`/api/runs/${runId}/narrative`),
  ]);

  $("workspaceTitle").textContent = `Case ${overview.case_id}`;
  $("workspaceMeta").textContent = `Run ${overview.run_id} | Graph ${overview.graph_version} | Verification ${overview.metrics.verification_status}`;

  const grid = $("overviewGrid");
  grid.innerHTML = "";
  for (const [key, value] of Object.entries({ ...overview.metrics, manifest_hash: overview.manifest_hash, ledger_hash: overview.ledger_hash, headline: overview.headline })) {
    const div = document.createElement("div");
    div.className = "hash";
    div.innerHTML = `<span class="k">${key}</span><span class="v">${value}</span>`;
    grid.appendChild(div);
  }

  fillList("graphNodes", graph.nodes, (node) => `${node.kind} | <strong>${node.id}</strong> | ${node.label}`, async (node) => {
    const detail = await api(`/api/runs/${runId}/nodes/${encodeURIComponent(node.id)}`);
    $("graphNodeDetail").textContent = JSON.stringify(detail, null, 2);
  });

  fillList("timelineList", timeline.items, (item) => `${item.time.kind === "unknown" ? "unknown" : item.time.value} | ${item.type} | ${item.action} | evidence=${item.evidence_count}`);
  fillList("hypothesesList", hypotheses.items, (item) => `#${item.rank} <strong>${item.title}</strong> | confidence=${item.confidence_score} | support=${item.support_count} | contradictions=${item.contradiction_count} | status=${item.adjudication_status}`);
  fillList("evidenceList", evidence.items, (item) => `<strong>${item.evidence_id}</strong> | source=${item.source_id} | supports=${item.supports_hypotheses.join(",") || "-"}`);

  $("narrativeBox").textContent = JSON.stringify(narrative, null, 2);
  $("graphNodeDetail").textContent = "Select a node to inspect metadata, links, and contradictions.";
}

async function loadDiff() {
  if (!state.activeRunId) return;
  const baseline = $("baselineRunId").value.trim();
  const diff = await api(`/api/runs/${state.activeRunId}/diff?against_run_id=${encodeURIComponent(baseline)}`);
  $("diffBox").textContent = JSON.stringify(diff, null, 2);
}

async function init() {
  renderTabs();
  $("loadDiffBtn").onclick = loadDiff;
  const fixtures = await api("/api/fixtures");
  renderFixtures(fixtures.items || []);
}

init().catch((error) => setStatus(`Initialization error: ${error.message}`, "fail"));

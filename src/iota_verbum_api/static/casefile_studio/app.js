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

function renderFixtures(items) {
  const host = $("fixtures");
  host.innerHTML = "";
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "fixture";
    card.innerHTML = `
      <small>${item.category}</small>
      <h3>${item.title}</h3>
      <p>${item.description}</p>
      <button class="btn btn-primary" data-id="${item.id}">Run Sample</button>
    `;
    host.appendChild(card);
  }
  host.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const fixtureId = target.dataset.id || "";
    if (!fixtureId) return;
    await startSampleRun(fixtureId);
  });
}

function renderSteps(steps) {
  const host = $("steps");
  host.innerHTML = "";
  for (const step of steps || []) {
    const li = document.createElement("li");
    li.className = step.status || "pending";
    li.textContent = `${step.label} - ${step.status}`;
    host.appendChild(li);
  }
}

async function pollRun(runRequestId) {
  state.activeRunRequestId = runRequestId;
  $("runStatusText").textContent = `Run request ${runRequestId} started.`;
  let finished = false;
  while (!finished) {
    const run = await api(`/api/runs/${runRequestId}`);
    renderSteps(run.steps || []);
    $("runMeta").textContent = JSON.stringify(
      {
        status: run.status,
        current_stage: run.current_stage,
        run_id: run.run_id || "",
        source: run.source || {},
      },
      null,
      2,
    );
    if (run.status === "completed") {
      finished = true;
      state.activeRunId = run.run_id;
      $("runStatusText").textContent = `Completed: ${run.run_id}`;
      await loadWorkspace(run.run_id);
      break;
    }
    if (run.status === "failed") {
      finished = true;
      $("runStatusText").textContent = `Failed: ${run.error || "unknown error"}`;
      break;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

async function startSampleRun(fixtureId) {
  const result = await api("/api/runs/sample", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fixture_id: fixtureId }),
  });
  await pollRun(result.run_request_id);
}

async function startUploadRun(formEvent) {
  formEvent.preventDefault();
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
    li.textContent = "No items.";
    host.appendChild(li);
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.innerHTML = formatter(item);
    host.appendChild(li);
  }
}

async function loadWorkspace(runId) {
  const [summary, timeline, contradictions, unknowns, receipts, artifacts] =
    await Promise.all([
      api(`/api/runs/${runId}/summary`),
      api(`/api/runs/${runId}/timeline`),
      api(`/api/runs/${runId}/contradictions`),
      api(`/api/runs/${runId}/unknowns`),
      api(`/api/runs/${runId}/receipts`),
      api(`/api/runs/${runId}/artifacts`),
    ]);

  $("workspaceTitle").textContent = `Casefile ${summary.casefile_id}`;
  fillList("timelineList", timeline.items, (item) => {
    const time = item.time.kind === "unknown" ? "unknown time" : item.time.value;
    return `<strong>${time}</strong> | ${item.type} | ${item.action}`;
  });
  fillList("contradictionsList", contradictions.items, (item) => {
    return `<strong>${item.kind}</strong> | ${item.reason}`;
  });

  const unknownItems = []
    .concat(unknowns.world_unknowns || [])
    .concat(unknowns.required_info || []);
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

  const hashes = summary.hashes;
  const grid = $("integrityGrid");
  grid.innerHTML = "";
  for (const [key, value] of Object.entries(hashes)) {
    const div = document.createElement("div");
    div.className = "hash";
    div.innerHTML = `<span class="k">${key}</span><span class="v">${value}</span>`;
    grid.appendChild(div);
  }
  const ledger = document.createElement("div");
  ledger.className = "hash";
  ledger.innerHTML = `<span class="k">ledger_dir</span><span class="v">${summary.ledger_dir}</span>`;
  grid.appendChild(ledger);
  $("replayBox").textContent = summary.replay_command;
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
  $("replayBox").className = `mono ${ok ? "pass" : "fail"}`;
}

async function init() {
  const fixtures = await api("/api/fixtures");
  state.fixtures = fixtures.items || [];
  renderFixtures(state.fixtures);

  $("uploadForm").addEventListener("submit", startUploadRun);
  $("replayBtn").addEventListener("click", runReplay);
  $("openSampleBtn").addEventListener("click", () => {
    document.getElementById("gallerySection").scrollIntoView({ behavior: "smooth" });
  });
  $("runOwnBtn").addEventListener("click", () => {
    document.getElementById("uploadSection").scrollIntoView({ behavior: "smooth" });
  });
}

init().catch((error) => {
  $("runStatusText").textContent = `Initialization error: ${error.message}`;
});

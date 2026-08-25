const DATA_BASE_PATH = "data";

async function fetchJson(path, fallback) {
  try {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) {
      return fallback;
    }
    return await response.json();
  } catch (error) {
    console.error(`Failed to load ${path}:`, error);
    return fallback;
  }
}

function formatTimestamp(isoString) {
  if (!isoString) {
    return "-";
  }
  return new Date(isoString).toLocaleString("zh-CN", { hour12: false });
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function renderLatestStatusList(latestStatusEntries, containerId) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  if (latestStatusEntries.length === 0) {
    container.innerHTML = '<p class="empty-state">暂无监测数据，等待第一次 Actions 运行。</p>';
    return;
  }

  for (const entry of latestStatusEntries) {
    const card = document.createElement("div");
    card.className = "status-card";
    card.innerHTML = `
      <h3>${escapeHtml(entry.target)}</h3>
      <p class="status-url"><a href="${escapeHtml(entry.url)}" target="_blank" rel="noopener">${escapeHtml(entry.url)}</a></p>
      <p class="status-meta">最后检查：${formatTimestamp(entry.checked_at)}</p>
      <p class="status-content">${escapeHtml(entry.content)}</p>
    `;
    container.appendChild(card);
  }
}

function groupHistoryByTarget(historyEntries) {
  const grouped = new Map();
  for (const entry of historyEntries) {
    if (!grouped.has(entry.target)) {
      grouped.set(entry.target, []);
    }
    grouped.get(entry.target).push(entry);
  }
  for (const entries of grouped.values()) {
    entries.sort((a, b) => new Date(a.changed_at) - new Date(b.changed_at));
  }
  return grouped;
}

function renderChartCard(container, targetName, entries, seriesLabel) {
  const chartCard = document.createElement("div");
  chartCard.className = "chart-card";

  const title = document.createElement("h3");
  title.textContent = targetName;
  chartCard.appendChild(title);

  if (entries.length === 0) {
    const emptyState = document.createElement("p");
    emptyState.className = "empty-state";
    emptyState.textContent = "暂无变动记录，趋势图会在检测到第一次变动后出现。";
    chartCard.appendChild(emptyState);
    container.appendChild(chartCard);
    return;
  }

  const canvas = document.createElement("canvas");
  chartCard.appendChild(canvas);
  container.appendChild(chartCard);

  new Chart(canvas, {
    type: "line",
    data: {
      labels: entries.map((entry) => formatTimestamp(entry.changed_at)),
      datasets: [
        {
          label: seriesLabel,
          data: entries.map((_, index) => index + 1),
          borderColor: "#60a5fa",
          backgroundColor: "rgba(96, 165, 250, 0.2)",
          stepped: true,
          fill: true,
          tension: 0,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { precision: 0 },
        },
      },
    },
  });
}

function renderTrendCharts(historyEntries, latestStatusEntries, containerId, seriesLabel) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  const groupedByTarget = groupHistoryByTarget(historyEntries);
  const knownTargetNames = new Set([
    ...latestStatusEntries.map((entry) => entry.target),
    ...groupedByTarget.keys(),
  ]);

  if (knownTargetNames.size === 0) {
    container.innerHTML = '<p class="empty-state">暂无监测数据，等待第一次 Actions 运行。</p>';
    return;
  }

  for (const targetName of knownTargetNames) {
    renderChartCard(container, targetName, groupedByTarget.get(targetName) ?? [], seriesLabel);
  }
}

async function loadAndRenderSection(dataBasePath, statusContainerId, chartContainerId, seriesLabel) {
  const [latestStatusEntries, historyEntries] = await Promise.all([
    fetchJson(`${dataBasePath}/latest.json`, []),
    fetchJson(`${dataBasePath}/history.json`, []),
  ]);

  renderLatestStatusList(latestStatusEntries, statusContainerId);
  renderTrendCharts(historyEntries, latestStatusEntries, chartContainerId, seriesLabel);
}

async function init() {
  await loadAndRenderSection(DATA_BASE_PATH, "latest-status-list", "trend-charts", "累计变动次数");
  await loadAndRenderSection("data/flights", "flight-status-list", "flight-trend-charts", "累计降价提醒次数");
}

init();

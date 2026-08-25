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
  return new Date(isoString).toLocaleString("ja-JP", { hour12: false });
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
    container.innerHTML = '<p class="empty-state">監視データはまだありません。最初の Actions 実行をお待ちください。</p>';
    return;
  }

  for (const entry of latestStatusEntries) {
    const card = document.createElement("div");
    card.className = "status-card";
    card.innerHTML = `
      <h3>${escapeHtml(entry.target)}</h3>
      <p class="status-url"><a href="${escapeHtml(entry.url)}" target="_blank" rel="noopener">${escapeHtml(entry.url)}</a></p>
      <p class="status-meta">最終確認：${formatTimestamp(entry.checked_at)}</p>
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

function renderChartCard(container, targetName, entries, seriesLabel, seriesColor) {
  const chartCard = document.createElement("div");
  chartCard.className = "chart-card";

  const title = document.createElement("h3");
  title.textContent = targetName;
  chartCard.appendChild(title);

  if (entries.length === 0) {
    const emptyState = document.createElement("p");
    emptyState.className = "empty-state";
    emptyState.textContent = "変動記録はまだありません。最初の変動を検知すると推移グラフが表示されます。";
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
          borderColor: seriesColor,
          backgroundColor: `${seriesColor}33`,
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

function renderTrendCharts(historyEntries, latestStatusEntries, containerId, seriesLabel, seriesColor) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  const groupedByTarget = groupHistoryByTarget(historyEntries);
  const knownTargetNames = new Set([
    ...latestStatusEntries.map((entry) => entry.target),
    ...groupedByTarget.keys(),
  ]);

  if (knownTargetNames.size === 0) {
    container.innerHTML = '<p class="empty-state">監視データはまだありません。最初の Actions 実行をお待ちください。</p>';
    return;
  }

  for (const targetName of knownTargetNames) {
    renderChartCard(container, targetName, groupedByTarget.get(targetName) ?? [], seriesLabel, seriesColor);
  }
}

async function loadAndRenderSection(dataBasePath, statusContainerId, chartContainerId, seriesLabel, seriesColor) {
  const [latestStatusEntries, historyEntries] = await Promise.all([
    fetchJson(`${dataBasePath}/latest.json`, []),
    fetchJson(`${dataBasePath}/history.json`, []),
  ]);

  renderLatestStatusList(latestStatusEntries, statusContainerId);
  renderTrendCharts(historyEntries, latestStatusEntries, chartContainerId, seriesLabel, seriesColor);

  return latestStatusEntries;
}

function renderSummary(stockEntries, webpageEntries) {
  const allEntries = [...stockEntries, ...webpageEntries];
  const lastCheckedTimes = allEntries.map((entry) => entry.checked_at).filter(Boolean);
  const mostRecent = lastCheckedTimes.length > 0 ? lastCheckedTimes.sort().at(-1) : null;

  document.getElementById("stat-stock-count").textContent = String(stockEntries.length);
  document.getElementById("stat-webpage-count").textContent = String(webpageEntries.length);
  document.getElementById("stat-last-checked").textContent = formatTimestamp(mostRecent);
}

function initNavHighlight() {
  const sections = document.querySelectorAll("main section[id]");
  const navLinkMap = new Map();
  document.querySelectorAll(".nav-link").forEach((link) => {
    navLinkMap.set(link.dataset.nav, link);
  });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          navLinkMap.forEach((link) => link.classList.remove("active"));
          const activeLink = navLinkMap.get(entry.target.id);
          if (activeLink) activeLink.classList.add("active");
        }
      });
    },
    { rootMargin: "-40% 0px -50% 0px", threshold: 0 }
  );

  sections.forEach((section) => observer.observe(section));
}

async function init() {
  initNavHighlight();

  const stockEntries = await loadAndRenderSection(
    "data/stocks",
    "stock-status-list",
    "stock-trend-charts",
    "累計最安値更新回数",
    "#34d399"
  );
  const webpageEntries = await loadAndRenderSection(
    DATA_BASE_PATH,
    "latest-status-list",
    "trend-charts",
    "累計変動回数",
    "#7c8aa8"
  );

  renderSummary(stockEntries, webpageEntries);
}

init();

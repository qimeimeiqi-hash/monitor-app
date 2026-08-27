// トップページ（docs/index.html）専用のロジック。
// 「株価」「K線シグナル」は銘柄ごとの詳細を stock-detail.html / kline-detail.html に切り出し、
// ここでは一覧性を保つため、銘柄カード（名称・現在値・ミニグラフ）だけを並べる。

const DATA_BASE_PATH = "data";
const STOCK_MINI_CHART_COLOR = "#34d399";
const KLINE_MINI_CHART_COLOR = "#7c8aa8";
const KLINE_MINI_CANDLE_COUNT = 30;

function renderOverviewGridEmptyState(container) {
  container.innerHTML = '<p class="empty-state">監視データはまだありません。最初の Actions 実行をお待ちください。</p>';
}

function appendMiniChartOrNote(card, values, seriesColor, emptyNoteText) {
  if (values.length < 2) {
    const note = document.createElement("p");
    note.className = "overview-card-note";
    note.textContent = emptyNoteText;
    card.appendChild(note);
    return;
  }
  const chartWrap = document.createElement("div");
  chartWrap.className = "mini-chart-wrap";
  const canvas = document.createElement("canvas");
  chartWrap.appendChild(canvas);
  card.appendChild(chartWrap);
  renderMiniLineChart(canvas, values, seriesColor);
}

function renderStockOverviewGrid(latestStatusEntries, historyEntries, containerId) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  if (latestStatusEntries.length === 0) {
    renderOverviewGridEmptyState(container);
    return;
  }

  const groupedByTarget = groupHistoryByTarget(historyEntries);

  for (const entry of latestStatusEntries) {
    const card = document.createElement("a");
    card.className = "overview-card";
    card.href = `stock-detail.html?id=${encodeURIComponent(entry.id)}`;
    card.innerHTML = `
      <h3>${escapeHtml(entry.target)}</h3>
      <p class="overview-card-content">${escapeHtml(entry.content)}</p>
    `;

    const newLowCounts = (groupedByTarget.get(entry.target) ?? []).map((_, index) => index + 1);
    appendMiniChartOrNote(card, newLowCounts, STOCK_MINI_CHART_COLOR, "2か月最安値の更新記録はまだありません");

    container.appendChild(card);
  }
}

async function renderKlineOverviewGrid(latestStatusEntries, historyEntries, containerId) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  if (latestStatusEntries.length === 0) {
    renderOverviewGridEmptyState(container);
    return;
  }

  const groupedByTarget = groupHistoryByTarget(historyEntries);

  for (const entry of latestStatusEntries) {
    const card = document.createElement("a");
    card.className = "overview-card";
    card.href = `kline-detail.html?id=${encodeURIComponent(entry.id)}`;

    const targetHistory = groupedByTarget.get(entry.target) ?? [];
    const latestSignal = targetHistory.length > 0 ? targetHistory[targetHistory.length - 1] : null;
    const badgeHtml = latestSignal
      ? `<span class="signal-badge ${latestSignal.action}">${latestSignal.action === "buy" ? "買い" : "売り"}</span>`
      : "";

    card.innerHTML = `
      <div class="overview-card-header">
        <h3>${escapeHtml(entry.target)}</h3>
        ${badgeHtml}
      </div>
      <p class="overview-card-content">${escapeHtml(entry.content)}</p>
    `;

    const candles = await fetchJson(`data/kline/candles/${entry.id}.json`, []);
    const recentCloses = candles.slice(-KLINE_MINI_CANDLE_COUNT).map((candle) => candle.close);
    appendMiniChartOrNote(card, recentCloses, KLINE_MINI_CHART_COLOR, "価格データはまだありません");

    container.appendChild(card);
  }
}

async function loadAndRenderStockOverview() {
  const [latestStatusEntries, historyEntries] = await Promise.all([
    fetchJson("data/stocks/latest.json", []),
    fetchJson("data/stocks/history.json", []),
  ]);
  renderStockOverviewGrid(latestStatusEntries, historyEntries, "stock-overview-grid");
  return latestStatusEntries;
}

async function loadAndRenderKlineOverview() {
  const [latestStatusEntries, historyEntries] = await Promise.all([
    fetchJson("data/kline/latest.json", []),
    fetchJson("data/kline/history.json", []),
  ]);
  await renderKlineOverviewGrid(latestStatusEntries, historyEntries, "kline-overview-grid");
  return latestStatusEntries;
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

async function loadAndRenderWebpageSection() {
  const [latestStatusEntries, historyEntries] = await Promise.all([
    fetchJson(`${DATA_BASE_PATH}/latest.json`, []),
    fetchJson(`${DATA_BASE_PATH}/history.json`, []),
  ]);

  renderLatestStatusList(latestStatusEntries, "latest-status-list");
  renderTrendCharts(historyEntries, latestStatusEntries, "trend-charts", "累計変動回数", "#7c8aa8");

  return latestStatusEntries;
}

function renderSummary(stockEntries, klineEntries, webpageEntries) {
  const allEntries = [...stockEntries, ...klineEntries, ...webpageEntries];
  const lastCheckedTimes = allEntries.map((entry) => entry.checked_at).filter(Boolean);
  const mostRecent = lastCheckedTimes.length > 0 ? lastCheckedTimes.sort().at(-1) : null;

  // 株価（2か月最安値）とK線シグナルは対象銘柄が重なるため、名称で重複を除いた
  // 銘柄数（＝実際に監視している銘柄の種類数）を表示する。
  const uniqueStockNames = new Set([
    ...stockEntries.map((entry) => entry.target),
    ...klineEntries.map((entry) => entry.target),
  ]);

  document.getElementById("stat-stock-count").textContent = String(uniqueStockNames.size);
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

  const stockEntries = await loadAndRenderStockOverview();
  const klineEntries = await loadAndRenderKlineOverview();
  const webpageEntries = await loadAndRenderWebpageSection();

  renderSummary(stockEntries, klineEntries, webpageEntries);
}

init();

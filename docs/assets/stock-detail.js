// 株価（2か月最安値監視）の銘柄別詳細ページ。URL の ?id= で対象銘柄を指定する。

function renderStockDetailNotFound() {
  document.getElementById("detail-header").innerHTML =
    '<p class="empty-state">指定された銘柄が見つかりませんでした。<a href="index.html#stocks">一覧に戻る</a></p>';
}

function renderStockDetailHeader(entry) {
  const header = document.getElementById("detail-header");
  header.innerHTML = `
    <h1>${escapeHtml(entry.target)}</h1>
    <p class="status-url"><a href="${escapeHtml(entry.url)}" target="_blank" rel="noopener">${escapeHtml(entry.url)}</a></p>
    <p class="status-meta">最終確認：${formatTimestamp(entry.checked_at)}</p>
    <p class="detail-current-value">${escapeHtml(entry.content)}</p>
  `;
}

function renderNewLowEventList(targetHistory, containerId) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  if (targetHistory.length === 0) {
    container.innerHTML = '<p class="empty-state">2か月最安値の更新記録はまだありません。</p>';
    return;
  }

  const sortedEntries = [...targetHistory].sort((a, b) => new Date(b.changed_at) - new Date(a.changed_at));

  for (const entry of sortedEntries) {
    const card = document.createElement("div");
    card.className = "signal-card";
    card.innerHTML = `
      <p class="status-meta">${formatTimestamp(entry.changed_at)}</p>
      <p class="status-content">${escapeHtml(entry.new_value)}</p>
      <p class="signal-stop-loss">更新前の最安値：${escapeHtml(entry.old_value)}</p>
    `;
    container.appendChild(card);
  }
}

async function initStockDetailPage() {
  const stockId = getQueryParam("id");
  const [latestStatusEntries, historyEntries] = await Promise.all([
    fetchJson("data/stocks/latest.json", []),
    fetchJson("data/stocks/history.json", []),
  ]);

  const entry = latestStatusEntries.find((candidate) => candidate.id === stockId);
  if (!entry) {
    renderStockDetailNotFound();
    return;
  }

  renderStockDetailHeader(entry);

  const targetHistory = groupHistoryByTarget(historyEntries).get(entry.target) ?? [];

  const chartContainer = document.getElementById("detail-trend-chart");
  chartContainer.innerHTML = "";
  renderChartCard(chartContainer, entry.target, targetHistory, "累計最安値更新回数", "#34d399");

  renderNewLowEventList(targetHistory, "detail-event-list");
}

initStockDetailPage();

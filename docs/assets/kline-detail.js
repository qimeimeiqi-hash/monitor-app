// K線売買シグナルの銘柄別詳細ページ。URL の ?id= で対象銘柄を指定する。

function renderKlineDetailNotFound() {
  document.getElementById("detail-header").innerHTML =
    '<p class="empty-state">指定された銘柄が見つかりませんでした。<a href="index.html#kline">一覧に戻る</a></p>';
}

function renderKlineDetailHeader(entry) {
  const header = document.getElementById("detail-header");
  header.innerHTML = `
    <h1>${escapeHtml(entry.target)}</h1>
    <p class="status-url"><a href="${escapeHtml(entry.url)}" target="_blank" rel="noopener">${escapeHtml(entry.url)}</a></p>
    <p class="status-meta">最終確認：${formatTimestamp(entry.checked_at)}</p>
    <p class="detail-current-value">${escapeHtml(entry.content)}</p>
  `;
}

async function initKlineDetailPage() {
  const stockId = getQueryParam("id");
  const [latestStatusEntries, historyEntries] = await Promise.all([
    fetchJson("data/kline/latest.json", []),
    fetchJson("data/kline/history.json", []),
  ]);

  const entry = latestStatusEntries.find((candidate) => candidate.id === stockId);
  if (!entry) {
    renderKlineDetailNotFound();
    return;
  }

  renderKlineDetailHeader(entry);

  const candles = await fetchJson(`data/kline/candles/${entry.id}.json`, []);
  const chartContainer = document.getElementById("detail-candle-chart");
  chartContainer.innerHTML = "";
  renderCandlestickChartCard(chartContainer, entry.target, candles);

  const targetHistory = groupHistoryByTarget(historyEntries).get(entry.target) ?? [];
  renderSignalHistory(targetHistory, "detail-signal-history");
}

initKlineDetailPage();

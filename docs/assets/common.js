// 全ページ（index / stock-detail / kline-detail）で共有するユーティリティとレンダリング関数。

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

function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
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

function computeSimpleMovingAverage(values, window) {
  return values.map((_, index) => {
    if (index < window - 1) {
      return null;
    }
    const windowSlice = values.slice(index - window + 1, index + 1);
    return windowSlice.reduce((sum, value) => sum + value, 0) / window;
  });
}

function renderSignalHistory(historyEntries, containerId) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  if (historyEntries.length === 0) {
    container.innerHTML = '<p class="empty-state">シグナル履歴はまだありません。買い/売りシグナルが発生すると表示されます。</p>';
    return;
  }

  const sortedEntries = [...historyEntries].sort((a, b) => new Date(b.changed_at) - new Date(a.changed_at));

  for (const entry of sortedEntries) {
    const card = document.createElement("div");
    card.className = "signal-card";
    const actionLabel = entry.action === "buy" ? "買い" : "売り";
    const reasonsHtml = entry.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("");
    const stopLossHtml = entry.stop_loss_label
      ? `<p class="signal-stop-loss">損切りライン：${escapeHtml(entry.stop_loss_label)}</p>`
      : "";
    card.innerHTML = `
      <div class="signal-card-header">
        <span class="signal-badge ${entry.action}">${actionLabel}</span>
        <h3>${escapeHtml(entry.target)}</h3>
      </div>
      <p class="status-meta">${formatTimestamp(entry.changed_at)}</p>
      <p class="status-content">${escapeHtml(entry.price_label)}</p>
      <ul class="signal-reasons">${reasonsHtml}</ul>
      ${stopLossHtml}
    `;
    container.appendChild(card);
  }
}

const CANDLESTICK_DISPLAY_COUNT = 60;

function renderCandlestickChartCard(container, targetName, candles) {
  const chartCard = document.createElement("div");
  chartCard.className = "chart-card candle-chart-card";

  const title = document.createElement("h3");
  title.textContent = targetName;
  chartCard.appendChild(title);

  if (candles.length === 0) {
    const emptyState = document.createElement("p");
    emptyState.className = "empty-state";
    emptyState.textContent = "ローソク足データはまだありません。";
    chartCard.appendChild(emptyState);
    container.appendChild(chartCard);
    return;
  }

  // SMA is computed over the full history so it stays accurate at the edge of
  // the displayed window, then only the trailing window is actually rendered
  // (showing all ~6 months of daily candles in one fixed-width card would
  // squeeze each candle into an unreadable sliver).
  const closes = candles.map((candle) => candle.close);
  const sma20Full = computeSimpleMovingAverage(closes, 20);
  const sma60Full = computeSimpleMovingAverage(closes, 60);

  const visibleCandles = candles.slice(-CANDLESTICK_DISPLAY_COUNT);
  const sma20 = sma20Full.slice(-CANDLESTICK_DISPLAY_COUNT);
  const sma60 = sma60Full.slice(-CANDLESTICK_DISPLAY_COUNT);

  const canvasWrap = document.createElement("div");
  canvasWrap.className = "candle-chart-canvas-wrap";
  const canvas = document.createElement("canvas");
  canvasWrap.appendChild(canvas);
  chartCard.appendChild(canvasWrap);
  container.appendChild(chartCard);

  const bullishColor = "#34d399";
  const bearishColor = "#f87171";

  new Chart(canvas, {
    type: "bar",
    data: {
      labels: visibleCandles.map((candle) => candle.date),
      datasets: [
        {
          label: "値幅",
          data: visibleCandles.map((candle) => [candle.low, candle.high]),
          backgroundColor: visibleCandles.map((candle) => (candle.close >= candle.open ? bullishColor : bearishColor)),
          barPercentage: 0.2,
          categoryPercentage: 0.9,
          grouped: false,
        },
        {
          label: "実体",
          data: visibleCandles.map((candle) => [Math.min(candle.open, candle.close), Math.max(candle.open, candle.close)]),
          backgroundColor: visibleCandles.map((candle) => (candle.close >= candle.open ? bullishColor : bearishColor)),
          barPercentage: 0.7,
          categoryPercentage: 0.9,
          grouped: false,
        },
        {
          label: "SMA20",
          type: "line",
          data: sma20,
          borderColor: "#7c8aa8",
          pointRadius: 0,
          borderWidth: 1.5,
        },
        {
          label: "SMA60",
          type: "line",
          data: sma60,
          borderColor: "#f4b860",
          pointRadius: 0,
          borderWidth: 1.5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: { display: false },
        y: { beginAtZero: false },
      },
    },
  });
}

// 一覧ページのカードに埋め込む、軸なしの小型トレンドグラフ。
function renderMiniLineChart(canvas, values, seriesColor) {
  new Chart(canvas, {
    type: "line",
    data: {
      labels: values.map((_, index) => index),
      datasets: [
        {
          data: values,
          borderColor: seriesColor,
          backgroundColor: `${seriesColor}22`,
          fill: true,
          tension: 0.15,
          pointRadius: 0,
          borderWidth: 1.5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
      },
      scales: {
        x: { display: false },
        y: { display: false },
      },
    },
  });
}

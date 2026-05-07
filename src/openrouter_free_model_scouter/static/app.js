let allModels = [];
let eventsModalOffset = 0;
let healthEventsOffset = 0;

const fullDateTimeFormatter = new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZoneName: 'short'
});
const timeFormatter = new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit'
});
const monthDayFormatter = new Intl.DateTimeFormat(undefined, {
    month: 'numeric',
    day: 'numeric'
});
const dateFormatter = new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric'
});

function parseServerTimestamp(value) {
    if (!value) return null;
    const text = String(value).trim();
    const normalized = text.includes('T') ? text : text.replace(' ', 'T');
    const date = new Date(normalized);
    return Number.isNaN(date.getTime()) ? null : date;
}

function formatBrowserDateTime(value) {
    const date = parseServerTimestamp(value);
    return date ? fullDateTimeFormatter.format(date) : String(value || '-');
}

function formatChartAxisTime(value, period) {
    const date = parseServerTimestamp(value);
    if (!date) return value;
    if (period === '1d') return timeFormatter.format(date);
    if (period === '1y') return `${dateFormatter.format(date)}`;
    return `${monthDayFormatter.format(date)}\n${timeFormatter.format(date)}`;
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function eventTitle(event) {
    const labels = {
        MODEL_ADDED: 'Model added',
        MODEL_REMOVED: 'Model removed',
        MODEL_DEGRADED: 'Degraded',
        MODEL_RECOVERED: 'Recovered',
        MODEL_RATE_LIMITED: 'Rate limited',
        MODEL_FLAPPING: 'Flapping'
    };
    return labels[event.event_type] || event.event_type;
}

function eventMarker(event) {
    const markers = {
        MODEL_ADDED: '+',
        MODEL_REMOVED: '-',
        MODEL_DEGRADED: '!',
        MODEL_RECOVERED: 'OK',
        MODEL_RATE_LIMITED: '429',
        MODEL_FLAPPING: '~'
    };
    return markers[event.event_type] || '*';
}

function eventBadgeClasses(event) {
    if (event.severity === 'high') return 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200';
    if (event.severity === 'medium') return 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200';
    return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200';
}

document.addEventListener('DOMContentLoaded', () => {
    fetchSummary();
    fetchModels();
    fetchImportantEvents();

    // Search handler
    document.getElementById('searchInput').addEventListener('input', filterModels);

    // Close modal handlers
    document.getElementById('modal-close').addEventListener('click', closeModal);
    document.getElementById('modal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('modal')) closeModal();
    });
    document.getElementById('events-view-all').addEventListener('click', openEventsModal);
    document.getElementById('events-modal-close').addEventListener('click', closeEventsModal);
    document.getElementById('events-modal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('events-modal')) closeEventsModal();
    });
    document.getElementById('events-modal-load-more').addEventListener('click', loadMoreImportantEvents);
    document.getElementById('health-events-load-more').addEventListener('click', loadMoreHealthEvents);
});

function sortModels(models) {
    models.sort((a, b) => {
        // 1. Uptime descending
        if (a.uptime_24h !== b.uptime_24h) {
            return b.uptime_24h - a.uptime_24h;
        }
        // 2. Latency ascending (null as infinity)
        const latA = a.avg_latency_24h !== null ? a.avg_latency_24h : Infinity;
        const latB = b.avg_latency_24h !== null ? b.avg_latency_24h : Infinity;
        if (latA !== latB) {
            return latA - latB;
        }
        // 3. Model ID ascending
        return a.model_id.localeCompare(b.model_id);
    });
    return models;
}

function filterModels() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const filtered = allModels.filter(model => model.model_id.toLowerCase().includes(searchTerm));
    renderModels(filtered);
}

function copyToClipboard(text, btnElement) {
    const onSuccess = () => {
        const originalContent = btnElement.innerHTML;
        btnElement.innerHTML = '✅';
        setTimeout(() => {
            btnElement.innerHTML = originalContent;
        }, 1500);
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(onSuccess).catch(err => {
            console.error('Failed to copy: ', err);
        });
    } else {
        // Fallback for non-HTTPS environments
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "absolute";
        textArea.style.left = "-999999px";
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            onSuccess();
        } catch (err) {
            console.error('Failed to copy (fallback): ', err);
        } finally {
            textArea.remove();
        }
    }
}

async function fetchSummary() {
    try {
        const res = await fetch('/api/summary');
        const data = await res.json();

        document.getElementById('summary-total').textContent = data.total_models;
        document.getElementById('summary-healthy').textContent = data.healthy_count;
        document.getElementById('summary-degraded').textContent = data.degraded_count;
        document.getElementById('summary-down').textContent = data.down_count;
        if (data.last_updated) {
            document.getElementById('last-updated').textContent = `Last updated: ${formatBrowserDateTime(data.last_updated)}`;
        } else {
            document.getElementById('last-updated').textContent = 'Last updated: Never';
        }
    } catch (err) {
        console.error('Failed to fetch summary:', err);
    }
}

async function fetchModels() {
    try {
        const res = await fetch('/api/models');
        const data = await res.json();
        allModels = data;
        sortModels(allModels);
        filterModels();
    } catch (err) {
        console.error('Failed to fetch models:', err);
    }
}

async function fetchImportantEvents() {
    try {
        const res = await fetch('/api/events?type=important&period=30d&limit=5');
        const data = await res.json();
        renderEventList(
            document.getElementById('important-events-list'),
            data.items || [],
            'No free-model list changes recorded in the last 30 days.'
        );
    } catch (err) {
        console.error('Failed to fetch important events:', err);
    }
}

function renderEventList(container, events, emptyMessage, append = false) {
    if (!append) container.innerHTML = '';
    if (!events.length && !append) {
        container.innerHTML = `<div class="p-6 text-sm text-gray-500 dark:text-gray-400">${escapeHtml(emptyMessage)}</div>`;
        return;
    }

    events.forEach(event => {
        const row = document.createElement('button');
        row.type = 'button';
        row.className = 'w-full text-left px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition';
        row.addEventListener('click', () => {
            if (!document.getElementById('events-modal').classList.contains('hidden')) {
                closeEventsModal();
            }
            openHistory(event.model_id);
        });
        const transition = event.old_value || event.new_value
            ? `<div class="text-xs text-gray-400 mt-1">${escapeHtml(event.old_value || 'none')} -> ${escapeHtml(event.new_value || 'none')}</div>`
            : '';
        row.innerHTML = `
            <div class="flex items-start gap-3">
                <span class="shrink-0 inline-flex items-center justify-center w-9 h-9 rounded ${eventBadgeClasses(event)} text-xs font-bold">${escapeHtml(eventMarker(event))}</span>
                <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-2">
                        <span class="font-semibold text-gray-900 dark:text-gray-100">${escapeHtml(eventTitle(event))}</span>
                        <span class="text-xs uppercase tracking-wide text-gray-400">${escapeHtml(event.severity)}</span>
                    </div>
                    <div class="text-sm text-gray-600 dark:text-gray-300 truncate">${escapeHtml(event.model_id)}</div>
                    <div class="text-sm text-gray-500 dark:text-gray-400">${escapeHtml(event.message)}</div>
                    ${transition}
                </div>
                <time class="shrink-0 text-xs text-gray-400">${escapeHtml(formatBrowserDateTime(event.event_datetime))}</time>
            </div>
        `;
        container.appendChild(row);
    });
}

async function openEventsModal() {
    eventsModalOffset = 0;
    document.getElementById('events-modal').classList.remove('hidden');
    document.getElementById('events-modal-list').innerHTML = '';
    await loadMoreImportantEvents();
}

function closeEventsModal() {
    document.getElementById('events-modal').classList.add('hidden');
}

async function loadMoreImportantEvents() {
    try {
        const res = await fetch(`/api/events?type=important&period=30d&limit=20&offset=${eventsModalOffset}`);
        const data = await res.json();
        renderEventList(
            document.getElementById('events-modal-list'),
            data.items || [],
            'No free-model list changes recorded in the last 30 days.',
            eventsModalOffset > 0
        );
        eventsModalOffset = data.next_offset || eventsModalOffset;
        document.getElementById('events-modal-load-more').classList.toggle('hidden', !data.has_more);
    } catch (err) {
        console.error('Failed to fetch more important events:', err);
    }
}

function renderModels(models) {
    const tbody = document.getElementById('models-tbody');
    tbody.innerHTML = '';

    models.forEach(model => {
        const tr = document.createElement('tr');
        tr.className = "hover:bg-gray-100 dark:hover:bg-gray-700 transition";

        // Determine status class
        let statusClass = "text-gray-500";
        let statusIcon = "UNKNOWN";

        // Status Indicators logic update
        if (model.uptime_24h >= 90) {
            statusClass = "text-green-500 font-bold";
            statusIcon = "🟢 OK";
        } else if (model.uptime_24h >= 50) {
            statusClass = "text-yellow-500 font-bold";
            statusIcon = "🟡 UNSTABLE";
        } else {
            statusClass = "text-red-500 font-bold";
            statusIcon = "🔴 DOWN";
        }

        // Keep old status icon if detailed status is needed, but requirement said "Status Indicators"
        // Let's append the detailed status label for clarity if it differs significantly
        // or just stick to the new requirement. The requirement says:
        // "🟢 Normal (Uptime 90%+)", "🟡 Unstable (50-89%)", "🔴 Down (<50%)"
        // I will use these.

        tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100 flex items-center">
                ${model.model_id}
                <button onclick="copyToClipboard('${model.model_id}', this)" class="ml-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition" title="Copy Model ID">📋</button>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm ${statusClass}">${statusIcon} <span class="text-xs font-normal text-gray-400">(${model.latest_status})</span></td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${model.uptime_24h.toFixed(1)}%</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${model.avg_latency_24h ? Math.round(model.avg_latency_24h) + ' ms' : '-'}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${createSparkline(model.sparkline_data)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${model.consecutive_failures}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                <button onclick="openHistory('${model.model_id}')" class="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-200 font-semibold">History</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

let chartInstance = null;

// Expose to window for onclick handler
window.openHistory = async function(modelId, period = '1d') {
    const modal = document.getElementById('modal');
    const title = document.getElementById('modal-title');
    const chartContainer = document.getElementById('chart-container');

    // Save state
    window.currentModelId = modelId;
    window.currentPeriod = period;

    // Update button UI
    document.querySelectorAll('.period-btn').forEach(btn => {
        if (btn.getAttribute('data-period') === period) {
            btn.classList.add('bg-blue-600', 'text-white');
            btn.classList.remove('bg-gray-200', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-200');
        } else {
            btn.classList.remove('bg-blue-600', 'text-white');
            btn.classList.add('bg-gray-200', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-200');
        }
    });

    title.textContent = `History: ${modelId} (${period})`;
    modal.classList.remove('hidden');

    // Clear previous chart
    if (chartInstance) {
        chartInstance.dispose();
    }
    chartInstance = echarts.init(chartContainer);
    chartInstance.showLoading();

    try {
        const res = await fetch(`/api/models/${modelId}/history?period=${period}`);
        if (!res.ok) throw new Error('Failed to fetch history');
        const history = await res.json();

        renderChart(history);
        resetHealthEvents();
        await loadMoreHealthEvents();
    } catch (err) {
        console.error(err);
        chartInstance.hideLoading();
        chartContainer.innerText = "Error loading history.";
    }
}

function resetHealthEvents() {
    healthEventsOffset = 0;
    document.getElementById('health-events-list').innerHTML = '';
    document.getElementById('health-events-load-more').classList.add('hidden');
}

async function loadMoreHealthEvents() {
    if (!window.currentModelId) return;
    const params = new URLSearchParams({
        type: 'health',
        period: '30d',
        limit: '10',
        offset: String(healthEventsOffset),
        model_id: window.currentModelId
    });
    try {
        const res = await fetch(`/api/events?${params.toString()}`);
        const data = await res.json();
        renderEventList(
            document.getElementById('health-events-list'),
            data.items || [],
            'No health events recorded for this model in the last 30 days.',
            healthEventsOffset > 0
        );
        healthEventsOffset = data.next_offset || healthEventsOffset;
        document.getElementById('health-events-load-more').classList.toggle('hidden', !data.has_more);
    } catch (err) {
        console.error('Failed to fetch health events:', err);
    }
}

function renderChart(history) {
    chartInstance.hideLoading();

    const dates = history.map(h => h.run_datetime);

    let successes = 0;
    const dataLatency = [];
    const dataUptime = [];

    history.forEach((h, i) => {
        if (h.ok) successes++;
        // Calculate cumulative uptime
        const uptime = (successes / (i + 1)) * 100;
        dataUptime.push(uptime.toFixed(1));

        let color = '#10B981'; // green
        if (!h.ok) {
             if (h.status_label === '429') color = '#F59E0B'; // yellow
             else color = '#EF4444'; // red
        }
        dataLatency.push({
            value: h.latency_ms || 0,
            itemStyle: { color: color },
            status: h.status_label,
            date: formatBrowserDateTime(h.run_datetime)
        });
    });

    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            formatter: function (params) {
                if (!params || !params.length) return '';
                const point = history[params[0].dataIndex];
                const lines = [`<strong>${formatBrowserDateTime(point.run_datetime)}</strong>`];
                params.forEach(item => {
                    if (item.seriesName === 'Latency') {
                        const latency = point.latency_ms == null ? '-' : `${point.latency_ms} ms`;
                        lines.push(`${item.marker}${item.seriesName}: ${latency} (${point.status_label})`);
                    } else {
                        lines.push(`${item.marker}${item.seriesName}: ${item.value}%`);
                    }
                });
                return lines.join('<br/>');
            }
        },
        legend: {
            data: ['Latency', 'Uptime'],
            textStyle: { color: '#9CA3AF' }
        },
        xAxis: {
            type: 'category',
            data: dates,
            axisLabel: {
                 formatter: function (value) {
                     return formatChartAxisTime(value, window.currentPeriod);
                 }
            }
        },
        yAxis: [
            {
                type: 'value',
                name: 'Latency (ms)',
                position: 'left',
                axisLine: { show: true, lineStyle: { color: '#9CA3AF' } }
            },
            {
                type: 'value',
                name: 'Uptime (%)',
                min: 0,
                max: 100,
                position: 'right',
                axisLine: { show: true, lineStyle: { color: '#9CA3AF' } },
                splitLine: { show: false }
            }
        ],
        series: [
            {
                name: 'Latency',
                data: dataLatency,
                type: 'bar',
                yAxisIndex: 0
            },
            {
                name: 'Uptime',
                data: dataUptime,
                type: 'line',
                yAxisIndex: 1,
                itemStyle: { color: '#8B5CF6' }, // purple line
                smooth: true
            }
        ]
    };

    chartInstance.setOption(option);

    // Resize chart on window resize
    window.addEventListener('resize', () => {
        if(chartInstance) chartInstance.resize();
    });
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
    resetHealthEvents();
    if (chartInstance) {
        chartInstance.dispose();
        chartInstance = null;
    }
}

function createSparkline(data) {
    if (!data || data.length === 0) return '-';
    const width = 100;
    const height = 24;
    const barWidth = Math.max(1, Math.floor(width / data.length) - 1);
    
    const validData = data.filter(d => d !== null);
    const maxVal = validData.length > 0 ? Math.max(...validData) : 100;
    
    let svg = `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" class="overflow-visible inline-block">`;
    data.forEach((val, i) => {
        const x = i * (width / Math.max(1, data.length));
        if (val === null) {
            svg += `<rect x="${x}" y="${height - 2}" width="${barWidth}" height="2" fill="#EF4444"></rect>`;
        } else {
            const h = Math.max(2, (val / maxVal) * height);
            const y = height - h;
            svg += `<rect x="${x}" y="${y}" width="${barWidth}" height="${h}" fill="#3B82F6" opacity="0.7"></rect>`;
        }
    });
    svg += `</svg>`;
    return svg;
}

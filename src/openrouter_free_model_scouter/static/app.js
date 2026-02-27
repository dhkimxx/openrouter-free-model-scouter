let allModels = [];

document.addEventListener('DOMContentLoaded', () => {
    fetchSummary();
    fetchModels();

    // Search handler
    document.getElementById('searchInput').addEventListener('input', filterModels);

    // Close modal handlers
    document.getElementById('modal-close').addEventListener('click', closeModal);
    document.getElementById('modal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('modal')) closeModal();
    });
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
    navigator.clipboard.writeText(text).then(() => {
        const originalContent = btnElement.innerHTML;
        btnElement.innerHTML = '✅';
        setTimeout(() => {
            btnElement.innerHTML = originalContent;
        }, 1500);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}

async function fetchSummary() {
    try {
        const res = await fetch('/api/summary');
        const data = await res.json();

        document.getElementById('summary-total').textContent = data.total_models;
        document.getElementById('summary-healthy').textContent = data.healthy_count;
        document.getElementById('summary-degraded').textContent = data.degraded_count;
        document.getElementById('summary-down').textContent = data.down_count;
        document.getElementById('last-updated').textContent = `Last updated: ${data.last_updated || 'Never'}`;
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
window.openHistory = async function(modelId) {
    const modal = document.getElementById('modal');
    const title = document.getElementById('modal-title');
    const chartContainer = document.getElementById('chart-container');

    title.textContent = `History: ${modelId}`;
    modal.classList.remove('hidden');

    // Clear previous chart
    if (chartInstance) {
        chartInstance.dispose();
    }
    chartInstance = echarts.init(chartContainer);
    chartInstance.showLoading();

    try {
        // Handle modelId with slashes by URL encoding or relying on path handling
        // If modelId is "google/gemma", URL becomes "/api/models/google/gemma/history"
        // This is valid path for our router.

        const res = await fetch(`/api/models/${modelId}/history`);
        if (!res.ok) throw new Error('Failed to fetch history');
        const history = await res.json();

        renderChart(history);
    } catch (err) {
        console.error(err);
        chartInstance.hideLoading();
        chartContainer.innerText = "Error loading history.";
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
            date: h.run_datetime
        });
    });

    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' }
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
                     try {
                         const d = new Date(value);
                         if (!isNaN(d.getTime())) {
                            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                         }
                         return value.split(' ')[1] || value;
                     } catch(e) { return value; }
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

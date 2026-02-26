document.addEventListener('DOMContentLoaded', () => {
    fetchSummary();
    fetchModels();

    // Close modal handlers
    document.getElementById('modal-close').addEventListener('click', closeModal);
    document.getElementById('modal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('modal')) closeModal();
    });
});

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
        renderModels(data);
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
        if (model.latest_status === "OK") {
            statusClass = "text-green-500 font-bold";
            statusIcon = "✅ OK";
        } else if (model.latest_status === "429") {
            statusClass = "text-yellow-500 font-bold";
            statusIcon = "⚠️ 429";
        } else if (model.latest_status.startsWith("HTTP")) {
            statusClass = "text-orange-500 font-bold";
            statusIcon = `⚠️ ${model.latest_status}`;
        } else if (model.latest_status === "FAIL") {
            statusClass = "text-red-500 font-bold";
            statusIcon = "❌ FAIL";
        } else {
            statusClass = "text-gray-400";
            statusIcon = model.latest_status;
        }

        tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">${model.model_id}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm ${statusClass}">${statusIcon}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${model.uptime_24h.toFixed(1)}%</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${model.avg_latency_24h ? Math.round(model.avg_latency_24h) + ' ms' : '-'}</td>
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

    const data = history.map(h => {
        let color = '#10B981'; // green
        if (!h.ok) {
             if (h.status_label === '429') color = '#F59E0B'; // yellow
             else color = '#EF4444'; // red
        }
        return {
            value: h.latency_ms || 0,
            itemStyle: { color: color },
            status: h.status_label,
            date: h.run_datetime
        };
    });

    const option = {
        tooltip: {
            trigger: 'axis',
            formatter: function (params) {
                const item = params[0].data;
                return `${item.date}<br/>Status: <b>${item.status}</b><br/>Latency: ${item.value} ms`;
            }
        },
        xAxis: {
            type: 'category',
            data: dates,
            axisLabel: {
                 formatter: function (value) {
                     // Try to format date
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
        yAxis: {
            type: 'value',
            name: 'Latency (ms)'
        },
        series: [
            {
                data: data,
                type: 'bar',
                name: 'Latency'
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

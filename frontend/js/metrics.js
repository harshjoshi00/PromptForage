/**
 * Metrics Dashboard — renders evaluation results and cost/quality analysis.
 */

const MetricsDashboard = {
    /**
     * Render the full metrics dashboard.
     * @param {HTMLElement} container - Container element.
     * @param {object} pipelineData - Pipeline execution data.
     * @param {object} costData - Cost/token data.
     * @param {object} runtimeData - Runtime simulation data.
     */
    renderPipelineMetrics(container, pipelineData, costData, runtimeData) {
        if (!pipelineData && !costData) {
            container.innerHTML = '<p style="color: var(--text-muted); padding: 20px;">No metrics available yet.</p>';
            return;
        }

        let html = '';

        // --- Overview Cards ---
        html += '<div class="metrics-grid">';

        if (costData) {
            html += this._metricCard(costData.total_calls || 0, 'LLM Calls', '');
            html += this._metricCard(costData.repair_calls || 0, 'Repair Calls', costData.repair_calls > 0 ? 'warning' : 'success');
            html += this._metricCard(this._formatTokens(costData.total_tokens || 0), 'Total Tokens', '');
            html += this._metricCard(`$${(costData.total_cost_usd || 0).toFixed(4)}`, 'Total Cost', '');
        }

        if (pipelineData) {
            const latency = (pipelineData.total_latency_ms || 0) / 1000;
            html += this._metricCard(`${latency.toFixed(1)}s`, 'Total Latency', '');
        }

        if (runtimeData) {
            const execStatus = runtimeData.is_executable ? '✅ Yes' : '❌ No';
            html += this._metricCard(execStatus, 'Executable', runtimeData.is_executable ? 'success' : 'danger');
        }

        html += '</div>';

        // --- Per-Stage Breakdown ---
        if (pipelineData && pipelineData.stages) {
            html += '<h3 style="color: var(--text-secondary); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 20px 0 12px;">Pipeline Stages</h3>';
            html += '<table style="width: 100%; border-collapse: collapse;">';
            html += '<thead><tr>';
            html += '<th style="text-align:left;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Stage</th>';
            html += '<th style="text-align:center;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Status</th>';
            html += '<th style="text-align:right;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Errors</th>';
            html += '<th style="text-align:right;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Repairs</th>';
            html += '<th style="text-align:right;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Latency</th>';
            html += '</tr></thead><tbody>';

            const stageLabels = {
                'stage_1_lexer': 'S1: Lexer',
                'stage_2_parser': 'S2: Parser',
                'stage_3_ir_generator': 'S3: IR Gen',
                'stage_4_optimizer': 'S4: Optimizer',
            };

            for (const stage of pipelineData.stages) {
                const label = stageLabels[stage.stage] || stage.stage;
                const statusBadge = stage.success
                    ? '<span class="badge badge-success">✓ Pass</span>'
                    : '<span class="badge badge-danger">✗ Fail</span>';
                const latency = (stage.latency_ms / 1000).toFixed(1);

                html += `<tr>
                    <td style="padding:10px 12px;border-bottom:1px solid var(--border-subtle);font-weight:500;">${label}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid var(--border-subtle);text-align:center;">${statusBadge}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid var(--border-subtle);text-align:right;color:${stage.validation_errors > 0 ? 'var(--warning)' : 'var(--text-muted)'};">${stage.validation_errors}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid var(--border-subtle);text-align:right;color:${stage.repair_attempts > 0 ? 'var(--warning)' : 'var(--text-muted)'};">${stage.repair_attempts}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid var(--border-subtle);text-align:right;font-family:var(--font-mono);font-size:0.85rem;">${latency}s</td>
                </tr>`;
            }
            html += '</tbody></table>';
        }

        // --- Cost Breakdown ---
        if (costData && costData.per_stage) {
            html += '<h3 style="color: var(--text-secondary); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 24px 0 12px;">Cost Breakdown</h3>';
            html += '<table style="width: 100%; border-collapse: collapse;">';
            html += '<thead><tr>';
            html += '<th style="text-align:left;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Stage</th>';
            html += '<th style="text-align:right;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Calls</th>';
            html += '<th style="text-align:right;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Tokens</th>';
            html += '<th style="text-align:right;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Cost</th>';
            html += '</tr></thead><tbody>';

            for (const [stage, data] of Object.entries(costData.per_stage)) {
                html += `<tr>
                    <td style="padding:8px 12px;border-bottom:1px solid var(--border-subtle);">${stage}</td>
                    <td style="padding:8px 12px;border-bottom:1px solid var(--border-subtle);text-align:right;">${data.calls}</td>
                    <td style="padding:8px 12px;border-bottom:1px solid var(--border-subtle);text-align:right;font-family:var(--font-mono);font-size:0.85rem;">${this._formatTokens(data.total_tokens)}</td>
                    <td style="padding:8px 12px;border-bottom:1px solid var(--border-subtle);text-align:right;font-family:var(--font-mono);font-size:0.85rem;">$${data.cost_usd.toFixed(4)}</td>
                </tr>`;
            }
            html += '</tbody></table>';
        }

        // --- Runtime Checks ---
        if (runtimeData && runtimeData.checks) {
            html += '<h3 style="color: var(--text-secondary); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 24px 0 12px;">Runtime Checks</h3>';
            for (const check of runtimeData.checks) {
                const icon = check.passed ? '✅' : '❌';
                html += `<div style="display:flex;align-items:center;gap:8px;padding:6px 0;font-size:0.9rem;">
                    <span>${icon}</span>
                    <span style="color:var(--text-primary);">${check.name.replace(/_/g, ' ')}</span>
                    <span style="color:var(--text-muted);font-size:0.8rem;margin-left:auto;">${check.details}</span>
                </div>`;
            }
        }

        container.innerHTML = html;
    },

    _metricCard(value, label, type) {
        const cls = type ? ` ${type}` : '';
        return `<div class="metric-card${cls}">
            <div class="metric-value">${value}</div>
            <div class="metric-label">${label}</div>
        </div>`;
    },

    _formatTokens(count) {
        if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
        if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
        return String(count);
    },

    renderEvaluationResults(container, evalData) {
        if (!evalData) {
            container.innerHTML = '<p style="color: var(--text-muted); padding: 20px;">No evaluation data available.</p>';
            return;
        }

        let html = '';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;margin:36px 0 16px;">';
        html += '  <h2 style="color:var(--text-primary);font-size:1.1rem;font-weight:700;margin:0;">Pipeline Evaluation Benchmarks</h2>';
        html += '  <button class="btn btn-secondary btn-sm" id="run-eval-refresh-btn">🔄 Run Full Benchmarks</button>';
        html += '</div>';

        // --- Summary Cards ---
        html += '<div class="metrics-grid">';
        const rateClass = evalData.success_rate >= 80 ? 'success' : evalData.success_rate >= 50 ? 'warning' : 'danger';
        html += this._metricCard(`${evalData.success_rate}%`, 'Success Rate', rateClass);
        html += this._metricCard(evalData.total_prompts, 'Total Prompts', '');
        html += this._metricCard(`${(evalData.avg_latency_ms / 1000).toFixed(1)}s`, 'Avg Latency', '');
        html += this._metricCard(`$${evalData.total_cost_usd.toFixed(4)}`, 'Total Cost', '');
        html += this._metricCard(evalData.avg_retries.toFixed(1), 'Avg Retries', evalData.avg_retries > 0.5 ? 'warning' : 'success');
        html += '</div>';

        // --- Category Table ---
        if (evalData.category_results) {
            html += '<h3 style="color: var(--text-secondary); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 24px 0 12px;">Results by Category</h3>';
            html += '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:24px;">';
            for (const [cat, data] of Object.entries(evalData.category_results)) {
                const badgeClass = data.success_rate >= 80 ? 'badge-success' : data.success_rate >= 50 ? 'badge-warning' : 'badge-danger';
                html += `
                    <div style="background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:12px 16px;min-width:140px;flex:1;">
                        <div style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase;margin-bottom:4px;">${cat}</div>
                        <div style="display:flex;align-items:baseline;gap:6px;">
                            <span style="font-size:1.2rem;font-weight:700;color:var(--text-primary);">${data.success}/${data.total}</span>
                            <span class="badge ${badgeClass}" style="font-size:0.7rem;padding:1px 6px;">${data.success_rate}%</span>
                        </div>
                    </div>
                `;
            }
            html += '</div>';
        }

        // --- Per-Prompt Results Table ---
        if (evalData.results && evalData.results.length > 0) {
            html += '<h3 style="color: var(--text-secondary); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 24px 0 12px;">Detailed Benchmarks</h3>';
            html += '<table style="width: 100%; border-collapse: collapse;">';
            html += '<thead><tr>';
            html += '<th style="text-align:left;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Prompt</th>';
            html += '<th style="text-align:left;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Category</th>';
            html += '<th style="text-align:center;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Status</th>';
            html += '<th style="text-align:right;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Latency</th>';
            html += '<th style="text-align:right;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Retries</th>';
            html += '<th style="text-align:right;padding:8px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.8rem;">Cost</th>';
            html += '</tr></thead><tbody>';

            for (const r of evalData.results) {
                const statusBadge = r.success
                    ? '<span class="badge badge-success">✓ Pass</span>'
                    : `<span class="badge badge-danger" title="${r.error_message || 'Error'}">✗ Fail</span>`;
                const latency = (r.total_latency_ms / 1000).toFixed(1);

                html += `<tr>
                    <td style="padding:10px 12px;border-bottom:1px solid var(--border-subtle);font-weight:500;" title="${r.prompt_text}">${r.prompt_name}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:0.85rem;">${r.category}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid var(--border-subtle);text-align:center;">${statusBadge}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid var(--border-subtle);text-align:right;font-family:var(--font-mono);font-size:0.85rem;">${latency}s</td>
                    <td style="padding:10px 12px;border-bottom:1px solid var(--border-subtle);text-align:right;color:${r.total_retries > 0 ? 'var(--warning)' : 'var(--text-muted)'};">${r.total_retries}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid var(--border-subtle);text-align:right;font-family:var(--font-mono);font-size:0.85rem;">$${r.total_cost_usd.toFixed(4)}</td>
                </tr>`;
            }
            html += '</tbody></table>';
        }

        container.innerHTML = html;
        
        // Bind the refresh button
        const refreshBtn = document.getElementById('run-eval-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                // Call global app handler
                if (window.App && typeof window.App.runEvaluationSuite === 'function') {
                    window.App.runEvaluationSuite();
                }
            });
        }
    },
};

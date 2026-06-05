/**
 * AI App Compiler — Main Application Logic
 * Handles API calls, state management, UI updates, and pipeline orchestration.
 */

const App = {
    // --- State ---
    state: {
        isCompiling: false,
        currentResult: null,
        currentStage: 0,
    },

    // --- DOM Elements ---
    el: {},

    /**
     * Initialize the application.
     */
    init() {
        this.cacheElements();
        this.bindEvents();
        this.updateCharCount();
    },

    cacheElements() {
        this.el = {
            promptInput: document.getElementById('prompt-input'),
            compileBtn: document.getElementById('compile-btn'),
            charCount: document.getElementById('char-count'),
            pipelineSection: document.getElementById('pipeline-section'),
            outputSection: document.getElementById('output-section'),
            stages: document.querySelectorAll('.pipeline-stage'),
            tabs: document.querySelectorAll('.tab'),
            tabPanels: document.querySelectorAll('.tab-panel'),

            // Tab content containers
            tabAppSpec: document.getElementById('tab-app-spec'),
            tabUI: document.getElementById('tab-ui'),
            tabAPI: document.getElementById('tab-api'),
            tabDB: document.getElementById('tab-db'),
            tabAuth: document.getElementById('tab-auth'),
            tabMetrics: document.getElementById('tab-metrics'),
            tabPreview: document.getElementById('tab-preview'),
        };
    },

    bindEvents() {
        // Compile button
        this.el.compileBtn.addEventListener('click', () => this.compile());

        // Char count
        this.el.promptInput.addEventListener('input', () => this.updateCharCount());

        // Keyboard shortcut: Ctrl+Enter to compile
        this.el.promptInput.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.compile();
            }
        });

        // Tab switching
        this.el.tabs.forEach((tab) => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // Prompt cards click handler
        const cards = document.querySelectorAll('.prompt-card');
        cards.forEach((card) => {
            card.addEventListener('click', () => {
                const prompt = card.getAttribute('data-prompt');
                if (prompt) {
                    this.el.promptInput.value = prompt;
                    this.updateCharCount();
                    this.el.promptInput.focus();
                }
            });
        });
    },

    updateCharCount() {
        const len = this.el.promptInput.value.length;
        this.el.charCount.textContent = `${len} / 5000`;
    },

    // =========================================================================
    // COMPILATION
    // =========================================================================

    async compile() {
        const prompt = this.el.promptInput.value.trim();
        if (!prompt || prompt.length < 10) {
            this.showToast('Please enter at least 10 characters.', 'error');
            return;
        }

        if (this.state.isCompiling) return;

        this.state.isCompiling = true;
        this.el.compileBtn.disabled = true;
        this.el.compileBtn.innerHTML = '<span class="spinner"></span> Compiling...';

        // Show pipeline, hide output
        this.el.pipelineSection.classList.add('active');
        this.el.outputSection.classList.remove('active');

        // Reset stages
        this.resetStages();

        // Animate stages sequentially
        this.animateStage(0, 'running');
        this.startProgressiveAnimation();

        try {
            const response = await fetch('/api/compile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt }),
            });

            const data = await response.json();

            if (this.state.animationInterval) {
                clearInterval(this.state.animationInterval);
            }

            if (!response.ok) {
                throw new Error(data.detail || 'Compilation failed');
            }

            this.state.currentResult = data;

            // Update pipeline stages based on result
            if (data.pipeline && data.pipeline.stages) {
                this.updateStagesFromResult(data.pipeline.stages);
            }

            if (data.success) {
                this.showToast('Compilation successful! ✨', 'success');
                this.renderOutput(data);
            } else {
                this.showToast(`Compilation failed: ${data.error || 'Unknown error'}`, 'error');
                // Still render partial results if available
                if (data.pipeline) {
                    this.renderOutput(data);
                }
            }
        } catch (err) {
            if (this.state.animationInterval) {
                clearInterval(this.state.animationInterval);
            }
            console.error('Compilation error:', err);
            this.showToast(`Error: ${err.message}`, 'error');
            this.markAllStagesFailed();
        } finally {
            this.state.isCompiling = false;
            this.el.compileBtn.disabled = false;
            this.el.compileBtn.innerHTML = '⚡ Compile';
        }
    },

    // =========================================================================
    // PIPELINE ANIMATION
    // =========================================================================

    startProgressiveAnimation() {
        let currentMockStage = 0;
        this.state.animationInterval = setInterval(() => {
            if (!this.state.isCompiling) {
                clearInterval(this.state.animationInterval);
                return;
            }
            if (currentMockStage < 3) {
                this.animateStage(currentMockStage, 'passed');
                currentMockStage++;
                this.animateStage(currentMockStage, 'running');
            }
        }, 1200);
    },

    resetStages() {
        this.el.stages.forEach((stage) => {
            stage.className = 'pipeline-stage';
            stage.querySelector('.stage-status').textContent = 'Waiting...';
        });
    },

    animateStage(index, status) {
        if (index >= this.el.stages.length) return;
        const stage = this.el.stages[index];
        stage.className = `pipeline-stage ${status}`;

        const statusText = {
            running: '⏳ Processing...',
            passed: '✓ Passed',
            failed: '✗ Failed',
        };
        stage.querySelector('.stage-status').textContent = statusText[status] || status;
    },

    updateStagesFromResult(stages) {
        stages.forEach((s, i) => {
            if (i < this.el.stages.length) {
                this.animateStage(i, s.success ? 'passed' : 'failed');
            }
        });
    },

    markAllStagesFailed() {
        this.el.stages.forEach((_, i) => this.animateStage(i, 'failed'));
    },

    // =========================================================================
    // OUTPUT RENDERING
    // =========================================================================

    renderOutput(data) {
        this.el.outputSection.classList.add('active');

        // Full AppSpec
        if (data.app_spec) {
            JsonRenderer.renderWithCopy(this.el.tabAppSpec, data.app_spec);
        } else {
            this.el.tabAppSpec.innerHTML = '<p style="color:var(--text-muted);padding:20px;">No output generated.</p>';
        }

        // Individual schema tabs
        if (data.app_spec) {
            JsonRenderer.renderWithCopy(this.el.tabUI, data.app_spec.ui || {});
            JsonRenderer.renderWithCopy(this.el.tabAPI, data.app_spec.api || {});
            JsonRenderer.renderWithCopy(this.el.tabDB, data.app_spec.db || {});
            JsonRenderer.renderWithCopy(this.el.tabAuth, data.app_spec.auth || {});
        }

        // Metrics
        MetricsDashboard.renderPipelineMetrics(
            this.el.tabMetrics,
            data.pipeline,
            data.cost,
            data.runtime
        );

        // Append a dedicated container for evaluation results benchmarks below pipeline metrics
        let evalSection = document.getElementById('evaluation-results-section');
        if (!evalSection) {
            evalSection = document.createElement('div');
            evalSection.id = 'evaluation-results-section';
            this.el.tabMetrics.appendChild(evalSection);
        }

        // Preview
        if (data.runtime && data.runtime.is_executable && data.app_spec) {
            const appName = data.app_spec.metadata?.name || 'app';
            const safeName = appName.toLowerCase().replace(/[^a-z0-9_]/g, '_');
            this.el.tabPreview.innerHTML = `
                <p style="margin-bottom:12px;color:var(--text-secondary);font-size:0.9rem;">
                    Generated app preview — also available at 
                    <a href="/api/preview/${safeName}" target="_blank" style="color:var(--accent);">/api/preview/${safeName}</a>
                </p>
                <iframe class="preview-frame" src="/api/preview/${safeName}"></iframe>
            `;
        } else {
            this.el.tabPreview.innerHTML = '<p style="color:var(--text-muted);padding:20px;">No preview available — runtime simulation did not produce an executable app.</p>';
        }

        // Switch to AppSpec tab
        this.switchTab('app-spec');
    },

    // =========================================================================
    // TABS
    // =========================================================================

    switchTab(tabId) {
        this.el.tabs.forEach((t) => {
            t.classList.toggle('active', t.dataset.tab === tabId);
        });
        this.el.tabPanels.forEach((p) => {
            p.classList.toggle('active', p.id === `panel-${tabId}`);
        });
        if (tabId === 'metrics') {
            this.loadEvaluationResults();
        }
    },

    async loadEvaluationResults() {
        let evalSection = document.getElementById('evaluation-results-section');
        if (!evalSection) {
            evalSection = document.createElement('div');
            evalSection.id = 'evaluation-results-section';
            this.el.tabMetrics.appendChild(evalSection);
        }

        evalSection.innerHTML = `
            <div style="display:flex;align-items:center;gap:12px;padding:24px 0;margin-top:24px;border-top:1px solid var(--border-subtle);">
                <span class="spinner"></span>
                <span style="color:var(--text-secondary);">Loading evaluation benchmarks...</span>
            </div>
        `;

        try {
            const response = await fetch('/api/evaluation/results');
            if (!response.ok) {
                if (response.status === 404) {
                    evalSection.innerHTML = `
                        <div style="background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:24px;text-align:center;margin-top:24px;">
                            <h4 style="color:var(--text-secondary);margin-bottom:8px;">No Evaluation Results Found</h4>
                            <p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:16px;max-width:500px;margin-inline:auto;">
                                Run the evaluation suite to measure compiler reliability, accuracy, and latency across 20 test cases.
                            </p>
                            <button class="btn btn-primary btn-sm" id="run-eval-btn">⚡ Run Quick Evaluation</button>
                        </div>
                    `;
                    document.getElementById('run-eval-btn').addEventListener('click', () => this.runEvaluationSuite());
                    return;
                }
                throw new Error('Failed to load evaluation results');
            }

            const data = await response.json();
            MetricsDashboard.renderEvaluationResults(evalSection, data);
        } catch (err) {
            console.error(err);
            evalSection.innerHTML = `
                <div style="margin-top:24px;padding:12px;background:var(--danger-bg);border:1px solid rgba(239, 68, 68, 0.2);border-radius:var(--radius-md);color:var(--danger);">
                    Error loading evaluation benchmarks: ${err.message}
                </div>
            `;
        }
    },

    async runEvaluationSuite() {
        let evalSection = document.getElementById('evaluation-results-section');
        if (!evalSection) {
            evalSection = document.createElement('div');
            evalSection.id = 'evaluation-results-section';
            this.el.tabMetrics.appendChild(evalSection);
        }

        evalSection.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;gap:16px;padding:40px;background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:var(--radius-md);margin-top:24px;">
                <span class="spinner" style="width:36px;height:36px;"></span>
                <div style="text-align:center;">
                    <h4 style="color:var(--text-primary);margin-bottom:4px;">Running Evaluation Pipeline...</h4>
                    <p style="color:var(--text-muted);font-size:0.85rem;max-width:400px;margin:0 auto;">
                        Compiling 3 system designs, running schema checks, and verifying output executability. This may take 5-10 seconds.
                    </p>
                </div>
            </div>
        `;

        try {
            const response = await fetch('/api/evaluation/run?count=3', { method: 'POST' });
            if (!response.ok) throw new Error('Failed to run evaluation');
            const data = await response.json();
            this.showToast('Evaluation run completed! 📊', 'success');
            MetricsDashboard.renderEvaluationResults(evalSection, data);
        } catch (err) {
            console.error(err);
            this.showToast(`Evaluation failed: ${err.message}`, 'error');
            this.loadEvaluationResults();
        }
    },

    // =========================================================================
    // TOAST
    // =========================================================================

    showToast(message, type = 'info') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },
};

// Expose to window so other scripts can access
window.App = App;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => App.init());

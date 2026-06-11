/**
 * PromptForge — 4-Stage Interactive Pipeline
 * Handles the step-by-step compilation with user feedback at each stage.
 */

const App = {
    // --- State ---
    state: {
        isCompiling: false,
        currentStage: -1, // -1 = not started
        prompt: '',
        stageOutputs: {},    // { stage_1_lexer: {...}, stage_2_parser: {...}, ... }
        selectedFeatures: [],
        totalCost: { usd: 0, tokens: 0, latency: 0 },
        pipelineStages: [],
        runtime: null,
    },

    STAGES: [
        {
            key: 'stage_1_lexer',
            number: 1,
            name: 'Feature Extraction',
            subtitle: 'Stage 1 — Lexer',
            icon: '🔍',
            desc: 'Review the extracted features. Toggle features on/off to customize your application. Deselected features will not be included.',
            tip: 'Click features to select/deselect them. Use feedback to request additions or changes.',
            proceedLabel: '➡️ Proceed to Design',
        },
        {
            key: 'stage_2_parser',
            number: 2,
            name: 'System Design',
            subtitle: 'Stage 2 — Parser',
            icon: '🏗️',
            desc: 'Review the generated system design. This includes entities, roles, pages, and business rules derived from your selected features.',
            tip: 'You must review and approve the design. Use feedback to modify entities, add roles, or adjust business rules.',
            proceedLabel: '➡️ Proceed to Schema',
        },
        {
            key: 'stage_3_ir_generator',
            number: 3,
            name: 'Schema Generation',
            subtitle: 'Stage 3 — IR Generator',
            icon: '📐',
            desc: 'Review the generated schemas (UI, API, DB, Auth). You can edit the JSON directly in the editor or provide feedback.',
            tip: 'Edit the JSON directly for fine-grained control, or use feedback for broader changes.',
            proceedLabel: '➡️ Proceed to Final',
        },
        {
            key: 'stage_4_optimizer',
            number: 4,
            name: 'AppSpec & Optimization',
            subtitle: 'Stage 4 — Optimizer',
            icon: '🚀',
            desc: 'Review the final application specification. This is the complete output that will be used to generate your app.',
            tip: 'Make final adjustments. Once you complete this stage, the full application will be compiled.',
            proceedLabel: '🎉 Complete & Generate',
        },
    ],

    // --- DOM Elements ---
    el: {},

    // --- Initialize ---
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
            promptSection: document.getElementById('prompt-section'),
            promptCards: document.getElementById('prompt-cards'),

            // Stepper
            stageStepper: document.getElementById('stage-stepper'),
            stepperSteps: document.querySelectorAll('.stepper-step'),
            stepperConnectors: document.querySelectorAll('.stepper-connector'),

            // Workspace
            workspace: document.getElementById('pipeline-workspace'),
            artifactPane: document.getElementById('artifact-pane'),
            artifactIcon: document.getElementById('artifact-icon'),
            artifactTitle: document.getElementById('artifact-title'),
            artifactSubtitle: document.getElementById('artifact-subtitle'),
            artifactBadge: document.getElementById('artifact-badge'),
            artifactBody: document.getElementById('artifact-body'),
            artifactLoading: document.getElementById('artifact-loading'),

            // Feedback
            feedbackPane: document.getElementById('feedback-pane'),
            stageInfoNumber: document.getElementById('stage-info-number'),
            stageInfoTitle: document.getElementById('stage-info-title'),
            stageInfoDesc: document.getElementById('stage-info-desc'),
            stageInfoTip: document.getElementById('stage-info-tip'),
            feedbackInput: document.getElementById('feedback-input'),
            regenerateBtn: document.getElementById('regenerate-btn'),
            proceedBtn: document.getElementById('proceed-btn'),

            // Output
            outputSection: document.getElementById('output-section'),
            tabs: document.querySelectorAll('.tab'),
            tabPanels: document.querySelectorAll('.tab-panel'),
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
        // Compile / Start
        this.el.compileBtn.addEventListener('click', () => this.startPipeline());

        // Char count
        this.el.promptInput.addEventListener('input', () => this.updateCharCount());

        // Keyboard shortcut
        this.el.promptInput.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.startPipeline();
            }
        });

        // Prompt cards
        document.querySelectorAll('.prompt-card').forEach(card => {
            card.addEventListener('click', () => {
                const prompt = card.getAttribute('data-prompt');
                if (prompt) {
                    this.el.promptInput.value = prompt;
                    this.updateCharCount();
                    this.el.promptInput.focus();
                }
            });
        });

        // Tab switching
        this.el.tabs.forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // Regenerate
        this.el.regenerateBtn.addEventListener('click', () => this.handleRegenerate());

        // Proceed
        this.el.proceedBtn.addEventListener('click', () => this.handleProceed());
    },

    updateCharCount() {
        const len = this.el.promptInput.value.length;
        this.el.charCount.textContent = `${len} / 5000`;
    },

    // =========================================================================
    // PIPELINE START
    // =========================================================================

    async startPipeline() {
        const prompt = this.el.promptInput.value.trim();
        if (!prompt || prompt.length < 10) {
            this.showToast('Please enter at least 10 characters.', 'error');
            return;
        }
        if (this.state.isCompiling) return;

        // Reset state
        this.state = {
            ...this.state,
            isCompiling: true,
            currentStage: 0,
            prompt: prompt,
            stageOutputs: {},
            selectedFeatures: [],
            totalCost: { usd: 0, tokens: 0, latency: 0 },
            pipelineStages: [],
            runtime: null,
        };

        // Hide prompt section, show workspace
        this.el.promptSection.classList.add('hidden');
        this.el.promptCards.classList.add('hidden');
        this.el.outputSection.classList.remove('active');
        this.el.stageStepper.classList.add('active');
        this.el.workspace.classList.add('active');

        // Update stepper
        this.updateStepper(0);

        // Execute first stage
        this.executeStage(0);
    },

    // =========================================================================
    // STAGE EXECUTION
    // =========================================================================

    async executeStage(stageIndex, feedback = null) {
        const stage = this.STAGES[stageIndex];
        this.state.currentStage = stageIndex;

        // Update UI
        this.updateStepper(stageIndex);
        this.updateStageInfo(stage);
        this.showArtifactLoading(stage);

        // Disable buttons during processing
        this.el.regenerateBtn.disabled = true;
        this.el.proceedBtn.disabled = true;

        try {
            let requestBody = {
                prompt: this.state.prompt,
                stage: stage.key,
                previous_output: feedback ? this.state.stageOutputs[stage.key] : null,
                feedback: feedback,
                stage_inputs: this.state.stageOutputs,
            };

            // For Stage 1 with selected features, pass them
            if (stage.key === 'stage_1_lexer' && feedback && this.state.selectedFeatures.length > 0) {
                requestBody.selected_features = this.state.selectedFeatures.map(f => f.name);
            }

            const response = await fetch('/api/compile/step', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || data.detail || 'Stage execution failed');
            }

            // Store output
            this.state.stageOutputs[stage.key] = data.output;

            // Track costs
            if (data.cost) {
                this.state.totalCost.usd += data.cost.total_cost_usd || 0;
                this.state.totalCost.tokens += data.cost.total_tokens || 0;
                this.state.totalCost.latency += data.cost.total_latency_ms || 0;
            }

            if (data.runtime) {
                this.state.runtime = data.runtime;
            }

            // Track pipeline stage metadata
            const existingIdx = this.state.pipelineStages.findIndex(s => s.stage === stage.key);
            const stageMeta = {
                stage: stage.key,
                success: true,
                latency_ms: data.cost?.total_latency_ms || 0,
                repair_attempts: existingIdx >= 0 ? this.state.pipelineStages[existingIdx].repair_attempts + 1 : 0,
            };
            if (existingIdx >= 0) {
                this.state.pipelineStages[existingIdx] = stageMeta;
            } else {
                this.state.pipelineStages.push(stageMeta);
            }

            // Render stage-specific artifact
            this.renderArtifact(stageIndex, data.output);

        } catch (err) {
            console.error('Stage execution error:', err);
            this.showToast(`Error in ${stage.name}: ${err.message}`, 'error');
            this.showArtifactError(err.message);
        } finally {
            this.el.regenerateBtn.disabled = false;
            this.el.proceedBtn.disabled = false;
        }
    },

    // =========================================================================
    // ARTIFACT RENDERING (per stage)
    // =========================================================================

    renderArtifact(stageIndex, output) {
        const stage = this.STAGES[stageIndex];

        // Update badge to ready
        this.el.artifactBadge.innerHTML = '<span style="color:var(--success);">●</span> Ready for Review';

        switch (stageIndex) {
            case 0: this.renderStage1Features(output); break;
            case 1: this.renderStage2Design(output); break;
            case 2: this.renderStage3Schema(output); break;
            case 3: this.renderStage4AppSpec(output); break;
        }

        // Update proceed button label
        this.el.proceedBtn.textContent = stage.proceedLabel;
    },

    // --- Stage 1: Feature Chips ---
    renderStage1Features(output) {
        const features = output.features || [];
        // Initialize all features as selected
        this.state.selectedFeatures = features.map(f => ({ ...f, selected: true }));

        let html = `
            <div class="feature-list">
                <div class="feature-list-header">
                    <h3>Extracted Features</h3>
                    <span class="feature-count" id="feature-count">${features.length} / ${features.length} selected</span>
                </div>
                <div class="select-all-bar">
                    <button class="btn btn-sm btn-secondary" id="select-all-btn">✓ Select All</button>
                    <button class="btn btn-sm btn-secondary" id="deselect-all-btn">✗ Deselect All</button>
                </div>
                <div id="feature-chips-container">
        `;

        features.forEach((f, i) => {
            const priorityClass = `priority-${f.priority || 'medium'}`;
            html += `
                <div class="feature-chip selected" data-index="${i}" id="feature-chip-${i}">
                    <div class="feature-checkbox"></div>
                    <div class="feature-content">
                        <div class="feature-name">${this.escapeHtml(f.name.replace(/_/g, ' '))}</div>
                        <div class="feature-desc">${this.escapeHtml(f.description || '')}</div>
                        <div class="feature-meta">
                            <span class="feature-tag ${priorityClass}">${f.priority || 'medium'}</span>
                            ${f.requires_auth ? '<span class="feature-tag auth-tag">🔒 Auth</span>' : ''}
                            ${(f.target_roles || []).map(r => `<span class="feature-tag" style="background:var(--bg-elevated);color:var(--text-secondary);border:1px solid var(--border-default);">${r}</span>`).join('')}
                        </div>
                    </div>
                </div>
            `;
        });

        html += `</div>`;

        // Show app info section
        if (output.app_name || output.app_description) {
            html += `
                <div style="margin-top:16px;padding:14px;background:var(--bg-surface);border:1px solid var(--border-default);border-radius:var(--radius-md);">
                    <div style="font-size:0.78rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">App Info</div>
                    <div style="font-size:0.9rem;font-weight:600;color:var(--text-primary);margin-bottom:2px;">${this.escapeHtml(output.app_name || 'Unknown')}</div>
                    <div style="font-size:0.82rem;color:var(--text-secondary);">${this.escapeHtml(output.app_description || '')}</div>
                    ${output.entities ? `<div style="margin-top:8px;font-size:0.75rem;color:var(--text-muted);">Entities: ${output.entities.join(', ')}</div>` : ''}
                    ${output.roles ? `<div style="font-size:0.75rem;color:var(--text-muted);">Roles: ${output.roles.join(', ')}</div>` : ''}
                </div>
            `;
        }

        html += `</div>`;
        this.el.artifactBody.innerHTML = html;

        // Bind chip click events
        document.querySelectorAll('.feature-chip').forEach(chip => {
            chip.addEventListener('click', () => this.toggleFeature(parseInt(chip.dataset.index)));
        });

        // Select all / Deselect all
        document.getElementById('select-all-btn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.state.selectedFeatures.forEach(f => f.selected = true);
            this.refreshFeatureChips();
        });

        document.getElementById('deselect-all-btn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.state.selectedFeatures.forEach(f => f.selected = false);
            this.refreshFeatureChips();
        });
    },

    toggleFeature(index) {
        const f = this.state.selectedFeatures[index];
        if (f) {
            f.selected = !f.selected;
            this.refreshFeatureChips();
        }
    },

    refreshFeatureChips() {
        this.state.selectedFeatures.forEach((f, i) => {
            const chip = document.getElementById(`feature-chip-${i}`);
            if (chip) {
                chip.className = `feature-chip ${f.selected ? 'selected' : 'deselected'}`;
            }
        });

        const selectedCount = this.state.selectedFeatures.filter(f => f.selected).length;
        const countEl = document.getElementById('feature-count');
        if (countEl) {
            countEl.textContent = `${selectedCount} / ${this.state.selectedFeatures.length} selected`;
        }
    },

    // --- Stage 2: Design Cards ---
    renderStage2Design(output) {
        let html = '<div class="stage-output-view">';

        // Entities Section
        if (output.entities && output.entities.length > 0) {
            html += `<div class="design-cards">`;
            html += `<div style="font-size:0.78rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">📊 Entities (${output.entities.length})</div>`;
            output.entities.forEach(entity => {
                const fieldCount = entity.fields ? entity.fields.length : 0;
                const relCount = entity.relationships ? entity.relationships.length : 0;
                html += `
                    <div class="design-card open">
                        <div class="design-card-header" onclick="this.parentElement.classList.toggle('open')">
                            <h4>${this.escapeHtml(entity.name)}</h4>
                            <span style="font-size:0.72rem;color:var(--text-muted);">${fieldCount} fields · ${relCount} relations</span>
                            <span class="design-card-toggle">▼</span>
                        </div>
                        <div class="design-card-body">
                            <div style="font-size:0.82rem;color:var(--text-secondary);margin-bottom:10px;">${this.escapeHtml(entity.description || '')}</div>
                            ${entity.fields ? `
                                <div style="overflow-x:auto;">
                                    <table style="width:100%;font-size:0.78rem;border-collapse:collapse;">
                                        <thead>
                                            <tr style="border-bottom:1px solid var(--border-default);">
                                                <th style="text-align:left;padding:6px 8px;color:var(--text-muted);font-weight:600;">Field</th>
                                                <th style="text-align:left;padding:6px 8px;color:var(--text-muted);font-weight:600;">Type</th>
                                                <th style="text-align:center;padding:6px 8px;color:var(--text-muted);font-weight:600;">Required</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${entity.fields.map(f => `
                                                <tr style="border-bottom:1px solid var(--border-subtle);">
                                                    <td style="padding:5px 8px;color:var(--text-primary);font-family:var(--font-mono);">${this.escapeHtml(f.name)}</td>
                                                    <td style="padding:5px 8px;color:var(--accent-light);font-family:var(--font-mono);">${this.escapeHtml(f.type)}</td>
                                                    <td style="padding:5px 8px;text-align:center;">${f.required ? '✓' : '—'}</td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            ` : ''}
                            ${entity.relationships && entity.relationships.length > 0 ? `
                                <div style="margin-top:10px;padding-top:8px;border-top:1px solid var(--border-subtle);">
                                    <div style="font-size:0.72rem;font-weight:600;color:var(--text-muted);margin-bottom:4px;">Relationships</div>
                                    ${entity.relationships.map(r => `
                                        <div style="font-size:0.78rem;color:var(--text-secondary);padding:3px 0;">
                                            → <span style="color:var(--accent-light);">${this.escapeHtml(r.target_entity)}</span>
                                            <span style="color:var(--text-muted);">(${r.type})</span>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        }

        // Roles Section
        if (output.roles && output.roles.length > 0) {
            html += `
                <div style="margin-top:16px;">
                    <div style="font-size:0.78rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">🔐 Roles (${output.roles.length})</div>
                    <div style="display:flex;flex-wrap:wrap;gap:8px;">
                        ${output.roles.map(r => `
                            <div style="padding:10px 14px;background:var(--bg-surface);border:1px solid var(--border-default);border-radius:var(--radius-md);flex:1;min-width:150px;">
                                <div style="font-size:0.85rem;font-weight:600;color:var(--text-primary);">${this.escapeHtml(r.name)}${r.is_default ? ' <span style="color:var(--accent-light);font-size:0.7rem;">(default)</span>' : ''}</div>
                                <div style="font-size:0.75rem;color:var(--text-secondary);margin-top:2px;">${this.escapeHtml(r.description || '')}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Pages Section
        if (output.pages && output.pages.length > 0) {
            html += `
                <div style="margin-top:16px;">
                    <div style="font-size:0.78rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">📄 Pages (${output.pages.length})</div>
                    <div style="display:flex;flex-wrap:wrap;gap:8px;">
                        ${output.pages.map(p => `
                            <div style="padding:8px 12px;background:var(--bg-surface);border:1px solid var(--border-default);border-radius:var(--radius-md);font-size:0.82rem;">
                                <span style="color:var(--text-primary);font-weight:500;">${this.escapeHtml(p.name)}</span>
                                <span style="color:var(--text-muted);font-size:0.72rem;margin-left:6px;">${(p.access_roles || []).join(', ')}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Full JSON toggle
        html += `
            <div style="margin-top:16px;">
                <button class="btn btn-sm btn-secondary" id="toggle-raw-json-btn" style="margin-bottom:8px;">📄 Toggle Raw JSON</button>
                <div id="raw-json-container" style="display:none;position:relative;">
                    <div id="raw-json-viewer"></div>
                </div>
            </div>
        `;

        html += '</div>';
        this.el.artifactBody.innerHTML = html;

        // Bind raw JSON toggle
        document.getElementById('toggle-raw-json-btn')?.addEventListener('click', () => {
            const container = document.getElementById('raw-json-container');
            if (container.style.display === 'none') {
                container.style.display = 'block';
                if (typeof JsonRenderer !== 'undefined') {
                    JsonRenderer.renderWithCopy(document.getElementById('raw-json-viewer'), output);
                }
            } else {
                container.style.display = 'none';
            }
        });
    },

    // --- Stage 3: Editable Schema ---
    renderStage3Schema(output) {
        const jsonStr = JSON.stringify(output, null, 2);
        this.el.artifactBody.innerHTML = `
            <div class="stage-output-view">
                <div class="editable-json-label">
                    <span>📐 Generated Schema</span>
                    <span class="edit-indicator">✏️ Editable</span>
                </div>
                <div class="editable-json-container">
                    <textarea class="editable-json" id="schema-editor" spellcheck="false">${this.escapeHtml(jsonStr)}</textarea>
                </div>
            </div>
        `;
    },

    // --- Stage 4: Editable AppSpec ---
    renderStage4AppSpec(output) {
        const jsonStr = JSON.stringify(output, null, 2);
        this.el.artifactBody.innerHTML = `
            <div class="stage-output-view">
                <div class="editable-json-label">
                    <span>🚀 Final Application Specification</span>
                    <span class="edit-indicator">✏️ Editable</span>
                </div>
                <div class="editable-json-container">
                    <textarea class="editable-json" id="appspec-editor" spellcheck="false">${this.escapeHtml(jsonStr)}</textarea>
                </div>
            </div>
        `;
    },

    // =========================================================================
    // USER ACTIONS
    // =========================================================================

    async handleRegenerate() {
        const feedbackText = this.el.feedbackInput.value.trim();
        if (!feedbackText) {
            this.showToast('Please enter feedback to regenerate.', 'warning');
            return;
        }

        this.el.regenerateBtn.disabled = true;
        this.el.regenerateBtn.innerHTML = '<span class="spinner"></span> Regenerating...';

        await this.executeStage(this.state.currentStage, feedbackText);

        this.el.regenerateBtn.disabled = false;
        this.el.regenerateBtn.innerHTML = '🔄 Regenerate';
        this.el.feedbackInput.value = '';

        this.showToast('Output regenerated with your feedback!', 'success');
    },

    handleProceed() {
        const stageIndex = this.state.currentStage;
        const stage = this.STAGES[stageIndex];

        // Stage 1: Filter features based on selection
        if (stageIndex === 0) {
            const selected = this.state.selectedFeatures.filter(f => f.selected);
            if (selected.length === 0) {
                this.showToast('Please select at least one feature to proceed.', 'warning');
                return;
            }

            // Update the stage output to only include selected features
            const filteredOutput = { ...this.state.stageOutputs[stage.key] };
            filteredOutput.features = selected;
            this.state.stageOutputs[stage.key] = filteredOutput;
        }

        // Stage 3: Read edited JSON from textarea
        if (stageIndex === 2) {
            const editor = document.getElementById('schema-editor');
            if (editor) {
                try {
                    const edited = JSON.parse(editor.value);
                    this.state.stageOutputs[stage.key] = edited;
                } catch (e) {
                    this.showToast('Invalid JSON in schema editor. Please fix the JSON before proceeding.', 'error');
                    return;
                }
            }
        }

        // Stage 4: Read edited JSON from textarea
        if (stageIndex === 3) {
            const editor = document.getElementById('appspec-editor');
            if (editor) {
                try {
                    const edited = JSON.parse(editor.value);
                    this.state.stageOutputs[stage.key] = edited;
                } catch (e) {
                    this.showToast('Invalid JSON in AppSpec editor. Please fix the JSON before proceeding.', 'error');
                    return;
                }
            }
        }

        // Mark current stage as completed in stepper
        this.markStepCompleted(stageIndex);

        // Move to next stage
        const nextIndex = stageIndex + 1;
        if (nextIndex < this.STAGES.length) {
            this.el.feedbackInput.value = '';
            this.executeStage(nextIndex);
        } else {
            this.completePipeline();
        }
    },

    // =========================================================================
    // PIPELINE COMPLETION
    // =========================================================================

    completePipeline() {
        this.state.isCompiling = false;

        // Hide workspace
        this.el.workspace.classList.remove('active');

        // Show completion banner
        const banner = document.createElement('div');
        banner.className = 'completion-banner';
        banner.innerHTML = `
            <span class="completion-icon">🎉</span>
            <span class="completion-text">Pipeline Complete — Your application has been compiled successfully!</span>
        `;
        this.el.outputSection.parentElement.insertBefore(banner, this.el.outputSection);

        // Show output section
        this.el.outputSection.classList.add('active');

        // Build final response object
        const appSpec = this.state.stageOutputs['stage_4_optimizer'];
        const finalData = {
            success: true,
            app_spec: appSpec,
            pipeline: {
                stages: this.state.pipelineStages,
                total_latency_ms: this.state.totalCost.latency,
            },
            cost: {
                total_calls: this.state.pipelineStages.length,
                total_cost_usd: this.state.totalCost.usd,
                total_tokens: this.state.totalCost.tokens,
            },
            runtime: this.state.runtime || { is_executable: false },
        };

        this.renderOutput(finalData);
        this.showToast('Compilation completed successfully! 🎉', 'success');

        // Show restart button
        this.el.compileBtn.disabled = false;
        this.el.compileBtn.innerHTML = '🔄 New Compilation';
        this.el.compileBtn.onclick = () => this.resetPipeline();
    },

    resetPipeline() {
        // Remove completion banner
        const banner = document.querySelector('.completion-banner');
        if (banner) banner.remove();

        // Reset state
        this.state = {
            isCompiling: false,
            currentStage: -1,
            prompt: '',
            stageOutputs: {},
            selectedFeatures: [],
            totalCost: { usd: 0, tokens: 0, latency: 0 },
            pipelineStages: [],
            runtime: null,
        };

        // Show prompt section
        this.el.promptSection.classList.remove('hidden');
        this.el.promptCards.classList.remove('hidden');
        this.el.stageStepper.classList.remove('active');
        this.el.workspace.classList.remove('active');
        this.el.outputSection.classList.remove('active');

        // Reset stepper
        this.el.stepperSteps.forEach(s => s.className = 'stepper-step');
        this.el.stepperConnectors.forEach(c => c.className = 'stepper-connector');

        // Reset button
        this.el.compileBtn.innerHTML = '⚡ Start Pipeline';
        this.el.compileBtn.onclick = () => this.startPipeline();

        // Clear prompt
        this.el.promptInput.value = '';
        this.updateCharCount();
    },

    // =========================================================================
    // UI HELPERS
    // =========================================================================

    updateStepper(activeIndex) {
        this.el.stepperSteps.forEach((step, i) => {
            step.className = 'stepper-step';
            if (i < activeIndex) step.classList.add('completed');
            else if (i === activeIndex) step.classList.add('active');
        });

        this.el.stepperConnectors.forEach((conn, i) => {
            conn.className = 'stepper-connector';
            if (i < activeIndex) conn.classList.add('completed');
        });
    },

    markStepCompleted(index) {
        const step = this.el.stepperSteps[index];
        if (step) {
            step.className = 'stepper-step completed';
            step.querySelector('.stepper-circle').textContent = '✓';
        }
        const conn = this.el.stepperConnectors[index];
        if (conn) conn.classList.add('completed');
    },

    updateStageInfo(stage) {
        this.el.artifactIcon.textContent = stage.icon;
        this.el.artifactTitle.textContent = stage.name;
        this.el.artifactSubtitle.textContent = stage.subtitle;

        this.el.stageInfoNumber.textContent = stage.number;
        this.el.stageInfoTitle.textContent = stage.name;
        this.el.stageInfoDesc.textContent = stage.desc;
        this.el.stageInfoTip.innerHTML = `<span class="tip-icon">💡</span><span>${stage.tip}</span>`;
    },

    showArtifactLoading(stage) {
        this.el.artifactBadge.innerHTML = '<span class="spinner" style="width:10px;height:10px;border-width:1.5px;"></span> Processing';
        this.el.artifactBody.innerHTML = `
            <div class="artifact-body-loading">
                <div class="spinner spinner-lg"></div>
                <div class="loading-text">Running ${stage.name}...</div>
            </div>
        `;
    },

    showArtifactError(message) {
        this.el.artifactBadge.innerHTML = '<span style="color:var(--danger);">●</span> Error';
        this.el.artifactBody.innerHTML = `
            <div style="padding:24px;text-align:center;color:var(--danger);">
                <div style="font-size:1.5rem;margin-bottom:8px;">⚠️</div>
                <div style="font-size:0.88rem;font-weight:500;">${this.escapeHtml(message)}</div>
                <div style="font-size:0.78rem;color:var(--text-muted);margin-top:6px;">Try regenerating with different feedback.</div>
            </div>
        `;
    },

    // =========================================================================
    // OUTPUT RENDERING (Final Stage)
    // =========================================================================

    renderOutput(data) {
        this.el.outputSection.classList.add('active');

        if (data.app_spec) {
            if (typeof JsonRenderer !== 'undefined') {
                JsonRenderer.renderWithCopy(this.el.tabAppSpec, data.app_spec);
                JsonRenderer.renderWithCopy(this.el.tabUI, data.app_spec.ui || {});
                JsonRenderer.renderWithCopy(this.el.tabAPI, data.app_spec.api || {});
                JsonRenderer.renderWithCopy(this.el.tabDB, data.app_spec.db || {});
                JsonRenderer.renderWithCopy(this.el.tabAuth, data.app_spec.auth || {});
            }
        } else {
            this.el.tabAppSpec.innerHTML = '<p style="color:var(--text-muted);padding:20px;">No output generated.</p>';
        }

        if (typeof MetricsDashboard !== 'undefined') {
            MetricsDashboard.renderPipelineMetrics(
                this.el.tabMetrics,
                data.pipeline,
                data.cost,
                data.runtime
            );
        }

        // Append evaluation results container
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

        this.switchTab('app-spec');
    },

    // =========================================================================
    // TABS
    // =========================================================================

    switchTab(tabId) {
        this.el.tabs.forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tabId);
        });
        this.el.tabPanels.forEach(p => {
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
                                Run the evaluation suite to measure compiler reliability.
                            </p>
                            <button class="btn btn-primary btn-sm" id="run-eval-btn">⚡ Run Quick Evaluation</button>
                        </div>
                    `;
                    document.getElementById('run-eval-btn')?.addEventListener('click', () => this.runEvaluationSuite());
                    return;
                }
                throw new Error('Failed to load evaluation results');
            }

            const data = await response.json();
            if (typeof MetricsDashboard !== 'undefined') {
                MetricsDashboard.renderEvaluationResults(evalSection, data);
            }
        } catch (err) {
            console.error(err);
            evalSection.innerHTML = `
                <div style="margin-top:24px;padding:12px;background:var(--danger-bg);border:1px solid var(--danger-border);border-radius:var(--radius-md);color:var(--danger);">
                    Error loading evaluation benchmarks: ${err.message}
                </div>
            `;
        }
    },

    async runEvaluationSuite() {
        let evalSection = document.getElementById('evaluation-results-section');
        if (!evalSection) return;

        evalSection.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;gap:16px;padding:40px;background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:var(--radius-md);margin-top:24px;">
                <span class="spinner spinner-lg"></span>
                <div style="text-align:center;">
                    <h4 style="color:var(--text-primary);margin-bottom:4px;">Running Evaluation Pipeline...</h4>
                    <p style="color:var(--text-muted);font-size:0.85rem;max-width:400px;margin:0 auto;">
                        Compiling 3 system designs and verifying output executability. This may take 5-10 seconds.
                    </p>
                </div>
            </div>
        `;

        try {
            const response = await fetch('/api/evaluation/run?count=3', { method: 'POST' });
            if (!response.ok) throw new Error('Failed to run evaluation');
            const data = await response.json();
            this.showToast('Evaluation run completed! 📊', 'success');
            if (typeof MetricsDashboard !== 'undefined') {
                MetricsDashboard.renderEvaluationResults(evalSection, data);
            }
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

    // =========================================================================
    // UTILITIES
    // =========================================================================

    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },
};

// Expose to window
window.App = App;

// Initialize
document.addEventListener('DOMContentLoaded', () => App.init());

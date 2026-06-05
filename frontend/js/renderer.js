/**
 * JSON Renderer — syntax-highlighted JSON viewer with collapsible nodes.
 */

const JsonRenderer = {
    /**
     * Render a JSON object as syntax-highlighted HTML.
     * @param {any} data - The JSON data to render.
     * @param {number} indent - Current indentation level.
     * @returns {string} HTML string.
     */
    render(data, indent = 0) {
        if (data === null || data === undefined) {
            return '<span class="json-null">null</span>';
        }

        const type = typeof data;
        const pad = '  '.repeat(indent);
        const padInner = '  '.repeat(indent + 1);

        if (type === 'string') {
            // Escape HTML in string values
            const escaped = data
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
            return `<span class="json-string">"${escaped}"</span>`;
        }

        if (type === 'number') {
            return `<span class="json-number">${data}</span>`;
        }

        if (type === 'boolean') {
            return `<span class="json-boolean">${data}</span>`;
        }

        if (Array.isArray(data)) {
            if (data.length === 0) {
                return '<span class="json-bracket">[]</span>';
            }

            const items = data.map(
                (item) => `${padInner}${this.render(item, indent + 1)}`
            );

            return [
                '<span class="json-bracket">[</span>',
                items.join(',\n'),
                `${pad}<span class="json-bracket">]</span>`,
            ].join('\n');
        }

        if (type === 'object') {
            const keys = Object.keys(data);
            if (keys.length === 0) {
                return '<span class="json-bracket">{}</span>';
            }

            const entries = keys.map((key) => {
                const val = this.render(data[key], indent + 1);
                return `${padInner}<span class="json-key">"${key}"</span>: ${val}`;
            });

            return [
                '<span class="json-bracket">{</span>',
                entries.join(',\n'),
                `${pad}<span class="json-bracket">}</span>`,
            ].join('\n');
        }

        return String(data);
    },

    /**
     * Render JSON into a container element.
     * @param {HTMLElement} container - The container element.
     * @param {any} data - The JSON data.
     */
    renderInto(container, data) {
        container.innerHTML = `<pre class="json-viewer">${this.render(data)}</pre>`;
    },

    /**
     * Render JSON with a copy button.
     * @param {HTMLElement} container - The container element.
     * @param {any} data - The JSON data.
     */
    renderWithCopy(container, data) {
        container.style.position = 'relative';
        const jsonStr = JSON.stringify(data, null, 2);

        container.innerHTML = `
            <button class="copy-btn" onclick="JsonRenderer.copyToClipboard(this, '${container.id}')">
                📋 Copy
            </button>
            <pre class="json-viewer" id="${container.id}-pre">${this.render(data)}</pre>
        `;

        // Store raw JSON for copy
        container.dataset.rawJson = jsonStr;
    },

    /**
     * Copy JSON to clipboard.
     */
    async copyToClipboard(btn, containerId) {
        const container = document.getElementById(containerId);
        const rawJson = container.dataset.rawJson;

        try {
            await navigator.clipboard.writeText(rawJson);
            btn.textContent = '✅ Copied!';
            setTimeout(() => { btn.textContent = '📋 Copy'; }, 2000);
        } catch (e) {
            btn.textContent = '❌ Failed';
            setTimeout(() => { btn.textContent = '📋 Copy'; }, 2000);
        }
    },
};

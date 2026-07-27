/* LiquidRound — Instructions prompt editor (Quill WYSIWYG + Markdown + History) */

var instrQuill = null;
var instrActiveTab = 'editor';

document.addEventListener('DOMContentLoaded', function() {
    initQuillEditor();
});

function initQuillEditor() {
    var pane = document.getElementById('instr-editor-pane');
    if (!pane) return;
    pane.innerHTML = '';

    var quillDiv = document.createElement('div');
    quillDiv.id = 'instr-quill';
    pane.appendChild(quillDiv);

    instrQuill = new Quill(quillDiv, {
        theme: 'snow',
        modules: { toolbar: [
            ['bold', 'italic', 'underline', 'strike'],
            [{'header': [1, 2, 3, false]}],
            [{'list': 'ordered'}, {'list': 'bullet'}],
            ['link', 'code-block'],
            ['clean']
        ]},
        placeholder: 'Edit prompt content…'
    });

    var md = document.getElementById('instr-markdown-src').value;
    if (typeof marked !== 'undefined' && md.trim()) {
        instrQuill.root.innerHTML = marked.parse(md);
    } else {
        instrQuill.setText(md);
    }
}

function switchTab(tab) {
    var editorPane  = document.getElementById('instr-editor-pane');
    var mdPane      = document.getElementById('instr-markdown-pane');
    var historyPane = document.getElementById('instr-history-pane');
    var mdTextarea  = document.getElementById('instr-markdown-textarea');
    var src         = document.getElementById('instr-markdown-src');

    document.querySelectorAll('.instr-tab').forEach(function(b) { b.classList.remove('active'); });

    if (tab === 'editor') {
        if (instrActiveTab === 'markdown' && mdTextarea) {
            src.value = mdTextarea.value;
            if (instrQuill && typeof marked !== 'undefined') {
                instrQuill.root.innerHTML = marked.parse(mdTextarea.value);
            }
        }
        editorPane.style.display = '';
        mdPane.style.display = 'none';
        historyPane.style.display = 'none';
        document.getElementById('tab-editor').classList.add('active');

    } else if (tab === 'markdown') {
        if (instrActiveTab === 'editor' && instrQuill) {
            var text = quillToMarkdown();
            src.value = text;
            if (mdTextarea) mdTextarea.value = text;
        }
        editorPane.style.display = 'none';
        mdPane.style.display = '';
        historyPane.style.display = 'none';
        document.getElementById('tab-markdown').classList.add('active');

    } else if (tab === 'history') {
        if (instrActiveTab === 'editor' && instrQuill) {
            src.value = quillToMarkdown();
        } else if (instrActiveTab === 'markdown' && mdTextarea) {
            src.value = mdTextarea.value;
        }
        editorPane.style.display = 'none';
        mdPane.style.display = 'none';
        historyPane.style.display = '';
        document.getElementById('tab-history').classList.add('active');
        loadVersionHistory();
    }

    instrActiveTab = tab;
}

function quillToMarkdown() {
    if (!instrQuill) return document.getElementById('instr-markdown-src').value;

    var lines = [];
    var delta = instrQuill.getContents();
    var ops = delta.ops || [];
    var currentLine = '';

    for (var i = 0; i < ops.length; i++) {
        var op = ops[i];
        var text = (typeof op.insert === 'string') ? op.insert : '';
        var attrs = op.attributes || {};

        if (text === '\n') {
            if (attrs.header) {
                var prefix = '#'.repeat(attrs.header) + ' ';
                lines.push(prefix + currentLine);
            } else if (attrs.list === 'ordered') {
                lines.push('1. ' + currentLine);
            } else if (attrs.list === 'bullet') {
                lines.push('- ' + currentLine);
            } else if (attrs['code-block']) {
                lines.push('    ' + currentLine);
            } else {
                lines.push(currentLine);
            }
            currentLine = '';
            continue;
        }

        var parts = text.split('\n');
        for (var j = 0; j < parts.length; j++) {
            var part = parts[j];
            if (attrs.bold) part = '**' + part + '**';
            if (attrs.italic) part = '*' + part + '*';
            if (attrs.code) part = '`' + part + '`';
            if (attrs.link) part = '[' + part + '](' + attrs.link + ')';

            if (j > 0) {
                lines.push(currentLine);
                currentLine = '';
            }
            currentLine += part;
        }
    }
    if (currentLine) lines.push(currentLine);

    return lines.join('\n').trimEnd();
}

async function savePrompt() {
    var src = document.getElementById('instr-markdown-src');
    var mdTextarea = document.getElementById('instr-markdown-textarea');

    if (instrActiveTab === 'editor' && instrQuill) {
        src.value = quillToMarkdown();
    } else if (instrActiveTab === 'markdown' && mdTextarea) {
        src.value = mdTextarea.value;
    }

    var slug = document.getElementById('instr-slug').value;
    var content = src.value.trim();
    var status = document.getElementById('save-status');

    try {
        status.textContent = 'Saving…';
        status.className = 'save-status saving';

        var resp = await fetch('/app/skills/' + encodeURIComponent(slug), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content: content}),
        });
        var data = await resp.json();

        if (data.ok) {
            status.textContent = 'Saved';
            status.className = 'save-status saved';
            var badge = document.getElementById('version-badge');
            if (badge) badge.textContent = 'v' + data.version_count;
            setTimeout(function() { status.textContent = ''; status.className = 'save-status'; }, 2500);
        } else {
            status.textContent = 'Error: ' + (data.error || 'unknown');
            status.className = 'save-status error';
        }
    } catch(err) {
        status.textContent = 'Save failed';
        status.className = 'save-status error';
    }
}

async function loadVersionHistory() {
    var slug = document.getElementById('instr-slug').value;
    var pane = document.getElementById('instr-history-pane');
    if (!pane || !slug) return;

    pane.innerHTML = '<div class="version-loading">Loading…</div>';

    try {
        var resp = await fetch('/app/api/prompt-versions/' + encodeURIComponent(slug));
        var data = await resp.json();
        var versions = data.versions || [];

        if (!versions.length) {
            pane.innerHTML = '<div class="version-empty">No version history yet. Save the prompt to create the first version.</div>';
            return;
        }

        var html = '<div class="version-list">';
        versions.forEach(function(v) {
            var dt = v.created_at || '';
            if (dt.indexOf('T') > 0) dt = dt.substring(0, 16).replace('T', ' ');
            var by = v.changed_by || '';
            var preview = (v.preview || '').substring(0, 140).replace(/</g, '&lt;').replace(/\n/g, ' ');

            html += '<div class="version-item">';
            html += '<div class="version-item-head">';
            html += '<span class="version-num">v' + v.version + '</span>';
            html += '<span class="version-date">' + dt + '</span>';
            if (by) html += '<span class="version-by">' + by + '</span>';
            html += '</div>';
            html += '<div class="version-preview">' + preview + '</div>';
            html += '<div class="version-item-actions">';
            html += '<button class="version-btn" onclick="viewVersion(' + v.id + ')">View</button>';
            html += '<button class="version-btn version-btn-revert" onclick="revertVersion(' + v.id + ',\'' + slug + '\')">Revert</button>';
            html += '</div>';
            html += '</div>';
        });
        html += '</div>';
        pane.innerHTML = html;
    } catch(err) {
        pane.innerHTML = '<div class="version-error">Failed to load version history</div>';
    }
}

async function viewVersion(versionId) {
    try {
        var resp = await fetch('/app/api/prompt-version/' + versionId);
        var data = await resp.json();
        if (data.error) return;

        var content = data.content || '';
        document.getElementById('instr-markdown-src').value = content;
        var mdTextarea = document.getElementById('instr-markdown-textarea');
        if (mdTextarea) mdTextarea.value = content;

        if (instrQuill && typeof marked !== 'undefined') {
            instrQuill.root.innerHTML = marked.parse(content);
        }
        switchTab('editor');
    } catch(err) {
        console.error('Failed to load version:', err);
    }
}

async function revertVersion(versionId, slug) {
    if (!confirm('Revert to this version? This will save it as a new version.')) return;

    try {
        var resp = await fetch('/app/api/prompt-versions/' + encodeURIComponent(slug) + '/revert', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({version_id: versionId}),
        });
        var data = await resp.json();

        if (data.ok) {
            var content = data.content || '';
            document.getElementById('instr-markdown-src').value = content;
            var mdTextarea = document.getElementById('instr-markdown-textarea');
            if (mdTextarea) mdTextarea.value = content;

            if (instrQuill && typeof marked !== 'undefined') {
                instrQuill.root.innerHTML = marked.parse(content);
            }

            var badge = document.getElementById('version-badge');
            if (badge) badge.textContent = 'v' + data.version_count;

            switchTab('editor');
        }
    } catch(err) {
        console.error('Failed to revert version:', err);
    }
}

const API_BASE_URL = 'http://localhost:5001';

let sessionId = '';
let indexUrl = '';
let metadataUrl = '';
let papers = [];
let selectedFiles = [];
let totalTokens = 0;
let totalCost = 0;
let queryCount = 0;

document.addEventListener('DOMContentLoaded', function() {
    sessionId = 'session_' + Date.now();
    document.getElementById('sessionId').value = sessionId;
    setupEventListeners();
    console.log('App initialized. Session:', sessionId);
});

function setupEventListeners() {
    document.getElementById('fileInput').addEventListener('change', handleFileSelect);
    document.getElementById('uploadBtn').addEventListener('click', uploadPapers);
    document.getElementById('sendBtn').addEventListener('click', sendMessage);
    document.getElementById('messageInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

function handleFileSelect(e) {
    selectedFiles = Array.from(e.target.files);
    const uploadBtn = document.getElementById('uploadBtn');
    uploadBtn.disabled = selectedFiles.length === 0;
    
    if (selectedFiles.length > 0) {
        document.querySelector('.file-input-label').textContent = selectedFiles.length + ' file(s) selected';
        console.log('Files selected:', selectedFiles.length);
    }
}

async function uploadPapers() {
    if (selectedFiles.length === 0) return;

    showLoading('Uploading and processing papers...');
    
    try {
        const formData = new FormData();
        formData.append('session_id', sessionId);
        
        selectedFiles.forEach(function(file) {
            formData.append('files', file);
        });
        
        const uploadUrl = API_BASE_URL + '/systematic-review/upload';
        console.log('Uploading to:', uploadUrl);
        console.log('Session ID:', sessionId);
        console.log('Files:', selectedFiles.map(f => f.name));
        
        const response = await fetch(uploadUrl, {
            method: 'POST',
            body: formData,
            // Don't set Content-Type header - browser will set it with boundary
            mode: 'cors',
            credentials: 'same-origin'
        });
        
        console.log('Response status:', response.status);
        console.log('Response headers:', [...response.headers.entries()]);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response body:', errorText);
            throw new Error('Upload failed: ' + response.status + ' - ' + errorText);
        }
        
        const result = await response.json();
        console.log('Upload result:', result);
        
        papers = result.papers || [];
        indexUrl = result.index_path;
        metadataUrl = result.metadata_path;
        updatePapersList();
        
        if (result.token_usage) {
            totalTokens += result.token_usage.embedding_tokens || 0;
            totalCost += result.token_usage.embedding_cost_usd || 0;
            updateTokenDisplay();
        }
        
        addBotMessage('Successfully processed ' + papers.length + ' paper(s)!');
        document.getElementById('sendBtn').disabled = false;
        
        document.getElementById('fileInput').value = '';
        document.querySelector('.file-input-label').textContent = 'Choose PDF Files';
        selectedFiles = [];
        document.getElementById('uploadBtn').disabled = true;
        
    } catch (error) {
        console.error('Upload error:', error);
        console.error('Error stack:', error.stack);
        showError('Failed to upload: ' + error.message);
    } finally {
        hideLoading();
    }
}

function updatePapersList() {
    const papersList = document.getElementById('papersList');
    const paperCount = document.getElementById('paperCount');
    
    paperCount.textContent = papers.length;
    
    if (papers.length === 0) {
        papersList.innerHTML = '<p style="text-align: center; color: #999; font-size: 13px;">No papers uploaded yet</p>';
        return;
    }
    
    papersList.innerHTML = papers.map(function(paper) {
        return '<div class="paper-item">' +
            '<div class="paper-icon">📄</div>' +
            '<div class="paper-info">' +
            '<div class="paper-name">' + paper + '</div>' +
            '<div class="paper-status">✓ Processed</div>' +
            '</div>' +
            '</div>';
    }).join('');
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message || papers.length === 0) return;
    
    addUserMessage(message);
    input.value = '';
    
    showLoading('Analyzing papers and generating comparison...');
    
    try {
        const response = await fetch(API_BASE_URL + '/systematic-review/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                question: message,
                index_path: indexUrl,
                metadata_path: metadataUrl
            })
        });
        
        const result = await response.json();
        console.log('Query result:', result);
        
        if (result.status === 'success') {
            let answer = result.answer;
            
            if (result.token_usage) {
                const tokens = result.token_usage.total_tokens || 0;
                const cost = result.token_usage.total_cost_usd || 0;
                
                totalTokens += tokens;
                totalCost += cost;
                queryCount += 1;
                updateTokenDisplay();
                
                answer += '\n\n---\n\n';
                answer += '**📊 Query Stats:** ' + tokens.toLocaleString() + ' tokens used | Cost: $' + cost.toFixed(6);
            }
            
            addBotMessage(answer);
        } else {
            addBotMessage('❌ Error: ' + (result.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Query error:', error);
        addBotMessage('❌ Error processing your question: ' + error.message);
    } finally {
        hideLoading();
    }
}

function addUserMessage(text) {
    const container = document.getElementById('messagesContainer');
    const div = document.createElement('div');
    div.className = 'message user';
    div.innerHTML = '<div class="message-avatar">U</div>' +
        '<div class="message-content">' + escapeHtml(text) + '</div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function addBotMessage(text) {
    const container = document.getElementById('messagesContainer');
    const div = document.createElement('div');
    div.className = 'message bot';
    div.innerHTML = '<div class="message-avatar">AI</div>' +
        '<div class="message-content">' + formatMarkdown(text) + '</div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function formatMarkdown(text) {
    let html = text;
    
    html = html.replace(/---/g, '<hr>');
    html = html.replace(/### (.+)/g, '<h3>$1</h3>');
    html = html.replace(/## (.+)/g, '<h2>$1</h2>');
    html = html.replace(/# (.+)/g, '<h1>$1</h1>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    html = convertMarkdownTables(html);
    
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

function convertMarkdownTables(text) {
    const lines = text.split('\n');
    let result = [];
    let i = 0;
    
    while (i < lines.length) {
        const line = lines[i].trim();
        
        if (line.startsWith('|') && line.endsWith('|')) {
            let tableLines = [];
            let j = i;
            
            while (j < lines.length && lines[j].trim().startsWith('|')) {
                tableLines.push(lines[j]);
                j++;
            }
            
            result.push(buildHtmlTable(tableLines));
            i = j;
        } else {
            result.push(line);
            i++;
        }
    }
    
    return result.join('\n');
}

function buildHtmlTable(lines) {
    let html = '<table>';
    let isFirstRow = true;
    let hasValidRow = false;
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        // Skip separator lines
        if (line.includes('---') || line.includes('===')) {
            continue;
        }
        
        // Skip empty lines
        if (!line) {
            continue;
        }
        
        // Parse cells
        const cells = line.split('|').filter(function(c) { 
            return c.trim(); 
        }).map(function(c) { 
            return c.trim(); 
        });
        
        // Skip rows with no content or only dashes/empty cells
        if (cells.length === 0) {
            continue;
        }
        
        // Check if all cells are empty or just dashes
        const hasContent = cells.some(function(cell) {
            return cell && cell !== '-' && cell !== '' && cell.length > 0;
        });
        
        if (!hasContent) {
            continue;  // Skip this row entirely
        }
        
        const tag = isFirstRow ? 'th' : 'td';
        
        html += '<tr>';
        for (let j = 0; j < cells.length; j++) {
            html += '<' + tag + '>' + cells[j] + '</' + tag + '>';
        }
        html += '</tr>';
        
        isFirstRow = false;
        hasValidRow = true;
    }
    
    html += '</table>';
    
    // Return empty string if no valid rows found
    return hasValidRow ? html : '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateTokenDisplay() {
    document.getElementById('totalTokens').textContent = totalTokens.toLocaleString();
    document.getElementById('queryCount').textContent = queryCount;
    document.getElementById('totalCost').textContent = '$' + totalCost.toFixed(4);
}

function showLoading(text) {
    document.getElementById('loadingText').textContent = text;
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

function showError(message) {
    const status = document.getElementById('uploadStatus');
    status.innerHTML = '<div class="error-message">' + message + '</div>';
    setTimeout(function() { 
        status.innerHTML = ''; 
    }, 5000);
}
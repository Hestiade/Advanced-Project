#!/usr/bin/env python3
"""Standalone Log Viewer - Opens in its own browser window."""

import os
import json
import webbrowser
import http.server
import socketserver
from pathlib import Path
from datetime import datetime

PORT = 5001
LOG_DIR = Path(__file__).parent / "logs"

HTML_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Email Log Viewer</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            margin-bottom: 20px;
        }
        h1 { 
            font-size: 1.5rem;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        select, input {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            color: #fff;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.9rem;
        }
        button {
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            border: none;
            color: #fff;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
        }
        button:hover { opacity: 0.9; }
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat {
            background: rgba(255,255,255,0.05);
            padding: 15px 25px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value { font-size: 1.8rem; font-weight: bold; color: #00d4ff; }
        .stat-label { font-size: 0.8rem; color: #888; }
        table {
            width: 100%;
            border-collapse: collapse;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            overflow: hidden;
        }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }
        th { background: rgba(0,212,255,0.1); color: #00d4ff; font-weight: 600; }
        tr:hover { background: rgba(255,255,255,0.05); }
        .action-forward { color: #3fb950; }
        .action-spam { color: #f85149; }
        .action-review { color: #f0883e; }
        .action-needs-review { color: #f0883e; }
        .badge {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-forward { background: rgba(63,185,80,0.2); color: #3fb950; }
        .badge-spam { background: rgba(248,81,73,0.2); color: #f85149; }
        .badge-review { background: rgba(240,136,62,0.2); color: #f0883e; }
        .risk-flags { color: #f85149; font-weight: bold; }
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.85);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-content {
            background: #1a1a3e;
            border-radius: 12px;
            width: 90%;
            max-width: 800px;
            max-height: 85vh;
            overflow: auto;
        }
        .modal-header {
            padding: 15px 20px;
            background: rgba(0,212,255,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-close { background: none; border: none; color: #888; font-size: 1.5rem; cursor: pointer; }
        .modal-body { padding: 20px; }
        .field { margin-bottom: 12px; }
        .field label { color: #00d4ff; font-weight: 600; display: inline-block; width: 120px; }
        .field pre { 
            background: rgba(0,0,0,0.3); 
            padding: 15px; 
            border-radius: 8px; 
            white-space: pre-wrap;
            max-height: 200px;
            overflow: auto;
            margin-top: 8px;
        }
        .empty { text-align: center; padding: 50px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Email Log Viewer</h1>
            <div class="controls">
                <select id="sessionFilter" onchange="loadLogs()">
                    <option value="">Select Session...</option>
                </select>
                <select id="actionFilter" onchange="filterLogs()">
                    <option value="all">All Actions</option>
                    <option value="forward">Forwarded</option>
                    <option value="spam">Spam</option>
                    <option value="needs-review">Needs Review</option>
                </select>
                <input type="text" id="searchBox" placeholder="Search..." oninput="filterLogs()">
                <button onclick="loadSessions()">🔄 Refresh</button>
            </div>
        </header>
        
        <div class="stats">
            <div class="stat"><div class="stat-value" id="statTotal">0</div><div class="stat-label">Total</div></div>
            <div class="stat"><div class="stat-value" id="statForward">0</div><div class="stat-label">Forwarded</div></div>
            <div class="stat"><div class="stat-value" id="statSpam">0</div><div class="stat-label">Spam</div></div>
            <div class="stat"><div class="stat-value" id="statReview">0</div><div class="stat-label">Review</div></div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>From</th>
                    <th>Subject</th>
                    <th>Action</th>
                    <th>Category</th>
                    <th>Forward To</th>
                    <th>Confidence</th>
                    <th>Flags</th>
                </tr>
            </thead>
            <tbody id="logTable"></tbody>
        </table>
    </div>
    
    <div id="modal" class="modal" onclick="if(event.target===this)closeModal()">
        <div class="modal-content">
            <div class="modal-header">
                <h2>📧 Email Details</h2>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>
    
    <script>
        let allLogs = [];
        
        async function loadSessions() {
            try {
                const resp = await fetch('/api/sessions');
                const sessions = await resp.json();
                const select = document.getElementById('sessionFilter');
                select.innerHTML = '<option value="">Select Session...</option>' +
                    sessions.map(s => `<option value="${s.session_id}">${s.session_id}</option>`).join('');
                
                // Auto-select first session
                if (sessions.length > 0) {
                    select.value = sessions[0].session_id;
                    loadLogs();
                }
            } catch (e) {
                console.error(e);
            }
        }
        
        async function loadLogs() {
            const session = document.getElementById('sessionFilter').value;
            if (!session) {
                document.getElementById('logTable').innerHTML = '<tr><td colspan="8" class="empty">Select a session</td></tr>';
                return;
            }
            try {
                const resp = await fetch('/api/logs?session=' + session);
                allLogs = await resp.json();
                filterLogs();
            } catch (e) {
                document.getElementById('logTable').innerHTML = '<tr><td colspan="8" class="empty">No logs found</td></tr>';
            }
        }
        
        function filterLogs() {
            const action = document.getElementById('actionFilter').value;
            const search = document.getElementById('searchBox').value.toLowerCase();
            
            let filtered = allLogs.filter(log => {
                if (action !== 'all' && !log.final_action?.includes(action) && !log.action?.includes(action)) return false;
                if (search && !JSON.stringify(log).toLowerCase().includes(search)) return false;
                return true;
            });
            
            // Stats
            document.getElementById('statTotal').textContent = allLogs.length;
            document.getElementById('statForward').textContent = allLogs.filter(l => l.final_action === 'forwarded' || l.action === 'forward').length;
            document.getElementById('statSpam').textContent = allLogs.filter(l => l.final_action === 'spam' || l.action === 'spam' || l.category === 'spam').length;
            document.getElementById('statReview').textContent = allLogs.filter(l => l.final_action?.includes('review') || l.action?.includes('review')).length;
            
            // Render table
            const table = document.getElementById('logTable');
            if (filtered.length === 0) {
                table.innerHTML = '<tr><td colspan="8" class="empty">No logs match filters</td></tr>';
                return;
            }
            
            table.innerHTML = filtered.map((log, idx) => {
                const time = log.timestamp?.substring(11, 19) || '-';
                const from = (log.from_addr || '-').substring(0, 25);
                const subj = (log.subject || '-').substring(0, 40);
                const action = log.final_action || log.action || '-';
                const cat = log.ai_category || log.category || '-';
                const fwd = log.forward_destinations?.join(', ') || log.forward_to || '-';
                const conf = log.ai_confidence || log.confidence || 0;
                const flags = log.risk_flags?.join(', ') || '';
                
                let badge = 'badge-review';
                if (action.includes('forward')) badge = 'badge-forward';
                if (action.includes('spam')) badge = 'badge-spam';
                
                return `<tr onclick="showDetail(${idx})" style="cursor:pointer">
                    <td>${time}</td>
                    <td title="${log.from_addr}">${from}</td>
                    <td title="${log.subject}">${subj}</td>
                    <td><span class="badge ${badge}">${action}</span></td>
                    <td>${cat}</td>
                    <td>${fwd.substring(0, 20)}</td>
                    <td>${Math.round(conf * 100)}%</td>
                    <td class="risk-flags">${flags}</td>
                </tr>`;
            }).join('');
        }
        
        function showDetail(idx) {
            const log = allLogs[idx];
            const body = document.getElementById('modalBody');
            body.innerHTML = `
                <div class="field"><label>Time:</label> ${log.timestamp || '-'}</div>
                <div class="field"><label>UID:</label> ${log.uid || '-'}</div>
                <div class="field"><label>From:</label> ${log.from_addr || '-'}</div>
                <div class="field"><label>Subject:</label> ${log.subject || '-'}</div>
                <div class="field"><label>Action:</label> ${log.final_action || log.action || '-'}</div>
                <div class="field"><label>Category:</label> ${log.ai_category || log.category || '-'}</div>
                <div class="field"><label>Forward To:</label> ${log.forward_destinations?.join(', ') || log.forward_to || '-'}</div>
                <div class="field"><label>Confidence:</label> ${Math.round((log.ai_confidence || log.confidence || 0) * 100)}%</div>
                <div class="field"><label>Risk Flags:</label> <span class="risk-flags">${log.risk_flags?.join(', ') || 'None'}</span></div>
                <div class="field"><label>Reason:</label> ${log.ai_reason || log.reason || '-'}</div>
                <div class="field"><label>Body Preview:</label><pre>${log.body_preview || '(none)'}</pre></div>
            `;
            document.getElementById('modal').style.display = 'flex';
        }
        
        function closeModal() {
            document.getElementById('modal').style.display = 'none';
        }
        
        document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
        
        // Load on start
        loadSessions();
    </script>
</body>
</html>
'''

class LogHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        elif self.path == '/api/sessions':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # List all session files
            sessions = []
            for f in sorted(LOG_DIR.glob("email_log_*.jsonl"), reverse=True):
                session_id = f.stem.replace("email_log_", "")
                sessions.append({
                    "session_id": session_id,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                })
            
            self.wfile.write(json.dumps(sessions).encode())
        elif self.path.startswith('/api/logs'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Parse session from query
            session_id = None
            if '?session=' in self.path:
                session_id = self.path.split('?session=')[1]
            
            logs = []
            if session_id:
                log_file = LOG_DIR / f"email_log_{session_id}.jsonl"
                if log_file.exists():
                    with open(log_file) as f:
                        for line in f:
                            if line.strip():
                                try:
                                    logs.append(json.loads(line))
                                except:
                                    pass
            
            self.wfile.write(json.dumps(logs).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logging


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          📊 Email Log Viewer                            ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"\n  Opening in browser: http://localhost:{PORT}\n")
    
    # Create logs dir if needed
    LOG_DIR.mkdir(exist_ok=True)
    
    with socketserver.TCPServer(("", PORT), LogHandler) as httpd:
        webbrowser.open(f'http://localhost:{PORT}')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")


if __name__ == '__main__':
    main()

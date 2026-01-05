#!/usr/bin/env python3
"""Web Dashboard for the AI Mail Redirection Agent."""

import threading
import time
import os
import sys
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO

from mail_agent import load_config, Router, IMAPClient, SMTPClient
from email_logger import log_email, log_action, get_stats

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mail-agent-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
emails_data = []
pending_reviews = {}  # uid -> email data for manual review
is_running = False
config = None


@dataclass
class EmailStatus:
    uid: str
    from_addr: str
    subject: str
    body: str = ""
    status: str = "Pending"
    forward_to: list = field(default_factory=list)
    category: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    needs_review: bool = False


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Mail Redirection Agent</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        h1 { 
            font-size: 1.8rem; 
            color: #E95420;
        }
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1rem;
        }
        .status-dot {
            width: 12px; height: 12px;
            border-radius: 50%;
            background: #ff4444;
            animation: pulse 2s infinite;
        }
        .status-dot.running { background: #00ff88; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 450px;
            gap: 20px;
        }
        .left-panel, .right-panel {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .info-bar {
            display: flex;
            gap: 20px;
            padding: 15px 20px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            font-size: 0.9rem;
            flex-wrap: wrap;
        }
        .info-bar span { color: #888; }
        .info-bar strong { color: #E95420; }
        .controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s;
        }
        .btn-primary {
            background: #E95420;
            color: white;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(233,84,32,0.4); }
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #e0e0e0;
        }
        .btn-secondary:hover { background: rgba(255,255,255,0.2); }
        .btn-danger { background: #ff4444; color: white; }
        .btn-danger:hover { background: #ff6666; }
        .btn-sm {
            padding: 6px 12px;
            font-size: 0.8rem;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            overflow: hidden;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 0.85rem;
        }
        th {
            background: rgba(255,255,255,0.05);
            color: #E95420;
            font-weight: 600;
        }
        tr:hover { background: rgba(255,255,255,0.02); }
        tr.needs-review { background: rgba(255,193,7,0.1); }
        .status-badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .status-pending { background: rgba(255,193,7,0.2); color: #ffc107; }
        .status-processing { background: rgba(233,84,32,0.2); color: #E95420; }
        .status-forwarded { background: rgba(0,255,136,0.2); color: #00ff88; }
        .status-skipped { background: rgba(136,136,136,0.2); color: #888; }
        .status-error { background: rgba(255,68,68,0.2); color: #ff4444; }
        .status-review { background: rgba(255,193,7,0.3); color: #ffc107; }
        .confidence-bar {
            width: 50px; height: 5px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            overflow: hidden;
            display: inline-block;
        }
        .confidence-fill {
            height: 100%;
            background: #E95420;
            transition: width 0.3s;
        }
        .confidence-fill.low { background: #ff4444; }
        .action-btns {
            display: flex;
            gap: 5px;
        }
        .btn-approve { background: #00ff88; color: #000; }
        .btn-reject { background: #ff4444; color: #fff; }
        
        /* Tab Styles */
        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
        }
        .tab-btn {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            color: #888;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
        }
        .tab-btn.active {
            background: #E95420;
            color: #fff;
            border: none;
        }
        .tab-content { display: block; }
        .tab-content:not(.active) { display: none; }
        
        /* Terminal Styles */
        .terminal-container {
            background: #0d1117;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #30363d;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .terminal-header {
            background: #161b22;
            padding: 10px 15px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 1px solid #30363d;
        }
        .terminal-dot {
            width: 12px; height: 12px;
            border-radius: 50%;
        }
        .terminal-dot.red { background: #ff5f56; }
        .terminal-dot.yellow { background: #ffbd2e; }
        .terminal-dot.green { background: #27c93f; }
        .terminal-title {
            margin-left: 10px;
            font-family: monospace;
            color: #8b949e;
            font-size: 0.85rem;
        }
        .terminal-body {
            flex: 1;
            padding: 15px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.8rem;
            line-height: 1.5;
            overflow-y: auto;
            max-height: 600px;
        }
        .terminal-line {
            white-space: pre-wrap;
            word-break: break-all;
        }
        .terminal-line.prompt { color: #58a6ff; }
        .terminal-line.success { color: #3fb950; }
        .terminal-line.error { color: #f85149; }
        .terminal-line.info { color: #8b949e; }
        .terminal-line.header { color: #d2a8ff; font-weight: bold; }
        .terminal-line.dim { color: #484f58; }
        .terminal-line.reasoning { color: #f0883e; font-style: italic; }
        
        .stats {
            display: flex;
            gap: 15px;
            padding: 15px 20px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
        }
        .stat { text-align: center; }
        .stat-value { font-size: 1.3rem; font-weight: bold; color: #E95420; }
        .stat-label { font-size: 0.7rem; color: #888; }
        
        .table-container {
            max-height: 350px;
            overflow-y: auto;
            border-radius: 12px;
        }
        
        .tooltip {
            position: relative;
            cursor: help;
        }
        .tooltip:hover::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 0;
            background: #000;
            color: #fff;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.75rem;
            white-space: nowrap;
            z-index: 100;
            max-width: 300px;
            white-space: normal;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📬 AI Mail Redirection Agent</h1>
            <div style="display:flex;align-items:center;gap:20px;">
                <div class="status">
                    <div class="status-dot" id="statusDot"></div>
                    <span id="statusText">Stopped</span>
                </div>
            </div>
        </header>
        
        <div class="main-grid">
            <div class="left-panel">
            <div class="info-bar">
                    <div><span>Account:</span> <strong id="account">-</strong></div>
                    <div><span>AI:</span> <strong id="aiModel">-</strong></div>
                    <div><span>Host:</span> <strong id="ollamaHost">-</strong></div>
                    <div><span>Categories:</span> <strong id="categories">-</strong></div>
                </div>
                
                <div class="controls">
                    <button class="btn-primary" id="startBtn" onclick="startWatching()">▶ Start</button>
                    <button class="btn-danger" id="stopBtn" onclick="stopWatching()" style="display:none">⏹ Stop</button>
                    <button class="btn-secondary" onclick="refreshOnce()">🔄 Refresh</button>
                    <button class="btn-secondary" onclick="clearTerminal()">🗑 Clear Log</button>
                    <button class="btn-danger" onclick="shutdownServer()">⏻ Shutdown</button>
                </div>
                
                <div class="tabs">
                    <button class="tab-btn active" onclick="switchTab('emails', this)">📧 Emails</button>
                    <button class="tab-btn" onclick="switchTab('logs', this)">📊 Logs</button>
                </div>
                
                <div id="emailsTab" class="tab-content active">
                    <div class="filter-bar">
                        <span class="filter-label">Filter:</span>
                        <button class="filter-btn active" onclick="setFilter('all')">All</button>
                        <button class="filter-btn" onclick="setFilter('review')">⚠ Pending Review</button>
                        <button class="filter-btn" onclick="setFilter('forwarded')">✓ Forwarded</button>
                        <button class="filter-btn" onclick="setFilter('skipped')">★ Skipped</button>
                    </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>From</th>
                                <th>Subject</th>
                                <th>Status</th>
                                <th>Category</th>
                                <th>Conf</th>
                                <th>Forward To</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody id="emailTable">
                            <tr><td colspan="7" style="text-align:center;color:#888;">No emails loaded</td></tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="stats">
                    <div class="stat"><div class="stat-value" id="statTotal">0</div><div class="stat-label">Total</div></div>
                    <div class="stat"><div class="stat-value" id="statForwarded">0</div><div class="stat-label">Forwarded</div></div>
                    <div class="stat"><div class="stat-value" id="statSkipped">0</div><div class="stat-label">Skipped</div></div>
                    <div class="stat"><div class="stat-value" id="statReview">0</div><div class="stat-label">Review</div></div>
                    <div class="stat"><div class="stat-value" id="statErrors">0</div><div class="stat-label">Errors</div></div>
                </div>
                </div><!-- end emailsTab -->
                
                <div id="logsTab" class="tab-content">
                    <div class="filter-bar">
                        <span class="filter-label">Session:</span>
                        <select id="logSessionSelect" onchange="loadLogSession()" style="min-width:200px;"></select>
                        <button class="btn-secondary" onclick="loadLogSessions()">🔄 Refresh</button>
                        <button class="btn-primary" onclick="downloadLogs()">⬇ Download Log</button>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Time</th>
                                    <th>From</th>
                                    <th>Subject</th>
                                    <th>Action</th>
                                    <th>Category</th>
                                    <th>Forward To</th>
                                    <th>Conf</th>
                                </tr>
                            </thead>
                            <tbody id="logTableBody">
                                <tr><td colspan="7" style="text-align:center;color:#888;">Select a session</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="stats">
                        <div class="stat"><div class="stat-value" id="logStatTotal">0</div><div class="stat-label">Total</div></div>
                        <div class="stat"><div class="stat-value" id="logStatForward">0</div><div class="stat-label">Forwarded</div></div>
                        <div class="stat"><div class="stat-value" id="logStatSpam">0</div><div class="stat-label">Spam</div></div>
                        <div class="stat"><div class="stat-value" id="logStatReview">0</div><div class="stat-label">Review</div></div>
                    </div>
                </div><!-- end logsTab -->
            </div>
            
            <div class="right-panel">
                <div class="terminal-container">
                    <div class="terminal-header">
                        <div class="terminal-dot red"></div>
                        <div class="terminal-dot yellow"></div>
                        <div class="terminal-dot green"></div>
                        <span class="terminal-title">Terminal — Mail Agent</span>
                    </div>
                    <div class="terminal-body" id="terminal"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const socket = io();
        const terminal = document.getElementById('terminal');
        
        function termPrint(text, className = '') {
            const line = document.createElement('div');
            line.className = 'terminal-line ' + className;
            line.textContent = text;
            terminal.appendChild(line);
            terminal.scrollTop = terminal.scrollHeight;
        }
        
        function clearTerminal() {
            terminal.innerHTML = '';
            termPrint('╔══════════════════════════════════════════╗', 'header');
            termPrint('║     AI Mail Redirection Agent            ║', 'header');
            termPrint('╚══════════════════════════════════════════╝', 'header');
            termPrint('Terminal cleared.', 'dim');
        }
        
        socket.on('connect', () => {
            termPrint('╔══════════════════════════════════════════╗', 'header');
            termPrint('║     AI Mail Redirection Agent            ║', 'header');
            termPrint('╚══════════════════════════════════════════╝', 'header');
            termPrint('Connected to server.', 'success');
            socket.emit('get_config');
        });
        
        socket.on('config', data => {
            document.getElementById('account').textContent = data.account;
            document.getElementById('aiModel').textContent = data.ai_model;
            document.getElementById('ollamaHost').textContent = data.ollama_host;
            document.getElementById('categories').textContent = data.categories;
            termPrint(`Account: ${data.account}`, 'info');
            termPrint(`AI: ${data.ai_model} @ ${data.ollama_host}`, 'info');
            termPrint('Ready.', 'prompt');
            
        });
        
        socket.on('status', data => {
            const dot = document.getElementById('statusDot');
            const text = document.getElementById('statusText');
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            
            if (data.running) {
                dot.classList.add('running');
                text.textContent = 'Running';
                startBtn.style.display = 'none';
                stopBtn.style.display = 'inline-block';
            } else {
                dot.classList.remove('running');
                text.textContent = 'Stopped';
                startBtn.style.display = 'inline-block';
                stopBtn.style.display = 'none';
            }
        });
        
        socket.on('emails', data => {
            window.emailsData = data;
            renderEmailTable(data);
        });
        
        socket.on('terminal', data => {
            termPrint(data.text, data.type || '');
        });
        
        socket.on('shutdown', () => {
            termPrint('Server shutting down...', 'error');
            setTimeout(() => { window.close(); }, 1000);
        });
        
        function startWatching() { socket.emit('start'); }
        function stopWatching() { socket.emit('stop'); }
        function refreshOnce() { socket.emit('refresh'); }
        
        // Track current email for auto-advance
        let currentEmailUid = null;
        
        function approveEmail(uid) { 
            socket.emit('approve', {uid: uid}); 
            advanceToNextReview(uid);
        }
        function rejectEmail(uid) { 
            socket.emit('reject', {uid: uid}); 
            advanceToNextReview(uid);
        }
        
        function advanceToNextReview(currentUid) {
            // Find next email that needs review
            const reviewEmails = window.emailsData.filter(e => e.needs_review && e.uid != currentUid);
            if (reviewEmails.length > 0) {
                // Open next review email
                setTimeout(() => openEmail(reviewEmails[0].uid), 300);
            } else {
                closeModal();
            }
        }
        
        function shutdownServer() { 
            if (confirm('Shutdown the mail agent server?')) {
                socket.emit('shutdown'); 
            }
        }
        
        // Filter functionality
        let currentFilter = 'all';
        
        function setFilter(filter) {
            currentFilter = filter;
            // Update button states
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            // Re-render table
            if (window.emailsData) {
                renderEmailTable(window.emailsData);
            }
        }
        
        // Tab switching
        function switchTab(tab, btn) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(tab + 'Tab').classList.add('active');
            
            if (tab === 'logs') {
                loadLogSessions();
            }
        }
        
        // Log viewer functions
        let logData = [];
        
        async function loadLogSessions() {
            try {
                const resp = await fetch('/api/log-sessions');
                const sessions = await resp.json();
                const select = document.getElementById('logSessionSelect');
                select.innerHTML = sessions.map(s => 
                    `<option value="${s.session_id}">${s.session_id}</option>`
                ).join('') || '<option value="">No sessions</option>';
                if (sessions.length > 0) loadLogSession();
            } catch(e) { console.error(e); }
        }
        
        async function loadLogSession() {
            const session = document.getElementById('logSessionSelect').value;
            if (!session) return;
            try {
                const resp = await fetch('/api/logs?session=' + session);
                logData = await resp.json();
                renderLogTable();
            } catch(e) { console.error(e); }
        }
        
        function renderLogTable() {
            const table = document.getElementById('logTableBody');
            let forward = 0, spam = 0, review = 0;
            
            logData.forEach(l => {
                const action = l.final_action || l.action || '';
                if (action.includes('forward')) forward++;
                if (action.includes('spam') || l.category === 'spam') spam++;
                if (action.includes('review')) review++;
            });
            
            document.getElementById('logStatTotal').textContent = logData.length;
            document.getElementById('logStatForward').textContent = forward;
            document.getElementById('logStatSpam').textContent = spam;
            document.getElementById('logStatReview').textContent = review;
            
            if (logData.length === 0) {
                table.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#888;">No logs in this session</td></tr>';
                return;
            }
            
            table.innerHTML = logData.map(l => {
                const time = l.timestamp?.substring(11, 19) || '-';
                const from = (l.from_addr || '-').substring(0, 25);
                const subj = (l.subject || '-').substring(0, 35);
                const action = l.final_action || l.action || '-';
                const cat = l.ai_category || l.category || '-';
                const fwd = l.forward_destinations?.join(', ') || l.forward_to || '-';
                const conf = Math.round((l.ai_confidence || l.confidence || 0) * 100);
                return `<tr><td>${time}</td><td>${from}</td><td>${subj}</td><td>${action}</td><td>${cat}</td><td>${fwd}</td><td>${conf}%</td></tr>`;
            }).join('');
        }
        
        function downloadLogs() {
            const session = document.getElementById('logSessionSelect').value;
            if (session) {
                window.location.href = '/api/logs/download?session=' + session;
            }
        }
        
        function renderEmailTable(data) {
            const table = document.getElementById('emailTable');
            let forwarded = 0, skipped = 0, errors = 0, review = 0;
            
            // Apply filter
            const filtered = data.filter(e => {
                if (currentFilter === 'all') return true;
                if (currentFilter === 'review') return e.needs_review;
                if (currentFilter === 'forwarded') return e.status === 'Forwarded';
                if (currentFilter === 'skipped') return e.status === 'Skipped';
                return true;
            });
            
            // Count totals from all data
            data.forEach(e => {
                if (e.status === 'Forwarded') forwarded++;
                if (e.status === 'Skipped') skipped++;
                if (e.status === 'Error') errors++;
                if (e.needs_review) review++;
            });
            
            if (filtered.length === 0) {
                table.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#888;">No emails match filter</td></tr>';
            } else {
                table.innerHTML = filtered.map(e => {
                    const statusClass = e.needs_review ? 'status-review' : 'status-' + e.status.toLowerCase();
                    const confWidth = (e.confidence * 100) + '%';
                    const confClass = e.confidence < 0.5 ? 'low' : '';
                    const forwardTo = e.forward_to.join(', ') || '-';
                    const rowClass = e.needs_review ? 'needs-review' : '';
                    
                    let actionBtns = '';
                    if (e.needs_review) {
                        actionBtns = `
                            <button class="btn-sm btn-approve" onclick="approveEmail('${e.uid}')">✓</button>
                            <button class="btn-sm btn-reject" onclick="rejectEmail('${e.uid}')">✗</button>
                        `;
                    } else if (e.status === 'Forwarded') {
                        actionBtns = '✓';
                    } else if (e.status === 'Skipped') {
                        actionBtns = '–';
                    }
                    
                    const reasoningTooltip = e.reasoning ? `data-tooltip="${e.reasoning}"` : '';
                    
                    return `<tr class="${rowClass}" onclick="openEmail('${e.uid}')">
                        <td>${e.from_addr.slice(0,18)}</td>
                        <td title="${e.subject}">${e.subject.slice(0,30)}</td>
                        <td><span class="status-badge ${statusClass}">${e.needs_review ? 'Review' : e.status}</span></td>
                        <td class="tooltip" ${reasoningTooltip}>${e.category}</td>
                        <td><div class="confidence-bar"><div class="confidence-fill ${confClass}" style="width:${confWidth}"></div></div> ${Math.round(e.confidence*100)}%</td>
                        <td>${forwardTo.slice(0,22)}</td>
                        <td class="action-btns" onclick="event.stopPropagation()">${actionBtns}</td>
                    </tr>`;
                }).join('');
            }
            
            document.getElementById('statTotal').textContent = data.length;
            document.getElementById('statForwarded').textContent = forwarded;
            document.getElementById('statSkipped').textContent = skipped;
            document.getElementById('statReview').textContent = review;
            document.getElementById('statErrors').textContent = errors;
        }
        
        // Modal functions
        function openEmail(uid) {
            const email = window.emailsData.find(e => e.uid == uid);
            if (!email) return;
            
            document.getElementById('modalFrom').textContent = email.from_addr;
            document.getElementById('modalSubject').textContent = email.subject;
            document.getElementById('modalBody').textContent = email.body || '(No body)';
            document.getElementById('modalCategory').textContent = email.category || 'unknown';
            document.getElementById('modalConfidence').textContent = Math.round(email.confidence * 100) + '%';
            document.getElementById('modalReasoning').textContent = email.reasoning || '-';
            document.getElementById('modalForwardTo').textContent = email.forward_to.join(', ') || '-';
            document.getElementById('modalStatus').textContent = email.status;
            
            // Track current email for prev/next navigation
            currentEmailUid = email.uid;
            
            // Show/hide action buttons based on status
            const approveBtn = document.getElementById('modalApproveBtn');
            const rejectBtn = document.getElementById('modalRejectBtn');
            if (email.needs_review) {
                approveBtn.style.display = 'inline-block';
                rejectBtn.style.display = 'inline-block';
                approveBtn.onclick = () => approveEmail(email.uid);
                rejectBtn.onclick = () => rejectEmail(email.uid);
            } else {
                approveBtn.style.display = 'none';
                rejectBtn.style.display = 'none';
            }
            
            document.getElementById('emailModal').style.display = 'flex';
        }
        
        function prevEmail() {
            if (!window.emailsData || !currentEmailUid) return;
            const currentIdx = window.emailsData.findIndex(e => e.uid == currentEmailUid);
            if (currentIdx > 0) {
                openEmail(window.emailsData[currentIdx - 1].uid);
            }
        }
        
        function nextEmail() {
            if (!window.emailsData || !currentEmailUid) return;
            const currentIdx = window.emailsData.findIndex(e => e.uid == currentEmailUid);
            if (currentIdx < window.emailsData.length - 1) {
                openEmail(window.emailsData[currentIdx + 1].uid);
            }
        }
        
        function closeModal() {
            document.getElementById('emailModal').style.display = 'none';
            currentEmailUid = null;
        }
        
        // Close modal on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });
    </script>
    
    <!-- Email Modal -->
    <div id="emailModal" class="modal" onclick="if(event.target===this)closeModal()">
        <div class="modal-content">
            <div class="modal-header">
                <h2>📧 Email Details</h2>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <div class="modal-body">
                <div class="modal-field">
                    <label>From:</label>
                    <span id="modalFrom"></span>
                </div>
                <div class="modal-field">
                    <label>Subject:</label>
                    <span id="modalSubject"></span>
                </div>
                <div class="modal-field">
                    <label>Status:</label>
                    <span id="modalStatus"></span>
                </div>
                <div class="modal-field">
                    <label>AI Category:</label>
                    <span id="modalCategory"></span> (<span id="modalConfidence"></span>)
                </div>
                <div class="modal-field">
                    <label>Forward To:</label>
                    <span id="modalForwardTo"></span>
                </div>
                <div class="modal-field">
                    <label>AI Reasoning:</label>
                    <span id="modalReasoning"></span>
                </div>
                <div class="modal-body-content">
                    <label>Body:</label>
                    <pre id="modalBody"></pre>
                </div>
            </div>
            <div class="modal-footer">
                <div style="display:flex;gap:8px;">
                    <button id="modalPrevBtn" class="btn-secondary" onclick="prevEmail()">← Prev</button>
                    <button id="modalNextBtn" class="btn-secondary" onclick="nextEmail()">Next →</button>
                </div>
                <div style="display:flex;gap:8px;">
                    <button id="modalApproveBtn" class="btn-primary btn-approve">✓ Approve & Forward</button>
                    <button id="modalRejectBtn" class="btn-danger">✗ Reject / Skip</button>
                    <button class="btn-secondary" onclick="closeModal()">Close</button>
                </div>
            </div>
        </div>
    </div>
    
    <style>
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-content {
            background: #1a1a2e;
            border-radius: 12px;
            width: 90%;
            max-width: 800px;
            max-height: 90vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: rgba(255,255,255,0.05);
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .modal-header h2 { 
            font-size: 1.2rem; 
            color: #E95420;
        }
        .modal-close {
            background: none;
            border: none;
            font-size: 1.5rem;
            color: #888;
            cursor: pointer;
        }
        .modal-close:hover { color: #fff; }
        .modal-body {
            padding: 20px;
            overflow-y: auto;
            flex: 1;
        }
        .modal-field {
            margin-bottom: 12px;
        }
        .modal-field label {
            color: #E95420;
            font-weight: 600;
            display: inline-block;
            width: 100px;
        }
        .modal-field span {
            color: #e0e0e0;
        }
        .modal-body-content {
            margin-top: 15px;
        }
        .modal-body-content label {
            color: #E95420;
            font-weight: 600;
            display: block;
            margin-bottom: 8px;
        }
        .modal-body-content pre {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 8px;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Consolas', monospace;
            font-size: 0.85rem;
            color: #ccc;
            max-height: 300px;
            overflow-y: auto;
        }
        .modal-footer {
            padding: 15px 20px;
            background: rgba(255,255,255,0.05);
            border-top: 1px solid rgba(255,255,255,0.1);
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }
        tr { cursor: pointer; }
        tr:hover { background: rgba(255,255,255,0.05) !important; }
        
        .filter-bar {
            display: flex;
            gap: 8px;
            align-items: center;
            margin-bottom: 15px;
            padding: 10px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
        }
        .filter-label {
            color: #888;
            font-size: 0.85rem;
            margin-right: 5px;
        }
        .filter-btn {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            color: #aaa;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.2s;
        }
        .filter-btn:hover {
            background: rgba(255,255,255,0.15);
            color: #fff;
        }
        .filter-btn.active {
            background: #E95420;
            border-color: transparent;
            color: #fff;
        }
    </style>
</body>
</html>
'''



def term_print(text, msg_type=''):
    """Send terminal message to clients."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    socketio.emit('terminal', {'text': f'[{timestamp}] {text}', 'type': msg_type})


def process_emails():
    """Fetch and process unread emails."""
    global emails_data, pending_reviews, config
    
    term_print("Checking for new emails...", "info")
    
    try:
        router = Router(
            rules=config.rules,
            ai_enabled=config.ai_routing.enabled,
            gemini_api_key=config.gemini_api_key,
            ollama_model=config.ollama_model,
            ai_destinations=config.ai_routing.destinations,
            default_action=config.default_action,
            company_name=config.company.name,
            company_mailbox=config.company.mailbox,
        )
        
        smtp = SMTPClient(
            host=config.email.smtp_host,
            port=config.email.smtp_port,
            address=config.email.address,
            password=config.email.password,
            use_tls=config.email.use_tls,
        )
        
        imap = IMAPClient(
            host=config.email.imap_host,
            port=config.email.imap_port,
            address=config.email.address,
            password=config.email.password,
            use_ssl=config.email.use_ssl,
            use_starttls=config.email.use_starttls,
        )
        
        with imap:
            # Pre-create all folders at startup
            for folder in ["Processed", "Review", "Skipped", "Quarantine"]:
                if not imap._client.folder_exists(folder):
                    imap._client.create_folder(folder)
            
            # Load existing emails from Review folder (persisted from previous sessions)
            existing_uids = {e.uid for e in emails_data}
            review_emails = list(imap.fetch_from_folder("Review"))
            for e in review_emails:
                if e.uid not in existing_uids:
                    emails_data.append(EmailStatus(
                        uid=e.uid,
                        from_addr=e.from_addr,
                        subject=e.subject,
                        body=e.body,
                        status="Review",
                        needs_review=True
                    ))
                    existing_uids.add(e.uid)
                
                # Also add to pending_reviews so they can be approved/rejected
                if e.uid not in pending_reviews:
                    pending_reviews[e.uid] = {
                        'email': e,
                        'decision': None,  # No AI decision for existing Review emails
                        'smtp': smtp,
                        'imap': imap
                    }
            
            emails = list(imap.fetch_unread())
            
            if not emails and not review_emails:
                term_print("No unread emails.", "dim")
                socketio.emit('emails', [asdict(e) for e in emails_data])
                return
            elif not emails:
                term_print(f"No new emails. {len(review_emails)} in Review folder.", "dim")
                socketio.emit('emails', [asdict(e) for e in emails_data])
                return
            
            term_print(f"Found {len(emails)} unread email(s)", "success")
            
            # Add new emails to list (don't replace) - use existing_uids from above
            new_emails = [e for e in emails if e.uid not in existing_uids]
            
            if not new_emails:
                term_print("No new emails to process.", "dim")
                socketio.emit('emails', [asdict(e) for e in emails_data])
                return
            
            # Add new emails to tracking list
            for e in new_emails:
                emails_data.append(EmailStatus(
                    uid=e.uid,
                    from_addr=e.from_addr,
                    subject=e.subject,
                    body=e.body,
                    status="Pending"
                ))
            
            socketio.emit('emails', [asdict(e) for e in emails_data])
            
            # Process each NEW email - ALL go to Review for user approval
            for idx, email in enumerate(new_emails):
                # Find index in emails_data
                email_idx = next(i for i, e in enumerate(emails_data) if e.uid == email.uid)
                
                emails_data[email_idx].status = "Processing"
                socketio.emit('emails', [asdict(e) for e in emails_data])
                
                decision = router.decide(email)
                
                # Store AI reasoning
                if decision.ai_result:
                    emails_data[email_idx].category = decision.ai_result.category
                    emails_data[email_idx].confidence = decision.ai_result.confidence
                    emails_data[email_idx].reasoning = decision.ai_result.reasoning
                
                # Auto-approve if confidence > 80% and has a destination
                if decision.ai_result and decision.ai_result.confidence > 0.80 and decision.should_forward:
                    # Check if it's a quarantine (spam/phishing)
                    is_quarantine = decision.ai_result.category == "quarantine"
                    
                    # Auto-forward
                    try:
                        all_destinations = decision.all_destinations
                        for dest in all_destinations:
                            smtp.forward_email(email, dest)
                        
                        # Move to appropriate folder
                        if is_quarantine:
                            imap.move_email(email.uid, "Quarantine")
                            emails_data[email_idx].status = "Quarantined"
                            term_print(f"═" * 60, "header")
                            term_print(f"[{idx+1}/{len(new_emails)}] 🚨 QUARANTINED ({decision.ai_result.confidence:.0%})", "error")
                        else:
                            imap.move_email(email.uid, "Processed")
                            emails_data[email_idx].status = "Forwarded"
                            term_print(f"═" * 60, "header")
                            term_print(f"[{idx+1}/{len(new_emails)}] ✓ AUTO-APPROVED ({decision.ai_result.confidence:.0%})", "success")
                        
                        emails_data[email_idx].forward_to = all_destinations
                        
                        dest_str = ", ".join(all_destinations)
                        term_print(f"From: {email.from_addr}", "info")
                        term_print(f"Subject: {email.subject}", "info")
                        term_print(f"→ {dest_str}", "success" if not is_quarantine else "error")
                        term_print(f"💭 {decision.ai_result.reasoning}", "reasoning")
                        
                        # Log to file
                        log_email(
                            uid=email.uid,
                            from_addr=email.from_addr,
                            to_addr=config.email.address,
                            subject=email.subject,
                            body=email.body,
                            ai_action="spam" if is_quarantine else "forward",
                            ai_route_to=decision.ai_result.forward_to if decision.ai_result else None,
                            ai_category=decision.ai_result.category if decision.ai_result else "",
                            ai_confidence=decision.ai_result.confidence if decision.ai_result else 0,
                            ai_reason=decision.ai_result.reasoning if decision.ai_result else "",
                            ai_raw_response="",
                            final_action="quarantined" if is_quarantine else "forwarded",
                            forward_destinations=all_destinations,
                        )
                        
                    except Exception as e:
                        emails_data[email_idx].status = "Error"
                        term_print(f"[{idx+1}/{len(new_emails)}] ✗ Error: {e}", "error")
                
                else:
                    # Needs manual review (low confidence or uncategorized)
                    emails_data[email_idx].status = "Review"
                    emails_data[email_idx].needs_review = True
                    emails_data[email_idx].forward_to = decision.all_destinations if decision.should_forward else []
                    
                    # Move to Review folder (persists on restart)
                    imap.move_email(email.uid, "Review")
                    
                    pending_reviews[email.uid] = {
                        'email': email,
                        'decision': decision,
                        'smtp': smtp,
                        'imap': imap
                    }
                    
                    # Show FULL email content in log
                    term_print(f"═" * 60, "header")
                    conf_pct = decision.ai_result.confidence if decision.ai_result else 0
                    term_print(f"[{idx+1}/{len(new_emails)}] ⚠ NEEDS REVIEW ({conf_pct:.0%})", "error")
                    term_print(f"─" * 60, "dim")
                    term_print(f"From: {email.from_addr}", "info")
                    term_print(f"Subject: {email.subject}", "info")
                    term_print(f"─" * 60, "dim")
                    for line in email.body.split('\n')[:30]:
                        term_print(f"  {line}", "dim")
                    if len(email.body.split('\n')) > 30:
                        term_print(f"  ... ({len(email.body.split(chr(10))) - 30} more lines)", "dim")
                    term_print(f"─" * 60, "dim")
                    
                    if decision.ai_result:
                        if decision.should_forward:
                            dest_str = ", ".join(decision.all_destinations)
                            term_print(f"🤖 AI Suggests: {decision.ai_result.category.upper()} → {dest_str}", "success")
                        else:
                            term_print(f"🤖 AI Suggests: UNCATEGORIZED (no forward)", "error")
                        term_print(f"   💭 {decision.ai_result.reasoning}", "reasoning")
                    
                    term_print(f"   ⏳ Waiting for user approval...", "prompt")
                
                socketio.emit('emails', [asdict(e) for e in emails_data])
            
            forwarded = sum(1 for e in emails_data if e.status == "Forwarded")
            review = sum(1 for e in emails_data if e.needs_review)
            term_print(f"═" * 60, "header")
            term_print(f"Done. Auto-forwarded: {forwarded} | Needs review: {review}", "success")
                
    except Exception as e:
        term_print(f"Error: {e}", "error")


def watch_loop():
    """Background watching loop."""
    global is_running
    while is_running:
        process_emails()
        term_print("Waiting 30s...", "dim")
        time.sleep(30)


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/log-sessions')
def api_log_sessions():
    """List all available log sessions."""
    from pathlib import Path
    log_dir = Path(__file__).parent / "logs"
    sessions = []
    if log_dir.exists():
        for f in sorted(log_dir.glob("email_log_*.jsonl"), reverse=True):
            session_id = f.stem.replace("email_log_", "")
            sessions.append({
                "session_id": session_id,
                "size": f.stat().st_size,
            })
    return jsonify(sessions)


@app.route('/api/logs')
def api_logs():
    """Get logs for a specific session."""
    try:
        from pathlib import Path
        session_id = request.args.get('session', '')
        if not session_id:
            return jsonify([])
        
        log_dir = Path(__file__).parent / "logs"
        log_file = log_dir / f"email_log_{session_id}.jsonl"
        
        logs = []
        if log_file.exists():
            with open(log_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            logs.append(json.loads(line))
                        except:
                            pass
        return jsonify(logs)
    except Exception as e:
        print(f"Error in /api/logs: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/logs/download')
def api_download_logs():
    """Download a log file."""
    from pathlib import Path
    from flask import send_file
    session_id = request.args.get('session', '')
    log_dir = Path(__file__).parent / "logs"
    log_file = log_dir / f"email_log_{session_id}.jsonl"
    
    if log_file.exists():
        return send_file(log_file, as_attachment=True, download_name=f"email_log_{session_id}.jsonl")
    return jsonify({"error": "Log file not found"}), 404


@socketio.on('get_config')
def send_config():
    global config
    config = load_config()
    ai_model = config.ollama_model if config.ollama_model else "Gemini"
    ollama_host = os.getenv("OLLAMA_HOST", "localhost:11434")
    socketio.emit('config', {
        'account': config.email.address,
        'ai_model': ai_model,
        'ollama_host': ollama_host,
        'categories': len(config.ai_routing.destinations)
    })
    socketio.emit('status', {'running': is_running})


@socketio.on('start')
def start_watching():
    global is_running
    if not is_running:
        is_running = True
        socketio.emit('status', {'running': True})
        term_print("Started watching inbox...", "success")
        thread = threading.Thread(target=watch_loop, daemon=True)
        thread.start()


@socketio.on('stop')
def stop_watching():
    global is_running
    is_running = False
    socketio.emit('status', {'running': False})
    term_print("Stopped.", "info")


@socketio.on('refresh')
def refresh_once():
    thread = threading.Thread(target=process_emails, daemon=True)
    thread.start()


@socketio.on('approve')
def approve_email(data):
    """Approve and forward a pending review email."""
    global emails_data, pending_reviews
    uid = data.get('uid')
    
    # Convert to int if string
    try:
        uid = int(uid)
    except (ValueError, TypeError):
        term_print(f"✗ Invalid uid: {uid}", "error")
        return
    
    term_print(f"Approving email uid={uid}...", "info")
    
    if uid not in pending_reviews:
        term_print(f"✗ Email not found in pending reviews (uid={uid})", "error")
        return
    
    review = pending_reviews[uid]
    email = review['email']
    decision = review['decision']
    
    try:
        smtp = SMTPClient(
            host=config.email.smtp_host,
            port=config.email.smtp_port,
            address=config.email.address,
            password=config.email.password,
            use_tls=config.email.use_tls,
        )
        
        imap = IMAPClient(
            host=config.email.imap_host,
            port=config.email.imap_port,
            address=config.email.address,
            password=config.email.password,
            use_ssl=config.email.use_ssl,
            use_starttls=config.email.use_starttls,
        )
        
        # Forward to all destinations
        # Handle None decision (emails from previous sessions with no AI analysis)
        destinations = []
        if decision and hasattr(decision, 'should_forward') and decision.should_forward:
            destinations = decision.all_destinations
        
        if not destinations:
            # If no AI destination, use the one shown in UI
            for e in emails_data:
                if e.uid == uid and e.forward_to:
                    destinations = e.forward_to
                    break
        
        if destinations:
            for dest in destinations:
                smtp.forward_email(email, dest)
            dest_str = ", ".join(destinations)
            term_print(f"✓ Approved & forwarded: {email.subject[:30]} → {dest_str}", "success")
            
            # Move from Review folder to Processed folder
            with imap:
                imap.move_email(uid, "Processed", source_folder="Review")
        else:
            term_print(f"✓ Approved (no destination): {email.subject[:30]}", "success")
        
        # Update status
        for e in emails_data:
            if e.uid == uid:
                e.status = "Forwarded"
                e.needs_review = False
                e.forward_to = destinations
                break
        
        # Log the action
        log_action(uid, "approved", destinations)
        
        del pending_reviews[uid]
        socketio.emit('emails', [asdict(e) for e in emails_data])
        
    except Exception as e:
        term_print(f"✗ Error approving: {e}", "error")


@socketio.on('reject')
def reject_email(data):
    """Reject/skip a pending review email."""
    global emails_data, pending_reviews
    uid = data.get('uid')
    
    # Convert to int if string
    try:
        uid = int(uid)
    except (ValueError, TypeError):
        term_print(f"✗ Invalid uid: {uid}", "error")
        return
    
    term_print(f"Rejecting email uid={uid}...", "info")
    
    if uid not in pending_reviews:
        term_print(f"✗ Email not found in pending reviews (uid={uid})", "error")
        return
    
    email = pending_reviews[uid]['email']
    
    # Move from Review folder to Skipped folder
    try:
        imap = IMAPClient(
            host=config.email.imap_host,
            port=config.email.imap_port,
            address=config.email.address,
            password=config.email.password,
            use_ssl=config.email.use_ssl,
            use_starttls=config.email.use_starttls,
        )
        with imap:
            imap.move_email(uid, "Skipped", source_folder="Review")
    except Exception as e:
        term_print(f"Warning: Could not move to Skipped folder: {e}", "dim")
    
    # Update status
    for e in emails_data:
        if e.uid == uid:
            e.status = "Skipped"
            e.needs_review = False
            break
    
    # Log the action
    log_action(uid, "rejected")
    
    del pending_reviews[uid]
    term_print(f"✗ Rejected: {email.subject[:30]} → Skipped folder", "dim")
    socketio.emit('emails', [asdict(e) for e in emails_data])


@socketio.on('shutdown')
def shutdown_server():
    term_print("Shutting down server...", "error")
    socketio.emit('shutdown')
    socketio.sleep(1)
    os._exit(0)


if __name__ == '__main__':
    print("\n" + "="*50)
    print("  AI Mail Redirection Agent - Web Dashboard")
    print("="*50)
    print("\n  Open in browser: http://localhost:5000\n")
    print("="*50 + "\n")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)

import os
import sys
import shutil
from datetime import datetime

import fastf1
import numpy as np
import pandas as pd
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "f1_cache")
MAX_CACHE_SIZE_MB = 400
MAX_CACHED_SESSIONS = 2

def check_and_clear_cache():
		if not os.path.exists(CACHE_DIR):
				os.makedirs(CACHE_DIR)
				return

		total_size = sum(
				os.path.getsize(os.path.join(dirpath, filename))
				for dirpath, dirnames, filenames in os.walk(CACHE_DIR)
				for filename in filenames
		)

		size_mb = total_size / (1024 * 1024)
		print(f"Cache size: {size_mb:.1f}MB")

		if size_mb > MAX_CACHE_SIZE_MB:
				print(f"Cache exceeds {MAX_CACHE_SIZE_MB}MB. Clearing...")
				shutil.rmtree(CACHE_DIR)
				os.makedirs(CACHE_DIR)

check_and_clear_cache()
fastf1.Cache.enable_cache(CACHE_DIR)

loaded_sessions = {}

def get_session_key(year, gp, session_type):
		return f"{year}_{gp}_{session_type}"

def load_session(year, gp, session_type):
		key = get_session_key(year, gp, session_type)

		if key not in loaded_sessions and len(loaded_sessions) >= MAX_CACHED_SESSIONS:
				oldest_key = next(iter(loaded_sessions))
				del loaded_sessions[oldest_key]
				print(f"Cleared cached session: {oldest_key}")

		if key not in loaded_sessions:
				session = fastf1.get_session(int(year), gp, session_type)
				session.load(telemetry=True, laps=True, weather=True)
				loaded_sessions[key] = session
		return loaded_sessions[key]

def clean_timedelta(df):
		df = df.copy()
		for col in df.columns:
				if pd.api.types.is_timedelta64_dtype(df[col]):
						df[col] = df[col].dt.total_seconds()
		return df

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
		<meta charset="UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
		<title>F1 Telemetry Analytics</title>
		<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
		<link rel="preconnect" href="https://fonts.googleapis.com">
		<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
		<style>
:root {
		--bg-dark: #0d0d0d;
		--bg-elevated: #1a1a1a;
		--bg-card: #222222;
		--border-subtle: #2a2a2a;
		--border-light: #3a3a3a;
		--text-primary: #ffffff;
		--text-secondary: #a3a3a3;
		--text-muted: #737373;
		--accent: #dc2626;
		--accent-hover: #b91c1c;
		--accent-soft: rgba(220, 38, 38, 0.1);
		--success: #10b981;
		--warning: #f59e0b;
		--info: #3b82f6;
}

* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
}

html {
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
}

body {
		font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
		background: var(--bg-dark);
		color: var(--text-primary);
		line-height: 1.6;
		font-size: 14px;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-dark); }
::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

.header {
		background: var(--bg-elevated);
		border-bottom: 1px solid var(--border-subtle);
		position: sticky;
		top: 0;
		z-index: 1000;
		backdrop-filter: blur(10px);
}

.header-content {
		max-width: 1400px;
		margin: 0 auto;
		padding: 1rem 1.5rem;
}

.header-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1rem;
}

.logo {
		display: flex;
		align-items: center;
		gap: 0.75rem;
}

.logo-mark {
		width: 32px;
		height: 32px;
		background: var(--accent);
		border-radius: 4px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: 700;
		font-size: 14px;
}

.logo-text {
		font-weight: 600;
		font-size: 15px;
		letter-spacing: -0.01em;
}

.session-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.375rem 0.75rem;
		background: var(--accent-soft);
		border: 1px solid var(--accent);
		border-radius: 6px;
		font-size: 12px;
		font-weight: 500;
		color: var(--accent);
}

.controls-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 0.75rem;
}

.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
}

.form-label {
		font-size: 11px;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
}

.form-select, .form-input {
		padding: 0.625rem 0.875rem;
		background: var(--bg-card);
		border: 1px solid var(--border-light);
		border-radius: 6px;
		color: var(--text-primary);
		font-size: 13px;
		font-family: inherit;
		transition: all 0.15s;
		-webkit-appearance: none;
		appearance: none;
}

.form-select {
		background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%23737373' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 0.75rem center;
		padding-right: 2.5rem;
}

.form-select:focus, .form-input:focus {
		outline: none;
		border-color: var(--accent);
}

.form-select:disabled {
		opacity: 0.5;
		cursor: not-allowed;
}

.btn {
		padding: 0.625rem 1.25rem;
		border: none;
		border-radius: 6px;
		font-size: 13px;
		font-weight: 500;
		font-family: inherit;
		cursor: pointer;
		transition: all 0.15s;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		white-space: nowrap;
}

.btn-primary {
		background: var(--accent);
		color: white;
}

.btn-primary:hover:not(:disabled) {
		background: var(--accent-hover);
}

.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
}

.btn-secondary {
		background: var(--bg-card);
		color: var(--text-primary);
		border: 1px solid var(--border-light);
}

.btn-secondary:hover {
		background: var(--bg-elevated);
		border-color: var(--text-muted);
}

.loading-overlay {
		position: fixed;
		inset: 0;
		background: rgba(13, 13, 13, 0.95);
		backdrop-filter: blur(4px);
		display: none;
		place-items: center;
		z-index: 9999;
}

.loading-overlay.active { display: grid; }

.loader { text-align: center; }

.spinner {
		width: 40px;
		height: 40px;
		margin: 0 auto 1rem;
		border: 2px solid var(--border-light);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.loader-text {
		font-size: 13px;
		color: var(--text-secondary);
		font-weight: 500;
}

.loader-subtext {
		font-size: 12px;
		color: var(--text-muted);
		margin-top: 0.25rem;
}

.container {
		max-width: 1400px;
		margin: 0 auto;
		padding: 1.5rem;
}

.section {
		display: none;
}

.section.active {
		display: block;
		animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
		from { opacity: 0; }
		to { opacity: 1; }
}

.section-header {
		margin-bottom: 1.5rem;
}

.section-title {
		font-size: 20px;
		font-weight: 600;
		letter-spacing: -0.02em;
		margin-bottom: 0.25rem;
}

.section-subtitle {
		font-size: 13px;
		color: var(--text-secondary);
}

.tabs {
		display: flex;
		gap: 0.25rem;
		border-bottom: 1px solid var(--border-subtle);
		margin-bottom: 1.5rem;
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
}

.tab {
		padding: 0.75rem 1.25rem;
		border: none;
		background: none;
		color: var(--text-secondary);
		font-size: 13px;
		font-weight: 500;
		font-family: inherit;
		cursor: pointer;
		border-bottom: 2px solid transparent;
		transition: all 0.15s;
		white-space: nowrap;
}

.tab:hover { color: var(--text-primary); }

.tab.active {
		color: var(--accent);
		border-bottom-color: var(--accent);
}

.tab-content {
		display: none;
}

.tab-content.active {
		display: block;
}

.card {
		background: var(--bg-card);
		border: 1px solid var(--border-subtle);
		border-radius: 8px;
		padding: 1.25rem;
		margin-bottom: 1rem;
}

.card-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1rem;
}

.card-title {
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
}

.grid {
		display: grid;
		gap: 1rem;
}

.grid-2 { grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
.grid-3 { grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); }
.grid-4 { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }

.chart-wrapper {
		position: relative;
		height: 300px;
}

.stat-card {
		background: var(--bg-elevated);
		border: 1px solid var(--border-subtle);
		border-radius: 6px;
		padding: 1rem;
		text-align: center;
}

.stat-label {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
		margin-bottom: 0.5rem;
}

.stat-value {
		font-size: 24px;
		font-weight: 600;
		letter-spacing: -0.02em;
		color: var(--accent);
}

.stat-unit {
		font-size: 12px;
		color: var(--text-secondary);
		margin-top: 0.25rem;
}

.pedals {
		display: flex;
		gap: 1.5rem;
		justify-content: center;
}

.pedal {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
}

.pedal-bar-wrap {
		width: 48px;
		height: 160px;
		background: var(--bg-elevated);
		border: 1px solid var(--border-subtle);
		border-radius: 6px;
		display: flex;
		flex-direction: column-reverse;
		overflow: hidden;
}

.pedal-bar {
		width: 100%;
		transition: height 0.05s linear;
}

#throttle-bar { background: linear-gradient(to top, var(--success), #059669); }
#brake-bar { background: linear-gradient(to top, var(--accent), #991b1b); }

.pedal-label {
		font-size: 11px;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-secondary);
}

.pedal-value {
		font-size: 13px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
}

.strategy-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
}

.strategy-row {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 0.875rem;
		background: var(--bg-elevated);
		border: 1px solid var(--border-subtle);
		border-radius: 6px;
}

.strategy-driver {
		min-width: 50px;
		font-weight: 600;
		font-size: 13px;
		font-variant-numeric: tabular-nums;
}

.strategy-stints {
		display: flex;
		gap: 2px;
		flex: 1;
		height: 24px;
		border-radius: 4px;
		overflow: hidden;
}

.stint {
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 10px;
		font-weight: 600;
		color: rgba(0,0,0,0.8);
		min-width: 24px;
}

.stint.SOFT { background: #dc2626; color: white; }
.stint.MEDIUM { background: #f59e0b; }
.stint.HARD { background: #e5e5e5; }
.stint.INTERMEDIATE { background: #10b981; }
.stint.WET { background: #3b82f6; color: white; }

.track-container {
		background: var(--bg-elevated);
		border: 1px solid var(--border-subtle);
		border-radius: 8px;
		padding: 1.5rem;
		display: flex;
		justify-content: center;
		align-items: center;
}

#track-canvas, #mini-track-canvas {
		max-width: 100%;
		height: auto;
}

.replay-controls {
		display: flex;
		gap: 0.75rem;
		align-items: center;
		flex-wrap: wrap;
		margin-bottom: 1rem;
}

.progress-wrap {
		width: 100%;
		margin-bottom: 1rem;
}

.progress-bar {
		width: 100%;
		height: 4px;
		-webkit-appearance: none;
		appearance: none;
		background: var(--bg-elevated);
		border-radius: 2px;
		outline: none;
		cursor: pointer;
}

.progress-bar::-webkit-slider-thumb {
		-webkit-appearance: none;
		width: 14px;
		height: 14px;
		background: var(--accent);
		border-radius: 50%;
		cursor: pointer;
}

.progress-bar::-moz-range-thumb {
		width: 14px;
		height: 14px;
		background: var(--accent);
		border-radius: 50%;
		border: none;
		cursor: pointer;
}

.welcome {
		text-align: center;
		padding: 3rem 1rem;
}

.welcome-title {
		font-size: 28px;
		font-weight: 600;
		letter-spacing: -0.02em;
		margin-bottom: 0.5rem;
}

.welcome-subtitle {
		font-size: 15px;
		color: var(--text-secondary);
		margin-bottom: 2rem;
}

.features {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
		max-width: 900px;
		margin: 0 auto;
}

.feature {
		padding: 1.5rem;
		background: var(--bg-card);
		border: 1px solid var(--border-subtle);
		border-radius: 8px;
		transition: border-color 0.15s;
}

.feature:hover {
		border-color: var(--border-light);
}

.feature-icon {
		font-size: 24px;
		margin-bottom: 0.75rem;
}

.feature-title {
		font-size: 14px;
		font-weight: 600;
		margin-bottom: 0.25rem;
}

.feature-desc {
		font-size: 12px;
		color: var(--text-secondary);
		line-height: 1.5;
}

.footer {
		text-align: center;
		padding: 2rem 1rem;
		border-top: 1px solid var(--border-subtle);
		margin-top: 3rem;
}

.footer-text {
		font-size: 12px;
		color: var(--text-muted);
}

.footer-link {
		color: var(--accent);
		text-decoration: none;
}

.footer-link:hover {
		text-decoration: underline;
}

@media (max-width: 768px) {
		.header-content { padding: 0.875rem 1rem; }
		.header-top { flex-direction: column; align-items: flex-start; gap: 0.75rem; }
		.controls-grid { grid-template-columns: 1fr; }
		.container { padding: 1rem; }
		.tabs { gap: 0; }
		.tab { padding: 0.625rem 1rem; font-size: 12px; }
		.grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
		.chart-wrapper { height: 250px; }
		.welcome { padding: 2rem 1rem; }
		.welcome-title { font-size: 22px; }
		.features { grid-template-columns: 1fr; }
		.replay-controls { flex-direction: column; align-items: stretch; }
}

@media (max-width: 480px) {
		body { font-size: 13px; }
		.section-title { font-size: 18px; }
		.chart-wrapper { height: 220px; }
		.stat-value { font-size: 20px; }
}
		</style>
</head>
<body>
		<header class="header">
				<div class="header-content">
						<div class="header-top">
								<div class="logo">
										<div class="logo-mark">F1</div>
										<span class="logo-text">Telemetry Analytics</span>
								</div>
								<div class="session-badge" id="session-info" style="display:none;">
										<svg width="12" height="12" fill="currentColor"><circle cx="6" cy="6" r="6"/></svg>
										<span id="session-name">No session loaded</span>
								</div>
						</div>
						<div class="controls-grid">
								<div class="form-group">
										<label class="form-label">Year</label>
										<select id="year-select" class="form-select"><option value="">Select year</option></select>
								</div>
								<div class="form-group">
										<label class="form-label">Grand Prix</label>
										<select id="gp-select" class="form-select" disabled><option value="">Select year first</option></select>
								</div>
								<div class="form-group">
										<label class="form-label">Session</label>
										<select id="session-select" class="form-select">
												<option value="R">Race</option>
												<option value="Q">Qualifying</option>
												<option value="FP1">Practice 1</option>
												<option value="FP2">Practice 2</option>
												<option value="FP3">Practice 3</option>
										</select>
								</div>
								<div class="form-group" style="align-self: flex-end;">
										<button id="load-btn" class="btn btn-primary" disabled>Load Session</button>
								</div>
						</div>
				</div>
		</header>

		<div class="loading-overlay" id="loading-overlay">
				<div class="loader">
						<div class="spinner"></div>
						<div class="loader-text">Loading data...</div>
						<div class="loader-subtext">This may take 30-60 seconds</div>
				</div>
		</div>

		<main class="container">
				<section class="section active" id="welcome-section">
						<div class="welcome">
								<h1 class="welcome-title">F1 Telemetry Analytics</h1>
								<p class="welcome-subtitle">Professional-grade analysis of Formula 1 race data</p>
								<div class="features">
										<div class="feature">
												<div class="feature-icon">📊</div>
												<div class="feature-title">Speed Analysis</div>
												<div class="feature-desc">Detailed speed traces and sector comparisons</div>
										</div>
										<div class="feature">
												<div class="feature-icon">🎬</div>
												<div class="feature-title">Live Replay</div>
												<div class="feature-desc">Replay laps with real-time telemetry</div>
										</div>
										<div class="feature">
												<div class="feature-icon">⚔️</div>
												<div class="feature-title">Driver Comparison</div>
												<div class="feature-desc">Compare performance between drivers</div>
										</div>
										<div class="feature">
												<div class="feature-icon">🔧</div>
												<div class="feature-title">Strategy View</div>
												<div class="feature-desc">Tire strategy and pit stop analysis</div>
										</div>
								</div>
						</div>
				</section>

				<section class="section" id="data-section">
						<nav class="tabs">
								<button class="tab active" data-view="speed">Speed</button>
								<button class="tab" data-view="replay">Live Replay</button>
								<button class="tab" data-view="compare">Compare</button>
								<button class="tab" data-view="laptimes">Lap Times</button>
								<button class="tab" data-view="positions">Positions</button>
								<button class="tab" data-view="strategy">Strategy</button>
								<button class="tab" data-view="track">Track Map</button>
						</nav>

						<div class="tab-content active" id="speed-view">
								<div class="section-header">
										<h2 class="section-title">Speed Analysis</h2>
										<p class="section-subtitle">Analyze driver speed throughout their fastest lap</p>
								</div>
								<div class="grid grid-3">
										<div class="form-group">
												<label class="form-label">Driver</label>
												<select id="speed-driver-select" class="form-select"><option value="">Select driver</option></select>
										</div>
										<div class="form-group" style="align-self: flex-end;">
												<button id="load-speed-btn" class="btn btn-secondary">Analyze</button>
										</div>
								</div>
								<div class="card">
										<div class="card-header"><div class="card-title">Speed Trace</div></div>
										<div class="chart-wrapper"><canvas id="speed-chart"></canvas></div>
								</div>
						</div>

						<div class="tab-content" id="replay-view">
								<div class="section-header">
										<h2 class="section-title">Live Replay</h2>
										<p class="section-subtitle">Watch lap replay with real-time telemetry data</p>
								</div>
								<div class="grid grid-3">
										<div class="form-group">
												<label class="form-label">Driver</label>
												<select id="replay-driver-select" class="form-select"><option value="">Select driver</option></select>
										</div>
										<div class="form-group" style="align-self: flex-end;">
												<button id="load-replay-btn" class="btn btn-secondary">Load Replay</button>
										</div>
								</div>
								<div class="card">
										<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin-bottom:1rem;">
												<div>
														<div class="form-label">Driver</div>
														<div style="font-size:15px; font-weight:600; margin-top:0.25rem;" id="replay-driver-name">-</div>
												</div>
												<div>
														<div class="form-label">Lap Time</div>
														<div style="font-size:15px; font-weight:600; margin-top:0.25rem; font-variant-numeric: tabular-nums;" id="replay-lap-time">-</div>
												</div>
												<div>
														<div class="form-label">Progress</div>
														<div style="font-size:15px; font-weight:600; margin-top:0.25rem;" id="replay-time">0%</div>
												</div>
										</div>
										<div class="replay-controls">
												<button id="replay-play-btn" class="btn btn-primary">Play</button>
												<button id="replay-reset-btn" class="btn btn-secondary">Reset</button>
												<div class="form-group" style="min-width:120px;">
														<label class="form-label">Speed</label>
														<select id="replay-speed-select" class="form-select">
																<option value="0.5">0.5x</option>
																<option value="1" selected>1x</option>
																<option value="2">2x</option>
																<option value="5">5x</option>
														</select>
												</div>
										</div>
										<div class="progress-wrap">
												<input type="range" id="replay-progress" class="progress-bar" min="0" max="100" value="0">
										</div>
										<div class="grid grid-4" style="margin-bottom:1rem;">
												<div class="stat-card">
														<div class="stat-label">Speed</div>
														<div class="stat-value" id="replay-speed-value">0</div>
														<div class="stat-unit">km/h</div>
												</div>
												<div class="stat-card">
														<div class="stat-label">Gear</div>
														<div class="stat-value" id="replay-gear-value">-</div>
												</div>
												<div class="stat-card">
														<div class="stat-label">RPM</div>
														<div class="stat-value" id="replay-rpm-value" style="font-size:18px;">0</div>
												</div>
												<div class="stat-card">
														<div class="stat-label">DRS</div>
														<div class="stat-value" id="replay-drs-value" style="font-size:14px;">OFF</div>
												</div>
										</div>
										<div class="grid grid-2">
												<div class="card">
														<div class="card-header"><div class="card-title">Pedal Inputs</div></div>
														<div class="pedals">
																<div class="pedal">
																		<div class="pedal-bar-wrap"><div class="pedal-bar" id="throttle-bar"></div></div>
																		<div class="pedal-label">Throttle</div>
																		<div class="pedal-value" id="replay-throttle-value">0%</div>
																</div>
																<div class="pedal">
																		<div class="pedal-bar-wrap"><div class="pedal-bar" id="brake-bar"></div></div>
																		<div class="pedal-label">Brake</div>
																		<div class="pedal-value" id="replay-brake-value">0%</div>
																</div>
														</div>
												</div>
												<div class="card">
														<div class="card-header"><div class="card-title">Track Position</div></div>
														<div style="display:flex; justify-content:center;">
																<canvas id="mini-track-canvas" width="400" height="300"></canvas>
														</div>
												</div>
										</div>
								</div>
						</div>

						<div class="tab-content" id="compare-view">
								<div class="section-header">
										<h2 class="section-title">Driver Comparison</h2>
										<p class="section-subtitle">Compare fastest laps between two drivers</p>
								</div>
								<div class="grid grid-3">
										<div class="form-group">
												<label class="form-label">Driver 1</label>
												<select id="compare-driver1" class="form-select"><option value="">Select driver</option></select>
										</div>
										<div class="form-group">
												<label class="form-label">Driver 2</label>
												<select id="compare-driver2" class="form-select"><option value="">Select driver</option></select>
										</div>
										<div class="form-group" style="align-self: flex-end;">
												<button id="compare-btn" class="btn btn-secondary">Compare</button>
										</div>
								</div>
								<div id="compare-result"></div>
								<div class="card">
										<div class="card-header"><div class="card-title">Speed Comparison</div></div>
										<div class="chart-wrapper"><canvas id="compare-chart"></canvas></div>
								</div>
						</div>

						<div class="tab-content" id="laptimes-view">
								<div class="section-header">
										<h2 class="section-title">Lap Times</h2>
										<p class="section-subtitle">Analyze lap time progression</p>
								</div>
								<div class="grid grid-3">
										<div class="form-group">
												<label class="form-label">Driver</label>
												<select id="laptimes-driver" class="form-select"><option value="">All drivers</option></select>
										</div>
										<div class="form-group" style="align-self: flex-end;">
												<button id="load-laptimes-btn" class="btn btn-secondary">Analyze</button>
										</div>
								</div>
								<div class="card">
										<div class="card-header"><div class="card-title">Lap Time Evolution</div></div>
										<div class="chart-wrapper" style="height:400px;"><canvas id="laptimes-chart"></canvas></div>
								</div>
						</div>

						<div class="tab-content" id="positions-view">
								<div class="section-header">
										<h2 class="section-title">Race Positions</h2>
										<p class="section-subtitle">Track position changes throughout the race</p>
								</div>
								<div class="grid grid-3">
										<div class="form-group">
												<label class="form-label">Driver</label>
												<select id="positions-driver" class="form-select"><option value="">All drivers</option></select>
										</div>
										<div class="form-group" style="align-self: flex-end;">
												<button id="load-positions-btn" class="btn btn-secondary">View</button>
										</div>
								</div>
								<div class="card">
										<div class="card-header"><div class="card-title">Position Changes</div></div>
										<div class="chart-wrapper" style="height:450px;"><canvas id="positions-chart"></canvas></div>
								</div>
						</div>

						<div class="tab-content" id="strategy-view">
								<div class="section-header">
										<h2 class="section-title">Tire Strategy</h2>
										<p class="section-subtitle">Analyze tire choices and pit stop timing</p>
								</div>
								<div class="card">
										<div class="card-header"><div class="card-title">Strategy Overview</div></div>
										<div class="strategy-list" id="strategy-container"></div>
								</div>
						</div>

						<div class="tab-content" id="track-view">
								<div class="section-header">
										<h2 class="section-title">Track Map</h2>
										<p class="section-subtitle">Circuit layout with speed visualization</p>
								</div>
								<div class="track-container">
										<canvas id="track-canvas" width="700" height="500"></canvas>
								</div>
						</div>
				</section>
		</main>

		<footer class="footer">
				<p class="footer-text">Powered by <a href="https://github.com/theOehrly/Fast-F1" target="_blank" class="footer-link">FastF1</a> • Formula 1 Telemetry Data</p>
		</footer>

		<script src="{{ url_for('static', filename='js/main.js') }}"></script>
</body>
</html>
"""

@app.route("/")
def index():
		return render_template_string(HTML_TEMPLATE)

@app.route("/api/schedule/<int:year>")
def get_schedule(year):
		try:
				schedule = fastf1.get_event_schedule(year)
				events = []
				for _, row in schedule.iterrows():
						if row["EventFormat"] in ("conventional", "sprint_shootout", "sprint_qualifying", "sprint"):
								events.append({
										"round": int(row["RoundNumber"]),
										"name": row["EventName"],
										"country": row["Country"],
										"location": row["Location"],
										"date": str(row["EventDate"]),
								})
				return jsonify({"year": year, "events": events})
		except Exception as e:
				return jsonify({"error": str(e)}), 500

@app.route("/api/session")
def get_session_info():
		year = request.args.get("year", type=int)
		gp = request.args.get("gp")
		session_type = request.args.get("session", "R")
		try:
				session = load_session(year, gp, session_type)
				drivers = []
				for drv in session.drivers:
						info = session.get_driver(drv)
						drivers.append({
								"code": info.Abbreviation,
								"name": f"{info.FirstName} {info.LastName}",
								"team": info.TeamName,
								"color": f"#{info.TeamColor}" if info.TeamColor else "#3b82f6",
						})
				return jsonify({"event": session.event["EventName"], "session": session_type, "year": year, "drivers": drivers})
		except Exception as e:
				return jsonify({"error": str(e)}), 500

@app.route("/api/telemetry")
def get_telemetry():
		year = request.args.get("year", type=int)
		gp = request.args.get("gp")
		session_type = request.args.get("session", "R")
		driver = request.args.get("driver")
		try:
				session = load_session(year, gp, session_type)
				laps = session.laps.pick_drivers(driver)
				fastest = laps.pick_fastest()
				tel = fastest.get_telemetry()
				tel_df = tel[["Distance", "Speed"]].copy()
				tel_df = tel_df.replace({np.nan: None})
				return jsonify({"driver": driver, "lap_time": fastest["LapTime"].total_seconds() if pd.notna(fastest["LapTime"]) else None, "telemetry": tel_df.to_dict(orient="records")})
		except Exception as e:
				return jsonify({"error": str(e)}), 500

@app.route("/api/telemetry/full")
def get_telemetry_full():
		year = request.args.get("year", type=int)
		gp = request.args.get("gp")
		session_type = request.args.get("session", "R")
		driver = request.args.get("driver")
		try:
				session = load_session(year, gp, session_type)
				laps = session.laps.pick_drivers(driver)
				fastest = laps.pick_fastest()
				tel = fastest.get_telemetry()

				cols = ["Distance", "Speed", "Throttle", "Brake", "nGear", "RPM", "DRS"]
				if "X" in tel.columns and "Y" in tel.columns:
						cols.extend(["X", "Y"])

				available = [c for c in cols if c in tel.columns]
				tel_df = tel[available].copy()
				tel_df = tel_df.replace({np.nan: None})

				return jsonify({
						"driver": driver,
						"lap_time": fastest["LapTime"].total_seconds() if pd.notna(fastest["LapTime"]) else None,
						"telemetry": tel_df.to_dict(orient="records")
				})
		except Exception as e:
				return jsonify({"error": str(e)}), 500

@app.route("/api/compare")
def compare_drivers():
		year = request.args.get("year", type=int)
		gp = request.args.get("gp")
		session_type = request.args.get("session", "R")
		driver1 = request.args.get("driver1")
		driver2 = request.args.get("driver2")
		try:
				session = load_session(year, gp, session_type)
				result = {}
				for drv in [driver1, driver2]:
						laps = session.laps.pick_drivers(drv)
						fastest = laps.pick_fastest()
						tel = fastest.get_telemetry()
						info = session.get_driver(drv)
						tel_df = tel[["Distance", "Speed"]].copy()
						tel_df = tel_df.replace({np.nan: None})
						result[drv] = {"name": f"{info.FirstName} {info.LastName}", "team": info.TeamName, "color": f"#{info.TeamColor}" if info.TeamColor else "#3b82f6", "lap_time": fastest["LapTime"].total_seconds() if pd.notna(fastest["LapTime"]) else None, "telemetry": tel_df.to_dict(orient="records")}
				return jsonify(result)
		except Exception as e:
				return jsonify({"error": str(e)}), 500

@app.route("/api/laps")
def get_laps():
		year = request.args.get("year", type=int)
		gp = request.args.get("gp")
		session_type = request.args.get("session", "R")
		driver = request.args.get("driver")
		try:
				session = load_session(year, gp, session_type)
				laps = session.laps
				if driver:
						laps = laps.pick_drivers(driver)
				cols = ["Driver", "LapNumber", "LapTime"]
				available = [c for c in cols if c in laps.columns]
				laps_df = laps[available].copy()
				laps_df = clean_timedelta(laps_df)
				laps_df = laps_df.replace({np.nan: None})
				return jsonify(laps_df.to_dict(orient="records"))
		except Exception as e:
				return jsonify({"error": str(e)}), 500

@app.route("/api/positions")
def get_positions():
		year = request.args.get("year", type=int)
		gp = request.args.get("gp")
		session_type = request.args.get("session", "R")
		try:
				session = load_session(year, gp, session_type)
				laps = session.laps
				drivers_data = {}

				for drv in session.drivers:
						info = session.get_driver(drv)
						drv_laps = laps.pick_drivers(drv)
						if "Position" not in drv_laps.columns or "LapNumber" not in drv_laps.columns:
								continue

						drv_laps_sorted = drv_laps[["LapNumber", "Position"]].dropna().sort_values("LapNumber")

						drivers_data[info.Abbreviation] = {
								"name": f"{info.FirstName} {info.LastName}",
								"team": info.TeamName,
								"color": f"#{info.TeamColor}" if info.TeamColor else "#3b82f6",
								"laps": drv_laps_sorted["LapNumber"].astype(int).tolist(),
								"positions": drv_laps_sorted["Position"].astype(int).tolist(),
						}

				return jsonify(drivers_data)
		except Exception as e:
				return jsonify({"error": str(e)}), 500

@app.route("/api/strategy")
def get_strategy():
		year = request.args.get("year", type=int)
		gp = request.args.get("gp")
		session_type = request.args.get("session", "R")
		try:
				session = load_session(year, gp, session_type)
				laps = session.laps
				strategies = {}
				for drv in session.drivers:
						info = session.get_driver(drv)
						drv_laps = laps.pick_drivers(drv)
						stints = []
						for stint_num in drv_laps["Stint"].unique():
								if pd.isna(stint_num):
										continue
								stint_laps = drv_laps[drv_laps["Stint"] == stint_num]
								compound = stint_laps["Compound"].iloc[0] if len(stint_laps) > 0 else "UNKNOWN"
								stints.append({"compound": compound, "start_lap": int(stint_laps["LapNumber"].min()), "end_lap": int(stint_laps["LapNumber"].max()), "laps": int(stint_laps["LapNumber"].max() - stint_laps["LapNumber"].min() + 1)})
						strategies[info.Abbreviation] = {"name": f"{info.FirstName} {info.LastName}", "color": f"#{info.TeamColor}" if info.TeamColor else "#3b82f6", "stints": stints}
				return jsonify(strategies)
		except Exception as e:
				return jsonify({"error": str(e)}), 500

@app.route("/api/track-map")
def get_track_map():
		year = request.args.get("year", type=int)
		gp = request.args.get("gp")
		session_type = request.args.get("session", "R")
		try:
				session = load_session(year, gp, session_type)
				fastest = session.laps.pick_fastest()
				tel = fastest.get_telemetry()
				if "X" in tel.columns and "Y" in tel.columns:
						track_data = tel[["X", "Y", "Speed"]].copy()
						track_data = track_data.replace({np.nan: None})
						return jsonify(track_data.to_dict(orient="records"))
				else:
						return jsonify({"error": "No position data available"}), 404
		except Exception as e:
				return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
		port = int(os.environ.get("PORT", 5000))
		app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
/* ═══════════════════════════════════════════════════════════
	 F1 Telemetry Analytics - Professional UI
	 ═══════════════════════════════════════════════════════════ */

const state = {
		year: null,
		gp: null,
		session: 'R',
		drivers: [],
		charts: {},
		currentView: 'speed',
		replay: {
				isPlaying: false,
				currentFrame: 0,
				interval: null,
				speed: 1,
				telemetryData: null,
				driver: null
		}
};

// Chart.js Configuration
Chart.defaults.color = '#a3a3a3';
Chart.defaults.borderColor = '#2a2a2a';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.elements.point.radius = 0;
Chart.defaults.elements.line.borderWidth = 2;
Chart.defaults.animation.duration = 400;
Chart.defaults.plugins.legend.display = false;

// DOM Helpers
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
		populateYears();
		setupEventListeners();
});

function populateYears() {
		const yearSelect = $('#year-select');
		const currentYear = new Date().getFullYear();

		for (let y = currentYear; y >= 2022; y--) {
				const opt = document.createElement('option');
				opt.value = y;
				opt.textContent = y;
				yearSelect.appendChild(opt);
		}
}

function setupEventListeners() {
		const yearSelect = $('#year-select');
		const gpSelect = $('#gp-select');
		const loadBtn = $('#load-btn');

		if (yearSelect) yearSelect.addEventListener('change', onYearChange);
		if (gpSelect) gpSelect.addEventListener('change', onGPChange);
		if (loadBtn) loadBtn.addEventListener('click', loadSession);

		// Tab navigation
		$$('.tab').forEach(tab => {
				tab.addEventListener('click', () => {
						const view = tab.dataset.view;
						switchView(view);
				});
		});

		// View-specific buttons
		const loadSpeedBtn = $('#load-speed-btn');
		const compareBtn = $('#compare-btn');
		const loadLaptimesBtn = $('#load-laptimes-btn');
		const loadReplayBtn = $('#load-replay-btn');
		const loadPositionsBtn = $('#load-positions-btn');

		if (loadSpeedBtn) loadSpeedBtn.addEventListener('click', loadSpeed);
		if (compareBtn) compareBtn.addEventListener('click', loadComparison);
		if (loadLaptimesBtn) loadLaptimesBtn.addEventListener('click', loadLapTimes);
		if (loadReplayBtn) loadReplayBtn.addEventListener('click', loadReplayData);
		if (loadPositionsBtn) loadPositionsBtn.addEventListener('click', loadPositions);

		// Replay controls
		const replayPlayBtn = $('#replay-play-btn');
		const replayResetBtn = $('#replay-reset-btn');
		const replaySpeedSelect = $('#replay-speed-select');
		const replayProgress = $('#replay-progress');

		if (replayPlayBtn) replayPlayBtn.addEventListener('click', toggleReplay);
		if (replayResetBtn) replayResetBtn.addEventListener('click', resetReplay);
		if (replaySpeedSelect) replaySpeedSelect.addEventListener('change', changeReplaySpeed);
		if (replayProgress) replayProgress.addEventListener('input', seekReplay);
}

function switchView(view) {
		$$('.tab').forEach(t => t.classList.remove('active'));
		$$('.tab-content').forEach(tc => tc.classList.remove('active'));

		const tab = $(`.tab[data-view="${view}"]`);
		const content = $(`#${view}-view`);

		if (tab) tab.classList.add('active');
		if (content) content.classList.add('active');

		state.currentView = view;
}

function showLoading() {
		const overlay = $('#loading-overlay');
		if (overlay) overlay.classList.add('active');
}

function hideLoading() {
		const overlay = $('#loading-overlay');
		if (overlay) overlay.classList.remove('active');
}

function formatTime(seconds) {
		if (!seconds) return '-';
		const min = Math.floor(seconds / 60);
		const sec = (seconds % 60).toFixed(3);
		return min > 0 ? `${min}:${sec.padStart(6, '0')}` : `${sec}s`;
}

async function apiFetch(url) {
		const res = await fetch(url);
		const data = await res.json();
		if (data.error) throw new Error(data.error);
		return data;
}

function destroyChart(name) {
		if (state.charts[name]) {
				state.charts[name].destroy();
				delete state.charts[name];
		}
}

function makeChartOptions(opts = {}) {
		return {
				responsive: true,
				maintainAspectRatio: false,
				interaction: { mode: 'index', intersect: false },
				plugins: {
						legend: { display: opts.showLegend || false },
						tooltip: {
								backgroundColor: 'rgba(26, 26, 26, 0.95)',
								padding: 10,
								titleFont: { size: 12, weight: '600' },
								bodyFont: { size: 11 },
								borderColor: '#3a3a3a',
								borderWidth: 1,
								displayColors: false
						}
				},
				scales: {
						x: {
								title: { display: !!opts.xTitle, text: opts.xTitle, font: { size: 11 } },
								grid: { color: '#1a1a1a' },
								ticks: { maxTicksLimit: 15 }
						},
						y: {
								title: { display: !!opts.yTitle, text: opts.yTitle, font: { size: 11 } },
								grid: { color: '#1a1a1a' },
								min: opts.yMin,
								max: opts.yMax
						}
				}
		};
}

async function onYearChange() {
		const year = $('#year-select').value;
		const gpSelect = $('#gp-select');
		const loadBtn = $('#load-btn');

		if (!year) {
				if (gpSelect) {
						gpSelect.disabled = true;
						gpSelect.innerHTML = '<option value="">Select year first</option>';
				}
				if (loadBtn) loadBtn.disabled = true;
				return;
		}

		showLoading();
		try {
				const data = await apiFetch(`/api/schedule/${year}`);

				if (gpSelect) {
						gpSelect.innerHTML = '<option value="">Select Grand Prix</option>';
						gpSelect.disabled = false;

						data.events.filter(e => e.round > 0).forEach(e => {
								const opt = document.createElement('option');
								opt.value = e.name;
								opt.textContent = e.name;
								gpSelect.appendChild(opt);
						});
				}

				if (loadBtn) loadBtn.disabled = true;
		} catch (err) {
				alert('Error loading schedule: ' + err.message);
		} finally {
				hideLoading();
		}
}

function onGPChange() {
		const gp = $('#gp-select');
		const loadBtn = $('#load-btn');
		if (gp && loadBtn) {
				loadBtn.disabled = !gp.value;
		}
}

async function loadSession() {
		const yearSelect = $('#year-select');
		const gpSelect = $('#gp-select');
		const sessionSelect = $('#session-select');

		if (!yearSelect || !gpSelect || !sessionSelect) return;

		const year = yearSelect.value;
		const gp = gpSelect.value;
		const session = sessionSelect.value;

		if (!year || !gp) {
				alert('Please select a year and Grand Prix');
				return;
		}

		showLoading();

		try {
				const data = await apiFetch(
						`/api/session?year=${year}&gp=${encodeURIComponent(gp)}&session=${session}`
				);

				state.year = year;
				state.gp = gp;
				state.session = session;
				state.drivers = data.drivers;

				// Update UI
				const sessionInfo = $('#session-info');
				const sessionName = $('#session-name');
				if (sessionInfo && sessionName) {
						sessionInfo.style.display = 'flex';
						const sessionNames = { R: 'Race', Q: 'Qualifying', FP1: 'FP1', FP2: 'FP2', FP3: 'FP3' };
						sessionName.textContent = `${data.event} - ${sessionNames[session]}`;
				}

				// Populate driver dropdowns
				populateDriverSelects();

				// Show data section
				const welcomeSection = $('#welcome-section');
				const dataSection = $('#data-section');
				if (welcomeSection) welcomeSection.classList.remove('active');
				if (dataSection) dataSection.classList.add('active');

				// Auto-load strategy and track
				loadStrategy();
				loadTrackMap();

		} catch (err) {
				alert('Error loading session: ' + err.message);
		} finally {
				hideLoading();
		}
}

function populateDriverSelects() {
		const selectors = [
				'#speed-driver-select',
				'#compare-driver1',
				'#compare-driver2',
				'#laptimes-driver',
				'#replay-driver-select',
				'#positions-driver'
		];

		selectors.forEach(sel => {
				const element = $(sel);
				if (!element) return;

				const allowAll = sel.includes('laptimes') || sel.includes('positions');

				element.innerHTML = allowAll 
						? '<option value="">All drivers</option>' 
						: '<option value="">Select driver</option>';

				state.drivers.forEach(d => {
						const opt = document.createElement('option');
						opt.value = d.code;
						opt.textContent = `${d.code} - ${d.name}`;
						element.appendChild(opt);
				});
		});
}

async function loadSpeed() {
		const driverSelect = $('#speed-driver-select');
		if (!driverSelect) return;

		const driver = driverSelect.value;
		if (!driver) {
				alert('Please select a driver');
				return;
		}

		showLoading();

		try {
				const data = await apiFetch(
						`/api/telemetry/full?year=${state.year}&gp=${encodeURIComponent(state.gp)}` +
						`&session=${state.session}&driver=${driver}`
				);

				const tel = data.telemetry;
				const driverInfo = state.drivers.find(d => d.code === driver);

				const canvas = $('#speed-chart');
				if (!canvas) return;

				destroyChart('speed');
				state.charts.speed = new Chart(canvas, {
						type: 'line',
						data: {
								labels: tel.map(t => Math.round(t.Distance)),
								datasets: [{
										label: 'Speed',
										data: tel.map(t => t.Speed),
										borderColor: driverInfo?.color || '#dc2626',
										backgroundColor: (driverInfo?.color || '#dc2626') + '15',
										fill: true,
										tension: 0.3
								}]
						},
						options: makeChartOptions({ xTitle: 'Distance (m)', yTitle: 'Speed (km/h)' })
				});

		} catch (err) {
				alert('Error loading speed data: ' + err.message);
		} finally {
				hideLoading();
		}
}

async function loadComparison() {
		const driver1Select = $('#compare-driver1');
		const driver2Select = $('#compare-driver2');

		if (!driver1Select || !driver2Select) return;

		const d1 = driver1Select.value;
		const d2 = driver2Select.value;

		if (!d1 || !d2) {
				alert('Please select both drivers');
				return;
		}

		if (d1 === d2) {
				alert('Please select different drivers');
				return;
		}

		showLoading();

		try {
				const data = await apiFetch(
						`/api/compare?year=${state.year}&gp=${encodeURIComponent(state.gp)}` +
						`&session=${state.session}&driver1=${d1}&driver2=${d2}`
				);

				const drv1 = data[d1];
				const drv2 = data[d2];

				// Show comparison result
				const resultDiv = $('#compare-result');
				if (resultDiv) {
						const timeDiff = Math.abs(drv1.lap_time - drv2.lap_time);
						const faster = drv1.lap_time < drv2.lap_time ? drv1 : drv2;

						resultDiv.innerHTML = `
								<div class="card" style="margin-bottom:1rem;">
										<div style="display:grid; grid-template-columns:1fr auto 1fr; gap:2rem; align-items:center; text-align:center;">
												<div>
														<div style="color:${drv1.color}; font-weight:600; margin-bottom:0.5rem;">${drv1.name}</div>
														<div style="font-size:18px; font-weight:600; font-variant-numeric:tabular-nums;">${formatTime(drv1.lap_time)}</div>
												</div>
												<div style="color:var(--text-muted); font-size:20px;">VS</div>
												<div>
														<div style="color:${drv2.color}; font-weight:600; margin-bottom:0.5rem;">${drv2.name}</div>
														<div style="font-size:18px; font-weight:600; font-variant-numeric:tabular-nums;">${formatTime(drv2.lap_time)}</div>
												</div>
										</div>
										<div style="text-align:center; margin-top:1rem; padding-top:1rem; border-top:1px solid var(--border-subtle);">
												<div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.25rem;">Gap</div>
												<div style="font-size:20px; font-weight:700; color:var(--success);">+${timeDiff.toFixed(3)}s</div>
												<div style="font-size:12px; color:var(--text-secondary); margin-top:0.25rem;">${faster.name} faster</div>
										</div>
								</div>
						`;
				}

				const tel1 = drv1.telemetry;
				const tel2 = drv2.telemetry;
				const distances = (tel1.length >= tel2.length ? tel1 : tel2).map(t => Math.round(t.Distance));

				const canvas = $('#compare-chart');
				if (canvas) {
						destroyChart('compare');
						state.charts.compare = new Chart(canvas, {
								type: 'line',
								data: {
										labels: distances,
										datasets: [
												{
														label: drv1.name,
														data: tel1.map(t => t.Speed),
														borderColor: drv1.color,
														tension: 0.3
												},
												{
														label: drv2.name,
														data: tel2.map(t => t.Speed),
														borderColor: drv2.color,
														tension: 0.3
												}
										]
								},
								options: makeChartOptions({ 
										xTitle: 'Distance (m)', 
										yTitle: 'Speed (km/h)',
										showLegend: true
								})
						});
				}

		} catch (err) {
				alert('Error comparing drivers: ' + err.message);
		} finally {
				hideLoading();
		}
}

async function loadLapTimes() {
		const driverSelect = $('#laptimes-driver');
		if (!driverSelect) return;

		const driver = driverSelect.value;

		showLoading();

		try {
				let url = `/api/laps?year=${state.year}&gp=${encodeURIComponent(state.gp)}&session=${state.session}`;
				if (driver) url += `&driver=${driver}`;

				const laps = await apiFetch(url);

				const grouped = {};
				laps.forEach(l => {
						if (!grouped[l.Driver]) grouped[l.Driver] = [];
						grouped[l.Driver].push(l);
				});

				const datasets = Object.entries(grouped).map(([drv, drvLaps]) => {
						const info = state.drivers.find(d => d.code === drv);
						return {
								label: drv,
								data: drvLaps.map(l => ({ x: l.LapNumber, y: l.LapTime })),
								borderColor: info?.color || '#737373',
								borderWidth: driver ? 2 : 1.5,
								tension: 0.3
						};
				});

				const canvas = $('#laptimes-chart');
				if (canvas) {
						destroyChart('laptimes');
						state.charts.laptimes = new Chart(canvas, {
								type: 'line',
								data: { datasets },
								options: {
										...makeChartOptions({ xTitle: 'Lap Number', yTitle: 'Lap Time (s)' }),
										plugins: {
												...makeChartOptions().plugins,
												legend: { display: !driver, position: 'right', labels: { usePointStyle: true, boxWidth: 6 } },
												tooltip: {
														...makeChartOptions().plugins.tooltip,
														callbacks: {
																label: (ctx) => `${ctx.dataset.label}: ${formatTime(ctx.parsed.y)}`
														}
												}
										},
										scales: {
												x: { type: 'linear', title: { display: true, text: 'Lap Number' }, grid: { color: '#1a1a1a' } },
												y: { title: { display: true, text: 'Lap Time (s)' }, grid: { color: '#1a1a1a' } }
										}
								}
						});
				}

		} catch (err) {
				alert('Error loading lap times: ' + err.message);
		} finally {
				hideLoading();
		}
}

async function loadReplayData() {
		const driverSelect = $('#replay-driver-select');
		if (!driverSelect) return;

		const driver = driverSelect.value;
		if (!driver) {
				alert('Please select a driver');
				return;
		}

		showLoading();

		try {
				const data = await apiFetch(
						`/api/telemetry/full?year=${state.year}&gp=${encodeURIComponent(state.gp)}` +
						`&session=${state.session}&driver=${driver}`
				);

				state.replay.telemetryData = data.telemetry;
				state.replay.driver = driver;
				state.replay.currentFrame = 0;

				const driverInfo = state.drivers.find(d => d.code === driver);

				const driverName = $('#replay-driver-name');
				const lapTime = $('#replay-lap-time');
				const progress = $('#replay-progress');

				if (driverName) driverName.textContent = `${driver} - ${driverInfo?.name || ''}`;
				if (lapTime) lapTime.textContent = formatTime(data.lap_time);
				if (progress) {
						progress.max = data.telemetry.length - 1;
						progress.value = 0;
				}

				drawReplayFrame(0);

		} catch (err) {
				alert('Error loading replay: ' + err.message);
		} finally {
				hideLoading();
		}
}

function drawReplayFrame(frameIndex) {
		if (!state.replay.telemetryData || frameIndex >= state.replay.telemetryData.length) return;

		const frame = state.replay.telemetryData[frameIndex];

		const speedValue = $('#replay-speed-value');
		const throttleValue = $('#replay-throttle-value');
		const brakeValue = $('#replay-brake-value');
		const gearValue = $('#replay-gear-value');
		const rpmValue = $('#replay-rpm-value');
		const drsValue = $('#replay-drs-value');

		if (speedValue) speedValue.textContent = Math.round(frame.Speed || 0);
		if (throttleValue) throttleValue.textContent = Math.round(frame.Throttle || 0) + '%';
		if (brakeValue) brakeValue.textContent = (frame.Brake ? 100 : 0) + '%';
		if (gearValue) gearValue.textContent = frame.nGear || '-';
		if (rpmValue) rpmValue.textContent = Math.round(frame.RPM || 0);
		if (drsValue) drsValue.textContent = frame.DRS > 0 ? 'OPEN' : 'CLOSED';

		const throttleBar = $('#throttle-bar');
		const brakeBar = $('#brake-bar');

		if (throttleBar) throttleBar.style.height = `${frame.Throttle || 0}%`;
		if (brakeBar) brakeBar.style.height = `${frame.Brake ? 100 : 0}%`;

		drawMiniTrack(frameIndex);

		const replayProgress = $('#replay-progress');
		const replayTime = $('#replay-time');

		if (replayProgress) replayProgress.value = frameIndex;
		if (replayTime) {
				const progress = (frameIndex / (state.replay.telemetryData.length - 1)) * 100;
				replayTime.textContent = `${Math.round(progress)}%`;
		}
}

function drawMiniTrack(currentFrame) {
		const canvas = $('#mini-track-canvas');
		if (!canvas) return;

		const ctx = canvas.getContext('2d');
		const W = canvas.width;
		const H = canvas.height;

		ctx.clearRect(0, 0, W, H);

		const telData = state.replay.telemetryData;
		if (!telData || telData.length === 0) return;

		const positions = telData.filter(t => t.X && t.Y);
		if (positions.length === 0) return;

		const xs = positions.map(p => p.X);
		const ys = positions.map(p => p.Y);
		const minX = Math.min(...xs), maxX = Math.max(...xs);
		const minY = Math.min(...ys), maxY = Math.max(...ys);
		const rangeX = maxX - minX || 1;
		const rangeY = maxY - minY || 1;

		const pad = 20;
		const scale = Math.min((W - pad*2) / rangeX, (H - pad*2) / rangeY);

		const toCanvas = (x, y) => [
				pad + (x - minX) * scale,
				H - pad - (y - minY) * scale
		];

		// Draw track
		ctx.strokeStyle = '#2a2a2a';
		ctx.lineWidth = 3;
		ctx.beginPath();
		positions.forEach((p, i) => {
				const [x, y] = toCanvas(p.X, p.Y);
				if (i === 0) ctx.moveTo(x, y);
				else ctx.lineTo(x, y);
		});
		ctx.stroke();

		// Draw car
		const current = telData[currentFrame];
		if (current && current.X && current.Y) {
				const [cx, cy] = toCanvas(current.X, current.Y);
				const driverInfo = state.drivers.find(d => d.code === state.replay.driver);

				ctx.fillStyle = driverInfo?.color || '#dc2626';
				ctx.beginPath();
				ctx.arc(cx, cy, 5, 0, Math.PI * 2);
				ctx.fill();

				ctx.strokeStyle = driverInfo?.color || '#dc2626';
				ctx.lineWidth = 2;
				ctx.beginPath();
				ctx.arc(cx, cy, 9, 0, Math.PI * 2);
				ctx.stroke();
		}
}

function toggleReplay() {
		if (state.replay.isPlaying) {
				pauseReplay();
		} else {
				playReplay();
		}
}

function playReplay() {
		if (!state.replay.telemetryData) return;

		state.replay.isPlaying = true;
		const playBtn = $('#replay-play-btn');
		if (playBtn) playBtn.textContent = 'Pause';

		const fps = 30;
		const interval = 1000 / fps / state.replay.speed;

		state.replay.interval = setInterval(() => {
				state.replay.currentFrame++;

				if (state.replay.currentFrame >= state.replay.telemetryData.length) {
						resetReplay();
						return;
				}

				drawReplayFrame(state.replay.currentFrame);
		}, interval);
}

function pauseReplay() {
		state.replay.isPlaying = false;
		const playBtn = $('#replay-play-btn');
		if (playBtn) playBtn.textContent = 'Play';

		if (state.replay.interval) {
				clearInterval(state.replay.interval);
				state.replay.interval = null;
		}
}

function resetReplay() {
		pauseReplay();
		state.replay.currentFrame = 0;
		drawReplayFrame(0);
}

function changeReplaySpeed() {
		const speedSelect = $('#replay-speed-select');
		if (!speedSelect) return;

		const speed = parseFloat(speedSelect.value);
		state.replay.speed = speed;

		if (state.replay.isPlaying) {
				pauseReplay();
				playReplay();
		}
}

function seekReplay(e) {
		const frame = parseInt(e.target.value);
		state.replay.currentFrame = frame;
		drawReplayFrame(frame);
}

async function loadPositions() {
		const driverSelect = $('#positions-driver');
		if (!driverSelect) return;

		const driver = driverSelect.value;

		showLoading();

		try {
				const data = await apiFetch(
						`/api/positions?year=${state.year}&gp=${encodeURIComponent(state.gp)}&session=${state.session}`
				);

				const datasets = [];

				Object.entries(data).forEach(([code, d]) => {
						if (driver && code !== driver) return;

						datasets.push({
								label: code,
								data: d.laps.map((lap, i) => ({ x: lap, y: d.positions[i] })),
								borderColor: d.color,
								borderWidth: driver ? 3 : 1.5,
								tension: 0.1
						});
				});

				const canvas = $('#positions-chart');
				if (canvas) {
						destroyChart('positions');
						state.charts.positions = new Chart(canvas, {
								type: 'line',
								data: { datasets },
								options: {
										responsive: true,
										maintainAspectRatio: false,
										plugins: {
												legend: { 
														display: !driver, 
														position: 'right',
														labels: { usePointStyle: true, boxWidth: 6, font: { size: 10 } }
												},
												tooltip: {
														backgroundColor: 'rgba(26, 26, 26, 0.95)',
														padding: 10,
														callbacks: {
																label: (ctx) => `${ctx.dataset.label}: P${ctx.parsed.y}`
														}
												}
										},
										scales: {
												x: {
														type: 'linear',
														title: { display: true, text: 'Lap Number' },
														grid: { color: '#1a1a1a' }
												},
												y: {
														reverse: true,
														min: 1,
														max: 20,
														title: { display: true, text: 'Position' },
														grid: { color: '#1a1a1a' },
														ticks: { stepSize: 1 }
												}
										}
								}
						});
				}

		} catch (err) {
				alert('Error loading positions: ' + err.message);
		} finally {
				hideLoading();
		}
}

async function loadStrategy() {
		try {
				const data = await apiFetch(
						`/api/strategy?year=${state.year}&gp=${encodeURIComponent(state.gp)}&session=${state.session}`
				);

				const container = $('#strategy-container');
				if (!container) return;

				container.innerHTML = '';

				let maxLap = 0;
				Object.values(data).forEach(d => {
						d.stints.forEach(s => { if (s.end_lap > maxLap) maxLap = s.end_lap; });
				});

				Object.entries(data).forEach(([code, d]) => {
						const row = document.createElement('div');
						row.className = 'strategy-row';

						const driver = document.createElement('div');
						driver.className = 'strategy-driver';
						driver.style.color = d.color;
						driver.textContent = code;
						row.appendChild(driver);

						const stints = document.createElement('div');
						stints.className = 'strategy-stints';

						d.stints.forEach(s => {
								const bar = document.createElement('div');
								bar.className = `stint ${s.compound}`;
								bar.style.width = `${(s.laps / maxLap) * 100}%`;
								bar.textContent = s.laps > 3 ? s.laps : '';
								bar.title = `${s.compound}: ${s.laps} laps (L${s.start_lap}-${s.end_lap})`;
								stints.appendChild(bar);
						});

						row.appendChild(stints);
						container.appendChild(row);
				});

		} catch (err) {
				console.warn('Strategy not available:', err);
		}
}

async function loadTrackMap() {
		try {
				const data = await apiFetch(
						`/api/track-map?year=${state.year}&gp=${encodeURIComponent(state.gp)}&session=${state.session}`
				);

				const canvas = $('#track-canvas');
				if (!canvas) return;

				const ctx = canvas.getContext('2d');
				const W = canvas.width;
				const H = canvas.height;

				ctx.clearRect(0, 0, W, H);

				const xs = data.map(p => p.X).filter(Boolean);
				const ys = data.map(p => p.Y).filter(Boolean);
				if (xs.length === 0) return;

				const minX = Math.min(...xs), maxX = Math.max(...xs);
				const minY = Math.min(...ys), maxY = Math.max(...ys);
				const rangeX = maxX - minX || 1;
				const rangeY = maxY - minY || 1;

				const pad = 40;
				const scale = Math.min((W - pad*2) / rangeX, (H - pad*2) / rangeY);

				const toCanvas = (x, y) => [
						pad + (x - minX) * scale,
						H - pad - (y - minY) * scale
				];

				const speeds = data.map(p => p.Speed).filter(Boolean);
				const minSpd = Math.min(...speeds);
				const maxSpd = Math.max(...speeds);
				const spdRange = maxSpd - minSpd || 1;

				function speedColor(speed) {
						const t = (speed - minSpd) / spdRange;
						const r = Math.round(220 + 35 * t);
						const g = Math.round(38 + 38 * (1 - t));
						const b = Math.round(38 + 38 * (1 - t));
						return `rgb(${r},${g},${b})`;
				}

				ctx.lineWidth = 4;
				ctx.lineCap = 'round';
				ctx.lineJoin = 'round';

				for (let i = 1; i < data.length; i++) {
						if (!data[i].X || !data[i].Y) continue;
						const [x1, y1] = toCanvas(data[i-1].X, data[i-1].Y);
						const [x2, y2] = toCanvas(data[i].X, data[i].Y);

						ctx.beginPath();
						ctx.strokeStyle = speedColor(data[i].Speed || minSpd);
						ctx.moveTo(x1, y1);
						ctx.lineTo(x2, y2);
						ctx.stroke();
				}

				// Legend
				const legendW = 150, legendH = 12;
				const lx = W - legendW - 25, ly = H - 35;

				const grad = ctx.createLinearGradient(lx, 0, lx + legendW, 0);
				grad.addColorStop(0, speedColor(minSpd));
				grad.addColorStop(0.5, speedColor((minSpd + maxSpd) / 2));
				grad.addColorStop(1, speedColor(maxSpd));

				ctx.fillStyle = grad;
				ctx.fillRect(lx, ly, legendW, legendH);

				ctx.fillStyle = '#737373';
				ctx.font = '10px Inter';
				ctx.fillText(`${Math.round(minSpd)} km/h`, lx, ly + legendH + 14);
				ctx.textAlign = 'right';
				ctx.fillText(`${Math.round(maxSpd)} km/h`, lx + legendW, ly + legendH + 14);

		} catch (err) {
				console.warn('Track map not available:', err);
		}
}

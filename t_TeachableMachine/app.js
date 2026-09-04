// Global Application State
let capture;
let canvas;
let videoDevices = [];
let selectedDeviceId = null;
let currentFacingMode = 'user';
let mirrorMode = true;

let classifier = null;
let isModelLoaded = false;
let topResults = [];
let classMappings = {};
let tableRendered = false;

// BLE State Variables
let bleDevice = null;
let bleServer = null;
let bleService = null;
let txCharacteristic = null;
let rxCharacteristic = null;

let isSendingData = false;
let lastSentTime = 0;
let lastSentValue = null;

// BLE UUIDs for Nordic UART Service (NUS)
const NUS_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e';
const NUS_TX_UUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'; // Write (Web -> ESP32)
const NUS_RX_UUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'; // Notify (ESP32 -> Web)

// -------------------------------------------------------------
// p5.js Lifecycle Methods
// -------------------------------------------------------------
function setup() {
  // Create 1:1 ratio canvas inside the UI container
  canvas = createCanvas(400, 400);
  canvas.parent('canvas-holder');
  
  // Initialize camera and list hardware devices
  initCamera();
  enumerateCameras();
}

function draw() {
  background(10, 10, 15);
  
  // Draw the square cropped webcam stream
  if (capture && capture.loadedmetadata && capture.elt && capture.elt.videoWidth > 0) {
    push();
    if (mirrorMode) {
      translate(width, 0);
      scale(-1, 1);
    }
    // Crop center 400x400 out of 640x480 webcam frame
    // sx = (640 - 400) / 2 = 120, sy = (480 - 400) / 2 = 40
    image(capture, 0, 0, 400, 400, 120, 40, 400, 400);
    pop();
  } else {
    fill(150);
    textSize(14);
    textAlign(CENTER, CENTER);
    text("카메라 비디오를 로드하는 중...", width / 2, height / 2);
  }
  
  // Draw top inference text overlay at the bottom of the canvas
  if (isModelLoaded && topResults && topResults.length > 0) {
    const topResult = topResults[0];
    if (topResult && topResult.label) {
      fill(0, 0, 0, 160);
      noStroke();
      rect(0, height - 60, width, 60);
      
      fill(255);
      textSize(16);
      textStyle(BOLD);
      textAlign(LEFT, CENTER);
      const confidence = topResult.confidence !== undefined ? topResult.confidence : topResult.probability;
      const confidencePercent = confidence !== undefined ? (confidence * 100).toFixed(1) : '0.0';
      text(`👉 감지결과: ${topResult.label} (${confidencePercent}%)`, 20, height - 30);
    }
  }
}

// -------------------------------------------------------------
// Camera Hardware Management
// -------------------------------------------------------------
async function initCamera() {
  if (capture) {
    capture.remove();
  }
  
  const constraints = {
    audio: false,
    video: {
      width: { ideal: 640 },
      height: { ideal: 480 }
    }
  };
  
  if (selectedDeviceId) {
    constraints.video.deviceId = { exact: selectedDeviceId };
  } else {
    constraints.video.facingMode = currentFacingMode;
  }
  
  capture = createCapture(constraints, function(stream) {
    logTerminal("카메라 스트림 시작 완료.", "sys");
    setTimeout(enumerateCameras, 1000);
  });
  capture.size(640, 480);
  capture.hide();
}

async function enumerateCameras() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    videoDevices = devices.filter(device => device.kind === 'videoinput');
    
    const select = document.getElementById('camera-select');
    if (select) {
      const currentVal = select.value;
      select.innerHTML = '';
      
      const optDefault = document.createElement('option');
      optDefault.value = '';
      optDefault.textContent = '자동 선택 (facingMode 우선)';
      select.appendChild(optDefault);
      
      videoDevices.forEach((device, index) => {
        const option = document.createElement('option');
        option.value = device.deviceId;
        option.textContent = device.label || `카메라 입력 장치 ${index + 1}`;
        select.appendChild(option);
      });
      
      if (currentVal && videoDevices.some(d => d.deviceId === currentVal)) {
        select.value = currentVal;
      }
    }
  } catch (err) {
    console.warn("Could not retrieve camera list:", err);
  }
}

function toggleMirror() {
  mirrorMode = !mirrorMode;
  logTerminal(`좌우 반전(거울 모드): ${mirrorMode ? '활성화' : '비활성화'}`, 'sys');
}

function switchCameraFacing() {
  currentFacingMode = currentFacingMode === 'user' ? 'environment' : 'user';
  selectedDeviceId = null;
  const select = document.getElementById('camera-select');
  if (select) select.value = '';
  initCamera();
  logTerminal(`카메라 방향 전환: ${currentFacingMode === 'user' ? '전면(User)' : '후면(Environment)'}`, 'sys');
}

function changeCameraDevice(deviceId) {
  selectedDeviceId = deviceId || null;
  initCamera();
  logTerminal(`카메라 소스 변경: ${deviceId ? deviceId.substring(0, 10) + '...' : '기본'}`, 'sys');
}

// -------------------------------------------------------------
// Teachable Machine Model Loader & Inference Loop
// -------------------------------------------------------------
async function loadModel() {
  const modelInput = document.getElementById('model-url-input').value.trim();
  if (!modelInput) {
    alert('Teachable Machine 모델 공유 URL 또는 고유 짧은 ID를 입력해주세요.');
    return;
  }
  
  let modelUrl = '';
  // Robust regex parser to extract model ID and clean up duplicates
  const match = modelInput.match(/\/models\/([a-zA-Z0-9_-]+)/);
  if (match && match[1]) {
    modelUrl = `https://teachablemachine.withgoogle.com/models/${match[1]}/`;
  } else if (!modelInput.includes('/') && !modelInput.includes('.')) {
    modelUrl = `https://teachablemachine.withgoogle.com/models/${modelInput}/`;
  } else {
    modelUrl = modelInput;
    if (!modelUrl.startsWith('http://') && !modelUrl.startsWith('https://')) {
      modelUrl = `https://teachablemachine.withgoogle.com/models/${modelInput}/`;
    }
    if (!modelUrl.endsWith('/')) {
      modelUrl += '/';
    }
  }
  
  const modelJsonPath = modelUrl + 'model.json';
  
  logTerminal(`모델 다운로드 요청: ${modelUrl}`, 'sys');
  updateModelStatus('running', '다운로드 중');
  
  try {
    isModelLoaded = false;
    tableRendered = false;
    
    // Load using standard ml5 callback model (safest in legacy ml5)
    classifier = ml5.imageClassifier(modelJsonPath, function() {
      logTerminal('Teachable Machine 모델 로드 성공!', 'sys');
      updateModelStatus('success', '정상 로드 완료');
      isModelLoaded = true;
      localStorage.setItem('tm_model_url', modelInput);
      
      // Parse labels list
      let classes = [];
      if (classifier.classes) {
        classes = classifier.classes;
      } else if (classifier.model && classifier.model.classes) {
        classes = classifier.model.classes;
      } else if (classifier.model && classifier.model.labels) {
        classes = classifier.model.labels;
      }
      
      if (classes && classes.length > 0) {
        logTerminal(`감지된 클래스: ${classes.join(', ')}`, 'sys');
        renderMappingTable(classes);
      } else {
        logTerminal('클래스 목록 로드 지연. 첫 추론 후 테이블이 생성됩니다.', 'sys');
      }
      
      // Trigger classification loop
      classifyVideo();
    });
  } catch (err) {
    logTerminal(`모델 로드 실패: ${err.message || err}`, 'err');
    updateModelStatus('pending', '준비 대기 중');
  }
}

function classifyVideo() {
  // CRITICAL: Verify that the video is playing and has positive width/height
  // to prevent tf.js from throwing empty-tensor slice errors!
  if (classifier && isModelLoaded && capture && capture.elt && capture.elt.videoWidth > 0 && capture.elt.videoHeight > 0) {
    classifier.classify(capture, gotResults);
  } else {
    setTimeout(classifyVideo, 100);
  }
}

function gotResults(error, results) {
  if (error) {
    console.error("Classification error:", error);
    logTerminal(`[추론 에러] ${error.message || error}`, 'err');
    setTimeout(classifyVideo, 150);
    return;
  }
  
  if (!results || !Array.isArray(results) || results.length === 0) {
    setTimeout(classifyVideo, 100);
    return;
  }
  
  topResults = results;
  
  // Render mapping table if it hasn't been rendered yet
  if (!tableRendered) {
    const classes = results.map(r => r.label).filter(Boolean);
    if (classes.length > 0) {
      renderMappingTable(classes);
    }
  }
  
  // Sync horizontal bars
  updateProgressBars(results);
  
  // Send classification to ESP32 via BLE
  const topResult = results[0];
  if (topResult && topResult.label) {
    const confidence = topResult.confidence !== undefined ? topResult.confidence : topResult.probability;
    if (confidence !== undefined && confidence > 0.5) {
      const mappedVal = classMappings[topResult.label];
      if (mappedVal !== undefined && mappedVal !== '') {
        sendData(mappedVal);
      }
    }
  }
  
  classifyVideo();
}

// -------------------------------------------------------------
// Mapping Config Table
// -------------------------------------------------------------
function renderMappingTable(classes) {
  const container = document.getElementById('mapping-rows');
  if (!container) return;
  
  let savedMappings = {};
  try {
    const saved = localStorage.getItem('tm_class_map');
    if (saved) savedMappings = JSON.parse(saved);
  } catch (e) {
    console.error("Local storage mapping fetch error:", e);
  }
  
  container.innerHTML = '';
  classMappings = {};
  
  const defaultVals = ['1', '2', 'abc', '4'];
  
  classes.forEach((className, idx) => {
    let mappingVal = savedMappings[className];
    if (mappingVal === undefined) {
      mappingVal = defaultVals[idx] || `${idx + 1}`;
    }
    classMappings[className] = mappingVal;
    
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <div class="class-label-cell">
          <span class="class-name">${className}</span>
          <div class="class-bar-container">
            <div class="class-bar" id="bar-${className.replace(/[^a-zA-Z0-9]/g, '_')}"></div>
          </div>
        </div>
      </td>
      <td style="text-align: right;">
        <input type="text" class="mapping-input" data-class="${className}" value="${mappingVal}">
      </td>
    `;
    container.appendChild(tr);
  });
  
  // Bind input listeners
  const inputs = container.querySelectorAll('.mapping-input');
  inputs.forEach(input => {
    input.addEventListener('input', (e) => {
      const cls = e.target.getAttribute('data-class');
      const val = e.target.value;
      classMappings[cls] = val;
      localStorage.setItem('tm_class_map', JSON.stringify(classMappings));
    });
  });
  
  tableRendered = true;
  
  const placeholder = document.getElementById('no-model-placeholder');
  if (placeholder) placeholder.style.display = 'none';
}

function updateProgressBars(results) {
  const bars = document.querySelectorAll('.class-bar');
  bars.forEach(bar => {
    bar.style.width = '0%';
  });
  
  if (!results || !Array.isArray(results)) return;
  
  results.forEach(result => {
    if (!result || !result.label) return;
    const cleanId = `bar-${result.label.replace(/[^a-zA-Z0-9]/g, '_')}`;
    const bar = document.getElementById(cleanId);
    if (bar) {
      const confidence = result.confidence !== undefined ? result.confidence : result.probability;
      if (confidence !== undefined) {
        bar.style.width = `${confidence * 100}%`;
      }
    }
  });
}

// -------------------------------------------------------------
// Web Bluetooth NUS Client Logic
// -------------------------------------------------------------
async function connectBLE() {
  if (!navigator.bluetooth) {
    alert("현재 브라우저는 Web Bluetooth API를 지원하지 않습니다. (Chrome, Edge 브라우저 권장)");
    return;
  }
  
  logTerminal('스캔 대기: 기기명 Prefix "ESP_" 및 UART UUID 필터링...', 'sys');
  updateBleStatus('running', '연결 스캔 중');
  
  try {
    bleDevice = await navigator.bluetooth.requestDevice({
      filters: [
        {
          services: [NUS_SERVICE_UUID],
          namePrefix: 'ESP_'
        }
      ]
    });
    
    bleDevice.addEventListener('gattserverdisconnected', onDisconnected);
    
    logTerminal(`연결 진행 중: ${bleDevice.name}`, 'sys');
    bleServer = await bleDevice.gatt.connect();
    
    logTerminal('UART 서비스 활성화 중...', 'sys');
    bleService = await bleServer.getPrimaryService(NUS_SERVICE_UUID);
    
    logTerminal('송수신 채널 확인 중...', 'sys');
    txCharacteristic = await bleService.getCharacteristic(NUS_TX_UUID);
    rxCharacteristic = await bleService.getCharacteristic(NUS_RX_UUID);
    
    logTerminal('알림(Notifications) 수신 활성화...', 'sys');
    await rxCharacteristic.startNotifications();
    rxCharacteristic.addEventListener('characteristicvaluechanged', handleNotification);
    
    logTerminal('블루투스 기기 연결됨!', 'sys');
    updateBleStatus('success', '연결됨');
    
    document.getElementById('ble-connect-btn').style.display = 'none';
    document.getElementById('ble-disconnect-btn').style.display = 'inline-flex';
  } catch (err) {
    logTerminal(`BLE 스캔/연결 에러: ${err.message}`, 'err');
    updateBleStatus('pending', '연결 대기 중');
  }
}

function handleNotification(event) {
  const value = event.target.value;
  const decoder = new TextDecoder('utf-8');
  const text = decoder.decode(value);
  logTerminal(`RX (수신): ${text.trim()}`, 'rx');
}

async function sendData(val) {
  if (!txCharacteristic || isSendingData) return;
  
  // Duplicate Suppression filter check
  const preventDuplicate = document.getElementById('ble-dedup-toggle').checked;
  if (preventDuplicate && val === lastSentValue) {
    return;
  }
  
  // Throttle timer check
  const sendInterval = parseInt(document.getElementById('ble-interval-slider').value);
  const now = Date.now();
  if (now - lastSentTime < sendInterval) {
    return;
  }
  
  // Add message Delimiter
  const delimiterType = document.getElementById('ble-delimiter').value;
  let suffix = '';
  if (delimiterType === 'lf') suffix = '\n';
  else if (delimiterType === 'crlf') suffix = '\r\n';
  
  const finalVal = val + suffix;
  const encoder = new TextEncoder();
  const buffer = encoder.encode(finalVal);
  
  isSendingData = true;
  lastSentTime = now;
  
  try {
    // Write without response for maximum transmission efficiency
    await txCharacteristic.writeValueWithoutResponse(buffer);
    lastSentValue = val;
    logTerminal(`TX (명령 송신): ${val}`, 'tx');
  } catch (err) {
    logTerminal(`송신 오류: ${err.message}`, 'err');
  } finally {
    isSendingData = false;
  }
}

function onDisconnected() {
  logTerminal('디바이스와 연결이 해제되었습니다.', 'err');
  updateBleStatus('pending', '연결 대기 중');
  
  document.getElementById('ble-connect-btn').style.display = 'inline-flex';
  document.getElementById('ble-disconnect-btn').style.display = 'none';
  
  bleDevice = null;
  bleServer = null;
  bleService = null;
  txCharacteristic = null;
  rxCharacteristic = null;
}

function disconnectBLE() {
  if (bleDevice && bleDevice.gatt.connected) {
    logTerminal('연결 종료를 시도합니다...', 'sys');
    bleDevice.gatt.disconnect();
  }
}

// -------------------------------------------------------------
// UI Utilities
// -------------------------------------------------------------
function updateBleStatus(state, text) {
  const badge = document.getElementById('ble-status-badge');
  if (!badge) return;
  badge.className = `badge ${state}`;
  badge.querySelector('.badge-text').textContent = text;
}

function updateModelStatus(state, text) {
  const badge = document.getElementById('model-status-badge');
  if (!badge) return;
  badge.className = `badge ${state}`;
  badge.querySelector('.badge-text').textContent = text;
}

function logTerminal(message, type = 'sys') {
  const terminal = document.getElementById('terminal-log');
  if (!terminal) return;
  
  const line = document.createElement('div');
  line.className = `terminal-line ${type}`;
  
  const timestamp = document.createElement('span');
  timestamp.className = 'timestamp';
  const now = new Date();
  const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${Math.floor(now.getMilliseconds() / 100)}`;
  timestamp.textContent = `[${timeStr}]`;
  
  const content = document.createElement('span');
  content.textContent = ` ${message}`;
  
  line.appendChild(timestamp);
  line.appendChild(content);
  terminal.appendChild(line);
  
  terminal.scrollTop = terminal.scrollHeight;
  
  // Keep terminal clean by pruning old entries
  while (terminal.children.length > 80) {
    terminal.removeChild(terminal.firstChild);
  }
}

function copyMicroPythonCode() {
  const code = document.getElementById('micropython-code').textContent;
  navigator.clipboard.writeText(code).then(() => {
    const copyBtn = document.getElementById('copy-code-btn');
    copyBtn.textContent = '복사 완료!';
    copyBtn.style.background = 'var(--status-success-bg)';
    copyBtn.style.color = 'var(--status-success-text)';
    
    setTimeout(() => {
      copyBtn.textContent = '코드 복사';
      copyBtn.style.background = 'rgba(255, 255, 255, 0.08)';
      copyBtn.style.color = 'var(--text-primary)';
    }, 2000);
  }).catch(err => {
    alert('코드를 클립보드에 쓰지 못했습니다: ' + err);
  });
}

// -------------------------------------------------------------
// Unhandled Exception Handlers (Outputs directly to Web UI terminal)
// -------------------------------------------------------------
window.onerror = function (message, source, lineno, colno, error) {
  const msg = `[오류] JS: ${message} (라인: ${lineno})`;
  console.error(msg, error);
  if (document.getElementById('terminal-log')) {
    logTerminal(msg, 'err');
  }
  return false;
};

window.addEventListener('unhandledrejection', function (event) {
  const msg = `[오류] Promise Rejection: ${event.reason}`;
  console.error(msg);
  if (document.getElementById('terminal-log')) {
    logTerminal(msg, 'err');
  }
});

// Initialization on DOM ready
window.addEventListener('DOMContentLoaded', () => {
  const isSecure = location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  const warningBanner = document.getElementById('security-warning');
  
  if (!navigator.bluetooth) {
    warningBanner.style.display = 'flex';
    warningBanner.innerHTML = '⚠️ <strong>지원 오류:</strong> 현재 웹 브라우저는 Web Bluetooth API를 지원하지 않습니다. Chrome, Microsoft Edge 브라우저 등 Chromium 기반 브라우저를 이용해 주세요. (<a href="https://developer.mozilla.org/en-US/docs/Web/API/Web_Bluetooth_API" target="_blank" style="color: inherit; text-decoration: underline;">MDN 문서 보기</a>)';
  } else if (!isSecure) {
    warningBanner.style.display = 'flex';
    warningBanner.innerHTML = '⚠️ <strong>보안 프로토콜 알림:</strong> 웹 브라우저 보안 규정상 Web Bluetooth 및 외부 모델 로드(CORS)는 <strong>HTTPS 보안 도메인</strong> 또는 <strong>localhost(127.0.0.1)</strong> 주소에서만 동작합니다. 로컬 파일(file:///) 환경에서는 모델 로드가 차단되므로 로컬 서버를 구동해 localhost로 접속해 주세요. (<a href="https://developer.mozilla.org/en-US/docs/Web/API/Web_Bluetooth_API#security_considerations" target="_blank" style="color: inherit; text-decoration: underline;">상세 보안 규정 링크</a>)';
  }
  
  const slider = document.getElementById('ble-interval-slider');
  const sliderVal = document.getElementById('ble-interval-val');
  if (slider && sliderVal) {
    slider.addEventListener('input', (e) => {
      sliderVal.textContent = `${e.target.value}ms`;
    });
  }
  
  const savedModel = localStorage.getItem('tm_model_url');
  if (savedModel) {
    document.getElementById('model-url-input').value = savedModel;
  }
  
  const cameraSelect = document.getElementById('camera-select');
  if (cameraSelect) {
    cameraSelect.addEventListener('focus', enumerateCameras);
  }
});

function computeWsUrl() {
  try {
    var override = (document.body && document.body.dataset) ? document.body.dataset.ws : null;
    if (override) return override;
  } catch (_) {}
  var url = new URL(location.href);
  var proto = url.protocol === 'https:' ? 'wss' : 'ws';
  // Always prefer same-host:port unless explicitly overridden
  return proto + '//' + url.host + '/ws';
}
const WS_URL = computeWsUrl();

class CommandCanvas {
  constructor(root, id) {
    this.root = root;
    this.id = id;
    this.term = new (window.Terminal || Terminal)({
      convertEol: true,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
      theme: {
        background: '#141821',
        foreground: '#e6eaf2',
        cursor: '#a3bffa',
        selectionBackground: '#2b344b'
      }
    });
    this.socket = null;
    if (window.FitAddon && window.FitAddon.FitAddon) {
      this.fit = new window.FitAddon.FitAddon();
      this.term.loadAddon(this.fit);
    } else {
      this.fit = null;
    }
  }

  connect() {
    this.socket = new WebSocket(WS_URL);
    this.socket.binaryType = 'arraybuffer';

    this.socket.onopen = () => {
      setStatus('Connected');
      this.term.writeln('\u001b[38;5;111m◆ Connected to Canvas Terminal\u001b[0m');
      this.term.focus();
      this.resizeToFit();
      // Send a probe command to verify end-to-end
      try {
        const probe = 'echo FRONTEND_OK && uname -a\r';
        this.socket.send(new TextEncoder().encode(probe));
      } catch (e) { console.error('probe send failed', e); }
    };

    this.socket.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        const text = new TextDecoder().decode(event.data);
        this.term.write(text);
      } else if (typeof event.data === 'string') {
        this.term.write(event.data);
      }
    };

    this.socket.onclose = () => { setStatus('Disconnected'); this.term.writeln('\r\n\x1b[31m◆ Disconnected\x1b[0m'); };
    this.socket.onerror = (e) => { setStatus('Error'); this.term.writeln('\r\n\x1b[31m◆ Socket error\x1b[0m'); console.error(e); };

    this.term.onData(data => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        // On Android, Enter may need CR instead of LF.
        const normalized = data.replace(/\r?\n/g, '\r');
        const bytes = new TextEncoder().encode(normalized);
        this.socket.send(bytes);
      }
    });

    const termContainer = this.root.querySelector('.terminal');
    this.term.open(termContainer);
    if (this.fit) this.fit.fit();

    const observer = new ResizeObserver(() => { if (this.fit) this.fit.fit(); this.resizeToFit(); });
    observer.observe(termContainer);

    // Ensure focus for mobile keyboard
    termContainer.addEventListener('click', () => this.term.focus());
  }

  resizeToFit() {
    const cols = Math.max(20, Math.floor(this.term.cols));
    const rows = Math.max(5, Math.floor(this.term.rows));
    try {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: 'resize', cols, rows }));
      }
    } catch {}
  }

  dispose() {
    try { this.socket?.close(); } catch {}
    try { this.term?.dispose(); } catch {}
  }
}

function createCard() {
  const tpl = document.getElementById('card-template');
  const node = tpl.content.firstElementChild.cloneNode(true);
  const rid = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : ('id-' + Date.now() + '-' + Math.random().toString(16).slice(2));
  node.dataset.id = rid;

  const closeBtn = node.querySelector('.btn.close');
  closeBtn.addEventListener('click', () => { canvas.dispose(); node.remove(); });

  const termDiv = node.querySelector('.terminal');
  termDiv.addEventListener('dblclick', () => termDiv.focus());

  document.getElementById('workspace').prepend(node);

  const canvas = new CommandCanvas(node, node.dataset.id);
  try {
    console.log('WS_URL =', WS_URL);
    canvas.connect();
  } catch (e) {
    console.error('Failed to connect websocket', e);
  }
  return canvas;
}

function setStatus(text) { document.getElementById('conn').textContent = text; }

function boot() {
  document.getElementById('new-card').addEventListener('click', createCard);
  createCard();
}

addEventListener('DOMContentLoaded', boot);

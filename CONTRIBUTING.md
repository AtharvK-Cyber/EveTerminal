# Contributing to EveTerminal

Thank you for your interest in contributing to **EveTerminal**! Our goal is to provide the network engineering community with the most dependable, fast, and ergonomic open-source terminal client for lab and production environments.

---

## 🛠️ Development Setup

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/AtharvK-Cyber/EveTerminal.git
cd EveTerminal

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .
pip install flake8 pytest
```

### 2. Running Unit Tests

Before submitting any changes, verify all automated tests pass:

```bash
python3 -m unittest discover tests -v
```

### 3. Launching in Development Mode

```bash
# Launch GUI directly from source tree
python3 -m eveterminal

# Or test with arguments
python3 -m eveterminal /T /N "R1" telnet://127.0.0.1:23
```

---

## 📜 Coding Guidelines

1. **Clean-Room Integrity**:
   - Never copy or reference proprietary decompiled source code.
   - Use documented standard RFCs (RFC 854/855 for Telnet, RFC 4251 for SSH, ECMA-48 / ANSI X3.64 for VT escape sequences).
2. **Thread Safety**:
   - Always marshal socket packets from background reader threads to the Qt GUI thread using `pyqtSignal` with `Qt.ConnectionType.QueuedConnection`. Never access GUI painter state directly from reader threads.
3. **Focus Isolation**:
   - The terminal canvas must never allow Qt focus traversal to swallow control keys like `Tab`, `Shift+Tab`, or Cisco break sequences (`Ctrl+Shift+6`).

---

## 🚀 Submitting a Pull Request

1. Fork the repository and create your feature branch: `git checkout -b feature/awesome-addition`.
2. Commit your changes: `git commit -m "feat: add feature description"`.
3. Push to your branch: `git push origin feature/awesome-addition`.
4. Open a Pull Request on GitHub describing your changes and test results.

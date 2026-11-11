# Wolftrack Dashboard

A cross-platform Electron and Vue desktop application designed to display live and recorded sensor telemetry data from the Wolftrack CAN data logging system.

## 🏗 Architecture

The Dashboard is a full-stack desktop application that pairs a **Vue.js Frontend** (packaged via Electron) with a **Python Backend [`wolftrack-visualizer`](https://github.com/wmBaja/wolftrack-visualizer)**.

- **Frontend:** Built with Vue 3, Vite, and TailwindCSS. It connects to the backend dynamically via WebSockets to stream live data.
- **Backend:** A FastAPI and PyZMQ python application that processes CAN bus data.
- **Dynamic Ports:** To avoid port conflicts on host machines, the Dashboard's Electron main process automatically spawns the Python backend on a dynamic, randomly assigned port, and securely passes that port to the Vue frontend via IPC.

---

## 💻 Local Development

### 1. Workspace Setup
Because the dashboard heavily relies on the backend, **you must have both repositories cloned locally**. By default, the dashboard expects them to be in the same parent directory:

```text
baja/
├── wolftrack-dashboard/
└── wolftrack-visualizer/
```

*Note: If your visualizer is cloned somewhere else, you must set an environment variable before running the dashboard:*
```bash
export WOLFTRACK_VISUALIZER_DIR="/path/to/your/custom/location"
```

### 2. Running the App
Install Node dependencies:
```bash
npm install
```

Start the application in Development Mode (with hot-reloading):
```bash
npm run dev
```

*(This will automatically find your local `wolftrack-visualizer` source code, spin up the Python backend using `uv run python`, and launch the Electron window).*

---

## 📦 Building & Packaging

### Local Production Build
To create a fully standalone executable (`.AppImage`, `.exe`, or `.dmg`) on your local machine:

1. Ensure the visualizer repository is set up side-by-side.
2. Run the build script:
```bash
npm run electron:build
```
This script will automatically:
- Compile the Python backend into a single executable using PyInstaller.
- Copy your local `.env` configuration.
- Build the Vue frontend.
- Package everything into a standalone Electron application located in the `release/` folder.

### GitHub Actions (CI/CD)
The project utilizes an optimized dual-repo CI/CD pipeline:
1. When code is pushed to `wolftrack-visualizer`, its workflow compiles the standalone binaries and attaches them to a "Rolling Release" on GitHub.
2. When code is pushed to this `wolftrack-dashboard` repository, the workflow **downloads the pre-built backend binaries directly** (skipping the 2-minute PyInstaller step), dynamically injects your `.env` configuration using GitHub Secrets, and packages the final Electron app. 
3. The final `.AppImage`/`.exe` is then published as an official GitHub Release automatically!
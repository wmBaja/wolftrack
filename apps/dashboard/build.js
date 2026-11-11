import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dashboardDir = __dirname;
const visualizerDir = path.join(__dirname, '../wolftrack-visualizer');
const backendDir = path.join(dashboardDir, 'backend');

function runCommand(command, cwd) {
    console.log(`\n> Running: ${command} in ${cwd}`);
    execSync(command, { stdio: 'inherit', cwd });
}

try {
    console.log("=== Building Python Backend (wolftrack-visualizer) ===");

    // Ensure pyinstaller is installed
    runCommand('uv add pyinstaller', visualizerDir);

    // Build the standalone executable
    // Note: added --paths src to ensure local modules like config.py are included
    runCommand('uv run pyinstaller --name wolftrack-visualizer --onefile --noconfirm --clean --paths src src/app.py', visualizerDir);

    console.log("\n=== Copying Backend to Electron Resources ===");

    if (!fs.existsSync(backendDir)) {
        fs.mkdirSync(backendDir, { recursive: true });
    }

    const isWindows = process.platform === 'win32';
    const executableName = isWindows ? 'wolftrack-visualizer.exe' : 'wolftrack-visualizer';

    const sourcePath = path.join(visualizerDir, 'dist', executableName);
    const destPath = path.join(backendDir, executableName);

    if (fs.existsSync(sourcePath)) {
        fs.copyFileSync(sourcePath, destPath);
        console.log(`Copied executable from ${sourcePath} to ${destPath}`);
    } else {
        console.error(`Error: Could not find built backend executable at ${sourcePath}`);
        process.exit(1);
    }

    const envSourcePath = path.join(visualizerDir, '.env');
    const envDestPath = path.join(backendDir, '.env');

    if (fs.existsSync(envSourcePath)) {
        fs.copyFileSync(envSourcePath, envDestPath);
        console.log(`Copied .env from ${envSourcePath} to ${envDestPath}`);
    } else {
        console.warn(`Warning: Could not find .env at ${visualizerDir}`);
    }

    console.log("\n=== Building Vue App ===");
    runCommand('npm run build', dashboardDir);

    console.log("\n=== Packaging Electron App ===");
    runCommand('npx electron-builder', dashboardDir);

    console.log("\n=== Build Complete! ===");
} catch (error) {
    console.error(`\nBuild failed: ${error.message}`);
    process.exit(1);
}

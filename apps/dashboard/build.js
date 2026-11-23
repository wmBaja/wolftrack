import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dashboardDir = __dirname;
const visualizerDir = path.join(__dirname, '../visualizer');
const backendDir = path.join(dashboardDir, 'backend');

function runCommand(command, cwd) {
    console.log(`\n> Running: ${command} in ${cwd}`);
    execSync(command, { stdio: 'inherit', cwd });
}

try {
    console.log("=== Building Python Backend (wolftrack-visualizer) ===");

    // Build the standalone backend directory. Local timing showed this starts
    // faster than --onefile, which extracts the same payload on every launch.
    runCommand('uv run pyinstaller --name wolftrack-visualizer --onedir --noconfirm --clean --paths src src/app.py', visualizerDir);

    console.log("\n=== Copying Backend to Electron Resources ===");

    if (!fs.existsSync(backendDir)) {
        fs.mkdirSync(backendDir, { recursive: true });
    }

    const sourcePath = path.join(visualizerDir, 'dist', 'wolftrack-visualizer');

    if (fs.existsSync(sourcePath)) {
        fs.cpSync(sourcePath, backendDir, { recursive: true });
        console.log(`Copied backend directory from ${sourcePath} to ${backendDir}`);
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

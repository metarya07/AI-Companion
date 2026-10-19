const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn, exec } = require('child_process');
const os = require('os');

const PORT = 42100;
const PROFILES_DIR = path.join(os.homedir(), '.claude', 'profiles');
const PACKAGE_ROOT = path.resolve(__dirname, '..', '..');
const PROJECTS_BASE = path.resolve(PACKAGE_ROOT, '..'); // 'A:\\Projects'

// Find Claude executable path
function getClaudePath() {
  const wingetPkg = path.join(
    os.homedir(),
    'AppData\\Local\\Microsoft\\WinGet\\Packages\\Anthropic.ClaudeCode_Microsoft.Winget.Source_8wekyb3d8bbwe\\claude.exe'
  );
  if (fs.existsSync(wingetPkg)) {
    return wingetPkg;
  }
  return 'claude';
}

// Check if OmniRoute server is responding
function checkOmniRouteStatus() {
  return new Promise((resolve) => {
    const req = http.get('http://localhost:20128/v1/models', { timeout: 1500 }, (res) => {
      resolve(res.statusCode >= 200 && res.statusCode < 500);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

// Start OmniRoute background process
function startOmniRoute() {
  return new Promise((resolve, reject) => {
    try {
      const child = spawn('cmd.exe', ['/c', 'start', '/min', 'powershell', '-NoExit', '-Command', 'omniroute'], {
        detached: true,
        stdio: 'ignore'
      });
      child.unref();
      setTimeout(resolve, 3000);
    } catch (err) {
      reject(err);
    }
  });
}

// Sync Claude profiles via OmniRoute
function syncProfiles() {
  return new Promise((resolve) => {
    exec('omniroute setup-claude', (error, stdout, stderr) => {
      if (error) {
        resolve({ success: false, error: stderr || error.message });
      } else {
        resolve({ success: true, output: stdout });
      }
    });
  });
}

// Get list of profiles with categories
function getProfiles() {
  if (!fs.existsSync(PROFILES_DIR)) {
    return [];
  }
  const files = fs.readdirSync(PROFILES_DIR, { withFileTypes: true });
  return files
    .filter(dirent => dirent.isDirectory())
    .map(dirent => {
      const name = dirent.name;
      let category = 'Other';
      let badge = 'Custom';
      let isFree = name.includes('free') || name.includes('auto');

      if (name.startsWith('auto-best-') || name.startsWith('auto-coding') || name.startsWith('meta-')) {
        category = 'Recommended & Combo';
        badge = name.includes('free') ? 'Free Combo' : 'Smart Router';
      } else if (name.startsWith('auto-')) {
        category = 'Auto Routing';
        badge = 'Auto';
      } else if (name.startsWith('antigravity-')) {
        category = 'Antigravity / Gemini';
        badge = 'Google / Antigravity';
      } else if (name.startsWith('nvidia-')) {
        category = 'Nvidia NIM';
        badge = 'Nvidia NIM';
      } else if (name.startsWith('openrouter-')) {
        category = 'OpenRouter';
        badge = name.includes('free') ? 'Free OpenRouter' : 'OpenRouter';
      } else if (name.startsWith('kiro-') || name.startsWith('kr-')) {
        category = 'Kiro Code';
        badge = 'Kiro';
      } else if (name.startsWith('ddgw-')) {
        category = 'DuckDuckGo Gateway';
        badge = 'Free Web';
      } else if (name.startsWith('aug-')) {
        category = 'August Claude/GPT';
        badge = 'Aug';
      }

      return {
        name,
        category,
        badge,
        isFree,
        path: path.join(PROFILES_DIR, name)
      };
    });
}

// Get project folders in workspace and A:\Projects
function getProjects() {
  const projects = [];
  projects.push({ name: 'AI-Companion (Current)', path: PACKAGE_ROOT });
  try {
    if (fs.existsSync(PROJECTS_BASE)) {
      const list = fs.readdirSync(PROJECTS_BASE, { withFileTypes: true });
      list.filter(d => d.isDirectory()).forEach(d => {
        const full = path.join(PROJECTS_BASE, d.name);
        if (full !== PACKAGE_ROOT) {
          projects.push({
            name: d.name,
            path: full
          });
        }
      });
    }
  } catch (e) {
    console.error('Error listing projects:', e);
  }
  projects.push({ name: 'A:\\ (Root Drive)', path: 'A:\\' });
  return projects;
}

// Launch Claude Code in a new terminal window
async function launchClaude(profileName, projectPath) {
  const isRunning = await checkOmniRouteStatus();
  if (!isRunning) {
    await startOmniRoute();
  }

  const claudeExe = getClaudePath();
  const profileDir = path.join(PROFILES_DIR, profileName);
  const targetDir = projectPath || PACKAGE_ROOT;

  // PowerShell command to launch
  const psCommand = [
    `$Host.UI.RawUI.WindowTitle = 'Claude Code [${profileName}]';`,
    `$env:CLAUDE_CONFIG_DIR = '${profileDir}';`,
    `$env:ANTHROPIC_BASE_URL = 'http://localhost:20128';`,
    `$env:ANTHROPIC_AUTH_TOKEN = 'dummy';`,
    `Remove-Item env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue;`,
    `Set-Location -Path '${targetDir}';`,
    `Write-Host '==================================================' -ForegroundColor Cyan;`,
    `Write-Host '  OmniRoute + Claude Code Launcher' -ForegroundColor Green;`,
    `Write-Host '  Profile:  ${profileName}' -ForegroundColor Yellow;`,
    `Write-Host '  Working:  ${targetDir}' -ForegroundColor Yellow;`,
    `Write-Host '  Gateway:  http://localhost:20128' -ForegroundColor Yellow;`,
    `Write-Host '==================================================' -ForegroundColor Cyan;`,
    `Write-Host '';`,
    `& '${claudeExe}'`
  ].join(' ');

  const child = spawn('cmd.exe', ['/c', 'start', 'powershell', '-NoExit', '-Command', psCommand], {
    detached: true,
    stdio: 'ignore'
  });
  child.unref();
  return { success: true, profile: profileName, directory: targetDir };
}

// HTTP Server
const server = http.createServer(async (req, res) => {
  const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
  const pathname = parsedUrl.pathname;

  const sendJson = (data, status = 200) => {
    res.writeHead(status, {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    res.end(JSON.stringify(data));
  };

  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    return res.end();
  }

  // API Endpoints
  if (pathname === '/api/status') {
    const isOmniRunning = await checkOmniRouteStatus();
    const profiles = getProfiles();
    return sendJson({
      omnirouteRunning: isOmniRunning,
      omnirouteUrl: 'http://localhost:20128',
      claudePath: getClaudePath(),
      profilesCount: profiles.length,
      workspace: PACKAGE_ROOT
    });
  }

  if (pathname === '/api/profiles') {
    return sendJson(getProfiles());
  }

  if (pathname === '/api/projects') {
    return sendJson(getProjects());
  }

  if (pathname === '/api/start-omniroute' && req.method === 'POST') {
    await startOmniRoute();
    return sendJson({ success: true, message: 'OmniRoute started' });
  }

  if (pathname === '/api/sync-profiles' && req.method === 'POST') {
    const result = await syncProfiles();
    return sendJson(result);
  }

  if (pathname === '/api/launch' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const data = JSON.parse(body || '{}');
        const profile = data.profile || 'auto-best-free';
        const project = data.project || PACKAGE_ROOT;
        const result = await launchClaude(profile, project);
        return sendJson(result);
      } catch (err) {
        return sendJson({ success: false, error: err.message }, 500);
      }
    });
    return;
  }

  // Serve static files from public/
  let filePath = path.join(__dirname, 'public', pathname === '/' ? 'index.html' : pathname);
  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    const ext = path.extname(filePath);
    const mimeTypes = {
      '.html': 'text/html',
      '.js': 'application/javascript',
      '.css': 'text/css',
      '.svg': 'image/svg+xml',
      '.png': 'image/png',
      '.json': 'application/json'
    };
    res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'text/plain' });
    return fs.createReadStream(filePath).pipe(res);
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not Found');
});

server.listen(PORT, () => {
  console.log(`\n======================================================`);
  console.log(`  OmniRoute & Claude Code Desktop Manager`);
  console.log(`  Running at: http://localhost:${PORT}`);
  console.log(`  Workspace: ${PACKAGE_ROOT}`);
  console.log(`======================================================\n`);
});

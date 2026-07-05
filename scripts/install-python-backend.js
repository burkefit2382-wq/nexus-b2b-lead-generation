const { spawnSync } = require("node:child_process");

const candidates = process.platform === "win32" ? ["python", "py"] : ["python3", "python"];

for (const command of candidates) {
  const args = command === "py"
    ? ["-3.11", "-m", "pip", "install", "-r", "backend/requirements.txt"]
    : ["-m", "pip", "install", "-r", "backend/requirements.txt"];
  const result = spawnSync(command, args, { stdio: "inherit" });
  if (result.status === 0) {
    process.exit(0);
  }
}

console.error("Unable to install Python backend requirements: no working Python command found.");
process.exit(1);

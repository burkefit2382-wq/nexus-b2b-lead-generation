const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const backendDir = path.join(root, "backend");
const distDir = path.join(root, "frontend", "dist");

const files = [
  "index.html",
  "dashboard.html",
  "lead-control-center.html",
  "workflow-demo.html",
  "styles.css",
  "app.js",
  "_headers",
  "staticwebapp.config.json",
];

const directories = ["assets", "pilot"];

function copyFile(relativePath) {
  const source = path.join(backendDir, relativePath);
  const target = path.join(distDir, relativePath);
  if (!fs.existsSync(source)) return;
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
  console.log(`copied ${relativePath}`);
}

function copyDirectory(relativePath) {
  const source = path.join(backendDir, relativePath);
  const target = path.join(distDir, relativePath);
  if (!fs.existsSync(source)) return;
  fs.cpSync(source, target, { recursive: true });
  console.log(`copied ${relativePath}/`);
}

fs.mkdirSync(distDir, { recursive: true });

for (const file of files) {
  copyFile(file);
}

for (const directory of directories) {
  copyDirectory(directory);
}

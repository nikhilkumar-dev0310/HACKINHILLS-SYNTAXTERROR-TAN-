// Bundle the React app (app/main.jsx) into one minified script: app.bundle.js.
// Only needed after editing files in app/; build.py inlines the bundle, so viewing the site needs no Node.
//   node dashboard/build_app.mjs        (needs esbuild, react and react-dom, e.g. npm i -g esbuild react react-dom)
import { createRequire } from "module";
import path from "path";
import { fileURLToPath } from "url";
const here = path.dirname(fileURLToPath(import.meta.url));
const roots = [process.env.NODE_PATH, path.join(here, "node_modules"), "/home/claude/.npm-global/lib/node_modules", "/usr/local/lib/node_modules", "/usr/lib/node_modules"].filter(Boolean);
const req = createRequire(import.meta.url);
let esbuild; for (const r of [...roots, path.join(roots[2], "tsx/node_modules")]) { try { esbuild = req(path.join(r, "esbuild")); break; } catch (e) {} }
if (!esbuild) { console.error("esbuild not found; install it with npm i -g esbuild"); process.exit(1); }
const res = await esbuild.build({
  entryPoints: [path.join(here, "app/main.jsx")], bundle: true, minify: true, format: "iife", target: ["es2020"], jsx: "automatic",
  nodePaths: roots, define: { "process.env.NODE_ENV": '"production"' }, outfile: path.join(here, "app.bundle.js"), legalComments: "none", logLevel: "warning", metafile: true
});
const kb = Object.values(res.metafile.outputs)[0].bytes / 1024;
console.log("wrote dashboard/app.bundle.js", Math.round(kb), "KB");

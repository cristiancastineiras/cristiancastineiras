// Genera static/pixel/logo.svg: el logo de la web (un prompt «>_» en píxeles), favicon incluido. Mismo tratamiento
// que el resto de sprites: tiles con relieve, degradado y esquinas convexas redondeadas. El cursor es fijo: parpadeando
// distrae del texto. Para cambiar el logo, redibuja ART (16×16) y vuelve a ejecutarlo.
//
//   node apps/web/scripts/make-pixel-logo.mjs
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { outlinePath, runPath, TILE_PATTERN } from "./pixel-lib.mjs";

// a = chevron, h = brillo, c = cursor
const ART = [
  "................",
  "................",
  "................",
  "..ha............",
  "..haa...........",
  "...aaa..........",
  "....aaa.........",
  ".....aaa........",
  ".....aaa........",
  "....aaa.........",
  "...aaa..........",
  "..aaa...........",
  "..aa....cccccc..",
  "........cccccc..",
  "................",
  "................",
];
const grid = ART.map((row) => row.split(""));
if (grid.some((r) => r.length !== 16) || grid.length !== 16) throw new Error("la cuadrícula debe ser de 16×16");

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none" role="img" aria-labelledby="title">
  <title id="title">Logo (pixel art)</title>
  <defs>
    ${TILE_PATTERN}
    <linearGradient id="chevron" x1="4" y1="6" x2="16" y2="26" gradientUnits="userSpaceOnUse">
      <stop stop-color="#56D364"/>
      <stop offset="0.5" stop-color="#2EA043"/>
      <stop offset="1" stop-color="#116329"/>
    </linearGradient>
    <linearGradient id="cursor" x1="16" y1="24" x2="28" y2="28" gradientUnits="userSpaceOnUse">
      <stop stop-color="#F2598A"/>
      <stop offset="1" stop-color="#FFB152"/>
    </linearGradient>
    <clipPath id="rounded-outline" clipPathUnits="userSpaceOnUse">
      <path clip-rule="evenodd" d="${outlinePath(grid)}"/>
    </clipPath>
  </defs>
  <g clip-path="url(#rounded-outline)">
    <path d="${runPath(grid, "a")}" fill="url(#chevron)"/>
    <path d="${runPath(grid, "h")}" fill="#AFF5B4"/>
    <path d="${runPath(grid, "a")}${runPath(grid, "h")}" fill="url(#tile-relief)"/>
    <g class="cursor">
      <path d="${runPath(grid, "c")}" fill="url(#cursor)"/>
      <path d="${runPath(grid, "c")}" fill="url(#tile-relief)"/>
    </g>
  </g>
</svg>
`;
writeFileSync(fileURLToPath(new URL("../static/pixel/logo.svg", import.meta.url)), svg);
console.log(`logo.svg (${(svg.length / 1024).toFixed(1)} KB)`);

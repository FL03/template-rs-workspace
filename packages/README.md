# Web package integration

Place JavaScript/TypeScript wrappers and Emscripten build packaging here.
These are excluded from Cargo workspace membership. Rust packages stay under
`crates/` or `cmp/`; compile and package them for the selected web target.

`wasm32-unknown-unknown` with wasm-bindgen, `wasm32-wasip2` components, and
`wasm32-unknown-emscripten` have different linking/runtime contracts. Emscripten
requires a separately installed and activated emsdk (`emcc`). No SDK or web
runtime is installed by this template.

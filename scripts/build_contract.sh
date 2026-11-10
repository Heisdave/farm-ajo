#!/usr/bin/env bash
# Build the Farm Ajo circle contract to wasm (release, size-optimised).
set -euo pipefail
cd "$(dirname "$0")/../contracts/ajo-circle"
export PATH="$HOME/.cargo/bin:$PATH"
rustup target add wasm32-unknown-unknown
cargo build --target wasm32-unknown-unknown --release
mkdir -p res
cp target/wasm32-unknown-unknown/release/farm_ajo_circle.wasm res/
ls -lh res/farm_ajo_circle.wasm

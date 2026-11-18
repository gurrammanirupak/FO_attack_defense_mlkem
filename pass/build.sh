#!/usr/bin/env bash
# Build the FODefensePass LLVM plugin.
# Requires clang++/llvm-config from LLVM 18 on PATH.
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p build

clang++ -fPIC -shared \
    $(llvm-config --cxxflags) \
    FODefensePass.cpp \
    -o build/FODefensePass.so

echo "Built: $(pwd)/build/FODefensePass.so"
echo "Export it for the firmware wrapper with:"
echo "  export FODEFENSE_SO=$(pwd)/build/FODefensePass.so"

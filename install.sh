#!/bin/bash

# Update submodules
git submodule update --init --recursive
if [ $? -ne 0 ]; then
    echo "Error: Submodule update failed"
    exit 1
fi

# Install Python dependencies
pip install -r requirements.txt --user
if [ $? -ne 0 ]; then
    echo "Error: Python dependencies installation failed"
    exit 1
fi


# Install and build repo-visualizer
cd vendor/repo-visualizer
npm install --legacy-peer-deps
if [ $? -ne 0 ]; then
    echo "Error: repo-visualizer dependencies installation failed"
    exit 1
fi

npm install -g esbuild
if [ $? -ne 0 ]; then
    echo "Error: esbuild installation failed"
    exit 1
fi

mkdir -p dist
npm run build
if [ $? -ne 0 ]; then
    echo "Error: repo-visualizer build failed"
    exit 1
fi
cd ../..

# Create symbolic link for kin command
if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo ln -sf "$(pwd)/kin" /usr/local/bin/kin
fi
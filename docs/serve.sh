#!/bin/bash

echo "🚀 OMA Documentation Server"
echo "=========================="

# Check if bundle is installed
if ! command -v bundle &> /dev/null; then
    echo "❌ Bundler is not installed. Installing..."
    gem install bundler
fi

echo "📦 Installing dependencies..."
bundle install

echo "🔧 Building site..."
bundle exec jekyll build

echo "🌐 Starting Jekyll server..."
echo "📍 Site will be available at: http://localhost:4000"
echo "🔄 Live reload enabled - changes will be reflected automatically"
echo "⏹️  Press Ctrl+C to stop the server"
echo ""

bundle exec jekyll serve --livereload --open-url --host 0.0.0.0

#!/bin/bash

# Jekyll 로컬 서버 실행 스크립트
echo "Installing dependencies..."
bundle install

echo "Starting Jekyll server..."
bundle exec jekyll serve --livereload --open-url

echo "Jekyll server is running at http://localhost:4000"
echo "Press Ctrl+C to stop the server"

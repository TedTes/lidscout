#!/bin/bash

echo "🚀 Creating Business Scraper Project Structure"
echo "=============================================="
echo ""

# Create main directories
echo "📁 Creating directory structure..."
mkdir -p backend/app/{api,models,services,utils}
mkdir -p frontend/src/{app,components,services,types}

echo "✅ Directories created"
echo ""
echo "📝 Project structure ready!"
echo ""
echo "Structure:"
echo "business-scraper/"
echo "├── backend/"
echo "│   └── app/"
echo "│       ├── api/"
echo "│       ├── models/"
echo "│       ├── services/"
echo "│       └── utils/"
echo "└── frontend/"
echo "    └── src/"
echo "        ├── app/"
echo "        ├── components/"
echo "        ├── services/"
echo "        └── types/"
echo ""
echo "✅ Done! Ready to add files."
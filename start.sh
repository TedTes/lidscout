#!/bin/bash

echo "Creating LidScout signal detection project structure"
echo "=============================================="
echo ""

# Create main directories
echo "Creating directory structure..."
mkdir -p domain/{signal,score,cluster}
mkdir -p application/{ingestion,extraction,scoring,clustering,reporting}
mkdir -p adapters/{reddit,hackernews}
mkdir -p infrastructure/{db,llm,email,scheduler}
mkdir -p api/{routes,controllers,schemas}
mkdir -p workers
mkdir -p web_client/{app,components,hooks,lib,styles}
mkdir -p shared
mkdir -p tests

echo "Directories created"
echo ""
echo "Project structure ready"
echo ""
echo "Structure:"
echo "lidscout/"
echo "├── domain/{signal,score,cluster}"
echo "├── application/{ingestion,extraction,scoring,clustering,reporting}"
echo "├── adapters/{reddit,hackernews}"
echo "├── infrastructure/{db,llm,email,scheduler}"
echo "├── api/{routes,controllers,schemas}"
echo "├── workers"
echo "├── web_client/{app,components,hooks,lib,styles}"
echo "├── shared"
echo "└── tests"
echo ""
echo "Done. Ready to add files."

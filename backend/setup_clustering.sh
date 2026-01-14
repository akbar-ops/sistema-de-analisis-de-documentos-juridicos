#!/bin/bash

# Setup script for new clustering architecture
# Run this after pulling the new code

set -e  # Exit on error

echo "================================================================"
echo "  Cluster Graph Architecture - Setup Script"
echo "================================================================"
echo ""

# Check if we're in the backend directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Please run this script from the backend/ directory"
    exit 1
fi

# 1. Install dependencies
echo "📦 Step 1/5: Installing Python dependencies..."
pip install umap-learn hdbscan scikit-learn

# 2. Create migrations
echo ""
echo "🗄️  Step 2/5: Creating database migrations..."
python manage.py makemigrations documents

# 3. Run migrations
echo ""
echo "⚡ Step 3/5: Running migrations..."
python manage.py migrate

# 4. Check for documents
echo ""
echo "📊 Step 4/5: Checking for documents with embeddings..."
python manage.py shell << EOF
from apps.documents.models import Document
count = Document.objects.filter(
    status='processed',
    enhanced_embedding__isnull=False
).count()
print(f"\n✅ Found {count} documents with embeddings")
if count == 0:
    print("⚠️  Warning: No documents with embeddings found!")
    print("   You need to process some documents first before clustering.")
else:
    print(f"   Ready to cluster {count} documents!")
EOF

# 5. Prompt for initial cluster computation
echo ""
echo "🎯 Step 5/5: Compute initial cluster graph?"
echo "   This will create the first cluster graph (may take 1-5 minutes)"
echo ""
read -p "   Run initial clustering now? [y/N] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Computing initial cluster graph..."
    echo "   (Using up to 200 documents for faster initial computation)"
    echo ""
    python manage.py rebuild_clusters --max-docs 200
    
    echo ""
    echo "✅ Initial cluster graph created!"
fi

# Done
echo ""
echo "================================================================"
echo "  ✅ Setup Complete!"
echo "================================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Start Celery worker (for background tasks):"
echo "   celery -A config worker --loglevel=info -Q default,high_priority"
echo ""
echo "2. Start Celery Beat (for nightly recomputation):"
echo "   celery -A config beat --loglevel=info"
echo ""
echo "   Or run both together:"
echo "   celery -A config worker -B --loglevel=info -Q default,high_priority"
echo ""
echo "3. Test the API:"
echo "   curl http://localhost:8000/api/documents/all_clusters/"
echo ""
echo "4. View cluster graphs in admin:"
echo "   http://localhost:8000/admin/documents/clustergraph/"
echo ""
echo "5. Manually rebuild clusters anytime:"
echo "   python manage.py rebuild_clusters"
echo ""
echo "📖 Documentation:"
echo "   - CLUSTER_ARCHITECTURE.md (full guide)"
echo "   - MIGRATION_GUIDE.md (migration from old system)"
echo ""
echo "================================================================"

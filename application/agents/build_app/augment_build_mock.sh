#!/bin/bash
# Mock Augment CLI script for testing
# Simulates successful code generation without requiring API credentials

PROMPT_OR_FILE="${1:-}"
MODEL="${2:-sonnet4}"
WORKSPACE_DIR="${3:-$(pwd)}"
BRANCH_ID="${4:-unknown}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$BRANCH_ID] $1"
}

log "Starting Mock Augment CLI execution"
log "Model: $MODEL"
log "Workspace: $WORKSPACE_DIR"
log "Branch ID: $BRANCH_ID"

# Simulate some work
sleep 2

# Create some mock files to simulate code generation
cd "$WORKSPACE_DIR" || exit 1

# Create mock entity files
mkdir -p application/entity/pet/version_1
cat > application/entity/pet/version_1/pet.py << 'EOF'
"""Pet entity for pet store application."""
from pydantic import BaseModel

class Pet(BaseModel):
    """Pet entity."""
    name: str
    species: str
    age: int
EOF

mkdir -p application/entity/report/version_1
cat > application/entity/report/version_1/report.py << 'EOF'
"""Report entity for pet store application."""
from pydantic import BaseModel

class Report(BaseModel):
    """Report entity."""
    title: str
    content: str
EOF

# Create mock processor
mkdir -p application/processor
cat > application/processor/report_processor.py << 'EOF'
"""Report processor for generating reports."""

async def generate_report(data):
    """Generate report from pet data."""
    return {"title": "Pet Report", "content": "Mock report content"}
EOF

# Create mock routes
mkdir -p application/routes
cat > application/routes/pets.py << 'EOF'
"""Pet routes."""
from quart import Blueprint

pets_bp = Blueprint('pets', __name__)

@pets_bp.route('/pets', methods=['GET'])
async def list_pets():
    return {"pets": []}
EOF

cat > application/routes/reports.py << 'EOF'
"""Report routes."""
from quart import Blueprint

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports', methods=['GET'])
async def list_reports():
    return {"reports": []}
EOF

# Create mock workflows
mkdir -p application/resources/workflow/pet/version_1
cat > application/resources/workflow/pet/version_1/Pet.json << 'EOF'
{
  "name": "Pet",
  "version": "1",
  "states": []
}
EOF

mkdir -p application/resources/workflow/report/version_1
cat > application/resources/workflow/report/version_1/Report.json << 'EOF'
{
  "name": "Report",
  "version": "1",
  "states": []
}
EOF

log "Mock Augment CLI execution completed successfully"
exit 0


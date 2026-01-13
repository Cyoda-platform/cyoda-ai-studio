#!/bin/bash

# Cyoda AI Studio - Open All HTML Reports
# Opens all generated HTML reports in the default browser

REPORTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/reports"

echo "🌐 Opening HTML reports..."
echo "========================="
echo ""

# Function to open a report
open_report() {
    local report_path="$1"
    local report_name="$2"

    if [ -f "$report_path" ]; then
        echo "✅ Opening $report_name..."
        xdg-open "$report_path" 2>/dev/null || open "$report_path" 2>/dev/null || start "$report_path" 2>/dev/null || {
            echo "⚠️  Could not open $report_name automatically"
            echo "   Path: $report_path"
        }
        sleep 1
    else
        echo "⚠️  $report_name not found at: $report_path"
        echo "   Run the corresponding make target first:"
        case "$report_name" in
            "Coverage Report")
                echo "   make test-coverage"
                ;;
            "Eval Report")
                echo "   make test-eval"
                ;;
            "Lint Report")
                echo "   make lint"
                ;;
            "Complexity Report")
                echo "   make complexity"
                ;;
        esac
    fi
    echo ""
}

# Open all reports
open_report "$REPORTS_DIR/coverage/index.html" "Coverage Report"
open_report "$REPORTS_DIR/eval/unified_report.html" "Eval Report"
open_report "$REPORTS_DIR/lint/report.html" "Lint Report"
open_report "$REPORTS_DIR/complexity/report.html" "Complexity Report"

echo "========================="
echo "✅ Done!"
echo ""
echo "💡 Tip: Run 'make check-all' to generate all reports"
echo ""

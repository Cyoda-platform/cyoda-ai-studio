# ADK Evaluation Visualization Guide

Complete guide to visualizing and reporting on ADK evaluation results.

---

## 🎨 Visualization Options

### 1. HTML Report (Recommended) ⭐

**Beautiful, shareable HTML reports with charts and detailed breakdowns.**

```bash
# Generate HTML report from latest eval results
python application/agents/tests/evals/generate_html_report.py \
  application/agents/.adk/eval_history/agents_coordinator_routing_*.json \
  -o eval_report.html

# Open in browser
open eval_report.html  # macOS
xdg-open eval_report.html  # Linux
start eval_report.html  # Windows
```

**Features:**
- ✅ Clean, modern UI with color-coded results
- ✅ Summary statistics (pass rate, scores)
- ✅ Detailed per-test breakdowns
- ✅ Tool call comparisons (expected vs actual)
- ✅ Match indicators (✅ MATCH / ❌ MISMATCH)
- ✅ Print-friendly styling
- ✅ Shareable with team

**Example Output:**
```
📊 Summary: 8/10 tests passed (80%)
🌐 Open in browser: file:///.../eval_report.html
```

---

### 2. Console Table Output

**Quick terminal view with detailed results.**

```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true

adk eval application/agents \
  application/agents/tests/evals/coordinator_routing.evalset.json \
  --config_file_path application/agents/tests/evals/tools_only_config.json \
  --print_detailed_results
```

**Output:**
```
+----+---------------------------+---------------------------+-------------------+
|    | prompt                    | expected_response         | actual_response   |
+====+===========================+===========================+===================+
|  0 | Deploy my environment     | Let me deploy.            | (empty)           |
+----+---------------------------+---------------------------+-------------------+
```

**Features:**
- ✅ Immediate feedback in terminal
- ✅ Table format with aligned columns
- ✅ Shows prompts, responses, tool calls, scores
- ✅ Good for CI/CD pipelines

---

### 3. ADK Web UI (Interactive Testing) 🌐

**Browser-based interactive UI for live agent testing.**

```bash
# Launch Web UI
./application/agents/tests/evals/launch_web_ui.sh

# Or manually:
adk web application/agents \
  --port 8080 \
  --reload \
  --logo-text "Cyoda AI Assistant"
```

**Access:** http://127.0.0.1:8080

**Features:**
- ✅ Chat interface for testing agents
- ✅ Real-time conversation testing
- ✅ Session persistence (SQLite)
- ✅ Artifact storage
- ✅ Multi-agent routing visualization
- ✅ Auto-reload on code changes

**Use Cases:**
- Manual testing of conversation flows
- Debugging agent behavior
- Demonstrating to stakeholders
- Exploratory testing

---

### 4. Custom Python Analysis

**Detailed programmatic analysis of results.**

```bash
# Analyze specific result file
python application/agents/tests/evals/analyze_eval_results.py \
  application/agents/.adk/eval_history/agents_*.evalset_result.json
```

**Output:**
```
================================================================================
EVAL CASE: case_07_deploy_environment
STATUS: ✅ PASSED
================================================================================

METRICS:
  tool_trajectory_avg_score: 1.00 (threshold: 1.0) ✅ PASS

TOOL CALLS COMPARISON:
Expected: transfer_to_agent(environment_agent)
Actual:   transfer_to_agent(environment_agent)
✅ MATCH
```

**Features:**
- ✅ Detailed side-by-side comparisons
- ✅ Line-by-line tool call analysis
- ✅ Response matching details
- ✅ Customizable output format

---

### 5. ADK Visual Builder (Future)

**Drag-and-drop agent workflow designer.**

**Status:** Not yet in ADK Python CLI (available in Cloud Console)

**Cloud Console Access:**
1. Go to https://console.cloud.google.com/ai/reasoning-engines
2. Navigate to Agent Builder
3. Use Visual Builder for drag-and-drop design

**Alternative:** Third-party visualizer at https://github.com/glaforge (ADK Agent Code Visualizer)

---

## 📊 Comparison Matrix

| Feature | HTML Report | Console Table | Web UI | Python Script |
|---------|-------------|---------------|--------|---------------|
| **Speed** | Fast | Instant | Real-time | Fast |
| **Detail Level** | High | Medium | Interactive | Very High |
| **Shareable** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Interactive** | ❌ No | ❌ No | ✅ Yes | ❌ No |
| **CI/CD Friendly** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| **Offline** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Pretty** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |

---

## 🎯 Recommended Workflows

### For Daily Development
1. **Run eval** with `--print_detailed_results` for quick feedback
2. **Generate HTML report** weekly for progress tracking
3. **Use Web UI** for interactive debugging

### For CI/CD
```bash
# Run eval (exit code 0 if passed, 1 if failed)
adk eval application/agents tests/coordinator_routing.evalset.json \
  --config_file_path tests/tools_only_config.json \
  > eval_output.txt 2>&1

# Generate HTML report
python tests/generate_html_report.py \
  .adk/eval_history/agents_*.json \
  -o reports/eval_${CI_COMMIT_SHA}.html

# Archive HTML report
mv reports/eval_${CI_COMMIT_SHA}.html ${CI_ARTIFACTS_DIR}/
```

### For Stakeholder Demos
1. **Launch Web UI** (`./launch_web_ui.sh`)
2. **Demo live conversations** with agents
3. **Share HTML report** for detailed results

### For Debugging Failures
1. **Run analysis script** to see exact differences
2. **Compare expected vs actual** tool calls
3. **Inspect LLM reasoning** in detailed output

---

## 🛠️ Advanced: Custom Visualization

### Export to JSON for Custom Tools

```python
import json
from pathlib import Path

# Load eval results
result_file = Path(".adk/eval_history/agents_*.evalset_result.json")
data = json.loads(result_file.read_text())

# Extract metrics
for case in data['eval_case_results']:
    print(f"{case['eval_id']}: {case['final_eval_status']}")
```

### Integration with Dashboards

Export results to:
- **Grafana**: Convert JSON → InfluxDB → Grafana
- **Tableau**: Export to CSV for analysis
- **Google Sheets**: Use Apps Script to import JSON
- **Jupyter Notebook**: Analyze with pandas/matplotlib

Example CSV export:
```python
import csv

cases = data['eval_case_results']
with open('eval_results.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['Test ID', 'Status', 'Score'])
    for case in cases:
        writer.writerow([
            case['eval_id'],
            'PASS' if case['final_eval_status'] == 1 else 'FAIL',
            case['overall_eval_metric_results'][0]['score']
        ])
```

---

## 📁 Output Files

### Evaluation Results Location
```
application/agents/
└── .adk/
    └── eval_history/
        ├── agents_coordinator_routing_1767210775.xxx.evalset_result.json
        ├── agents_coordinator_routing_1767210775.yyy.evalset_result.json
        └── ...
```

### Generated Reports
```
application/agents/tests/evals/
├── latest_eval_report.html          # HTML report
├── FULL_EVAL_COMPARISON.txt         # Text analysis
└── eval_results.csv                 # CSV export (if created)
```

---

## 🚀 Quick Start Examples

### Generate HTML Report Now
```bash
cd application/agents/tests/evals
python generate_html_report.py \
  ../../.adk/eval_history/agents_coordinator_routing_*.json \
  -o latest_eval_report.html

# Open in browser
open latest_eval_report.html
```

### Launch Web UI Now
```bash
cd application/agents/tests/evals
./launch_web_ui.sh
```

### Run Eval with Detailed Output
```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true
adk eval application/agents \
  application/agents/tests/evals/coordinator_routing.evalset.json \
  --config_file_path application/agents/tests/evals/tools_only_config.json \
  --print_detailed_results | tee eval_output.txt
```

---

## 💡 Tips

### Best Practices
1. **Generate HTML reports after each major change** for tracking
2. **Use Web UI during development** for quick iteration
3. **Archive HTML reports** by date or commit hash
4. **Share reports with team** via email/Slack/Confluence

### Customization
- Modify `generate_html_report.py` for custom styling
- Add company logo to HTML template
- Integrate with existing reporting tools
- Create custom visualizations with matplotlib/plotly

### Performance
- HTML generation is fast (~1 second for 10 tests)
- Web UI supports hot reload for development
- Console output is instant

---

## 📚 Related Documentation

- **FINAL_SOLUTION.md** - Complete evaluation implementation
- **README.md** - Quick start guide
- **README_MOCKING.md** - Tool mocking details
- [ADK Documentation](https://google.github.io/adk-docs/)
- [Visual Builder Guide](https://google.github.io/adk-docs/visual-builder/)

---

## 🆘 Troubleshooting

### "HTML report is blank"
- Check that result files exist: `ls .adk/eval_history/*.json`
- Verify JSON is valid: `python -m json.tool result.json`

### "Web UI won't start"
- Check port 8080 is available: `lsof -i :8080`
- Try different port: `adk web application/agents --port 8081`

### "Can't find ADK Studio"
- ADK Studio is in Google Cloud Console, not CLI
- Use Web UI (`adk web`) for local development
- Or use Visual Builder in cloud console

---

## ✨ Examples

See the included files:
- **latest_eval_report.html** - Example HTML report
- **launch_web_ui.sh** - Web UI launcher script
- **generate_html_report.py** - HTML generator source

**Your HTML report is ready!**

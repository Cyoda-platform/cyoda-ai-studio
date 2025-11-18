"""
Tests for intelligent workflow and entity scanning with flexible naming conventions.

This test suite verifies that the _scan_versioned_resources function can handle:
- Exact case matches (customerworkflow.json)
- Case-insensitive matches (CustomerWorkflow.json for customerworkflow directory)
- Single JSON file fallback
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from application.agents.github.tools import _scan_versioned_resources


class TestWorkflowScanning:
    """Test intelligent workflow scanning with various naming conventions."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_exact_case_match(self, temp_repo):
        """Test scanning with exact case match (lowercase directory, lowercase file)."""
        workflow_dir = temp_repo / 'workflow' / 'orderprocessing' / 'version_1'
        workflow_dir.mkdir(parents=True)

        workflow_file = workflow_dir / 'orderprocessing.json'
        workflow_file.write_text(json.dumps({'name': 'OrderProcessing', 'states': []}))

        results = _scan_versioned_resources(temp_repo / 'workflow', 'workflow', temp_repo)

        assert len(results) == 1
        assert results[0]['name'] == 'orderprocessing'
        assert results[0]['version'] == 'version_1'
        assert results[0]['path'] == 'workflow/orderprocessing/version_1/orderprocessing.json'
        assert results[0]['content']['name'] == 'OrderProcessing'

    def test_case_insensitive_match(self, temp_repo):
        """Test scanning with case-insensitive match (lowercase directory, PascalCase file)."""
        workflow_dir = temp_repo / 'workflow' / 'customerworkflow' / 'version_1'
        workflow_dir.mkdir(parents=True)

        workflow_file = workflow_dir / 'CustomerWorkflow.json'
        workflow_file.write_text(json.dumps({'name': 'CustomerWorkflow', 'states': []}))

        results = _scan_versioned_resources(temp_repo / 'workflow', 'workflow', temp_repo)

        assert len(results) == 1
        assert results[0]['name'] == 'customerworkflow'
        assert results[0]['version'] == 'version_1'
        assert results[0]['path'] == 'workflow/customerworkflow/version_1/CustomerWorkflow.json'
        assert results[0]['content']['name'] == 'CustomerWorkflow'

    def test_single_file_fallback(self, temp_repo):
        """Test scanning with single JSON file fallback (different name)."""
        workflow_dir = temp_repo / 'workflow' / 'payment' / 'version_1'
        workflow_dir.mkdir(parents=True)

        workflow_file = workflow_dir / 'PaymentWorkflow.json'
        workflow_file.write_text(json.dumps({'name': 'Payment', 'states': []}))

        results = _scan_versioned_resources(temp_repo / 'workflow', 'workflow', temp_repo)

        assert len(results) == 1
        assert results[0]['name'] == 'payment'
        assert results[0]['version'] == 'version_1'
        assert results[0]['path'] == 'workflow/payment/version_1/PaymentWorkflow.json'

    def test_multiple_versions(self, temp_repo):
        """Test scanning with multiple versions of the same workflow."""
        for version in [1, 2, 3]:
            workflow_dir = temp_repo / 'workflow' / 'order' / f'version_{version}'
            workflow_dir.mkdir(parents=True)

            workflow_file = workflow_dir / 'Order.json'
            workflow_file.write_text(json.dumps({'name': 'Order', 'version': version}))

        results = _scan_versioned_resources(temp_repo / 'workflow', 'workflow', temp_repo)

        assert len(results) == 3
        assert all(r['name'] == 'order' for r in results)
        assert [r['version'] for r in results] == ['version_1', 'version_2', 'version_3']

    def test_mixed_naming_conventions(self, temp_repo):
        """Test scanning with mixed naming conventions in the same directory."""
        workflows = [
            ('orderprocessing', 'version_1', 'orderprocessing.json'),  # Exact match
            ('customerworkflow', 'version_1', 'CustomerWorkflow.json'),  # Case-insensitive
            ('payment', 'version_1', 'PaymentWorkflow.json'),  # Single file fallback
        ]

        for workflow_name, version, filename in workflows:
            workflow_dir = temp_repo / 'workflow' / workflow_name / version
            workflow_dir.mkdir(parents=True)

            workflow_file = workflow_dir / filename
            workflow_file.write_text(json.dumps({'name': workflow_name}))

        results = _scan_versioned_resources(temp_repo / 'workflow', 'workflow', temp_repo)

        assert len(results) == 3
        workflow_names = {r['name'] for r in results}
        assert workflow_names == {'orderprocessing', 'customerworkflow', 'payment'}

    def test_direct_json_file(self, temp_repo):
        """Test scanning with direct JSON file (no versioning)."""
        workflow_dir = temp_repo / 'workflow'
        workflow_dir.mkdir(parents=True)

        workflow_file = workflow_dir / 'simple.json'
        workflow_file.write_text(json.dumps({'name': 'Simple', 'states': []}))

        results = _scan_versioned_resources(workflow_dir, 'workflow', temp_repo)

        assert len(results) == 1
        assert results[0]['name'] == 'simple'
        assert results[0]['version'] is None
        assert results[0]['path'] == 'workflow/simple.json'

    def test_directory_without_version_case_insensitive(self, temp_repo):
        """Test scanning directory without version structure with case-insensitive match."""
        workflow_dir = temp_repo / 'workflow' / 'simple'
        workflow_dir.mkdir(parents=True)

        workflow_file = workflow_dir / 'Simple.json'
        workflow_file.write_text(json.dumps({'name': 'Simple', 'states': []}))

        results = _scan_versioned_resources(temp_repo / 'workflow', 'workflow', temp_repo)

        assert len(results) == 1
        assert results[0]['name'] == 'simple'
        assert results[0]['version'] is None
        assert results[0]['path'] == 'workflow/simple/Simple.json'

    def test_empty_directory(self, temp_repo):
        """Test scanning with empty workflow directory."""
        workflow_dir = temp_repo / 'workflow'
        workflow_dir.mkdir(parents=True)

        results = _scan_versioned_resources(workflow_dir, 'workflow', temp_repo)

        assert len(results) == 0

    def test_nonexistent_directory(self, temp_repo):
        """Test scanning with non-existent workflow directory."""
        results = _scan_versioned_resources(temp_repo / 'workflow', 'workflow', temp_repo)

        assert len(results) == 0

    def test_invalid_json_file(self, temp_repo):
        """Test scanning with invalid JSON file (should be skipped with warning)."""
        workflow_dir = temp_repo / 'workflow' / 'invalid' / 'version_1'
        workflow_dir.mkdir(parents=True)

        workflow_file = workflow_dir / 'Invalid.json'
        workflow_file.write_text('{ invalid json }')

        results = _scan_versioned_resources(temp_repo / 'workflow', 'workflow', temp_repo)

        assert len(results) == 0

    def test_entity_scanning(self, temp_repo):
        """Test that the same logic works for entity scanning."""
        entity_dir = temp_repo / 'entity' / 'customer' / 'version_1'
        entity_dir.mkdir(parents=True)

        entity_file = entity_dir / 'Customer.json'
        entity_file.write_text(json.dumps({'name': 'Customer', 'fields': []}))

        results = _scan_versioned_resources(temp_repo / 'entity', 'entity', temp_repo)

        assert len(results) == 1
        assert results[0]['name'] == 'customer'
        assert results[0]['version'] == 'version_1'
        assert results[0]['path'] == 'entity/customer/version_1/Customer.json'


#!/usr/bin/env python3
"""Fix all eval_id values to be unique and descriptive."""

import json
import re
from pathlib import Path


def slugify(text):
    """Convert text to a clean slug."""
    # Remove special characters, convert to lowercase
    text = re.sub(r"[^\w\s-]", "", text.lower())
    # Replace spaces and underscores with hyphens
    text = re.sub(r"[-\s]+", "_", text)
    return text.strip("_")


def generate_eval_id(filename, eval_set_id, existing_ids):
    """Generate a unique and descriptive eval_id from filename or eval_set_id."""

    # Remove .evalset.json suffix
    base = filename.replace(".evalset.json", "")

    # Mappings for common patterns
    mappings = {
        # GitHub scenarios
        "github_scenario_add_a_customer_entity_with_id_name_email_phone_fie": "gh_add_customer_entity",
        "github_scenario_add_a_discount_feature_to_orders": "gh_add_discount_feature",
        "github_scenario_add_a_processor_to_validate_email_format_in_custom": "gh_add_email_validator",
        "github_scenario_add_a_requirement_document_to_the_repository_for_a": "gh_add_requirements_doc",
        "github_scenario_add_a_workflow_for_customer_with_create_update_del": "gh_add_customer_workflow",
        "github_scenario_add_rest_endpoints_for_product_entity_with_get_pos": "gh_add_product_endpoints",
        "github_scenario_build_an_application_based_on_the_attached_require": "gh_build_app_from_requirements",
        "github_scenario_build_an_application_based_on_the_docs_in_this_bra": "gh_build_app_from_docs",
        "github_scenario_view_edit_the_customer_entity_in_the_canvas": "gh_view_customer_entity",
        "github_scenario_view_edit_the_order_workflow_in_the_canvas": "gh_view_order_workflow",
        "github_scenario_view_edit_the_requirement_document_in_the_canvas": "gh_view_requirements_doc",
        # Build app scenarios
        "build_app_design_functional_requirements": "gh_design_requirements",
        "build_app_initial_request": "gh_initial_request",
        "build_app_repo_setup": "gh_repo_setup",
        "institutional_trading_platform": "gh_trading_platform",
        # Setup scenarios
        "launch_setup_agent_initial": "setup_initial",
        "setup": "setup_general",
        # Coordinator scenarios
        "coordinator": "coord_general",
        "coordinator_routing": "coord_routing",
        # QA scenarios
        "what_is_cyoda": "qa_what_is_cyoda",
    }

    # Check if we have a direct mapping
    if base in mappings:
        eval_id = mappings[base]
    else:
        # Generate from the base name
        # Remove prefixes
        for prefix in [
            "github_scenario_",
            "environment_scenario_",
            "setup_",
            "coordinator_",
        ]:
            if base.startswith(prefix):
                base = base[len(prefix) :]
                break

        # Truncate if too long and make it a slug
        eval_id = slugify(base)[:50]

    # Ensure uniqueness
    original_id = eval_id
    counter = 1
    while eval_id in existing_ids:
        eval_id = f"{original_id}_{counter}"
        counter += 1

    return eval_id


def fix_all_eval_ids():
    """Update eval_ids in all evalset files."""
    base_path = Path(__file__).parent.parent.parent.parent.parent
    agents_dir = base_path / "application/agents"

    if not agents_dir.exists():
        print(f"❌ Directory not found: {agents_dir}")
        return

    # Find all evalset files
    evalset_files = list(agents_dir.rglob("*.evalset.json"))

    print(f"📊 Found {len(evalset_files)} evalset files\n")

    # Track all eval_ids to ensure uniqueness
    all_eval_ids = set()
    updates = []

    for evalset_file in sorted(evalset_files):
        # Read the file
        with open(evalset_file, "r") as f:
            data = json.load(f)

        eval_set_id = data.get("eval_set_id", "")
        filename = evalset_file.name

        # Get old eval_ids
        old_eval_ids = [case.get("eval_id", "") for case in data.get("eval_cases", [])]

        # Generate new eval_id (all cases in same file get same base id)
        new_eval_id_base = generate_eval_id(filename, eval_set_id, all_eval_ids)

        # Update all cases
        for idx, case in enumerate(data.get("eval_cases", [])):
            old_id = case.get("eval_id", "")

            # If multiple cases, append index
            if len(data.get("eval_cases", [])) > 1:
                new_eval_id = f"{new_eval_id_base}_{idx + 1}"
            else:
                new_eval_id = new_eval_id_base

            # Ensure uniqueness
            counter = 1
            original_new_id = new_eval_id
            while new_eval_id in all_eval_ids:
                new_eval_id = f"{original_new_id}_v{counter}"
                counter += 1

            case["eval_id"] = new_eval_id
            all_eval_ids.add(new_eval_id)

            if old_id != new_eval_id:
                updates.append((evalset_file, old_id, new_eval_id))

        # Write back
        with open(evalset_file, "w") as f:
            json.dump(data, f, indent=2)

    # Print summary
    print("\n" + "=" * 80)
    print("UPDATES SUMMARY")
    print("=" * 80)

    for file, old, new in updates:
        rel_path = file.relative_to(base_path)
        print(f"✅ {rel_path}")
        print(f"   {old} → {new}")

    print(
        f"\n✅ Updated {len(evalset_files)} evalset files with {len(updates)} changes"
    )
    print(f"✅ All {len(all_eval_ids)} eval_ids are now unique")


if __name__ == "__main__":
    fix_all_eval_ids()

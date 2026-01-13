#!/usr/bin/env python3
"""Fix eval_id values in environment evalset files to be unique and descriptive."""

import json
from pathlib import Path

# Mapping of file patterns to new eval_ids
EVAL_ID_MAPPING = {
    "check_the_current_status_of_a_cyoda_environment": "env_check_status",
    "create_a_new_cyoda_environment_for_testing_purpose": "env_create_new",
    "deploy_my_python_java_application_to_a_specific_cy": "env_deploy_app",
    "describe_a_specific_cyoda_environment_and_see_what": "env_describe",
    "get_the_details_of_a_specific_application_deployed": "env_get_app_details",
    "get_the_logs_of_a_specific_application_deployed_in": "env_get_app_logs",
    "get_the_metrics_of_a_specific_application_deployed": "env_get_app_metrics",
    "get_the_pods_of_a_specific_application_deployed_in": "env_get_app_pods",
    "get_the_status_of_a_specific_application_deployed": "env_get_app_status",
    "list_all_the_applications_deployed_in_a_specific_c": "env_list_apps",
    "list_all_the_cyoda_environments_i_have_access_to": "env_list_all",
    "restart_a_specific_application_deployed_in_a_cyoda": "env_restart_app",
    "scale_a_specific_application_deployed_in_a_cyoda_e": "env_scale_app",
    "scale_a_specific_environment": "env_scale_env",
    "troubleshoot_an_application_deployed_in_a_cyoda_en": "env_troubleshoot_app",
}


def fix_eval_ids():
    """Update eval_ids in all environment evalset files."""
    base_path = Path(__file__).parent.parent.parent.parent.parent
    evals_dir = base_path / "application/agents/environment/evals"

    if not evals_dir.exists():
        print(f"❌ Directory not found: {evals_dir}")
        return

    updated_count = 0

    for evalset_file in sorted(evals_dir.glob("*.evalset.json")):
        # Find matching pattern in filename
        new_eval_id = None
        for pattern, eval_id in EVAL_ID_MAPPING.items():
            if pattern in evalset_file.name:
                new_eval_id = eval_id
                break

        if not new_eval_id:
            print(f"⚠️  No mapping found for: {evalset_file.name}")
            continue

        # Read the file
        with open(evalset_file, "r") as f:
            data = json.load(f)

        # Get old eval_id
        old_eval_id = None
        if data.get("eval_cases") and len(data["eval_cases"]) > 0:
            old_eval_id = data["eval_cases"][0].get("eval_id", "unknown")

        # Update eval_id in all test cases
        for case in data.get("eval_cases", []):
            case["eval_id"] = new_eval_id

        # Write back
        with open(evalset_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"✅ {evalset_file.name}")
        print(f"   {old_eval_id} → {new_eval_id}")
        updated_count += 1

    print(f"\n✅ Updated {updated_count} evalset files")


if __name__ == "__main__":
    fix_eval_ids()

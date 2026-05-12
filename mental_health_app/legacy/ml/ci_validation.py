"""CI/CD validation for model configuration, API contracts, and integration checks."""

import subprocess
import sys
from pathlib import Path
import os


def resolve_workspace_root() -> Path:
    """Resolve project root by walking up until model_config.yaml is found."""
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        if (parent / "model_config.yaml").exists():
            return parent
    raise FileNotFoundError("Could not locate workspace root containing model_config.yaml")


def run_test(name, command, description):
    """Run a test command and report results."""
    print(f"\n{'=' * 70}")
    print(f"TEST: {name}")
    print(f"{'=' * 70}")
    print(f"Description: {description}\n")

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

        if result.returncode == 0:
            print("PASS")
            if result.stdout:
                print("\nOutput (last 500 chars):")
                print(result.stdout[-500:])
            return True

        print("FAIL")
        print("\nError output:")
        print(result.stderr)
        return False

    except subprocess.TimeoutExpired:
        print("TIMEOUT - Test took too long")
        return False
    except Exception as exc:
        print(f"ERROR - {exc}")
        return False


def check_file_exists(path, description, base_path=None):
    """Check if a required file exists."""
    if base_path is None:
        base_path = Path(__file__).parent
    full_path = base_path / path
    if full_path.exists():
        print(f"PASS {description}: {path}")
        return True
    print(f"FAIL {description} NOT FOUND: {path} ({full_path})")
    return False


def main():
    print("\n" + "=" * 70)
    print("CI/CD VALIDATION: Mental Health App")
    print("=" * 70)

    results = {}
    workspace_root = resolve_workspace_root()

    # 1. Check file existence
    print("\n" + "=" * 70)
    print("STEP 1: File Existence Checks")
    print("=" * 70)

    files_to_check = [
        ("model_config.yaml", "Configuration file"),
        ("mental_health_app/ml/train_model.py", "Training script"),
        ("mental_health_app/ml/clinical_rules.py", "Safety gate service"),
        ("mental_health_app/ml/api_contracts.py", "API contracts (Pydantic schemas)"),
        ("mental_health_app/ml/test_api_contracts.py", "API contracts tests"),
        ("mental_health_app/ml/train_structured_support_model.py", "Structured model train wrapper"),
        ("mental_health_app/ml/eval_structured_support_model.py", "Structured model eval wrapper"),
        ("mental_health_app/ml/structured_support_model/train_pipeline.py", "Structured model train pipeline"),
        ("mental_health_app/ml/structured_support_model/eval_pipeline.py", "Structured model eval pipeline"),
        ("mental_health_app/ml/structured_support_model/inference_wrapper.py", "Structured model inference wrapper"),
        ("mental_health_app/ml/structured_support_model/feature_schema.json", "Structured model feature schema"),
        ("mental_health_app/ml/test_validation.py", "Validation tests"),
        ("mental_health_app/ml/integration_test.py", "Integration tests"),
        ("mental_health_app/lib/core/services/ml_service.dart", "Dart ML service"),
    ]

    results["files"] = all(
        check_file_exists(path, desc, workspace_root) for path, desc in files_to_check
    )

    # 2. Check configuration consistency
    print("\n" + "=" * 70)
    print("STEP 2: Configuration Validation")
    print("=" * 70)

    import yaml

    config_path = workspace_root / "model_config.yaml"
    with open(config_path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    checks = [
        (config["model"]["lookback_days"] == 14, "LOOKBACK_DAYS = 14"),
        (config["model"]["num_features"] == 4, "NUM_FEATURES = 4"),
        (config["model"]["num_classes"] == 6, "NUM_CLASSES = 6"),
        (len(config["emotions"]["map"]) == 6, "6 emotion classes defined"),
        (len(config["emotions"]["critical"]) == 2, "2 critical emotions"),
        ("clinical_rules" in config, "Safety-related config section present"),
    ]

    results["config"] = True
    for check, desc in checks:
        if check:
            print(f"PASS {desc}")
        else:
            print(f"FAIL {desc}")
            results["config"] = False

    # 3. Run unit tests
    print("\n" + "=" * 70)
    print("STEP 3: Unit Tests")
    print("=" * 70)

    results["validation_tests"] = run_test(
        "Input Validation Tests",
        "python test_validation.py",
        "Validates input tensor shape checking (14, 4) format",
    )

    results["clinical_tests"] = run_test(
        "Safety Gate Service Tests",
        "python clinical_rules.py",
        "Tests deterministic safety category matching and policy resolution",
    )

    results["api_contract_tests"] = run_test(
        "API Contract Tests",
        "python test_api_contracts.py",
        "Validates two API modes, PII filtering, no-text handling, and low-confidence policy",
    )

    results["structured_compile"] = run_test(
        "Structured Model Compile",
        "python -m py_compile structured_support_model\\train_pipeline.py structured_support_model\\eval_pipeline.py structured_support_model\\inference_wrapper.py",
        "Verifies structured baseline train/eval/inference modules compile",
    )

    # 4. Integration test
    print("\n" + "=" * 70)
    print("STEP 4: Integration Tests")
    print("=" * 70)

    results["integration"] = run_test(
        "End-to-End Integration",
        "python integration_test.py",
        "Tests safety gate conflict handling and policy outcomes",
    )

    # 5. Dart validation
    print("\n" + "=" * 70)
    print("STEP 5: Dart Code Validation")
    print("=" * 70)

    dart_service = workspace_root / "mental_health_app/lib/core/services/ml_service.dart"
    tries = [
        ("mlLookbackDays = 14", "const int mlLookbackDays = 14;"),
        ("mlNumFeatures = 4", "const int mlNumFeatures = 4;"),
        ("mlNumClasses = 6", "const int mlNumClasses = 6;"),
        ("_validateInterpreterShape()", "_validateInterpreterShape()"),
    ]

    dart_content = dart_service.read_text(encoding="utf-8")
    results["dart"] = True
    for check_name, expected in tries:
        if expected in dart_content:
            print(f"PASS Found: {check_name}")
        else:
            print(f"FAIL Missing: {check_name}")
            results["dart"] = False

    # 6. Summary
    print("\n" + "=" * 70)
    print("CI/CD VALIDATION SUMMARY")
    print("=" * 70)

    summary = [
        ("File Checks", results["files"]),
        ("Configuration Consistency", results["config"]),
        ("Validation Tests", results["validation_tests"]),
        ("Safety Gate Tests", results["clinical_tests"]),
        ("API Contract Tests", results["api_contract_tests"]),
        ("Structured Model Compile", results["structured_compile"]),
        ("Integration Tests", results["integration"]),
        ("Dart Code", results["dart"]),
    ]

    passed = sum(1 for _, result in summary if result)
    total = len(summary)

    print(f"\nResults: {passed}/{total} checks passed\n")

    for test_name, result in summary:
        status = "PASS" if result else "FAIL"
        print(f"  {test_name:<30} {status}")

    print("\n" + "=" * 70)
    if all(result for _, result in summary):
        print("ALL CI/CD CHECKS PASSED - Ready for deployment")
        print("=" * 70)
        return 0

    print("SOME CHECKS FAILED - Fix issues before deploying")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())

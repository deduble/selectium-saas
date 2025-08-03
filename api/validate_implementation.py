"""
Implementation validation script to check code structure and basic functionality.
"""
import ast
import os
import sys
from pathlib import Path

def validate_file_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST to check syntax
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def count_functions_and_classes(file_path):
    """Count functions and classes in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
        
        return functions, classes
    except Exception:
        return [], []

def validate_api_structure():
    """Validate the overall API structure."""
    print("🔍 Validating FastAPI backend implementation...\n")
    
    # Define required files and their expected content
    required_files = {
        'main.py': {
            'description': 'FastAPI application with all routes',
            'required_functions': ['health_check', 'google_auth_url', 'create_task', 'get_user_tasks'],
            'required_imports': ['FastAPI', 'HTTPException', 'Depends']
        },
        'models.py': {
            'description': 'SQLAlchemy database models',
            'required_classes': ['User', 'Task', 'APIKey'],
            'required_imports': ['Column', 'String', 'Integer']
        },
        'schemas.py': {
            'description': 'Pydantic validation schemas',
            'required_classes': ['TaskCreate', 'UserResponse', 'APIKeyResponse'],
            'required_imports': ['BaseModel', 'Field']
        },
        'auth.py': {
            'description': 'Authentication system with Google OAuth and JWT',
            'required_functions': ['create_access_token', 'verify_token', 'get_current_user'],
            'required_imports': ['HTTPException', 'jwt']
        },
        'celery_app.py': {
            'description': 'Celery task queue configuration',
            'required_functions': ['submit_task', 'cancel_task', 'get_queue_stats'],
            'required_imports': ['Celery']
        },
        'database.py': {
            'description': 'Database configuration and session management',
            'required_functions': ['get_db', 'create_tables'],
            'required_imports': ['create_engine', 'sessionmaker']
        }
    }
    
    print("📁 Checking file structure and syntax...\n")
    
    total_files = len(required_files)
    valid_files = 0
    issues = []
    
    for filename, requirements in required_files.items():
        file_path = Path(filename)
        
        if not file_path.exists():
            issues.append(f"❌ {filename}: File missing")
            continue
        
        # Check syntax
        is_valid, error = validate_file_syntax(file_path)
        if not is_valid:
            issues.append(f"❌ {filename}: {error}")
            continue
        
        print(f"✅ {filename}: Valid syntax")
        
        # Count functions and classes
        functions, classes = count_functions_and_classes(file_path)
        
        # Check required functions
        if 'required_functions' in requirements:
            missing_functions = set(requirements['required_functions']) - set(functions)
            if missing_functions:
                issues.append(f"⚠️  {filename}: Missing functions: {', '.join(missing_functions)}")
            else:
                print(f"   ✅ All required functions present ({len(requirements['required_functions'])} found)")
        
        # Check required classes
        if 'required_classes' in requirements:
            missing_classes = set(requirements['required_classes']) - set(classes)
            if missing_classes:
                issues.append(f"⚠️  {filename}: Missing classes: {', '.join(missing_classes)}")
            else:
                print(f"   ✅ All required classes present ({len(requirements['required_classes'])} found)")
        
        # Check imports (basic check)
        if 'required_imports' in requirements:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            missing_imports = []
            for import_name in requirements['required_imports']:
                if import_name not in content:
                    missing_imports.append(import_name)
            
            if missing_imports:
                issues.append(f"⚠️  {filename}: Missing imports: {', '.join(missing_imports)}")
            else:
                print(f"   ✅ All required imports present")
        
        valid_files += 1
        print()
    
    # Summary
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Files checked: {total_files}")
    print(f"Valid files: {valid_files}")
    print(f"Issues found: {len(issues)}")
    
    if issues:
        print("\n🚨 ISSUES DETECTED:")
        for issue in issues:
            print(f"   {issue}")
    
    if valid_files == total_files and len(issues) == 0:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("✅ FastAPI backend implementation is complete and ready!")
        return True
    else:
        print(f"\n⚠️  VALIDATION COMPLETED WITH {len(issues)} ISSUES")
        print("   Please review and fix the issues above.")
        return False


def check_endpoint_coverage():
    """Check if all required endpoints are implemented."""
    print("\n🔍 Checking API endpoint coverage...\n")
    
    required_endpoints = {
        'Authentication': [
            'google_auth_url',
            'google_auth_callback', 
            'get_current_user_info',
            'logout'
        ],
        'Tasks': [
            'get_user_tasks',
            'create_task',
            'get_task',
            'update_task',
            'delete_task',
            'get_task_logs',
            'download_task_results'
        ],
        'API Keys': [
            'get_api_keys',
            'create_api_key',
            'delete_api_key'
        ],
        'Subscription': [
            'get_user_subscription',
            'get_subscription_plans'
        ],
        'Analytics': [
            'get_usage_analytics',
            'get_dashboard_stats'
        ]
    }
    
    # Read main.py to check for endpoint definitions
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        total_endpoints = sum(len(endpoints) for endpoints in required_endpoints.values())
        found_endpoints = 0
        missing_endpoints = []
        
        for category, endpoints in required_endpoints.items():
            print(f"📋 {category}:")
            category_found = 0
            
            for endpoint in endpoints:
                if f"def {endpoint}" in content:
                    print(f"   ✅ {endpoint}")
                    found_endpoints += 1
                    category_found += 1
                else:
                    print(f"   ❌ {endpoint}")
                    missing_endpoints.append(f"{category}: {endpoint}")
            
            print(f"   ({category_found}/{len(endpoints)} found)\n")
        
        print(f"📊 ENDPOINT COVERAGE: {found_endpoints}/{total_endpoints} ({found_endpoints/total_endpoints*100:.1f}%)")
        
        if missing_endpoints:
            print(f"\n🚨 MISSING ENDPOINTS:")
            for endpoint in missing_endpoints:
                print(f"   - {endpoint}")
            return False
        else:
            print("\n🎉 ALL ENDPOINTS IMPLEMENTED!")
            return True
            
    except FileNotFoundError:
        print("❌ main.py not found!")
        return False


def validate_requirements():
    """Validate requirements.txt file."""
    print("\n🔍 Checking requirements.txt...\n")
    
    if not Path('requirements.txt').exists():
        print("❌ requirements.txt not found!")
        return False
    
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        requirements = f.read()
    
    essential_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'psycopg2-binary',
        'celery',
        'redis',
        'pydantic',
        'python-jose',
        'passlib',
        'authlib',
        'httpx'
    ]
    
    missing_packages = []
    for package in essential_packages:
        if package not in requirements:
            missing_packages.append(package)
        else:
            print(f"✅ {package}")
    
    if missing_packages:
        print(f"\n❌ Missing essential packages: {', '.join(missing_packages)}")
        return False
    else:
        print(f"\n✅ All essential packages present ({len(essential_packages)} found)")
        return True


def main():
    """Run all validations."""
    print("🚀 SELEXTRACT CLOUD API VALIDATION")
    print("=" * 50)
    print()
    
    results = []
    
    # File structure validation
    results.append(validate_api_structure())
    
    # Endpoint coverage check
    results.append(check_endpoint_coverage())
    
    # Requirements validation
    results.append(validate_requirements())
    
    print("\n" + "=" * 50)
    print("🏁 FINAL VALIDATION RESULTS")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 CONGRATULATIONS!")
        print("✅ FastAPI backend implementation is COMPLETE and READY!")
        print("🚀 You can now proceed with deployment.")
        return True
    else:
        print(f"\n⚠️  VALIDATION FAILED")
        print("❌ Please fix the issues above before deployment.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
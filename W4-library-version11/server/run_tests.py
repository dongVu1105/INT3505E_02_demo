#!/usr/bin/env python3
"""
Script helper để chạy tests với các options khác nhau
"""
import sys
import subprocess
import argparse


def run_command(cmd, description):
    """Chạy command và hiển thị kết quả"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='Run Library API Tests')
    parser.add_argument('--mode', '-m', 
                       choices=['all', 'unit', 'coverage', 'verbose', 'fast'],
                       default='all',
                       help='Test mode to run')
    parser.add_argument('--class', '-c', 
                       dest='test_class',
                       help='Run specific test class (e.g., TestAuthenticationEndpoints)')
    parser.add_argument('--method', '-t',
                       dest='test_method',
                       help='Run specific test method (e.g., test_login_success)')
    
    args = parser.parse_args()
    
    # Determine command based on mode
    if args.test_class and args.test_method:
        # Run specific test method
        cmd = f'python -m unittest test_api.{args.test_class}.{args.test_method}'
        description = f'Running {args.test_class}.{args.test_method}'
    elif args.test_class:
        # Run specific test class
        cmd = f'python -m unittest test_api.{args.test_class}'
        description = f'Running {args.test_class}'
    elif args.mode == 'all':
        # Run all tests with unittest
        cmd = 'python -m unittest test_api.py'
        description = 'Running all tests'
    elif args.mode == 'unit':
        # Run with pytest
        cmd = 'pytest test_api.py'
        description = 'Running tests with pytest'
    elif args.mode == 'coverage':
        # Run with coverage
        cmd = 'pytest test_api.py --cov=. --cov-report=html --cov-report=term'
        description = 'Running tests with coverage report'
    elif args.mode == 'verbose':
        # Run with verbose output
        cmd = 'python -m unittest test_api.py -v'
        description = 'Running tests (verbose mode)'
    elif args.mode == 'fast':
        # Run only fast tests (exclude slow tests if any)
        cmd = 'pytest test_api.py -v --tb=short'
        description = 'Running tests (fast mode)'
    
    # Run the tests
    success = run_command(cmd, description)
    
    # Print summary
    print(f"\n{'='*60}")
    if success:
        print("  ✅ Tests completed successfully!")
    else:
        print("  ❌ Tests failed!")
    print(f"{'='*60}\n")
    
    # Return appropriate exit code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

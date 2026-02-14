#!/bin/bash

###############################################################################
# Motion Play - Lambda Deployment Script
#
# Deploys one or more Lambda functions by name.
#
# Usage:
#   ./deploy.sh <function> [function ...]   Deploy specific functions
#   ./deploy.sh --all                       Deploy all functions
#   ./deploy.sh --list                      List available functions
#
# Examples:
#   ./deploy.sh sendCommand processData
#   ./deploy.sh --all
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Node.js and npm installed
#   - Lambda functions already created in AWS (use lambda-deployment-guide.md
#     for first-time setup)
#
# Run from the lambda/ directory:
#   cd lambda && ./deploy.sh sendCommand
###############################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}==>${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

# Configuration
REGION="us-west-2"
FUNCTION_PREFIX="motionplay"

# All known Lambda functions (directory names under lambda/)
ALL_FUNCTIONS=(
    processData
    processStatus
    sendCommand
    getSessions
    getSessionData
    updateSession
    deleteSession
    getDeviceConfig
    updateDeviceConfig
)

# Resolve script directory so it works from anywhere
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

###############################################################################
# Helpers
###############################################################################

usage() {
    echo "Usage: $0 <function> [function ...] | --all | --list"
    echo ""
    echo "Options:"
    echo "  --all     Deploy all Lambda functions"
    echo "  --list    List available function names"
    echo "  --help    Show this help"
    echo ""
    echo "Available functions:"
    for f in "${ALL_FUNCTIONS[@]}"; do
        echo "  $f"
    done
    exit 0
}

list_functions() {
    echo "Available Lambda functions:"
    for f in "${ALL_FUNCTIONS[@]}"; do
        if [ -d "$SCRIPT_DIR/$f" ]; then
            echo -e "  ${GREEN}$f${NC}"
        else
            echo -e "  ${RED}$f${NC} (directory missing)"
        fi
    done
    exit 0
}

deploy_function() {
    local func_name="$1"
    local func_dir="$SCRIPT_DIR/$func_name"
    local aws_name="${FUNCTION_PREFIX}-${func_name}"

    if [ ! -d "$func_dir" ]; then
        print_error "Directory not found: $func_dir"
        return 1
    fi

    if [ ! -f "$func_dir/index.js" ]; then
        print_error "No index.js found in $func_dir"
        return 1
    fi

    echo ""
    print_status "Deploying ${aws_name}..."

    # Install dependencies
    cd "$func_dir"
    if [ -f "package.json" ]; then
        npm install --silent 2>/dev/null
        print_success "Dependencies installed"
    fi

    # Create zip
    rm -f function.zip
    zip -q -r function.zip .
    local zip_size
    zip_size=$(du -h function.zip | cut -f1)
    print_success "Package created (${zip_size})"

    # Check if function exists in AWS, then create or update
    if aws lambda get-function --function-name "$aws_name" --region "$REGION" &>/dev/null; then
        aws lambda update-function-code \
            --function-name "$aws_name" \
            --zip-file fileb://function.zip \
            --region "$REGION" \
            >/dev/null
        print_success "${aws_name} updated"
    else
        print_warning "${aws_name} does not exist in AWS. Skipping."
        print_warning "Use infrastructure/lambda-deployment-guide.md for first-time creation."
        rm -f function.zip
        cd "$SCRIPT_DIR"
        return 1
    fi

    # Clean up
    rm -f function.zip
    cd "$SCRIPT_DIR"
}

###############################################################################
# Main
###############################################################################

if [ $# -eq 0 ]; then
    usage
fi

# Parse arguments
FUNCTIONS_TO_DEPLOY=()

for arg in "$@"; do
    case "$arg" in
        --all)
            FUNCTIONS_TO_DEPLOY=("${ALL_FUNCTIONS[@]}")
            ;;
        --list)
            list_functions
            ;;
        --help|-h)
            usage
            ;;
        *)
            # Validate function name
            valid=false
            for f in "${ALL_FUNCTIONS[@]}"; do
                if [ "$arg" = "$f" ]; then
                    valid=true
                    break
                fi
            done
            if [ "$valid" = true ]; then
                FUNCTIONS_TO_DEPLOY+=("$arg")
            else
                print_error "Unknown function: $arg"
                echo "Run '$0 --list' to see available functions."
                exit 1
            fi
            ;;
    esac
done

if [ ${#FUNCTIONS_TO_DEPLOY[@]} -eq 0 ]; then
    print_error "No functions to deploy."
    exit 1
fi

# Prerequisites check
if ! command -v aws &>/dev/null; then
    print_error "AWS CLI not found. Please install it first."
    exit 1
fi

if ! command -v npm &>/dev/null; then
    print_error "npm not found. Please install it first."
    exit 1
fi

# Verify AWS credentials
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
if [ -z "$ACCOUNT_ID" ]; then
    print_error "Failed to get AWS account ID. Check your AWS credentials."
    exit 1
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Motion Play Lambda Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Account:   ${ACCOUNT_ID}"
echo -e "  Region:    ${REGION}"
echo -e "  Functions: ${#FUNCTIONS_TO_DEPLOY[@]}"

# Deploy each function
SUCCEEDED=()
FAILED=()

for func in "${FUNCTIONS_TO_DEPLOY[@]}"; do
    if deploy_function "$func"; then
        SUCCEEDED+=("$func")
    else
        FAILED+=("$func")
    fi
done

# Summary
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Deployment Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ ${#SUCCEEDED[@]} -gt 0 ]; then
    echo -e "  ${GREEN}Deployed:${NC}"
    for f in "${SUCCEEDED[@]}"; do
        echo -e "    ${GREEN}✓${NC} ${FUNCTION_PREFIX}-${f}"
    done
fi

if [ ${#FAILED[@]} -gt 0 ]; then
    echo -e "  ${RED}Failed:${NC}"
    for f in "${FAILED[@]}"; do
        echo -e "    ${RED}✗${NC} ${FUNCTION_PREFIX}-${f}"
    done
fi

echo ""

if [ ${#FAILED[@]} -gt 0 ]; then
    exit 1
fi

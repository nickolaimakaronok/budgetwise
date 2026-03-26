#!/bin/bash
# build.sh — builds BudgetWise.app with clean environment (no conda conflict)

echo "🔨 Building BudgetWise.app..."

# Remove conda from PATH for this build only
export PATH="/Users/nickolaimakaronok/Documents/DevelopAndProgramming/budgetwise/.venv/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Force Python to use only venv packages
export PYTHONPATH="/Users/nickolaimakaronok/Documents/DevelopAndProgramming/budgetwise"
unset CONDA_DEFAULT_ENV
unset CONDA_PREFIX

# Run PyInstaller with clean env
.venv/bin/python3 -m PyInstaller --noconfirm --clean BudgetWise.spec

echo "✅ Done! Run: open dist/BudgetWise.app"
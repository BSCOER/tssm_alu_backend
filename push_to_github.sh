#!/bin/bash

# Script to push modular backend to GitHub
# This script helps commit and push the refactored code

echo "========================================="
echo "TSSM Alumni Backend - Push to GitHub"
echo "========================================="
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not a git repository"
    echo "Please run this script from the repository root"
    exit 1
fi

echo "📋 Current branch:"
git branch --show-current
echo ""

# Show status
echo "📊 Git status:"
git status --short
echo ""

# Ask for confirmation
read -p "Do you want to stage all changes? (y/n): " stage_all

if [ "$stage_all" = "y" ] || [ "$stage_all" = "Y" ]; then
    echo "📦 Staging all changes..."
    git add .
    echo "✅ Changes staged"
    echo ""
fi

# Show what will be committed
echo "📝 Files to be committed:"
git status --short
echo ""

# Ask for commit message
echo "💬 Enter commit message (or press Enter for default):"
read -p "Message: " commit_msg

if [ -z "$commit_msg" ]; then
    commit_msg="refactor: Convert monolithic backend to modular architecture

- Created config.py for centralized configuration
- Created extensions.py for Flask extensions
- Created database.py for MongoDB connection
- Created utils/ package for helper functions
- Created services/ package for business logic
- Created routes/ package for API blueprints
- Backed up original app.py as app_monolithic_backup.py
- Added comprehensive documentation

No logic changes - purely structural refactoring for maintainability"
fi

echo ""
echo "📝 Commit message:"
echo "$commit_msg"
echo ""

read -p "Proceed with commit? (y/n): " do_commit

if [ "$do_commit" = "y" ] || [ "$do_commit" = "Y" ]; then
    echo "💾 Committing changes..."
    git commit -m "$commit_msg"
    echo "✅ Changes committed"
    echo ""
    
    # Ask about pushing
    read -p "Push to remote? (y/n): " do_push
    
    if [ "$do_push" = "y" ] || [ "$do_push" = "Y" ]; then
        echo "🚀 Pushing to remote..."
        
        # Get current branch
        current_branch=$(git branch --show-current)
        
        # Push
        git push origin "$current_branch"
        
        if [ $? -eq 0 ]; then
            echo "✅ Successfully pushed to origin/$current_branch"
            echo ""
            echo "🎉 Done! Your modular backend is now on GitHub"
        else
            echo "❌ Push failed. Please check your connection and try again"
            exit 1
        fi
    else
        echo "⏸️  Skipped push. You can push later with:"
        echo "   git push origin $(git branch --show-current)"
    fi
else
    echo "⏸️  Commit cancelled"
    exit 0
fi

echo ""
echo "========================================="
echo "Next steps:"
echo "1. Complete route blueprint extraction"
echo "2. Create new app.py with application factory"
echo "3. Test all endpoints"
echo "4. Deploy to staging"
echo "========================================="

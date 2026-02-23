# PowerShell script to push modular backend to GitHub
# This script helps commit and push the refactored code

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "TSSM Alumni Backend - Push to GitHub" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in a git repository
if (-not (Test-Path ".git")) {
    Write-Host "❌ Error: Not a git repository" -ForegroundColor Red
    Write-Host "Please run this script from the repository root"
    exit 1
}

Write-Host "📋 Current branch:" -ForegroundColor Yellow
git branch --show-current
Write-Host ""

# Show status
Write-Host "📊 Git status:" -ForegroundColor Yellow
git status --short
Write-Host ""

# Ask for confirmation
$stageAll = Read-Host "Do you want to stage all changes? (y/n)"

if ($stageAll -eq "y" -or $stageAll -eq "Y") {
    Write-Host "📦 Staging all changes..." -ForegroundColor Yellow
    git add .
    Write-Host "✅ Changes staged" -ForegroundColor Green
    Write-Host ""
}

# Show what will be committed
Write-Host "📝 Files to be committed:" -ForegroundColor Yellow
git status --short
Write-Host ""

# Ask for commit message
Write-Host "💬 Enter commit message (or press Enter for default):" -ForegroundColor Yellow
$commitMsg = Read-Host "Message"

if ([string]::IsNullOrWhiteSpace($commitMsg)) {
    $commitMsg = @"
refactor: Convert monolithic backend to modular architecture

- Created config.py for centralized configuration
- Created extensions.py for Flask extensions
- Created database.py for MongoDB connection
- Created utils/ package for helper functions
- Created services/ package for business logic
- Created routes/ package for API blueprints
- Backed up original app.py as app_monolithic_backup.py
- Added comprehensive documentation

No logic changes - purely structural refactoring for maintainability
"@
}

Write-Host ""
Write-Host "📝 Commit message:" -ForegroundColor Yellow
Write-Host $commitMsg
Write-Host ""

$doCommit = Read-Host "Proceed with commit? (y/n)"

if ($doCommit -eq "y" -or $doCommit -eq "Y") {
    Write-Host "💾 Committing changes..." -ForegroundColor Yellow
    git commit -m $commitMsg
    Write-Host "✅ Changes committed" -ForegroundColor Green
    Write-Host ""
    
    # Ask about pushing
    $doPush = Read-Host "Push to remote? (y/n)"
    
    if ($doPush -eq "y" -or $doPush -eq "Y") {
        Write-Host "🚀 Pushing to remote..." -ForegroundColor Yellow
        
        # Get current branch
        $currentBranch = git branch --show-current
        
        # Push
        git push origin $currentBranch
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Successfully pushed to origin/$currentBranch" -ForegroundColor Green
            Write-Host ""
            Write-Host "🎉 Done! Your modular backend is now on GitHub" -ForegroundColor Green
        } else {
            Write-Host "❌ Push failed. Please check your connection and try again" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "⏸️  Skipped push. You can push later with:" -ForegroundColor Yellow
        Write-Host "   git push origin $(git branch --show-current)"
    }
} else {
    Write-Host "⏸️  Commit cancelled" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Next steps:"
Write-Host "1. Complete route blueprint extraction"
Write-Host "2. Create new app.py with application factory"
Write-Host "3. Test all endpoints"
Write-Host "4. Deploy to staging"
Write-Host "=========================================" -ForegroundColor Cyan

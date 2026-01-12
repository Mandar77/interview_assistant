<#
.SYNOPSIS
    Interview Assistant - Deployment Script for Windows
.DESCRIPTION
    Deploys the Interview Assistant to AWS using CDK
.PARAMETER Action
    The action to perform: deploy, destroy, synth, diff, status, upload-backend, upload-frontend
.EXAMPLE
    .\deploy.ps1 deploy
    .\deploy.ps1 upload-backend
    .\deploy.ps1 upload-frontend
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("deploy", "destroy", "synth", "diff", "status", "upload-backend", "upload-frontend", "bootstrap", "create-key", "ssh")]
    [string]$Action = "deploy"
)

$ErrorActionPreference = "Stop"
$AWS_PROFILE = "interview-assistant"
$AWS_REGION = "us-east-1"
$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $PROJECT_ROOT) { $PROJECT_ROOT = Get-Location }

# Colors for output
function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Cyan }
function Write-Success { Write-Host "[SUCCESS] $args" -ForegroundColor Green }
function Write-Warning { Write-Host "[WARNING] $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "[ERROR] $args" -ForegroundColor Red }

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check AWS CLI
    if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
        Write-Error "AWS CLI not found. Install from: https://aws.amazon.com/cli/"
        exit 1
    }
    
    # Check Node.js
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Error "Node.js not found. Install from: https://nodejs.org/"
        exit 1
    }
    
    # Check AWS profile
    $profiles = aws configure list-profiles
    if ($profiles -notcontains $AWS_PROFILE) {
        Write-Error "AWS profile '$AWS_PROFILE' not configured. Run: aws configure --profile $AWS_PROFILE"
        exit 1
    }
    
    Write-Success "All prerequisites met!"
}

# Bootstrap CDK (one-time setup)
function Invoke-Bootstrap {
    Write-Info "Bootstrapping CDK..."
    Set-Location "$PROJECT_ROOT\infra"
    
    # Install dependencies if needed
    if (-not (Test-Path "node_modules")) {
        Write-Info "Installing CDK dependencies..."
        npm install
    }
    
    $account = aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text
    npx cdk bootstrap "aws://${account}/${AWS_REGION}" --profile $AWS_PROFILE
    
    Write-Success "CDK bootstrap complete!"
}

# Create EC2 key pair
function New-EC2KeyPair {
    Write-Info "Creating EC2 key pair..."
    
    $keyName = "interview-assistant-key"
    $keyPath = "$PROJECT_ROOT\$keyName.pem"
    
    # Check if key already exists in AWS
    $existingKey = aws ec2 describe-key-pairs --key-names $keyName --profile $AWS_PROFILE --region $AWS_REGION 2>$null
    
    if ($existingKey) {
        Write-Warning "Key pair '$keyName' already exists in AWS."
        if (Test-Path $keyPath) {
            Write-Info "Local key file exists at: $keyPath"
        } else {
            Write-Warning "Local key file NOT found. You may need to delete the key in AWS and recreate."
            Write-Info "To delete: aws ec2 delete-key-pair --key-name $keyName --profile $AWS_PROFILE --region $AWS_REGION"
        }
        return
    }
    
    # Create new key pair
    Write-Info "Creating new key pair..."
    aws ec2 create-key-pair `
        --key-name $keyName `
        --query 'KeyMaterial' `
        --output text `
        --profile $AWS_PROFILE `
        --region $AWS_REGION > $keyPath
    
    Write-Success "Key pair created and saved to: $keyPath"
    Write-Warning "IMPORTANT: Keep this file safe! You cannot download it again."
}

# Deploy infrastructure
function Invoke-Deploy {
    Write-Info "Deploying Interview Assistant infrastructure..."
    Set-Location "$PROJECT_ROOT\infra"
    
    # Install dependencies if needed
    if (-not (Test-Path "node_modules")) {
        Write-Info "Installing CDK dependencies..."
        npm install
    }
    
    # Build TypeScript
    Write-Info "Building CDK stack..."
    npm run build
    
    # Deploy
    Write-Info "Deploying to AWS..."
    npx cdk deploy --all --profile $AWS_PROFILE --require-approval never
    
    Write-Success "Infrastructure deployment complete!"
    Write-Info "Run '.\deploy.ps1 status' to see deployment details"
}

# Get deployment status
function Get-DeploymentStatus {
    Write-Info "Fetching deployment status..."
    
    # Get CloudFormation outputs
    $outputs = aws cloudformation describe-stacks `
        --stack-name InterviewAssistantStack `
        --profile $AWS_PROFILE `
        --region $AWS_REGION `
        --query 'Stacks[0].Outputs' `
        --output json 2>$null | ConvertFrom-Json
    
    if (-not $outputs) {
        Write-Warning "Stack not deployed yet. Run '.\deploy.ps1 deploy' first."
        return
    }
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "   INTERVIEW ASSISTANT - DEPLOYMENT STATUS" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    foreach ($output in $outputs) {
        Write-Host "$($output.OutputKey): " -NoNewline -ForegroundColor Yellow
        Write-Host $output.OutputValue -ForegroundColor White
    }
    
    Write-Host "`n========================================`n" -ForegroundColor Cyan
}

# Upload backend to EC2
function Invoke-UploadBackend {
    Write-Info "Uploading backend to EC2..."
    
    # Get EC2 public IP
    $ip = aws cloudformation describe-stacks `
        --stack-name InterviewAssistantStack `
        --profile $AWS_PROFILE `
        --region $AWS_REGION `
        --query 'Stacks[0].Outputs[?OutputKey==`EC2PublicIP`].OutputValue' `
        --output text
    
    if (-not $ip) {
        Write-Error "Could not find EC2 IP. Deploy infrastructure first."
        exit 1
    }
    
    $keyPath = "$PROJECT_ROOT\interview-assistant-key.pem"
    if (-not (Test-Path $keyPath)) {
        Write-Error "Key file not found at: $keyPath"
        Write-Info "Run '.\deploy.ps1 create-key' to create a key pair"
        exit 1
    }
    
    Write-Info "EC2 IP: $ip"
    Write-Info "Uploading backend files..."
    
    # Use SCP to upload (requires OpenSSH)
    $backendPath = "$PROJECT_ROOT\backend"
    
    # Create remote directory
    ssh -i $keyPath -o StrictHostKeyChecking=no ec2-user@$ip "mkdir -p ~/interview-assistant/backend"
    
    # Upload files (exclude __pycache__, .venv, etc.)
    $excludes = @("__pycache__", ".venv", "*.pyc", ".git", "temp", "logs")
    $excludeArgs = $excludes | ForEach-Object { "--exclude=$_" }
    
    # Use rsync if available, otherwise scp
    if (Get-Command rsync -ErrorAction SilentlyContinue) {
        rsync -avz --progress $excludeArgs -e "ssh -i $keyPath -o StrictHostKeyChecking=no" "$backendPath/" "ec2-user@${ip}:~/interview-assistant/backend/"
    } else {
        # Fallback to scp (less efficient)
        scp -i $keyPath -o StrictHostKeyChecking=no -r "$backendPath\*" "ec2-user@${ip}:~/interview-assistant/backend/"
    }
    
    Write-Success "Backend uploaded!"
    
    # Install dependencies and restart service
    Write-Info "Installing dependencies on EC2..."
    ssh -i $keyPath -o StrictHostKeyChecking=no ec2-user@$ip @"
cd ~/interview-assistant/backend
pip3.11 install -r requirements.txt --user
python3.11 -m spacy download en_core_web_sm
sudo systemctl restart interview-assistant
"@
    
    Write-Success "Backend deployment complete!"
}

# Upload frontend to S3
function Invoke-UploadFrontend {
    Write-Info "Building and uploading frontend..."
    
    # Build frontend
    Set-Location "$PROJECT_ROOT\frontend"
    
    Write-Info "Installing frontend dependencies..."
    npm install
    
    # Get backend URL for environment
    $backendUrl = aws cloudformation describe-stacks `
        --stack-name InterviewAssistantStack `
        --profile $AWS_PROFILE `
        --region $AWS_REGION `
        --query 'Stacks[0].Outputs[?OutputKey==`BackendURL`].OutputValue' `
        --output text
    
    Write-Info "Backend URL: $backendUrl"
    
    # Create .env.production
    @"
VITE_API_BASE_URL=${backendUrl}/api
VITE_WS_BASE_URL=ws://$($backendUrl -replace 'http://', '')/ws
VITE_ENABLE_MEDIAPIPE=true
VITE_ENABLE_DEBUG_PANEL=false
"@ | Out-File -FilePath ".env.production" -Encoding utf8
    
    Write-Info "Building frontend..."
    npm run build
    
    # Get S3 bucket name
    $bucketName = aws cloudformation describe-stacks `
        --stack-name InterviewAssistantStack `
        --profile $AWS_PROFILE `
        --region $AWS_REGION `
        --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' `
        --output text
    
    Write-Info "Uploading to S3 bucket: $bucketName"
    
    # Upload to S3
    aws s3 sync ./dist "s3://$bucketName" `
        --profile $AWS_PROFILE `
        --delete `
        --cache-control "max-age=31536000,public" `
        --exclude "*.html" `
        --exclude "*.json"
    
    # Upload HTML with no-cache
    aws s3 sync ./dist "s3://$bucketName" `
        --profile $AWS_PROFILE `
        --cache-control "no-cache,no-store,must-revalidate" `
        --exclude "*" `
        --include "*.html" `
        --include "*.json"
    
    # Get CloudFront URL
    $frontendUrl = aws cloudformation describe-stacks `
        --stack-name InterviewAssistantStack `
        --profile $AWS_PROFILE `
        --region $AWS_REGION `
        --query 'Stacks[0].Outputs[?OutputKey==`FrontendURL`].OutputValue' `
        --output text
    
    Write-Success "Frontend deployed!"
    Write-Host "`nFrontend URL: $frontendUrl" -ForegroundColor Green
    
    # Invalidate CloudFront cache
    Write-Info "Invalidating CloudFront cache..."
    $distributionId = aws cloudfront list-distributions `
        --profile $AWS_PROFILE `
        --query "DistributionList.Items[?Origins.Items[?contains(DomainName, '$bucketName')]].Id" `
        --output text
    
    if ($distributionId) {
        aws cloudfront create-invalidation `
            --distribution-id $distributionId `
            --paths "/*" `
            --profile $AWS_PROFILE | Out-Null
        Write-Success "CloudFront cache invalidated!"
    }
}

# SSH into EC2
function Invoke-SSH {
    $ip = aws cloudformation describe-stacks `
        --stack-name InterviewAssistantStack `
        --profile $AWS_PROFILE `
        --region $AWS_REGION `
        --query 'Stacks[0].Outputs[?OutputKey==`EC2PublicIP`].OutputValue' `
        --output text
    
    if (-not $ip) {
        Write-Error "Could not find EC2 IP. Deploy infrastructure first."
        exit 1
    }
    
    $keyPath = "$PROJECT_ROOT\interview-assistant-key.pem"
    Write-Info "Connecting to EC2 at $ip..."
    ssh -i $keyPath -o StrictHostKeyChecking=no ec2-user@$ip
}

# Synthesize CloudFormation template
function Invoke-Synth {
    Write-Info "Synthesizing CloudFormation template..."
    Set-Location "$PROJECT_ROOT\infra"
    npm run build
    npx cdk synth --profile $AWS_PROFILE
}

# Show diff
function Invoke-Diff {
    Write-Info "Showing infrastructure diff..."
    Set-Location "$PROJECT_ROOT\infra"
    npm run build
    npx cdk diff --profile $AWS_PROFILE
}

# Destroy infrastructure
function Invoke-Destroy {
    Write-Warning "This will DESTROY all infrastructure!"
    $confirm = Read-Host "Type 'yes' to confirm"
    
    if ($confirm -ne "yes") {
        Write-Info "Aborted."
        return
    }
    
    Set-Location "$PROJECT_ROOT\infra"
    npx cdk destroy --all --profile $AWS_PROFILE --force
    
    Write-Success "Infrastructure destroyed!"
}

# Main execution
try {
    Test-Prerequisites
    
    switch ($Action) {
        "deploy"         { Invoke-Deploy }
        "destroy"        { Invoke-Destroy }
        "synth"          { Invoke-Synth }
        "diff"           { Invoke-Diff }
        "status"         { Get-DeploymentStatus }
        "upload-backend" { Invoke-UploadBackend }
        "upload-frontend"{ Invoke-UploadFrontend }
        "bootstrap"      { Invoke-Bootstrap }
        "create-key"     { New-EC2KeyPair }
        "ssh"            { Invoke-SSH }
    }
} catch {
    Write-Error $_.Exception.Message
    exit 1
} finally {
    Set-Location $PROJECT_ROOT
}
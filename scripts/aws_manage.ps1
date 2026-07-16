# AWS EC2 Instance Management Script
# Usage:
#   .\aws_manage.ps1 start    # Start instance
#   .\aws_manage.ps1 stop     # Stop instance
#   .\aws_manage.ps1 status   # Check status
#   .\aws_manage.ps1 ip       # Get current public IP

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "status", "ip")]
    [string]$Action
)

# CHANGE THIS to your instance ID
$INSTANCE_ID = "i-YOUR_INSTANCE_ID_HERE"
$REGION = "ap-south-1"  # Mumbai (change if different)

function Get-InstanceState {
    $state = aws ec2 describe-instances `
        --instance-ids $INSTANCE_ID `
        --region $REGION `
        --query "Reservations[].Instances[].State.Name" `
        --output text
    return $state
}

function Get-InstanceIP {
    $ip = aws ec2 describe-instances `
        --instance-ids $INSTANCE_ID `
        --region $REGION `
        --query "Reservations[].Instances[].PublicIpAddress" `
        --output text
    return $ip
}

switch ($Action) {
    "start" {
        Write-Host "Starting instance $INSTANCE_ID..." -ForegroundColor Cyan
        aws ec2 start-instances --instance-ids $INSTANCE_ID --region $REGION | Out-Null
        
        Write-Host "Waiting for instance to be running..." -ForegroundColor Yellow
        aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
        
        $ip = Get-InstanceIP
        Write-Host "Instance running!" -ForegroundColor Green
        Write-Host "Public IP: $ip" -ForegroundColor Green
        Write-Host "URL: http://$ip" -ForegroundColor Green
    }
    "stop" {
        Write-Host "Stopping instance $INSTANCE_ID..." -ForegroundColor Cyan
        aws ec2 stop-instances --instance-ids $INSTANCE_ID --region $REGION | Out-Null
        
        Write-Host "Waiting for instance to stop..." -ForegroundColor Yellow
        aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID --region $REGION
        
        Write-Host "Instance stopped! (Saving ~$1/day)" -ForegroundColor Green
    }
    "status" {
        $state = Get-InstanceState
        $ip = Get-InstanceIP
        Write-Host "Instance ID: $INSTANCE_ID"
        Write-Host "State: $state"
        Write-Host "IP: $ip"
    }
    "ip" {
        $ip = Get-InstanceIP
        Write-Host $ip
    }
}

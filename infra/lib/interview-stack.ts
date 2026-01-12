/**
 * Interview Assistant - EC2 Deployment Stack
 * Location: infra/lib/interview-stack.ts
 * 
 * Deploys:
 * - EC2 t2.micro instance with Docker, Ollama, FastAPI
 * - S3 bucket for frontend hosting
 * - CloudFront distribution
 * - Security groups and IAM roles
 */

import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import { Construct } from 'constructs';

export class InterviewAssistantStack extends cdk.Stack {
  public readonly backendUrl: cdk.CfnOutput;
  public readonly frontendUrl: cdk.CfnOutput;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ============================================
    // VPC - Use default VPC (free tier friendly)
    // ============================================
    const vpc = ec2.Vpc.fromLookup(this, 'DefaultVPC', {
      isDefault: true,
    });

    // ============================================
    // Security Group for EC2
    // ============================================
    const backendSG = new ec2.SecurityGroup(this, 'BackendSG', {
      vpc,
      description: 'Security group for Interview Assistant backend',
      allowAllOutbound: true,
    });

    // Allow HTTP
    backendSG.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      'Allow HTTP'
    );

    // Allow HTTPS
    backendSG.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'Allow HTTPS'
    );

    // Allow SSH (restrict to your IP in production)
    backendSG.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(22),
      'Allow SSH'
    );

    // Allow FastAPI port
    backendSG.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(8000),
      'Allow FastAPI'
    );

    // ============================================
    // IAM Role for EC2
    // ============================================
    const ec2Role = new iam.Role(this, 'EC2Role', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      description: 'Role for Interview Assistant EC2 instance',
    });

    ec2Role.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore')
    );

    ec2Role.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy')
    );

    // ============================================
    // EC2 User Data Script
    // ============================================
    const userDataScript = ec2.UserData.forLinux();
    userDataScript.addCommands(
      '#!/bin/bash',
      'set -e',
      'exec > >(tee /var/log/user-data.log) 2>&1',
      '',
      '# Update system',
      'yum update -y',
      '',
      '# Install Docker',
      'yum install -y docker git',
      'systemctl start docker',
      'systemctl enable docker',
      'usermod -aG docker ec2-user',
      '',
      '# Install Docker Compose',
      'curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose',
      'chmod +x /usr/local/bin/docker-compose',
      '',
      '# Install Python 3.11',
      'yum install -y python3.11 python3.11-pip',
      '',
      '# Create app directory',
      'mkdir -p /home/ec2-user/interview-assistant',
      'chown -R ec2-user:ec2-user /home/ec2-user/interview-assistant',
      '',
      '# Install Ollama',
      'curl -fsSL https://ollama.com/install.sh | sh',
      'systemctl enable ollama',
      'systemctl start ollama',
      '',
      '# Wait for Ollama to start',
      'sleep 10',
      '',
      '# Pull lightweight model for t2.micro',
      'ollama pull tinyllama',
      '',
      '# Install nginx',
      'yum install -y nginx',
      '',
      '# Configure nginx',
      'cat > /etc/nginx/conf.d/interview-assistant.conf << \'NGINXEOF\'',
      'server {',
      '    listen 80;',
      '    server_name _;',
      '',
      '    location /api/ {',
      '        proxy_pass http://127.0.0.1:8000/;',
      '        proxy_http_version 1.1;',
      '        proxy_set_header Upgrade $http_upgrade;',
      '        proxy_set_header Connection "upgrade";',
      '        proxy_set_header Host $host;',
      '        proxy_set_header X-Real-IP $remote_addr;',
      '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;',
      '        proxy_read_timeout 300s;',
      '    }',
      '',
      '    location /ws/ {',
      '        proxy_pass http://127.0.0.1:8000/ws/;',
      '        proxy_http_version 1.1;',
      '        proxy_set_header Upgrade $http_upgrade;',
      '        proxy_set_header Connection "upgrade";',
      '        proxy_set_header Host $host;',
      '        proxy_read_timeout 86400;',
      '    }',
      '',
      '    location /health {',
      '        proxy_pass http://127.0.0.1:8000/health;',
      '    }',
      '}',
      'NGINXEOF',
      '',
      'rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true',
      'systemctl start nginx',
      'systemctl enable nginx',
      '',
      '# Create systemd service for backend',
      'cat > /etc/systemd/system/interview-assistant.service << \'SERVICEEOF\'',
      '[Unit]',
      'Description=Interview Assistant Backend',
      'After=network.target',
      '',
      '[Service]',
      'Type=simple',
      'User=ec2-user',
      'WorkingDirectory=/home/ec2-user/interview-assistant/backend',
      'ExecStart=/usr/bin/python3.11 -m uvicorn app:app --host 0.0.0.0 --port 8000',
      'Restart=always',
      'RestartSec=10',
      'Environment=PYTHONUNBUFFERED=1',
      'Environment=OLLAMA_HOST=http://localhost:11434',
      'Environment=OLLAMA_MODEL=tinyllama',
      '',
      '[Install]',
      'WantedBy=multi-user.target',
      'SERVICEEOF',
      '',
      'systemctl daemon-reload',
      '',
      '# Create init complete marker',
      'echo "EC2 initialization complete!" > /home/ec2-user/init-complete.txt',
      'chown ec2-user:ec2-user /home/ec2-user/init-complete.txt',
    );

    // ============================================
    // EC2 Instance
    // ============================================
    const instance = new ec2.Instance(this, 'BackendInstance', {
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      // Using t3.micro - also free tier eligible and better performance than t2.micro
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T3,
        ec2.InstanceSize.MICRO
      ),
      machineImage: ec2.MachineImage.latestAmazonLinux2023(),
      securityGroup: backendSG,
      role: ec2Role,
      userData: userDataScript,
      keyName: 'interview-assistant-key',
      blockDevices: [
        {
          deviceName: '/dev/xvda',
          volume: ec2.BlockDeviceVolume.ebs(20, {
            volumeType: ec2.EbsDeviceVolumeType.GP3,
            encrypted: true,
          }),
        },
      ],
    });

    cdk.Tags.of(instance).add('Name', 'interview-assistant-backend');

    // ============================================
    // Elastic IP
    // ============================================
    const eip = new ec2.CfnEIP(this, 'BackendEIP', {
      instanceId: instance.instanceId,
      tags: [{ key: 'Name', value: 'interview-assistant-eip' }],
    });

    // ============================================
    // S3 Bucket for Frontend
    // ============================================
    const frontendBucket = new s3.Bucket(this, 'FrontendBucket', {
      bucketName: `interview-assistant-frontend-${this.account}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // ============================================
    // CloudFront Distribution
    // ============================================
    const distribution = new cloudfront.Distribution(this, 'FrontendDistribution', {
      defaultBehavior: {
        origin: new origins.S3Origin(frontendBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: 'index.html',
      errorResponses: [
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.minutes(5),
        },
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.minutes(5),
        },
      ],
    });

    // ============================================
    // Outputs
    // ============================================
    new cdk.CfnOutput(this, 'BackendURL', {
      value: `http://${eip.attrPublicIp}`,
      description: 'Backend API URL',
      exportName: 'InterviewAssistantBackendURL',
    });

    new cdk.CfnOutput(this, 'FrontendURL', {
      value: `https://${distribution.distributionDomainName}`,
      description: 'Frontend URL (CloudFront)',
      exportName: 'InterviewAssistantFrontendURL',
    });

    new cdk.CfnOutput(this, 'EC2InstanceId', {
      value: instance.instanceId,
      description: 'EC2 Instance ID',
    });

    new cdk.CfnOutput(this, 'EC2PublicIP', {
      value: eip.attrPublicIp,
      description: 'EC2 Public IP',
    });

    new cdk.CfnOutput(this, 'S3BucketName', {
      value: frontendBucket.bucketName,
      description: 'Frontend S3 Bucket',
    });

    new cdk.CfnOutput(this, 'SSHCommand', {
      value: `ssh -i interview-assistant-key.pem ec2-user@${eip.attrPublicIp}`,
      description: 'SSH command',
    });
  }
}
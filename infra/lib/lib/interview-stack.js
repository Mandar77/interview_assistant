"use strict";
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
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.InterviewAssistantStack = void 0;
const cdk = __importStar(require("aws-cdk-lib"));
const ec2 = __importStar(require("aws-cdk-lib/aws-ec2"));
const iam = __importStar(require("aws-cdk-lib/aws-iam"));
const s3 = __importStar(require("aws-cdk-lib/aws-s3"));
const cloudfront = __importStar(require("aws-cdk-lib/aws-cloudfront"));
const origins = __importStar(require("aws-cdk-lib/aws-cloudfront-origins"));
class InterviewAssistantStack extends cdk.Stack {
    constructor(scope, id, props) {
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
        backendSG.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'Allow HTTP');
        // Allow HTTPS
        backendSG.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), 'Allow HTTPS');
        // Allow SSH (restrict to your IP in production)
        backendSG.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(22), 'Allow SSH');
        // Allow FastAPI port
        backendSG.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(8000), 'Allow FastAPI');
        // ============================================
        // IAM Role for EC2
        // ============================================
        const ec2Role = new iam.Role(this, 'EC2Role', {
            assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
            description: 'Role for Interview Assistant EC2 instance',
        });
        ec2Role.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'));
        ec2Role.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'));
        // ============================================
        // EC2 User Data Script
        // ============================================
        const userDataScript = ec2.UserData.forLinux();
        userDataScript.addCommands('#!/bin/bash', 'set -e', 'exec > >(tee /var/log/user-data.log) 2>&1', '', '# Update system', 'yum update -y', '', '# Install Docker', 'yum install -y docker git', 'systemctl start docker', 'systemctl enable docker', 'usermod -aG docker ec2-user', '', '# Install Docker Compose', 'curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose', 'chmod +x /usr/local/bin/docker-compose', '', '# Install Python 3.11', 'yum install -y python3.11 python3.11-pip', '', '# Create app directory', 'mkdir -p /home/ec2-user/interview-assistant', 'chown -R ec2-user:ec2-user /home/ec2-user/interview-assistant', '', '# Install Ollama', 'curl -fsSL https://ollama.com/install.sh | sh', 'systemctl enable ollama', 'systemctl start ollama', '', '# Wait for Ollama to start', 'sleep 10', '', '# Pull lightweight model for t2.micro', 'ollama pull tinyllama', '', '# Install nginx', 'yum install -y nginx', '', '# Configure nginx', 'cat > /etc/nginx/conf.d/interview-assistant.conf << \'NGINXEOF\'', 'server {', '    listen 80;', '    server_name _;', '', '    location /api/ {', '        proxy_pass http://127.0.0.1:8000/;', '        proxy_http_version 1.1;', '        proxy_set_header Upgrade $http_upgrade;', '        proxy_set_header Connection "upgrade";', '        proxy_set_header Host $host;', '        proxy_set_header X-Real-IP $remote_addr;', '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;', '        proxy_read_timeout 300s;', '    }', '', '    location /ws/ {', '        proxy_pass http://127.0.0.1:8000/ws/;', '        proxy_http_version 1.1;', '        proxy_set_header Upgrade $http_upgrade;', '        proxy_set_header Connection "upgrade";', '        proxy_set_header Host $host;', '        proxy_read_timeout 86400;', '    }', '', '    location /health {', '        proxy_pass http://127.0.0.1:8000/health;', '    }', '}', 'NGINXEOF', '', 'rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true', 'systemctl start nginx', 'systemctl enable nginx', '', '# Create systemd service for backend', 'cat > /etc/systemd/system/interview-assistant.service << \'SERVICEEOF\'', '[Unit]', 'Description=Interview Assistant Backend', 'After=network.target', '', '[Service]', 'Type=simple', 'User=ec2-user', 'WorkingDirectory=/home/ec2-user/interview-assistant/backend', 'ExecStart=/usr/bin/python3.11 -m uvicorn app:app --host 0.0.0.0 --port 8000', 'Restart=always', 'RestartSec=10', 'Environment=PYTHONUNBUFFERED=1', 'Environment=OLLAMA_HOST=http://localhost:11434', 'Environment=OLLAMA_MODEL=tinyllama', '', '[Install]', 'WantedBy=multi-user.target', 'SERVICEEOF', '', 'systemctl daemon-reload', '', '# Create init complete marker', 'echo "EC2 initialization complete!" > /home/ec2-user/init-complete.txt', 'chown ec2-user:ec2-user /home/ec2-user/init-complete.txt');
        // ============================================
        // EC2 Instance
        // ============================================
        const instance = new ec2.Instance(this, 'BackendInstance', {
            vpc,
            vpcSubnets: {
                subnetType: ec2.SubnetType.PUBLIC,
            },
            // Using t3.micro - also free tier eligible and better performance than t2.micro
            instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
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
exports.InterviewAssistantStack = InterviewAssistantStack;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiaW50ZXJ2aWV3LXN0YWNrLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vaW50ZXJ2aWV3LXN0YWNrLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7QUFBQTs7Ozs7Ozs7O0dBU0c7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7OztBQUVILGlEQUFtQztBQUNuQyx5REFBMkM7QUFDM0MseURBQTJDO0FBQzNDLHVEQUF5QztBQUN6Qyx1RUFBeUQ7QUFDekQsNEVBQThEO0FBRzlELE1BQWEsdUJBQXdCLFNBQVEsR0FBRyxDQUFDLEtBQUs7SUFJcEQsWUFBWSxLQUFnQixFQUFFLEVBQVUsRUFBRSxLQUFzQjtRQUM5RCxLQUFLLENBQUMsS0FBSyxFQUFFLEVBQUUsRUFBRSxLQUFLLENBQUMsQ0FBQztRQUV4QiwrQ0FBK0M7UUFDL0MsNkNBQTZDO1FBQzdDLCtDQUErQztRQUMvQyxNQUFNLEdBQUcsR0FBRyxHQUFHLENBQUMsR0FBRyxDQUFDLFVBQVUsQ0FBQyxJQUFJLEVBQUUsWUFBWSxFQUFFO1lBQ2pELFNBQVMsRUFBRSxJQUFJO1NBQ2hCLENBQUMsQ0FBQztRQUVILCtDQUErQztRQUMvQyx5QkFBeUI7UUFDekIsK0NBQStDO1FBQy9DLE1BQU0sU0FBUyxHQUFHLElBQUksR0FBRyxDQUFDLGFBQWEsQ0FBQyxJQUFJLEVBQUUsV0FBVyxFQUFFO1lBQ3pELEdBQUc7WUFDSCxXQUFXLEVBQUUsZ0RBQWdEO1lBQzdELGdCQUFnQixFQUFFLElBQUk7U0FDdkIsQ0FBQyxDQUFDO1FBRUgsYUFBYTtRQUNiLFNBQVMsQ0FBQyxjQUFjLENBQ3RCLEdBQUcsQ0FBQyxJQUFJLENBQUMsT0FBTyxFQUFFLEVBQ2xCLEdBQUcsQ0FBQyxJQUFJLENBQUMsR0FBRyxDQUFDLEVBQUUsQ0FBQyxFQUNoQixZQUFZLENBQ2IsQ0FBQztRQUVGLGNBQWM7UUFDZCxTQUFTLENBQUMsY0FBYyxDQUN0QixHQUFHLENBQUMsSUFBSSxDQUFDLE9BQU8sRUFBRSxFQUNs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QUFVO1lBQ2hDLFdBQVcsRUFBRSxvQkFBb0I7U0FDbEMsQ0FBQyxDQUFDO1FBRUgsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxZQUFZLEVBQUU7WUFDcEMsS0FBSyxFQUFFLCtDQUErQyxHQUFHLENBQUMsWUFBWSxFQUFFO1lBQ3hFLFdBQVcsRUFBRSxhQUFhO1NBQzNCLENBQUMsQ0FBQztJQUNMLENBQUM7Q0FDRjtBQTVSRCwwREE0UkMiLCJzb3VyY2VzQ29udGVudCI6WyIvKipcclxuICogSW50ZXJ2aWV3IEFzc2lzdGFudCAtIEVDMiBEZXBsb3ltZW50IFN0YWNrXHJcbiAqIExvY2F0aW9uOiBpbmZyYS9saWIvaW50ZXJ2aWV3LXN0YWNrLnRzXHJcbiAqIFxyXG4gKiBEZXBsb3lzOlxyXG4gKiAtIEVDMiB0Mi5taWNybyBpbnN0YW5jZSB3aXRoIERvY2tlciwgT2xsYW1hLCBGYXN0QVBJXHJcbiAqIC0gUzMgYnVja2V0IGZvciBmcm9udGVuZCBob3N0aW5nXHJcbiAqIC0gQ2xvdWRGcm9udCBkaXN0cmlidXRpb25cclxuICogLSBTZWN1cml0eSBncm91cHMgYW5kIElBTSByb2xlc1xyXG4gKi9cclxuXHJcbmltcG9ydCAqIGFzIGNkayBmcm9tICdhd3MtY2RrLWxpYic7XHJcbmltcG9ydCAqIGFzIGVjMiBmcm9tICdhd3MtY2RrLWxpYi9hd3MtZWMyJztcclxuaW1wb3J0ICogYXMgaWFtIGZyb20gJ2F3cy1jZGstbGliL2F3cy1pYW0nO1xyXG5pbXBvcnQgKiBhcyBzMyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtczMnO1xyXG5pbXBvcnQgKiBhcyBjbG91ZGZyb250IGZyb20gJ2F3cy1jZGstbGliL2F3cy1jbG91ZGZyb250JztcclxuaW1wb3J0ICogYXMgb3JpZ2lucyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtY2xvdWRmcm9udC1vcmlnaW5zJztcclxuaW1wb3J0IHsgQ29uc3RydWN0IH0gZnJvbSAnY29uc3RydWN0cyc7XHJcblxyXG5leHBvcnQgY2xhc3MgSW50ZXJ2aWV3QXNzaXN0YW50U3RhY2sgZXh0ZW5kcyBjZGsuU3RhY2sge1xyXG4gIHB1YmxpYyByZWFkb25seSBiYWNrZW5kVXJsOiBjZGsuQ2ZuT3V0cHV0O1xyXG4gIHB1YmxpYyByZWFkb25seSBmcm9udGVuZFVybDogY2RrLkNmbk91dHB1dDtcclxuXHJcbiAgY29uc3RydWN0b3Ioc2NvcGU6IENvbnN0cnVjdCwgaWQ6IHN0cmluZywgcHJvcHM/OiBjZGsuU3RhY2tQcm9wcykge1xyXG4gICAgc3VwZXIoc2NvcGUsIGlkLCBwcm9wcyk7XHJcblxyXG4gICAgLy8gPT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT1cclxuICAgIC8vIFZQQyAtIFVzZSBkZWZhdWx0IFZQQyAoZnJlZSB0aWVyIGZyaWVuZGx5KVxyXG4gICAgLy8gPT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT1cclxuICAgIGNvbnN0IHZwYyA9IGVjMi5WcGMuZnJvbUxvb2t1cCh0aGlzLCAnRGVmYXVsdFZQQycsIHtcclxuICAgICAgaXNEZWZhdWx0OiB0cnVlLFxyXG4gICAgfSk7XHJcblxyXG4gICAgLy8gPT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT1cclxuICAgIC8vIFNlY3VyaXR5IEdyb3VwIGZvciBFQzJcclxuICAgIC8vID09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09XHJcbiAgICBjb25zdCBiYWNrZW5kU0cgPSBuZXcgZWMyLlNlY3VyaXR5R3JvdXAodGhpcywgJ0JhY2tlbmRTRycsIHtcclxuICAgICAgdnBjLFxyXG4gICAgICBkZXNjcmlwdGlvbjogJ1NlY3VyaXR5IGdyb3VwIGZvciBJbnRlcnZpZXcgQXNzaXN0YW50IGJhY2tlbmQnLFxyXG4gICAgICBhbGxvd0FsbE91dGJvdW5kOiB0cnVlLFxyXG4gICAgfSk7XHJcblxyXG4gICAgLy8gQWxsb3cgSFRUUFxyXG4gICAgYmFja2VuZFNHLmFkZEluZ3Jlc3NSdWxlKFxyXG4gICAgICBlYzIuUGVlci5hbnlJcHY0KCksXHJcbiAgICAgIGVjMi5Qb3J0LnRjcCg4MCksXHJcbiAgICAgICdBbGxvdyBIVFRQJ1xyXG4gICAgKTtcclxuXHJcbiAgICAvLyBBbGxvdyBIVFRQU1xyXG4gICAgYmFja2VuZFNHLmFkZEluZ3Jlc3NSdWxlKFxyXG4gICAgICBlYzIuUGVlci5hbnlJcHY0KCksXHJcbiAgICAgIGVjMi5Qb3J0LnRjcCg0NDMpLFxyXG4gICAgICAnQWxsb3cgSFRUUFMnXHJcbiAgICApO1xyXG5cclxuICAgIC8vIEFsbG93IFNTSCAocmVzdHJpY3QgdG8geW91ciBJUCBpbiBwcm9kdWN0aW9uKVxyXG4gICAgYmFja2VuZFNHLmFkZEluZ3Jlc3NSdWxlKFxyXG4gICAgICBlYzIuUGVlci5hbnlJcHY0KCksXHJcbiAgICAgIGVjMi5Qb3J0LnRjcCgyMiksXHJcbiAgICAgICdBbGxvdyBTU0gnXHJcbiAgICApO1xyXG5cclxuICAgIC8vIEFsbG93IEZhc3RBUEkgcG9ydFxyXG4gICAgYmFja2VuZFNHLmFkZEluZ3Jlc3NSdWxlKFxyXG4gICAgICBlYzIuUGVlci5hbnlJcHY0KCksXHJcbiAgICAgIGVjMi5Qb3J0LnRjcCg4MDAwKSxcclxuICAgICAgJ0FsbG93IEZhc3RBUEknXHJcbiAgICApO1xyXG5cclxuICAgIC8vID09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09XHJcbiAgICAvLyBJQU0gUm9sZSBmb3IgRUMyXHJcbiAgICAvLyA9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PVxyXG4gICAgY29uc3QgZWMyUm9sZSA9IG5ldyBpYW0uUm9sZSh0aGlzLCAnRUMyUm9sZScsIHtcclxuICAgICAgYXNzdW1lZEJ5OiBuZXcgaWFtLlNlcnZpY2VQcmluY2lwYWwoJ2VjMi5hbWF6b25hd3MuY29tJyksXHJcbiAgICAgIGRlc2NyaXB0aW9uOiAnUm9sZSBmb3IgSW50ZXJ2aWV3IEFzc2lzdGFudCBFQzIgaW5zdGFuY2UnLFxyXG4gICAgfSk7XHJcblxyXG4gICAgZWMyUm9sZS5hZGRNYW5hZ2VkUG9saWN5KFxyXG4gICAgICBpYW0uTWFuYWdlZFBvbGljeS5mcm9tQXdzTWFuYWdlZFBvbGljeU5hbWUoJ0FtYXpvblNTTU1hbmFnZWRJbnN0YW5jZUNvcmUnKVxyXG4gICAgKTtcclxuXHJcbiAgICBlYzJSb2xlLmFkZE1hbmFnZWRQb2xpY3koXHJcbiAgICAgIGlhbS5NYW5hZ2VkUG9saWN5LmZyb21Bd3NNYW5hZ2VkUG9saWN5TmFtZSgnQ2xvdWRXYXRjaEFnZW50U2VydmVyUG9saWN5JylcclxuICAgICk7XHJcblxyXG4gICAgLy8gPT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT1cclxuICAgIC8vIEVDMiBVc2VyIERhdGEgU2NyaXB0XHJcbiAgICAvLyA9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PVxyXG4gICAgY29uc3QgdXNlckRhdGFTY3JpcHQgPSBlYzIuVXNlckRhdGEuZm9yTGludXgoKTtcclxuICAgIHVzZXJEYXRhU2NyaXB0LmFkZENvbW1hbmRzKFxyXG4gICAgICAnIyEvYmluL2Jhc2gnLFxyXG4gICAgICAnc2V0IC1lJyxcclxuICAgICAgJ2V4ZWMgPiA+KHRlZSAvdmFyL2xvZy91c2VyLWRhdGEubG9nKSAyPiYxJyxcclxuICAgICAgJycsXHJcbiAgICAgICcjIFVwZGF0ZSBzeXN0ZW0nLFxyXG4gICAgICAneXVtIHVwZGF0ZSAteScsXHJcbiAgICAgICcnLFxyXG4gICAgICAnIyBJbnN0YWxsIERvY2tlcicsXHJcbiAgICAgICd5dW0gaW5zdGFsbCAteSBkb2NrZXIgZ2l0JyxcclxuICAgICAgJ3N5c3RlbWN0bCBzdGFydCBkb2NrZXInLFxyXG4gICAgICAnc3lzdGVtY3RsIGVuYWJsZSBkb2NrZXInLFxyXG4gICAgICAndXNlcm1vZCAtYUcgZG9ja2VyIGVjMi11c2VyJyxcclxuICAgICAgJycsXHJcbiAgICAgICcjIEluc3RhbGwgRG9ja2VyIENvbXBvc2UnLFxyXG4gICAgICAnY3VybCAtTCBcImh0dHBzOi8vZ2l0aHViLmNvbS9kb2NrZXIvY29tcG9zZS9yZWxlYXNlcy9sYXRlc3QvZG93bmxvYWQvZG9ja2VyLWNvbXBvc2UtJCh1bmFtZSAtcyktJCh1bmFtZSAtbSlcIiAtbyAvdXNyL2xvY2FsL2Jpbi9kb2NrZXItY29tcG9zZScsXHJcbiAgICAgICdjaG1vZCAreCAvdXNyL2xvY2FsL2Jpbi9kb2NrZXItY29tcG9zZScsXHJcbiAgICAgICcnLFxyXG4gICAgICAnIyBJbnN0YWxsIFB5dGhvbiAzLjExJyxcclxuICAgICAgJ3l1bSBpbnN0YWxsIC15IHB5dGhvbjMuMTEgcHl0aG9uMy4xMS1waXAnLFxyXG4gICAgICAnJyxcclxuICAgICAgJyMgQ3JlYXRlIGFwcCBkaXJlY3RvcnknLFxyXG4gICAgICAnbWtkaXIgLXAgL2hvbWUvZWMyLXVzZXIvaW50ZXJ2aWV3LWFzc2lzdGFudCcsXHJcbiAgICAgICdjaG93biAtUiBlYzItdXNlcjplYzItdXNlciAvaG9tZS9lYzItdXNlci9pbnRlcnZpZXctYXNzaXN0YW50JyxcclxuICAgICAgJycsXHJcbiAgICAgICcjIEluc3RhbGwgT2xsYW1hJyxcclxuICAgICAgJ2N1cmwgLWZzU0wgaHR0cHM6Ly9vbGxhbWEuY29tL2luc3RhbGwuc2ggfCBzaCcsXHJcbiAgICAgICdzeXN0ZW1jdGwgZW5hYmxlIG9sbGFtYScsXHJcbiAgICAgICdzeXN0ZW1jdGwgc3RhcnQgb2xsYW1hJyxcclxuICAgICAgJycsXHJcbiAgICAgICcjIFdhaXQgZm9yIE9sbGFtYSB0byBzdGFydCcsXHJcbiAgICAgICdzbGVlcCAxMCcsXHJcbiAgICAgICcnLFxyXG4gICAgICAnIyBQdWxsIGxpZ2h0d2VpZ2h0IG1vZGVsIGZvciB0Mi5taWNybycsXHJcbiAgICAgICdvbGxhbWEgcHVsbCB0aW55bGxhbWEnLFxyXG4gICAgICAnJyxcclxuICAgICAgJyMgSW5zdGFsbCBuZ2lueCcsXHJcbiAgICAgICd5dW0gaW5zdGFsbCAteSBuZ2lueCcsXHJcbiAgICAgICcnLFxyXG4gICAgICAnIyBDb25maWd1cmUgbmdpbngnLFxyXG4gICAgICAnY2F0ID4gL2V0Yy9uZ2lueC9jb25mLmQvaW50ZXJ2aWV3LWFzc2lzdGFudC5jb25mIDw8IFxcJ05HSU5YRU9GXFwnJyxcclxuICAgICAgJ3NlcnZlciB7JyxcclxuICAgICAgJyAgICBsaXN0ZW4gODA7JyxcclxuICAgICAgJyAgICBzZXJ2ZXJfbmFtZSBfOycsXHJcbiAgICAgICcnLFxyXG4gICAgICAnICAgIGxvY2F0aW9uIC9hcGkvIHsnLFxyXG4gICAgICAnICAgICAgICBwcm94eV9wYXNzIGh0dHA6Ly8xMjcuMC4wLjE6ODAwMC87JyxcclxuICAgICAgJyAgICAgICAgcHJveHlfaHR0cF92ZXJzaW9uIDEuMTsnLFxyXG4gICAgICAnICAgICAgICBwcm94eV9zZXRfaGVhZGVyIFVwZ3JhZGUgJGh0dHBfdXBncmFkZTsnLFxyXG4gICAgICAnICAgICAgICBwcm94eV9zZXRfaGVhZGVyIENvbm5lY3Rpb24gXCJ1cGdyYWRlXCI7JyxcclxuICAgICAgJyAgICAgICAgcHJveHlfc2V0X2hlYWRlciBIb3N0ICRob3N0OycsXHJcbiAgICAgICcgICAgICAgIHByb3h5X3NldF9oZWFkZXIgWC1SZWFsLUlQICRyZW1vdGVfYWRkcjsnLFxyXG4gICAgICAnICAgICAgICBwcm94eV9zZXRfaGVhZGVyIFgtRm9yd2FyZGVkLUZvciAkcHJveHlfYWRkX3hfZm9yd2FyZGVkX2ZvcjsnLFxyXG4gICAgICAnICAgICAgICBwcm94eV9yZWFkX3RpbWVvdXQgMzAwczsnLFxyXG4gICAgICAnICAgIH0nLFxyXG4gICAgICAnJyxcclxuICAgICAgJyAgICBsb2NhdGlvbiAvd3MvIHsnLFxyXG4gICAgICAnICAgICAgICBwcm94eV9wYXNzIGh0dHA6Ly8xMjcuMC4wLjE6ODAwMC93cy87JyxcclxuICAgICAgJyAgICAgICAgcHJveHlfaHR0cF92ZXJzaW9uIDEuMTsnLFxyXG4gICAgICAnICAgICAgICBwcm94eV9zZXRfaGVhZGVyIFVwZ3JhZGUgJGh0dHBfdXBncmFkZTsnLFxyXG4gICAgICAnICAgICAgICBwcm94eV9zZXRfaGVhZGVyIENvbm5lY3Rpb24gXCJ1cGdyYWRlXCI7JyxcclxuICAgICAgJyAgICAgICAgcHJveHlfc2V0X2hlYWRlciBIb3N0ICRob3N0OycsXHJcbiAgICAgICcgICAgICAgIHByb3h5X3JlYWRfdGltZW91dCA4NjQwMDsnLFxyXG4gICAgICAnICAgIH0nLFxyXG4gICAgICAnJyxcclxuICAgICAgJyAgICBsb2NhdGlvbiAvaGVhbHRoIHsnLFxyXG4gICAgICAnICAgICAgICBwcm94eV9wYXNzIGh0dHA6Ly8xMjcuMC4wLjE6ODAwMC9oZWFsdGg7JyxcclxuICAgICAgJyAgICB9JyxcclxuICAgICAgJ30nLFxyXG4gICAgICAnTkdJTlhFT0YnLFxyXG4gICAgICAnJyxcclxuICAgICAgJ3JtIC1mIC9ldGMvbmdpbngvY29uZi5kL2RlZmF1bHQuY29uZiAyPi9kZXYvbnVsbCB8fCB0cnVlJyxcclxuICAgICAgJ3N5c3RlbWN0bCBzdGFydCBuZ2lueCcsXHJcbiAgICAgICdzeXN0ZW1jdGwgZW5hYmxlIG5naW54JyxcclxuICAgICAgJycsXHJcbiAgICAgICcjIENyZWF0ZSBzeXN0ZW1kIHNlcnZpY2UgZm9yIGJhY2tlbmQnLFxyXG4gICAgICAnY2F0ID4gL2V0Yy9zeXN0ZW1kL3N5c3RlbS9pbnRlcnZpZXctYXNzaXN0YW50LnNlcnZpY2UgPDwgXFwnU0VSVklDRUVPRlxcJycsXHJcbiAgICAgICdbVW5pdF0nLFxyXG4gICAgICAnRGVzY3JpcHRpb249SW50ZXJ2aWV3IEFzc2lzdGFudCBCYWNrZW5kJyxcclxuICAgICAgJ0FmdGVyPW5ldHdvcmsudGFyZ2V0JyxcclxuICAgICAgJycsXHJcbiAgICAgICdbU2VydmljZV0nLFxyXG4gICAgICAnVHlwZT1zaW1wbGUnLFxyXG4gICAgICAnVXNlcj1lYzItdXNlcicsXHJcbiAgICAgICdXb3JraW5nRGlyZWN0b3J5PS9ob21lL2VjMi11c2VyL2ludGVydmlldy1hc3Npc3RhbnQvYmFja2VuZCcsXHJcbiAgICAgICdFeGVjU3RhcnQ9L3Vzci9iaW4vcHl0aG9uMy4xMSAtbSB1dmljb3JuIGFwcDphcHAgLS1ob3N0IDAuMC4wLjAgLS1wb3J0IDgwMDAnLFxyXG4gICAgICAnUmVzdGFydD1hbHdheXMnLFxyXG4gICAgICAnUmVzdGFydFNlYz0xMCcsXHJcbiAgICAgICdFbnZpcm9ubWVudD1QWVRIT05VTkJVRkZFUkVEPTEnLFxyXG4gICAgICAnRW52aXJvbm1lbnQ9T0xMQU1BX0hPU1Q9aHR0cDovL2xvY2FsaG9zdDoxMTQzNCcsXHJcbiAgICAgICdFbnZpcm9ubWVudD1PTExBTUFfTU9ERUw9dGlueWxsYW1hJyxcclxuICAgICAgJycsXHJcbiAgICAgICdbSW5zdGFsbF0nLFxyXG4gICAgICAnV2FudGVkQnk9bXVsdGktdXNlci50YXJnZXQnLFxyXG4gICAgICAnU0VSVklDRUVPRicsXHJcbiAgICAgICcnLFxyXG4gICAgICAnc3lzdGVtY3RsIGRhZW1vbi1yZWxvYWQnLFxyXG4gICAgICAnJyxcclxuICAgICAgJyMgQ3JlYXRlIGluaXQgY29tcGxldGUgbWFya2VyJyxcclxuICAgICAgJ2VjaG8gXCJFQzIgaW5pdGlhbGl6YXRpb24gY29tcGxldGUhXCIgPiAvaG9tZS9lYzItdXNlci9pbml0LWNvbXBsZXRlLnR4dCcsXHJcbiAgICAgICdjaG93biBlYzItdXNlcjplYzItdXNlciAvaG9tZS9lYzItdXNlci9pbml0LWNvbXBsZXRlLnR4dCcsXHJcbiAgICApO1xyXG5cclxuICAgIC8vID09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09XHJcbiAgICAvLyBFQzIgSW5zdGFuY2VcclxuICAgIC8vID09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09XHJcbiAgICBjb25zdCBpbnN0YW5jZSA9IG5ldyBlYzIuSW5zdGFuY2UodGhpcywgJ0JhY2tlbmRJbnN0YW5jZScsIHtcclxuICAgICAgdnBjLFxyXG4gICAgICB2cGNTdWJuZXRzOiB7XHJcbiAgICAgICAgc3VibmV0VHlwZTogZWMyLlN1Ym5ldFR5cGUuUFVCTElDLFxyXG4gICAgICB9LFxyXG4gICAgICAvLyBVc2luZyB0My5taWNybyAtIGFsc28gZnJlZSB0aWVyIGVsaWdpYmxlIGFuZCBiZXR0ZXIgcGVyZm9ybWFuY2UgdGhhbiB0Mi5taWNyb1xyXG4gICAgICBpbnN0YW5jZVR5cGU6IGVjMi5JbnN0YW5jZVR5cGUub2YoXHJcbiAgICAgICAgZWMyLkluc3RhbmNlQ2xhc3MuVDMsXHJcbiAgICAgICAgZWMyLkluc3RhbmNlU2l6ZS5NSUNST1xyXG4gICAgICApLFxyXG4gICAgICBtYWNoaW5lSW1hZ2U6IGVjMi5NYWNoaW5lSW1hZ2UubGF0ZXN0QW1hem9uTGludXgyMDIzKCksXHJcbiAgICAgIHNlY3VyaXR5R3JvdXA6IGJhY2tlbmRTRyxcclxuICAgICAgcm9sZTogZWMyUm9sZSxcclxuICAgICAgdXNlckRhdGE6IHVzZXJEYXRhU2NyaXB0LFxyXG4gICAgICBrZXlOYW1lOiAnaW50ZXJ2aWV3LWFzc2lzdGFudC1rZXknLFxyXG4gICAgICBibG9ja0RldmljZXM6IFtcclxuICAgICAgICB7XHJcbiAgICAgICAgICBkZXZpY2VOYW1lOiAnL2Rldi94dmRhJyxcclxuICAgICAgICAgIHZvbHVtZTogZWMyLkJsb2NrRGV2aWNlVm9sdW1lLmVicygyMCwge1xyXG4gICAgICAgICAgICB2b2x1bWVUeXBlOiBlYzIuRWJzRGV2aWNlVm9sdW1lVHlwZS5HUDMsXHJcbiAgICAgICAgICAgIGVuY3J5cHRlZDogdHJ1ZSxcclxuICAgICAgICAgIH0pLFxyXG4gICAgICAgIH0sXHJcbiAgICAgIF0sXHJcbiAgICB9KTtcclxuXHJcbiAgICBjZGsuVGFncy5vZihpbnN0YW5jZSkuYWRkKCdOYW1lJywgJ2ludGVydmlldy1hc3Npc3RhbnQtYmFja2VuZCcpO1xyXG5cclxuICAgIC8vID09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09XHJcbiAgICAvLyBFbGFzdGljIElQXHJcbiAgICAvLyA9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PVxyXG4gICAgY29uc3QgZWlwID0gbmV3IGVjMi5DZm5FSVAodGhpcywgJ0JhY2tlbmRFSVAnLCB7XHJcbiAgICAgIGluc3RhbmNlSWQ6IGluc3RhbmNlLmluc3RhbmNlSWQsXHJcbiAgICAgIHRhZ3M6IFt7IGtleTogJ05hbWUnLCB2YWx1ZTogJ2ludGVydmlldy1hc3Npc3RhbnQtZWlwJyB9XSxcclxuICAgIH0pO1xyXG5cclxuICAgIC8vID09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09XHJcbiAgICAvLyBTMyBCdWNrZXQgZm9yIEZyb250ZW5kXHJcbiAgICAvLyA9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PVxyXG4gICAgY29uc3QgZnJvbnRlbmRCdWNrZXQgPSBuZXcgczMuQnVja2V0KHRoaXMsICdGcm9udGVuZEJ1Y2tldCcsIHtcclxuICAgICAgYnVja2V0TmFtZTogYGludGVydmlldy1hc3Npc3RhbnQtZnJvbnRlbmQtJHt0aGlzLmFjY291bnR9YCxcclxuICAgICAgYmxvY2tQdWJsaWNBY2Nlc3M6IHMzLkJsb2NrUHVibGljQWNjZXNzLkJMT0NLX0FMTCxcclxuICAgICAgcmVtb3ZhbFBvbGljeTogY2RrLlJlbW92YWxQb2xpY3kuREVTVFJPWSxcclxuICAgICAgYXV0b0RlbGV0ZU9iamVjdHM6IHRydWUsXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyA9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PVxyXG4gICAgLy8gQ2xvdWRGcm9udCBEaXN0cmlidXRpb25cclxuICAgIC8vID09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09XHJcbiAgICBjb25zdCBkaXN0cmlidXRpb24gPSBuZXcgY2xvdWRmcm9udC5EaXN0cmlidXRpb24odGhpcywgJ0Zyb250ZW5kRGlzdHJpYnV0aW9uJywge1xyXG4gICAgICBkZWZhdWx0QmVoYXZpb3I6IHtcclxuICAgICAgICBvcmlnaW46IG5ldyBvcmlnaW5zLlMzT3JpZ2luKGZyb250ZW5kQnVja2V0KSxcclxuICAgICAgICB2aWV3ZXJQcm90b2NvbFBvbGljeTogY2xvdWRmcm9udC5WaWV3ZXJQcm90b2NvbFBvbGljeS5SRURJUkVDVF9UT19IVFRQUyxcclxuICAgICAgICBjYWNoZVBvbGljeTogY2xvdWRmcm9udC5DYWNoZVBvbGljeS5DQUNISU5HX09QVElNSVpFRCxcclxuICAgICAgfSxcclxuICAgICAgZGVmYXVsdFJvb3RPYmplY3Q6ICdpbmRleC5odG1sJyxcclxuICAgICAgZXJyb3JSZXNwb25zZXM6IFtcclxuICAgICAgICB7XHJcbiAgICAgICAgICBodHRwU3RhdHVzOiA0MDMsXHJcbiAgICAgICAgICByZXNwb25zZUh0dHBTdGF0dXM6IDIwMCxcclxuICAgICAgICAgIHJlc3BvbnNlUGFnZVBhdGg6ICcvaW5kZXguaHRtbCcsXHJcbiAgICAgICAgICB0dGw6IGNkay5EdXJhdGlvbi5taW51dGVzKDUpLFxyXG4gICAgICAgIH0sXHJcbiAgICAgICAge1xyXG4gICAgICAgICAgaHR0cFN0YXR1czogNDA0LFxyXG4gICAgICAgICAgcmVzcG9uc2VIdHRwU3RhdHVzOiAyMDAsXHJcbiAgICAgICAgICByZXNwb25zZVBhZ2VQYXRoOiAnL2luZGV4Lmh0bWwnLFxyXG4gICAgICAgICAgdHRsOiBjZGsuRHVyYXRpb24ubWludXRlcyg1KSxcclxuICAgICAgICB9LFxyXG4gICAgICBdLFxyXG4gICAgfSk7XHJcblxyXG4gICAgLy8gPT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT1cclxuICAgIC8vIE91dHB1dHNcclxuICAgIC8vID09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09XHJcbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnQmFja2VuZFVSTCcsIHtcclxuICAgICAgdmFsdWU6IGBodHRwOi8vJHtlaXAuYXR0clB1YmxpY0lwfWAsXHJcbiAgICAgIGRlc2NyaXB0aW9uOiAnQmFja2VuZCBBUEkgVVJMJyxcclxuICAgICAgZXhwb3J0TmFtZTogJ0ludGVydmlld0Fzc2lzdGFudEJhY2tlbmRVUkwnLFxyXG4gICAgfSk7XHJcblxyXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0Zyb250ZW5kVVJMJywge1xyXG4gICAgICB2YWx1ZTogYGh0dHBzOi8vJHtkaXN0cmlidXRpb24uZGlzdHJpYnV0aW9uRG9tYWluTmFtZX1gLFxyXG4gICAgICBkZXNjcmlwdGlvbjogJ0Zyb250ZW5kIFVSTCAoQ2xvdWRGcm9udCknLFxyXG4gICAgICBleHBvcnROYW1lOiAnSW50ZXJ2aWV3QXNzaXN0YW50RnJvbnRlbmRVUkwnLFxyXG4gICAgfSk7XHJcblxyXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0VDMkluc3RhbmNlSWQnLCB7XHJcbiAgICAgIHZhbHVlOiBpbnN0YW5jZS5pbnN0YW5jZUlkLFxyXG4gICAgICBkZXNjcmlwdGlvbjogJ0VDMiBJbnN0YW5jZSBJRCcsXHJcbiAgICB9KTtcclxuXHJcbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnRUMyUHVibGljSVAnLCB7XHJcbiAgICAgIHZhbHVlOiBlaXAuYXR0clB1YmxpY0lwLFxyXG4gICAgICBkZXNjcmlwdGlvbjogJ0VDMiBQdWJsaWMgSVAnLFxyXG4gICAgfSk7XHJcblxyXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ1MzQnVja2V0TmFtZScsIHtcclxuICAgICAgdmFsdWU6IGZyb250ZW5kQnVja2V0LmJ1Y2tldE5hbWUsXHJcbiAgICAgIGRlc2NyaXB0aW9uOiAnRnJvbnRlbmQgUzMgQnVja2V0JyxcclxuICAgIH0pO1xyXG5cclxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdTU0hDb21tYW5kJywge1xyXG4gICAgICB2YWx1ZTogYHNzaCAtaSBpbnRlcnZpZXctYXNzaXN0YW50LWtleS5wZW0gZWMyLXVzZXJAJHtlaXAuYXR0clB1YmxpY0lwfWAsXHJcbiAgICAgIGRlc2NyaXB0aW9uOiAnU1NIIGNvbW1hbmQnLFxyXG4gICAgfSk7XHJcbiAgfVxyXG59Il19
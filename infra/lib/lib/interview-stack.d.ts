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
import { Construct } from 'constructs';
export declare class InterviewAssistantStack extends cdk.Stack {
    readonly backendUrl: cdk.CfnOutput;
    readonly frontendUrl: cdk.CfnOutput;
    constructor(scope: Construct, id: string, props?: cdk.StackProps);
}

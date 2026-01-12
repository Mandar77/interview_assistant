#!/usr/bin/env node
/**
 * CDK App Entry Point
 * Location: infra/bin/interview-assistant.ts
 */

import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { InterviewAssistantStack } from '../lib/interview-stack';

const app = new cdk.App();

// Environment configuration
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT || '696791035505',
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};

// Create the main stack
new InterviewAssistantStack(app, 'InterviewAssistantStack', {
  env,
  description: 'Interview Assistant - AI-powered mock interview platform',
  
  // Stack-level tags
  tags: {
    Project: 'InterviewAssistant',
    Environment: 'production',
    ManagedBy: 'CDK',
  },
});

app.synth();
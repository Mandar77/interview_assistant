#!/usr/bin/env node
"use strict";
/**
 * CDK App Entry Point
 * Location: infra/bin/interview-assistant.ts
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
require("source-map-support/register");
const cdk = __importStar(require("aws-cdk-lib"));
const interview_stack_1 = require("../lib/interview-stack");
const app = new cdk.App();
// Environment configuration
const env = {
    account: process.env.CDK_DEFAULT_ACCOUNT || '696791035505',
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};
// Create the main stack
new interview_stack_1.InterviewAssistantStack(app, 'InterviewAssistantStack', {
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiaW50ZXJ2aWV3LWFzc2lzdGFudC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL2Jpbi9pbnRlcnZpZXctYXNzaXN0YW50LnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7O0FBQ0E7OztHQUdHOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7OztBQUVILHVDQUFxQztBQUNyQyxpREFBbUM7QUFDbkMsNERBQWlFO0FBRWpFLE1BQU0sR0FBRyxHQUFHLElBQUksR0FBRyxDQUFDLEdBQUcsRUFBRSxDQUFDO0FBRTFCLDRCQUE0QjtBQUM1QixNQUFNLEdBQUcsR0FBRztJQUNWLE9BQU8sRUFBRSxPQUFPLENBQUMsR0FBRyxDQUFDLG1CQUFtQixJQUFJLGNBQWM7SUFDMUQsTUFBTSxFQUFFLE9BQU8sQ0FBQyxHQUFHLENBQUMsa0JBQWtCLElBQUksV0FBVztDQUN0RCxDQUFDO0FBRUYsd0JBQXdCO0FBQ3hCLElBQUkseUNBQXVCLENBQUMsR0FBRyxFQUFFLHlCQUF5QixFQUFFO0lBQzFELEdBQUc7SUFDSCxXQUFXLEVBQUUsMERBQTBEO0lBRXZFLG1CQUFtQjtJQUNuQixJQUFJLEVBQUU7UUFDSixPQUFPLEVBQUUsb0JBQW9CO1FBQzdCLFdBQVcsRUFBRSxZQUFZO1FBQ3pCLFNBQVMsRUFBRSxLQUFLO0tBQ2pCO0NBQ0YsQ0FBQyxDQUFDO0FBRUgsR0FBRyxDQUFDLEtBQUssRUFBRSxDQUFDIiwic291cmNlc0NvbnRlbnQiOlsiIyEvdXNyL2Jpbi9lbnYgbm9kZVxyXG4vKipcclxuICogQ0RLIEFwcCBFbnRyeSBQb2ludFxyXG4gKiBMb2NhdGlvbjogaW5mcmEvYmluL2ludGVydmlldy1hc3Npc3RhbnQudHNcclxuICovXHJcblxyXG5pbXBvcnQgJ3NvdXJjZS1tYXAtc3VwcG9ydC9yZWdpc3Rlcic7XHJcbmltcG9ydCAqIGFzIGNkayBmcm9tICdhd3MtY2RrLWxpYic7XHJcbmltcG9ydCB7IEludGVydmlld0Fzc2lzdGFudFN0YWNrIH0gZnJvbSAnLi4vbGliL2ludGVydmlldy1zdGFjayc7XHJcblxyXG5jb25zdCBhcHAgPSBuZXcgY2RrLkFwcCgpO1xyXG5cclxuLy8gRW52aXJvbm1lbnQgY29uZmlndXJhdGlvblxyXG5jb25zdCBlbnYgPSB7XHJcbiAgYWNjb3VudDogcHJvY2Vzcy5lbnYuQ0RLX0RFRkFVTFRfQUNDT1VOVCB8fCAnNjk2NzkxMDM1NTA1JyxcclxuICByZWdpb246IHByb2Nlc3MuZW52LkNES19ERUZBVUxUX1JFR0lPTiB8fCAndXMtZWFzdC0xJyxcclxufTtcclxuXHJcbi8vIENyZWF0ZSB0aGUgbWFpbiBzdGFja1xyXG5uZXcgSW50ZXJ2aWV3QXNzaXN0YW50U3RhY2soYXBwLCAnSW50ZXJ2aWV3QXNzaXN0YW50U3RhY2snLCB7XHJcbiAgZW52LFxyXG4gIGRlc2NyaXB0aW9uOiAnSW50ZXJ2aWV3IEFzc2lzdGFudCAtIEFJLXBvd2VyZWQgbW9jayBpbnRlcnZpZXcgcGxhdGZvcm0nLFxyXG4gIFxyXG4gIC8vIFN0YWNrLWxldmVsIHRhZ3NcclxuICB0YWdzOiB7XHJcbiAgICBQcm9qZWN0OiAnSW50ZXJ2aWV3QXNzaXN0YW50JyxcclxuICAgIEVudmlyb25tZW50OiAncHJvZHVjdGlvbicsXHJcbiAgICBNYW5hZ2VkQnk6ICdDREsnLFxyXG4gIH0sXHJcbn0pO1xyXG5cclxuYXBwLnN5bnRoKCk7Il19
# Agent Core Security Configuration - Quick Reference

## Overview

This is a quick reference for the Agent Core IAM and security configuration implemented in TASK-CHT-003.

---

## IAM Roles Summary

### Execution Role: `${local.name_prefix}-ecs-execution`
```
Purpose: ECS infrastructure (ECR auth, CloudWatch logs)
Trust: ecs-tasks.amazonaws.com
Policies:
  - AmazonECSTaskExecutionRolePolicy (AWS managed)
  - Custom: Secrets Manager, KMS, CloudWatch Logs
```

### Task Role: `${local.name_prefix}-ecs-task`
```
Purpose: Application permissions (Bedrock, DynamoDB, CloudWatch)
Trust: ecs-tasks.amazonaws.com
Policies:
  - ecs_task_app: General application access
  - agent_core_access: Agent-specific permissions
```

---

## Permissions Quick Reference

### Agent Core Permissions
```
Bedrock:
  ✓ bedrock:InvokeModel
  ✓ bedrock:InvokeModelWithResponseStream

DynamoDB (Read-Only):
  ✓ dynamodb:GetItem
  ✓ dynamodb:Query
  ✗ dynamodb:PutItem (denied)
  ✗ dynamodb:DeleteItem (denied)
  
  Tables:
  - tech-news-conversation_sessions
  - tech-news-conversation_messages

CloudWatch:
  ✓ logs:CreateLogGroup
  ✓ logs:CreateLogStream
  ✓ logs:PutLogEvents
  
  Log Group: /ecs/tech-news-mystery-prod-agent-core
```

---

## Security Groups

### Inbound (Agent Core)
```
Port: 8080
Source: agent_core_alb security group only
CIDR: NOT 0.0.0.0/0 (VPC-internal only)
```

### Outbound (Agent Core)
```
Ports: All (0-65535)
Protocol: All
Destination: 0.0.0.0/0 (allows AWS service calls)
```

### Inbound (ALB)
```
Port: 8080
Source: VPC CIDR (10.40.0.0/16)
Protocol: TCP
```

---

## Common Tasks

### Check Role Permissions
```bash
# Execution role
aws iam get-role-policy \
  --role-name tech-news-mystery-prod-ecs-execution \
  --policy-name tech-news-mystery-prod-read-secrets

# Task role
aws iam get-role-policy \
  --role-name tech-news-mystery-prod-ecs-task \
  --policy-name tech-news-mystery-prod-agent-core-access
```

### Add Permission to Agent Core
```hcl
# In iam.tf, within agent_core_access policy:
{
  "Sid": "NewPermission",
  "Effect": "Allow",
  "Action": ["service:Action"],
  "Resource": "arn:aws:service:region:account:resource/*"
}
```

### Check Security Group Rules
```bash
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=tech-news-mystery-prod-agent-core-*"
```

### View CloudWatch Logs
```bash
aws logs tail /ecs/tech-news-mystery-prod-agent-core --follow
```

---

## Troubleshooting

### Agent Core Cannot Connect to Bedrock
```
Check: Task role has bedrock:InvokeModel permission
Check: Bedrock is available in var.aws_region
Check: CloudWatch logs in /ecs/tech-news-mystery-prod-agent-core
```

### Agent Core Cannot Query DynamoDB
```
Check: Task role has dynamodb:GetItem and dynamodb:Query
Check: Table names include ${var.dynamodb_table_prefix}
Check: ARN pattern matches: arn:aws:dynamodb:region:account:table/TABLE_NAME
Check: Index ARNs included in Resource list
```

### Agent Core Logs Not Appearing
```
Check: Execution role has logs:CreateLogStream permission
Check: Execution role has logs:PutLogEvents permission
Check: Log group /ecs/tech-news-mystery-prod-agent-core exists
Check: log_retention_in_days is set (30 days)
```

### Agent Core Not Accessible from VPC
```
Check: Security group inbound allows port 8080
Check: Source is agent_core_alb security group (not 0.0.0.0/0)
Check: ALB security group allows traffic from VPC CIDR
Check: Network ACLs allow communication
```

---

## Variable References

### In Terraform Files
```hcl
${var.aws_region}                          # us-west-2
${var.dynamodb_table_prefix}               # tech-news-
${data.aws_caller_identity.current.account_id}  # 123456789012
${local.name_prefix}                       # tech-news-mystery-prod
${local.vpc_id}                            # vpc-xxxxx
${aws_security_group.agent_core_alb.id}    # sg-xxxxx
```

### Environment Variables (Container)
```
AWS_REGION=us-west-2
ENVIRONMENT=production
DEBUG=false
AGENT_MODEL=claude-3-5-sonnet-20241022
MEMORY_TYPE=conversation_sessions
TOOL_TIMEOUT=300
ANTHROPIC_API_KEY=(from secrets manager)
```

---

## Related Files

- `infra/terraform/iam.tf` - IAM roles and policies
- `infra/terraform/network.tf` - Security groups
- `infra/terraform/ecs.tf` - Task definition and service
- `infra/terraform/locals.tf` - Variable definitions
- `infra/terraform/variables.tf` - Variable defaults

---

## Policy JSON Examples

### Bedrock Permission
```json
{
  "Sid": "BedrockInvokeForAgentCore",
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": "*"
}
```

### DynamoDB Permission
```json
{
  "Sid": "DynamoDBSessionAccess",
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:Query"
  ],
  "Resource": [
    "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.dynamodb_table_prefix}conversation_sessions",
    "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.dynamodb_table_prefix}conversation_messages",
    "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.dynamodb_table_prefix}conversation_sessions/index/*",
    "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.dynamodb_table_prefix}conversation_messages/index/*"
  ]
}
```

### CloudWatch Permission
```json
{
  "Sid": "CloudWatchLogs",
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/${local.name_prefix}-agent-core*"
}
```

---

## Testing

### Run All Tests
```bash
cd infra/terraform
python test_iam_security.py
```

### Run Terraform Validation
```bash
cd infra/terraform
./validate_terraform.sh
```

### Manual Verification
```bash
# 1. Check role exists
aws iam get-role --role-name tech-news-mystery-prod-ecs-task

# 2. Check policy attached
aws iam get-role-policy \
  --role-name tech-news-mystery-prod-ecs-task \
  --policy-name tech-news-mystery-prod-agent-core-access

# 3. Check task definition
aws ecs describe-task-definition \
  --task-definition tech-news-mystery-prod-agent-core

# 4. Check security group
aws ec2 describe-security-groups \
  --group-names tech-news-mystery-prod-agent-core-*
```

---

## Best Practices

1. **Always use variables** - Never hardcode region, account ID, or table names
2. **Least privilege** - Only grant needed permissions
3. **Resource-specific ARNs** - Use specific table/resource ARNs, not wildcards
4. **Separate roles** - Keep execution and task roles separate
5. **Regular audits** - Review CloudTrail for role assumption
6. **Document changes** - Update this reference when modifying permissions

---

## Support

For issues or questions about Agent Core security:
1. Check CloudWatch logs: `/ecs/tech-news-mystery-prod-agent-core`
2. Review IAM policies in AWS console
3. Check security group rules in EC2 console
4. Refer to implementation documents:
   - IMPLEMENTATION_CHT_003.md
   - TEST_RESULTS_CHT_003.md
   - TASK_CHT_003_COMPLETION.md

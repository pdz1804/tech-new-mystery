# =============================================================================
# AWS Bedrock AgentCore
# =============================================================================

locals {
  agentcore_name_prefix      = replace(local.name_prefix, "-", "_")
  agentcore_runtime_name     = "${local.agentcore_name_prefix}_agent"
  agentcore_memory_name      = "${local.agentcore_name_prefix}_memory"
  agentcore_browser_name     = "${local.agentcore_name_prefix}_browser"
  agentcore_interpreter_name = "${local.agentcore_name_prefix}_code_interpreter"

  agentcore_environment = {
    AWS_REGION             = var.aws_region
    BEDROCK_REGION         = var.aws_region
    ENVIRONMENT            = "production"
    AGENT_MODEL            = var.agent_core_model
    MEMORY_ID              = aws_bedrockagentcore_memory.agent_core.id
    BROWSER_ID             = aws_bedrockagentcore_browser.agent_core.browser_id
    CODE_INTERPRETER_ID    = aws_bedrockagentcore_code_interpreter.agent_core.code_interpreter_id
    APP_SECRET_ARN         = local.app_secret_arn
    REQUIRE_TRUE_STREAMING = "true"
    QDRANT_MODE            = "cloud"
    QDRANT_COLLECTION_NAME = var.qdrant_collection_name
    OPENAI_EMBEDDING_MODEL = var.openai_embedding_model
    TOOL_TIMEOUT           = tostring(var.agent_core_tool_timeout)
    MAX_SEARCH_RESULTS     = "8"
  }
}

resource "aws_iam_role" "agentcore_runtime" {
  name = "${local.name_prefix}-agentcore-runtime"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock-agentcore.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "agentcore_runtime" {
  name = "${local.name_prefix}-agentcore-runtime-policy"
  role = aws_iam_role.agentcore_runtime.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockInvoke"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      {
        Sid    = "AgentCoreMemory"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:CreateEvent",
          "bedrock-agentcore:DeleteEvent",
          "bedrock-agentcore:GetEvent",
          "bedrock-agentcore:GetMemory",
          "bedrock-agentcore:ListEvents",
          "bedrock-agentcore:ListMemories",
          "bedrock-agentcore:RetrieveMemory"
        ]
        Resource = aws_bedrockagentcore_memory.agent_core.arn
      },
      {
        Sid    = "AgentCoreBrowser"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:GetBrowserSession",
          "bedrock-agentcore:InvokeBrowser",
          "bedrock-agentcore:InvokeOnBrowserSession",
          "bedrock-agentcore:StartBrowserSession",
          "bedrock-agentcore:StopBrowserSession"
        ]
        Resource = aws_bedrockagentcore_browser.agent_core.browser_arn
      },
      {
        Sid    = "AgentCoreCodeInterpreter"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:GetCodeInterpreterSession",
          "bedrock-agentcore:InvokeCodeInterpreter",
          "bedrock-agentcore:InvokeOnCodeInterpreterSession",
          "bedrock-agentcore:StartCodeInterpreterSession",
          "bedrock-agentcore:StopCodeInterpreterSession"
        ]
        Resource = aws_bedrockagentcore_code_interpreter.agent_core.code_interpreter_arn
      },
      {
        Sid      = "ReadAppSecret"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = local.app_secret_arn
      },
      {
        Sid      = "ECRAuth"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "ECRPullAgentImage"
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = aws_ecr_repository.agent_core.arn
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "agentcore_memory" {
  name = "${local.name_prefix}-agentcore-memory"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock-agentcore.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "agentcore_memory_bedrock" {
  role       = aws_iam_role.agentcore_memory.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockAgentCoreMemoryBedrockModelInferenceExecutionRolePolicy"
}

resource "aws_bedrockagentcore_memory" "agent_core" {
  name                      = local.agentcore_memory_name
  description               = "Conversation memory for ${local.name_prefix} AgentCore runtime"
  event_expiry_duration     = var.agent_core_memory_event_expiry_days
  memory_execution_role_arn = aws_iam_role.agentcore_memory.arn

  depends_on = [aws_iam_role_policy_attachment.agentcore_memory_bedrock]
}

resource "aws_bedrockagentcore_browser" "agent_core" {
  name               = local.agentcore_browser_name
  description        = "Managed browser tool for ${local.name_prefix} AgentCore runtime"
  execution_role_arn = aws_iam_role.agentcore_runtime.arn

  network_configuration {
    network_mode = "PUBLIC"
  }
}

resource "aws_bedrockagentcore_code_interpreter" "agent_core" {
  name               = local.agentcore_interpreter_name
  description        = "Managed code interpreter tool for ${local.name_prefix} AgentCore runtime"
  execution_role_arn = aws_iam_role.agentcore_runtime.arn

  network_configuration {
    network_mode = "PUBLIC"
  }
}

resource "aws_bedrockagentcore_agent_runtime" "agent_core" {
  agent_runtime_name = local.agentcore_runtime_name
  description        = "Tech News Mystery AI agent - LangGraph + Bedrock Claude"
  role_arn           = aws_iam_role.agentcore_runtime.arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.agent_core.repository_url}:${var.agent_core_image_tag}"
    }
  }

  network_configuration {
    network_mode = "PUBLIC"
  }

  protocol_configuration {
    server_protocol = "HTTP"
  }

  environment_variables = local.agentcore_environment

  depends_on = [aws_iam_role_policy.agentcore_runtime]
}

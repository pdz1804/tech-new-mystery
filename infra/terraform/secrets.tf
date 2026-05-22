resource "aws_secretsmanager_secret" "app" {
  count                   = var.secrets_manager_arn == "" ? 1 : 0
  name                    = "${local.name_prefix}/app"
  recovery_window_in_days = 7
}

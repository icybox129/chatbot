resource "aws_cloudwatch_dashboard" "dashboard" {
  dashboard_name = "${var.naming_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # ECS CPU Utilization
      {
        "type" : "metric",
        "x" : 0,
        "y" : 0,
        "width" : 12,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ECS", "CPUUtilization", "ClusterName", var.ecs_cluster_name, "ServiceName", var.ecs_service_name]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "title" : "ECS CPU Utilization"
        }
      },
      # ECS Memory Utilization
      {
        "type" : "metric",
        "x" : 12,
        "y" : 0,
        "width" : 12,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ECS", "MemoryUtilization", "ClusterName", var.ecs_cluster_name, "ServiceName", var.ecs_service_name]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "title" : "ECS Memory Utilization"
        }
      },
      # ALB Request Count
      {
        "type" : "metric",
        "x" : 0,
        "y" : 6,
        "width" : 24,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", var.alb_name]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "title" : "ALB Request Count"
        }
      }
    ]
  })
}

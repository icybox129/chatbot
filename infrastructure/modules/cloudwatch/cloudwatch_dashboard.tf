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
        "y" : 12,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "period" : 60,
          "metrics" : [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", var.alb_arn_suffix, { "label" : "chatbot-dev-alb", "visible" : true, "region" : "eu-west-2" }]
          ],
          "region" : "eu-west-2",
          "stat" : "Sum",
          "title" : "Requests",
          "yAxis" : {
            "left" : {
              "min" : 0
            }
          },
          "view" : "timeSeries",
          "stacked" : false
        }
      }
    ]
  })
}
variable "cloud_name" {
  description = "Existing clouds.yaml profile, or null to use OS_* authentication. No credentials in Git."
  type        = string
  default     = null
}

variable "pool_id" {
  description = "The already allocated CyberRangeCZ pool ID."
  type        = number
  validation {
    condition     = var.pool_id > 0 && floor(var.pool_id) == var.pool_id
    error_message = "pool_id must identify the existing pool."
  }
}

variable "teams" {
  description = "Map actual trainee/run assignments to existing sandbox and Nova VM UUIDs."
  type = map(object({
    sandbox_uuid   = string
    kali_server_id = string
    web_server_id  = string
  }))
  validation {
    condition = (
      toset(keys(var.teams)) == toset(["A", "B"]) &&
      alltrue([for team in values(var.teams) : alltrue([
        for id in [team.sandbox_uuid, team.kali_server_id, team.web_server_id] :
        can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", id))
      ])]) &&
      length(distinct([for team in values(var.teams) : lower(team.sandbox_uuid)])) == 2 &&
      length(distinct(flatten([for team in values(var.teams) : [lower(team.kali_server_id), lower(team.web_server_id)]]))) == 4
    )
    error_message = "Use keys A/B, two distinct sandbox UUIDs, and four distinct VM UUIDs from those sandboxes."
  }
}

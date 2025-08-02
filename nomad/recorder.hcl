job "pitwall-recorder" {
  type = "batch"
  periodic {
    crons = [
      "45 8 3 8 *"
    ]
    prohibit_overlap = true
    time_zone = "America/New_York"
  }

  group "recorder" {
    task "run" {
      driver = "exec"

      config {
        command = "uv"
        args = ["run", "python", "-u", "capture.py", "--continuous", "--output", "/alloc/data"]
        work_dir = "/alloc/pitwall"
      }

      restart {
        attempts = 10
      }

      artifact {
        source = "https://code.kat5.dev/katie/pitwall/archive/main.zip"
        destination = "/alloc"
      }
    }
  }
}


job "pitwall-recorder" {
  type = "batch"
  periodic {
    crons = [
      "15 6 2 8 *",
      "45 9 2 8 *"
    ]
    prohibit_overlap = true
    time_zone = "America/New_York"
  }

  group "recorder" {
    task "run" {
      driver = "exec"

      config {
        command = "uv"
        args = ["run", "python", "-u", "capture.py", "--continuous"]
        work_dir = "/alloc/pitwall"
      }

      restart {
        attempts = 5
      }

      artifact {
        source = "https://code.kat5.dev/katie/pitwall/archive/main.zip"
        destination = "/alloc"
      }
    }
  }
}


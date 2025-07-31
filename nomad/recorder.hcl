job "pitwall-recorder" {
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
        source = "https://code.kat5.dev/kat/pitwall/archive/parsing.zip"
        destination = "/alloc"
      }
    }
  }
}


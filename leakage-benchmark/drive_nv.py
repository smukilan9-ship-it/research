"""Second campaign, on NVIDIA NIM, running alongside the Featherless one.

WHY SPLIT BY HOST RATHER THAN DUPLICATE
  Featherless caps us at three concurrent calls and serves
  nemotron-3-super-120b in minutes; NVIDIA serves the SAME model in 13s and
  deepseek-v4-flash in 29s. Running those two here and leaving Kimi-K3 and
  GLM-5.2 on Featherless uses both hosts at once and puts each model where it
  is fastest, instead of queueing everything behind one 3-slot limit.

  Results are never merged across hosts: the model ids differ by host, and so
  may the quantisation, so a cell from each is a separate row.
"""
import drive

drive.MODELS = "nvidia/nemotron-3-super-120b-a12b,deepseek-ai/deepseek-v4-flash-0731"
drive.BASE = ["python3", "-u", "runner.py", "--provider", "nvidia",
              "--reasoning", "high", "--models", drive.MODELS,
              "--workers", "4", "--max-tokens", "20000", "--http-timeout", "600"]
drive.LOG = drive.os.path.join(drive.HERE, "nvidia.log")
drive.PHASES = [
    ("NV-1  main corpus, C1+C6",
     drive.BASE + ["--all", "--conditions", "1,6", "--repeats", "1"]),
    ("NV-2  transfer set, C1+C2+C6, 3 shuffles",
     drive.BASE + ["--datasets", "mi,crime,student", "--conditions", "1,2,6",
                   "--repeats", "3"]),
    ("NV-3  main corpus, 3 shuffles",
     drive.BASE + ["--all", "--conditions", "1,6", "--repeats", "3"]),
]

if __name__ == "__main__":
    drive.main()

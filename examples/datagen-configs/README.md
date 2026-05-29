# Data-generation config examples

Examples for `batch_runner.py` and trajectory-compression workflows.

Run from the repository root unless an example says otherwise:

```bash
python batch_runner.py --config examples/datagen-configs/web_research.yaml --run_name web_research_v1
bash examples/datagen-configs/run_browser_tasks.sh
```

Generated data should go under the existing ignored `data/` directory or under `examples/generated/`.

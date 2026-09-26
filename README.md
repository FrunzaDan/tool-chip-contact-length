# Tool-Chip_Contact_Length
This repo contains a Python program that calculates the Tool-Chip Contact Length using computer vision from images shot by a high speed camera.

The general flow of this image processing software is the following:

![General_Flow](https://github.com/FrunzaDan/Tool-Chip_Contact_Length/blob/main/Documentation/Diagrams/TCCL_General_Flow.jpeg)

Run it with `./run.sh`. See [ai_docs/index.md](ai_docs/index.md) for full documentation: project layout, the step-by-step image-processing pipeline, and manual run instructions.

For development: `pip install -e '.[dev]'`. Checks: `pytest`, `ruff check .`, `ruff format .`, `mypy` — see [ai_docs/dev_environment.md](ai_docs/dev_environment.md).

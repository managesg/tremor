# T7 image: NGC PyTorch (pinned by digest) + ONLY the pins below (owner approval 2026-11-19).
# transformers 5.2.0 = first release containing models/qwen3_5 (card says "latest transformers"; see docs/reports/T7-smoke.md).
FROM nvcr.io/nvidia/pytorch:25.11-py3@sha256:417cbf33f87b5378849df37983552cd1f8bc8b62fe1ceabe004de816a55dff21
RUN pip install --no-cache-dir transformers==5.2.0 math-verify==0.9.0 latex2sympy2_extended==1.11.0 antlr4-python3-runtime==4.13.2

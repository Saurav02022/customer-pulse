"""Evaluation harness for the real Gemini assessment baseline (AI_EVALUATION.md).

Manual, network-using tooling. It never runs from pytest and never touches the product
database or the assessment cache. Real calls happen only through eval.run_baseline.
"""

"""
Test Script for Baseline-Gated Interactive Compiler endpoints.
Tests /api/compile/step endpoint, initial run, feedback refinement, and mock evaluation logic.
"""

import os
import json
import logging
from fastapi.testclient import TestClient

# Make sure we use MOCK_LLM=true for local evaluation testing
os.environ["MOCK_LLM"] = "true"

from backend.main import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = TestClient(app)


def test_lexer_initial_step():
    logger.info("Testing initial Lexer step...")
    payload = {
        "prompt": "Build a CRM with contact list and pipeline.",
        "stage": "stage_1_lexer",
        "previous_output": None,
        "feedback": None,
        "stage_inputs": {}
    }
    response = client.post("/api/compile/step", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["stage"] == "stage_1_lexer"
    assert "output" in data
    assert "evaluation" in data
    
    eval_report = data["evaluation"]
    assert "score" in eval_report
    assert "baseline" in eval_report
    assert "critique" in eval_report
    assert eval_report["passed"] is False  # First try should return below baseline (72)
    logger.info(f"Initial Score: {eval_report['score']} (Target: {eval_report['baseline']})")
    
    return data["output"]


def test_lexer_refine_step(previous_output):
    logger.info("Testing Lexer refinement step...")
    payload = {
        "prompt": "Build a CRM with contact list and pipeline.",
        "stage": "stage_1_lexer",
        "previous_output": previous_output,
        "feedback": "Add User entity and Profile fields to contacts.",
        "stage_inputs": {}
    }
    response = client.post("/api/compile/step", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["stage"] == "stage_1_lexer"
    assert "output" in data
    assert "evaluation" in data
    
    eval_report = data["evaluation"]
    assert eval_report["passed"] is True  # Second try should pass (92)
    logger.info(f"Refined Score: {eval_report['score']} (Target: {eval_report['baseline']})")
    
    return data["output"]


def test_parser_step(lexer_output):
    logger.info("Testing Stage 2 Parser step...")
    payload = {
        "prompt": "Build a CRM with contact list and pipeline.",
        "stage": "stage_2_parser",
        "previous_output": None,
        "feedback": None,
        "stage_inputs": {
            "stage_1_lexer": lexer_output
        }
    }
    response = client.post("/api/compile/step", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["stage"] == "stage_2_parser"
    assert "output" in data
    assert "evaluation" in data
    
    logger.info("Stage 2 Parser step test succeeded.")
    return data["output"]


if __name__ == "__main__":
    logger.info("Running interactive endpoints integration tests...")
    
    # 1. Test Lexer Initial
    lexer_out_initial = test_lexer_initial_step()
    
    # 2. Test Lexer Refine (simulating user giving feedback)
    lexer_out_refined = test_lexer_refine_step(lexer_out_initial)
    
    # 3. Test Parser Step (using the refined Lexer output)
    parser_out = test_parser_step(lexer_out_refined)
    
    logger.info("All integration tests passed successfully!")

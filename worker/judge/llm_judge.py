"""LLM judge for evaluating traces."""

import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)


class LLMJudge:
    """LLM-based judge for trace evaluation."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "mock")
        self.model = "gpt-4o-mini"  # Using gpt-4o-mini for cost efficiency
        self.is_mock = self.api_key == "mock"
        
        if not self.is_mock:
            logger.info(f"Initializing LLM Judge with model: {self.model}")
        else:
            logger.info("Using mock LLM Judge (no API key provided)")
    
    def evaluate(self, prompt: str) -> dict:
        """
        Evaluate a trace using the LLM judge.
        
        Args:
            prompt: Formatted judge prompt
        
        Returns:
            Dictionary with scores and feedback
        """
        if self.is_mock:
            logger.info("Using mock evaluation")
            return self._mock_evaluation()
        
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            logger.info(f"Calling OpenAI API with model: {self.model}")
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert code reviewer evaluating developer debugging sessions. "
                            "Analyze the provided trace and respond ONLY with valid JSON in this exact format:\n"
                            "{\n"
                            '  "problem_understanding": <float 0-5>,\n'
                            '  "causal_linking": <float 0-5>,\n'
                            '  "experiment_design": <float 0-5>,\n'
                            '  "efficiency": <float 0-5>,\n'
                            '  "reproducibility": <float 0-5>,\n'
                            '  "safety_hygiene": <float 0-5>,\n'
                            '  "feedback_summary": "<string>"\n'
                            "}\n"
                            "Do not include any text outside the JSON."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            content = response.choices[0].message.content
            logger.info(f"Received response from OpenAI: {content[:200]}...")
            
            scores = json.loads(content)
            
            # Validate scores
            scores = self._validate_scores(scores)
            
            result = {
                "model": self.model,
                "model_version": response.model,
                "scores": scores,
                "feedback_summary": scores.pop("feedback_summary", "No feedback provided"),
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            logger.info(f"Successfully evaluated trace. Overall score: {scores.get('overall', 0):.2f}/5")
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            logger.error(f"Response content: {content if 'content' in locals() else 'N/A'}")
            # Try to extract JSON from markdown code blocks
            if 'content' in locals():
                try:
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        scores = json.loads(json_match.group(1))
                        scores = self._validate_scores(scores)
                        return {
                            "model": self.model,
                            "scores": scores,
                            "feedback_summary": scores.pop("feedback_summary", "No feedback provided")
                        }
                except Exception as inner_e:
                    logger.error(f"Failed to extract JSON from markdown: {inner_e}")
            return self._mock_evaluation()
        
        except Exception as e:
            logger.error(f"Error calling LLM judge: {e}", exc_info=True)
            # Return mock on error
            return self._mock_evaluation()
    
    def _mock_evaluation(self) -> dict:
        """Return mock evaluation for testing."""
        return {
            "model": "mock",
            "model_version": "mock-1.0",
            "scores": {
                "problem_understanding": 3.5,
                "causal_linking": 3.0,
                "experiment_design": 3.5,
                "efficiency": 3.0,
                "reproducibility": 4.0,
                "safety_hygiene": 4.5,
                "overall": 3.5
            },
            "feedback_summary": (
                "The developer demonstrated a systematic approach to debugging. "
                "Good reproducibility and safety practices. "
                "Could improve efficiency by reducing redundant test runs."
            )
        }
    
    def _validate_scores(self, scores: dict) -> dict:
        """Validate and clamp scores to 0-5 range."""
        score_fields = [
            "problem_understanding",
            "causal_linking",
            "experiment_design",
            "efficiency",
            "reproducibility",
            "safety_hygiene",
            "overall"
        ]
        
        for field in score_fields:
            if field in scores:
                score = float(scores[field])
                scores[field] = max(0.0, min(5.0, score))
        
        # Compute overall if missing
        if "overall" not in scores:
            weights = {
                "problem_understanding": 0.20,
                "causal_linking": 0.25,
                "experiment_design": 0.20,
                "efficiency": 0.15,
                "reproducibility": 0.10,
                "safety_hygiene": 0.10
            }
            overall = sum(
                scores.get(field, 0) * weight
                for field, weight in weights.items()
            )
            scores["overall"] = round(overall, 2)
        
        return scores


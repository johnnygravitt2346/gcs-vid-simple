#!/usr/bin/env python3
"""
Gemini AI Question Generator

Generates trivia questions using Google's Gemini AI model.
Integrates with the pipeline to create diverse, engaging content.
"""

import asyncio
import json
import logging
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import google.generativeai as genai
from google.cloud import aiplatform

logger = logging.getLogger(__name__)

@dataclass
class QuestionGenerationRequest:
    topic: str
    difficulty: str
    question_count: int
    category: str = "General"
    style: str = "engaging"
    target_audience: str = "general"

@dataclass
class GeneratedQuestion:
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    explanation: str
    category: str
    difficulty: str
    confidence_score: float

class GeminiQuestionGenerator:
    def __init__(self, api_key: str, project_id: str):
        self.api_key = api_key
        self.project_id = project_id
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Question templates for different categories
        self.question_templates = {
            "science": {
                "prompt": "Generate {count} engaging science trivia questions about {topic}. Each question should have 4 multiple choice options with one correct answer. Include explanations.",
                "examples": [
                    "What is the chemical symbol for gold? A) Au B) Ag C) Fe D) Cu",
                    "Which planet is known as the Red Planet? A) Venus B) Mars C) Jupiter D) Saturn"
                ]
            },
            "history": {
                "prompt": "Create {count} interesting history trivia questions about {topic}. Each question should have 4 multiple choice options with one correct answer. Include explanations.",
                "examples": [
                    "In what year did World War II end? A) 1943 B) 1944 C) 1945 D) 1946",
                    "Who was the first President of the United States? A) John Adams B) Thomas Jefferson C) George Washington D) Benjamin Franklin"
                ]
            },
            "general": {
                "prompt": "Generate {count} fun general knowledge trivia questions about {topic}. Each question should have 4 multiple choice options with one correct answer. Include explanations.",
                "examples": [
                    "What is the capital of France? A) London B) Berlin C) Paris D) Madrid",
                    "How many sides does a hexagon have? A) 5 B) 6 C) 7 D) 8"
                ]
            }
        }
    
    async def generate_questions(self, request: QuestionGenerationRequest) -> List[GeneratedQuestion]:
        """Generate trivia questions using Gemini AI."""
        logger.info(f"Generating {request.question_count} questions about {request.topic}")
        
        try:
            # Build the prompt
            template = self.question_templates.get(request.category.lower(), self.question_templates["general"])
            prompt = self._build_prompt(request, template)
            
            # Generate with Gemini
            response = await self._generate_with_gemini(prompt)
            
            # Parse the response
            questions = self._parse_gemini_response(response, request)
            
            # Validate and clean questions
            validated_questions = self._validate_questions(questions)
            
            logger.info(f"Successfully generated {len(validated_questions)} questions")
            return validated_questions
            
        except Exception as e:
            logger.error(f"Failed to generate questions: {e}")
            # Fallback to template questions
            return self._generate_fallback_questions(request)
    
    def _build_prompt(self, request: QuestionGenerationRequest, template: Dict[str, str]) -> str:
        """Build the prompt for Gemini."""
        prompt = f"""
{template['prompt'].format(count=request.question_count, topic=request.topic)}

Difficulty level: {request.difficulty}
Style: {request.style}
Target audience: {request.target_audience}

Please format your response as a JSON array with this structure:
[
  {{
    "question": "The question text?",
    "option_a": "First option",
    "option_b": "Second option", 
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_answer": "The correct option letter (A, B, C, or D)",
    "explanation": "Brief explanation of why this is correct",
    "category": "{request.category}",
    "difficulty": "{request.difficulty}"
  }}
]

Make sure each question is engaging, educational, and appropriate for the difficulty level.
The correct answer should be one of the four options provided.
"""
        return prompt
    
    async def _generate_with_gemini(self, prompt: str) -> str:
        """Generate content using Gemini AI."""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def _parse_gemini_response(self, response: str, request: QuestionGenerationRequest) -> List[GeneratedQuestion]:
        """Parse Gemini's response into structured questions."""
        try:
            # Extract JSON from response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON array found in response")
            
            json_str = response[json_start:json_end]
            questions_data = json.loads(json_str)
            
            questions = []
            for q_data in questions_data:
                question = GeneratedQuestion(
                    question=q_data.get("question", ""),
                    option_a=q_data.get("option_a", ""),
                    option_b=q_data.get("option_b", ""),
                    option_c=q_data.get("option_c", ""),
                    option_d=q_data.get("option_d", ""),
                    correct_answer=q_data.get("correct_answer", ""),
                    explanation=q_data.get("explanation", ""),
                    category=q_data.get("category", request.category),
                    difficulty=q_data.get("difficulty", request.difficulty),
                    confidence_score=0.8  # Default confidence
                )
                questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise
    
    def _validate_questions(self, questions: List[GeneratedQuestion]) -> List[GeneratedQuestion]:
        """Validate and clean generated questions."""
        validated = []
        
        for q in questions:
            # Basic validation
            if (q.question and q.option_a and q.option_b and 
                q.option_c and q.option_d and q.correct_answer and 
                q.explanation):
                
                # Clean up text
                q.question = q.question.strip()
                q.option_a = q.option_a.strip()
                q.option_b = q.option_b.strip()
                q.option_c = q.option_c.strip()
                q.option_d = q.option_d.strip()
                q.explanation = q.explanation.strip()
                
                # Normalize correct answer
                q.correct_answer = q.correct_answer.upper().strip()
                if q.correct_answer in ['A', 'B', 'C', 'D']:
                    validated.append(q)
                else:
                    logger.warning(f"Invalid correct answer format: {q.correct_answer}")
        
        return validated
    
    def _generate_fallback_questions(self, request: QuestionGenerationRequest) -> List[GeneratedQuestion]:
        """Generate fallback questions when Gemini fails."""
        logger.info("Using fallback question generation")
        
        fallback_questions = [
            GeneratedQuestion(
                question=f"What is the main topic of {request.topic}?",
                option_a="Option A",
                option_b="Option B", 
                option_c="Option C",
                option_d="Option D",
                correct_answer="A",
                explanation="This is a fallback question generated when AI generation fails.",
                category=request.category,
                difficulty=request.difficulty,
                confidence_score=0.5
            )
            for _ in range(request.question_count)
        ]
        
        return fallback_questions

# Example usage
async def main():
    # Initialize generator (you'll need to set your API key)
    generator = GeminiQuestionGenerator(
        api_key="your_gemini_api_key_here",
        project_id="mythic-groove-469801-b7"
    )
    
    # Generate questions
    request = QuestionGenerationRequest(
        topic="Space Exploration",
        difficulty="Medium",
        question_count=3,
        category="Science"
    )
    
    questions = await generator.generate_questions(request)
    
    for i, q in enumerate(questions, 1):
        print(f"\nQuestion {i}:")
        print(f"Q: {q.question}")
        print(f"A) {q.option_a}")
        print(f"B) {q.option_b}")
        print(f"C) {q.option_c}")
        print(f"D) {q.option_d}")
        print(f"Correct: {q.correct_answer}")
        print(f"Explanation: {q.explanation}")

if __name__ == "__main__":
    asyncio.run(main())

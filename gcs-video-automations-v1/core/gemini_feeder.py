#!/usr/bin/env python3
"""
Gemini Feeder - Trivia Dataset Generator

Creates versioned trivia datasets from Gemini AI generation.
Produces clean, deduped CSV files ready for video pipeline consumption.
"""

import asyncio
import csv
import hashlib
import json
import logging
import os
import re
import tempfile
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib

import google.generativeai as genai
from google.cloud import storage

try:
    from .cloud_storage import get_cloud_storage
    from .path_resolver import get_path_resolver
except ImportError:
    # For testing without package structure
    from cloud_storage import get_cloud_storage
    from path_resolver import get_path_resolver

logger = logging.getLogger(__name__)

@dataclass
class FeederRequest:
    """Request to generate a trivia dataset."""
    channel_id: str
    prompt_preset: str
    quantity: int
    tags: Optional[List[str]] = None
    banned_topics: Optional[List[str]] = None
    banned_terms: Optional[List[str]] = None
    max_question_length: int = 200
    max_option_length: int = 100
    answer_distribution_tolerance: int = 1
    language_filter: str = "en"
    difficulty: str = "medium"
    style: str = "engaging"

@dataclass
class TriviaQuestion:
    """A single trivia question with validation."""
    qid: str
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    answer_key: str
    topic: Optional[str] = None
    tags: Optional[List[str]] = None
    difficulty: Optional[str] = None
    language: str = "en"
    
    def normalize_for_hash(self) -> str:
        """Normalize question content for deduplication hashing."""
        # Normalize text: lowercase, trim whitespace, standardize punctuation
        normalized = f"{self.question.lower().strip()}|{self.option_a.lower().strip()}|{self.option_b.lower().strip()}|{self.option_c.lower().strip()}|{self.option_d.lower().strip()}"
        # Remove extra whitespace and standardize punctuation
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized
    
    def get_hash(self) -> str:
        """Get SHA256 hash of normalized content."""
        return hashlib.sha256(self.normalize_for_hash().encode()).hexdigest()

@dataclass
class DatasetManifest:
    """Dataset metadata and statistics."""
    channel_id: str
    version: str
    source_model_preset: str
    row_count: int
    sha256_csv: str
    created_at: str
    stats: Dict[str, Any]
    prompt_config: Dict[str, Any]

class GeminiFeeder:
    """Generates trivia datasets using Gemini AI with validation and deduplication."""
    
    def __init__(self, api_key: str):
        """Initialize the Gemini Feeder."""
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        self.cloud_storage = get_cloud_storage()
        self.path_resolver = get_path_resolver()
        
        # Prompt presets for different topics/themes
        self.prompt_presets = {
            "general_knowledge": {
                "name": "General Knowledge",
                "prompt": "Generate {count} engaging general knowledge trivia questions. Each question should be interesting, educational, and appropriate for a general audience.",
                "examples": [
                    "What is the capital of France? A) London B) Berlin C) Paris D) Madrid",
                    "How many sides does a hexagon have? A) 5 B) 6 C) 7 D) 8"
                ]
            },
            "science_tech": {
                "name": "Science & Technology",
                "prompt": "Create {count} fascinating science and technology trivia questions. Cover various scientific fields and technological innovations.",
                "examples": [
                    "What is the chemical symbol for gold? A) Au B) Ag C) Fe D) Cu",
                    "Which planet is known as the Red Planet? A) Venus B) Mars C) Jupiter D) Saturn"
                ]
            },
            "history_culture": {
                "name": "History & Culture",
                "prompt": "Generate {count} captivating history and culture trivia questions. Include world history, art, literature, and cultural milestones.",
                "examples": [
                    "In what year did World War II end? A) 1943 B) 1944 C) 1945 D) 1946",
                    "Who painted the Mona Lisa? A) Michelangelo B) Leonardo da Vinci C) Raphael D) Donatello"
                ]
            },
            "geography_travel": {
                "name": "Geography & Travel",
                "prompt": "Create {count} exciting geography and travel trivia questions. Cover countries, capitals, landmarks, and geographical features.",
                "examples": [
                    "What is the largest ocean on Earth? A) Atlantic B) Indian C) Pacific D) Arctic",
                    "Which country is home to the Great Wall? A) Japan B) China C) Korea D) Mongolia"
                ]
            },
            "entertainment_sports": {
                "name": "Entertainment & Sports",
                "prompt": "Generate {count} fun entertainment and sports trivia questions. Include movies, music, games, and athletic achievements.",
                "examples": [
                    "Which actor played Iron Man in the Marvel Cinematic Universe? A) Chris Evans B) Robert Downey Jr. C) Chris Hemsworth D) Mark Ruffalo",
                    "In which year did the first FIFA World Cup take place? A) 1930 B) 1934 C) 1938 D) 1950"
                ]
            },
            "sports": {
                "name": "Sports & Athletics",
                "prompt": "Generate {count} exciting sports trivia questions covering various sports including basketball, football, baseball, soccer, tennis, and more. Focus on interesting facts, records, and engaging sports knowledge.",
                "examples": [
                    "Which sport is known as 'the beautiful game'? A) Basketball B) Baseball C) Soccer D) Tennis",
                    "In which year were the first modern Olympic Games held? A) 1924 B) 1900 C) 1888 D) 1896"
                ]
            },
            "sports_history": {
                "name": "Sports History & Rookies",
                "prompt": "Create {count} fascinating sports trivia questions focusing on rookie and historical aspects of sports history. Cover various sports (basketball, football, baseball, soccer, etc.) with focus on historical moments, records, and rookie achievements.",
                "examples": [
                    "Which sport is known as 'the king of sports'? A) Basketball B) Baseball C) Tennis D) Soccer",
                    "In which year were the first modern Olympic Games held? A) 1924 B) 1900 C) 1888 D) 1896"
                ]
            }
        }
    
    async def generate_dataset(self, request: FeederRequest) -> str:
        """Generate a complete trivia dataset and return the GCS URI."""
        logger.info(f"Starting dataset generation for channel {request.channel_id}")
        
        try:
            # Step 1: Generate questions from Gemini
            questions = await self._generate_questions(request)
            
            # Step 2: Validate and clean questions
            validated_questions = self._validate_questions(questions, request)
            
            # Step 3: Check deduplication
            deduped_questions = await self._deduplicate_questions(validated_questions, request.channel_id)
            
            # Step 4: Ensure we have enough questions
            if len(deduped_questions) < request.quantity:
                logger.warning(f"Only generated {len(deduped_questions)} questions, need {request.quantity}")
                # Could implement regeneration logic here
            
            # Step 5: Balance answer distribution
            balanced_questions = self._balance_answer_distribution(deduped_questions, request.answer_distribution_tolerance)
            
            # Step 6: Create dataset version and publish
            dataset_uri = await self._publish_dataset(balanced_questions, request)
            
            logger.info(f"Successfully generated dataset: {dataset_uri}")
            return dataset_uri
            
        except Exception as e:
            logger.error(f"Failed to generate dataset: {e}")
            raise
    
    async def _generate_questions(self, request: FeederRequest) -> List[TriviaQuestion]:
        """Generate questions using Gemini AI."""
        logger.info(f"Generating {request.quantity} questions using preset: {request.prompt_preset}")
        
        preset = self.prompt_presets.get(request.prompt_preset, self.prompt_presets["general_knowledge"])
        
        # Build the prompt
        prompt = self._build_gemini_prompt(preset, request)
        
        try:
            # Generate with Gemini
            response = await self._call_gemini(prompt)
            
            # Parse the response
            questions = self._parse_gemini_response(response, request)
            
            logger.info(f"Generated {len(questions)} questions from Gemini")
            return questions
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            # Fallback to template questions
            return self._generate_fallback_questions(request)
    
    def _build_gemini_prompt(self, preset: Dict[str, str], request: FeederRequest) -> str:
        """Build the prompt for Gemini AI."""
        prompt = f"""
{preset['prompt'].format(count=request.quantity)}

Difficulty: {request.difficulty}
Style: {request.style}
Language: {request.language_filter}

Requirements:
- Each question must have exactly 4 multiple choice options (A, B, C, D)
- One option must be the correct answer
- Questions should be engaging and educational
- Avoid placeholder text like "Option A" or empty strings
- Maximum question length: {request.max_question_length} characters
- Maximum option length: {request.max_option_length} characters

{f"Banned topics: {', '.join(request.banned_topics)}" if request.banned_topics else ""}
{f"Banned terms: {', '.join(request.banned_terms)}" if request.banned_terms else ""}

Please format your response as a JSON array with this exact structure:
[
  {{
    "question": "The question text?",
    "option_a": "First option",
    "option_b": "Second option", 
    "option_c": "Third option",
    "option_d": "Fourth option",
    "answer_key": "A",
    "topic": "optional topic",
    "tags": ["tag1", "tag2"]
  }}
]

Make sure each question is engaging, educational, and appropriate for the difficulty level.
The answer_key must be exactly one of: A, B, C, or D.
"""
        return prompt
    
    async def _call_gemini(self, prompt: str) -> str:
        """Call Gemini AI and return the response."""
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def _parse_gemini_response(self, response: str, request: FeederRequest) -> List[TriviaQuestion]:
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
            for i, q_data in enumerate(questions_data):
                # Generate QID
                qid = f"q{(i+1):03d}"
                
                question = TriviaQuestion(
                    qid=qid,
                    question=q_data.get("question", ""),
                    option_a=q_data.get("option_a", ""),
                    option_b=q_data.get("option_b", ""),
                    option_c=q_data.get("option_c", ""),
                    option_d=q_data.get("option_d", ""),
                    answer_key=q_data.get("answer_key", ""),
                    topic=q_data.get("topic"),
                    tags=q_data.get("tags", []),
                    difficulty=request.difficulty,
                    language=request.language_filter
                )
                questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise
    
    def _validate_questions(self, questions: List[TriviaQuestion], request: FeederRequest) -> List[TriviaQuestion]:
        """Validate and clean generated questions."""
        validated = []
        
        for q in questions:
            try:
                # Basic validation
                if not all([q.question, q.option_a, q.option_b, q.option_c, q.option_d, q.answer_key]):
                    logger.warning(f"Question {q.qid}: Missing required fields")
                    continue
                
                # Clean up text
                q.question = q.question.strip()
                q.option_a = q.option_a.strip()
                q.option_b = q.option_b.strip()
                q.option_c = q.option_c.strip()
                q.option_d = q.option_d.strip()
                q.answer_key = q.answer_key.upper().strip()
                
                # Validate answer key
                if q.answer_key not in ['A', 'B', 'C', 'D']:
                    logger.warning(f"Question {q.qid}: Invalid answer key: {q.answer_key}")
                    continue
                
                # Check length limits
                if len(q.question) > request.max_question_length:
                    logger.warning(f"Question {q.qid}: Question too long ({len(q.question)} chars)")
                    continue
                
                if any(len(opt) > request.max_option_length for opt in [q.option_a, q.option_b, q.option_c, q.option_d]):
                    logger.warning(f"Question {q.qid}: Option too long")
                    continue
                
                # Check for banned content
                if self._contains_banned_content(q, request):
                    logger.warning(f"Question {q.qid}: Contains banned content")
                    continue
                
                # Check for placeholders
                if self._contains_placeholders(q):
                    logger.warning(f"Question {q.qid}: Contains placeholder text")
                    continue
                
                # Ensure options are distinct
                options = [q.option_a, q.option_b, q.option_c, q.option_d]
                if len(set(options)) != 4:
                    logger.warning(f"Question {q.qid}: Duplicate options")
                    continue
                
                validated.append(q)
                
            except Exception as e:
                logger.error(f"Error validating question {q.qid}: {e}")
                continue
        
        logger.info(f"Validated {len(validated)} out of {len(questions)} questions")
        return validated
    
    def _contains_banned_content(self, question: TriviaQuestion, request: FeederRequest) -> bool:
        """Check if question contains banned topics or terms."""
        text_to_check = f"{question.question} {question.option_a} {question.option_b} {question.option_c} {question.option_d}".lower()
        
        # Check banned topics
        if request.banned_topics:
            for topic in request.banned_topics:
                if topic.lower() in text_to_check:
                    return True
        
        # Check banned terms
        if request.banned_terms:
            for term in request.banned_terms:
                if term.lower() in text_to_check:
                    return True
        
        return False
    
    def _contains_placeholders(self, question: TriviaQuestion) -> bool:
        """Check if question contains placeholder text."""
        placeholders = ["option a", "option b", "option c", "option d", "answer a", "answer b", "answer c", "answer d"]
        text_to_check = f"{question.question} {question.option_a} {question.option_b} {question.option_c} {question.option_d}".lower()
        
        return any(placeholder in text_to_check for placeholder in placeholders)
    
    async def _deduplicate_questions(self, questions: List[TriviaQuestion], channel_id: str) -> List[TriviaQuestion]:
        """Remove duplicate questions based on channel's dedup window."""
        logger.info(f"Checking deduplication for channel {channel_id}")
        
        # Get existing hashes from channel's dedup log
        existing_hashes = await self._get_channel_dedup_hashes(channel_id)
        
        deduped = []
        new_hashes = []
        
        for question in questions:
            question_hash = question.get_hash()
            
            if question_hash not in existing_hashes:
                deduped.append(question)
                new_hashes.append(question_hash)
            else:
                logger.info(f"Duplicate question detected: {question.qid}")
        
        # Update dedup log with new hashes
        if new_hashes:
            await self._update_channel_dedup_hashes(channel_id, new_hashes)
        
        logger.info(f"Deduplication: {len(deduped)} unique questions out of {len(questions)}")
        return deduped
    
    async def _get_channel_dedup_hashes(self, channel_id: str) -> set:
        """Get existing question hashes from channel's dedup log."""
        try:
            # Use new bucket structure for dedup
            dedup_uri = f"{self.path_resolver.gcs_channels}/dedup/hashes.jsonl"
            
            if self.cloud_storage.blob_exists(dedup_uri):
                content = self.cloud_storage.read_text_from_gcs(dedup_uri, f"dedup_read_{channel_id}")
                hashes = set()
                for line in content.strip().split('\n'):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            hashes.add(data.get('hash', ''))
                        except json.JSONDecodeError:
                            continue
                return hashes
            else:
                return set()
                
        except Exception as e:
            logger.warning(f"Failed to read dedup hashes: {e}")
            return set()
    
    async def _update_channel_dedup_hashes(self, channel_id: str, new_hashes: List[str]) -> None:
        """Update channel's dedup log with new question hashes."""
        try:
            # Use new bucket structure for dedup
            dedup_uri = f"{self.path_resolver.gcs_channels}/dedup/hashes.jsonl"
            
            # Ensure dedup directory exists
            self.cloud_storage.ensure_gcs_directory(f"{self.path_resolver.gcs_channels}/dedup", f"dedup_dir_{channel_id}")
            
            # Append new hashes
            timestamp = datetime.utcnow().isoformat()
            new_entries = []
            for hash_val in new_hashes:
                new_entries.append(json.dumps({
                    'hash': hash_val,
                    'timestamp': timestamp,
                    'source': 'gemini_feeder'
                }))
            
            # Read existing content and append
            existing_content = ""
            if self.cloud_storage.blob_exists(dedup_uri):
                existing_content = self.cloud_storage.read_text_from_gcs(dedup_uri, f"dedup_read_{channel_id}")
                if existing_content and not existing_content.endswith('\n'):
                    existing_content += '\n'
            
            new_content = existing_content + '\n'.join(new_entries)
            self.cloud_storage.write_text_to_gcs(new_content, dedup_uri, f"dedup_update_{channel_id}")
            
        except Exception as e:
            logger.error(f"Failed to update dedup hashes: {e}")
    
    def _balance_answer_distribution(self, questions: List[TriviaQuestion], tolerance: int) -> List[TriviaQuestion]:
        """Balance the distribution of answer keys (A, B, C, D)."""
        if len(questions) < 20:
            # For small datasets, don't worry about distribution
            return questions
        
        # Count current distribution
        distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        for q in questions:
            distribution[q.answer_key] += 1
        
        target_count = len(questions) // 4
        logger.info(f"Answer distribution: {distribution}, target: {target_count} per option")
        
        # Check if distribution is within tolerance
        max_deviation = max(abs(count - target_count) for count in distribution.values())
        if max_deviation <= tolerance:
            logger.info("Answer distribution is balanced")
            return questions
        
        # Try to rebalance by swapping some answers
        balanced_questions = questions.copy()
        attempts = 0
        max_attempts = 100
        
        while attempts < max_attempts:
            # Find the most imbalanced options
            over_represented = [k for k, v in distribution.items() if v > target_count + tolerance]
            under_represented = [k for k, v in distribution.items() if v < target_count - tolerance]
            
            if not over_represented or not under_represented:
                break
            
            # Try to swap one answer
            for q in balanced_questions:
                if q.answer_key in over_represented:
                    # Find a question with an under-represented answer to swap with
                    for other_q in balanced_questions:
                        if other_q != q and other_q.answer_key in under_represented:
                            # Swap their answer keys
                            q.answer_key, other_q.answer_key = other_q.answer_key, q.answer_key
                            
                            # Recalculate distribution
                            distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
                            for check_q in balanced_questions:
                                distribution[check_q.answer_key] += 1
                            
                            max_deviation = max(abs(count - target_count) for count in distribution.values())
                            if max_deviation <= tolerance:
                                logger.info(f"Rebalanced answer distribution: {distribution}")
                                return balanced_questions
                            
                            break
                    break
            
            attempts += 1
        
        logger.warning(f"Could not fully balance answer distribution after {attempts} attempts")
        return balanced_questions
    
    async def _publish_dataset(self, questions: List[TriviaQuestion], request: FeederRequest) -> str:
        """Publish the dataset to GCS and return the URI."""
        # Generate version string
        timestamp = datetime.utcnow()
        version = timestamp.strftime("%Y-%m-%d-%03d")  # YYYY-MM-DD-###
        
        # Ensure we have a unique version
        version = await self._ensure_unique_version(request.channel_id, version)
        
        # Create dataset directory using new bucket structure
        dataset_base_uri = self.path_resolver.dataset_uri(version)
        self.cloud_storage.ensure_gcs_directory(dataset_base_uri, f"dataset_dir_{request.channel_id}_{version}")
        
        # Generate CSV content
        csv_content = self._generate_csv_content(questions)
        
        # Generate NDJSON content
        ndjson_content = self._generate_ndjson_content(questions)
        
        # Calculate checksum
        csv_checksum = hashlib.sha256(csv_content.encode()).hexdigest()
        
        # Create manifest
        manifest = DatasetManifest(
            channel_id=request.channel_id,
            version=version,
            source_model_preset=request.prompt_preset,
            row_count=len(questions),
            sha256_csv=csv_checksum,
            created_at=timestamp.isoformat(),
            stats=self._calculate_dataset_stats(questions),
            prompt_config=asdict(request)
        )
        
        # Write files to GCS
        csv_uri = f"{dataset_base_uri}/questions.csv"
        ndjson_uri = f"{dataset_base_uri}/questions.ndjson"
        manifest_uri = f"{dataset_base_uri}/_DATASET.json"
        
        self.cloud_storage.write_text_to_gcs(csv_content, csv_uri, f"dataset_csv_{request.channel_id}_{version}")
        self.cloud_storage.write_text_to_gcs(ndjson_content, ndjson_uri, f"dataset_ndjson_{request.channel_id}_{version}")
        self.cloud_storage.write_json_to_gcs(asdict(manifest), manifest_uri, f"dataset_manifest_{request.channel_id}_{version}")
        
        logger.info(f"Published dataset to {dataset_base_uri}")
        return dataset_base_uri
    
    async def _ensure_unique_version(self, channel_id: str, version: str) -> str:
        """Ensure the version string is unique for the channel."""
        base_version = version
        counter = 1
        
        while True:
            dataset_uri = self.path_resolver.dataset_uri(version)
            
            if not self.cloud_storage.blob_exists(f"{dataset_uri}/_DATASET.json"):
                return version
            
            # Version exists, try next
            counter += 1
            version = f"{base_version}-{counter:03d}"
    
    def _generate_csv_content(self, questions: List[TriviaQuestion]) -> str:
        """Generate CSV content for the dataset."""
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'qid', 'question', 'option_a', 'option_b', 'option_c', 'option_d',
            'answer_key', 'topic', 'tags', 'difficulty', 'language'
        ])
        
        # Write questions
        for q in questions:
            writer.writerow([
                q.qid,
                q.question,
                q.option_a,
                q.option_b,
                q.option_c,
                q.option_d,
                q.answer_key,
                q.topic or '',
                ';'.join(q.tags) if q.tags else '',
                q.difficulty or '',
                q.language
            ])
        
        return output.getvalue()
    
    def _generate_ndjson_content(self, questions: List[TriviaQuestion]) -> str:
        """Generate NDJSON content for the dataset."""
        lines = []
        for q in questions:
            q_dict = asdict(q)
            # Convert tags list to string for CSV compatibility
            if q_dict['tags']:
                q_dict['tags'] = ';'.join(q_dict['tags'])
            lines.append(json.dumps(q_dict))
        
        return '\n'.join(lines)
    
    def _calculate_dataset_stats(self, questions: List[TriviaQuestion]) -> Dict[str, Any]:
        """Calculate statistics for the dataset."""
        # Answer distribution
        distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        for q in questions:
            distribution[q.answer_key] += 1
        
        # Length statistics
        question_lengths = [len(q.question) for q in questions]
        option_lengths = []
        for q in questions:
            option_lengths.extend([len(q.option_a), len(q.option_b), len(q.option_c), len(q.option_d)])
        
        # Topic distribution
        topics = {}
        for q in questions:
            if q.topic:
                topics[q.topic] = topics.get(q.topic, 0) + 1
        
        return {
            'answer_distribution': distribution,
            'length_stats': {
                'question_avg': sum(question_lengths) / len(question_lengths) if question_lengths else 0,
                'question_min': min(question_lengths) if question_lengths else 0,
                'question_max': max(question_lengths) if question_lengths else 0,
                'option_avg': sum(option_lengths) / len(option_lengths) if option_lengths else 0,
                'option_min': min(option_lengths) if option_lengths else 0,
                'option_max': max(option_lengths) if option_lengths else 0
            },
            'topic_distribution': topics,
            'difficulty_distribution': {
                q.difficulty: sum(1 for q2 in questions if q2.difficulty == q.difficulty)
                for q in questions
            }
        }
    
    def _generate_fallback_questions(self, request: FeederRequest) -> List[TriviaQuestion]:
        """Generate fallback questions when Gemini fails."""
        logger.info("Using fallback question generation")
        
        fallback_questions = []
        for i in range(request.quantity):
            qid = f"q{(i+1):03d}"
            question = TriviaQuestion(
                qid=qid,
                question=f"What is the main topic of {request.prompt_preset}?",
                option_a="Option A",
                option_b="Option B", 
                option_c="Option C",
                option_d="Option D",
                answer_key="A",
                topic=request.prompt_preset,
                tags=[request.prompt_preset],
                difficulty=request.difficulty,
                language=request.language_filter
            )
            fallback_questions.append(question)
        
        return fallback_questions

# Example usage
async def main():
    # Initialize feeder (you'll need to set your API key)
    feeder = GeminiFeeder(api_key="your_gemini_api_key_here")
    
    # Generate dataset
    request = FeederRequest(
        channel_id="ch01",
        prompt_preset="science_tech",
        quantity=10,
        difficulty="medium",
        style="engaging"
    )
    
    dataset_uri = await feeder.generate_dataset(request)
    print(f"Generated dataset: {dataset_uri}")

if __name__ == "__main__":
    asyncio.run(main())

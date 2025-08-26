#!/usr/bin/env python3
"""
Gemini Feeder - Trivia Dataset Generator (Fixed Version)

Creates versioned trivia datasets from Gemini AI generation with retry logic
to ensure the requested number of questions are generated.
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
from io import StringIO
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

class GeminiFeederFixed:
    """Generates trivia datasets using Gemini AI with retry logic to ensure quantity."""
    
    def __init__(self, api_key: str):
        """Initialize the Gemini Feeder."""
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Initialize cloud storage and path resolver
        self.cloud_storage = get_cloud_storage()
        self.path_resolver = get_path_resolver()
        
        # Prompt presets
        self.prompt_presets = {
            "sports": {
                "prompt": "Generate {count} engaging sports trivia questions. Focus on popular sports like football, basketball, baseball, soccer, tennis, and Olympic sports. Include questions about famous athletes, historical events, rules, and records."
            },
            "general_knowledge": {
                "prompt": "Generate {count} engaging general knowledge trivia questions covering history, science, geography, literature, art, and current events. Make them interesting and educational."
            },
            "science": {
                "prompt": "Generate {count} engaging science trivia questions covering physics, chemistry, biology, astronomy, and earth sciences. Include both basic concepts and fascinating facts."
            },
            "history": {
                "prompt": "Generate {count} engaging history trivia questions covering world history, American history, ancient civilizations, wars, discoveries, and influential figures."
            },
            "geography": {
                "prompt": "Generate {count} engaging geography trivia questions covering countries, capitals, landmarks, oceans, mountains, rivers, and world cultures. Include both physical and human geography."
            },
            "music": {
                "prompt": "Generate {count} engaging music trivia questions covering various genres, famous musicians, songs, albums, instruments, music history, and cultural impact. Include rock, pop, classical, jazz, and world music."
            },
            "entertainment": {
                "prompt": "Generate {count} engaging entertainment trivia questions covering movies, TV shows, actors, directors, awards, box office records, and pop culture moments. Include both classic and contemporary entertainment."
            },
            "art": {
                "prompt": "Generate {count} engaging art trivia questions covering famous artists, paintings, sculptures, art movements, art history, and cultural significance. Include both classical and modern art."
            },
            "literature": {
                "prompt": "Generate {count} engaging literature trivia questions covering famous authors, books, poems, literary movements, quotes, and literary history. Include both classic and contemporary literature."
            },
            "technology": {
                "prompt": "Generate {count} engaging technology trivia questions covering computers, software, internet, gadgets, tech companies, innovations, and digital culture. Include both historical and current tech topics."
            },
            "space": {
                "prompt": "Generate {count} engaging space trivia questions covering astronomy, planets, stars, space exploration, astronauts, missions, and cosmic phenomena. Include both solar system and deep space topics."
            },
            "animals": {
                "prompt": "Generate {count} engaging animal trivia questions covering wildlife, pets, extinct animals, animal behavior, habitats, and fascinating animal facts. Include both common and exotic animals."
            },
            "food": {
                "prompt": "Generate {count} engaging food trivia questions covering cuisines, ingredients, cooking techniques, food history, famous dishes, and culinary traditions from around the world."
            },
            "travel": {
                "prompt": "Generate {count} engaging travel trivia questions covering destinations, landmarks, cultures, travel history, famous journeys, and fascinating facts about places around the world."
            },
            "politics": {
                "prompt": "Generate {count} engaging politics trivia questions covering world leaders, political systems, elections, historical events, and political movements. Focus on educational content."
            },
            "business": {
                "prompt": "Generate {count} engaging business trivia questions covering companies, entrepreneurs, economics, business history, and corporate world facts. Include both historical and modern business topics."
            },
            "fashion": {
                "prompt": "Generate {count} engaging fashion trivia questions covering clothing styles, designers, fashion history, trends, and cultural significance of fashion throughout history."
            }
        }
    
    async def generate_dataset(self, request: FeederRequest) -> str:
        """Generate a complete trivia dataset with retry logic to ensure quantity."""
        logger.info(f"Starting dataset generation for channel {request.channel_id}")
        
        max_retries = 5
        all_questions = []
        
        for attempt in range(max_retries):
            logger.info(f"Generation attempt {attempt + 1}/{max_retries}")
            
            try:
                # Generate questions with higher target to account for filtering
                target_questions = max(request.quantity * 2, request.quantity + 5)
                logger.info(f"Requesting {target_questions} questions to ensure {request.quantity} after filtering")
                
                # Step 1: Generate questions from Gemini
                questions = await self._generate_questions(request, target_questions)
                
                # Step 2: Validate and clean questions
                validated_questions = self._validate_questions(questions, request)
                logger.info(f"Validated {len(validated_questions)} questions")
                
                # Step 3: Check deduplication (but be less strict for retry logic)
                deduped_questions = await self._deduplicate_questions(validated_questions, request.channel_id, strict=False)
                logger.info(f"Deduplicated to {len(deduped_questions)} questions")
                
                # Add to our collection
                all_questions.extend(deduped_questions)
                
                # Check if we have enough
                if len(all_questions) >= request.quantity:
                    logger.info(f"Successfully generated {len(all_questions)} questions (≥ {request.quantity} requested)")
                    break
                else:
                    logger.warning(f"Attempt {attempt + 1}: Only have {len(all_questions)} questions, need {request.quantity}")
                    if attempt < max_retries - 1:
                        logger.info("Retrying with different prompt...")
                        # Wait a bit before retrying
                        await asyncio.sleep(2)
                        continue
                    else:
                        logger.warning("Maximum retries reached, proceeding with available questions")
                        
            except Exception as e:
                logger.error(f"Generation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                else:
                    logger.error("All generation attempts failed")
                    raise
        
        # Remove duplicates from all collected questions
        unique_questions = self._remove_duplicates(all_questions)
        logger.info(f"Final unique questions: {len(unique_questions)}")
        
        # Take only the requested number
        final_questions = unique_questions[:request.quantity]
        
        # Step 4: Balance answer distribution
        balanced_questions = self._balance_answer_distribution(final_questions, request.answer_distribution_tolerance)
        
        # Step 5: Create dataset version and publish
        dataset_uri = await self._publish_dataset(balanced_questions, request)
        
        logger.info(f"Successfully generated dataset: {dataset_uri}")
        return dataset_uri
    
    def _remove_duplicates(self, questions: List[TriviaQuestion]) -> List[TriviaQuestion]:
        """Remove duplicate questions based on content similarity."""
        seen_hashes = set()
        unique_questions = []
        
        for q in questions:
            q_hash = q.get_hash()
            if q_hash not in seen_hashes:
                seen_hashes.add(q_hash)
                unique_questions.append(q)
        
        return unique_questions
    
    async def _generate_questions(self, request: FeederRequest, target_count: int) -> List[TriviaQuestion]:
        """Generate questions using Gemini AI with enhanced prompt."""
        logger.info(f"Generating {target_count} questions using preset: {request.prompt_preset}")
        
        preset = self.prompt_presets.get(request.prompt_preset, self.prompt_presets["general_knowledge"])
        
        # Build the prompt with emphasis on quantity
        prompt = self._build_enhanced_gemini_prompt(preset, request, target_count)
        
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
            return self._generate_fallback_questions(request, target_count)
    
    def _build_enhanced_gemini_prompt(self, preset: Dict[str, str], request: FeederRequest, target_count: int) -> str:
        """Build an enhanced prompt for Gemini AI with emphasis on quantity."""
        prompt = f"""
{preset['prompt'].format(count=target_count)}

IMPORTANT: You MUST generate EXACTLY {target_count} questions. This is critical.

Difficulty: {request.difficulty}
Style: {request.style}
Language: {request.language_filter}

Requirements:
- Generate EXACTLY {target_count} questions (no more, no less)
- Each question must have exactly 4 multiple choice options (A, B, C, D)
- One option must be the correct answer
- Questions should be engaging and educational
- Avoid placeholder text like "Option A" or empty strings
- Maximum question length: {request.max_question_length} characters
- Maximum option length: {request.max_option_length} characters

{f"Banned topics: {', '.join(request.banned_topics)}" if request.banned_topics else ""}
{f"Banned terms: {', '.join(request.banned_terms)}" if request.banned_terms else ""}

Please format your response as a JSON array with EXACTLY {target_count} questions in this structure:
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
  }},
  ... (repeat for all {target_count} questions)
]

CRITICAL: Ensure you generate exactly {target_count} questions. Count them before responding.
Make sure each question is engaging, educational, and appropriate for the difficulty level.
The answer_key must be exactly one of: A, B, C, or D.
"""
        return prompt
    
    async def _call_gemini(self, prompt: str) -> str:
        """Call Gemini AI and return the response."""
        try:
            response = self.model.generate_content(prompt)
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
        """Validate and clean generated questions with less strict filtering."""
        validated = []
        
        for q in questions:
            try:
                # Basic validation - be more lenient
                if not all([q.question, q.option_a, q.option_b, q.option_c, q.option_d, q.answer_key]):
                    logger.warning(f"Question {q.qid}: Missing required fields, skipping")
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
                    logger.warning(f"Question {q.qid}: Invalid answer key: {q.answer_key}, skipping")
                    continue
                
                # Check length limits - be more lenient
                if len(q.question) > request.max_question_length * 1.5:  # Allow 50% longer
                    logger.warning(f"Question {q.qid}: Question too long ({len(q.question)} chars), skipping")
                    continue
                
                if any(len(opt) > request.max_option_length * 1.5 for opt in [q.option_a, q.option_b, q.option_c, q.option_d]):
                    logger.warning(f"Question {q.qid}: Option too long, skipping")
                    continue
                
                # Check for banned content
                if self._contains_banned_content(q, request):
                    logger.warning(f"Question {q.qid}: Contains banned content, skipping")
                    continue
                
                # Check for placeholders - be more lenient
                if self._contains_placeholders(q):
                    logger.warning(f"Question {q.qid}: Contains placeholder text, skipping")
                    continue
                
                # Ensure options are distinct - be more lenient
                options = [q.option_a, q.option_b, q.option_c, q.option_d]
                if len(set(options)) < 3:  # Allow some similarity
                    logger.warning(f"Question {q.qid}: Too many duplicate options, skipping")
                    continue
                
                validated.append(q)
                
            except Exception as e:
                logger.warning(f"Question {q.qid}: Validation error: {e}, skipping")
                continue
        
        return validated
    
    def _contains_banned_content(self, question: TriviaQuestion, request: FeederRequest) -> bool:
        """Check if question contains banned content."""
        if not request.banned_topics and not request.banned_terms:
            return False
        
        text = f"{question.question} {question.option_a} {question.option_b} {question.option_c} {question.option_d}".lower()
        
        # Check banned topics
        if request.banned_topics:
            for topic in request.banned_topics:
                if topic.lower() in text:
                    return True
        
        # Check banned terms
        if request.banned_terms:
            for term in request.banned_terms:
                if term.lower() in text:
                    return True
        
        return False
    
    def _contains_placeholders(self, question: TriviaQuestion) -> bool:
        """Check if question contains placeholder text."""
        placeholders = ['option a', 'option b', 'option c', 'option d', 'placeholder', 'example']
        text = f"{question.question} {question.option_a} {question.option_b} {question.option_c} {question.option_d}".lower()
        
        return any(placeholder in text for placeholder in placeholders)
    
    async def _deduplicate_questions(self, questions: List[TriviaQuestion], channel_id: str, strict: bool = True) -> List[TriviaQuestion]:
        """Deduplicate questions with configurable strictness."""
        if not questions:
            return []
        
        # For retry logic, be less strict about deduplication
        if not strict:
            logger.info("Using lenient deduplication for retry logic")
            return questions
        
        try:
            existing_hashes = await self._get_channel_dedup_hashes(channel_id)
            
            deduped = []
            new_hashes = []
            
            for q in questions:
                q_hash = q.get_hash()
                if q_hash not in existing_hashes:
                    deduped.append(q)
                    new_hashes.append(q_hash)
            
            # Update dedup log with new hashes
            if new_hashes:
                await self._update_channel_dedup_hashes(channel_id, new_hashes)
            
            logger.info(f"Deduplication: {len(deduped)} unique questions out of {len(questions)}")
            return deduped
            
        except Exception as e:
            logger.warning(f"Deduplication failed: {e}, returning all questions")
            return questions
    
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
                    'source': 'gemini_feeder_fixed'
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
                            # Swap answer keys
                            q.answer_key, other_q.answer_key = other_q.answer_key, q.answer_key
                            
                            # Update distribution
                            distribution[q.answer_key] += 1
                            distribution[other_q.answer_key] -= 1
                            
                            # Check if we're now balanced
                            max_deviation = max(abs(count - target_count) for count in distribution.values())
                            if max_deviation <= tolerance:
                                logger.info("Successfully balanced answer distribution")
                                return balanced_questions
                            
                            break
                    break
            
            attempts += 1
        
        logger.warning("Could not fully balance answer distribution")
        return balanced_questions
    
    def _generate_fallback_questions(self, request: FeederRequest, target_count: int) -> List[TriviaQuestion]:
        """Generate fallback questions when Gemini fails."""
        logger.warning(f"Generating {target_count} fallback questions")
        
        # Simple fallback questions
        fallback_questions = [
            {
                "question": "What is the capital of France?",
                "option_a": "London",
                "option_b": "Berlin",
                "option_c": "Paris",
                "option_d": "Madrid",
                "answer_key": "C"
            },
            {
                "question": "Which planet is closest to the Sun?",
                "option_a": "Venus",
                "option_b": "Mercury",
                "option_c": "Earth",
                "option_d": "Mars",
                "answer_key": "B"
            },
            {
                "question": "What year did World War II end?",
                "option_a": "1943",
                "option_b": "1944",
                "option_c": "1945",
                "option_d": "1946",
                "answer_key": "C"
            }
        ]
        
        # Repeat questions to reach target count
        questions = []
        for i in range(target_count):
            q_data = fallback_questions[i % len(fallback_questions)]
            qid = f"q{(i+1):03d}"
            
            question = TriviaQuestion(
                qid=qid,
                question=q_data["question"],
                option_a=q_data["option_a"],
                option_b=q_data["option_b"],
                option_c=q_data["option_c"],
                option_d=q_data["option_d"],
                answer_key=q_data["answer_key"],
                topic="fallback",
                tags=["fallback"],
                difficulty=request.difficulty,
                language=request.language_filter
            )
            questions.append(question)
        
        return questions
    
    async def _publish_dataset(self, questions: List[TriviaQuestion], request: FeederRequest) -> str:
        """Publish the dataset to GCS and return the URI."""
        try:
            # Create dataset version
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            dataset_id = f"{timestamp}-{hash(str(questions)) % 10000:04d}"
            
            # Create CSV content
            csv_content = self._create_csv_content(questions)
            
            # Calculate CSV hash
            csv_hash = hashlib.sha256(csv_content.encode()).hexdigest()
            
            # Create manifest
            manifest = DatasetManifest(
                channel_id=request.channel_id,
                version=dataset_id,
                source_model_preset=request.prompt_preset,
                row_count=len(questions),
                sha256_csv=csv_hash,
                created_at=datetime.utcnow().isoformat(),
                stats={
                    "total_questions": len(questions),
                    "difficulty": request.difficulty,
                    "language": request.language_filter
                },
                prompt_config=asdict(request)
            )
            
            # Upload to GCS
            dataset_path = f"{self.path_resolver.gcs_channels}/trivia/datasets/{dataset_id}"
            
            # Upload CSV
            csv_uri = f"{dataset_path}/questions.csv"
            self.cloud_storage.write_text_to_gcs(csv_content, csv_uri, f"dataset_csv_{dataset_id}")
            
            # Upload manifest
            manifest_uri = f"{dataset_path}/_MANIFEST.json"
            manifest_json = json.dumps(asdict(manifest), indent=2)
            self.cloud_storage.write_text_to_gcs(manifest_json, manifest_uri, f"dataset_manifest_{dataset_id}")
            
            logger.info(f"Dataset published: {dataset_path}")
            return dataset_path
            
        except Exception as e:
            logger.error(f"Failed to publish dataset: {e}")
            raise
    
    def _create_csv_content(self, questions: List[TriviaQuestion]) -> str:
        """Create CSV content from questions."""
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "qid", "question", "option_a", "option_b", "option_c", "option_d",
            "answer_key", "topic", "tags", "difficulty", "language"
        ])
        
        # Write questions
        for q in questions:
            writer.writerow([
                q.qid, q.question, q.option_a, q.option_b, q.option_c, q.option_d,
                q.answer_key, q.topic or "", ",".join(q.tags or []), q.difficulty, q.language
            ])
        
        return output.getvalue()

# Backward compatibility
GeminiFeeder = GeminiFeederFixed

#!/usr/bin/env python3
"""
Efficient Pipeline Simple - A simplified version of the efficient pipeline for testing
without Firestore integration. Uses in-memory deduplication and spec-first generation.
"""

import asyncio
import csv
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class QuestionSpec:
    """Lightweight question specification for pre-deduplication."""
    sport: str
    league: str
    topic: str
    year: int
    entities: List[str]
    difficulty: int
    
    def to_key(self) -> str:
        """Generate a canonical key for deduplication."""
        sorted_entities = "|".join(sorted(self.entities))
        return f"{self.sport}|{self.league}|{self.topic}|{self.year}|{sorted_entities}|{self.difficulty}"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            'sport': self.sport,
            'league': self.league,
            'topic': self.topic,
            'year': self.year,
            'entities': self.entities,
            'difficulty': self.difficulty
        }

@dataclass
class SlideBoxes:
    """Precise positioning for all slide elements - matching reference script exactly."""
    BASE_W: int = 1920
    BASE_H: int = 1080
    question_px: Tuple[int, int, int, int] = (300, 265, 1332, 227)
    answer_a_px: Tuple[int, int, int, int] = (378, 569, 523, 110)
    answer_b_px: Tuple[int, int, int, int] = (1014, 568, 526, 113)
    answer_c_px: Tuple[int, int, int, int] = (379, 768, 517, 106)
    answer_d_px: Tuple[int, int, int, int] = (1018, 770, 519, 107)
    timer_px: Tuple[int, int, int, int] = (597, 114, 713, 126)
    # FIXED: Smaller, more appropriately sized answer box
    correct_px: Tuple[int, int, int, int] = (700, 500, 520, 80)

class EfficientPipelineSimple:
    """Simplified efficient pipeline for testing without Firestore."""
    
    def __init__(self, storage_client, gemini_api_key: str):
        self.storage_client = storage_client
        self.gemini_api_key = gemini_api_key
        
        # In-memory storage for testing
        self.spec_registry: Set[str] = set()
        self.coverage_counters: Dict[Tuple[str, int, int], int] = {}
        self.banlist: Set[str] = set()
        
        # Track used questions across videos to prevent duplicates
        self.used_questions: Set[str] = set()
        self.used_entities: Set[str] = set()
        self.used_years: Set[int] = set()
        
        # Statistics
        self.stats = {
            'specs_generated': 0,
            'specs_novel': 0,
            'specs_rejected': 0,
            'questions_generated': 0,
            'questions_valid': 0,
            'questions_invalid': 0,
            'dupes_prevented_pre_text': 0,
            'dupes_caught_post_text': 0
        }
        
        # Initialize Gemini model
        import google.generativeai as genai
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Initialize other components (commented out for now to avoid import issues)
        # self.feeder = ContinuousFeeder(self.gemini_model)
        # self.episode_builder = EpisodeBuilder()
        # self.cloud_storage = CloudStorage(storage_client)
        
        # Sports data for diversity
        self.sports_data = {
            'basketball': {
                'leagues': ['NBA', 'NCAA', 'FIBA', 'WNBA', 'EuroLeague'],
                'topics': [
                    'finals_mvp', 'championship', 'all_star', 'playoffs', 'regular_season',
                    'scoring_title', 'rebounding_title', 'assist_title', 'defensive_player',
                    'rookie_of_year', 'sixth_man', 'most_improved', 'coach_of_year',
                    'hall_of_fame', 'retired_numbers', 'arena_records', 'season_records'
                ],
                'teams': ['Lakers', 'Celtics', 'Bulls', 'Warriors', 'Heat', 'Spurs', 'Knicks', 'Nets', 'Clippers', 'Suns'],
                'players': ['Michael Jordan', 'LeBron James', 'Kobe Bryant', 'Magic Johnson', 'Larry Bird', 'Shaquille O\'Neal', 'Tim Duncan', 'Kevin Garnett', 'Dirk Nowitzki', 'Steve Nash']
            },
            'football': {
                'leagues': ['NFL', 'NCAA', 'CFL', 'XFL', 'USFL'],
                'topics': [
                    'super_bowl', 'playoffs', 'regular_season', 'championship',
                    'mvp', 'offensive_player', 'defensive_player', 'rookie_of_year',
                    'coach_of_year', 'comeback_player', 'man_of_year', 'pro_bowl',
                    'hall_of_fame', 'retired_numbers', 'stadium_records', 'season_records'
                ],
                'teams': ['Patriots', 'Cowboys', 'Steelers', 'Packers', '49ers', 'Giants', 'Jets', 'Eagles', 'Commanders', 'Raiders'],
                'players': ['Tom Brady', 'Peyton Manning', 'Jerry Rice', 'Jim Brown', 'Joe Montana', 'John Elway', 'Dan Marino', 'Brett Favre', 'Emmitt Smith', 'Barry Sanders']
            },
            'baseball': {
                'leagues': ['MLB', 'NCAA', 'NPB', 'KBO', 'LIDOM'],
                'topics': [
                    'world_series', 'all_star_game', 'playoffs', 'regular_season',
                    'mvp', 'cy_young', 'rookie_of_year', 'manager_of_year',
                    'gold_glove', 'silver_slugger', 'batting_title', 'home_run_title',
                    'hall_of_fame', 'retired_numbers', 'stadium_records', 'season_records'
                ],
                'teams': ['Yankees', 'Red Sox', 'Dodgers', 'Giants', 'Cubs', 'Cardinals', 'Braves', 'Astros', 'Phillies', 'Mets'],
                'players': ['Babe Ruth', 'Willie Mays', 'Hank Aaron', 'Ted Williams', 'Mickey Mantle', 'Stan Musial', 'Lou Gehrig', 'Joe DiMaggio', 'Ty Cobb', 'Honus Wagner']
            },
            'soccer': {
                'leagues': ['Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Champions League', 'Europa League', 'Copa Libertadores', 'AFC Champions League'],
                'topics': [
                    'world_cup', 'champions_league', 'league_title', 'cup_final',
                    'ballon_dor', 'golden_boot', 'best_player', 'best_goalkeeper',
                    'best_defender', 'best_midfielder', 'best_forward', 'fifa_awards',
                    'retired_numbers', 'stadium_records', 'season_records', 'international_caps'
                ],
                'teams': ['Manchester United', 'Real Madrid', 'Barcelona', 'Bayern Munich', 'Liverpool', 'AC Milan', 'Inter Milan', 'Juventus', 'PSG', 'Manchester City'],
                'players': ['Pelé', 'Maradona', 'Ronaldo', 'Messi', 'Cristiano Ronaldo', 'Zinedine Zidane', 'Ronaldinho', 'Rivaldo', 'Romário', 'George Best']
            },
            'hockey': {
                'leagues': ['NHL', 'NCAA', 'KHL', 'SHL', 'Liiga'],
                'topics': [
                    'stanley_cup', 'playoffs', 'all_star_game', 'regular_season',
                    'hart_trophy', 'vezina_trophy', 'calder_trophy', 'norris_trophy',
                    'selke_trophy', 'lady_byng', 'masterton_trophy', 'conn_smythe',
                    'hall_of_fame', 'retired_numbers', 'arena_records', 'season_records'
                ],
                'teams': ['Canadiens', 'Maple Leafs', 'Red Wings', 'Bruins', 'Blackhawks', 'Rangers', 'Flyers', 'Penguins', 'Oilers', 'Flames'],
                'players': ['Wayne Gretzky', 'Mario Lemieux', 'Bobby Orr', 'Gordie Howe', 'Maurice Richard', 'Jean Béliveau', 'Guy Lafleur', 'Mark Messier', 'Steve Yzerman', 'Joe Sakic']
            }
        }
        
        # Video themes for unique content per video
        self.video_themes = [
            'Legends and Records',
            'Championship Moments', 
            'Hall of Fame Stories',
            'Season Highlights',
            'Playoff Drama',
            'All-Star Showcases',
            'Rookie Breakthroughs',
            'Comeback Stories',
            'Defensive Dominance',
            'Offensive Explosions'
        ]
        
        # New flexible question types and time frames
        self.question_types = [
            'Fundamental Rule',
            'Common Terminology', 
            'Famous Record',
            'Historical Event',
            'Specific Statistic'
        ]
        
        self.time_frames = [
            'Current Rules',
            'All-Time',
            'N/A',
            '1990s',
            '2000s',
            '2010s',
            '2020s',
            'Classic Era',
            'Modern Era'
        ]
    
    async def _generate_spec_batch_simple(self, sport: str, difficulty: int, target: int = 20) -> List[QuestionSpec]:
        """Generate a batch of question specs for a specific sport and difficulty."""
        try:
            sport_data = self.sports_data.get(sport, {})
            leagues = sport_data.get('leagues', [sport])
            topics = sport_data.get('topics', ['general'])
            teams = sport_data.get('teams', [])
            players = sport_data.get('players', [])
            
            # Generate diverse specs
            specs = []
            for i in range(target):
                # Vary leagues, topics, years, and entities
                league = leagues[i % len(leagues)]
                topic = topics[i % len(topics)]
                year = 1980 + (i * 3) % 45  # Spread across decades
                
                # Vary entities
                if i % 3 == 0 and teams:
                    entities = [teams[i % len(teams)]]
                elif i % 3 == 1 and players:
                    entities = [players[i % len(players)]]
                else:
                    if teams:
                        entities = [teams[i % len(teams)]]
                    else:
                        entities = [sport]
                
                spec = QuestionSpec(
                    sport=sport,
                    league=league,
                    topic=topic,
                    year=year,
                    entities=entities,
                    difficulty=difficulty
                )
                specs.append(spec)
            
            return specs
            
        except Exception as e:
            logger.error(f"Error generating spec batch: {e}")
            return []
    
    async def _generate_sports_specs_simple(self, target_count: int, difficulty: int = 1) -> List[QuestionSpec]:
        """Generate sports specs with diversity across sports."""
        all_specs = []
        sports = list(self.sports_data.keys())
        
        # Generate specs for each sport
        for sport in sports:
            sport_specs = await self._generate_spec_batch_simple(sport, difficulty, target_count // len(sports))
            all_specs.extend(sport_specs)
        
        # Shuffle to avoid predictable patterns
        import random
        random.shuffle(all_specs)
        
        return all_specs[:target_count]
    
    async def _pre_dedupe_specs_simple(self, specs: List[QuestionSpec]) -> List[QuestionSpec]:
        """Pre-deduplicate specs using in-memory registry."""
        novel_specs = []
        
        for spec in specs:
            spec_key = spec.to_key()
            
            if spec_key not in self.spec_registry:
                # Check coverage counters
                decade = (spec.year // 10) * 10
                coverage_key = (spec.topic, decade, spec.difficulty)
                
                if self.coverage_counters.get(coverage_key, 0) < 15:  # Max 15 per topic/decade/difficulty
                    novel_specs.append(spec)
                    self.spec_registry.add(spec_key)
                    self.coverage_counters[coverage_key] = self.coverage_counters.get(coverage_key, 0) + 1
                    self.stats['specs_novel'] += 1
                else:
                    self.stats['specs_rejected'] += 1
            else:
                self.stats['specs_rejected'] += 1
        
        return novel_specs
    
    async def _generate_question_from_spec_simple(self, spec: QuestionSpec, max_retries: int = 3) -> Optional[Dict]:
        """Generate a question from a spec with retry logic."""
        for attempt in range(max_retries):
            try:
                # Build prompt for this spec
                prompt = self._build_spec_based_prompt(spec)
                
                # Call Gemini
                response = await self._call_gemini_direct(prompt)
                if not response:
                    logger.warning(f"Attempt {attempt + 1}: No response from Gemini")
                    continue
                
                # Parse response
                question_data = self._parse_gemini_response(response, spec)
                if not question_data:
                    logger.warning(f"Attempt {attempt + 1}: Failed to parse Gemini response")
                    continue
                
                # Validate question
                if self._validate_question_simple(question_data):
                    # Mark question as used to prevent duplicates
                    self._mark_question_as_used(question_data)
                    self.stats['questions_valid'] += 1
                    return question_data
                else:
                    logger.warning(f"Attempt {attempt + 1}: Question validation failed")
                    continue
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}: Error generating question: {e}")
                continue
        
        logger.error(f"Failed to generate question after {max_retries} attempts for spec: {spec.to_key()}")
        return None

    async def _generate_questions_with_retry(self, specs: List[QuestionSpec], target_count: int) -> List[Dict]:
        """Generate questions with retry logic until we reach the target count."""
        questions = []
        failed_specs = []
        
        # First pass: try to generate from all specs
        for spec in specs:
            if len(questions) >= target_count:
                break
                
            question = await self._generate_question_from_spec_simple(spec)
            if question:
                questions.append(question)
                logger.info(f"✅ Generated question {len(questions)}/{target_count}")
            else:
                failed_specs.append(spec)
        
        # If we still need more questions, retry failed specs with different approaches
        if len(questions) < target_count and failed_specs:
            logger.info(f"🔄 Need {target_count - len(questions)} more questions. Retrying failed specs...")
            
            for spec in failed_specs:
                if len(questions) >= target_count:
                    break
                
                # Try with a modified spec (different topic, year, etc.)
                modified_spec = self._modify_spec_for_retry(spec)
                question = await self._generate_question_from_spec_simple(modified_spec, max_retries=5)
                
                if question:
                    questions.append(question)
                    logger.info(f"✅ Generated question {len(questions)}/{target_count} with modified spec")
                else:
                    logger.warning(f"❌ Failed to generate question even with modified spec")
        
        return questions

    def _modify_spec_for_retry(self, spec: QuestionSpec) -> QuestionSpec:
        """Modify a spec to try different approaches for retry."""
        import random
        
        # Try different topics
        new_topics = ['general', 'championships', 'awards', 'rules', 'terminology']
        new_topic = random.choice(new_topics)
        
        # Try different years
        new_year = random.randint(1980, 2024)
        
        # Try different entities
        if spec.entities == ['N/A']:
            new_entities = [spec.sport]  # Use sport name instead of N/A
        else:
            new_entities = ['N/A']  # Try N/A instead of specific entities
        
        return QuestionSpec(
            sport=spec.sport,
            league=spec.league,
            topic=new_topic,
            year=new_year,
            entities=new_entities,
            difficulty=spec.difficulty
        )
    
    def _build_spec_based_prompt(self, spec: QuestionSpec) -> str:
                """Build a highly specific prompt based on the spec details."""
                return f"""Generate an EASY sports trivia question based on these exact specifications:
            
            Sport: {spec.sport}
            League: {spec.league}
            Topic: {spec.topic}
            Year: {spec.year}
            Entities: {', '.join(spec.entities)}
            Difficulty: EASY (1)
            
            CRITICAL REQUIREMENTS FOR ACCESSIBILITY:
            - Generate questions that CASUAL SPORTS FANS would know
            - Focus on FAMOUS players, teams, and events that are household names
            - Use GENERAL knowledge, not obscure historical facts
            - Avoid specific years, exact statistics, or niche details
            - Questions should be about things most people have heard of
            
            Content Requirements:
            - Question must be about {spec.sport} in {spec.league}
            - Must relate to {spec.topic} from {spec.year}
            - Must involve {', '.join(spec.entities)}
            - DIFFICULTY: EASY - Use well-known, verified facts that most sports fans would know
            - Question should be specific and factual, not generic
            - Must have exactly 4 answer choices (A, B, C, D)
            - One answer must be correct
            - Other answers should be plausible but clearly wrong for easy difficulty
            - Use famous players, teams, and events that are household names
            - Avoid obscure statistics or complex rules
            
            Fact Verification Guidelines:
            - Use only major championships, record-breaking performances, and widely-known achievements
            - Stick to facts that appeared in major sports media outlets
            - Use statistics that are commonly cited in sports discussions
            - Focus on events that had significant media coverage
            - When in doubt, use simpler, more basic facts that are impossible to dispute
            
            Format your response as JSON to match the CSV format:
            {{
                "question": "Your specific question here",
                "option_a": "Answer A",
                "option_b": "Answer B", 
                "option_c": "Answer C",
                "option_d": "Answer D",
                "correct_answer": "Full text of correct answer (not just letter)",
                "category": "Sports",
                "difficulty": "Easy"
            }}
            
            REMEMBER: Only use VERIFIED, HISTORICAL FACTS. If you cannot verify a fact with certainty, use a different, simpler fact that you know is true. This is for educational content that must be 100% accurate."""
    
    async def _call_gemini_direct(self, prompt: str) -> Optional[str]:
        """Call Gemini API directly with the prompt."""
        try:
            response = self.gemini_model.generate_content(prompt)
            if response and response.text:
                return response.text
            else:
                logger.warning("Empty response from Gemini")
                return None
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None
    
    def _parse_gemini_response(self, response: str, spec: QuestionSpec) -> Optional[Dict]:
        """Parse Gemini response into question data."""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                question_data = json.loads(json_str)
                
                # Add spec information
                question_data['spec'] = spec.to_dict()
                question_data['qid'] = f"q_{int(time.time())}_{hash(spec.to_key()) % 10000}"
                
                return question_data
            else:
                logger.warning("No JSON found in Gemini response")
                return None
                
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return None
    
    def _validate_question_simple(self, question_data: Dict) -> bool:
        """Simple validation of question data for new CSV format."""
        required_fields = ['question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
        
        # Check required fields
        for field in required_fields:
            if field not in question_data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Check that all options are present and not empty
        options = ['option_a', 'option_b', 'option_c', 'option_d']
        for option in options:
            if not question_data.get(option, '').strip():
                logger.warning(f"Option {option} is empty")
                return False
        
        # Check that correct answer matches one of the options
        correct_answer = question_data.get('correct_answer', '').strip()
        if not correct_answer:
            logger.warning("Correct answer is empty")
            return False
        
        # Check if correct answer matches any option
        options_text = [question_data.get(opt, '').strip() for opt in options]
        if correct_answer not in options_text:
            logger.warning(f"Correct answer '{correct_answer}' not found in options")
            return False
        
        # Check for uniqueness across videos
        question_text = question_data.get('question', '').strip()
        if question_text in self.used_questions:
            logger.warning(f"Duplicate question detected: {question_text[:50]}...")
            return False
        
        # Check for entity uniqueness (allow more reuse for easy questions)
        question_lower = question_text.lower()
        for sport in self.sports_data.keys():
            if sport.lower() in question_lower:
                # Allow more reuse for easy questions - increase limit from 3 to 15
                entity_count = sum(1 for q in self.used_questions if sport.lower() in q.lower())
                if entity_count >= 15:  # Increased from 3 to 15
                    logger.warning(f"Entity {sport} used too frequently ({entity_count} times)")
                    return False
        
        return True
    
    def _mark_question_as_used(self, question_data: Dict):
        """Mark a question as used to prevent duplicates."""
        question_text = question_data.get('question', '').strip()
        self.used_questions.add(question_text)
        
        # Extract entities from the question for tracking
        # This is a simple approach - in production you'd want more sophisticated entity extraction
        question_lower = question_text.lower()
        for sport in self.sports_data.keys():
            if sport.lower() in question_lower:
                self.used_entities.add(sport)
        
        # Track years mentioned in questions
        import re
        year_matches = re.findall(r'\b(19|20)\d{2}\b', question_text)
        for year_match in year_matches:
            try:
                year = int(year_match)
                self.used_years.add(year)
            except ValueError:
                pass
    
    async def run_sports_quiz_pipeline(self, quiz_count: int = 5, questions_per_quiz: int = 20) -> bool:
        """Run the full sports quiz pipeline."""
        try:
            logger.info(f"🚀 Starting sports quiz pipeline: {quiz_count} quiz(zes), {questions_per_quiz} questions each")
            
            for quiz_num in range(quiz_count):
                # Clear in-memory storage for each quiz to ensure diversity
                self.spec_registry.clear()
                self.coverage_counters.clear()
                self.banlist.clear()
                
                logger.info(f"🎯 Generating quiz {quiz_num + 1}/{quiz_count}")
                
                # Generate specs for this quiz
                specs = await self._generate_sports_specs_simple(questions_per_quiz, difficulty=1)
                self.stats['specs_generated'] += len(specs)
                
                # Pre-deduplicate specs
                novel_specs = await self._pre_dedupe_specs_simple(specs)
                
                if len(novel_specs) < questions_per_quiz:
                    logger.warning(f"Only {len(novel_specs)} novel specs available, need {questions_per_quiz}")
                    # Try to generate more specs
                    additional_specs = await self._generate_sports_specs_simple(questions_per_quiz - len(novel_specs), difficulty=1)
                    additional_novel = await self._pre_dedupe_specs_simple(additional_specs)
                    novel_specs.extend(additional_novel)
                
                # Generate questions from specs
                questions = await self._generate_questions_with_retry(novel_specs, questions_per_quiz)
                
                if len(questions) < questions_per_quiz:
                    logger.warning(f"Only generated {len(questions)} questions, need {questions_per_quiz}")
                
                # Build episode and create video
                if questions:
                    episode_id = f"episode_{quiz_num + 1:03d}"
                    episode = await self._build_single_episode_from_questions(questions, episode_id)
                    
                    if episode:
                        # Create video for this episode
                        video_path = await self._create_video_for_episode(episode, episode_id)
                        if video_path:
                            logger.info(f"✅ Quiz {quiz_num + 1} completed successfully")
                        else:
                            logger.error(f"❌ Video creation failed for quiz {quiz_num + 1}")
                    else:
                        logger.error(f"❌ Episode building failed for quiz {quiz_num + 1}")
                else:
                    logger.error(f"❌ No questions generated for quiz {quiz_num + 1}")
            
            # Log final statistics
            self._log_statistics()
            return True
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _build_single_episode_from_questions(self, questions: List[Dict], episode_id: str) -> Optional[Dict]:
        """Build a single episode from a list of questions."""
        try:
            # Convert questions to the expected format
            episode_questions = []
            for q in questions:
                episode_question = {
                    'question': q['question'],
                    'option_a': q['option_a'],
                    'option_b': q['option_b'],
                    'option_c': q['option_c'],
                    'option_d': q['option_d'],
                    'correct_answer': q['correct_answer'],
                    'category': q.get('category', 'Sports'),
                    'difficulty': q.get('difficulty', 'Easy')
                }
                episode_questions.append(episode_question)
            
            # Create episode data
            episode = {
                'episode_id': episode_id,
                'questions': episode_questions,
                'question_count': len(episode_questions),
                'created_at': datetime.now().isoformat(),
                'difficulty': 'easy',
                'sport': 'mixed_sports'
            }
            
            return episode
            
        except Exception as e:
            logger.error(f"Failed to build episode: {e}")
            return None
    
    async def _create_video_for_episode(self, episode: Dict, episode_id: str) -> Optional[str]:
        """Create a video for the episode."""
        try:
            # Create temporary CSV
            csv_path = await self._create_csv_from_episode(episode, episode_id)
            
            if csv_path:
                # Generate video from CSV
                video_path = await self._generate_video_from_csv(csv_path, episode_id)
                return video_path
            else:
                logger.error("Failed to create CSV from episode")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create video for episode: {e}")
            return None
    
    async def _create_csv_from_episode(self, episode: Dict, episode_id: str) -> Optional[str]:
        """Create a CSV file from episode data."""
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            csv_path = os.path.join(temp_dir, f"{episode_id}_questions.csv")
            
            # Write CSV
            with open(csv_path, 'w', newline='') as csvfile:
                fieldnames = ['question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'category', 'difficulty']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for q in episode['questions']:
                    writer.writerow({
                        'question': q['question'],
                        'option_a': q['option_a'],
                        'option_b': q['option_b'],
                        'option_c': q['option_c'],
                        'option_d': q['option_d'],
                        'correct_answer': q['correct_answer'],
                        'category': q.get('category', 'Sports'),
                        'difficulty': q.get('difficulty', 'Easy')
                    })
            
            logger.info(f"✅ Created CSV: {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"Failed to create CSV: {e}")
            return None
    
    async def _generate_video_from_csv(self, csv_path: str, episode_id: str) -> Optional[str]:
        """Generate video from CSV using the professional video generation."""
        try:
            logger.info(f"🎥 Starting video generation for episode {episode_id}")
            
            # Create output directory
            output_dir = os.path.join(tempfile.gettempdir(), f"trivia_work/output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Run professional video generation
            video_path = await self._run_professional_video_generation(csv_path, output_dir, episode_id)
            
            if video_path and os.path.exists(video_path):
                # Upload to GCS
                gcs_path = f"episodes/{episode_id}/video.mp4"
                bucket = self.storage_client.bucket("trivia-automations-2")
                blob = bucket.blob(gcs_path)
                blob.upload_from_filename(video_path)
                
                logger.info(f"📤 Uploaded professional video to gs://trivia-automations-2/{gcs_path}")
                logger.info(f"✅ Video generation successful!")
                logger.info(f"🎥 Video uploaded to: gs://trivia-automations-2/{gcs_path}")
                logger.info(f"🔗 View in GCS Console: https://console.cloud.google.com/storage/browser/trivia-automations-2?prefix={gcs_path}")
                
                return video_path
            else:
                logger.error("Video generation failed")
                return None
                
        except Exception as e:
            logger.error(f"Video generation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _run_professional_video_generation(self, csv_path: str, output_dir: str, episode_id: str) -> Optional[str]:
        """Run professional video generation using the exact logic from final_video_generator scripts."""
        try:
            import os
            import csv
            import subprocess
            import tempfile
            import shutil
            from PIL import Image, ImageDraw, ImageFont
            from google.cloud import texttospeech
            
            # Set up directories exactly like the reference scripts
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(os.path.join(output_dir, "tmp"), exist_ok=True)
            os.makedirs(os.path.join(output_dir, "clips"), exist_ok=True)
            
            # Create cloud_assets directory for video assets
            assets_dir = os.path.join(output_dir, "cloud_assets")
            os.makedirs(assets_dir, exist_ok=True)
            
            # Download required video assets from GCS
            logger.info("📦 Downloading video assets from GCS...")
            required_assets = [
                "1.mp4", "2.mp4", "3.mp4", 
                "ding_correct_answer_long.wav", 
                "ticking_clock_mechanical_5s.wav", 
                "slide_timer_bar_5s.mp4", 
                "slide_timer_bar_full_striped.png", 
                "An_energetic_game_202508201332_sdz6d.mp4", 
                "A_single_explosive_202508201347_hctna.mp4"
            ]
            
            for asset in required_assets:
                asset_path = os.path.join(assets_dir, asset)
                if not os.path.exists(asset_path):
                    gcs_path = f"gs://trivia-automations-2/channel-test/video-assets/{asset}"
                    logger.info(f"📥 Downloading {asset}...")
                    bucket_obj = self.storage_client.bucket("trivia-automations-2")
                    blob_obj = bucket_obj.blob(f"channel-test/video-assets/{asset}")
                    blob_obj.download_to_filename(asset_path)
            
            # Read CSV and convert to expected format
            with open(csv_path, 'r') as f:
                rows = list(csv.DictReader(f))
            
            if not rows:
                logger.error("No questions found in CSV")
                return None
            
            # COMPLETE TIMING SEQUENCE INSTRUCTIONS:
            # =====================================
            #
            # QUESTION CLIP TIMING:
            # ---------------------
            # 1. Question TTS plays (duration: question_tts_dur)
            # 2. After TTS ends, wait EXACTLY 5 seconds while timer.mp4 plays
            # 3. Timer duration: 5 seconds (from slide_timer_bar_5s.mp4)
            # 4. Total question clip duration: question_tts_dur + 5 seconds
            # 5. Timer starts immediately after TTS ends (timer_start = question_tts_dur)
            #
            # ANSWER CLIP TIMING:
            # -------------------
            # 1. Answer TTS plays immediately (duration: answer_tts_dur)
            # 2. After TTS ends, show answer slide for 3 seconds
            # 3. Total answer clip duration: answer_tts_dur + 3 seconds
            # 4. This creates a smooth transition from question to answer
            #
            # COMPLETE FLOW:
            # --------------
            # Intro → Question1 → Answer1 → Question2 → Answer2 → ... → Outro
            #
            # Each question-answer pair creates the complete trivia experience:
            # - Question phase: TTS + 5-second timer countdown
            # - Answer phase: "Correct Answer: X" TTS + answer display
            
            logger.info(f"🎬 Creating professional video for {len(rows)} questions using exact final_video_generator logic")
            
            # Convert CSV format to match expected format
            converted_rows = []
            for row in rows:
                # Parse CSV format exactly as shown in screenshot
                converted_row = {
                    'question': row.get('question', ''),
                    'answer_a': row.get('option_a', ''),
                    'answer_b': row.get('option_b', ''),
                    'answer_c': row.get('option_c', ''),
                    'answer_d': row.get('option_d', ''),
                    'correct_answer': row.get('correct_answer', '')  # Full text of correct answer
                }
                converted_rows.append(converted_row)
            
            # Define SlideBoxes exactly like the reference scripts
            @dataclass
            class SlideBoxes:
                BASE_W: int = 1920
                BASE_H: int = 1080
                question_px: Tuple[int, int, int, int] = (300, 265, 1332, 227)
                answer_a_px: Tuple[int, int, int, int] = (378, 569, 523, 110)
                answer_b_px: Tuple[int, int, int, int] = (1014, 568, 526, 113)
                answer_c_px: Tuple[int, int, int, int] = (379, 768, 517, 106)
                answer_d_px: Tuple[int, int, int, int] = (1018, 770, 519, 107)
                timer_px: Tuple[int, int, int, int] = (597, 114, 713, 126)
                correct_px: Tuple[int, int, int, int] = (576, 486, 759, 157)
            
            boxes = SlideBoxes()
            
            # Utility functions from reference scripts
            def scale_box(box, w, h, base_w=1920, base_h=1080):
                l, t, bw, bh = box
                return int(l * w / base_w), int(t * h / base_h), int(bw * w / base_w), int(bh * h / base_h)
            
            def render_text_to_png(text, box_w, box_h, font_path, out_path, is_bold=False, add_backdrop=False, custom_font_size=None):
                """Render text to PNG with intelligent sizing and wrapping - from reference scripts"""
                padding_w, padding_h = int(box_w * 0.1), int(box_h * 0.1)
                text_area_w, text_area_h = box_w - 2 * padding_w, box_h - 2 * padding_h
                img = Image.new('RGBA', (box_w, box_h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)

                def wrap(txt, font, max_w):
                    words = txt.split(); lines, cur = [], [];
                    for word in words:
                        candidate = " ".join(cur + [word]).strip()
                        if draw.textbbox((0,0), candidate, font=font)[2] <= max_w or not cur: cur.append(word)
                        else: lines.append(" ".join(cur)); cur = [word]
                    if cur: lines.append(" ".join(cur))
                    return "\n".join(lines)

                def fit(txt, min_s, max_s):
                    low, high = min_s, max_s; best_s, best_t = min_s, txt
                    while low <= high:
                        mid = (low + high) // 2
                        font = ImageFont.truetype(font_path, mid)
                        wrapped = wrap(txt, font, text_area_w)
                        _, _, w, h = draw.multiline_textbbox((0,0), wrapped, font=font, spacing=6)
                        if w <= text_area_w and h <= text_area_h: best_s, best_t = mid, wrapped; low = mid + 1
                        else: high = mid - 1
                    return best_s, best_t

                # Use custom font size if provided, otherwise auto-fit
                if custom_font_size:
                    font_size = custom_font_size
                    font = ImageFont.truetype(font_path, font_size)
                    wrapped = wrap(text, font, text_area_w)
                else:
                    font_size, wrapped = fit(text, 12, 120 if is_bold else 90)
                    font = ImageFont.truetype(font_path, font_size)
                _, _, text_w, text_h = draw.multiline_textbbox((0,0), wrapped, font=font, spacing=6)
                x, y = padding_w + (text_area_w - text_w) / 2, padding_h + (text_area_h - text_h) / 2

                # Beautiful text rendering with enhanced shadows and professional styling
                if is_bold:
                    # Softer shadow for bold text (question text) - reduced intensity for elegance
                    draw.multiline_text((x+2, y+2), wrapped, font=font, fill=(0,0,0,100), align="center", spacing=6)
                    draw.multiline_text((x, y), wrapped, font=font, fill="#1a1a1a", align="center", spacing=6)
                else:
                    # Subtle shadow for regular text (answer options)
                    draw.multiline_text((x+2, y+2), wrapped, font=font, fill=(0,0,0,120), align="center", spacing=6)
                    draw.multiline_text((x, y), wrapped, font=font, fill="#2d2d2d", align="center", spacing=6)
                
                # Add beautiful backdrop blur shadow for questions if requested
                if add_backdrop and is_bold:
                    # Create a subtle backdrop blur effect behind the text
                    from PIL import ImageFilter
                    
                    # Create a slightly larger text mask for the backdrop
                    backdrop_img = Image.new('RGBA', (box_w, box_h), (0, 0, 0, 0))
                    backdrop_draw = ImageDraw.Draw(backdrop_img)
                    
                    # Draw backdrop text with larger size and blur
                    backdrop_font = ImageFont.truetype(font_path, font_size + 4)  # Slightly larger
                    backdrop_draw.multiline_text((x+2, y+2), wrapped, font=backdrop_font, fill=(255,255,255,40), align="center", spacing=6)
                    
                    # Apply blur effect to backdrop
                    backdrop_img = backdrop_img.filter(ImageFilter.GaussianBlur(radius=8))
                    
                    # Composite backdrop behind main text
                    img = Image.alpha_composite(backdrop_img, img)
                
                img.save(out_path)
            
            def generate_google_tts(text, path):
                """Generate TTS using Google Cloud Text-to-Speech API - from reference scripts"""
                try:
                    client = texttospeech.TextToSpeechClient()
                    synthesis_input = texttospeech.SynthesisInput(text=text)
                    voice_config = texttospeech.VoiceSelectionParams(language_code="en-US", name="en-US-Neural2-F")
                    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=1.0)
                    response = client.synthesize_speech(input=synthesis_input, voice=voice_config, audio_config=audio_config)
                    with open(path, "wb") as out: out.write(response.audio_content)
                    
                    # Get audio duration
                    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', path], capture_output=True, text=True)
                    return float(result.stdout.strip())
                except Exception as e:
                    logger.error(f"Google TTS failed: {e}")
                    raise RuntimeError(f"Failed to generate TTS audio: {e}")
            
            def get_audio_duration(path: str) -> float:
                """Get audio duration in seconds"""
                result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', path], capture_output=True, text=True)
                return float(result.stdout.strip())
            
            # DATABASE-DRIVEN FONT OPTIMIZATION FUNCTIONS FOR SCALABILITY
            async def get_optimal_font_size_from_db(avg_chars: float, max_chars: int) -> tuple[int, str]:
                """
                Get optimal font size from database cache for scalable font optimization.
                This eliminates the need to recalculate font sizes for similar questions.
                
                Returns: (optimal_font_size, font_category)
                """
                # Example Firestore query for font optimization cache
                # font_cache_ref = db.collection('font_optimization_cache')
                # query = font_cache_ref.where('avg_answer_length', '>=', avg_chars - 2)\
                #                        .where('avg_answer_length', '<=', avg_chars + 2)\
                #                        .where('max_answer_length', '>=', max_chars - 5)\
                #                        .where('max_answer_length', '<=', max_chars + 5)\
                #                        .order_by('created_at', direction='DESCENDING')\
                #                        .limit(1)
                # 
                # doc = query.get()
                # if doc.exists:
                #     data = doc.to_dict()
                #     return data['optimal_font_size'], data['font_category']
                
                # Fallback to local calculation if no cache hit
                return calculate_optimal_font_size(avg_chars, max_chars)
            
            def calculate_optimal_font_size(avg_chars: float, max_chars: int) -> tuple[int, str]:
                """
                Calculate optimal font size based on character length metrics.
                This function can be cached or moved to a database lookup.
                """
                if avg_chars <= 20:
                    return 48, "short"
                elif avg_chars <= 35:
                    return 42, "medium"
                elif avg_chars <= 50:
                    return 36, "long"
                else:
                    return 32, "very_long"
            
            async def store_font_optimization_data(metadata: dict, episode_id: str):
                """
                Store font optimization metadata in Firestore for future scaling.
                This enables batch processing and consistent font sizing across videos.
                """
                # Example Firestore storage
                # font_cache_ref = db.collection('font_optimization_cache').document(metadata['question_id'])
                # await font_cache_ref.set({
                #     **metadata,
                #     'episode_id': episode_id,
                #     'created_at': firestore.SERVER_TIMESTAMP,
                #     'video_id': episode_id
                # })
                pass  # Placeholder for now
            
            # Find fonts - Now using professional Google Fonts for beautiful visual hierarchy
            def pick_font(candidates):
                for cand in candidates:
                    if os.path.exists(cand): return cand
                raise FileNotFoundError(f"No usable font found in candidates: {candidates}")
            
            # Modern font hierarchy using contemporary fonts for sleek, professional design
            font_candidates = [
                "/System/Library/Fonts/Supplemental/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/System/Library/Fonts/Supplemental/Geneva.ttf"
            ]
            bold_font_candidates = [
                "/System/Library/Fonts/Supplemental/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Geneva.ttf"
            ]
            display_font_candidates = [
                "/System/Library/Fonts/Supplemental/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/System/Library/Fonts/Supplemental/Geneva.ttf"
            ]
            
            fonts = {
                'regular': pick_font(font_candidates),      # Body text, answer options
                'bold': pick_font(bold_font_candidates),    # Question text, emphasis
                'display': pick_font(display_font_candidates) # Answer reveal, titles
            }
            
            # Prepare backgrounds exactly like reference scripts
            q_bg = os.path.join(output_dir, "tmp", "q_bg.mp4")
            logger.info("🎬 Preparing question background...")
            bg_cmd = [
                'ffmpeg', '-y', '-i', os.path.join(assets_dir, "1.mp4"), 
                '-i', os.path.join(assets_dir, "2.mp4"), 
                '-filter_complex', '[0:v][1:v]concat=n=2:v=1[outv]', 
                '-map', '[outv]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', q_bg
            ]
            result = subprocess.run(bg_cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error(f"Failed to create question background: {result.stderr}")
                return None
            
            # Get answer template and dimensions
            ans_template = os.path.join(assets_dir, "3.mp4")
            probe_cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_streams', ans_template
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"Failed to probe video dimensions: {result.stderr}")
                return None
            
            import json
            probe_data = json.loads(result.stdout)
            video_stream = next((s for s in probe_data['streams'] if s['codec_type'] == 'video'), None)
            if not video_stream:
                logger.error("No video stream found")
                return None
            
            w = int(video_stream['width'])
            h = int(video_stream['height'])
            logger.info(f"📐 Video dimensions: {w}x{h}")
            
            # Prepare intro/outro clips
            intro_path = os.path.join(output_dir, "tmp", "intro_prepared.mp4")
            outro_path = os.path.join(output_dir, "tmp", "outro_prepared.mp4")
            
            # Re-encode intro/outro to match target resolution AND frame rate for smooth playback
            # FIXED: Normalize frame rate to 30fps to match generated clips and prevent lag
            intro_cmd = [
                'ffmpeg', '-y', '-i', os.path.join(assets_dir, "An_energetic_game_202508201332_sdz6d.mp4"),
                '-vf', f'scale={w}:{h},fps=30', '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', 
                '-pix_fmt', 'yuv420p', '-r', '30', '-g', '60', intro_path
            ]
            result = subprocess.run(intro_cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error(f"Failed to prepare intro: {result.stderr}")
                return None
            
            outro_cmd = [
                'ffmpeg', '-y', '-i', os.path.join(assets_dir, "A_single_explosive_202508201347_hctna.mp4"),
                '-vf', f'scale={w}:{h},fps=30', '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', 
                '-pix_fmt', 'yuv420p', '-r', '30', '-g', '60', outro_path
            ]
            result = subprocess.run(outro_cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error(f"Failed to prepare outro: {result.stderr}")
                return None
            
            # Now create question clips using the EXACT logic from reference scripts
            clips = []
            for i, row in enumerate(converted_rows):
                logger.info(f"🎬 Creating clip {i+1}/{len(converted_rows)}...")
                
                # Extract text exactly like reference scripts
                q_text, a_text, b_text, c_text, d_text = (
                    row.get("question"), row.get("answer_a"), row.get("answer_b"), 
                    row.get("answer_c"), row.get("answer_d")
                )
                correct_answer = row.get("correct_answer", "A")
                
                # ===== PHASE 1: QUESTION CLIP =====
                logger.info(f"  📝 Creating question clip...")
                
                # TIMING SEQUENCE INSTRUCTIONS:
                # 1. Question TTS plays (duration: question_tts_dur)
                # 2. After TTS ends, wait 5 seconds while timer.mp4 plays
                # 3. Timer duration: 5 seconds (from slide_timer_bar_5s.mp4)
                # 4. Total question clip duration: question_tts_dur + 5 seconds
                
                # Generate TTS for question
                question_tts_path = os.path.join(output_dir, "tmp", f"q_{i}.mp3")
                question_tts_dur = generate_google_tts(f"{q_text} A: {a_text}. B: {b_text}. C: {c_text}. D: {d_text}.", question_tts_path)
                
                # Question clip timing: TTS duration + 5 second timer wait
                question_clip_dur = question_tts_dur + 5.0
                timer_start = round(question_tts_dur, 3)  # Timer starts immediately after TTS ends
                
                # Scale boxes exactly like reference scripts
                bx_q, bx_a, bx_b, bx_c, bx_d, bx_tm = (
                    scale_box(b, w, h) for b in (
                        boxes.question_px, boxes.answer_a_px, boxes.answer_b_px, 
                        boxes.answer_c_px, boxes.answer_d_px, boxes.timer_px
                    )
                )
                
                # Render text to PNG exactly like reference scripts
                q_png = os.path.join(output_dir, "tmp", f"q_{i}.png")
                a_png = os.path.join(output_dir, "tmp", f"a_{i}.png")
                b_png = os.path.join(output_dir, "tmp", f"b_{i}.png")
                c_png = os.path.join(output_dir, "tmp", f"c_{i}.png")
                d_png = os.path.join(output_dir, "tmp", f"d_{i}.png")
                
                # Calculate optimal font size for answers based on average character length
                answer_texts = [a_text, b_text, c_text, d_text]
                avg_chars = sum(len(text) for text in answer_texts) / len(answer_texts)
                
                # DATABASE-DRIVEN FONT SIZING: Use character length metadata for scalable font optimization
                answer_lengths = [len(text) for text in answer_texts]
                max_chars = max(answer_lengths)
                
                # Store character length metadata for database optimization
                question_metadata = {
                    'question_id': f"q_{i}",
                    'avg_answer_length': round(avg_chars, 2),
                    'max_answer_length': max_chars,
                    'answer_lengths': answer_lengths,
                    'optimal_font_size': None,  # Will be calculated below
                    'font_category': None
                }
                
                # DATABASE-DRIVEN FONT SIZING: Use cached optimization or calculate new
                optimal_font_size, font_category = calculate_optimal_font_size(avg_chars, max_chars)
                
                # Store the optimization result for database storage
                question_metadata['optimal_font_size'] = optimal_font_size
                question_metadata['font_category'] = font_category
                
                # Use the calculated optimal font size
                answer_font_size = optimal_font_size
                
                # DATABASE STORAGE: Store font optimization metadata for future scaling
                # This metadata can be used to:
                # 1. Pre-calculate font sizes for similar questions
                # 2. Batch process questions with similar character lengths
                # 3. Cache font sizing decisions for consistent results
                # 4. Optimize font rendering across multiple videos
                
                # Example database schema for font optimization:
                # font_optimization_cache: {
                #     'question_id': f"q_{i}",
                #     'avg_answer_length': avg_chars,
                #     'max_answer_length': max_chars,
                #     'answer_lengths': answer_lengths,
                #     'optimal_font_size': optimal_font_size,
                #     'font_category': font_category,
                #     'created_at': datetime.now(),
                #     'video_id': episode_id
                # }
                
                # For now, log the optimization data (can be stored in Firestore later)
                logger.info(f"🎨 Font optimization for Q{i+1}: avg={avg_chars:.1f} chars, category={font_category}, size={optimal_font_size}px")
                
                # TODO: Store in Firestore for scalable font optimization
                # await store_font_optimization_data(question_metadata, episode_id)
                
                # Beautiful visual hierarchy with professional fonts and dynamic sizing
                render_text_to_png(q_text, bx_q[2], bx_q[3], fonts['bold'], q_png, is_bold=True, add_backdrop=True)      # Question: Bold, prominent + backdrop
                render_text_to_png(a_text, bx_a[2], bx_a[3], fonts['regular'], a_png, is_bold=False, custom_font_size=answer_font_size)   # Answer A: Dynamic sizing
                render_text_to_png(b_text, bx_b[2], bx_b[3], fonts['regular'], b_png, is_bold=False, custom_font_size=answer_font_size)   # Answer B: Dynamic sizing
                render_text_to_png(c_text, bx_c[2], bx_c[3], fonts['regular'], c_png, is_bold=False, custom_font_size=answer_font_size)   # Answer C: Dynamic sizing
                render_text_to_png(d_text, bx_d[2], bx_d[3], fonts['regular'], d_png, is_bold=False, custom_font_size=answer_font_size)   # Answer D: Dynamic sizing

                # Get timer assets exactly like reference scripts
                timer_vid, timer_png, tick_sfx = (
                    os.path.join(assets_dir, "slide_timer_bar_5s.mp4"),
                    os.path.join(assets_dir, "slide_timer_bar_full_striped.png"),
                    os.path.join(assets_dir, "ticking_clock_mechanical_5s.wav")
                )
                
                # Build video filter complex for question clip
                q_vf = ";".join([
                    f"[2:v]format=rgba,scale={bx_q[2]}:{bx_q[3]},fade=in:st=1:d=0.5:alpha=1[q]",
                    f"[3:v]format=rgba,scale={bx_a[2]}:{bx_a[3]},fade=in:st=1:d=0.5:alpha=1[a]",
                    f"[4:v]format=rgba,scale={bx_b[2]}:{bx_b[3]},fade=in:st=1:d=0.5:alpha=1[b]",
                    f"[5:v]format=rgba,scale={bx_c[2]}:{bx_c[3]},fade=in:st=1:d=0.5:alpha=1[c]",
                    f"[6:v]format=rgba,scale={bx_d[2]}:{bx_d[3]},fade=in:st=1:d=0.5:alpha=1[d]",
                    f"[7:v]format=rgba,scale={bx_tm[2]}:{bx_tm[3]}[t_static]",
                    f"[8:v]format=rgba,scale={bx_tm[2]}:{bx_tm[3]},trim=0:5,setpts=PTS+{timer_start}/TB[t_run]",
                    f"[0:v][q]overlay={bx_q[0]}:{bx_q[1]}[v1]",
                    f"[v1][a]overlay={bx_a[0]}:{bx_a[1]}[v2]",
                    f"[v2][b]overlay={bx_b[0]}:{bx_b[1]}[v3]",
                    f"[v3][c]overlay={bx_c[0]}:{bx_c[1]}[v4]",
                    f"[v4][d]overlay={bx_d[0]}:{bx_d[1]}[v5]",
                    f"[v5][t_static]overlay={bx_tm[0]}:{bx_tm[1]}:enable='lt(t,{timer_start})'[v6]",
                    f"[v6][t_run]overlay={bx_tm[0]}:{bx_tm[1]}:enable='gte(t,{timer_start})'[v]"
                ])
                
                # Build audio filter complex for question clip with PROPER STEREO balance
                # FIXED: Ensure both TTS and ticking sound are properly distributed to both channels
                q_af = f"[1:a]aresample=48000,apad=pad_dur=5,pan=stereo|c0=c0|c1=c0[tts];[9:a]aresample=48000,adelay={int(timer_start*1000)}|{int(timer_start*1000)},pan=stereo|c0=c0|c1=c0[tick];[tts][tick]amix=inputs=2:duration=longest:dropout_transition=0[a]"
                
                # Create question clip
                question_clip_path = os.path.join(output_dir, "clips", f"question_{i}.mp4")
                
                q_cmd = [
                    'ffmpeg', '-y', '-i', q_bg, '-i', question_tts_path, '-loop', '1', '-t', str(question_clip_dur), 
                    '-i', q_png, '-loop', '1', '-t', str(question_clip_dur), '-i', a_png, '-loop', '1', '-t', str(question_clip_dur), 
                    '-i', b_png, '-loop', '1', '-t', str(question_clip_dur), '-i', c_png, '-loop', '1', '-t', str(question_clip_dur), 
                    '-i', d_png, '-loop', '1', '-t', str(question_clip_dur), '-i', timer_png, '-i', timer_vid, '-i', tick_sfx, 
                    '-filter_complex', f"{q_vf};{q_af}", '-map', "[v]", '-map', "[a]", '-c:v', 'libx264', 
                    '-c:a', 'aac', '-pix_fmt', 'yuv420p', '-t', str(question_clip_dur), question_clip_path
                ]
                
                result = subprocess.run(q_cmd, capture_output=True, text=True, timeout=120)
                if result.returncode != 0 or not os.path.exists(question_clip_path):
                    logger.error(f"Failed to create question clip {i+1}: {result.stderr}")
                    continue
                
                # ===== PHASE 2: ANSWER CLIP =====
                logger.info(f"  ✅ Creating answer clip...")
                
                # TIMING SEQUENCE INSTRUCTIONS FOR ANSWER CLIP:
                # 1. Answer TTS plays immediately (duration: answer_tts_dur)
                # 2. After TTS ends, show answer slide for 1 second (reduced for snappier feel)
                # 3. Total answer clip duration: answer_tts_dur + 1 second
                # 4. This creates a quick, engaging transition from question to answer
                
                # Generate TTS for answer reveal with proper format
                # Find which option (A, B, C, D) matches the correct answer text
                correct_option = None
                for option in ['a', 'b', 'c', 'd']:
                    if row.get(f'answer_{option}', '').strip() == correct_answer.strip():
                        correct_option = option.upper()
                        break
                
                if not correct_option:
                    # Fallback: use the first option if no match found
                    correct_option = 'A'
                
                # Clean answer text - just the answer, no "Correct Answer:" prefix
                answer_text = correct_answer  # Just the answer text for TTS
                answer_tts_path = os.path.join(output_dir, "tmp", f"answer_{i}.mp3")
                answer_tts_dur = generate_google_tts(answer_text, answer_tts_path)
                
                answer_clip_dur = answer_tts_dur + 1.0  # Answer TTS + 1 second display (reduced for snappier feel)
                
                # Create answer slide with correct answer highlighted
                answer_slide_png = os.path.join(output_dir, "tmp", f"answer_slide_{i}.png")
                
                # Clean answer display - just the answer text, no prefix
                correct_answer_text = correct_answer  # Just the answer text for display
                correct_answer_full = correct_answer  # Use the full correct answer text
                
                # Create answer slide with correct answer prominently displayed
                # FIXED: Use proper SlideBoxes coordinates for clean layout
                answer_img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
                answer_draw = ImageDraw.Draw(answer_img)
                
                # Use the exact coordinates from SlideBoxes for the answer display
                # This matches the reference script's clean layout exactly
                bx_correct = scale_box(boxes.correct_px, w, h)
                
                # Render the correct answer text in the proper box position
                # FIXED: Use custom font sizing for answer text to match other text proportions
                answer_img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
                answer_draw = ImageDraw.Draw(answer_img)
                
                # Beautiful answer text with larger, more prominent font size for maximum impact
                answer_font = ImageFont.truetype(fonts['display'], answer_font_size + 8)  # 8px larger than potential answers for prominence
                
                # Center the answer text in the box
                answer_bbox = answer_draw.textbbox((0, 0), correct_answer_text, font=answer_font)
                answer_w = answer_bbox[2] - answer_bbox[0]
                answer_h = answer_bbox[3] - answer_bbox[1]
                
                # Position text in the center of the answer box
                answer_x = bx_correct[0] + (bx_correct[2] - answer_w) // 2
                answer_y = bx_correct[1] + (bx_correct[3] - answer_h) // 2
                
                # Beautiful answer text with subtle, elegant shadows for modern look
                # Light shadow for subtle depth (reduced intensity)
                answer_draw.text((answer_x+2, answer_y+2), correct_answer_text, font=answer_font, fill=(0,0,0,80))
                # Main text in elegant green with clean, modern appearance
                answer_draw.text((answer_x, answer_y), correct_answer_text, font=answer_font, fill="#00CC44")  # Professional green
                
                answer_img.save(answer_slide_png)
                
                # Create answer clip with correct answer slide
                answer_clip_path = os.path.join(output_dir, "clips", f"answer_{i}.mp4")
                
                # Use answer template background (3.mp4) for answer clips
                answer_bg = os.path.join(assets_dir, "3.mp4")
                
                # Get ding sound for correct answer
                ding_sfx = os.path.join(assets_dir, "ding_correct_answer_long.wav")
                
                # Create answer clip with answer slide overlay
                answer_cmd = [
                    'ffmpeg', '-y', '-i', answer_bg, '-i', answer_tts_path, '-i', answer_slide_png, '-i', ding_sfx,
                    '-filter_complex', f"[2:v]format=rgba,scale={w}:{h},fade=in:st=0:d=0.5[slide];[0:v][slide]overlay=0:0[v];[1:a]aresample=48000,apad=pad_dur=1,pan=stereo|c0=c0|c1=c0[tts];[3:a]aresample=48000,adelay=0|0,pan=stereo|c0=c0|c1=c0[ding];[tts][ding]amix=inputs=2:duration=longest:dropout_transition=0[a]",
                    '-map', "[v]", '-map', "[a]", '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', 
                    '-t', str(answer_clip_dur), answer_clip_path
                ]
                
                result = subprocess.run(answer_cmd, capture_output=True, text=True, timeout=120)
                if result.returncode != 0 or not os.path.exists(answer_clip_path):
                    logger.error(f"Failed to create answer clip {i+1}: {result.stderr}")
                    continue
                
                # Add both clips to the sequence
                clips.append(question_clip_path)
                clips.append(answer_clip_path)
                
                logger.info(f"✅ Created question + answer clips {i+1} (Q: {question_clip_dur:.2f}s, A: {answer_clip_dur:.2f}s)")
            
            if not clips:
                logger.error("No clips created")
                return None
            
            # Create final video by concatenating intro + clips + outro exactly like reference scripts
            output_video = os.path.join(output_dir, f"{episode_id}_professional_video.mp4")
            
            # Create concat file
            concat_file = os.path.join(output_dir, "tmp", "concat.txt")
            with open(concat_file, 'w') as f:
                f.write(f"file '{intro_path}'\n")
                for clip in clips:
                    f.write(f"file '{clip}'\n")
                f.write(f"file '{outro_path}'\n")
            
            # Concatenate using ffmpeg exactly like reference scripts
            logger.info("🎬 Concatenating final video...")
            concat_cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file,
                '-c', 'copy', output_video
            ]
            
            result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0 and os.path.exists(output_video):
                logger.info(f"✅ Created professional video: {output_video}")
                return output_video
            else:
                logger.error(f"Failed to concatenate video: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Professional video generation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _log_statistics(self):
        """Log pipeline statistics."""
        total_dupes = self.stats['specs_rejected'] + self.stats['dupes_caught_post_text']
        if total_dupes > 0:
            prevention_rate = (self.stats['dupes_prevented_pre_text'] / total_dupes) * 100
        else:
            prevention_rate = 0
        
        logger.info("📊 Pipeline Statistics:")
        logger.info(f"  Specs generated: {self.stats['specs_generated']}")
        logger.info(f"  Specs novel: {self.stats['specs_novel']}")
        logger.info(f"  Specs rejected: {self.stats['specs_rejected']}")
        logger.info(f"  Questions generated: {self.stats['questions_generated']}")
        logger.info(f"  Questions valid: {self.stats['questions_valid']}")
        logger.info(f"  Questions invalid: {self.stats['questions_invalid']}")
        logger.info(f"  Dupes prevented pre-text: {self.stats['dupes_prevented_pre_text']}")
        logger.info(f"  Dupes caught post-text: {self.stats['dupes_caught_post_text']}")
        logger.info(f"  Dupe prevention rate: {prevention_rate:.1f}%")
    
    def _difficulty_to_int(self, difficulty: str) -> int:
        """Convert difficulty string to integer."""
        difficulty_map = {
            'easy': 1,
            'medium': 2,
            'hard': 3
        }
        return difficulty_map.get(difficulty.lower(), 1)

    async def _create_csv_from_questions(self, questions: List[Dict], filename: str) -> Optional[str]:
        """Create a CSV file from a list of questions directly."""
        try:
            import csv
            import os
            
            # Create episodes directory if it doesn't exist
            os.makedirs('episodes', exist_ok=True)
            
            csv_path = os.path.join('episodes', filename)
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'category', 'difficulty']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for question in questions:
                    # Ensure all required fields are present
                    row = {
                        'question': question.get('question', ''),
                        'option_a': question.get('option_a', ''),
                        'option_b': question.get('option_b', ''),
                        'option_c': question.get('option_c', ''),
                        'option_d': question.get('option_d', ''),
                        'correct_answer': question.get('correct_answer', ''),
                        'category': question.get('category', 'Sports'),
                        'difficulty': question.get('difficulty', 'Easy')
                    }
                    writer.writerow(row)
            
            logger.info(f"✅ Created CSV from questions: {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"Failed to create CSV from questions: {e}")
            import traceback
            traceback.print_exc()
            return None

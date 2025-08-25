#!/usr/bin/env python3
"""
CLI script to run the Gemini Feeder service.

Usage:
    python run_gemini_feeder.py --channel ch01 --preset science_tech --quantity 10
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gemini_feeder import GeminiFeeder, FeederRequest

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('gemini_feeder.log')
        ]
    )

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate trivia dataset using Gemini AI")
    
    parser.add_argument("--channel", required=True, help="Channel ID (e.g., ch01)")
    parser.add_argument("--preset", required=True, 
                       choices=["general_knowledge", "science_tech", "history_culture", "geography_travel", "entertainment_sports"],
                       help="Prompt preset to use")
    parser.add_argument("--quantity", type=int, required=True, help="Number of questions to generate")
    
    parser.add_argument("--difficulty", default="medium", 
                       choices=["easy", "medium", "hard"], help="Difficulty level")
    parser.add_argument("--style", default="engaging", help="Question style")
    parser.add_argument("--language", default="en", help="Language filter")
    
    parser.add_argument("--max-question-length", type=int, default=200, 
                       help="Maximum question length in characters")
    parser.add_argument("--max-option-length", type=int, default=100, 
                       help="Maximum option length in characters")
    parser.add_argument("--answer-distribution-tolerance", type=int, default=1,
                       help="Tolerance for answer distribution balancing")
    
    parser.add_argument("--tags", nargs="*", help="Additional tags for questions")
    parser.add_argument("--banned-topics", nargs="*", help="Topics to avoid")
    parser.add_argument("--banned-terms", nargs="*", help="Terms to avoid")
    
    parser.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY env var)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    return parser.parse_args()

async def main():
    """Main function."""
    args = parse_arguments()
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    setup_logging()
    
    logger = logging.getLogger(__name__)
    
    # Get API key
    api_key = args.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("No Gemini API key provided. Set GEMINI_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    try:
        # Initialize feeder
        logger.info("Initializing Gemini Feeder...")
        feeder = GeminiFeeder(api_key=api_key)
        
        # Create request
        request = FeederRequest(
            channel_id=args.channel,
            prompt_preset=args.preset,
            quantity=args.quantity,
            tags=args.tags,
            banned_topics=args.banned_topics,
            banned_terms=args.banned_terms,
            max_question_length=args.max_question_length,
            max_option_length=args.max_option_length,
            answer_distribution_tolerance=args.answer_distribution_tolerance,
            language_filter=args.language,
            difficulty=args.difficulty,
            style=args.style
        )
        
        logger.info(f"Starting dataset generation for channel {args.channel}")
        logger.info(f"Preset: {args.preset}")
        logger.info(f"Quantity: {args.quantity}")
        logger.info(f"Difficulty: {args.difficulty}")
        
        # Generate dataset
        dataset_uri = await feeder.generate_dataset(request)
        
        logger.info("=" * 60)
        logger.info("DATASET GENERATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Dataset URI: {dataset_uri}")
        logger.info(f"CSV file: {dataset_uri}/questions.csv")
        logger.info(f"NDJSON file: {dataset_uri}/questions.ndjson")
        logger.info(f"Manifest: {dataset_uri}/_DATASET.json")
        logger.info("=" * 60)
        
        # Print the dataset URI for easy copying
        print(f"\nDataset URI: {dataset_uri}")
        
    except Exception as e:
        logger.error(f"Failed to generate dataset: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

# Gemini Feeder - Trivia Dataset Generator

The Gemini Feeder is a core component of the Trivia Factory pipeline that generates trivia datasets using Google's Gemini AI. It creates clean, validated, and deduplicated CSV files ready for video generation.

## 🎯 Overview

The Gemini Feeder implements **Feature 0** from the work order:
- **Input**: Channel ID, prompt preset, quantity, and configuration
- **Output**: Versioned dataset in GCS with CSV, NDJSON, and manifest files
- **Key Features**: AI generation, validation, deduplication, and quality gates

## 🏗️ Architecture

```
Gemini AI → Question Generation → Validation → Deduplication → Balancing → GCS Publishing
    ↓              ↓                ↓            ↓            ↓           ↓
  API Call    Structured Data   Quality Check  Hash Check  A/B/C/D     Dataset
  Response    JSON Parsing      Length Limits  Channel    Distribution Version
             Error Handling     Banned Terms   Dedup Log   Tolerance   Manifest
```

## 📁 File Structure

```
backend/
├── src/
│   ├── gemini_feeder.py          # Core feeder implementation
│   ├── cloud_storage.py          # GCS operations
│   └── path_resolver.py          # Path management
├── scripts/
│   ├── run_gemini_feeder.py      # CLI interface
│   └── integrate_feeder_with_pipeline.py  # Integration demo
├── test_gemini_feeder.py         # Test suite
└── GEMINI_FEEDER_README.md       # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
export GOOGLE_CLOUD_PROJECT="your_project_id"
export GCS_BUCKET="your_bucket_name"
export CHANNEL_ID="ch01"
```

### 3. Test the Feeder

```bash
python test_gemini_feeder.py
```

### 4. Generate a Dataset

```bash
python scripts/run_gemini_feeder.py \
  --channel ch01 \
  --preset science_tech \
  --quantity 10 \
  --difficulty medium
```

## 🔧 Configuration

### Prompt Presets

The feeder comes with 5 built-in prompt presets:

| Preset | Description | Example Topics |
|--------|-------------|----------------|
| `general_knowledge` | General trivia questions | World facts, common knowledge |
| `science_tech` | Science and technology | Chemistry, physics, computers |
| `history_culture` | History and culture | World events, art, literature |
| `geography_travel` | Geography and travel | Countries, landmarks, maps |
| `entertainment_sports` | Entertainment and sports | Movies, music, athletics |

### Quality Settings

- **Length Limits**: Control question and option lengths
- **Answer Distribution**: Balance A/B/C/D distribution
- **Banned Content**: Filter out unwanted topics/terms
- **Language Filter**: Ensure content is in specified language

## 📊 Output Format

### CSV Structure

The generated CSV follows this schema:

```csv
qid,question,option_a,option_b,option_c,option_d,answer_key,topic,tags,difficulty,language
q001,What is the chemical symbol for gold?,Au,Ag,Fe,Cu,A,Chemistry,chemistry;elements,medium,en
q002,Which planet is the Red Planet?,Venus,Mars,Jupiter,Saturn,B,Astronomy,astronomy;planets,medium,en
```

### Dataset Manifest

Each dataset includes a `_DATASET.json` manifest:

```json
{
  "channel_id": "ch01",
  "version": "2025-01-27-001",
  "source_model_preset": "science_tech",
  "row_count": 10,
  "sha256_csv": "abc123...",
  "created_at": "2025-01-27T10:30:00Z",
  "stats": {
    "answer_distribution": {"A": 3, "B": 2, "C": 3, "D": 2},
    "length_stats": {...},
    "topic_distribution": {...}
  },
  "prompt_config": {...}
}
```

## 🔄 Pipeline Integration

### 1. Generate Dataset

```python
from gemini_feeder import GeminiFeeder, FeederRequest

feeder = GeminiFeeder(api_key="your_key")
request = FeederRequest(
    channel_id="ch01",
    prompt_preset="science_tech",
    quantity=10
)

dataset_uri = await feeder.generate_dataset(request)
# Returns: gs://bucket/datasets/ch01/2025-01-27-001/
```

### 2. Use with Video Pipeline

```bash
# Download and use the generated CSV
python scripts/trivia_video_generator.py \
  --csv gs://bucket/datasets/ch01/2025-01-27-001/questions.csv \
  --templates_dir gs://bucket/assets \
  --out_dir output
```

## 🧪 Testing

### Run Test Suite

```bash
python test_gemini_feeder.py
```

### Test Individual Components

```python
# Test question validation
from gemini_feeder import TriviaQuestion

q = TriviaQuestion(
    qid="q001",
    question="Test question?",
    option_a="A", option_b="B", option_c="C", option_d="D",
    answer_key="A"
)

hash_val = q.get_hash()
print(f"Question hash: {hash_val}")
```

## 🚨 Error Handling

### Common Issues

1. **API Key Missing**: Set `GEMINI_API_KEY` environment variable
2. **GCS Permissions**: Ensure service account has storage access
3. **Network Issues**: Check internet connectivity for Gemini API calls
4. **Validation Failures**: Questions may be rejected for quality reasons

### Fallback Behavior

- If Gemini fails, generates fallback questions
- If validation fails, logs warnings and continues
- If GCS fails, raises exception (no partial publishing)

## 📈 Monitoring

### Logs

The feeder provides detailed logging:
- Question generation progress
- Validation results
- Deduplication statistics
- GCS operation status

### Metrics

Track these key metrics:
- Questions generated vs. requested
- Validation success rate
- Deduplication effectiveness
- Processing time per dataset

## 🔮 Future Enhancements

### Planned Features

- **Multi-language Support**: Generate questions in different languages
- **Difficulty Calibration**: AI-powered difficulty scoring
- **Media Integration**: Support for image-based questions
- **Batch Processing**: Generate multiple datasets simultaneously

### Customization

- **Custom Prompt Presets**: Add your own topic templates
- **Advanced Filtering**: Sophisticated content filtering rules
- **Quality Scoring**: ML-based question quality assessment

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Code Standards

- Follow PEP 8 style guidelines
- Add type hints for all functions
- Include docstrings for all classes/methods
- Write tests for new features

## 📚 API Reference

### Core Classes

- **`GeminiFeeder`**: Main feeder implementation
- **`FeederRequest`**: Configuration for dataset generation
- **`TriviaQuestion`**: Individual question representation
- **`DatasetManifest`**: Dataset metadata and statistics

### Key Methods

- **`generate_dataset()`**: Main entry point
- **`_validate_questions()`**: Quality validation
- **`_deduplicate_questions()`**: Duplicate removal
- **`_publish_dataset()`**: GCS publishing

## 🆘 Support

### Getting Help

1. Check the logs for error details
2. Verify environment variables are set
3. Test with a small quantity first
4. Review the test suite for examples

### Debugging

Enable verbose logging:
```bash
python scripts/run_gemini_feeder.py --verbose --channel ch01 --preset science_tech --quantity 5
```

## 📄 License

This component is part of the Trivia Factory pipeline and follows the same licensing terms.

---

**Ready to generate some trivia?** 🎲

Start with a small dataset to test the system, then scale up to generate hundreds of questions for your video pipeline!

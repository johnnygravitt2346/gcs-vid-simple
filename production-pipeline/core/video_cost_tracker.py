"""
Video Cost Tracking System
Calculates and tracks costs for video generation pipeline
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

@dataclass
class CostBreakdown:
    """Breakdown of video generation costs"""
    gemini_api_calls: int = 0
    gemini_cost_per_call: float = 0.001  # $0.001 per 1K tokens (approximate)
    tts_seconds: float = 0.0
    tts_cost_per_second: float = 0.004  # $0.004 per second (Google TTS)
    video_processing_seconds: float = 0.0
    video_processing_cost_per_second: float = 0.002  # $0.002 per second (FFmpeg processing)
    storage_gb: float = 0.0
    storage_cost_per_gb_month: float = 0.02  # $0.02 per GB per month
    network_egress_gb: float = 0.0
    network_cost_per_gb: float = 0.12  # $0.12 per GB egress
    
    # Calculated costs
    total_gemini_cost: float = 0.0
    total_tts_cost: float = 0.0
    total_processing_cost: float = 0.0
    total_storage_cost: float = 0.0
    total_network_cost: float = 0.0
    total_cost: float = 0.0
    
    def __post_init__(self):
        """Calculate total costs"""
        self.calculate_costs()
    
    def calculate_costs(self):
        """Calculate all cost components"""
        self.total_gemini_cost = self.gemini_api_calls * self.gemini_cost_per_call
        self.total_tts_cost = self.tts_seconds * self.tts_cost_per_second
        self.total_processing_cost = self.video_processing_seconds * self.video_processing_cost_per_second
        self.total_storage_cost = self.storage_gb * self.storage_cost_per_gb_month
        self.total_network_cost = self.network_egress_gb * self.network_cost_per_gb
        
        self.total_cost = (
            self.total_gemini_cost +
            self.total_tts_cost +
            self.total_processing_cost +
            self.total_storage_cost +
            self.total_network_cost
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/display"""
        return {
            'gemini_api_calls': self.gemini_api_calls,
            'gemini_cost_per_call': self.gemini_cost_per_call,
            'tts_seconds': self.tts_seconds,
            'tts_cost_per_second': self.tts_cost_per_second,
            'video_processing_seconds': self.video_processing_seconds,
            'video_processing_cost_per_second': self.video_processing_cost_per_second,
            'storage_gb': self.storage_gb,
            'storage_cost_per_gb_month': self.storage_cost_per_gb_month,
            'network_egress_gb': self.network_egress_gb,
            'network_cost_per_gb': self.network_cost_per_gb,
            'total_gemini_cost': round(self.total_gemini_cost, 4),
            'total_tts_cost': round(self.total_tts_cost, 4),
            'total_processing_cost': round(self.total_processing_cost, 4),
            'total_storage_cost': round(self.total_storage_cost, 4),
            'total_network_cost': round(self.total_network_cost, 4),
            'total_cost': round(self.total_cost, 4)
        }

@dataclass
class VideoCostRecord:
    """Record of video generation costs"""
    job_id: str
    video_id: str
    channel_id: str
    topic: str
    difficulty_level: str
    num_questions: int
    video_duration_seconds: float
    output_file_size_gb: float
    cost_breakdown: CostBreakdown
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/display"""
        return {
            'job_id': self.job_id,
            'video_id': self.video_id,
            'channel_id': self.channel_id,
            'topic': self.topic,
            'difficulty_level': self.difficulty_level,
            'num_questions': self.num_questions,
            'video_duration_seconds': self.video_duration_seconds,
            'output_file_size_gb': self.output_file_size_gb,
            'cost_breakdown': self.cost_breakdown.to_dict(),
            'created_at': self.created_at,
            'metadata': self.metadata
        }

class VideoCostTracker:
    """Tracks and calculates video generation costs"""
    
    def __init__(self):
        self.cost_records: Dict[str, VideoCostRecord] = {}
        self.cost_history: List[VideoCostRecord] = []
        
        # Default cost configurations
        self.default_costs = {
            'gemini_cost_per_call': 0.001,
            'tts_cost_per_second': 0.004,
            'video_processing_cost_per_second': 0.002,
            'storage_cost_per_gb_month': 0.02,
            'network_cost_per_gb': 0.12
        }
    
    def estimate_costs_for_job(self, job_config: Dict) -> CostBreakdown:
        """Estimate costs for a video generation job"""
        
        num_questions = job_config.get('num_questions', 5)
        difficulty = job_config.get('difficulty_level', 'intermediate')
        topic = job_config.get('topic', 'Sports Trivia')
        
        # Estimate Gemini API calls
        # 1 call for topic planning + 1 call per question + 1 call for SEO content
        gemini_calls = 2 + num_questions
        
        # Estimate TTS duration
        # Intro: 7s, Each question: 6s, Outro: 5s
        tts_duration = 7 + (num_questions * 6) + 5
        
        # Estimate video processing time
        # Rough estimate: 2x real-time for processing
        video_duration = tts_duration
        processing_time = video_duration * 2
        
        # Estimate storage (video file + intermediate files)
        # Final video: ~50MB, intermediates: ~100MB per question
        storage_gb = 0.05 + (num_questions * 0.1)
        
        # Estimate network egress (final video download)
        network_gb = 0.05
        
        # Create cost breakdown
        cost_breakdown = CostBreakdown(
            gemini_api_calls=gemini_calls,
            tts_seconds=tts_duration,
            video_processing_seconds=processing_time,
            storage_gb=storage_gb,
            network_egress_gb=network_gb
        )
        
        return cost_breakdown
    
    def record_actual_costs(self, job_id: str, video_id: str, actual_costs: Dict) -> VideoCostRecord:
        """Record actual costs after video generation"""
        
        # Create cost breakdown from actual data
        cost_breakdown = CostBreakdown(
            gemini_api_calls=actual_costs.get('gemini_api_calls', 0),
            tts_seconds=actual_costs.get('tts_seconds', 0),
            video_processing_seconds=actual_costs.get('video_processing_seconds', 0),
            storage_gb=actual_costs.get('storage_gb', 0),
            network_egress_gb=actual_costs.get('network_egress_gb', 0)
        )
        
        # Create cost record
        cost_record = VideoCostRecord(
            job_id=job_id,
            video_id=video_id,
            channel_id=actual_costs.get('channel_id', 'unknown'),
            topic=actual_costs.get('topic', 'Unknown'),
            difficulty_level=actual_costs.get('difficulty_level', 'intermediate'),
            num_questions=actual_costs.get('num_questions', 0),
            video_duration_seconds=actual_costs.get('video_duration_seconds', 0),
            output_file_size_gb=actual_costs.get('output_file_size_gb', 0),
            cost_breakdown=cost_breakdown,
            metadata=actual_costs.get('metadata', {})
        )
        
        # Store record
        self.cost_records[video_id] = cost_record
        self.cost_history.append(cost_record)
        
        return cost_record
    
    def get_cost_summary(self, time_period_days: int = 30) -> Dict:
        """Get cost summary for a time period"""
        
        cutoff_date = datetime.now().timestamp() - (time_period_days * 24 * 60 * 60)
        
        period_records = [
            record for record in self.cost_history
            if datetime.fromisoformat(record.created_at).timestamp() > cutoff_date
        ]
        
        if not period_records:
            return {
                'total_videos': 0,
                'total_cost': 0.0,
                'average_cost_per_video': 0.0,
                'cost_breakdown': {},
                'period_days': time_period_days
            }
        
        total_cost = sum(record.cost_breakdown.total_cost for record in period_records)
        total_videos = len(period_records)
        average_cost = total_cost / total_videos
        
        # Aggregate cost breakdown
        cost_breakdown = {
            'gemini': sum(record.cost_breakdown.total_gemini_cost for record in period_records),
            'tts': sum(record.cost_breakdown.total_tts_cost for record in period_records),
            'processing': sum(record.cost_breakdown.total_processing_cost for record in period_records),
            'storage': sum(record.cost_breakdown.total_storage_cost for record in period_records),
            'network': sum(record.cost_breakdown.total_network_cost for record in period_records)
        }
        
        return {
            'total_videos': total_videos,
            'total_cost': round(total_cost, 4),
            'average_cost_per_video': round(average_cost, 4),
            'cost_breakdown': {k: round(v, 4) for k, v in cost_breakdown.items()},
            'period_days': time_period_days
        }
    
    def get_cost_by_difficulty(self) -> Dict:
        """Get cost breakdown by difficulty level"""
        
        difficulty_costs = {}
        
        for record in self.cost_history:
            difficulty = record.difficulty_level
            if difficulty not in difficulty_costs:
                difficulty_costs[difficulty] = {
                    'count': 0,
                    'total_cost': 0.0,
                    'average_cost': 0.0
                }
            
            difficulty_costs[difficulty]['count'] += 1
            difficulty_costs[difficulty]['total_cost'] += record.cost_breakdown.total_cost
        
        # Calculate averages
        for difficulty in difficulty_costs:
            count = difficulty_costs[difficulty]['count']
            total = difficulty_costs[difficulty]['total_cost']
            difficulty_costs[difficulty]['average_cost'] = round(total / count, 4)
            difficulty_costs[difficulty]['total_cost'] = round(total, 4)
        
        return difficulty_costs
    
    def get_cost_by_topic(self) -> Dict:
        """Get cost breakdown by topic"""
        
        topic_costs = {}
        
        for record in self.cost_history:
            topic = record.topic
            if topic not in topic_costs:
                topic_costs[topic] = {
                    'count': 0,
                    'total_cost': 0.0,
                    'average_cost': 0.0
                }
            
            topic_costs[topic]['count'] += 1
            topic_costs[topic]['total_cost'] += record.cost_breakdown.total_cost
        
        # Calculate averages
        for topic in topic_costs:
            count = topic_costs[topic]['count']
            total = topic_costs[topic]['total_cost']
            topic_costs[topic]['average_cost'] = round(total / count, 4)
            topic_costs[topic]['total_cost'] = round(total, 4)
        
        return topic_costs
    
    def export_cost_data(self, format: str = 'json') -> str:
        """Export cost data in specified format"""
        
        if format == 'json':
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'cost_records': [record.to_dict() for record in self.cost_history],
                'summary': self.get_cost_summary(),
                'by_difficulty': self.get_cost_by_difficulty(),
                'by_topic': self.get_cost_by_topic()
            }
            return json.dumps(export_data, indent=2)
        
        elif format == 'csv':
            # CSV format for spreadsheet analysis
            csv_lines = ['job_id,video_id,channel_id,topic,difficulty,num_questions,duration_seconds,file_size_gb,total_cost,gemini_cost,tts_cost,processing_cost,storage_cost,network_cost,created_at']
            
            for record in self.cost_history:
                csv_line = [
                    record.job_id,
                    record.video_id,
                    record.channel_id,
                    record.topic,
                    record.difficulty_level,
                    record.num_questions,
                    record.video_duration_seconds,
                    record.output_file_size_gb,
                    record.cost_breakdown.total_cost,
                    record.cost_breakdown.total_gemini_cost,
                    record.cost_breakdown.total_tts_cost,
                    record.cost_breakdown.total_processing_cost,
                    record.cost_breakdown.total_storage_cost,
                    record.cost_breakdown.total_network_cost,
                    record.created_at
                ]
                csv_lines.append(','.join(str(field) for field in csv_line))
            
            return '\n'.join(csv_lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_cost_efficiency_tips(self) -> List[str]:
        """Get tips for reducing video generation costs"""
        
        tips = []
        
        # Analyze cost patterns
        summary = self.get_cost_summary(30)
        if summary['total_videos'] > 0:
            avg_cost = summary['average_cost_per_video']
            
            if avg_cost > 0.05:  # More than 5 cents per video
                tips.append("💡 Consider batching questions to reduce per-video Gemini API calls")
                tips.append("💡 Use shorter TTS durations for intro/outro to reduce audio costs")
                tips.append("💡 Implement question caching to avoid regenerating similar content")
            
            if summary['cost_breakdown']['storage'] > summary['total_cost'] * 0.3:
                tips.append("💡 Implement automatic cleanup of intermediate files to reduce storage costs")
            
            if summary['cost_breakdown']['network'] > summary['total_cost'] * 0.2:
                tips.append("💡 Consider video compression to reduce download bandwidth costs")
        
        # Add general tips
        tips.extend([
            "💡 Use appropriate difficulty levels - harder questions may require more Gemini calls",
            "💡 Batch similar topics together to leverage question reuse",
            "💡 Monitor question pool availability to avoid unnecessary regeneration",
            "💡 Consider using pre-generated question banks for common topics"
        ])
        
        return tips

# Global instance
cost_tracker = VideoCostTracker()

def get_cost_tracker() -> VideoCostTracker:
    """Get the global cost tracker instance"""
    return cost_tracker

def estimate_job_costs(job_config: Dict) -> CostBreakdown:
    """Estimate costs for a video generation job"""
    return cost_tracker.estimate_costs_for_job(job_config)

def record_video_costs(job_id: str, video_id: str, actual_costs: Dict) -> VideoCostRecord:
    """Record actual costs after video generation"""
    return cost_tracker.record_actual_costs(job_id, video_id, actual_costs)


#!/usr/bin/env python3
"""
LLM Response Analyzer
=====================
Analyze and summarize dumped LLM responses to check for:
- Format consistency
- Parsing errors
- Missing fields
- Output quality issues

Usage:
    python tools/analyze_llm_responses.py [--project-id PROJECT_ID] [--worker WORKER_NAME]
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class LLMResponseAnalyzer:
    """Analyzer for LLM response dumps"""
    
    def __init__(self, project_id: str = None):
        """
        Initialize analyzer.
        
        Args:
            project_id: Project identifier (None for default logs)
        """
        self.project_id = project_id
        
        # Determine logs directory
        if project_id:
            self.logs_dir = os.path.join(Config.LOG_DIR, project_id, 'llm_responses')
        else:
            self.logs_dir = os.path.join(Config.LOG_DIR, 'llm_responses')
        
        logger.info(f"📂 Analyzing LLM responses from: {self.logs_dir}")
    
    def load_responses(self, worker_filter: str = None) -> List[Dict[str, Any]]:
        """
        Load all LLM response dumps.
        
        Args:
            worker_filter: Filter by worker name (orchestrator, breakdown_worker, etc.)
            
        Returns:
            List of response data
        """
        if not os.path.exists(self.logs_dir):
            logger.warning(f"⚠️ Logs directory not found: {self.logs_dir}")
            return []
        
        responses = []
        
        for filename in sorted(os.listdir(self.logs_dir)):
            if not filename.endswith('.json'):
                continue
            
            # Apply worker filter
            if worker_filter and not filename.startswith(worker_filter):
                continue
            
            filepath = os.path.join(self.logs_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data['filename'] = filename
                    responses.append(data)
            except Exception as e:
                logger.error(f"❌ Failed to load {filename}: {e}")
        
        logger.info(f"✅ Loaded {len(responses)} LLM responses")
        return responses
    
    def analyze_worker_responses(self, worker_name: str, responses: List[Dict[str, Any]]):
        """Analyze responses for a specific worker"""
        
        worker_responses = [r for r in responses if r['worker_name'] == worker_name]
        
        if not worker_responses:
            logger.info(f"❌ No responses found for worker: {worker_name}")
            return
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 ANALYSIS FOR: {worker_name.upper()}")
        logger.info(f"{'='*80}")
        
        # Basic stats
        total = len(worker_responses)
        success = sum(1 for r in worker_responses if r['parsing_success'])
        failed = total - success
        
        logger.info(f"📈 Total responses: {total}")
        logger.info(f"✅ Successful parsing: {success} ({success/total*100:.1f}%)")
        logger.info(f"❌ Failed parsing: {failed} ({failed/total*100:.1f}%)")
        
        # Analyze successful responses
        if success > 0:
            self._analyze_successful_responses(worker_name, worker_responses)
        
        # Analyze failures
        if failed > 0:
            self._analyze_failed_responses(worker_name, worker_responses)
    
    def _analyze_successful_responses(self, worker_name: str, responses: List[Dict[str, Any]]):
        """Analyze successful responses for field consistency"""
        
        successful = [r for r in responses if r['parsing_success']]
        
        logger.info(f"\n📋 Field Analysis (Successful Responses):")
        
        if worker_name == 'orchestrator':
            self._check_orchestrator_fields(successful)
        elif worker_name == 'breakdown_worker':
            self._check_breakdown_fields(successful)
        elif worker_name == 'estimation_worker':
            self._check_estimation_fields(successful)
        elif worker_name == 'validation_worker':
            self._check_validation_fields(successful)
    
    def _check_orchestrator_fields(self, responses: List[Dict[str, Any]]):
        """Check orchestrator output fields"""
        required_fields = ['categories', 'analysis_strategy', 'complexity_assessment']
        
        for field in required_fields:
            count = sum(1 for r in responses if field in r.get('parsed_result', {}))
            logger.info(f"   - '{field}': {count}/{len(responses)} ({count/len(responses)*100:.1f}%)")
    
    def _check_breakdown_fields(self, responses: List[Dict[str, Any]]):
        """Check breakdown worker output fields"""
        required_fields = [
            'id', 'category', 'sub_no', 'task_name', 'description',
            'complexity', 'dependencies', 'priority', 'premise', 'remark', 'note'
        ]
        
        # Check if 'breakdown' array exists
        with_breakdown = sum(1 for r in responses if 'breakdown' in r.get('parsed_result', {}))
        logger.info(f"   - Responses with 'breakdown' array: {with_breakdown}/{len(responses)}")
        
        # Check fields in tasks
        field_stats = defaultdict(int)
        total_tasks = 0
        description_with_sections = 0
        
        for response in responses:
            tasks = response.get('parsed_result', {}).get('breakdown', [])
            total_tasks += len(tasks)
            
            for task in tasks:
                for field in required_fields:
                    if field in task:
                        field_stats[field] += 1
                
                # Check description format (BACKEND, FRONTEND, TESTING sections)
                description = task.get('description', '')
                if all(section in description for section in ['BACKEND', 'FRONTEND', 'TESTING']):
                    description_with_sections += 1
        
        logger.info(f"   - Total tasks analyzed: {total_tasks}")
        logger.info(f"   - Tasks with proper description format (3 sections): {description_with_sections}/{total_tasks} ({description_with_sections/total_tasks*100:.1f}%)" if total_tasks > 0 else "   - No tasks found")
        
        logger.info(f"\n   Field Coverage:")
        for field in required_fields:
            count = field_stats[field]
            percentage = (count / total_tasks * 100) if total_tasks > 0 else 0
            logger.info(f"      - '{field}': {count}/{total_tasks} ({percentage:.1f}%)")
    
    def _check_estimation_fields(self, responses: List[Dict[str, Any]]):
        """Check estimation worker output fields"""
        required_fields = [
            'id', 'estimation_manday', 'backend_implement', 'backend_fixbug', 'backend_unittest',
            'frontend_implement', 'frontend_fixbug', 'frontend_unittest', 'responsive_implement',
            'testing_implement', 'confidence_level', 'breakdown_reasoning'
        ]
        
        # Check if 'estimation' object exists
        with_estimation = sum(1 for r in responses if 'estimation' in r.get('parsed_result', {}))
        logger.info(f"   - Responses with 'estimation' object: {with_estimation}/{len(responses)}")
        
        # Check fields
        field_stats = defaultdict(int)
        total_role_coverage = 0
        
        for response in responses:
            estimation = response.get('parsed_result', {}).get('estimation', {})
            
            for field in required_fields:
                if field in estimation:
                    field_stats[field] += 1
            
            # Check if all 3 roles are covered
            has_backend = any(estimation.get(f, 0) > 0 for f in ['backend_implement', 'backend_fixbug', 'backend_unittest'])
            has_frontend = any(estimation.get(f, 0) > 0 for f in ['frontend_implement', 'frontend_fixbug', 'frontend_unittest'])
            has_testing = estimation.get('testing_implement', 0) > 0
            
            if has_backend and has_frontend and has_testing:
                total_role_coverage += 1
        
        logger.info(f"   - Estimations covering all 3 roles: {total_role_coverage}/{len(responses)} ({total_role_coverage/len(responses)*100:.1f}%)")
        
        logger.info(f"\n   Field Coverage:")
        for field in required_fields:
            count = field_stats[field]
            percentage = (count / len(responses) * 100) if len(responses) > 0 else 0
            logger.info(f"      - '{field}': {count}/{len(responses)} ({percentage:.1f}%)")
    
    def _check_validation_fields(self, responses: List[Dict[str, Any]]):
        """Check validation worker output fields"""
        required_fields = [
            'validated_estimation', 'original_estimation', 'adjustment_applied',
            'adjustment_percentage', 'validation_notes', 'confidence_level'
        ]
        
        # Check if 'validation' object exists
        with_validation = sum(1 for r in responses if 'validation' in r.get('parsed_result', {}))
        logger.info(f"   - Responses with 'validation' object: {with_validation}/{len(responses)}")
        
        # Check fields
        field_stats = defaultdict(int)
        
        for response in responses:
            validation = response.get('parsed_result', {}).get('validation', {})
            
            for field in required_fields:
                if field in validation:
                    field_stats[field] += 1
        
        logger.info(f"\n   Field Coverage:")
        for field in required_fields:
            count = field_stats[field]
            percentage = (count / len(responses) * 100) if len(responses) > 0 else 0
            logger.info(f"      - '{field}': {count}/{len(responses)} ({percentage:.1f}%)")
    
    def _analyze_failed_responses(self, worker_name: str, responses: List[Dict[str, Any]]):
        """Analyze failed parsing responses"""
        
        failed = [r for r in responses if not r['parsing_success']]
        
        logger.info(f"\n❌ Failed Responses Analysis:")
        logger.info(f"   Total failed: {len(failed)}")
        
        # Show first few failures
        for i, response in enumerate(failed[:3], 1):
            logger.info(f"\n   Failure #{i}:")
            logger.info(f"      Timestamp: {response['timestamp']}")
            logger.info(f"      Task: {response['task_info']}")
            logger.info(f"      Response length: {response['raw_response_length']} chars")
            
            # Show first 200 chars of raw response
            raw_preview = response['raw_response'][:200].replace('\n', ' ')
            logger.info(f"      Preview: {raw_preview}...")
    
    def generate_summary_report(self, responses: List[Dict[str, Any]]) -> str:
        """Generate a comprehensive summary report"""
        
        report_lines = [
            "="*80,
            "LLM RESPONSE ANALYSIS SUMMARY REPORT",
            "="*80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Project ID: {self.project_id or 'Default'}",
            f"Total Responses Analyzed: {len(responses)}",
            ""
        ]
        
        # Group by worker
        workers = set(r['worker_name'] for r in responses)
        
        for worker in sorted(workers):
            worker_responses = [r for r in responses if r['worker_name'] == worker]
            success = sum(1 for r in worker_responses if r['parsing_success'])
            failed = len(worker_responses) - success
            
            report_lines.extend([
                f"\n{worker.upper()}:",
                f"   Total: {len(worker_responses)}",
                f"   Success: {success} ({success/len(worker_responses)*100:.1f}%)",
                f"   Failed: {failed} ({failed/len(worker_responses)*100:.1f}%)"
            ])
        
        report_lines.append("\n" + "="*80)
        
        report = "\n".join(report_lines)
        
        # Save report
        report_filename = f"llm_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = os.path.join(self.logs_dir, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"\n📄 Summary report saved to: {report_path}")
        
        return report


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze LLM response dumps')
    parser.add_argument('--project-id', help='Project identifier')
    parser.add_argument('--worker', help='Filter by worker name (orchestrator, breakdown_worker, estimation_worker, validation_worker)')
    
    args = parser.parse_args()
    
    analyzer = LLMResponseAnalyzer(project_id=args.project_id)
    
    # Load responses
    responses = analyzer.load_responses(worker_filter=args.worker)
    
    if not responses:
        logger.warning("❌ No responses found to analyze")
        return
    
    # Analyze by worker
    workers = set(r['worker_name'] for r in responses)
    
    for worker in sorted(workers):
        analyzer.analyze_worker_responses(worker, responses)
    
    # Generate summary report
    print("\n")
    report = analyzer.generate_summary_report(responses)
    print(report)


if __name__ == '__main__':
    main()

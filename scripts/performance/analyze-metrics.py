#!/usr/bin/env python3
"""
Performance Metrics Analysis Script for Selextract Cloud
Analyzes load testing results and generates detailed performance insights
"""

import argparse
import json
import csv
import os
import sys
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

class PerformanceAnalyzer:
    """Analyzes performance metrics from various load testing tools"""
    
    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.analysis_results = {}
        
        # Verify results directory exists
        if not self.results_dir.exists():
            raise FileNotFoundError(f"Results directory not found: {results_dir}")
            
    def analyze_k6_results(self) -> Dict[str, Any]:
        """Analyze K6 test results"""
        k6_file = self.results_dir / "k6-results.json"
        
        if not k6_file.exists():
            return {"error": "K6 results file not found"}
            
        try:
            with open(k6_file, 'r') as f:
                # K6 outputs one JSON object per line
                k6_data = []
                for line in f:
                    if line.strip():
                        k6_data.append(json.loads(line))
            
            # Extract metrics
            metrics = {}
            for entry in k6_data:
                if entry.get('type') == 'Point' and 'metric' in entry:
                    metric_name = entry['metric']
                    if metric_name not in metrics:
                        metrics[metric_name] = []
                    metrics[metric_name].append(entry.get('data', {}).get('value', 0))
            
            # Calculate statistics
            analysis = {}
            for metric, values in metrics.items():
                if values:
                    analysis[metric] = {
                        'count': len(values),
                        'mean': statistics.mean(values),
                        'median': statistics.median(values),
                        'min': min(values),
                        'max': max(values),
                        'p95': np.percentile(values, 95) if len(values) > 1 else values[0],
                        'p99': np.percentile(values, 99) if len(values) > 1 else values[0],
                        'std_dev': statistics.stdev(values) if len(values) > 1 else 0
                    }
            
            return {
                'tool': 'k6',
                'metrics': analysis,
                'total_data_points': sum(len(v) for v in metrics.values())
            }
            
        except Exception as e:
            return {"error": f"Failed to analyze K6 results: {str(e)}"}
    
    def analyze_artillery_results(self) -> Dict[str, Any]:
        """Analyze Artillery test results"""
        artillery_file = self.results_dir / "artillery-results.json"
        
        if not artillery_file.exists():
            return {"error": "Artillery results file not found"}
            
        try:
            with open(artillery_file, 'r') as f:
                artillery_data = json.load(f)
            
            # Extract summary statistics
            summary = artillery_data.get('aggregate', {})
            
            analysis = {
                'tool': 'artillery',
                'summary': {
                    'scenarios_launched': summary.get('scenariosLaunched', 0),
                    'scenarios_completed': summary.get('scenariosCompleted', 0),
                    'requests_completed': summary.get('requestsCompleted', 0),
                    'response_time': {
                        'min': summary.get('latency', {}).get('min'),
                        'max': summary.get('latency', {}).get('max'),
                        'median': summary.get('latency', {}).get('median'),
                        'p95': summary.get('latency', {}).get('p95'),
                        'p99': summary.get('latency', {}).get('p99')
                    },
                    'rps': {
                        'count': summary.get('rps', {}).get('count'),
                        'mean': summary.get('rps', {}).get('mean')
                    },
                    'errors': summary.get('errors', {})
                },
                'phases': artillery_data.get('phases', [])
            }
            
            return analysis
            
        except Exception as e:
            return {"error": f"Failed to analyze Artillery results: {str(e)}"}
    
    def analyze_locust_results(self) -> Dict[str, Any]:
        """Analyze Locust test results"""
        locust_stats_file = self.results_dir / "locust_stats.csv"
        locust_history_file = self.results_dir / "locust_stats_history.csv"
        
        analysis = {'tool': 'locust'}
        
        # Analyze stats
        if locust_stats_file.exists():
            try:
                stats_df = pd.read_csv(locust_stats_file)
                
                analysis['endpoint_stats'] = []
                for _, row in stats_df.iterrows():
                    if row['Type'] != 'Aggregated':
                        endpoint_stats = {
                            'name': row['Name'],
                            'method': row.get('Method', 'GET'),
                            'request_count': row['Request Count'],
                            'failure_count': row['Failure Count'],
                            'median_response_time': row['Median Response Time'],
                            'average_response_time': row['Average Response Time'],
                            'min_response_time': row['Min Response Time'],
                            'max_response_time': row['Max Response Time'],
                            'average_content_size': row['Average Content Size'],
                            'requests_per_sec': row['Requests/s'],
                            'failures_per_sec': row['Failures/s']
                        }
                        analysis['endpoint_stats'].append(endpoint_stats)
                
                # Overall statistics
                total_row = stats_df[stats_df['Type'] == 'Aggregated'].iloc[0] if 'Aggregated' in stats_df['Type'].values else None
                if total_row is not None:
                    analysis['summary'] = {
                        'total_requests': total_row['Request Count'],
                        'total_failures': total_row['Failure Count'],
                        'failure_rate': total_row['Failure Count'] / total_row['Request Count'] if total_row['Request Count'] > 0 else 0,
                        'median_response_time': total_row['Median Response Time'],
                        'average_response_time': total_row['Average Response Time'],
                        'requests_per_sec': total_row['Requests/s']
                    }
                    
            except Exception as e:
                analysis['stats_error'] = f"Failed to analyze Locust stats: {str(e)}"
        
        # Analyze history
        if locust_history_file.exists():
            try:
                history_df = pd.read_csv(locust_history_file)
                
                analysis['performance_over_time'] = {
                    'timestamps': history_df['Timestamp'].tolist(),
                    'user_count': history_df['User Count'].tolist(),
                    'requests_per_sec': history_df['Requests/s'].tolist(),
                    'failures_per_sec': history_df['Failures/s'].tolist(),
                    'response_time_50': history_df['50%'].tolist(),
                    'response_time_95': history_df['95%'].tolist()
                }
                
            except Exception as e:
                analysis['history_error'] = f"Failed to analyze Locust history: {str(e)}"
        
        return analysis
    
    def analyze_system_metrics(self) -> Dict[str, Any]:
        """Analyze system metrics before and after tests"""
        before_file = self.results_dir / "system-metrics-before.json"
        after_file = self.results_dir / "system-metrics-after.json"
        
        analysis = {'tool': 'system_metrics'}
        
        try:
            if before_file.exists() and after_file.exists():
                with open(before_file, 'r') as f:
                    before_metrics = json.load(f)
                with open(after_file, 'r') as f:
                    after_metrics = json.load(f)
                
                analysis['comparison'] = {
                    'memory_change': {
                        'before_mb': before_metrics['memory']['used_mb'],
                        'after_mb': after_metrics['memory']['used_mb'],
                        'difference_mb': after_metrics['memory']['used_mb'] - before_metrics['memory']['used_mb']
                    },
                    'disk_change': {
                        'before_percent': before_metrics['disk']['usage_percent'],
                        'after_percent': after_metrics['disk']['usage_percent'],
                        'difference_percent': after_metrics['disk']['usage_percent'] - before_metrics['disk']['usage_percent']
                    }
                }
                
        except Exception as e:
            analysis['error'] = f"Failed to analyze system metrics: {str(e)}"
        
        return analysis
    
    def analyze_database_performance(self) -> Dict[str, Any]:
        """Analyze database performance results"""
        db_file = self.results_dir / "database-performance.txt"
        
        if not db_file.exists():
            return {"error": "Database performance file not found"}
        
        try:
            with open(db_file, 'r') as f:
                content = f.read()
            
            # Extract timing information (simplified parsing)
            timing_lines = [line for line in content.split('\n') if 'Time:' in line]
            
            analysis = {
                'tool': 'database',
                'query_count': len(timing_lines),
                'timing_info': timing_lines[:10],  # First 10 timing results
                'file_size_kb': os.path.getsize(db_file) / 1024
            }
            
            return analysis
            
        except Exception as e:
            return {"error": f"Failed to analyze database performance: {str(e)}"}
    
    def analyze_redis_performance(self) -> Dict[str, Any]:
        """Analyze Redis performance results"""
        redis_file = self.results_dir / "redis-performance.txt"
        
        if not redis_file.exists():
            return {"error": "Redis performance file not found"}
        
        try:
            with open(redis_file, 'r') as f:
                content = f.read()
            
            # Parse Redis benchmark results
            lines = content.split('\n')
            benchmark_results = {}
            
            for line in lines:
                if 'requests per second' in line.lower():
                    parts = line.split()
                    if len(parts) >= 4:
                        operation = parts[0].replace(':', '')
                        rps = float(parts[-3])
                        benchmark_results[operation] = {
                            'requests_per_second': rps,
                            'avg_latency_ms': 1000.0 / rps if rps > 0 else 0
                        }
            
            analysis = {
                'tool': 'redis',
                'benchmark_results': benchmark_results,
                'total_operations': len(benchmark_results)
            }
            
            return analysis
            
        except Exception as e:
            return {"error": f"Failed to analyze Redis performance: {str(e)}"}
    
    def generate_performance_insights(self) -> Dict[str, Any]:
        """Generate performance insights and recommendations"""
        insights = {
            'recommendations': [],
            'warnings': [],
            'performance_score': 0,
            'bottlenecks': []
        }
        
        # Analyze K6 results for insights
        k6_analysis = self.analysis_results.get('k6', {})
        if 'metrics' in k6_analysis:
            # Check response times
            http_req_duration = k6_analysis['metrics'].get('http_req_duration', {})
            if 'p95' in http_req_duration:
                p95_time = http_req_duration['p95']
                if p95_time > 2000:  # 2 seconds
                    insights['warnings'].append(f"95th percentile response time is high: {p95_time:.0f}ms")
                    insights['bottlenecks'].append("High API response times")
                elif p95_time < 500:  # Under 500ms
                    insights['recommendations'].append("Excellent API response times")
            
            # Check error rates
            http_req_failed = k6_analysis['metrics'].get('http_req_failed', {})
            if 'mean' in http_req_failed:
                error_rate = http_req_failed['mean']
                if error_rate > 0.05:  # 5% error rate
                    insights['warnings'].append(f"High error rate: {error_rate*100:.1f}%")
                    insights['bottlenecks'].append("High error rate")
        
        # Analyze system resource usage
        system_analysis = self.analysis_results.get('system_metrics', {})
        if 'comparison' in system_analysis:
            memory_change = system_analysis['comparison']['memory_change']['difference_mb']
            if memory_change > 1000:  # More than 1GB increase
                insights['warnings'].append(f"High memory usage increase: {memory_change}MB")
                insights['bottlenecks'].append("Memory usage")
        
        # Calculate performance score (0-100)
        score_factors = []
        
        # Response time factor
        if 'metrics' in k6_analysis and 'http_req_duration' in k6_analysis['metrics']:
            p95_time = k6_analysis['metrics']['http_req_duration'].get('p95', 5000)
            response_score = max(0, 100 - (p95_time / 50))  # 100 points for 0ms, 0 points for 5000ms
            score_factors.append(response_score)
        
        # Error rate factor
        if 'metrics' in k6_analysis and 'http_req_failed' in k6_analysis['metrics']:
            error_rate = k6_analysis['metrics']['http_req_failed'].get('mean', 1)
            error_score = max(0, 100 - (error_rate * 2000))  # 100 points for 0% errors
            score_factors.append(error_score)
        
        # Throughput factor (simplified)
        if 'metrics' in k6_analysis and 'http_reqs' in k6_analysis['metrics']:
            rps = k6_analysis['metrics']['http_reqs'].get('mean', 0)
            throughput_score = min(100, rps * 2)  # 100 points for 50+ RPS
            score_factors.append(throughput_score)
        
        insights['performance_score'] = statistics.mean(score_factors) if score_factors else 50
        
        # Generate recommendations based on analysis
        if insights['performance_score'] < 60:
            insights['recommendations'].extend([
                "Consider optimizing database queries",
                "Review and tune application configuration",
                "Check for resource bottlenecks",
                "Consider horizontal scaling"
            ])
        elif insights['performance_score'] > 80:
            insights['recommendations'].extend([
                "Excellent performance! Consider load testing with higher loads",
                "Document current configuration for production deployment"
            ])
        
        return insights
    
    def create_visualizations(self):
        """Create performance visualization charts"""
        viz_dir = self.results_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        # K6 response time distribution
        k6_analysis = self.analysis_results.get('k6', {})
        if 'metrics' in k6_analysis and 'http_req_duration' in k6_analysis['metrics']:
            duration_stats = k6_analysis['metrics']['http_req_duration']
            
            plt.figure(figsize=(10, 6))
            metrics = ['min', 'median', 'mean', 'p95', 'p99', 'max']
            values = [duration_stats.get(m, 0) for m in metrics]
            
            plt.bar(metrics, values, color=['green', 'blue', 'orange', 'yellow', 'red', 'darkred'])
            plt.title('HTTP Request Duration Distribution')
            plt.ylabel('Time (ms)')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(viz_dir / "response_time_distribution.png")
            plt.close()
        
        # Locust performance over time
        locust_analysis = self.analysis_results.get('locust', {})
        if 'performance_over_time' in locust_analysis:
            perf_data = locust_analysis['performance_over_time']
            
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
            
            # Requests per second
            ax1.plot(perf_data['requests_per_sec'], label='Requests/sec', color='blue')
            ax1.plot(perf_data['failures_per_sec'], label='Failures/sec', color='red')
            ax1.set_title('Throughput Over Time')
            ax1.set_ylabel('Requests/sec')
            ax1.legend()
            ax1.grid(True)
            
            # Response times
            ax2.plot(perf_data['response_time_50'], label='50th percentile', color='green')
            ax2.plot(perf_data['response_time_95'], label='95th percentile', color='orange')
            ax2.set_title('Response Times Over Time')
            ax2.set_ylabel('Response Time (ms)')
            ax2.legend()
            ax2.grid(True)
            
            # User count
            ax3.plot(perf_data['user_count'], label='Active Users', color='purple')
            ax3.set_title('User Load Over Time')
            ax3.set_ylabel('Number of Users')
            ax3.set_xlabel('Time')
            ax3.legend()
            ax3.grid(True)
            
            plt.tight_layout()
            plt.savefig(viz_dir / "locust_performance_timeline.png")
            plt.close()
        
        print(f"Visualizations saved to: {viz_dir}")
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run complete performance analysis"""
        print("Starting performance analysis...")
        
        # Run individual analyses
        self.analysis_results['k6'] = self.analyze_k6_results()
        self.analysis_results['artillery'] = self.analyze_artillery_results()
        self.analysis_results['locust'] = self.analyze_locust_results()
        self.analysis_results['system_metrics'] = self.analyze_system_metrics()
        self.analysis_results['database'] = self.analyze_database_performance()
        self.analysis_results['redis'] = self.analyze_redis_performance()
        
        # Generate insights
        self.analysis_results['insights'] = self.generate_performance_insights()
        
        # Create visualizations
        try:
            self.create_visualizations()
        except Exception as e:
            print(f"Warning: Could not create visualizations: {e}")
        
        # Save analysis results
        analysis_file = self.results_dir / "analysis-results.json"
        with open(analysis_file, 'w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)
        
        print(f"Analysis complete. Results saved to: {analysis_file}")
        return self.analysis_results
    
    def print_summary(self):
        """Print analysis summary to console"""
        print("\n" + "="*60)
        print("PERFORMANCE ANALYSIS SUMMARY")
        print("="*60)
        
        insights = self.analysis_results.get('insights', {})
        
        # Performance Score
        score = insights.get('performance_score', 0)
        print(f"\nOverall Performance Score: {score:.1f}/100")
        
        if score >= 80:
            print("🟢 Excellent performance!")
        elif score >= 60:
            print("🟡 Good performance with room for improvement")
        else:
            print("🔴 Performance needs attention")
        
        # Warnings
        warnings = insights.get('warnings', [])
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"  • {warning}")
        
        # Bottlenecks
        bottlenecks = insights.get('bottlenecks', [])
        if bottlenecks:
            print(f"\n🚨 BOTTLENECKS ({len(bottlenecks)}):")
            for bottleneck in bottlenecks:
                print(f"  • {bottleneck}")
        
        # Recommendations
        recommendations = insights.get('recommendations', [])
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(recommendations)}):")
            for rec in recommendations:
                print(f"  • {rec}")
        
        # Tool-specific summaries
        print(f"\n📊 TOOL RESULTS:")
        
        # K6 Summary
        k6_data = self.analysis_results.get('k6', {})
        if 'metrics' in k6_data:
            print("  K6 Load Tests:")
            http_duration = k6_data['metrics'].get('http_req_duration', {})
            if 'p95' in http_duration:
                print(f"    • 95th percentile response time: {http_duration['p95']:.0f}ms")
            
            http_failed = k6_data['metrics'].get('http_req_failed', {})
            if 'mean' in http_failed:
                print(f"    • Error rate: {http_failed['mean']*100:.2f}%")
        
        # Artillery Summary
        artillery_data = self.analysis_results.get('artillery', {})
        if 'summary' in artillery_data:
            summary = artillery_data['summary']
            print("  Artillery Tests:")
            print(f"    • Scenarios completed: {summary.get('scenarios_completed', 0)}")
            print(f"    • Requests completed: {summary.get('requests_completed', 0)}")
            response_time = summary.get('response_time', {})
            if 'p95' in response_time:
                print(f"    • 95th percentile: {response_time['p95']}ms")
        
        # Locust Summary
        locust_data = self.analysis_results.get('locust', {})
        if 'summary' in locust_data:
            summary = locust_data['summary']
            print("  Locust Tests:")
            print(f"    • Total requests: {summary.get('total_requests', 0)}")
            print(f"    • Failure rate: {summary.get('failure_rate', 0)*100:.2f}%")
            print(f"    • Requests/sec: {summary.get('requests_per_sec', 0):.1f}")
        
        print("\n" + "="*60)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Analyze Selextract Cloud performance test results")
    parser.add_argument("results_dir", help="Directory containing performance test results")
    parser.add_argument("--format", choices=["json", "summary", "both"], default="both",
                       help="Output format (default: both)")
    parser.add_argument("--visualizations", action="store_true", default=True,
                       help="Generate visualization charts (default: True)")
    
    args = parser.parse_args()
    
    try:
        analyzer = PerformanceAnalyzer(args.results_dir)
        results = analyzer.run_analysis()
        
        if args.format in ["summary", "both"]:
            analyzer.print_summary()
        
        if args.format in ["json", "both"]:
            print(f"\nDetailed results available in: {args.results_dir}/analysis-results.json")
        
        # Exit with non-zero code if performance is poor
        score = results.get('insights', {}).get('performance_score', 50)
        if score < 60:
            sys.exit(1)
        
    except Exception as e:
        print(f"Error analyzing performance results: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
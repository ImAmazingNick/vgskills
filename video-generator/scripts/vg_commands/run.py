
"""
vg run commands

Evaluate and analyze video generation runs for quality, performance, and insights.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import time
from datetime import datetime, timedelta
import json


def register(subparsers):
    # Register run commands.
    run_parser = subparsers.add_parser('run', help='Evaluate and analyze video generation runs')
    run_sub = run_parser.add_subparsers(dest='run_command')

    # vg run evaluate
    eval_parser = run_sub.add_parser('evaluate', help='Evaluate a video generation run')
    eval_parser.add_argument('--run-id', help='Run ID to evaluate')
    eval_parser.add_argument('--last', action='store_true', help='Evaluate the most recent run')
    eval_parser.add_argument('--detailed', action='store_true', help='Include detailed analysis')
    eval_parser.set_defaults(func=cmd_evaluate)

    # vg run list
    list_parser = run_sub.add_parser('list', help='List runs with optional filtering')
    list_parser.add_argument('--status', choices=['success', 'partial_success', 'failure'], help='Filter by status')
    list_parser.add_argument('--since', help='Filter runs since date (YYYY-MM-DD)')
    list_parser.add_argument('--until', help='Filter runs until date (YYYY-MM-DD)')
    list_parser.add_argument('--limit', type=int, default=10, help='Maximum number of runs to show')
    list_parser.set_defaults(func=cmd_list)

    # vg run summary
    summary_parser = run_sub.add_parser('summary', help='Show summary of run evaluations')
    summary_parser.add_argument('--run-id', help='Run ID to summarize')
    summary_parser.add_argument('--days', type=int, default=7, help='Days to look back for summary')
    summary_parser.set_defaults(func=cmd_summary)

    # vg run dashboard
    dashboard_parser = run_sub.add_parser('dashboard', help='Generate HTML dashboard of runs')
    dashboard_parser.add_argument('--output', '-o', default='runs_dashboard.html', help='Output HTML file path')
    dashboard_parser.add_argument('--limit', type=int, default=50, help='Maximum number of runs to include')
    dashboard_parser.set_defaults(func=cmd_dashboard)


class RunEvaluator:
    # Evaluates video generation runs for quality and performance.

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.run_path = Path("videos/runs") / run_id
        self.evaluation_path = self.run_path / "evaluation"

    def evaluate_run(self, detailed: bool = False) -> Dict[str, Any]:
        # Main evaluation entry point.
        if not self.run_path.exists():
            return {
                "success": False,
                "error": f"Run directory not found: {self.run_path}",
                "code": "RUN_NOT_FOUND"
            }

        # Create evaluation directory if it doesn't exist
        self.evaluation_path.mkdir(exist_ok=True)

        evaluation = {
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(),
            "status": "unknown",
            "duration_total_s": None,
            "phases": {},
            "metrics": {},
            "artifacts": {},
            "issues": [],
            "recommendations": []
        }

        try:
            # Evaluate each phase
            evaluation["phases"]["recording"] = self.evaluate_recording_phase()
            evaluation["phases"]["editing"] = self.evaluate_editing_phase()
            evaluation["phases"]["audio"] = self.evaluate_audio_phase()
            evaluation["phases"]["composition"] = self.evaluate_composition_phase()

            # Calculate overall metrics
            evaluation["metrics"] = self.calculate_overall_metrics(evaluation["phases"])
            evaluation["duration_total_s"] = evaluation["metrics"].get("total_duration_s")

            # Determine status
            evaluation["status"] = self.determine_overall_status(evaluation["phases"])

            # Generate issues and recommendations
            evaluation["issues"] = self.detect_issues(evaluation["phases"])
            evaluation["recommendations"] = self.generate_recommendations(evaluation["phases"], evaluation["issues"])

            # Save evaluation
            self.save_evaluation(evaluation)

            return {
                "success": True,
                "evaluation": evaluation,
                "run_id": self.run_id,
                "status": evaluation["status"],
                "issues_count": len(evaluation["issues"]),
                "recommendations_count": len(evaluation["recommendations"])
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Evaluation failed: {str(e)}",
                "code": "EVALUATION_ERROR"
            }

    def evaluate_recording_phase(self) -> Dict[str, Any]:
        # Evaluate the recording phase with enhanced metrics.
        phase_eval = {
            "status": "unknown",
            "duration_s": None,
            "markers_captured": 0,
            "video_quality": "unknown",
            "technical_metrics": {},
            "issues": []
        }

        # Check for recording files
        raw_dir = self.run_path / "raw"
        if not raw_dir.exists():
            phase_eval["issues"].append("Raw recording directory not found")
            phase_eval["status"] = "missing"
            return phase_eval

        # Check recording.webm
        recording_file = raw_dir / "recording.webm"
        if not recording_file.exists():
            phase_eval["issues"].append("Recording video file not found")
            phase_eval["status"] = "missing"
            return phase_eval

        # Enhanced file analysis
        file_size = recording_file.stat().st_size
        phase_eval["file_size_mb"] = round(file_size / (1024 * 1024), 2)
        phase_eval["technical_metrics"]["file_size_mb"] = phase_eval["file_size_mb"]

        # Get video technical details using ffprobe
        technical_info = self.get_video_technical_info(recording_file)
        if technical_info:
            phase_eval["technical_metrics"].update(technical_info)

        # Check timeline.md for markers
        timeline_file = self.run_path / "timeline.md"
        if timeline_file.exists():
            try:
                with open(timeline_file, 'r') as f:
                    content = f.read()
                    # Count marker lines (rough estimate)
                    marker_lines = [line for line in content.split('\n') if '|' in line and len(line.strip()) > 10]
                    phase_eval["markers_captured"] = len(marker_lines)

                    # Analyze timeline completeness
                    phase_eval["timeline_completeness"] = self.analyze_timeline_completeness(content)
            except Exception as e:
                phase_eval["issues"].append(f"Could not read timeline: {str(e)}")

        # Enhanced quality assessment
        quality_score = self.calculate_video_quality_score(phase_eval)
        phase_eval["quality_score"] = quality_score

        if quality_score >= 0.8:
            phase_eval["video_quality"] = "excellent"
        elif quality_score >= 0.6:
            phase_eval["video_quality"] = "good"
        elif quality_score >= 0.4:
            phase_eval["video_quality"] = "acceptable"
        else:
            phase_eval["video_quality"] = "poor"
            if file_size < 1 * 1024 * 1024:  # < 1MB
                phase_eval["issues"].append("Recording file unusually small")

        phase_eval["status"] = "success" if not phase_eval["issues"] else "partial_success"
        return phase_eval

    def evaluate_editing_phase(self) -> Dict[str, Any]:
        # Evaluate the editing phase.
        phase_eval = {
            "status": "unknown",
            "operations": [],
            "time_saved_s": 0,
            "compression_ratio": 1.0,
            "issues": []
        }

        # Check for edited files
        trimmed_file = self.run_path / "trimmed.mp4"
        fast_file = self.run_path / "fast.mp4"

        if trimmed_file.exists():
            phase_eval["operations"].append("trim")
        if fast_file.exists():
            phase_eval["operations"].append("speed-gaps")

        if not phase_eval["operations"]:
            phase_eval["status"] = "skipped"
            return phase_eval

        phase_eval["status"] = "success"
        return phase_eval

    def evaluate_audio_phase(self) -> Dict[str, Any]:
        # Evaluate the audio phase with enhanced metrics.
        phase_eval = {
            "status": "unknown",
            "segments": 0,
            "total_duration_s": 0,
            "quality_score": 0.0,
            "technical_metrics": {},
            "sync_analysis": {},
            "issues": []
        }

        audio_dir = self.run_path / "audio"
        if not audio_dir.exists():
            phase_eval["status"] = "skipped"
            return phase_eval

        # Count audio files
        audio_files = list(audio_dir.glob("*.mp3"))
        phase_eval["segments"] = len(audio_files)

        if not audio_files:
            phase_eval["issues"].append("No audio segments found")
            phase_eval["status"] = "missing"
            return phase_eval

        # Analyze each audio file
        audio_analysis = []
        total_size = 0

        for audio_file in audio_files:
            analysis = self.analyze_audio_file(audio_file)
            audio_analysis.append(analysis)
            total_size += analysis.get("file_size_kb", 0)

        phase_eval["technical_metrics"]["audio_files"] = audio_analysis
        phase_eval["technical_metrics"]["total_size_kb"] = total_size

        # Calculate average metrics
        if audio_analysis:
            avg_bitrate = sum(a.get("bitrate_kbps", 0) for a in audio_analysis) / len(audio_analysis)
            avg_duration = sum(a.get("duration", 0) for a in audio_analysis) / len(audio_analysis)
            avg_sample_rate = sum(a.get("sample_rate", 0) for a in audio_analysis) / len(audio_analysis)

            phase_eval["technical_metrics"]["avg_bitrate_kbps"] = round(avg_bitrate, 1)
            phase_eval["technical_metrics"]["avg_duration_s"] = round(avg_duration, 2)
            phase_eval["technical_metrics"]["avg_sample_rate"] = int(avg_sample_rate)

        # Enhanced quality assessment
        phase_eval["quality_score"] = self.calculate_audio_quality_score(phase_eval)

        # Analyze audio-video sync if timeline exists
        sync_analysis = self.analyze_audio_video_sync()
        if sync_analysis:
            phase_eval["sync_analysis"] = sync_analysis

        # Check for common audio issues
        self.check_audio_issues(phase_eval)

        phase_eval["status"] = "success" if not phase_eval["issues"] else "partial_success"
        return phase_eval

    def evaluate_composition_phase(self) -> Dict[str, Any]:
        # Evaluate the composition phase with comprehensive metrics.
        phase_eval = {
            "status": "unknown",
            "sync_accuracy_ms": None,
            "final_size_mb": None,
            "technical_metrics": {},
            "quality_metrics": {},
            "performance_metrics": {},
            "issues": []
        }

        final_file = self.run_path / "final.mp4"
        if not final_file.exists():
            phase_eval["issues"].append("Final video file not found")
            phase_eval["status"] = "missing"
            return phase_eval

        # Get comprehensive file analysis
        file_size = final_file.stat().st_size
        phase_eval["final_size_mb"] = round(file_size / (1024 * 1024), 2)

        # Get technical info about final video
        technical_info = self.get_video_technical_info(final_file)
        if technical_info:
            phase_eval["technical_metrics"] = technical_info

        # Analyze composition quality
        quality_analysis = self.analyze_composition_quality(final_file)
        if quality_analysis:
            phase_eval["quality_metrics"] = quality_analysis

        # Performance analysis
        performance_analysis = self.analyze_composition_performance()
        if performance_analysis:
            phase_eval["performance_metrics"] = performance_analysis

        # Check for composition issues
        self.check_composition_issues(phase_eval)

        # Overall assessment
        quality_score = self.calculate_composition_quality_score(phase_eval)
        phase_eval["quality_score"] = quality_score

        # Determine status with more nuanced logic
        critical_issues = 0
        for issue in phase_eval["issues"]:
            if any(keyword in issue.lower() for keyword in ["unusually short", "very low", "not found", "failed"]):
                critical_issues += 1

        if critical_issues >= 2:
            phase_eval["status"] = "poor_quality"
        elif critical_issues == 1 or quality_score < 0.3:
            phase_eval["status"] = "needs_improvement"
        elif quality_score >= 0.7:
            phase_eval["status"] = "success"
        else:
            phase_eval["status"] = "acceptable"

        return phase_eval

    def calculate_overall_metrics(self, phases: Dict[str, Any]) -> Dict[str, Any]:
        # Calculate overall metrics from phase evaluations.
        metrics = {
            "total_duration_s": None,
            "total_size_mb": 0,
            "phases_completed": 0,
            "quality_score": 0.0
        }

        # Count completed phases
        for phase_name, phase_data in phases.items():
            if phase_data.get("status") in ["success", "partial_success"]:
                metrics["phases_completed"] += 1

        # Calculate quality score
        quality_scores = []
        if phases.get("recording", {}).get("video_quality") == "good":
            quality_scores.append(0.9)
        elif phases.get("recording", {}).get("video_quality") == "acceptable":
            quality_scores.append(0.7)

        if phases.get("audio", {}).get("quality_score"):
            quality_scores.append(phases["audio"]["quality_score"])

        if quality_scores:
            metrics["quality_score"] = sum(quality_scores) / len(quality_scores)

        # Calculate total size
        for phase_data in phases.values():
            if "file_size_mb" in phase_data:
                metrics["total_size_mb"] += phase_data["file_size_mb"]
            if "final_size_mb" in phase_data:
                metrics["total_size_mb"] += phase_data["final_size_mb"]

        return metrics

    def determine_overall_status(self, phases: Dict[str, Any]) -> str:
        # Determine overall run status.
        statuses = [phase.get("status", "unknown") for phase in phases.values()]

        if all(status == "success" for status in statuses):
            return "success"
        elif any(status in ["success", "partial_success"] for status in statuses):
            return "partial_success"
        else:
            return "failure"

    def detect_issues(self, phases: Dict[str, Any]) -> List[str]:
        # Detect issues across all phases.
        issues = []

        for phase_name, phase_data in phases.items():
            phase_issues = phase_data.get("issues", [])
            issues.extend([f"{phase_name}: {issue}" for issue in phase_issues])

        return issues

    def generate_recommendations(self, phases: Dict[str, Any], issues: List[str]) -> List[str]:
        # Generate recommendations based on evaluation.
        recommendations = []

        # Check for common issues and provide recommendations
        if any("unusually small" in issue for issue in issues):
            recommendations.append("Check recording settings - video files are smaller than expected")

        if phases.get("recording", {}).get("markers_captured", 0) == 0:
            recommendations.append("Add timeline markers to request file for better audio sync")

        if phases.get("editing", {}).get("operations", []) == []:
            recommendations.append("Consider adding speed-gaps editing to reduce long waiting periods")

        if phases.get("audio", {}).get("segments", 0) == 0:
            recommendations.append("Add narration to make the video more engaging")

        # Quality recommendations
        quality_score = phases.get("metrics", {}).get("quality_score", 0)
        if quality_score < 0.7:
            recommendations.append("Review recording setup for better video/audio quality")

        return recommendations

    def save_evaluation(self, evaluation: Dict[str, Any]):
        # Save evaluation to central evaluations file.
        import time
        start_time = time.time()

        self.save_to_central_evaluations(evaluation)

        # Add performance metric
        evaluation_time = time.time() - start_time
        evaluation["performance"] = {
            "evaluation_time_seconds": round(evaluation_time, 2)
        }

    def save_to_central_evaluations(self, evaluation: Dict[str, Any]):
        # Save evaluation to central evaluations.md file.
        central_file = Path("evaluations.md")

        # Load existing evaluations
        existing_evals = {}
        if central_file.exists():
            try:
                with open(central_file, 'r') as f:
                    content = f.read()

                # Parse existing evaluations (simple format)
                if "## Evaluations by Run" in content:
                    # Extract existing evaluations
                    existing_evals = self.parse_central_evaluations(content)
            except:
                pass

        # Add/update this evaluation
        existing_evals[evaluation['run_id']] = evaluation

        # Add comparative analysis
        evaluation = self.add_comparative_analysis(evaluation, existing_evals)

        # Generate new central file
        central_content = self.generate_central_evaluations_file(existing_evals)
        with open(central_file, 'w') as f:
            f.write(central_content)

    def parse_central_evaluations(self, content: str) -> Dict[str, Dict]:
        # Parse central evaluations file to extract evaluations.
        evaluations = {}
        current_run = None
        current_eval = {}

        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('## '):
                # Check if this is a run section
                if ' - ' in line:
                    run_id = line.split(' - ')[0].replace('## ', '')
                    current_run = run_id
                    current_eval = {'run_id': run_id}
                    evaluations[run_id] = current_eval

                    # Look for status, timestamp, etc.
                    while i + 1 < len(lines) and not lines[i + 1].strip().startswith('## '):
                        i += 1
                        next_line = lines[i].strip()
                        if next_line.startswith('**Status:**'):
                            # Parse status
                            status_text = next_line.replace('**Status:** ', '')
                            if '✅' in status_text:
                                current_eval['status'] = 'success'
                            elif '⚠️' in status_text:
                                current_eval['status'] = 'partial_success'
                            elif '❌' in status_text:
                                current_eval['status'] = 'failure'
                        elif next_line.startswith('**Timestamp:**'):
                            current_eval['timestamp'] = next_line.replace('**Timestamp:** ', '')
                        elif next_line.startswith('- **Quality Score:**'):
                            score_text = next_line.replace('- **Quality Score:** ', '').replace('/1.0', '')
                            try:
                                current_eval['quality_score'] = float(score_text)
                            except:
                                current_eval['quality_score'] = 0.0
            i += 1

        return evaluations

    def generate_central_evaluations_file(self, evaluations: Dict[str, Dict]) -> str:
        # Generate the central evaluations.md file.
        # Sort by timestamp (newest first)
        sorted_runs = sorted(evaluations.items(),
                           key=lambda x: x[1].get('timestamp', ''),
                           reverse=True)

        total_runs = len(evaluations)
        success_rate = sum(1 for e in evaluations.values() if e.get('status') == 'success') / max(len(evaluations), 1)
        avg_quality = sum(e.get('metrics', {}).get('quality_score', 0) for e in evaluations.values()) / max(len(evaluations), 1)

        content = """# Video Generator Evaluations

All video generation runs with their evaluation results.

## Summary

- **Total Runs:** """ + str(total_runs) + """
- **Success Rate:** """ + "{:.1%}".format(success_rate) + """
- **Average Quality:** """ + "{:.2f}".format(avg_quality) + """/1.0

## Evaluations by Run

"""



        for run_id, evaluation in sorted_runs:
            status_emoji = {
                'success': '✅',
                'partial_success': '⚠️',
                'failure': '❌'
            }.get(evaluation.get('status', 'unknown'), '❓')

            metrics = evaluation.get('metrics', {})
            issues = evaluation.get('issues', [])
            recommendations = evaluation.get('recommendations', [])

            content += "## " + run_id + " - " + status_emoji + " " + evaluation.get('status', 'unknown').replace('_', ' ').title() + "\n\n"
            content += "**Timestamp:** " + evaluation.get('timestamp', 'unknown') + "\n"
            content += "**Duration:** " + str(evaluation.get('duration_total_s', 'unknown')) + "\n\n"
            content += "### Overview\n\n"
            content += "- **Quality Score:** " + str(metrics.get('quality_score', 0))[:4] + "/1.0\n"
            content += "- **Phases Completed:** " + str(metrics.get('phases_completed', 0)) + "/4\n"
            content += "- **Total Size:** " + str(metrics.get('total_size_mb', 0))[:4] + " MB\n"
            content += "- **Issues Found:** " + str(len(issues)) + "\n"
            content += "- **Recommendations:** " + str(len(recommendations)) + "\n"

            # Add comparative analysis if available
            comparison = metrics.get('comparison')
            if comparison:
                quality_diff = comparison.get('vs_average_quality', 0)
                if quality_diff > 0.1:
                    content += "- **Performance:** 🟢 Above average (+{:.2f})\n".format(quality_diff)
                elif quality_diff < -0.1:
                    content += "- **Performance:** 🔴 Below average ({:.2f})\n".format(quality_diff)
                else:
                    content += "- **Performance:** 🟡 Average compared to other runs\n"

            # Add evaluation performance
            perf = evaluation.get('performance', {})
            if perf.get('evaluation_time_seconds'):
                content += "- **Evaluation Time:** {:.2f}s\n".format(perf['evaluation_time_seconds'])

            content += "\n### Phase Details\n"



            # Add detailed phase information
            phases = evaluation.get('phases', {})
            for phase_name, phase_data in phases.items():
                if phase_data.get('status') not in ['unknown', 'skipped']:
                    content += "#### " + phase_name.title() + " Phase\n"
                    content += "- **Status:** " + phase_data.get('status', 'unknown').replace('_', ' ').title() + "\n"

                    # Add technical metrics
                    tech_metrics = phase_data.get('technical_metrics', {})
                    if tech_metrics:
                        content += "- **Technical:** "
                        tech_details = []

                        if 'width' in tech_metrics and 'height' in tech_metrics:
                            tech_details.append(str(tech_metrics['width']) + "x" + str(tech_metrics['height']))
                        if 'fps' in tech_metrics:
                            tech_details.append("{:.1f}fps".format(tech_metrics['fps']))
                        if 'bitrate' in tech_metrics:
                            tech_details.append(str(tech_metrics['bitrate']) + "kbps")
                        if 'avg_bitrate_kbps' in tech_metrics:
                            tech_details.append("avg " + str(tech_metrics['avg_bitrate_kbps']) + "kbps")
                        if 'avg_sample_rate' in tech_metrics:
                            tech_details.append(str(tech_metrics['avg_sample_rate']) + "Hz")

                        content += ", ".join(tech_details) + "\n"

                    # Add quality score if available
                    if 'quality_score' in phase_data:
                        content += "- **Quality:** {:.2f}/1.0\n".format(phase_data['quality_score'])

                    # Add phase-specific metrics
                    if phase_name == 'recording' and 'markers_captured' in phase_data:
                        content += "- **Markers:** " + str(phase_data['markers_captured']) + "\n"
                    elif phase_name == 'audio' and 'segments' in phase_data:
                        content += "- **Segments:** " + str(phase_data['segments']) + "\n"
                    elif phase_name == 'editing' and 'operations' in phase_data:
                        content += "- **Operations:** " + ", ".join(phase_data['operations']) + "\n"

                    content += "\n"

            content += "### Issues\n"
            content += chr(10).join("- " + issue for issue in issues) if issues else "None"
            content += "\n\n### Recommendations\n"
            content += chr(10).join("- " + rec for rec in recommendations) if recommendations else "None"
            content += "\n\n---\n"

        return content


    def get_video_technical_info(self, video_file: Path) -> Dict[str, Any]:
        # Extract technical information from video file using ffmpeg
        try:
            import subprocess
            import re

            # Use ffmpeg -i to get stream information
            cmd = [
                "./node_modules/ffmpeg-static/ffmpeg",
                "-i", str(video_file)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.run_path.parent.parent)

            # Parse ffmpeg output for technical info
            output = result.stderr  # ffmpeg info goes to stderr

            info = {}

            # Extract duration (format: Duration: 00:00:10.50)
            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', output)
            if duration_match:
                hours, minutes, seconds, centiseconds = map(int, duration_match.groups())
                info['duration'] = hours * 3600 + minutes * 60 + seconds + centiseconds / 100

            # Extract bitrate (format: bitrate: 128 kb/s)
            bitrate_match = re.search(r'bitrate: (\d+) kb/s', output)
            if bitrate_match:
                info['bitrate'] = int(bitrate_match.group(1))

            # Extract video info (format: Video: h264 (Main) (avc1 / 0x31637661), yuv420p, 1920x1080)
            video_match = re.search(r'Video: (\w+).*?, .*?, (\d{3,4}x\d{3,4})', output)
            if video_match:
                info['codec'] = video_match.group(1)
                width_height = video_match.group(2).split('x')
                info['width'] = int(width_height[0])
                info['height'] = int(width_height[1])

            # Extract FPS (format: 30 fps)
            fps_match = re.search(r'(\d+(?:\.\d+)?) fps', output)
            if fps_match:
                info['fps'] = float(fps_match.group(1))

            return info

        except Exception as e:
            # If ffmpeg analysis fails, return basic file info
            try:
                file_size = video_file.stat().st_size
                return {
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'analysis_failed': True,
                    'error': str(e)
                }
            except:
                return {}

    def analyze_timeline_completeness(self, timeline_content: str) -> Dict[str, Any]:
        # Analyze timeline marker completeness and quality
        analysis = {
            "total_markers": 0,
            "unique_markers": 0,
            "time_span_s": 0,
            "marker_density": 0  # markers per minute
        }

        try:
            lines = timeline_content.split('\n')
            markers = []
            seen_markers = set()

            for line in lines:
                if '|' in line and len(line.strip()) > 10:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 3:
                        marker_name = parts[1]
                        try:
                            time_s = float(parts[2])
                            markers.append((marker_name, time_s))
                            seen_markers.add(marker_name)
                        except ValueError:
                            continue

            analysis["total_markers"] = len(markers)
            analysis["unique_markers"] = len(seen_markers)

            if markers:
                times = [m[1] for m in markers]
                analysis["time_span_s"] = max(times) - min(times)
                analysis["marker_density"] = (len(markers) / max(analysis["time_span_s"], 60)) * 60  # per minute

        except Exception:
            pass

        return analysis

    def calculate_video_quality_score(self, phase_eval: Dict[str, Any]) -> float:
        # Calculate overall video quality score (0.0 to 1.0)
        score = 0.0
        factors = 0

        # File size factor (larger = potentially better quality)
        file_size_mb = phase_eval.get("file_size_mb", 0)
        if file_size_mb > 50:
            score += 0.3  # Excellent size
        elif file_size_mb > 20:
            score += 0.2  # Good size
        elif file_size_mb > 5:
            score += 0.1  # Acceptable size
        factors += 0.3

        # Technical metrics factor
        tech = phase_eval.get("technical_metrics", {})
        tech_score = 0

        # If technical analysis failed, be more forgiving
        if tech.get("analysis_failed"):
            # Still give partial credit for having a video file
            tech_score += 0.2
        else:
            # Resolution score
            width = tech.get("width", 0)
            height = tech.get("height", 0)
            if width >= 1920 and height >= 1080:
                tech_score += 0.4  # 1080p+
            elif width >= 1280 and height >= 720:
                tech_score += 0.3  # 720p
            elif width >= 854 and height >= 480:
                tech_score += 0.2  # 480p

            # Bitrate score (kbps)
            bitrate = tech.get("bitrate", 0)
            if bitrate > 5000:
                tech_score += 0.3  # High bitrate
            elif bitrate > 2000:
                tech_score += 0.2  # Good bitrate
            elif bitrate > 500:
                tech_score += 0.1  # Acceptable bitrate

            # FPS score
            fps = tech.get("fps", 0)
            if fps >= 30:
                tech_score += 0.3  # Smooth playback
            elif fps >= 24:
                tech_score += 0.2  # Acceptable
            elif fps >= 15:
                tech_score += 0.1  # Basic

        score += tech_score * 0.4
        factors += 0.4

        # Timeline completeness factor
        timeline = phase_eval.get("timeline_completeness", {})
        timeline_score = 0

        marker_count = timeline.get("total_markers", 0)
        if marker_count > 10:
            timeline_score += 0.3  # Good marker coverage
        elif marker_count > 5:
            timeline_score += 0.2  # Acceptable coverage
        elif marker_count > 0:
            timeline_score += 0.1  # Basic coverage

        density = timeline.get("marker_density", 0)
        if density > 2:  # More than 2 markers per minute
            timeline_score += 0.2  # Good density
        elif density > 1:
            timeline_score += 0.1  # Acceptable density

        score += timeline_score * 0.3
        factors += 0.3

        return min(1.0, score / max(factors, 0.1))  # Normalize to 0-1 range

    def add_comparative_analysis(self, evaluation: Dict[str, Any], all_evaluations: Dict[str, Any]) -> Dict[str, Any]:
        # Add comparative analysis showing how this run compares to others.
        if len(all_evaluations) <= 1:
            return evaluation

        # Calculate averages from other runs
        other_runs = [e for rid, e in all_evaluations.items() if rid != evaluation['run_id']]

        if not other_runs:
            return evaluation

        avg_quality = sum(e.get('metrics', {}).get('quality_score', 0) for e in other_runs) / len(other_runs)
        avg_phases = sum(e.get('metrics', {}).get('phases_completed', 0) for e in other_runs) / len(other_runs)

        current_quality = evaluation.get('metrics', {}).get('quality_score', 0)
        current_phases = evaluation.get('metrics', {}).get('phases_completed', 0)

        # Add comparative insights
        comparison = {
            "vs_average_quality": current_quality - avg_quality,
            "vs_average_phases": current_phases - avg_phases,
            "rank_among_peers": None  # Could implement ranking
        }

        evaluation.setdefault('metrics', {})['comparison'] = comparison
        return evaluation

    def analyze_audio_file(self, audio_file: Path) -> Dict[str, Any]:
        # Analyze individual audio file for technical metrics.
        try:
            import subprocess
            import re

            cmd = [
                "./node_modules/ffmpeg-static/ffmpeg",
                "-i", str(audio_file)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.run_path.parent.parent)
            output = result.stderr

            info = {
                "filename": audio_file.name,
                "file_size_kb": round(audio_file.stat().st_size / 1024, 1)
            }

            # Extract duration (format: Duration: 00:00:10.50)
            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', output)
            if duration_match:
                hours, minutes, seconds, centiseconds = map(int, duration_match.groups())
                info['duration'] = hours * 3600 + minutes * 60 + seconds + centiseconds / 100

            # Extract bitrate (format: bitrate: 128 kb/s)
            bitrate_match = re.search(r'bitrate: (\d+) kb/s', output)
            if bitrate_match:
                info['bitrate_kbps'] = int(bitrate_match.group(1))

            # Extract audio info (format: Audio: mp3, 44100 Hz, stereo)
            audio_match = re.search(r'Audio: (\w+), (\d+) Hz, (\w+)', output)
            if audio_match:
                info['codec'] = audio_match.group(1)
                info['sample_rate'] = int(audio_match.group(2))
                channels_text = audio_match.group(3)
                if channels_text == 'stereo':
                    info['channels'] = 2
                elif channels_text == 'mono':
                    info['channels'] = 1
                else:
                    info['channels'] = 1

            return info

        except Exception as e:
            # Fallback basic info
            return {
                "filename": audio_file.name,
                "file_size_kb": round(audio_file.stat().st_size / 1024, 1),
                "duration": 0,
                "bitrate_kbps": 0,
                "sample_rate": 0,
                "channels": 0,
                "codec": "unknown",
                "analysis_failed": True,
                "error": str(e)
            }

    def calculate_audio_quality_score(self, phase_eval: Dict[str, Any]) -> float:
        # Calculate audio quality score (0.0 to 1.0).
        score = 0.0
        factors = 0

        tech = phase_eval.get("technical_metrics", {})

        # Bitrate factor
        avg_bitrate = tech.get("avg_bitrate_kbps", 0)
        if avg_bitrate > 128:  # High quality
            score += 0.3
        elif avg_bitrate > 64:  # Good quality
            score += 0.2
        elif avg_bitrate > 32:  # Acceptable
            score += 0.1
        factors += 0.3

        # Sample rate factor
        avg_sample_rate = tech.get("avg_sample_rate", 0)
        if avg_sample_rate >= 44100:  # CD quality
            score += 0.3
        elif avg_sample_rate >= 22050:  # Acceptable
            score += 0.2
        elif avg_sample_rate >= 11025:  # Basic
            score += 0.1
        factors += 0.3

        # File size factor (reasonable size per segment)
        audio_files = tech.get("audio_files", [])
        if audio_files:
            avg_size_kb = sum(f.get("file_size_kb", 0) for f in audio_files) / len(audio_files)
            if 50 <= avg_size_kb <= 500:  # Reasonable size range
                score += 0.4
            elif 20 <= avg_size_kb <= 1000:  # Acceptable range
                score += 0.2
        factors += 0.4

        return min(1.0, score / max(factors, 0.1))

    def analyze_audio_video_sync(self) -> Dict[str, Any]:
        # Analyze synchronization between audio and video timeline.
        analysis = {
            "sync_accuracy_ms": None,
            "timeline_coverage": 0,
            "issues": []
        }

        try:
            # Read timeline and check audio placements
            timeline_file = self.run_path / "timeline.md"
            if not timeline_file.exists():
                return analysis

            with open(timeline_file, 'r') as f:
                timeline_content = f.read()

            # Parse timeline markers
            markers = {}
            for line in timeline_content.split('\n'):
                if '|' in line and len(line.strip()) > 10:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 3:
                        try:
                            marker_name = parts[1]
                            time_s = float(parts[2])
                            markers[marker_name] = time_s
                        except ValueError:
                            continue

            if not markers:
                return analysis

            # Check audio directory for sync information
            audio_dir = self.run_path / "audio"
            if audio_dir.exists():
                audio_files = list(audio_dir.glob("*.mp3"))
                analysis["timeline_coverage"] = len(audio_files) / max(len(markers), 1)

            # Estimate sync accuracy (simplified - in practice would need more complex analysis)
            analysis["sync_accuracy_ms"] = 100  # Placeholder - would need actual sync measurement

        except Exception:
            pass

        return analysis

    def check_audio_issues(self, phase_eval: Dict[str, Any]):
        # Check for common audio-related issues.
        tech = phase_eval.get("technical_metrics", {})

        # Check bitrate consistency
        audio_files = tech.get("audio_files", [])
        if len(audio_files) > 1:
            bitrates = [f.get("bitrate_kbps", 0) for f in audio_files]
            if bitrates:
                bitrate_range = max(bitrates) - min(bitrates)
                if bitrate_range > 50:  # Significant variation
                    phase_eval["issues"].append(f"Audio bitrate varies significantly ({bitrate_range}kbps range)")

        # Check sample rate consistency
        sample_rates = [f.get("sample_rate", 0) for f in audio_files if f.get("sample_rate", 0) > 0]
        if len(set(sample_rates)) > 1:
            phase_eval["issues"].append("Inconsistent audio sample rates across segments")

        # Check for very short audio segments
        for audio_file in audio_files:
            duration = audio_file.get("duration", 0)
            if duration < 1.0:  # Less than 1 second
                phase_eval["issues"].append(f"Very short audio segment: {audio_file['filename']} ({duration:.1f}s)")
                break  # Only report first occurrence

    def analyze_composition_quality(self, final_file: Path) -> Dict[str, Any]:
        # Analyze the quality of the final composed video.
        analysis = {
            "compression_efficiency": 0,
            "audio_video_sync": "unknown",
            "artifacts_detected": 0
        }

        try:
            # Compare final file size to raw recording size
            raw_dir = self.run_path / "raw"
            raw_recording = raw_dir / "recording.webm"
            if raw_recording.exists():
                raw_size = raw_recording.stat().st_size
                final_size = final_file.stat().st_size

                if raw_size > 0:
                    compression_ratio = final_size / raw_size
                    analysis["compression_efficiency"] = round(compression_ratio, 3)

                    # Ideal compression: 0.3-0.7 (30-70% of original)
                    if 0.3 <= compression_ratio <= 0.7:
                        analysis["compression_quality"] = "optimal"
                    elif compression_ratio < 0.3:
                        analysis["compression_quality"] = "over_compressed"
                    else:
                        analysis["compression_quality"] = "under_compressed"

            # Check for audio sync issues (simplified)
            analysis["audio_video_sync"] = "estimated_good"  # Would need complex analysis

        except Exception:
            pass

        return analysis

    def analyze_composition_performance(self) -> Dict[str, Any]:
        # Analyze performance aspects of the composition.
        analysis = {
            "processing_efficiency": 0,
            "file_size_optimization": 0
        }

        try:
            # Analyze intermediate files to understand processing efficiency
            raw_dir = self.run_path / "raw"
            final_file = self.run_path / "final.mp4"

            if raw_dir.exists() and final_file.exists():
                # Count processing steps by intermediate files
                intermediate_files = []
                for pattern in ["*.mp4", "*.webm"]:
                    intermediate_files.extend(list(self.run_path.glob(f"**/{pattern}")))

                # Remove raw and final files from count
                raw_files = list(raw_dir.glob("*"))
                intermediate_files = [f for f in intermediate_files if f not in raw_files and f != final_file]

                analysis["processing_steps"] = len(intermediate_files)
                analysis["processing_efficiency"] = min(1.0, 1.0 / max(len(intermediate_files), 1))

        except Exception:
            pass

        return analysis

    def check_composition_issues(self, phase_eval: Dict[str, Any]):
        # Check for composition-related issues.
        quality = phase_eval.get("quality_metrics", {})

        # Check compression efficiency
        compression = quality.get("compression_efficiency", 0)
        if compression > 0:
            if compression < 0.1:  # Over-compressed
                phase_eval["issues"].append(f"Video heavily compressed ({compression:.1%} of original size)")
            elif compression > 0.9:  # Under-compressed
                phase_eval["issues"].append(f"Video insufficiently compressed ({compression:.1%} of original size)")

        # Check technical metrics
        tech = phase_eval.get("technical_metrics", {})
        duration = tech.get("duration", 0)
        if duration < 10:  # Very short video
            phase_eval["issues"].append(f"Final video unusually short ({duration:.1f}s)")

        # Check bitrate
        bitrate = tech.get("bitrate", 0)
        if bitrate < 500:  # Very low bitrate
            phase_eval["issues"].append(f"Final video bitrate very low ({bitrate}kbps)")
        elif bitrate > 20000:  # Extremely high bitrate
            phase_eval["issues"].append(f"Final video bitrate extremely high ({bitrate}kbps)")

    def calculate_composition_quality_score(self, phase_eval: Dict[str, Any]) -> float:
        # Calculate composition quality score (0.0 to 1.0).
        score = 0.0
        factors = 0

        # File size factor
        file_size_mb = phase_eval.get("final_size_mb", 0)
        if 10 <= file_size_mb <= 200:  # Reasonable video size range
            score += 0.3
        elif 5 <= file_size_mb <= 500:  # Acceptable range
            score += 0.15
        factors += 0.3

        # Quality metrics factor
        quality = phase_eval.get("quality_metrics", {})
        quality_score = 0

        compression_eff = quality.get("compression_efficiency", 0)
        if 0.3 <= compression_eff <= 0.7:  # Optimal compression
            quality_score += 0.4
        elif 0.1 <= compression_eff <= 0.9:  # Acceptable compression
            quality_score += 0.2

        score += quality_score * 0.4
        factors += 0.4

        # Technical metrics factor
        tech = phase_eval.get("technical_metrics", {})
        tech_score = 0

        # Duration check
        duration = tech.get("duration", 0)
        if duration > 30:  # Reasonable length
            tech_score += 0.2
        elif duration > 10:
            tech_score += 0.1

        # Bitrate check
        bitrate = tech.get("bitrate", 0)
        if 1000 <= bitrate <= 10000:  # Reasonable bitrate range
            tech_score += 0.3
        elif 500 <= bitrate <= 20000:  # Acceptable range
            tech_score += 0.15

        score += tech_score * 0.3
        factors += 0.3

        return min(1.0, score / max(factors, 0.1))




def find_runs(status_filter: Optional[str] = None,
              since: Optional[str] = None,
              until: Optional[str] = None,
              limit: int = 10) -> List[Dict[str, Any]]:
    # Find runs based on filters from central evaluations file.
    central_file = Path("evaluations.md")
    if not central_file.exists():
        return []

    try:
        with open(central_file, 'r') as f:
            content = f.read()

        # Parse all evaluations from central file
        all_evaluations = {}
        current_eval = {}
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if line.startswith('## ') and ' - ' in line:
                # Save previous evaluation if exists
                if current_eval and 'run_id' in current_eval:
                    all_evaluations[current_eval['run_id']] = current_eval

                # Start new evaluation
                run_id = line.split(' - ')[0].replace('## ', '')
                current_eval = {'run_id': run_id}

                # Extract status from the line
                if '✅' in line:
                    current_eval['status'] = 'success'
                elif '⚠️' in line:
                    current_eval['status'] = 'partial_success'
                elif '❌' in line:
                    current_eval['status'] = 'failure'

                # Look for timestamp in next few lines
                for j in range(i+1, min(i+10, len(lines))):
                    if lines[j].strip().startswith('**Timestamp:**'):
                        current_eval['timestamp'] = lines[j].strip().replace('**Timestamp:** ', '')
                        break

                # Look for quality score
                for j in range(i+1, min(i+20, len(lines))):
                    if lines[j].strip().startswith('- **Quality Score:**'):
                        score_text = lines[j].strip().replace('- **Quality Score:** ', '').replace('/1.0', '')
                        try:
                            current_eval['metrics'] = {'quality_score': float(score_text)}
                        except:
                            current_eval['metrics'] = {'quality_score': 0.0}
                        break

        # Add the last evaluation
        if current_eval and 'run_id' in current_eval:
            all_evaluations[current_eval['run_id']] = current_eval

        # Convert to list and apply filters
        runs = list(all_evaluations.values())

        # Apply status filter
        if status_filter:
            runs = [r for r in runs if r.get("status") == status_filter]

        # Apply date filters (simplified - would need better parsing)
        if since or until:
            filtered_runs = []
            for run in runs:
                try:
                    timestamp = run.get('timestamp', '')
                    if timestamp:
                        # Simple date check - could be improved
                        if since and timestamp < since:
                            continue
                        if until and timestamp > until:
                            continue
                    filtered_runs.append(run)
                except:
                    filtered_runs.append(run)
            runs = filtered_runs

        # Sort by timestamp (newest first) and limit
        runs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return runs[:limit]

    except Exception:
        return []


def find_last_run() -> Optional[str]:
    # Find the most recent run ID.
    runs_dir = Path("videos/runs")
    if not runs_dir.exists():
        return None

    # Look for the most recent directory
    run_dirs = sorted(runs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
    for run_dir in run_dirs:
        if run_dir.is_dir():
            # Check if it has a final.mp4 (indicating a completed run)
            if (run_dir / "final.mp4").exists():
                return run_dir.name

    return None




def cmd_evaluate(args) -> Dict[str, Any]:
    # Evaluate a run.
    import time
    start_time = time.time()

    run_id = args.run_id

    if args.last:
        run_id = find_last_run()
        if not run_id:
            return {
                "success": False,
                "error": "No completed runs found",
                "code": "NO_RUNS_FOUND"
            }

    if not run_id:
        return {
            "success": False,
            "error": "Must specify --run-id or use --last",
            "code": "MISSING_RUN_ID"
        }

    evaluator = RunEvaluator(run_id)
    result = evaluator.evaluate_run(detailed=args.detailed)

    # Add evaluation performance
    evaluation_time = time.time() - start_time
    if result.get("success") and result.get("evaluation"):
        result["evaluation"]["performance"] = {
            "evaluation_time_seconds": round(evaluation_time, 2)
        }

    if not result.get("success"):
        return result

    # Create human-readable output
    evaluation = result["evaluation"]

    status_emoji = {
        "success": "✅",
        "partial_success": "⚠️",
        "failure": "❌"
    }

    status = evaluation['status']
    emoji = status_emoji.get(status, "❓")

    output_lines = [
        f"🎯 Run Evaluation: {run_id}",
        "=" * 50,
        "",
        f"Status: {emoji} {status.replace('_', ' ').title()}",
        "",
        "📊 Metrics:",
        f"• Quality Score: {evaluation.get('metrics', {}).get('quality_score', 0):.2f}/1.0",
        f"• Phases Completed: {evaluation.get('metrics', {}).get('phases_completed', 0)}/4",
        f"• Total Size: {evaluation.get('metrics', {}).get('total_size_mb', 0):.1f} MB",
    ]

    # Add comparative analysis if available
    comparison = evaluation.get('metrics', {}).get('comparison')
    if comparison:
        quality_diff = comparison.get('vs_average_quality', 0)
        if quality_diff > 0.1:
            output_lines.append(f"• Performance: 🟢 Above average (+{quality_diff:.2f})")
        elif quality_diff < -0.1:
            output_lines.append(f"• Performance: 🔴 Below average ({quality_diff:.2f})")
        else:
            output_lines.append("• Performance: 🟡 Average compared to other runs")
        output_lines.append("")
        output_lines.append("🔍 Issues Found:")
    else:
        output_lines.append("")
        output_lines.append("🔍 Issues Found:")

    issues = evaluation.get('issues', [])
    if issues:
        for issue in issues[:5]:  # Limit to 5 issues
            output_lines.append(f"• {issue}")
        if len(issues) > 5:
            output_lines.append(f"• ... and {len(issues) - 5} more")
    else:
        output_lines.append("• None")

    recommendations = evaluation.get('recommendations', [])
    if recommendations:
        output_lines.append("")
        output_lines.append("💡 Recommendations:")
        for rec in recommendations[:5]:  # Limit to 5 recommendations
            output_lines.append(f"• {rec}")
        if len(recommendations) > 5:
            output_lines.append(f"• ... and {len(recommendations) - 5} more")

    output_lines.append("")
    output_lines.append("📁 Full report saved to: evaluations.md")

    # Replace the JSON result with formatted text
    result["_formatted_output"] = "\n".join(output_lines)
    result["_is_text_output"] = True

    return result


def cmd_list(args) -> Dict[str, Any]:
    # List runs with filtering.
    runs = find_runs(
        status_filter=args.status,
        since=args.since,
        until=args.until,
        limit=args.limit
    )

    return {
        "success": True,
        "runs": runs,
        "count": len(runs),
        "filters": {
            "status": args.status,
            "since": args.since,
            "until": args.until,
            "limit": args.limit
        }
    }


def cmd_summary(args) -> Dict[str, Any]:
    # Show summary of evaluations.
    if args.run_id:
        # Summary for specific run
        evaluator = RunEvaluator(args.run_id)
        if not evaluator.run_path.exists():
            return {
                "success": False,
                "error": f"Run not found: {args.run_id}",
                "code": "RUN_NOT_FOUND"
            }

        eval_file = evaluator.evaluation_path / ".run_evaluation.json"
        if not eval_file.exists():
            return {
                "success": False,
                "error": f"No evaluation found for run: {args.run_id}",
                "code": "NO_EVALUATION"
            }

        with open(eval_file, 'r') as f:
            evaluation = json.load(f)

        return {
            "success": True,
            "run_id": args.run_id,
            "summary": evaluation
        }

    else:
        # Summary of recent runs
        since_date = datetime.now() - timedelta(days=args.days)
        runs = find_runs(since=since_date.isoformat().split('T')[0])

        summary = {
            "total_runs": len(runs),
            "success_rate": 0.0,
            "avg_quality_score": 0.0,
            "total_duration_s": 0,
            "status_breakdown": {}
        }

        if runs:
            success_count = sum(1 for r in runs if r.get("status") == "success")
            summary["success_rate"] = success_count / len(runs)

            quality_scores = [r.get("metrics", {}).get("quality_score", 0) for r in runs]
            summary["avg_quality_score"] = sum(quality_scores) / len(quality_scores)

            summary["total_duration_s"] = sum(r.get("duration_total_s", 0) for r in runs if r.get("duration_total_s"))

            # Status breakdown
            for run in runs:
                status = run.get("status", "unknown")
                summary["status_breakdown"][status] = summary["status_breakdown"].get(status, 0) + 1

        return {
            "success": True,
            "period_days": args.days,
            "summary": summary
        }


def cmd_dashboard(args) -> Dict[str, Any]:
    # Generate HTML dashboard of runs.
    runs = find_runs(limit=args.limit)

    # Generate HTML dashboard
    html_content = generate_html_dashboard(runs)

    # Write to file
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        f.write(html_content)

    return {
        "success": True,
        "output_file": str(output_path),
        "runs_count": len(runs),
        "message": f"Dashboard generated with {len(runs)} runs"
    }


def generate_html_dashboard(runs: List[Dict[str, Any]]) -> str:
    """Generate ultra-minimalistic HTML dashboard - just the table."""
    html_parts = ['<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Runs Dashboard</title>']
    html_parts.append('<style>body{font-family:monospace;margin:0;padding:10px}')
    html_parts.append('table{width:100%;border-collapse:collapse}')
    html_parts.append('th,td{padding:8px;text-align:left;border-bottom:1px solid #ddd}')
    html_parts.append('th{background:#f0f0f0;font-weight:bold}tr:hover{background:#f9f9f9}')
    html_parts.append('.status-success{color:#0a0}.status-warning{color:#fa0}.status-error{color:#a00}')
    html_parts.append('a{color:#0066cc;text-decoration:none}a:hover{text-decoration:underline}')
    html_parts.append('</style></head><body><table><tr><th>Run ID</th><th>Status</th><th>Time</th><th>Quality</th></tr>')

    # Status emoji mapping
    status_emoji = {"success": "✅", "partial_success": "⚠️", "failure": "❌"}

    for run in runs:
        run_id = run.get('run_id', 'unknown')
        status = run.get('status', 'unknown')
        emoji = status_emoji.get(status, "❓")

        timestamp = run.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp_display = dt.strftime('%Y-%m-%d %H:%M')
            except:
                timestamp_display = timestamp[:16]
        else:
            timestamp_display = 'unknown'

        quality_score = run.get('metrics', {}).get('quality_score', 0)

        # Color coding for status
        status_class = {
            "success": "status-success",
            "partial_success": "status-warning",
            "failure": "status-error"
        }.get(status, "status-unknown")

        html_parts.append('<tr><td><a href="evaluations.md#{run_id}">{run_id}</a></td>'.format(run_id=run_id))
        html_parts.append('<td><span class="{}">{}</span></td>'.format(status_class, emoji + " " + status.replace('_', ' ').title()))
        html_parts.append('<td>{}</td>'.format(timestamp_display))
        html_parts.append('<td>{:.2f}</td></tr>'.format(quality_score))

    html_parts.append('</table></body></html>')
    return ''.join(html_parts)
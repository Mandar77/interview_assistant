"""
Question Generation Stream Test - Test SSE progress updates
Location: backend/tests/test_question_stream.py

Run with: python tests/test_question_stream.py
"""

import httpx
import json
import sys


def test_question_stream():
    """Test the SSE streaming endpoint for question generation."""
    
    url = "http://localhost:8000/api/v1/questions/generate-stream"
    
    payload = {
        "job_description": "Looking for a Python developer with FastAPI and PostgreSQL experience. Must understand REST APIs and microservices.",
        "interview_type": "technical",
        "difficulty": "medium",
        "num_questions": 2
    }
    
    print("=" * 60)
    print("Testing Question Generation with Progress Streaming")
    print("=" * 60)
    print(f"\nEndpoint: {url}")
    print(f"Generating {payload['num_questions']} {payload['interview_type']} questions...")
    print("-" * 60)
    
    try:
        with httpx.stream(
            "POST",
            url,
            json=payload,
            timeout=120.0  # 2 minute timeout
        ) as response:
            
            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code}")
                print(response.text)
                return
            
            questions = None
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                # Parse SSE format
                if line.startswith("event:"):
                    event_type = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    data_str = line.replace("data:", "").strip()
                    try:
                        data = json.loads(data_str)
                        
                        status = data.get("status", "unknown")
                        message = data.get("message", "")
                        progress = data.get("progress", 0)
                        
                        # Progress bar
                        bar_width = 30
                        filled = int(bar_width * progress / 100)
                        bar = "█" * filled + "░" * (bar_width - filled)
                        
                        print(f"\r[{bar}] {progress:3d}% | {status}: {message}", end="")
                        
                        if status == "complete":
                            questions = data.get("questions", [])
                            print()  # New line after progress
                            
                        elif status == "error":
                            print(f"\n\n❌ Error: {message}")
                            return
                            
                    except json.JSONDecodeError:
                        pass
            
            print("\n" + "-" * 60)
            
            if questions:
                print(f"\n✅ Successfully generated {len(questions)} questions:\n")
                for i, q in enumerate(questions, 1):
                    print(f"Question {i}:")
                    print(f"  {q.get('question', 'N/A')[:100]}...")
                    print(f"  Type: {q.get('interview_type')}, Difficulty: {q.get('difficulty')}")
                    print(f"  Skills: {', '.join(q.get('skill_tags', []))}")
                    print()
            else:
                print("\n⚠️ No questions returned")
                
    except httpx.TimeoutException:
        print("\n\n❌ Request timed out (>120 seconds)")
        print("This may indicate Ollama is running very slowly on your hardware.")
        print("Try using a smaller model: ollama pull llama3.2:1b")
        
    except httpx.ConnectError:
        print("\n\n❌ Could not connect to backend")
        print("Make sure the server is running: cd backend && python app.py")
        
    except Exception as e:
        print(f"\n\n❌ Error: {e}")


def test_with_curl_command():
    """Print curl command for manual testing."""
    print("\n" + "=" * 60)
    print("Manual Testing with curl")
    print("=" * 60)
    print("""
Run this command to test SSE streaming manually:

curl -N -X POST "http://localhost:8000/api/v1/questions/generate-stream" \\
  -H "Content-Type: application/json" \\
  -d '{"job_description": "Python developer", "interview_type": "technical", "difficulty": "medium", "num_questions": 1}'

You should see progress events like:
  event: progress
  data: {"status": "parsing_skills", "progress": 10, ...}
  
  event: progress
  data: {"status": "generating_questions", "progress": 60, ...}
  
  event: complete
  data: {"status": "complete", "questions": [...], "progress": 100}
""")


if __name__ == "__main__":
    # Check if httpx is installed
    try:
        import httpx
    except ImportError:
        print("Installing httpx...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
        import httpx
    
    test_question_stream()
    test_with_curl_command()
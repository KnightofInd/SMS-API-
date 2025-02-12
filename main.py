from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
import google.generativeai as genai
import json
import re
import os
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(title="Educational Content Generator API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyCINy1sxflACSJFOl9VvhaLoMLjLmsk5EU"
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel('gemini-pro')

# Output JSON file path
OUTPUT_FILE = "data.json"

def clean_json_response(text: str) -> dict:
    """Extract JSON data from the response text."""
    json_match = re.search(r'[\[\{].*[\]\}]', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    code_block_match = re.search(r'```(?:json)?(.*?)```', text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"Could not extract valid JSON from response: {text[:200]}...")

def validate_mcq_data(mcq_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate and fix MCQ data."""
    validated_mcqs = []
    for mcq in mcq_list:
        validated_mcq = {
            "question": mcq.get("question", ""),
            "options": mcq.get("options", []),
            "correct_answer": mcq.get("correct_answer", ""),
            "explanation": mcq.get("explanation", "No explanation provided")
        }
        if not isinstance(validated_mcq["options"], list):
            validated_mcq["options"] = []
        while len(validated_mcq["options"]) < 4:
            validated_mcq["options"].append(f"Option {len(validated_mcq['options']) + 1}")
        if validated_mcq["correct_answer"] not in validated_mcq["options"]:
            validated_mcq["correct_answer"] = validated_mcq["options"][0]
        validated_mcqs.append(validated_mcq)
    
    return validated_mcqs

class MCQQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    model_config = ConfigDict(extra='allow')

class CaseStudy(BaseModel):
    scenario: str
    question: str
    answer: str
    model_config = ConfigDict(extra='allow')

class TopicRequest(BaseModel):
    topic: str
    context: Optional[str] = None
    model_config = ConfigDict(extra='allow')

class EducationalContent(BaseModel):
    main_content: str
    mcq_questions: List[MCQQuestion]
    case_studies: List[CaseStudy]
    model_config = ConfigDict(extra='allow')

def generate_main_content(topic: str, context: Optional[str] = None) -> str:
    """Generate the main educational content"""
    prompt = f"""
    Create comprehensive educational content about {topic}.
    {f'Additional context: {context}' if context else ''}

    The content should:
    1. Be at least 500 words
    2. Be structured with clear sections
    3. Include examples and explanations
    4. Be suitable for students
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {str(e)}")

def generate_mcq_questions(topic: str, content: str) -> List[Dict[str, Any]]:
    """Generate MCQ questions based on the content"""
    prompt = f"""
    Create exactly 10 multiple choice questions (MCQs) about {topic} based on this content:

    {content}

    Return ONLY a JSON array with this structure:
    [
        {{
            "question": "Write your question here",
            "options": ["first option", "second option", "third option", "fourth option"],
            "correct_answer": "exact text of the correct option",
            "explanation": "Detailed explanation of why this answer is correct"
        }},
        // ... repeat for all 10 questions
    ]
    """
    
    try:
        response = model.generate_content(prompt)
        mcq_data = clean_json_response(response.text)
        validated_mcqs = validate_mcq_data(mcq_data)
        return validated_mcqs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating MCQs: {str(e)}")

def generate_case_studies(topic: str, content: str) -> List[Dict[str, Any]]:
    """Generate case study questions"""
    prompt = f"""
    Create exactly 3 case study questions about {topic} based on this content:

    {content}

    Return ONLY a JSON array with this structure:
    [
        {{
            "scenario": "Detailed case scenario description",
            "question": "Specific question about the scenario",
            "answer": "Detailed explanation and analysis"
        }},
        // ... repeat for all 3 case studies
    ]
    """
    
    try:
        response = model.generate_content(prompt)
        case_studies = clean_json_response(response.text)
        validated_cases = [{"scenario": cs.get("scenario", "Scenario not provided"),
                            "question": cs.get("question", "Question not provided"),
                            "answer": cs.get("answer", "Answer not provided")} 
                           for cs in case_studies]
        return validated_cases
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating case studies: {str(e)}")

@app.post("/generate", response_model=EducationalContent)
async def generate_educational_content(request: TopicRequest):
    """Generate complete educational content and save to JSON file"""
    try:
        content = generate_main_content(request.topic, request.context)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                mcqs = generate_mcq_questions(request.topic, content)
                break
            except Exception:
                if attempt == max_retries - 1:
                    raise
                continue

        for attempt in range(max_retries):
            try:
                case_studies = generate_case_studies(request.topic, content)
                break
            except Exception:
                if attempt == max_retries - 1:
                    raise
                continue

        response = EducationalContent(
            main_content=content,
            mcq_questions=[MCQQuestion(**q) for q in mcqs],
            case_studies=[CaseStudy(**cs) for cs in case_studies]
        )

        response_dict = response.dict()

        with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
            json.dump(response_dict, file, indent=4, ensure_ascii=False)

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating educational content: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

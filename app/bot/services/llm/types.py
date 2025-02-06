from typing import Dict, List, Optional, TypedDict

class InterviewConfig(TypedDict):
    bot_name: str
    company_name: str
    job_title: str
    company_context: str
    job_description: str
    interview_questions: List[str]

class InterviewState(TypedDict):
    messages: List[Dict[str, str]]
    next_question_index: int
    interview_config: InterviewConfig
    current_topic: Optional[str] 
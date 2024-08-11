
from typing import Optional    

def get_response(user_input: str) -> Optional[str]:
    lowered = user_input.lower()

    if "zdravo" in lowered:
        return "Zdravo brat!"
    
    return None
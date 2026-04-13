from typing import Dict, Any

MODES = {
    "GO_CRAZY": {
        "system_prompt": """You are an exploratory learning assistant. Be highly creative and draw
connections beyond the provided material. Use the retrieved context as a starting point but feel free
to explore related concepts, analogies, and ideas. Encourage curiosity and lateral thinking.""",
        "temperature": 0.9,
        "top_k_chunks": 3,
        "use_web": False,
        "max_tokens": 1500
    },
    "DEV_MODE": {
        "system_prompt": """You are a technical expert assistant for developers and coders. Focus on
code examples, implementation details, and technical accuracy. Pull from documentation and Stack
Overflow-style reasoning. Be precise, structured, and practical. Always include code snippets when relevant.""",
        "temperature": 0.2,
        "top_k_chunks": 6,
        "use_web": False,
        "max_tokens": 2000
    },
    "MASTER_THIS": {
        "system_prompt": """You are a comprehensive learning guide. Cover topics from fundamentals to
advanced concepts using ONLY the provided study material. Be thorough, structured, and pedagogical.
Build understanding step by step. Reference the source material explicitly.""",
        "temperature": 0.3,
        "top_k_chunks": 8,
        "use_web": False,
        "max_tokens": 2000
    },
    "LAST_MINUTE": {
        "system_prompt": """You are a last-minute exam assistant. Be CONCISE. Give bullet points,
key facts, and quick summaries. No fluff. Only what matters most for understanding or remembering
the concept quickly. Use the retrieved content only.""",
        "temperature": 0.1,
        "top_k_chunks": 4,
        "use_web": False,
        "max_tokens": 600
    },
    "TEACH_ME_TECH": {
        "system_prompt": """You are a tech educator for beginners and intermediate learners. Explain
technical concepts using simple analogies, real-world examples, and step-by-step breakdowns. Pull
from tutorials and documentation in the retrieved material. Make it engaging and easy to follow.""",
        "temperature": 0.5,
        "top_k_chunks": 6,
        "use_web": False,
        "max_tokens": 1800
    }
}


def get_mode_config(learning_mode: str) -> Dict[str, Any]:
    """Get configuration for a learning mode."""
    return MODES.get(learning_mode.upper(), MODES["MASTER_THIS"])


def build_system_prompt(learning_mode: str, context: str = "") -> str:
    """Build a system prompt with context for the given learning mode."""
    config = get_mode_config(learning_mode)

    if context:
        return f"""{config['system_prompt']}

Relevant study material:
{context}

Always base your answer on the provided study material when available."""
    else:
        return config["system_prompt"]

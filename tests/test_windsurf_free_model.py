import logging
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from providers.windsurf import WindsurfLLM

logger = logging.getLogger(Path(__file__).stem)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)


# Test Windsurf provider with free model
def test_windsurf_free_model():
    llm = WindsurfLLM(model_name="deepseek-v3")
    messages = [
        SystemMessage(content="Ти корисний асистент. Відповідай українською."),
        HumanMessage(content="Привіт! Як справи?"),
    ]
    response = llm.invoke(messages)
    logger.info("Відповідь від вільного моделі:")
    logger.info(response.content)


if __name__ == "__main__":
    test_windsurf_free_model()

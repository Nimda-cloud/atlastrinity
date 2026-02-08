from providers.windsurf import WindsurfLLM
from langchain_core.messages import SystemMessage, HumanMessage

# Test Windsurf provider with free model
def test_windsurf_free_model():
    llm = WindsurfLLM(model_name="deepseek-v3")
    
    messages = [
        SystemMessage(content="Ти корисний асистент. Відповідай українською."),
        HumanMessage(content="Привіт! Як справи?")
    ]
    
    response = llm.invoke(messages)
    print("Відповідь від вільного моделі:")
    print(response.content)

if __name__ == "__main__":
    test_windsurf_free_model()

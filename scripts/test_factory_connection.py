# Add project root and src to path
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from providers.factory import create_llm, get_provider_name  # type: ignore

print(f"Current Provider Name: {get_provider_name()}")

try:
    llm = create_llm(model_name="deepseek-v3")
    print(f"Created LLM Type: {type(llm)}")
    print(f"LLM Model Name: {llm.model_name}")
    print(f"LLM Proxy URL: {getattr(llm, 'proxy_url', 'N/A')}")
except Exception as e:
    print(f"Error creating LLM: {e}")

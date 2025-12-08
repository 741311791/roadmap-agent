# To install: pip install tavily-python
from tavily import TavilyClient
client = TavilyClient("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")
response = client.search(
    query="langgraph教程",
    search_depth="advanced",
    time_range="year",
    include_domains=["github.com"]
)
print(response)
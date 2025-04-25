import json
from typing import List

from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from pydantic import BaseModel, Field


class TextSummary(BaseModel):
    summary_nl: str = Field(description="Brief summary of the text in Dutch")
    summary_fr: str = Field(description="Brief summary of the text in French")
    topics: List[str] = Field(description="Main topics discussed in the text")

    class Config:
        json_schema_extra = {
            "summary_nl": "Deze tekst bespreekt impact van klimaatverandering.",
            "summary_fr": "Ce texte traite de l'impact du changement climatique.",
            "topics": ["climate", "environment", "policy"]
        }


class Summarizer2():
    def __init__(self, model_name="llama3"):
        # Initialize the Ollama model
        llm = OllamaLLM(model=model_name)

        prompt_template = """
        Analyze and summarize the following text in a structured format:

        {text}

        {format_instructions}
        """

        self.parser = PydanticOutputParser(pydantic_object=TextSummary)

        # Create the prompt with format instructions
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["text"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

        # Create the chain
        self.chain = prompt | llm

    def summarize(self, text):
        result = self.chain.invoke(input=text)

        return self.parser.parse(result)


# Example usage
if __name__ == "__main__":
    sample_text = """
    Climate change is one of the most pressing challenges of our time. Global temperatures
    have risen by about 1 degree Celsius since pre-industrial times, primarily due to
    human activities such as burning fossil fuels and deforestation. This warming has led
    to more frequent and severe weather events, rising sea levels, and disruptions to
    ecosystems worldwide. Scientists warn that without significant reductions in greenhouse
    gas emissions, these trends will accelerate, potentially leading to catastrophic outcomes.
    Governments, businesses, and individuals must take immediate action to transition to
    renewable energy sources, improve energy efficiency, and adapt to the changes already underway.
    """

    summary = Summarizer2().summarize(sample_text)

    if summary:
        # Print formatted output
        print("=== STRUCTURED SUMMARY ===")
        print(f"Summary Dutch: {summary.summary_nl}")
        print(f"Summary French: {summary.summary_fr}")
        print("\nTopics:")
        for topic in summary.topics:
            print(f"- {topic}")

        # Also output as JSON
        print("\n=== JSON OUTPUT ===")
        print(json.dumps(summary.model_dump(), indent=2))

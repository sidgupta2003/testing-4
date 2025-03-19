from transformers import pipeline
from django.conf import settings

class AIHelper:
    def __init__(self):
        # Initialize various pipelines
        self.sentiment_analyzer = pipeline("sentiment-analysis")
        self.text_generator = pipeline("text-generation")
        self.summarizer = pipeline("summarization")
        self.question_answerer = pipeline("question-answering")
    
    def analyze_sentiment(self, text):
        """Analyze the sentiment of given text"""
        try:
            result = self.sentiment_analyzer(text)
            return result[0]
        except Exception as e:
            return {"error": str(e)}
    
    def generate_text(self, prompt, max_length=100):
        """Generate text based on a prompt"""
        try:
            result = self.text_generator(prompt, max_length=max_length)
            return result[0]["generated_text"]
        except Exception as e:
            return {"error": str(e)}
    
    def summarize_text(self, text, max_length=130, min_length=30):
        """Summarize long text"""
        try:
            result = self.summarizer(text, max_length=max_length, min_length=min_length)
            return result[0]["summary_text"]
        except Exception as e:
            return {"error": str(e)}
    
    def answer_question(self, context, question):
        """Answer questions based on context"""
        try:
            result = self.question_answerer(question=question, context=context)
            return result
        except Exception as e:
            return {"error": str(e)}

# Create a singleton instance
ai_helper = AIHelper() 
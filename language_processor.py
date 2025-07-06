"""
Language Processor - Croatian normalization using LLM intelligence
Mango in Bulgaria compliant: No hardcoded patterns, pure LLM processing
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from openai import OpenAI
import json
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LanguageProcessor:
    """
    Language processing using pure LLM intelligence
    No hardcoded Croatian patterns - works for any language
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-4"
        
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process query to extract entities and normalize language
        Pure LLM approach - no hardcoded patterns
        
        Args:
            query: User query in any language
            
        Returns:
            Processed query with entities and normalized form
        """
        try:
            prompt = self._build_processing_prompt()
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "original_query": query,
                "language": result.get("language", "hr"),
                "normalized_query": result.get("normalized_query", query),
                "entities": result.get("entities", {}),
                "intent": result.get("intent", "unknown"),
                "agricultural_terms": result.get("agricultural_terms", []),
                "requires_clarification": result.get("requires_clarification", False),
                "clarification_questions": result.get("clarification_questions", [])
            }
            
        except Exception as e:
            logger.error(f"Language processing error: {str(e)}")
            return {
                "original_query": query,
                "language": "unknown",
                "normalized_query": query,
                "entities": {},
                "error": str(e)
            }
    
    async def extract_agricultural_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract agricultural entities from text
        Works for any language through LLM intelligence
        """
        try:
            prompt = """Extract agricultural entities from the text.
Return JSON with these categories:
{
    "crops": ["list of crops mentioned"],
    "chemicals": ["pesticides, fertilizers mentioned"],
    "fields": ["field names or references"],
    "quantities": ["amounts with units"],
    "dates": ["dates or time periods"],
    "activities": ["farming activities mentioned"],
    "problems": ["pests, diseases, issues mentioned"]
}

Be inclusive - extract both standard names and local variations."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            entities = json.loads(response.choices[0].message.content)
            return entities
            
        except Exception as e:
            logger.error(f"Entity extraction error: {str(e)}")
            return {
                "crops": [],
                "chemicals": [],
                "fields": [],
                "quantities": [],
                "dates": [],
                "activities": [],
                "problems": []
            }
    
    async def generate_response(self, 
                              query: str, 
                              answer_data: Dict[str, Any],
                              language: str = "hr") -> str:
        """
        Generate natural language response
        Adapts to user's language automatically
        """
        try:
            # Build response generation prompt
            prompt = f"""Generate a helpful agricultural response.
User language: {language}
User query: {query}

Information to convey:
{json.dumps(answer_data, ensure_ascii=False, indent=2)}

Guidelines:
1. Match the user's language and formality level
2. Be concise but complete
3. Include specific agricultural advice
4. If discussing chemicals/pesticides, always mention safety periods
5. Use local agricultural terms when appropriate

Generate a natural, helpful response."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an agricultural assistant helping farmers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7  # Higher temperature for more natural responses
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Response generation error: {str(e)}")
            # Fallback response
            return self._generate_fallback_response(query, answer_data, language)
    
    async def detect_language(self, text: str) -> str:
        """
        Detect language of text
        Returns ISO language code
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Faster model for simple task
                messages=[
                    {
                        "role": "system", 
                        "content": "Detect the language of the text. Return only the 2-letter ISO code (e.g., 'hr' for Croatian, 'en' for English, 'sl' for Slovenian)."
                    },
                    {"role": "user", "content": text}
                ],
                temperature=0
            )
            
            lang_code = response.choices[0].message.content.strip().lower()
            return lang_code if len(lang_code) == 2 else "hr"  # Default to Croatian
            
        except Exception as e:
            logger.error(f"Language detection error: {str(e)}")
            return "hr"  # Default to Croatian
    
    async def translate_response(self, text: str, target_language: str) -> str:
        """
        Translate response to target language
        Preserves agricultural terminology
        """
        try:
            prompt = f"""Translate this agricultural advice to {target_language}.
Preserve technical agricultural terms and chemical names.
Make it natural and conversational.

Text: {text}"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an agricultural translator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return text  # Return original if translation fails
    
    def _build_processing_prompt(self) -> str:
        """Build the prompt for query processing"""
        return """Process this agricultural query and extract information.
Return JSON with:
{
    "language": "detected language code",
    "normalized_query": "cleaned, normalized version",
    "entities": {
        "crop": "main crop mentioned",
        "chemical": "pesticide/fertilizer name",
        "field": "field name/reference",
        "quantity": "amount with unit",
        "activity": "farming activity"
    },
    "intent": "user's intent (query_info, report_activity, ask_advice, etc.)",
    "agricultural_terms": ["list of agricultural terms found"],
    "requires_clarification": boolean,
    "clarification_questions": ["questions to ask if clarification needed"]
}

Process queries in any language. Extract entities even if in local language.
Be intelligent about variations and abbreviations."""
    
    def _generate_fallback_response(self, query: str, answer_data: Dict[str, Any], language: str) -> str:
        """Generate a simple fallback response"""
        if language == "hr":
            return f"Informacije o vašem upitu: {json.dumps(answer_data, ensure_ascii=False)}"
        else:
            return f"Information about your query: {json.dumps(answer_data)}"
    
    async def enhance_with_context(self, query: str, context: Dict[str, Any]) -> str:
        """
        Enhance query with context information
        Helps LLM understand follow-up questions
        """
        try:
            # Build context string
            context_parts = []
            
            if context.get("recent_topics"):
                context_parts.append(f"Recent topics: {', '.join(context['recent_topics'])}")
            
            if context.get("current_field"):
                context_parts.append(f"Current field: {context['current_field']}")
            
            if context.get("current_crop"):
                context_parts.append(f"Current crop: {context['current_crop']}")
            
            if not context_parts:
                return query
            
            # Let LLM enhance the query with context
            prompt = f"""Enhance this query with the given context to make it more specific.
Query: {query}
Context: {' | '.join(context_parts)}

Return only the enhanced query, nothing else."""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Enhance queries with context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Context enhancement error: {str(e)}")
            return query  # Return original if enhancement fails
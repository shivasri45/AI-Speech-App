"""Test LLM JSON parsing with control characters."""

import json
import pytest
import sys
sys.path.insert(0, '.')

from app.core.llm_client import LLMClient


class TestJSONParsing:
    """Test JSON parsing with various problematic inputs."""

    def setup_method(self):
        self.client = LLMClient()

    def test_clean_json(self):
        """Test parsing clean JSON."""
        json_str = '{"score": 85, "feedback": "Good job"}'
        result = json.loads(json_str)
        assert result["score"] == 85
        assert result["feedback"] == "Good job"

    def test_json_with_newlines_in_feedback(self):
        """Test JSON with literal newlines in string values."""
        # This simulates LLM output with raw newlines in feedback
        json_str = '''{
    "relevance": 8,
    "arguments": 7,
    "structure": 6,
    "vocabulary": 7,
    "feedback": "Good points made.
However, more evidence needed.
Overall decent."
}'''
        # This should fail with standard json.loads
        with pytest.raises(json.JSONDecodeError):
            json.loads(json_str)
        
        # Our sanitize function should handle it
        sanitized = self._sanitize_json(json_str)
        result = json.loads(sanitized)
        assert result["relevance"] == 8
        assert "Good points" in result["feedback"]

    def test_json_with_tab_in_feedback(self):
        """Test JSON with tab character in string."""
        json_str = '{"feedback": "Point 1:\tGood\tPoint 2:\tBad"}'
        # Raw tabs should be escaped
        sanitized = self._sanitize_json(json_str)
        result = json.loads(sanitized)
        assert "Point 1" in result["feedback"]

    def test_json_with_control_characters(self):
        """Test JSON with various control characters."""
        # Simulate control char at position (chr(0) to chr(31))
        json_str = '{"feedback": "Line1' + chr(7) + 'Line2"}'  # Bell character
        sanitized = self._sanitize_json(json_str)
        result = json.loads(sanitized)
        assert "Line1" in result["feedback"]

    def test_json_in_markdown_block(self):
        """Test extracting JSON from markdown code block."""
        response = '''Here is the analysis:
```json
{
    "relevance": 9,
    "arguments": 8,
    "structure": 7,
    "vocabulary": 8,
    "feedback": "Excellent argumentation"
}
```
'''
        import re
        json_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", response, re.DOTALL)
        assert json_match is not None
        result = json.loads(json_match.group(1))
        assert result["relevance"] == 9

    def test_json_without_markdown(self):
        """Test extracting JSON without markdown wrapper."""
        response = '''The scores are:
{
    "relevance": 7,
    "arguments": 6,
    "feedback": "Needs improvement"
}
Some additional text.'''
        start = response.find("{")
        end = response.rfind("}")
        json_str = response[start:end + 1]
        result = json.loads(json_str)
        assert result["relevance"] == 7

    def _sanitize_json(self, s: str) -> str:
        """Sanitize JSON string - same logic as in llm_client.py"""
        try:
            json.loads(s)
            return s
        except json.JSONDecodeError:
            pass
        
        # Replace raw newlines/tabs in the string with escaped versions
        # But we need to be careful - only escape inside string values
        result = []
        in_string = False
        i = 0
        while i < len(s):
            c = s[i]
            
            # Handle escape sequences
            if c == '\\' and i + 1 < len(s):
                result.append(c)
                result.append(s[i + 1])
                i += 2
                continue
            
            # Track string boundaries
            if c == '"':
                in_string = not in_string
                result.append(c)
                i += 1
                continue
            
            # Handle control characters
            if ord(c) < 32:
                if in_string:
                    # Inside a string - escape them
                    if c == '\n':
                        result.append('\\n')
                    elif c == '\r':
                        result.append('\\r')
                    elif c == '\t':
                        result.append('\\t')
                    # Skip other control characters inside strings
                else:
                    # Outside string - these are formatting, keep newlines/tabs
                    if c in '\n\r\t':
                        result.append(c)
                i += 1
                continue
            
            result.append(c)
            i += 1
        
        return ''.join(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

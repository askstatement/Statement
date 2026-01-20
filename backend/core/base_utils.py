import os
import re
import json
import hashlib
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from bson import ObjectId
from datetime import datetime, date
from cryptography.fernet import Fernet, InvalidToken
from core.base_database import BaseDatabase
from core.logger import Logger

logger = Logger(__name__)

class BaseUtils(BaseDatabase):
    def __init__(self):
        pass
    
    def extract_text(self, file_path):
        extracted_text = ""
        if file_path.lower().endswith(".pdf"):
            images = convert_from_path(file_path)
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image)
                extracted_text += f"\n--- Page {i + 1} ---\n{text}"
        else:
            image = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(image)
        return extracted_text


    def sanitize_mongo_doc(self, doc):
        # Handle dicts
        if isinstance(doc, dict):
            return {k: self.sanitize_mongo_doc(v) for k, v in doc.items()}

        # Handle lists
        elif isinstance(doc, list):
            return [self.sanitize_mongo_doc(item) for item in doc]

        # Handle Mongo ObjectId
        elif isinstance(doc, ObjectId):
            return str(doc)

        # Handle Plaid model objects (they have to_dict())
        elif hasattr(doc, "to_dict"):
            try:
                return self.sanitize_mongo_doc(doc.to_dict())
            except Exception:
                return str(doc)

        # Handle datetime safely → convert to ISO string
        elif isinstance(doc, datetime):
            return doc.isoformat()

        # Fallback: primitive type or cast to str
        else:
            return doc
        
    def fix_dates_for_mongo(self, doc):
        if isinstance(doc, dict):
            return {k: self.fix_dates_for_mongo(v) for k, v in doc.items()}
        elif isinstance(doc, list):
            return [self.fix_dates_for_mongo(v) for v in doc]
        elif isinstance(doc, date) and not isinstance(doc, datetime):
            # convert pure date to datetime at midnight
            return datetime.combine(doc, datetime.min.time())
        else:
            return doc

    def normalize_key(self, value: str) -> str:
        if not value:
            return ""

        # Uppercase and strip
        value = value.upper().strip()

        # Remove digits
        value = re.sub(r"\d+", "", value)

        # Remove special characters but keep spaces
        value = re.sub(r"[^A-Z\s]", "", value)

        # Collapse multiple spaces
        value = re.sub(r"\s+", " ", value)

        return value.strip()
        
    def sum_token_dicts(self, dict1, dict2):
        """
        Sums the values of two token usage dictionaries with the same structure.

        Args:
            dict1 (dict): First token usage dictionary.
            dict2 (dict): Second token usage dictionary.

        Returns:
            dict: A new dictionary with summed values.
        """
        try:
            return {key: dict1.get(key, 0) + dict2.get(key, 0) for key in dict1}
        except Exception as e:
            return dict1
        
    def generate_hash(self, input_string, algorithm="md5"):
        """
        Generate a hash from a given string using the specified algorithm.

        Parameters:
            input_string (str): The input string to hash.
            algorithm (str): Hashing algorithm to use (default: 'sha256').
                            Common options: 'md5', 'sha1', 'sha256', 'sha512'.

        Returns:
            str: The hexadecimal hash string.
        """
        try:
            if not input_string:
                return None
            # Encode the string to bytes
            encoded_str = input_string.encode('utf-8')
            
            # Create a hash object based on the chosen algorithm
            hash_obj = hashlib.new(algorithm)
            hash_obj.update(encoded_str)
            
            # Return the hexadecimal representation
            return hash_obj.hexdigest()
        except Exception as e:
            logger.error(f"Error generating hash: {e}")
            return input_string

    def _get_fernet(self) -> Fernet:
        key = os.getenv("PROJECTS_SECRET_KEY")
        if not key:
            raise RuntimeError("PROJECTS_SECRET_KEY env var not set")
        return Fernet(key)

    def encode_secret(self, value: str) -> str:
        return self._get_fernet().encrypt(value.encode()).decode()

    def decode_secret(self, token: str) -> str:
        try:
            return self._get_fernet().decrypt(token.encode()).decode()
        except InvalidToken:
            return ""
        
    def parse_rate(self, rate_str: str):
        """
        Utility: parse "30/m" → (30, seconds)
        """
        match = re.match(r"(\d+)\s*/\s*([smhd])", rate_str.strip().lower())
        if not match:
            raise ValueError("Invalid rate format. Use like '10/s', '30/m', '100/h', '1000/d'")
        count = int(match.group(1))
        unit = match.group(2)
        seconds = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
        return count, seconds
    
    def parse_token_rate(self, rate_str: str):
        """
        Utility: parse "10000/tpm" → (10000, seconds)
        """
        match = re.match(r"(\d+)\s*/\s*(tpm|tph|tpd)", rate_str.strip().lower())
        if not match:
            raise ValueError("Invalid token limit format. Use '10000/tpm', '500000/tph', or '10000000/tpd'")
        count = int(match.group(1))
        unit = match.group(2)
        seconds = {"tpm": 60, "tph": 3600, "tpd": 86400}[unit]
        return count, seconds

    def extract_json(self, response_text: str):
        try:
            response_json = json.loads(response_text)
            return response_json
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {}
        
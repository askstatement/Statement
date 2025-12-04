import json
import hashlib
from core.base_database import BaseDatabase

from core.logger import Logger
logger = Logger(__name__)

class BaseService(BaseDatabase):
    name: str = "base"
    base_path: str = "services/"
    es_mapping_json: str = "mapping.json"
    es_mapping: list = []

    def __init__(self, base_path: str = "services/"):
        logger.info(f"Initializing service: {self.base_path}{self.name}")
        super().__init__()
        # load base path
        if base_path:
            self.base_path = base_path
        # load schema_json if exists
        if self.es_mapping_json and self.es_mapping == []:
            try:
                self.es_mapping = self.load_json_file(self.es_mapping_json)
                logger.info(f"[{self.name}] Elasticsearch indices initialized.")
            except Exception as e:
                logger.error(f"[{self.name}] Error loading mapping JSON: {e}")
            
    def load_json_file(self, file: str):
        path = self.base_path + self.name + "/" + file
        # dynamically load json file without service prefix
        with open(path, "r") as f:
            return json.load(f)
        
    @staticmethod
    def generate_hash(input_string="", algorithm="md5"):
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

    def clean_dict(self, data):
        """Recursively remove None/empty values and convert Stripe monetary fields to major units."""

        def _convert(value, currency):
            """Convert integer or decimal string amounts using currency exponent."""
            exponent = self.CURRENCY_EXPONENTS.get(currency.lower(), 2) if currency else 2

            # If it's already a decimal string
            if isinstance(value, str):
                try:
                    value = int(value)
                except:
                    return value  # If it's not a number, return unchanged

            return value / (10**exponent)

        def _clean(obj):
            if isinstance(obj, dict):
                # Detect currency at this level
                currency_here = (
                    obj.get("currency") if isinstance(obj.get("currency"), str) else None
                )

                cleaned = {}
                for k, v in obj.items():
                    if v in (None, "", [], {}):
                        continue

                    # If the value is int and looks like a money field
                    if isinstance(v, int) and (
                        k.startswith("amount")
                        or k.startswith("total")
                        or k.startswith("subtotal")
                        or k.endswith("_amount")
                        or k.endswith("_amount_decimal")
                    ):
                        cleaned[k] = _convert(v, currency_here)
                    else:
                        cleaned[k] = _clean(v)
                return cleaned

            elif isinstance(obj, list):
                return [_clean(v) for v in obj if v not in (None, "", [], {})]

            return obj

        return _clean(data)


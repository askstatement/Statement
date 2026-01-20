import json
import tiktoken
from enum import Enum
from bson import ObjectId
from typing import List, Dict, Union
from jose import jwt, JWTError
from functools import wraps
from fastapi import Request, WebSocket, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from core.base_database import BaseDatabase
from core.base_utils import BaseUtils
from core.config import JWT_SECRET_KEY, ALGORITHM, TOKEN_MODEL
from core.logger import Logger

logger = Logger(__name__)

base_utils = BaseUtils()

class AuthMode(str, Enum):
    TOKEN = "token"
    PROJECT = "project"
    
class AuthScope(str, Enum):
    USER = "user"

async def get_user_from_token_data(token_data: dict):
    """Retrieve user object based on decoded JWT token data."""
    email = token_data.get("email")
    users_collection = BaseDatabase.mongodb.get_collection("users")
    user = await users_collection.find_one({"email": email, "$or": [{"archived": {"$exists": False}}, {"archived": False}]})
    return user

async def get_session_from_token_data(token_data: dict):
    """Retrieve session object based on decoded JWT token data."""
    session_id = token_data.get("session_id")
    sessions_collection = BaseDatabase.mongodb.get_collection("sessions")
    session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    return session

def ws_auth_required(_func=None, mode: AuthMode = AuthMode.TOKEN):
    """
    Decorator for WebSocket route handlers that require authentication.
    Expects a 'token' query parameter in the WebSocket connection URL or the project_id/projectId for project mode.

    Important: The decorator does NOT accept the connection. The handler must call
    await websocket.accept() after this decorator runs.

    Can be used as:
        @ws_auth_required
        or
        @ws_auth_required(mode=AuthMode.PROJECT)
    """

    def decorator(f):
        @wraps(f)
        async def wrapper(self, websocket: WebSocket, *args, **kwargs):
            if mode == AuthMode.TOKEN:
                # Extract token from query parameters
                token = websocket.query_params.get("token")
                # Also check Authorization header if not in query params
                if not token:
                    token = websocket.headers.get("Authorization")
                    if token and token.startswith("Bearer "):
                        token = token[len("Bearer "):]
                if not token:
                    logger.warning("ws_auth_required: No token provided")
                    # Accept then close with policy violation code
                    try:
                        await websocket.accept()
                    except Exception as e:
                        logger.error(f"ws_auth_required: Failed to accept websocket on token rejection: {e}")
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return

                try:
                    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
                    user_obj = await get_user_from_token_data(payload)
                    if not user_obj:
                        logger.warning(f"ws_auth_required: User not found from token")
                        try:
                            await websocket.accept()
                        except Exception as e:
                            logger.error(f"ws_auth_required: Failed to accept websocket on user not found: {e}")
                        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                        return
                    # Attach user to websocket state
                    websocket.state.user = user_obj
                    logger.debug(f"ws_auth_required: User authenticated: {user_obj.get('email')}")
                except JWTError as e:
                    logger.warning(f"ws_auth_required: WebSocket invalid token: {e}")
                    try:
                        await websocket.accept()
                    except Exception as e:
                        logger.error(f"ws_auth_required: Failed to accept websocket on JWT error: {e}")
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return

                return await f(self, websocket, *args, **kwargs)
            elif mode == AuthMode.PROJECT:
                project_id = websocket.query_params.get("projectId") or websocket.query_params.get("project_id")
                if not project_id:
                    logger.warning("ws_auth_required (PROJECT): No projectId provided")
                    try:
                        await websocket.accept()
                    except Exception as e:
                        logger.error(f"ws_auth_required (PROJECT): Failed to accept websocket on missing projectId: {e}")
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return

                projects_collection = BaseDatabase.mongodb.get_collection("projects")
                project = await projects_collection.find_one({"_id": ObjectId(project_id), "archived": False})
                if not project:
                    logger.warning(f"ws_auth_required (PROJECT): Project not found: {project_id}")
                    try:
                        await websocket.accept()
                    except Exception as e:
                        logger.error(f"ws_auth_required (PROJECT): Failed to accept websocket on invalid projectId: {e}")
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return

                # Attach project to websocket state
                websocket.state.project = project
                # Also attach user
                users_collection = BaseDatabase.mongodb.get_collection("users")
                user = await users_collection.find_one({"_id": ObjectId(project.get("user_id")), "$or": [{"archived": {"$exists": False}}, {"archived": False}]})
                if not user:
                    logger.warning(f"ws_auth_required (PROJECT): User not found for project: {project_id}")
                    try:
                        await websocket.accept()
                    except Exception as e:
                        logger.error(f"ws_auth_required (PROJECT): Failed to accept websocket on user not found: {e}")
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
                websocket.state.user = user
                logger.debug(f"ws_auth_required (PROJECT): Project authenticated: {project_id}")

                return await f(self, websocket, *args, **kwargs)
            else:
                raise RuntimeError(f"ws_auth_required: Unsupported AuthMode: {mode}")

        return wrapper

    # Support both @ws_auth_required and @ws_auth_required(mode=...)
    if _func is None:
        return decorator
    else:
        return decorator(_func)

def auth_required(_func=None, scope: AuthScope = AuthScope.USER):
    """
    Decorator for routes that require authentication.
    Can be used on async FastAPI endpoints.

    Can be used as:
        @auth_required
        or
        @auth_required(scope=AuthScope.USER)
    """
    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            # Get Request object
            request = kwargs.get("request") or next((a for a in args if isinstance(a, Request)), None)
            if not request:
                raise RuntimeError("Request object not found. Ensure route includes 'request: Request'.")

            # If middleware already attached user, use it
            user = getattr(request.state, "user", None)
            if user:
                logger.debug(f"Authenticated user: {getattr(user, 'email', None) or user}")
                return await f(*args, **kwargs)

            # Else, decode token manually
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                logger.warning("Unauthorized request (missing token)")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

            token = auth_header[len("Bearer "):]
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
                user_obj = await get_user_from_token_data(payload)
                session = await get_session_from_token_data(payload)
                if not user_obj:
                    logger.warning("Unauthorized request (invalid token)")
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
                request.state.user = user_obj
                request.state.session = session
            except JWTError as e:
                logger.warning(f"Invalid token: {e}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

            return await f(*args, **kwargs)
        return wrapper

    # Support both @auth_required and @auth_required(scope=...)
    if _func is None:
        return decorator
    else:
        return decorator(_func)

async def get_project_and_user_from_api_key(api_key: str):
    """Retrieve project and user object associated with the given API key."""
    keys_collection = BaseDatabase.mongodb.get_collection("api_keys")
    project_key = await keys_collection.find_one({"api_key": api_key, "archived": False})
    if not project_key:
        return None, None
    projects_collection = BaseDatabase.mongodb.get_collection("projects")
    project = await projects_collection.find_one({"_id": ObjectId(project_key.get("project_id")), "archived": False})
    if not project:
        return None, None
    users_collection = BaseDatabase.mongodb.get_collection("users")
    user = await users_collection.find_one({"_id": ObjectId(project.get("user_id")), "$or": [{"archived": {"$exists": False}}, {"archived": False}]})
    if not user:
        return None, None
    return project, user

def api_key_required(func):
    """
    Decorator for FastAPI routes that require Authorization Bearer tokens.

    Usage:
        @api_key_required
        async def my_route(request: Request):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract FastAPI request object
        request: Request = (
            kwargs.get("request")
            or next((a for a in args if isinstance(a, Request)), None)
        )
        if not request:
            raise RuntimeError("Request object not found. Ensure route includes 'request: Request'.")

        # Get Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid Authorization header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Authorization header",
            )

        # Extract API key
        api_key = auth_header.split("Bearer ")[-1].strip()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key missing in Authorization header",
            )

        # Validate API key → get user
        project_obj, user_obj = await get_project_and_user_from_api_key(api_key)
        if not user_obj or not project_obj:
            logger.warning("Unauthorized request (invalid API key)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
            )

        # Store authenticated user in request.state
        logger.debug(f"Authenticated user via API key: {user_obj.get('email', None) or user_obj.get('_id')}")
        request.state.user = user_obj
        request.state.project = project_obj
        request.state.api_key = api_key

        # Proceed with the actual endpoint logic
        return await func(*args, **kwargs)

    return wrapper

def rate_limit(limit: str):
    """
    Rate limiting decorator used for project-based rate limiting.

    Example usage:
        @rate_limit("30/m")
        @rate_limit("10/s")

    Automatically detects:
      - The API path (from request.url.path)
      - The user ID (from request.state.user)
    """
    max_requests, window_seconds = base_utils.parse_rate(limit)
    collection = BaseDatabase.mongodb.get_collection("project_rate_usage")
    # Use max TTL (1 day) to accommodate all rate limit windows
    max_ttl_seconds = 86400 + 60  # 1 day - maximum TTL for any rate limit option

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find FastAPI Request object
            request: Request = (
                kwargs.get("request") or
                next((a for a in args if isinstance(a, Request)), None)
            )
            if not request:
                raise RuntimeError("Request object not found in function arguments")

            # Detect project from request.state
            project = getattr(request.state, "project", None)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required for rate-limited route"
                )

            project_id = project.get("_id") if isinstance(project, dict) else getattr(project, "id", None)

            # Detect the path automatically
            path_key = request.url.path or "default"

            # Use combined key (project_id + path) for isolation
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)

            query = {
                "project_id": project_id,
                "path": path_key,
                "timestamp": {"$gte": window_start},
            }

            usage_count = await collection.count_documents(query)

            if usage_count >= max_requests:
                logger.warning(f"Rate limit exceeded for project={project_id} path={path_key}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded ({limit}) for this endpoint"
                )

            # Log request usage
            await collection.insert_one({
                "project_id": project_id,
                "path": path_key,
                "timestamp": now
            })

            # Auto-create TTL + compound index (safe to call multiple times)
            try:
                await collection.create_index("timestamp", expireAfterSeconds=max_ttl_seconds)
                await collection.create_index([("project_id", 1), ("path", 1)])
            except Exception:
                pass  # ignore race conditions on index creation

            return await func(*args, **kwargs)
        return wrapper
    return decorator

def count_tokens_for_text(text: str, model: str = TOKEN_MODEL) -> int:
    """Count tokens for a plain text string."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text or ""))

def count_tokens_for_messages(messages: List[Dict[str, Union[str, dict]]], model: str = TOKEN_MODEL) -> int:
    """Count tokens for a list of chat messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens_per_message = 3
    tokens_per_name = 1
    total_tokens = 0

    for msg in messages:
        total_tokens += tokens_per_message
        for key, value in msg.items():
            if isinstance(value, dict):
                # if assistant returns structured data
                value = str(value)
            total_tokens += len(encoding.encode(str(value)))
            if key == "name":
                total_tokens += tokens_per_name
    total_tokens += 3  # priming
    return total_tokens

def token_limit(limit: str):
    """
    Token-based rate limiting decorator for projects.

    Example usage:
        @token_limit("10000/tpm")

    Automatically detects:
      - The API path (from request.url.path)
      - The user ID (from request.state.user)
    """
    max_tokens, window_seconds = base_utils.parse_token_rate(limit)
    collection = BaseDatabase.mongodb.get_collection("project_token_usage")

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = (
                kwargs.get("request") or
                next((a for a in args if isinstance(a, Request)), None)
            )
            if not request:
                raise RuntimeError("Request object not found in function arguments")

            project = getattr(request.state, "project", None)
            if not project:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

            project_id = project.get("_id") if isinstance(project, dict) else getattr(project, "id", None)
            if not project_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing project_id")

            path_key = request.url.path or "default"
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)

            # Get total tokens used in current window
            query = {"project_id": project_id, "path": path_key, "timestamp": {"$gte": window_start}}
            records = await collection.find(query).to_list(length=None)
            total_tokens_used = sum(rec.get("total_tokens", 0) for rec in records)

            if total_tokens_used >= max_tokens:
                logger.warning(f"Token limit exceeded for project={project_id} path={path_key}")
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Token limit exceeded ({limit})"
                )

            # --- Count INPUT tokens ---
            input_tokens = 0
            model = TOKEN_MODEL
            try:
                # Try JSON body first (common for REST/chat endpoints)
                parsed = None
                try:
                    parsed = await request.json()
                except Exception:
                    # fallback read raw body and attempt JSON decode
                    try:
                        raw = await request.body()
                        parsed = json.loads(raw.decode("utf-8"))
                    except Exception:
                        parsed = None

                if isinstance(parsed, dict):
                    # If standard chat messages structure exists
                    messages = parsed.get("messages")
                    if isinstance(messages, list) and messages:
                        model = parsed.get("model", TOKEN_MODEL)
                        try:
                            input_tokens = count_tokens_for_messages(messages, model)
                        except Exception as e:
                            logger.debug(f"token_limit: failed to count messages tokens: {e}")
                            input_tokens = count_tokens_for_text(json.dumps(messages), model)
                    else:
                        # No messages list: count tokens for full JSON body
                        model = parsed.get("model", TOKEN_MODEL)
                        input_tokens = count_tokens_for_text(json.dumps(parsed), model)
                else:
                    # Treat raw body (webhooks, form posts, plain text) as text
                    try:
                        raw = await request.body()
                        text = raw.decode("utf-8", errors="ignore")
                        # If form-encoded, include raw text
                        input_tokens = count_tokens_for_text(text, TOKEN_MODEL)
                    except Exception as e:
                        logger.debug(f"token_limit: failed to read raw body: {e}")
                        input_tokens = 0
            except Exception as e:
                logger.error(f"token_limit: Failed to parse request body for token counting: {e}")
                input_tokens = 0
                model = TOKEN_MODEL

            # Execute the endpoint
            response = await func(*args, **kwargs)

            # --- Count OUTPUT tokens ---
            output_tokens = 0
            try:
                res_json = None

                # response might be dict-like already
                if isinstance(response, dict):
                    res_json = response

                # starlette/fastapi Response objects may expose content/body/media
                elif hasattr(response, "body") or hasattr(response, "content") or hasattr(response, "media"):
                    # Try several strategies safely
                    try:
                        # If .body is callable (some response types), await it
                        body_attr = getattr(response, "body", None)
                        if callable(body_attr):
                            body_bytes = await response.body()
                        elif isinstance(body_attr, (bytes, bytearray)):
                            body_bytes = bytes(body_attr)
                        else:
                            # try .content
                            content_attr = getattr(response, "content", None)
                            if isinstance(content_attr, (bytes, bytearray)):
                                body_bytes = bytes(content_attr)
                            else:
                                # try .media (already decoded)
                                media_attr = getattr(response, "media", None)
                                if media_attr is not None:
                                    res_json = media_attr
                                    body_bytes = None
                                else:
                                    body_bytes = None

                        if body_bytes is not None:
                            try:
                                res_json = json.loads(body_bytes.decode("utf-8"))
                            except Exception:
                                # not JSON: keep as raw text
                                res_json = None
                                raw_text = body_bytes.decode("utf-8", errors="ignore")
                                output_tokens = count_tokens_for_text(raw_text, model)
                    except Exception as e:
                        logger.debug(f"token_limit: error extracting response body: {e}")

                else:
                    # Fallback: try to parse string representation
                    try:
                        res_json = json.loads(str(response))
                    except Exception:
                        res_json = None

                # If we have JSON-like structure, try to extract fields commonly used by chat responses
                if res_json is not None and output_tokens == 0:
                    try:
                        if isinstance(res_json, dict) and "choices" in res_json:
                            output_text = res_json["choices"][0]["message"]["content"]
                        elif isinstance(res_json, dict) and "response" in res_json:
                            output_text = res_json["response"]
                        else:
                            output_text = json.dumps(res_json)
                        output_tokens = count_tokens_for_text(output_text, model)
                    except Exception as e:
                        logger.debug(f"token_limit: failed to count output tokens from JSON: {e}")
                        output_tokens = 0
            except Exception as e:
                logger.error(f"Failed to count output tokens: {e}")
                output_tokens = 0

            total = input_tokens + output_tokens

            logger.debug(
                f"[token_limit] project={project_id} path={path_key} input={input_tokens} output={output_tokens} total={total} / {max_tokens}"
            )

            # add token usage info to response if possible
            try:
                if isinstance(response, dict):
                    response["usage"] = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total
                    }
                elif hasattr(response, "body") or hasattr(response, "content") or hasattr(response, "media"):
                    # Only modify response when we can safely build a JSONResponse
                    try:
                        # Attempt to extract existing content as JSON
                        existing = None
                        try:
                            body_attr = getattr(response, "body", None)
                            if callable(body_attr):
                                body_bytes = await response.body()
                                existing = json.loads(body_bytes.decode("utf-8"))
                            elif isinstance(body_attr, (bytes, bytearray)):
                                existing = json.loads(bytes(body_attr).decode("utf-8"))
                        except Exception:
                            try:
                                media = getattr(response, "media", None)
                                if media is not None:
                                    existing = media
                            except Exception:
                                existing = None

                        if existing is None:
                            # can't safely augment streaming or unknown content
                            pass
                        else:
                            existing["usage"] = {
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "total_tokens": total
                            }
                            # preserve status_code and headers if available
                            status_code = getattr(response, "status_code", 200)
                            headers = getattr(response, "headers", None)
                            response = JSONResponse(content=existing, status_code=status_code, headers=headers)
                    except Exception as e:
                        logger.debug(f"token_limit: could not attach usage to response: {e}")
            except Exception:
                pass

            return response
        return wrapper
    return decorator

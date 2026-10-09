import hmac
import hashlib
import base64
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

try:
    from backend.config import settings
    from backend.database import get_db
    from backend.models.manager import Manager
except ImportError:
    from config import settings
    from database import get_db
    from models.manager import Manager

security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"pbkdf2_sha256$100000${salt.hex()}${key.hex()}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored PBKDF2 hash."""
    try:
        parts = hashed_password.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        stored_key = bytes.fromhex(parts[3])
        computed_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(stored_key, computed_key)
    except Exception:
        return False

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _b64_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode((data + padding).encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT Bearer token using HMAC-SHA256."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": int(expire.timestamp())})
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_json = json.dumps(to_encode, separators=(',', ':')).encode('utf-8')
    
    unsigned_token = f"{_b64_encode(header_json)}.{_b64_encode(payload_json)}"
    signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        unsigned_token.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    return f"{unsigned_token}.{_b64_encode(signature)}"

def decode_access_token(token: str) -> dict:
    """Validates signature and expiration of a JWT Bearer token."""
    parts = token.split('.')
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    unsigned_token = f"{parts[0]}.{parts[1]}"
    signature = _b64_decode(parts[2])
    expected_signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        unsigned_token.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token signature.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = json.loads(_b64_decode(parts[1]).decode('utf-8'))
    exp = payload.get("exp")
    if exp and datetime.utcnow().timestamp() > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload

def get_current_manager(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Manager:
    """Dependency to extract and verify current authenticated Manager."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(credentials.credentials)
    manager_id = payload.get("sub")
    if not manager_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing manager ID.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    manager = db.query(Manager).filter(Manager.manager_id == manager_id).first()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated manager account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return manager

def require_store_manager(current_manager: Manager = Depends(get_current_manager)) -> Manager:
    """Ensures manager role is STORE_MANAGER or CITY_MANAGER."""
    if current_manager.role not in ("STORE_MANAGER", "CITY_MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Store Manager or City Manager privileges required."
        )
    return current_manager

def require_city_manager(current_manager: Manager = Depends(get_current_manager)) -> Manager:
    """Ensures manager role is strictly CITY_MANAGER."""
    if current_manager.role != "CITY_MANAGER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="City Operations Manager privileges required for this action."
        )
    return current_manager


from datetime import datetime, timedelta
from email import message
from typing import Optional

import databases
import enum

import jwt
import sqlalchemy
from pydantic import BaseModel, EmailStr, Field, validator
from fastapi import FastAPI, HTTPException, dependencies, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import DATABASE_URL, JWT_SECRET
from email_validator import validate_email as validate_e, EmailNotValidError
from passlib.context import CryptContext
from starlette.requests import Request


database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()


class UserRole(enum.Enum):
    super_admin = "super admin"
    admin = "admin"
    user = "user"


users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("email", sqlalchemy.String(120), unique=True),
    sqlalchemy.Column("password", sqlalchemy.String(255)),
    sqlalchemy.Column("full_name", sqlalchemy.String(200)),
    sqlalchemy.Column("phone", sqlalchemy.String(13)),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=False, server_default=sqlalchemy.func.now()),
    sqlalchemy.Column(
        "last_modified_at",
        sqlalchemy.DateTime,
        nullable=False,
        server_default=sqlalchemy.func.now(),
        onupdate=sqlalchemy.func.now(),
    ),
    sqlalchemy.Column("role", sqlalchemy.Enum(UserRole), nullable=False, server_default=UserRole.user.name)
)


class FullNameField(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
        
    @classmethod
    def validate(cls, v) -> str:
        try:
            first_name, *last_name = v.split()
            if len(last_name) == 0 or last_name is None:
                raise ValueError("Full Name must be at least two names")
            return f"{last_name[-1].capitalize()}, {first_name.capitalize()}" 
        except:
            raise ValueError("Full Name must be at least two names")


class BaseUser(BaseModel):
    email: EmailStr = Field(..., description="User email for contact")
    full_name: FullNameField = Field(min_length=3)

    @validator("full_name")
    def validate_full_name(cls, v):
        try:
            first_name, last_name = v.split()
            return v
        except Exception:
            raise ValueError("You should provide at least 2 names")


class UserSignIn(BaseUser):
    password: str = Field(min_length=6, description="User Password")
    role: Optional[str]


class UserSignOut(BaseUser):
    phone: Optional[str]
    created_at: datetime
    last_modified_at: datetime
    token: str
    role: UserRole


class ColorEnum(enum.Enum):
    pink = "pink"
    black = "black"
    white = "white"
    yellow = "yellow"


class SizeEnum(enum.Enum):
    xs = "xs"
    s = "s"
    m = "m"
    l = "l"
    xl = "xl"
    xxl = "xxl"


clothes = sqlalchemy.Table(
    "clothes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String(120)),
    sqlalchemy.Column("color", sqlalchemy.Enum(ColorEnum), nullable=False),
    sqlalchemy.Column("size", sqlalchemy.Enum(SizeEnum), nullable=False),
    sqlalchemy.Column("photo_url", sqlalchemy.String(255)),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=False, server_default=sqlalchemy.func.now()),
    sqlalchemy.Column(
        "last_modified_at",
        sqlalchemy.DateTime,
        nullable=False,
        server_default=sqlalchemy.func.now(),
        onupdate=sqlalchemy.func.now(),
    ),
)

class ClothesBase(BaseModel):
    name: str = Field(min_length=5, max_length=120)
    color: ColorEnum = Field(description="One of pink, black, white, yellow")
    size: SizeEnum = Field(description="One of xs, s, m, l, xl, xxl")
    
class ClothesIn(ClothesBase):
    photo_url: Optional[str] = Field(description="Url to clothe photo")
    
    
class ClothesOut(ClothesBase):
    id: int
    created_at: datetime

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CustomHTTPBearer(HTTPBearer):
    async def __call__(
        self, request: Request
    ) -> Optional[HTTPAuthorizationCredentials]:
        res = await super().__call__(request)
        
        try:
            payload = jwt.decode(res.credentials, config.JWT_SECRET, algorithms=["HS256"])
            user = await database.fetch_one(users.select().where(users.c.id == payload["sub"]))
            
            request.state.user = user
            
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token is expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid Token")
        except Exception as ex:
            raise ex
                

oauth2_scheme = CustomHTTPBearer()


def is_admin(request: Request):
    user = request.state.user
    if user and user['role'] not in (UserRole.admin, UserRole.super_admin):
        raise HTTPException(status_code=403, detail="User has not permission for this resource")

def create_access_token(user):
    try:
        payload = {"sub": user["id"], "exp": datetime.utcnow() + timedelta(minutes=120)}
        return jwt.encode(payload, JWT_SECRET)
    except Exception as ex:
        raise ex
    
    
    
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
    
    
@app.get("/clothes", dependencies=[Depends(oauth2_scheme)])
async def get_all_clothes():
    return await database.fetch_all(clothes.select())

@app.post(
    "/clothes", 
    response_model=ClothesOut, 
    dependencies=[
        Depends(oauth2_scheme), 
        Depends(is_admin)
        ],
    status_code=201
    )
async def create_clothes(clothes_data: ClothesIn):
    id_ = await database.execute(clothes.insert().values(**clothes_data.dict()))
    created_clothes = await database.fetch_one(clothes.select().where(clothes.c.id == id_))
    response = ClothesOut(
            id=created_clothes["id"],
            name=created_clothes["name"],
            color=created_clothes["color"],
            size=created_clothes["size"],
            created_at=created_clothes["created_at"],
        
    )
    return response 
    
    
    
    
@app.post("/register/", response_model=UserSignOut, status_code=201)
async def create_user(user: UserSignIn):
    user.password = pwd_context.hash(user.password)
    q = users.insert().values(**user.dict())
    id_ = await database.execute(q)
    created_user = await database.fetch_one(users.select().where(users.c.id == id_))
    token = create_access_token(created_user)
    response = UserSignOut(
        full_name=created_user["full_name"],
        email=created_user["email"],
        phone=created_user["phone"],
        created_at=created_user["created_at"],
        last_modified_at=created_user["last_modified_at"],
        role=created_user["role"],
        token=token
    )
    return response


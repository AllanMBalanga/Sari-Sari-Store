from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_host: str  
    database_user: str
    database_password: str        
    database_name: str      
    secret_key: str         
    algorithm: str          
    token_minutes: int      
    
    class Config:
        env_file = ".env"

settings = Settings()
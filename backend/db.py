from sqlmodel import SQLModel, create_engine, Session

# SQLite DB URL
DATABASE_URL = "sqlite:///./app.db"

# Create engine with echo enabled for debugging
engine = create_engine(DATABASE_URL, echo=True)

# Create tables
SQLModel.metadata.create_all(engine)

# SessionLocal is a helper function to create new DB sessions
def get_session():
    with Session(engine) as session:
        yield session

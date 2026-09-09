from sqlalchemy import create_engine, inspect, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
from app.core import settings

Path('app/db').mkdir(parents=True, exist_ok=True)
engine=create_engine(settings.DATABASE_URL,connect_args={'check_same_thread':False} if 'sqlite' in settings.DATABASE_URL else {})
if 'sqlite' in settings.DATABASE_URL:
    @event.listens_for(engine, 'connect')
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor=dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()
SessionLocal=sessionmaker(autocommit=False,autoflush=False,bind=engine)
Base=declarative_base()

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def init_db():
    from app.models import Project, Transcript, TranscriptSegment, Caption, Short, EditJob, ChannelSetting, Chapter, ContentPackage, ProcessingJob
    Base.metadata.create_all(bind=engine)
    # Lightweight migration for databases created by earlier ClipForge versions.
    insp=inspect(engine)
    if 'projects' in insp.get_table_names():
        existing={c['name'] for c in insp.get_columns('projects')}
        additions={'processing_progress':'INTEGER DEFAULT 0','processing_step':'TEXT DEFAULT \'Waiting\''}
        with engine.begin() as conn:
            for name, ddl in additions.items():
                if name not in existing: conn.execute(text(f'ALTER TABLE projects ADD COLUMN {name} {ddl}'))
    if 'shorts' in insp.get_table_names():
        existing={c['name'] for c in insp.get_columns('shorts')}
        with engine.begin() as conn:
            if 'score' not in existing: conn.execute(text('ALTER TABLE shorts ADD COLUMN score FLOAT'))
            if 'reason' not in existing: conn.execute(text('ALTER TABLE shorts ADD COLUMN reason TEXT'))
            additions={'category':'TEXT','subcategories':'JSON','confidence':'FLOAT','signals':'JSON','detected_events':'JSON','warnings':'JSON','analysis_source':"TEXT DEFAULT 'local'"}
            for name, ddl in additions.items():
                if name not in existing: conn.execute(text(f'ALTER TABLE shorts ADD COLUMN {name} {ddl}'))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from .models import Base


class Store:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            'sqlite:///' + path.as_posix(),
            connect_args={'check_same_thread': False, 'timeout': 5},
            hide_parameters=True,
        )

        @event.listens_for(self.engine, 'connect')
        def configure_sqlite(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA busy_timeout=5000')

        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self):
        with self.engine.connect() as connection:
            connection.exec_driver_sql('PRAGMA journal_mode=WAL')
        Base.metadata.create_all(self.engine)
        # Additive migration: keep batch A users, messages and runs intact.
        with self.engine.begin() as connection:
            columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(runs)')}
            if 'details_json' not in columns:
                connection.exec_driver_sql("ALTER TABLE runs ADD COLUMN details_json TEXT NOT NULL DEFAULT '{}'")
            if 'cancel_requested' not in columns:
                connection.exec_driver_sql('ALTER TABLE runs ADD COLUMN cancel_requested BOOLEAN NOT NULL DEFAULT 0')
            event_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(execution_events)')}
            if 'event_key' not in event_columns:
                connection.exec_driver_sql('ALTER TABLE execution_events ADD COLUMN event_key VARCHAR(160)')
            connection.exec_driver_sql('CREATE UNIQUE INDEX IF NOT EXISTS uq_event_key ON execution_events(event_key)')
            connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_active_session_run ON runs(session_id) WHERE run_status IN ('running', 'awaiting_input', 'paused')")
            connection.exec_driver_sql('PRAGMA user_version=1')

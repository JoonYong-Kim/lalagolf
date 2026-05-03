from sqlalchemy import Engine, text


def check_database_connection(engine: Engine) -> bool:
    with engine.connect() as connection:
        connection.execute(text("select 1"))
    return True

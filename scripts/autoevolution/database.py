"""Database helper functions for the scraper."""

def get_or_create(session, model, defaults=None, **kwargs):
    """
    Gets an object or creates it if it doesn't exist.
    Returns (instance, created_boolean).
    """
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        # Update existing instance with defaults if provided
        if defaults:
            for key, value in defaults.items():
                setattr(instance, key, value)
        return instance, False
    else:
        params = {**kwargs, **(defaults or {})}
        instance = model(**params)
        session.add(instance)
        session.flush()
        return instance, True


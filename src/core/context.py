from contextvars import ContextVar
request_dict: ContextVar[dict] = ContextVar("request_dict", default={})


def set_context(**kwargs):
   
    if request_dict.get() is None:
        request_dict.set({})

    current_context = request_dict.get()
    current_context.update(kwargs)
    request_dict.set(current_context)


def get_context(key: str = ''):
    
    context = request_dict.get()
    if context is None:
        return None if key else {}

    if key:
        if key in context:
            return context.get(key)
        else:
            return None

    return context

def get_user():
    
    return get_context('login_name')

def get_context_db():
    
    return get_context('db')


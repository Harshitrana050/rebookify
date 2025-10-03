from flask import abort
from flask_login import current_user
from functools import wraps

def seller_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'seller':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# accounts/validators.py

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class UppercaseValidator:
    """Validate that the password contains at least one uppercase letter."""
    
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _('Password must contain at least one uppercase letter (A-Z).'),
                code='password_no_upper',
            )

    def get_help_text(self):
        return _('Your password must contain at least one uppercase letter (A-Z).')


class LowercaseValidator:
    """Validate that the password contains at least one lowercase letter."""
    
    def validate(self, password, user=None):
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _('Password must contain at least one lowercase letter (a-z).'),
                code='password_no_lower',
            )

    def get_help_text(self):
        return _('Your password must contain at least one lowercase letter (a-z).')


class SpecialCharacterValidator:
    """Validate that the password contains at least one special character."""
    
    def validate(self, password, user=None):
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                _('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>).'),
                code='password_no_special',
            )

    def get_help_text(self):
        return _('Your password must contain at least one special character (!@#$%^&*(),.?":{}|<>).')


class NumberValidator:
    """Validate that the password contains at least one number."""
    
    def validate(self, password, user=None):
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _('Password must contain at least one number (0-9).'),
                code='password_no_number',
            )

    def get_help_text(self):
        return _('Your password must contain at least one number (0-9).')


class MinLengthValidator:
    """Validate that the password is at least 10 characters long."""
    
    def __init__(self, min_length=10):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _(f'Password must be at least {self.min_length} characters long.'),
                code='password_too_short',
            )

    def get_help_text(self):
        return _(f'Your password must be at least {self.min_length} characters long.')
    
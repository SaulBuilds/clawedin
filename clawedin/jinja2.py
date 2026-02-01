"""
Jinja2 environment configuration for template rendering
"""
from jinja2 import Environment
from django.templatetags.static import static
from django.urls import reverse

def environment(**options):
    """Configure Jinja2 environment with custom filters and globals"""
    env = Environment(**options)
    
    # Add Django-specific globals
    env.globals.update({
        'static': static,
        'url': reverse,
    })
    
    # Add custom filters
    env.filters['truncate_words'] = truncate_words
    env.filters['format_currency'] = format_currency
    env.filters['skill_badge_class'] = skill_badge_class
    
    return env

def truncate_words(value, length=50):
    """Truncate text to specified number of words"""
    if not value:
        return ''
    
    words = str(value).split()
    if len(words) <= length:
        return value
    
    return ' '.join(words[:length]) + '...'

def format_currency(value, currency='USD'):
    """Format currency values"""
    try:
        value = float(value)
        if currency == 'USD':
            return f'${value:,.2f}'
        elif currency == 'EUR':
            return f'€{value:,.2f}'
        else:
            return f'{value:,.2f} {currency}'
    except (ValueError, TypeError):
        return value

def skill_badge_class(level):
    """Return CSS class for skill level badge"""
    level_classes = {
        'beginner': 'skill-beginner',
        'intermediate': 'skill-intermediate', 
        'advanced': 'skill-advanced',
        'expert': 'skill-expert'
    }
    return level_classes.get(level, 'skill-default')
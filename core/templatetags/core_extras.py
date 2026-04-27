from django import template

register = template.Library()


SAMPLE_STATUS_META = {
    'RECEIVED_FRONT_DESK': {
        'label': 'Front desk',
        'full_label': 'Received at Front Desk',
        'class': 'status-badge--frontdesk',
        'icon': 'assignment',
    },
    'SENT_TO_LAB': {
        'label': 'Sent to lab',
        'full_label': 'Sent to Lab',
        'class': 'status-badge--lab',
        'icon': 'send',
    },
    'TESTING_IN_PROGRESS': {
        'label': 'Testing',
        'full_label': 'Testing in Progress',
        'class': 'status-badge--lab',
        'icon': 'science',
    },
    'RESULTS_ENTERED': {
        'label': 'Results entered',
        'full_label': 'Results Entered',
        'class': 'status-badge--review',
        'icon': 'fact_check',
    },
    'REVIEW_PENDING': {
        'label': 'Review',
        'full_label': 'Review Pending',
        'class': 'status-badge--review',
        'icon': 'rate_review',
    },
    'REPORT_APPROVED': {
        'label': 'Approved',
        'full_label': 'Report Approved',
        'class': 'status-badge--complete',
        'icon': 'verified',
    },
    'REPORT_SENT': {
        'label': 'Sent',
        'full_label': 'Report Sent',
        'class': 'status-badge--complete',
        'icon': 'outbox',
    },
    'CANCELLED': {
        'label': 'Cancelled',
        'full_label': 'Cancelled',
        'class': 'status-badge--cancelled',
        'icon': 'cancel',
    },
}

REVIEW_STATUS_META = {
    'APPROVED': {'label': 'Approved', 'class': 'status-badge--complete', 'icon': 'verified'},
    'REJECTED': {'label': 'Rejected', 'class': 'status-badge--cancelled', 'icon': 'report'},
    'PENDING': {'label': 'Pending', 'class': 'status-badge--review', 'icon': 'rate_review'},
}

WORKFLOW_STEPS = [
    ('RECEIVED_FRONT_DESK', 'Received', 'inventory_2'),
    ('SENT_TO_LAB', 'Sent to lab', 'send'),
    ('TESTING_IN_PROGRESS', 'Testing', 'science'),
    ('RESULTS_ENTERED', 'Results', 'fact_check'),
    ('REVIEW_PENDING', 'Review', 'rate_review'),
    ('REPORT_APPROVED', 'Approved', 'verified'),
    ('REPORT_SENT', 'Sent', 'outbox'),
]

WORKFLOW_INDEX = {code: index for index, (code, _label, _icon) in enumerate(WORKFLOW_STEPS)}

NEXT_STEP_META = {
    'RECEIVED_FRONT_DESK': {
        'label': 'Send to lab',
        'description': 'Front desk can move this sample to lab testing.',
        'icon': 'send',
        'tone': 'primary',
    },
    'SENT_TO_LAB': {
        'label': 'Enter results',
        'description': 'Lab can begin testing and record parameter results.',
        'icon': 'edit_note',
        'tone': 'primary',
    },
    'TESTING_IN_PROGRESS': {
        'label': 'Complete results',
        'description': 'Finish recording all requested test results.',
        'icon': 'edit_note',
        'tone': 'primary',
    },
    'RESULTS_ENTERED': {
        'label': 'Send for review',
        'description': 'Results are ready for consultant review.',
        'icon': 'forward_to_inbox',
        'tone': 'warning',
    },
    'REVIEW_PENDING': {
        'label': 'Review report',
        'description': 'Consultant approval or correction is required.',
        'icon': 'rate_review',
        'tone': 'warning',
    },
    'REPORT_APPROVED': {
        'label': 'Download report',
        'description': 'Report is approved and ready to hand over.',
        'icon': 'download',
        'tone': 'success',
    },
    'REPORT_SENT': {
        'label': 'Complete',
        'description': 'Report has been sent to the customer.',
        'icon': 'check_circle',
        'tone': 'success',
    },
    'CANCELLED': {
        'label': 'Cancelled',
        'description': 'This sample is closed and cannot move forward.',
        'icon': 'cancel',
        'tone': 'danger',
    },
}

@register.filter(name='replace')
def replace_filter(value, arg):
    """
    Replaces all occurrences of the first part of arg with the second part of arg in the given string.
    Argument 'arg' should be a string in the format "old,new".
    Example: {{ some_string|replace:"_, " }}
    """
    if not isinstance(value, str):
        value = str(value) # Ensure value is a string
        
    if isinstance(arg, str) and ',' in arg:
        old_char, new_char = arg.split(',', 1)
        return value.replace(old_char, new_char)
    return value

@register.filter(name='getattr')
def getattr_filter(obj, attr_name):
    """
    Gets an attribute from an object. Returns None if attribute doesn't exist.
    Usage: {{ my_object|getattr:"attribute_name" }}
    """
    return getattr(obj, attr_name, None)


@register.inclusion_tag('core/includes/sample_status_badge.html')
def sample_status_badge(sample, compact=False, show_icon=True):
    status = getattr(sample, 'current_status', sample)
    meta = SAMPLE_STATUS_META.get(status, {
        'label': str(status).replace('_', ' ').title(),
        'full_label': str(status).replace('_', ' ').title(),
        'class': 'status-badge--neutral',
        'icon': 'label',
    })
    display_label = meta['label'] if compact else meta['full_label']
    if hasattr(sample, 'get_current_status_display') and not compact:
        display_label = sample.get_current_status_display()
    return {
        'label': display_label,
        'title': meta['full_label'],
        'status_class': meta['class'],
        'icon': meta['icon'],
        'show_icon': show_icon,
    }


@register.inclusion_tag('core/includes/sample_status_badge.html')
def review_status_badge(review, compact=False, show_icon=True):
    status = getattr(review, 'status', review)
    meta = REVIEW_STATUS_META.get(status, {
        'label': str(status).replace('_', ' ').title(),
        'class': 'status-badge--neutral',
        'icon': 'label',
    })
    label = meta['label']
    if hasattr(review, 'get_status_display') and not compact:
        label = review.get_status_display()
    return {
        'label': label,
        'title': meta['label'],
        'status_class': meta['class'],
        'icon': meta['icon'],
        'show_icon': show_icon,
    }


@register.simple_tag
def sample_workflow_steps(sample):
    current_status = getattr(sample, 'current_status', '')
    current_index = WORKFLOW_INDEX.get(current_status, -1)
    if current_status == 'RESULTS_ENTERED':
        current_index = WORKFLOW_INDEX['RESULTS_ENTERED']
    steps = []
    for index, (code, label, icon) in enumerate(WORKFLOW_STEPS):
        if current_status == 'CANCELLED':
            state = 'pending'
        elif index < current_index:
            state = 'complete'
        elif index == current_index:
            state = 'current'
        else:
            state = 'pending'
        steps.append({
            'code': code,
            'label': label,
            'icon': icon,
            'state': state,
        })
    return steps


@register.simple_tag
def sample_next_step(sample):
    status = getattr(sample, 'current_status', '')
    return NEXT_STEP_META.get(status, {
        'label': 'View sample',
        'description': 'Open the record to review details and activity.',
        'icon': 'visibility',
        'tone': 'neutral',
    })

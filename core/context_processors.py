from __future__ import annotations

from .models import LabProfile


def lab_profile(request):
    """Expose lab profile details to all templates."""
    profile = LabProfile.get_active()
    return {
        'lab_profile': profile,
        'lab_profile_address': profile.formatted_address,
        'lab_profile_contact_line': profile.contact_line,
    }

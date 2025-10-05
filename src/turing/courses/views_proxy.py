import logging
import requests
from django.conf import settings
from django.http import StreamingHttpResponse, Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from .models import Course, Enrollment

logger = logging.getLogger(__name__)

CHUNK_SIZE = 8192
SUPABASE_ALLOWED_HOST = getattr(settings, "SUPABASE_ALLOWED_HOST", "bxvduwertvebzbamjjki.supabase.co")
SUPABASE_SERVICE_KEY = getattr(settings, "SUPABASE_SERVICE_KEY", None)  # normalmente None si el bucket es público


@login_required
def tutoring_schedule_proxy(request, pk):
    course = get_object_or_404(Course, pk=pk)

    user = request.user
    is_staff = user.is_staff
    is_enrolled = Enrollment.objects.filter(student=user, course=course).exists()

    if not (is_staff or is_enrolled):
        return HttpResponse("Forbidden", status=403)

    try:
        file_url = course.tutoring_schedule.file.url
    except Exception:
        raise Http404("No tutoring schedule available for this course.")

    if SUPABASE_ALLOWED_HOST not in file_url:
        return HttpResponse("Forbidden file host", status=403)

    upstream_headers = {
        "Accept": "application/pdf",
    }
    if SUPABASE_SERVICE_KEY:
        upstream_headers["Authorization"] = f"Bearer {SUPABASE_SERVICE_KEY}"

    if_modified_since = request.headers.get("If-Modified-Since")
    if if_modified_since:
        upstream_headers["If-Modified-Since"] = if_modified_since

    try:
        upstream = requests.get(file_url, stream=True, headers=upstream_headers, timeout=15)
    except requests.RequestException as exc:
        logger.exception("Error fetching tutoring schedule from upstream: %s", exc)
        return HttpResponse("Error fetching file", status=502)

    if upstream.status_code == 304:
        return HttpResponse(status=304)

    if upstream.status_code != 200:
        logger.warning("Upstream returned status %s for URL %s", upstream.status_code, file_url)
        return HttpResponse(f"Upstream returned {upstream.status_code}", status=upstream.status_code)

    def stream_generator():
        try:
            for chunk in upstream.iter_content(CHUNK_SIZE):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    content_type = upstream.headers.get("Content-Type", "application/pdf")

    response = StreamingHttpResponse(stream_generator(), content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="tutoring_schedule_{course.pk}.pdf"'

    content_length = upstream.headers.get("Content-Length")
    if content_length:
        response["Content-Length"] = content_length

    last_modified = upstream.headers.get("Last-Modified")
    if last_modified:
        response["Last-Modified"] = last_modified
    etag = upstream.headers.get("ETag")
    if etag:
        response["ETag"] = etag

    response["Cache-Control"] = "private, max-age=3600"

    return response

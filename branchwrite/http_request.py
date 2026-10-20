"""Keep authenticated COW requests at the origin the caller selected."""
from urllib.request import HTTPRedirectHandler, build_opener


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def open_without_redirect(request, *, timeout):
    # Automatic redirects can forward a Bearer key or change a POST into GET.
    # A redirect proves neither rejection nor durable completion of a mutation.
    return build_opener(_NoRedirect).open(request, timeout=timeout)

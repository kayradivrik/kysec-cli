"""SecAI Web Arayüzü Mikro-Yönlendiricisi (Micro-Router).

Harici paket bağımlılığı (FastAPI/Flask) gerektirmeden, standart kütüphane
BaseHTTPRequestHandler üzerinde rotalama, parametre eşleme ({id}) ve
dekoratör tabanlı uç nokta tanımlaması sağlar.
"""

import re
from typing import Any, Callable, Dict, Optional, Tuple


class Router:
    """REST API uç noktalarını düzenli ve parametrik olarak yöneten yönlendirici."""

    def __init__(self) -> None:
        self.routes: Dict[str, list[Tuple[re.Pattern, Callable]]] = {
            "GET": [],
            "POST": [],
        }

    def get(self, path: str) -> Callable:
        """GET isteği için dekoratör."""
        return self._add_route("GET", path)

    def post(self, path: str) -> Callable:
        """POST isteği için dekoratör."""
        return self._add_route("POST", path)

    def _add_route(self, method: str, path: str) -> Callable:
        def decorator(fn: Callable) -> Callable:
            # {param} formatını adlandırılmış regex grubuna (?P<param>[^/]+) dönüştür
            pattern = re.sub(r"\{([a-zA-Z0-9_]+)\}", r"(?P<\1>[^/]+)", path)
            regex = re.compile(f"^{pattern}$")
            self.routes[method].append((regex, fn))
            return fn

        return decorator

    def match(self, method: str, path: str) -> Tuple[Optional[Callable], Dict[str, Any]]:
        """Verilen HTTP metodu ve yol için eşleşen işleyiciyi ve parametreleri döner."""
        for regex, fn in self.routes.get(method, []):
            m = regex.match(path)
            if m:
                return fn, m.groupdict()
        return None, {}


from .views import index, EntranceWebSocketHandler, BoxWebSocketHandler
from .utils import URLWrapper


def setup_box_routes(app):
    id = app["ID"]
    # Pass BASE_URL as arg when initialize an URLWrapper instance
    BASE_URL = "/dandelion/" + id
    wrap = URLWrapper(BASE_URL)
    app.router.add_route('*',
                         wrap("ws"),
                         BoxWebSocketHandler(),
                         name="ws"
                         )
    app.router.add_get(wrap(), index, name='index')


def setup_entrance_routes(app):
    id = app["ID"]
    wrap = URLWrapper("/dandelion")
    app.router.add_route('*', wrap('/'), index)
    app.router.add_route('*',
                         wrap("ws"),
                         EntranceWebSocketHandler(),
                         name="ws")

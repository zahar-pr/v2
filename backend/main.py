import os

import aggregator
import catalog
import domain
import view
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
)
app = FastAPI(title="Поиск поставщиков продуктов питания")


class FreshStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-store"
        return response


@app.get("/api/options")
def api_options():
    return {
        "categories": [{"id": c.id, "title": c.title} for c in catalog.CATEGORIES],
        "places": list(catalog.PLACES),
        "defaults": {"category": catalog.DEFAULT_CATEGORY, "place": catalog.DEFAULT_PLACE},
    }


@app.get("/api/search")
async def api_search(
    place: str = Query(catalog.DEFAULT_PLACE, description="город или регион"),
    category: str = Query(catalog.DEFAULT_CATEGORY, description="id категории из /api/options"),
):
    chosen = catalog.category(category)
    if chosen is None:
        raise HTTPException(400, f"Неизвестная категория «{category}»")
    try:
        found = await aggregator.find(chosen, place)
    except domain.PlaceNotFound:
        raise HTTPException(404, f"Не нашёл регион «{place}»")
    except domain.SourceUnavailable as error:
        raise HTTPException(
            503, f"К сожалению ничего не нашлось, Попробуйте ещё раз другие город/поставщик. Ошибка ({error})."
        )
    return {"html": view.render(found)}


app.mount("/", FreshStaticFiles(directory=FRONTEND_DIR, html=True))

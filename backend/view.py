from html import escape

from domain import Supplier

CARD = """<div class="card supplier">
  <div class="score {level}">{score}</div>
  <div>
    <div><span class="name">{name}</span><span class="verdict">{verdict}</span></div>
    <div class="meta">{meta}</div>
    <div class="contacts">{contacts}</div>
    <div class="why">{why}</div>
  </div>
</div>"""
LINK = '<a href="{href}" target="_blank" class="{css}">{text}</a>'
NOTHING_FOUND = '<p class="small">Ничего не нашлось. Попробуйте другую категорию или город.</p>'


def render(suppliers: list[Supplier]) -> str:
    return "".join(_card(supplier) for supplier in suppliers) or NOTHING_FOUND


def _card(supplier: Supplier) -> str:
    rating = supplier.rating
    return CARD.format(
        level=rating.level,
        score=rating.score,
        name=escape(supplier.name),
        verdict=rating.verdict,
        meta=_meta(supplier),
        contacts=_contacts(supplier),
        why=escape(_why(supplier)),
    )


def _meta(supplier: Supplier) -> str:
    facts = [escape(supplier.kind)]
    if supplier.wholesale:
        facts.append("<b>опт/производство</b>")
    facts.append(escape(supplier.address))
    if supplier.branches > 1:
        facts.append(f"точек: {supplier.branches}")
    facts.append(escape(supplier.hours))
    return " · ".join(fact for fact in facts if fact)


def _contacts(supplier: Supplier) -> str:
    links = [_link(f"tel:{phone}", phone) for phone in supplier.phones]
    links += [_link(f"mailto:{email}", email) for email in supplier.emails]
    if supplier.website:
        links.append(_link(supplier.website, "сайт ↗"))
    links.append(_link(supplier.source, f"источник: {supplier.source_title} ↗", css="small"))
    return "".join(links)


def _link(href: str, text: str, css: str = "") -> str:
    return LINK.format(href=escape(href), text=escape(text), css=css)


def _why(supplier: Supplier) -> str:
    rating = supplier.rating
    why = "Плюсы: " + (", ".join(rating.plus) or "—")
    if rating.minus:
        why += ". Уточнить: " + ", ".join(rating.minus)
    return why

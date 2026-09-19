import React from 'react';
import FactorStrip from './FactorStrip.jsx';
import StatusPicker from './StatusPicker.jsx';
import { placeOf, plural, ratingOf, statusTitle, strongest, weakest } from '../data/suppliers.js';

export default function SupplierCard({
  supplier, index, statuses, inCompare, compareFull, onOpen, onCompare, onStatus,
}) {
  const s = supplier;
  const strong = strongest(s);
  const weak = weakest(s);
  const docs = s.certs.length;

  const spec = (label, value, ok) => (
    <div>
      <div className="specs__k">{label}</div>
      <div className={`specs__v${value ? (ok ? ' specs__v--ok' : '') : ' specs__v--none'}`}>
        {value || 'нет данных'}
      </div>
    </div>
  );

  return (
    <article className="card" style={{ animationDelay: `${Math.min(index, 8) * 0.04}s` }}>
      <div className="card__head">
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="card__title">{s.name}</div>
          <div className="card__sub">{placeOf(s)}</div>
        </div>
        <div className="card__rate">
          <div className={`prio prio--${s.level}`} title="Приоритет звонка по вашим настройкам">
            {s.score}
          </div>
          <div className="card__reviews">{s.verdict}</div>
        </div>
      </div>

      <div className="tags">
        <span className={`tag tag--${s.type}`}>{s.typeTitle}</span>
        {ratingOf(s) && (
          <span className="tag tag--rating" title={`Оценка на ${s.reviewsSource}`}>
            ★ {s.rating.toFixed(1)} · {s.reviewsSource}
          </span>
        )}
        {s.commentsCount > 0 && (
          <span className="tag tag--team" title="Оценка вашей команды">
            {s.commentsRating ? `★ ${s.commentsRating} · ` : ''}
            команда: {s.commentsCount}
          </span>
        )}
        {s.legalActive && <span className="tag tag--ok">действующее юрлицо</span>}
        {s.cats.slice(0, 2).map((c) => <span className="tag tag--cat" key={c}>{c}</span>)}
        {s.status !== 'new' && (
          <span className={`tag tag--status tag--${s.status}`}>{statusTitle(s.status, statuses)}</span>
        )}
        {s.verified && <span className="tag tag--ok">данные подтверждены</span>}
      </div>

      <FactorStrip factors={s.factors} onOpen={onOpen} />

      <div className="why">
        {strong && (
          <div className="why__row why__row--plus">
            <b>{strong.title}:</b> {strong.text}
          </div>
        )}
        {weak && (
          <div className="why__row why__row--minus">
            <b>{weak.title}:</b> {weak.text}
          </div>
        )}
      </div>

      <div className="specs">
        {spec('Мин. заказ', s.moq)}
        {spec('Цена', s.priceList ? 'прайс на сайте' : s.price, Boolean(s.priceList))}
        {spec('Доставка', s.delivery)}
        <div>
          <div className="specs__k">Документы</div>
          <div className={`specs__v ${docs ? 'specs__v--ok' : 'specs__v--none'}`}>
            {docs ? `${docs} ${plural(docs, 'документ', 'документа', 'документов')}` : 'не найдены'}
          </div>
        </div>
      </div>

      {s.okved && (
        <div className="card__okved" title="Основной вид деятельности по данным ФНС">
          ОКВЭД {s.okved} · {s.okvedName}
        </div>
      )}

      {!s.phone && !s.email && s.checkLinks.length > 0 && (
        <a
          className="card__manual"
          href={s.checkLinks[0].url}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
        >
          Контактов нет — найти в Яндексе ↗
        </a>
      )}

      <div className="card__actions">
        <button type="button" className="btn btn--deep" onClick={onOpen}>Подробнее</button>
        <button
          type="button"
          className={`btn ${inCompare ? 'btn--in' : compareFull ? 'btn--full' : 'btn--ghost'}`}
          onClick={onCompare}
          disabled={compareFull}
        >
          {inCompare ? 'В сравнении' : compareFull ? 'Слот занят' : 'Сравнить'}
        </button>
        <StatusPicker value={s.status} statuses={statuses} onChange={onStatus} compact />
      </div>
    </article>
  );
}

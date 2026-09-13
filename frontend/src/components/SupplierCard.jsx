import React from 'react';
import { plural, score } from '../data/suppliers.js';

export default function SupplierCard({ supplier, index, inCompare, compareFull, onOpen, onCompare }) {
  const s = supplier;
  const docs = s.certs.length;
  const matched = score(s);

  const spec = (label, value) => (
    <div>
      <div className="specs__k">{label}</div>
      <div className={`specs__v${value ? '' : ' specs__v--none'}`}>{value || 'нет данных'}</div>
    </div>
  );

  return (
    <article className="card" style={{ animationDelay: `${Math.min(index, 8) * 0.04}s` }}>
      <div className="card__head">
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="card__title">{s.name}</div>
          <div className="card__sub">{[s.city, s.cats[0]].filter(Boolean).join(' · ')}</div>
        </div>
        <div className="card__rate">
          <div className="rating" title="Рейтинг данных: насколько полно заполнена карточка">
            <strong>{s.rating ? s.rating.toFixed(1) : '—'}</strong><span>/5</span>
          </div>
          <div className="card__reviews">
            {s.reviews
              ? `${s.reviews} ${plural(s.reviews, 'отзыв', 'отзыва', 'отзывов')}`
              : `${s.sourcesCount} ${plural(s.sourcesCount, 'источник', 'источника', 'источников')}`}
          </div>
        </div>
      </div>

      <div className="tags">
        {s.cats.slice(0, 3).map((c) => <span className="tag" key={c}>{c}</span>)}
        {s.wholesale && <span className="tag tag--ok">опт/производство</span>}
        {s.verified && <span className="tag tag--ok">данные подтверждены</span>}
        {s.geo && <span className="tag">поставки: {s.geo}</span>}
      </div>

      <div className="specs">
        {spec('Мин. заказ', s.moq)}
        {spec('Цена', s.price)}
        {spec('Доставка', s.delivery)}
        <div>
          <div className="specs__k">Документы</div>
          <div className={`specs__v ${docs ? 'specs__v--ok' : 'specs__v--none'}`}>
            {docs ? `${docs} ${plural(docs, 'документ', 'документа', 'документов')}` : 'нет данных'}
          </div>
        </div>
      </div>

      <div className="score">
        <div className="score__track"><div className="score__fill" style={{ width: `${matched}%` }} /></div>
        <div className="score__label">готовность {matched}%</div>
      </div>

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
      </div>
    </article>
  );
}

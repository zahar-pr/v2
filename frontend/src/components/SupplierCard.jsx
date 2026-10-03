import React from 'react';
import FactorStrip from './FactorStrip.jsx';
import StatusPicker from './StatusPicker.jsx';
import SafetyBadge from './SafetyBadge.jsx';
import PriceTag from './PriceTag.jsx';
import { placeOf, plural, statusTitle, strongest, weakest } from '../data/suppliers.js';

/** Пустые поля не рисуем: строка выдачи должна показывать то, что известно. */
function factsOf(s) {
  const docs = s.certs.length;
  return [
    ['Мин. заказ', s.moq, false],
    ['Цена', s.priceList ? 'прайс на сайте' : s.price, Boolean(s.priceList)],
    ['Доставка', s.delivery, false],
    ['Документы', docs ? `${docs} ${plural(docs, 'документ', 'документа', 'документов')}` : '', true],
  ].filter(([, value]) => value);
}

function reviewTag(s) {
  const box = s.reviewsSummary || {};
  if (box.externalAverage === null || box.externalAverage === undefined) return null;
  const count = box.externalCount
    ? ` · ${box.externalCount} ${plural(box.externalCount, 'отзыв', 'отзыва', 'отзывов')}`
    : '';
  return `★ ${box.externalAverage}${count}`;
}

export default function SupplierCard({
  supplier, index, statuses, inCompare, compareFull, onOpen, onCompare, onStatus,
}) {
  const s = supplier;
  const strong = strongest(s);
  const weak = weakest(s);
  const facts = factsOf(s);
  const reviews = reviewTag(s);
  const tone = (s.safety && s.safety.tone) || 'none';

  return (
    <article
      className={`row row--tone-${tone}${s.trustTier ? ` row--${s.trustTier}` : ''}`}
      style={{ animationDelay: `${Math.min(index, 8) * 0.03}s` }}
    >
      <div className="row__main">
        <div className="row__marks">
          <SafetyBadge safety={s.safety} />
          {s.trustTier === 'trusted' && s.clients.length > 0 && (
            <span className="mark mark--trusted">Возит сетям: {s.clients.slice(0, 3).join(', ')}</span>
          )}
        </div>

        <button type="button" className="row__name" onClick={onOpen}>{s.name}</button>
        <div className="row__sub">
          {[s.typeTitle, placeOf(s), s.years].filter(Boolean).join(' · ')}
        </div>

        {s.coverage && s.coverage.reason && (
          <div className="row__reach">{s.coverage.reason}</div>
        )}

        <div className="tags">
          <PriceTag price={s.priceLevel} />
          {reviews && (
            <span className="tag tag--rating" title={(s.reviewsSummary || {}).verdict}>
              {reviews}
            </span>
          )}
          {s.commentsCount > 0 && (
            <span className="tag tag--team" title="Оценка вашей команды">
              {s.commentsRating ? `★ ${s.commentsRating} · ` : ''}
              команда: {s.commentsCount}
            </span>
          )}
          <span className="tag tag--fill" title="Сколько полей профиля заполнено">
            профиль {s.profile.percent}%
          </span>
          {s.cats.slice(0, 2).map((c) => <span className="tag tag--cat" key={c}>{c}</span>)}
          {s.status !== 'new' && (
            <span className={`tag tag--status tag--${s.status}`}>
              {statusTitle(s.status, statuses)}
              {s.statusDays ? ` · ${s.statusDays} дн` : ''}
            </span>
          )}
        </div>

        {s.trustNote && <p className="row__note">{s.trustNote}</p>}

        <FactorStrip factors={s.factors} onOpen={onOpen} />

        <div className="why">
          {strong && (
            <div className="why__row why__row--plus"><b>{strong.title}:</b> {strong.text}</div>
          )}
          {weak && (
            <div className="why__row why__row--minus"><b>{weak.title}:</b> {weak.text}</div>
          )}
        </div>

        {facts.length > 0 ? (
          <div className="facts-line">
            {facts.map(([label, value, ok]) => (
              <div className="fact" key={label}>
                <span className="fact__k">{label}</span>
                <span className={`fact__v${ok ? ' fact__v--ok' : ''}`}>{value}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="facts-none">
            Условий в источниках нет — {s.profile.missing.length} полей закрываются одним звонком
          </div>
        )}

        {s.okved && (
          <div className="row__okved" title="Основной вид деятельности по данным ФНС">
            ОКВЭД {s.okved} · {s.okvedName}
          </div>
        )}
      </div>

      <div className="row__side">
        <div className="row__score">
          <div className={`prio prio--${s.level}`} title="Приоритет звонка по вашим настройкам">
            {s.score}
          </div>
          <span className="row__verdict">{s.verdict}</span>
        </div>

        {s.phone && (
          <a className="row__phone" href={`tel:${s.phone.replace(/[^+\d]/g, '')}`}>{s.phone}</a>
        )}
        {!s.phone && s.email && (
          <a className="row__phone" href={`mailto:${s.email}`}>{s.email}</a>
        )}
        {!s.phone && !s.email && s.checkLinks.length > 0 && (
          <a
            className="row__find" href={s.checkLinks[0].url} target="_blank" rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            Контактов нет — найти ↗
          </a>
        )}

        <div className="row__actions">
          <button type="button" className="btn btn--deep" onClick={onOpen}>Досье</button>
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
      </div>
    </article>
  );
}

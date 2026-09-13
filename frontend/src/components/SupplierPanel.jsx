import React, { useEffect } from 'react';
import { checkedAt, dash, plural, score } from '../data/suppliers.js';

export default function SupplierPanel({ supplier, note, onNote, inCompare, compareFull, onCompare, onClose }) {
  const s = supplier;
  const tel = (value) => value.replace(/[^+\d]/g, '');

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  const facts = [
    ['Категории', s.cats.join(', ')],
    ['Город', dash(s.city)],
    ...(s.address && s.address !== s.city ? [['Адрес', s.address]] : []),
    ['Часы работы', dash(s.hours)],
    ['Опт или производство', s.wholesale ? 'да, по данным источника' : 'нет данных'],
    ...(s.branches > 1 ? [['Точек в городе', String(s.branches)]] : []),
    ['Регион работы', dash(s.geo || s.region)],
    ['Минимальный заказ', dash(s.moq)],
    ['Примерная цена', dash(s.price)],
    ['Доставка', dash(s.delivery)],
    ['На рынке', dash(s.years)],
    ...(s.inn ? [['ИНН', s.inn]] : []),
    ...(s.ogrn ? [['ОГРН', s.ogrn]] : []),
    ['Готовность к контакту', `${score(s)}%${s.verdict ? ` · ${s.verdict}` : ''}`],
  ];

  return (
    <>
      <button type="button" className="scrim" aria-label="Закрыть" onClick={onClose} />
      <aside className="panel" role="dialog" aria-label={s.name}>
        <div className="panel__head">
          <h2>{s.name}</h2>
          <button type="button" className="panel__close" onClick={onClose} aria-label="Закрыть">✕</button>
        </div>

        <div className="panel__body">
          <div className="panel__meta">
            <div className="rating" title="Рейтинг данных: насколько полно заполнена карточка">
              <strong>{s.rating ? s.rating.toFixed(1) : '—'}</strong><span>/5</span>
            </div>
            <small>
              {s.reviews
                ? `${s.reviews} ${plural(s.reviews, 'отзыв', 'отзыва', 'отзывов')}`
                : `${s.sourcesCount} ${plural(s.sourcesCount, 'источник', 'источника', 'источников')}`}
              {checkedAt(s) ? ` · проверено ${checkedAt(s)}` : ''}
            </small>
            <span className={`badge ${s.verified ? 'badge--ok' : 'badge--warn'}`}>
              {s.verified ? 'Данные подтверждены' : 'Требует проверки'}
            </span>
          </div>

          {s.about && <p className="panel__about">{s.about}</p>}

          <div>
            <div className="section-title">Условия работы</div>
            <div className="facts">
              {facts.map(([k, v]) => (
                <div className="facts__row" key={k}>
                  <div className="facts__k">{k}</div>
                  <div className="facts__v">{v}</div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="section-title">Документы</div>
            <div className="certs">
              {(s.certs.length ? s.certs : ['Документы не найдены в открытых источниках']).map((c) => (
                <span className="cert" key={c}>{c}</span>
              ))}
            </div>
          </div>

          <div>
            <div className="section-title">Контакты</div>
            <div className="contacts">
              {s.manager && (
                <div className="contacts__row">
                  <span className="contacts__k">Менеджер</span>
                  <span className="contacts__v">{s.manager}</span>
                </div>
              )}
              <div className="contacts__row">
                <span className="contacts__k">Телефон</span>
                {s.phones.length ? (
                  <span className="contacts__v">
                    {s.phones.map((phone, i) => (
                      <React.Fragment key={phone}>
                        {i > 0 && ' · '}
                        <a href={`tel:${tel(phone)}`}>{phone}</a>
                      </React.Fragment>
                    ))}
                  </span>
                ) : (
                  <span className="contacts__v contacts__v--muted">нет данных</span>
                )}
              </div>
              <div className="contacts__row">
                <span className="contacts__k">Почта</span>
                {s.emails.length ? (
                  <span className="contacts__v">
                    {s.emails.map((email, i) => (
                      <React.Fragment key={email}>
                        {i > 0 && ' · '}
                        <a href={`mailto:${email}`}>{email}</a>
                      </React.Fragment>
                    ))}
                  </span>
                ) : (
                  <span className="contacts__v contacts__v--muted">нет данных</span>
                )}
              </div>
              <div className="contacts__row">
                <span className="contacts__k">Сайт</span>
                {s.site && s.site !== '—'
                  ? <a className="contacts__v" href={`https://${s.site}`} target="_blank" rel="noreferrer">{s.site}</a>
                  : <span className="contacts__v contacts__v--muted">нет сайта</span>}
              </div>
            </div>
          </div>

          <div>
            <div className="section-title">Источники данных</div>
            <div className="sources">
              {(s.sources.length ? s.sources : [{ id: 'none', title: s.sourceTitle, url: s.source }])
                .map((item) => (
                  <a
                    className="source"
                    key={item.id + item.url}
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {item.title} ↗
                  </a>
                ))}
            </div>
            {s.verified && s.verifiedBy && <div className="note__status">{s.verifiedBy}</div>}
          </div>

          <div>
            <div className="section-title">Заметки по поставщику</div>
            <textarea
              className="note"
              value={note || ''}
              onChange={(e) => onNote(e.target.value)}
              placeholder="Например: запросили КП на 20.09, обещали прайс с отсрочкой 14 дней"
            />
            <div className="note__status">
              {note ? 'Заметка сохраняется автоматически' : 'Заметка пока пустая'}
            </div>
          </div>

          <div className="panel__cta">
            {s.email
              ? <a href={`mailto:${s.email}`}>Написать поставщику</a>
              : s.phone
                ? <a href={`tel:${tel(s.phone)}`}>Позвонить поставщику</a>
                : <a href={s.source} target="_blank" rel="noreferrer">Открыть источник</a>}
            <button
              type="button"
              className={`btn ${inCompare ? 'btn--in' : compareFull ? 'btn--full' : 'btn--ghost'}`}
              onClick={onCompare}
              disabled={compareFull}
            >
              {inCompare ? 'В сравнении' : compareFull ? 'Слот занят' : 'Сравнить'}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

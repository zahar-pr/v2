import React, { useEffect, useState } from 'react';
import StatusPicker from './StatusPicker.jsx';
import { checkedAt, dash, placeOf, plural, ratingOf } from '../data/suppliers.js';

export default function SupplierPanel({
  supplier, note, statuses, onNote, onStatus, inCompare, compareFull, onCompare, onClose,
}) {
  const s = supplier;
  const [done, setDone] = useState({});
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
    ['Тип поставщика', s.typeTitle],
    ['Категории', s.cats.join(', ')],
    ['Где находится', placeOf(s) || '—'],
    ...(s.address && s.address !== s.city ? [['Адрес', s.address]] : []),
    ['Часы работы', dash(s.hours)],
    ...(s.branches > 1 ? [['Точек в городе', String(s.branches)]] : []),
    ['Регион поставок', dash(s.geo || s.region)],
    ['Минимальный заказ', dash(s.moq)],
    ['Цена', dash(s.price)],
    ['Доставка', dash(s.delivery)],
    ['На рынке', dash(s.years)],
  ];

  const legal = [
    ['Юрлицо', dash(s.legalName)],
    ['Статус в ФНС', dash(s.legalStatus)],
    ['Основной ОКВЭД', dash([s.okved, s.okvedName].filter(Boolean).join(' · '))],
    ['Руководитель', dash(s.legalHead)],
    ['ИНН', dash(s.inn)],
    ['ОГРН', dash(s.ogrn)],
    ['На рынке', dash(s.years)],
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
            <div className={`prio prio--${s.level}`}>{s.score}</div>
            <div>
              <div className="panel__verdict">{s.verdict}</div>
              <small>
                {s.rank ? `${s.rank}-е место в выдаче · ` : ''}
                {s.sourcesCount} {plural(s.sourcesCount, 'источник', 'источника', 'источников')}
                {checkedAt(s) ? ` · проверено ${checkedAt(s)}` : ''}
              </small>
            </div>
            <span className={`badge ${s.verified ? 'badge--ok' : 'badge--warn'}`}>
              {s.verified ? 'Данные подтверждены' : 'Требует проверки'}
            </span>
          </div>

          {s.legalClosed && (
            <div className="alarm">
              В ЕГРЮЛ есть запись о прекращении деятельности — проверьте статус юрлица перед сделкой.
            </div>
          )}

          {s.about && <p className="panel__about">{s.about}</p>}

          <div>
            <div className="section-title">Почему такой приоритет</div>
            <div className="scorecard">
              {s.factors.map((f) => (
                <div className="srow" key={f.id}>
                  <div className="srow__head">
                    <span className="srow__title" title={f.hint}>{f.title}</span>
                    <span className="srow__weight">вес {f.weight}%</span>
                    <span className="srow__score">{f.score}</span>
                  </div>
                  <div className="srow__track">
                    <span className="srow__fill" style={{ width: `${f.score}%` }} />
                  </div>
                  {f.plus.map((text) => (
                    <div className="srow__line srow__line--plus" key={text}>{text}</div>
                  ))}
                  {f.minus.map((text) => (
                    <div className="srow__line srow__line--minus" key={text}>{text}</div>
                  ))}
                </div>
              ))}
            </div>
          </div>

          {s.ask.length > 0 && (
            <div>
              <div className="section-title">Что уточнить в первом звонке</div>
              <div className="asklist">
                {s.ask.map((question) => (
                  <label className={`askitem${done[question] ? ' askitem--done' : ''}`} key={question}>
                    <input
                      type="checkbox"
                      checked={Boolean(done[question])}
                      onChange={() => setDone((prev) => ({ ...prev, [question]: !prev[question] }))}
                    />
                    {question}
                  </label>
                ))}
              </div>
            </div>
          )}

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
            {s.priceList && (
              <a className="source" href={s.priceList} target="_blank" rel="noreferrer">
                Прайс-лист на сайте ↗
              </a>
            )}
          </div>

          <div>
            <div className="section-title">Юрлицо и реквизиты</div>
            <div className="facts">
              {legal.map(([k, v]) => (
                <div className="facts__row" key={k}>
                  <div className="facts__k">{k}</div>
                  <div className="facts__v">{v}</div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="section-title">Отзывы и оценки</div>
            {ratingOf(s) ? (
              <div className="reviews">
                <div className="reviews__score">{s.rating.toFixed(1)}</div>
                <div>
                  <div className="reviews__count">
                    {s.reviews} {plural(s.reviews, 'отзыв', 'отзыва', 'отзывов')}
                  </div>
                  <small>по данным подключённых справочников</small>
                </div>
              </div>
            ) : (
              <div className="reviews reviews--empty">
                Оценок в подключённых источниках нет. Откройте отзывы и решите сами:
              </div>
            )}
            <div className="sources">
              {s.reviewLinks.map((item) => (
                <a className="source" key={item.url} href={item.url} target="_blank" rel="noreferrer">
                  {item.title} ↗
                </a>
              ))}
            </div>
          </div>

          <div>
            <div className="section-title">Контакты</div>
            <div className="contacts">
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
              {s.socials.length > 0 && (
                <div className="contacts__row">
                  <span className="contacts__k">Соцсети</span>
                  <span className="contacts__v">
                    {s.socials.map((item, i) => (
                      <React.Fragment key={item.url}>
                        {i > 0 && ' · '}
                        <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a>
                      </React.Fragment>
                    ))}
                  </span>
                </div>
              )}
            </div>

            <div className={`manual${s.phone || s.email ? '' : ' manual--urgent'}`}>
              <div className="manual__title">
                {s.phone || s.email
                  ? 'Проверить данные вручную'
                  : 'Контактов в открытых источниках нет — найдите вручную'}
              </div>
              <div className="sources">
                {s.checkLinks.map((item) => (
                  <a className="source" key={item.url} href={item.url} target="_blank" rel="noreferrer">
                    {item.title} ↗
                  </a>
                ))}
              </div>
            </div>
          </div>

          <div>
            <div className="section-title">Источники данных</div>
            <div className="sources">
              {(s.sources.length ? s.sources : [{ id: 'none', title: s.sourceTitle, url: s.source }])
                .map((item) => (
                  <a className="source" key={item.id + item.url} href={item.url} target="_blank" rel="noreferrer">
                    {item.title} ↗
                  </a>
                ))}
            </div>
            {s.verified && s.verifiedBy && <div className="note__status">{s.verifiedBy}</div>}
          </div>

          <div>
            <div className="section-title">Работа с поставщиком</div>
            <StatusPicker value={s.status} statuses={statuses} onChange={onStatus} />
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
            {s.phone
              ? <a href={`tel:${tel(s.phone)}`}>Позвонить</a>
              : s.email
                ? <a href={`mailto:${s.email}`}>Написать</a>
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

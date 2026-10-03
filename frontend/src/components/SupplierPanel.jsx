import React, { useEffect, useState } from 'react';
import StatusPicker from './StatusPicker.jsx';
import Comments from './Comments.jsx';
import SafetyBadge from './SafetyBadge.jsx';
import PriceTag from './PriceTag.jsx';
import { setCheck } from '../api/client.js';
import { ageText, checkedAt, dash, placeOf, plural, quoteLetter } from '../data/suppliers.js';

export default function SupplierPanel({
  supplier, note, statuses, onNote, onStatus, onComment,
  inCompare, compareFull, onCompare, onClose,
}) {
  const s = supplier;
  const [done, setDone] = useState(() => new Set(supplier.checksDone || []));
  const [allGaps, setAllGaps] = useState(false);
  const tel = (value) => value.replace(/[^+\d]/g, '');
  const reviews = s.reviewsSummary || {};

  useEffect(() => {
    setDone(new Set(supplier.checksDone || []));
  }, [supplier.id, supplier.checksDone]);

  const toggleCheck = (question) => {
    const next = new Set(done);
    const marked = !next.has(question);
    if (marked) next.add(question);
    else next.delete(question);
    setDone(next);
    setCheck(s.id, question, marked).catch(() => {});
  };

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

  const gaps = allGaps ? s.profile.missing : s.profile.missing.slice(0, 6);

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
            <PriceTag price={s.priceLevel} />
          </div>

          {s.coverage && s.coverage.reason && (
            <div className="reachline">{s.coverage.reason}</div>
          )}

          {s.about && <p className="panel__about">{s.about}</p>}

          <div>
            <div className="section-title">Санитарная история</div>
            <div className={`safebox safebox--${s.safety.tone}`}>
              <div className="safebox__head">
                <SafetyBadge safety={s.safety} compact />
              </div>
              <p className="safebox__text">{s.safety.text}</p>

              {s.safety.incident && (
                <div className="safebox__grid">
                  <div><span>Решение</span><b>{s.safety.incident.date}</b></div>
                  {s.safety.incident.days > 0 && (
                    <div>
                      <span>Срок приостановки</span>
                      <b>
                        {s.safety.incident.days} суток
                        {s.safety.incident.until ? ` · до ${s.safety.incident.until}` : ''}
                      </b>
                    </div>
                  )}
                  <div>
                    <span>Ограничение сейчас</span>
                    <b>{s.safety.incident.active ? 'действует' : 'снято'}</b>
                  </div>
                  {s.safety.incident.chain && (
                    <div><span>Возил в сеть</span><b>{s.safety.incident.chain}</b></div>
                  )}
                </div>
              )}

              {s.safety.incident && s.safety.incident.source && (
                <a
                  className="source" href={s.safety.incident.source}
                  target="_blank" rel="noreferrer"
                >
                  {s.safety.incident.sourceTitle || 'Публикация'} ↗
                </a>
              )}

              {s.safety.docs.length > 0 && (
                <div className="safebox__docs">
                  {s.safety.docs.map((item) => <span className="cert" key={item}>{item}</span>)}
                </div>
              )}
            </div>
          </div>

          <div>
            {s.trustTier === 'trusted' && (
              <div className="verdictbox verdictbox--trusted">
                <div className="verdictbox__title">{s.verdict}</div>

                {s.clients.length > 0 && (
                  <div className="verdictbox__part">
                    <div className="verdictbox__label">Поставляет сетям</div>
                    <div className="chainlist">
                      {s.clients.map((chain) => (
                        <span className="chain" key={chain}>{chain}</span>
                      ))}
                    </div>
                  </div>
                )}

                {s.products.length > 0 && (
                  <div className="verdictbox__part">
                    <div className="verdictbox__label">Что именно возит</div>
                    <div className="verdictbox__value">{s.products.join(', ')}</div>
                  </div>
                )}

                {s.geo && (
                  <div className="verdictbox__part">
                    <div className="verdictbox__label">География поставок</div>
                    <div className="verdictbox__value">{s.geo}</div>
                  </div>
                )}

                <p className="verdictbox__text">{s.trustNote}</p>

                {s.sources.length > 0 && (
                  <div className="verdictbox__part">
                    <div className="verdictbox__label">Чем подтверждается</div>
                    <div className="verdictbox__links">
                      {s.sources.map((item) => (
                        <a key={item.url} href={item.url} target="_blank" rel="noreferrer">
                          {item.title} ↗
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="section-title">Уровень цен</div>
            <div className={`pricebox pricebox--${s.priceLevel.tier}`}>
              <div className="pricebox__head">
                <b>{s.priceLevel.title}</b>
                <span>{s.priceLevel.hint}</span>
              </div>
              <ul className="pricebox__why">
                {s.priceLevel.why.map((line) => <li key={line}>{line}</li>)}
              </ul>
              {s.priceLevel.estimate && (
                <div className="pricebox__note">
                  Это оценка уровня, а не цена из прайса: прайс запрашивается у поставщика.
                  Сравнить с текущим можно сразу после первого КП.
                </div>
              )}
            </div>
          </div>

          <div>
            <div className="section-title">
              Отзывы
              {reviews.demo && <span className="demo">часть строк — демо</span>}
            </div>
            <div className="revbox">
              <div className="revbox__verdict">{reviews.verdict}</div>

              {reviews.teamCount > 0 && (
                <div className="revrow">
                  <div className="revrow__score">
                    {reviews.teamRating ? reviews.teamRating : '—'}
                  </div>
                  <div className="revrow__body">
                    <b>Коллеги в Goulash</b>
                    <small>
                      {reviews.teamCount}{' '}
                      {plural(reviews.teamCount, 'комментарий', 'комментария', 'комментариев')}
                      {' '}— ниже на этой странице
                    </small>
                  </div>
                </div>
              )}

              {reviews.external.map((item) => (
                <div className="revrow" key={item.id + item.source}>
                  <div className="revrow__score">{item.rating}</div>
                  <div className="revrow__body">
                    <b>
                      {item.source}
                      {item.demo && <span className="demo demo--inline">демо</span>}
                    </b>
                    <small>
                      {item.count
                        ? `${item.count} ${plural(item.count, 'отзыв', 'отзыва', 'отзывов')}`
                        : 'оценка без счётчика'}
                    </small>
                  </div>
                  {item.url && (
                    <a href={item.url} target="_blank" rel="noreferrer">Открыть ↗</a>
                  )}
                </div>
              ))}

              <div className="sources">
                {s.reviewLinks.map((item) => (
                  <a className="source" key={item.url} href={item.url} target="_blank" rel="noreferrer">
                    {item.title} ↗
                  </a>
                ))}
              </div>
            </div>
          </div>

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
                  <label className={`askitem${done.has(question) ? ' askitem--done' : ''}`} key={question}>
                    <input
                      type="checkbox"
                      checked={done.has(question)}
                      onChange={() => toggleCheck(question)}
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
            <div className="section-title">
              Профиль заполнен на {s.profile.percent}%
            </div>
            <div className="fill">
              <div className="fill__track">
                <span className="fill__bar" style={{ width: `${s.profile.percent}%` }} />
              </div>
              <div className="fill__count">
                {s.profile.filled} из {s.profile.total} полей
              </div>
            </div>
            {s.profile.missing.length > 0 && (
              <>
                <div className="fill__hint">
                  Чего не хватает и зачем это нужно — спросите в первом разговоре:
                </div>
                <div className="gaps">
                  {gaps.map((item) => (
                    <div className="gap" key={item.title}>
                      <b>{item.title}</b>
                      <span>{item.why}</span>
                    </div>
                  ))}
                </div>
                {s.profile.missing.length > 6 && (
                  <button
                    type="button" className="fill__more"
                    onClick={() => setAllGaps((v) => !v)}
                  >
                    {allGaps ? 'Свернуть' : `Показать все ${s.profile.missing.length}`}
                  </button>
                )}
              </>
            )}
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
            <div className="section-title">Проверить самому</div>
            <div className="regs__hint">
              {s.inn
                ? `Девять государственных реестров с подставленным ИНН ${s.inn} — открывается в один клик.`
                : 'ИНН мы не нашли, поэтому ссылки открывают поиск по названию компании.'}
            </div>
            <div className="regs">
              {s.registries.map((item) => (
                <a className="reg" key={item.id} href={item.url} target="_blank" rel="noreferrer">
                  <b>{item.title}</b>
                  <span>{item.why}</span>
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

          <Comments supplierId={s.id} onChanged={onComment} />

          <div>
            <div className="section-title">Работа с поставщиком</div>
            <StatusPicker value={s.status} statuses={statuses} onChange={onStatus} />
            {s.status !== 'new' && s.statusAuthor && (
              <div className="note__status">
                Статус поставил {s.statusAuthor} {ageText(s.statusDays)}
              </div>
            )}
            <textarea
              className="note"
              value={note || ''}
              onChange={(e) => onNote(e.target.value)}
              placeholder="Например: запросили КП на 20.09, обещали прайс с отсрочкой 14 дней"
            />
            <div className="note__status">
              {note
                ? `Заметка команды${s.noteAuthor ? `, последним правил ${s.noteAuthor}` : ''} — сохраняется автоматически`
                : 'Заметку видит вся команда'}
            </div>
          </div>

          <div className="panel__cta">
            {s.phone
              ? <a href={`tel:${tel(s.phone)}`}>Позвонить</a>
              : s.email
                ? <a href={quoteLetter(s)}>Запросить КП</a>
                : <a href={s.source} target="_blank" rel="noreferrer">Открыть источник</a>}
            {s.email && s.phone && (
              <a
                className="btn btn--ghost"
                href={quoteLetter(s)}
                onClick={() => { if (s.status === 'new') onStatus('quoted'); }}
              >
                Запросить КП
              </a>
            )}
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

import React, { useEffect } from 'react';
import { plural, statusTitle } from '../data/suppliers.js';

const WHEN = (at) => (at ? new Date(at * 1000).toLocaleDateString('ru-RU') : '');

/**
 * Кабинет Goulash Tech. Аккаунт один на всю команду — логина нет намеренно:
 * закупки ведёт одна компания, и статусы с заметками видят все.
 */
export default function Workspace({ data, statuses, loading, onPick, onOpen, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  const funnel = [
    ['В работе', data && data.working],
    ['Запросили КП', data && data.quoted],
    ['Подходят', data && data.fit],
    ['Отказ', data && data.rejected],
  ];

  return (
    <div className="modal" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal__in">
        <div className="modal__sheet">
          <div className="modal__head">
            <h2>Кабинет Goulash Tech</h2>
            <button type="button" className="btn btn--cyan" onClick={onClose}>Закрыть</button>
          </div>

          {loading && <div className="modal__hint">Открываем кабинет…</div>}

          {!loading && data && (
            <div className="ws">
              <div className="ws__top">
                <div className="ws__who">
                  <strong>{data.company}</strong>
                  <small>
                    Закупки для {data.chains} сетей общепита · база в {data.city}
                  </small>
                </div>
                <div className="ws__funnel">
                  {funnel.map(([label, value]) => (
                    <div className="ws__cell" key={label}>
                      <b>{value || 0}</b>
                      <span>{label}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="ws__hint">
                Проект — это сеть-заказчик со своим городом и набором продуктов. Выберите
                проект, и выдача отфильтруется под его закупку.
              </div>
              <div className="ws__warn">
                <b>Цифры в карточках — это кандидаты из нашей базы под такую закупку, а не
                список действующих поставщиков сети.</b> Кто у кого закупает на самом деле,
                торговые сети не публикуют. Набор категорий выведен из кухни сети, а не из её
                договоров. Единственное, что здесь привязано к конкретной сети документально, —
                красная строка о санитарных решениях: это её бывшие поставщики, со ссылками на
                публикации в карточках.
              </div>

              <div className="ws__grid">
                {data.projects.map((item) => (
                  <button
                    type="button" className="wscard" key={item.id}
                    onClick={() => onPick(item)}
                  >
                    <div className="wscard__head">
                      <strong>{item.chain}</strong>
                      <span className="wscard__city">{item.cityTitle}</span>
                    </div>
                    <div className="wscard__kitchen">{item.kitchen}</div>
                    <div className="wscard__need">{item.need}</div>
                    <div className="wscard__cats">
                      {item.catTitles.map((title) => (
                        <span key={title}>{title}</span>
                      ))}
                    </div>
                    {item.incidents.length > 0 && (
                      <div className="wscard__alarm">
                        По публикациям, {item.incidents.length}{' '}
                        {plural(item.incidents.length, 'поставщик', 'поставщика', 'поставщиков')}
                        {' '}этой сети попал
                        {item.incidents.length === 1 ? '' : 'и'} под санитарные решения
                      </div>
                    )}
                    <div className="wscard__foot">
                      <span title="Сколько компаний в нашей базе подходит под этот срез">
                        <b>{item.found}</b>{' '}
                        {plural(item.found, 'кандидат', 'кандидата', 'кандидатов')}
                      </span>
                      <span className="wscard__safe">
                        <b>{item.safe}</b> без замечаний
                      </span>
                    </div>
                  </button>
                ))}
              </div>

              {data.activity.length > 0 && (
                <>
                  <div className="section-title">Последние действия команды</div>
                  <div className="ws__feed">
                    {data.activity.map((item) => (
                      <button
                        type="button" className="wsline" key={item.supplierId + item.at}
                        onClick={() => onOpen(item.supplierId)}
                      >
                        <span className={`tag tag--status tag--${item.status}`}>
                          {statusTitle(item.status, statuses)}
                        </span>
                        <b>{item.name}</b>
                        <span className="wsline__meta">
                          {[item.city, item.author, WHEN(item.at)].filter(Boolean).join(' · ')}
                        </span>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

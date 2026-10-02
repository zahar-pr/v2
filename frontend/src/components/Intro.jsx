import React, { useEffect, useRef, useState } from 'react';

const FLY_MS = 420;

/** Короткая памятка на первый заход: как читать балл и цветные карточки. */
export default function Intro({ weights, onDetails, onClose }) {
  const sheet = useRef(null);
  const [leaving, setLeaving] = useState(false);

  // Закрываясь, окно улетает в кнопку «?» — чтобы было видно, где его потом искать.
  const leave = (then) => {
    const box = sheet.current;
    const target = document.querySelector('.helper');
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!box || !target || still) {
      then();
      return;
    }

    const from = box.getBoundingClientRect();
    const to = target.getBoundingClientRect();
    box.style.setProperty('--fly-x', `${to.left + to.width / 2 - (from.left + from.width / 2)}px`);
    box.style.setProperty('--fly-y', `${to.top + to.height / 2 - (from.top + from.height / 2)}px`);
    box.style.setProperty('--fly-scale', `${Math.max(to.width / from.width, 0.05)}`);
    target.classList.add('helper--caught');
    setLeaving(true);
    window.setTimeout(() => {
      target.classList.remove('helper--caught');
      then();
    }, FLY_MS);
  };

  const close = () => leave(onClose);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') close(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  });

  const order = ['reputation', 'volume', 'reach', 'docs', 'logistics', 'trust'];
  const titles = {
    reputation: 'Репутация',
    volume: 'Опт и объёмы',
    reach: 'Связь',
    docs: 'Документы',
    logistics: 'Логистика',
    trust: 'Достоверность',
  };

  return (
    <div
      className={`modal${leaving ? ' modal--leaving' : ''}`}
      onClick={(e) => { if (e.target === e.currentTarget) close(); }}
    >
      <div className="modal__in modal__in--narrow">
        <div className="modal__sheet" ref={sheet}>
          <div className="modal__head">
            <h2>Как читать выдачу</h2>
            <button type="button" className="btn btn--cyan" onClick={close}>Понятно</button>
          </div>

          <div className="intro">
            <section className="intro__item">
              <h3 className="intro__title">Балл — это количество доверия</h3>
              <p>
                От 0 до 100: с кем связаться ПЕРВЫМ, а НЕ чей продукт ВКУСНЕЕ — качество еды по
                открытым данным ЗНАТЬ НЕЛЬЗЯ.
              </p>
            </section>

            <section className="intro__item">
              <h3 className="intro__title">Профиль «Сбалансировано»</h3>
              <p>
                Шесть факторов с весами. Система считает ее по многим факторам и отдает ей большее
                предпочтение. Вот система расчета весов факторов:
              </p>
              <div className="intro__weights">
                {order.map((id) => (
                  <span className="intro__weight" key={id}>
                    {titles[id]} <b>{weights[id]}</b>
                  </span>
                ))}
              </div>
              <p className="intro__after">
                Но есть и исключения - компании, которые набирают 100 или 0 из-за других факторов
                (их рейтинг выставляется автоматически)
              </p>
            </section>

            <section className="intro__item intro__item--good">
              <h3 className="intro__title">Зелёные — 100 баллов</h3>
              <p>
                Поставщики крупных сетей общепита. Им дается МАКСИМАЛЬНЫЙ рейтинг, даже если данных
                мало: за них говорит сама работа с сетями. Если сети названы в источнике, они
                перечислены в карточке, если связь не подтверждена — так и написано.
              </p>
            </section>

            <section className="intro__item intro__item--bad">
              <h3 className="intro__title">Красные — 0 баллов</h3>
              <p>
                Компании, которым Роспотребнадзор приостанавливал работу после отравлений и
                проверок. В карточке — санкция, дата, сеть-заказчик и ссылки на публикации.
              </p>
            </section>

            <button type="button" className="intro__more" onClick={() => leave(onDetails)}>
              Подробно о расчёте и профилях →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

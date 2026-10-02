import React, { useEffect } from 'react';

/** Короткая памятка на первый заход: как читать балл и цветные карточки. */
export default function Intro({ weights, onDetails, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

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
    <div className="modal" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal__in modal__in--narrow">
        <div className="modal__sheet">
          <div className="modal__head">
            <h2>Как читать выдачу</h2>
            <button type="button" className="btn btn--cyan" onClick={onClose}>Понятно</button>
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

            <button type="button" className="intro__more" onClick={onDetails}>
              Подробно о расчёте и профилях →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

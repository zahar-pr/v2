import React, { useEffect, useRef, useState } from 'react';

const FLY_MS = 420;

const ORDER = ['safety', 'reputation', 'volume', 'docs', 'logistics', 'reach', 'trust'];
const TITLES = {
  safety: 'Санитарная история',
  reputation: 'Репутация',
  volume: 'Опт и объёмы',
  docs: 'Документы',
  logistics: 'Логистика',
  reach: 'Связь',
  trust: 'Полнота данных',
};

/** Памятка на каждый заход: как устроена выдача и что в ней демонстрационное. */
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

  return (
    <div
      className={`modal${leaving ? ' modal--leaving' : ''}`}
      onClick={(e) => { if (e.target === e.currentTarget) close(); }}
    >
      <div className="modal__in modal__in--narrow">
        <div className="modal__sheet" ref={sheet}>
          <div className="modal__head">
            <h2>Система расчета</h2>
            <button type="button" className="btn btn--cyan" onClick={close}>Понятно</button>
          </div>

          <div className="intro">
            <section className="intro__item">
              <h3 className="intro__title">Сервис отвечает на один вопрос</h3>
              <p>
                У кого закупить еду, чтобы ей не отравились гости, и кому звонить первым.
                Не «какие компании есть в городе» — это покажет любая карта.
              </p>
            </section>

            <section className="intro__item intro__item--good">
              <h3 className="intro__title">Сначала санитарная история</h3>
              <p>
                Каждая компания сверяется с перечнем решений Роспотребнадзора и судов о
                приостановке производства. Зелёная плашка значит «сверено, не числится»,
                жёлтая — «подтверждать нечем: юрлицо или документы не найдены»,
                красная — «решение было». Если приостановка истекла, в карточке так и
                написано: запрета нет, но случай был.
              </p>
            </section>

            <section className="intro__item">
              <h3 className="intro__title">Балл — это приоритет звонка</h3>
              <p>
                От 0 до 100. Семь факторов со своими весами; «Сбалансировано» —
                профиль по умолчанию:
              </p>
              <div className="intro__weights">
                {ORDER.map((id) => (
                  <span className="intro__weight" key={id}>
                    {TITLES[id]} <b>{weights[id]}</b>
                  </span>
                ))}
              </div>
              <p className="intro__after">
                Санитарная история работает не слагаемым, а потолком: сколько бы ни было
                телефонов и деклараций, компания с действующим решением наверх не всплывёт.
              </p>
            </section>

            <section className="intro__item intro__item--good">
              <h3 className="intro__title">Зелёные — 100 баллов</h3>
              <p>
                Поставщики крупных сетей общепита. Им ставится максимум, даже если данных
                мало: сети пускают поставщика к полке только после аудита производства, и это
                сильнее любой декларации. Названные в источниках сети перечислены в карточке;
                где связь не подтверждена — так и написано.
              </p>
            </section>

            <section className="intro__item intro__item--bad">
              <h3 className="intro__title">Красные — 0 баллов</h3>
              <p>
                Компании из санитарных дел: приостановки после массового отравления и проверок.
                В карточке — что нашли, дата решения, срок, сеть-заказчик и ссылка на публикацию.
              </p>
            </section>

            <section className="intro__item">
              <h3 className="intro__title">Дорогой поставщик или дешёвый</h3>
              <p>
                Прайсы почти никто не публикует, поэтому уровень цены выводится из структуры
                сделки: завод дешевле дистрибьютора, дистрибьютор дешевле мелкого опта, объём
                сбивает цену. У такой строки всегда стоит пометка «оценка» и список оснований.
              </p>
            </section>

            <section className="intro__item">
              <h3 className="intro__title">Прочерков в карточке нет</h3>
              <p>
                Что собрано — лежит в досье, чего собрать нельзя — превращается в ссылку с
                подставленным ИНН: декларации в Росаккредитации, проверки в ЕРКНМ, суды,
                долги, госконтракты. Плюс список «чего не хватает» с объяснением, зачем это
                поле нужно, — его удобно зачитывать в первом звонке.
              </p>
            </section>

            <section className="intro__item intro__item--demo">
              <h3 className="intro__title">Что здесь демонстрационное</h3>
              <p>
                Чтобы было видно, как сервис работает в деле, часть жизни добавлена заранее:
                у некоторых поставщиков уже проставлены статусы, написаны комментарии коллег,
                кто-то лежит в списке обзвона и с отмеченным «Запросили КП». Часть внешних
                оценок — тоже витрина, у каждой такой строки стоит пометка «демо».
                Данные о компаниях, реквизиты и санитарные решения — настоящие,
                со ссылками на источники.
              </p>
            </section>

            <button type="button" className="intro__more" onClick={() => leave(onDetails)}>
              Подробно о факторах и профилях →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

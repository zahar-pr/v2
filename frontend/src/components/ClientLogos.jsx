import React, { useState } from 'react';

// Клиенты Goulash Tech. Логотипы лежат в public/clients/;
// если файл не загрузился, показывается название текстом.
const CLIENTS = [
  ['UP Sushi', 'up-sushi.svg'],
  ['Сушкоф и пицца', 'sushkof.svg'],
  ['FoodGarden', 'foodgarden.svg'],
  ['Жиши суши', 'zhishi-sushi.svg'],
  ['СушиСелл', 'sushisell.svg'],
  ['Ninja Pizza', 'ninja-pizza.svg'],
  ['Сытый Король', 'sytyj-korol.svg'],
  ['Неместные', 'nemestnye.svg'],
  ['Rolik', 'rolik.svg'],
  ['Японский домик', 'yaponskij-domik.svg'],
  ['Magic Burger', 'magic-burger.svg'],
  ['Sushiman', 'sushiman.svg'],
  ['Sayori', 'sayori.svg'],
  ['ТиЧ Пицца', 'tich-pizza.svg'],
  ['Суши Шеф', 'sushi-shef.svg'],
  ['VЁSLA', 'vesla.svg'],
  ['Пицца Сан', 'pizza-san.svg'],
  ['Жизнь Март', 'zhizn-mart.svg'],
  ['ЁЮ', 'yoyu.png'],
];

function ClientLogo({ name, file }) {
  const [failed, setFailed] = useState(false);
  return (
    <li className="clients__item" title={name}>
      {failed ? (
        <span className="clients__name">{name}</span>
      ) : (
        <img
          src={`/clients/${file}`}
          alt={name}
          loading="lazy"
          decoding="async"
          onError={() => setFailed(true)}
        />
      )}
    </li>
  );
}

export default function ClientLogos() {
  return (
    <ul className="clients" aria-label="Клиенты Goulash Tech">
      {CLIENTS.map(([name, file]) => <ClientLogo key={file} name={name} file={file} />)}
    </ul>
  );
}

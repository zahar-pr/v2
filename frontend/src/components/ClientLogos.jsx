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
        <img src={`/clients/${file}`} alt={name} decoding="async" onError={() => setFailed(true)} />
      )}
    </li>
  );
}

/**
 * Бегущая строка логотипов. Лента печатается дважды подряд и сдвигается ровно на
 * половину — так склейка не видна и строка идёт бесконечно.
 */
export default function ClientLogos() {
  const line = (hidden) => (
    <ul className="clients__line" aria-hidden={hidden || undefined}>
      {CLIENTS.map(([name, file]) => (
        <ClientLogo key={`${hidden ? 'copy' : 'main'}-${file}`} name={name} file={file} />
      ))}
    </ul>
  );

  return (
    <div className="clients" aria-label="Клиенты Goulash Tech">
      <div className="clients__track">
        {line(false)}
        {line(true)}
      </div>
    </div>
  );
}

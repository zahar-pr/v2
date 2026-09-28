import React, { useState } from 'react';

// Клиенты Goulash Tech. Логотипы лежат в public/clients/<slug>.(svg|png|webp);
// если файла нет, показывается название текстом.
const CLIENTS = [
  ['UP Sushi', 'up-sushi'],
  ['Сушкоф и пицца', 'sushkof'],
  ['FoodGarden', 'foodgarden'],
  ['Жиши суши', 'zhishi-sushi'],
  ['СушиСелл', 'sushisell'],
  ['Ninja Pizza', 'ninja-pizza'],
  ['Сытый Король', 'sytyj-korol'],
  ['Неместные', 'nemestnye'],
  ['Rolik', 'rolik'],
  ['Японский домик', 'yaponskij-domik'],
  ['Magic Burger', 'magic-burger'],
  ['Sushiman', 'sushiman'],
  ['Sayori', 'sayori'],
  ['ТиЧ Пицца', 'tich-pizza'],
  ['Суши Шеф', 'sushi-shef'],
  ['VЁSLA', 'vesla'],
  ['Пицца Сан', 'pizza-san'],
  ['Жизнь Март', 'zhizn-mart'],
  ['ЁЮ', 'yoyu'],
];

const EXTS = ['svg', 'png', 'webp'];

function ClientLogo({ name, slug }) {
  const [ext, setExt] = useState(0);
  const failed = ext >= EXTS.length;
  return (
    <li className="clients__item" title={name}>
      {failed ? (
        <span className="clients__name">{name}</span>
      ) : (
        <img
          src={`/clients/${slug}.${EXTS[ext]}`}
          alt={name}
          loading="lazy"
          decoding="async"
          onError={() => setExt((i) => i + 1)}
        />
      )}
    </li>
  );
}

export default function ClientLogos() {
  return (
    <ul className="clients" aria-label="Клиенты Goulash Tech">
      {CLIENTS.map(([name, slug]) => <ClientLogo key={slug} name={name} slug={slug} />)}
    </ul>
  );
}

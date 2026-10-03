import React from 'react';

/** Дорогой поставщик или дешёвый. Это оценка уровня, и так и подписано. */
export default function PriceTag({ price, compact }) {
  if (!price) return null;
  const hint = [price.hint, ...(price.why || [])].join('. ');

  return (
    <span className={`ptag ptag--${price.tier}`} title={hint}>
      <i aria-hidden="true">₽</i>
      <span>{price.title}</span>
      {!compact && price.estimate && <em>оценка</em>}
    </span>
  );
}

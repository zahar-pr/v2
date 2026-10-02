import React from 'react';

/** Кнопка в шапке, из которой вылетает и в которую возвращается памятка. */
export default function HelpButton({ onOpen }) {
  return (
    <button
      type="button"
      className="helper"
      onClick={onOpen}
      title="Система расчета: балл, зелёные и красные карточки"
      aria-label="Система расчета"
    >
      <span className="helper__sign" aria-hidden="true">?</span>
      <span className="helper__hint">Система расчета</span>
    </button>
  );
}

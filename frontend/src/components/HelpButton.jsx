import React from 'react';

/** Кнопка в шапке, из которой вылетает и в которую возвращается памятка. */
export default function HelpButton({ onOpen }) {
  return (
    <button
      type="button"
      className="helper"
      onClick={onOpen}
      title="Как читать выдачу: балл, зелёные и красные карточки"
      aria-label="Как читать выдачу"
    >
      <span className="helper__sign" aria-hidden="true">?</span>
      <span className="helper__hint">Как читать выдачу</span>
    </button>
  );
}

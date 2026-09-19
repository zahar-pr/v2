import React, { useEffect, useState } from 'react';
import { addComment, deleteComment, getComments } from '../api/client.js';
import { plural } from '../data/suppliers.js';

const STARS = [1, 2, 3, 4, 5];

export default function Comments({ supplierId, onChanged }) {
  const [items, setItems] = useState([]);
  const [author, setAuthor] = useState('');
  const [text, setText] = useState('');
  const [rating, setRating] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    setLoading(true);
    getComments(supplierId)
      .then((answer) => {
        if (!alive) return;
        setItems(answer.items);
        setAuthor((prev) => prev || answer.author || '');
        setLoading(false);
      })
      .catch(() => { if (alive) { setItems([]); setLoading(false); } });
    return () => { alive = false; };
  }, [supplierId]);

  const send = () => {
    const clean = text.trim();
    if (!clean || sending) return;
    setSending(true);
    setError('');
    addComment(supplierId, clean, rating || null, author.trim())
      .then((saved) => {
        setItems((prev) => [saved, ...prev]);
        setText('');
        setRating(0);
        setSending(false);
        if (onChanged) onChanged();
      })
      .catch((e) => { setError(e.message); setSending(false); });
  };

  const remove = (id) => {
    deleteComment(id)
      .then(() => {
        setItems((prev) => prev.filter((c) => c.id !== id));
        if (onChanged) onChanged();
      })
      .catch(() => {});
  };

  const rated = items.filter((c) => c.rating);
  const average = rated.length
    ? (rated.reduce((sum, c) => sum + c.rating, 0) / rated.length).toFixed(1)
    : null;

  return (
    <div>
      <div className="section-title">
        Комментарии команды
        {average && <span className="cmt__avg">{average} из 5</span>}
      </div>

      <div className="cmt__form">
        <div className="cmt__row">
          <input
            className="cmt__name"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            placeholder="Ваше имя"
            maxLength={60}
          />
          <div className="stars" role="group" aria-label="Оценка поставщика">
            {STARS.map((star) => (
              <button
                type="button"
                key={star}
                className={`star${rating >= star ? ' star--on' : ''}`}
                onClick={() => setRating(rating === star ? 0 : star)}
                aria-label={`Оценка ${star} из 5`}
              >
                ★
              </button>
            ))}
          </div>
        </div>
        <textarea
          className="note"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Что выяснили: условия, цены, как отвечают, стоит ли работать"
        />
        {error && <div className="cmt__error">{error}</div>}
        <button
          type="button"
          className="btn btn--deep"
          onClick={send}
          disabled={sending || !text.trim()}
        >
          {sending ? 'Отправляем…' : 'Оставить комментарий'}
        </button>
      </div>

      {loading && <div className="note__status">Загружаем комментарии…</div>}

      {!loading && items.length === 0 && (
        <div className="note__status">
          Комментариев пока нет. Первый после звонка сэкономит время всей команде.
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="cmt__list">
          <div className="note__status">
            {items.length} {plural(items.length, 'комментарий', 'комментария', 'комментариев')}
          </div>
          {items.map((item) => (
            <div className="cmt" key={item.id}>
              <div className="cmt__head">
                <span className="cmt__author">{item.author}</span>
                {item.rating && <span className="cmt__rating">★ {item.rating}</span>}
                <span className="cmt__date">
                  {item.createdAt
                    ? new Date(item.createdAt * 1000).toLocaleDateString('ru-RU')
                    : ''}
                </span>
                {item.mine && (
                  <button type="button" className="cmt__remove" onClick={() => remove(item.id)}>
                    удалить
                  </button>
                )}
              </div>
              <div className="cmt__text">{item.text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

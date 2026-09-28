import { useEffect, useState } from 'react';

const KEY = 'provizia_theme';
const DARK = '(prefers-color-scheme: dark)';

function saved() {
  try {
    const value = localStorage.getItem(KEY);
    return value === 'dark' || value === 'light' ? value : '';
  } catch (error) {
    return '';
  }
}

function system() {
  return window.matchMedia && window.matchMedia(DARK).matches ? 'dark' : 'light';
}

/**
 * Тема страницы: выбор пользователя важнее системной настройки.
 * Пока выбора нет, следим за системной темой и переключаемся вместе с ней.
 */
export default function useTheme() {
  const [theme, setTheme] = useState(() => saved() || system());
  const [chosen, setChosen] = useState(() => Boolean(saved()));

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (chosen || !window.matchMedia) return undefined;
    const mq = window.matchMedia(DARK);
    const update = () => setTheme(mq.matches ? 'dark' : 'light');
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, [chosen]);

  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    setChosen(true);
    try {
      localStorage.setItem(KEY, next);
    } catch (error) {
      // приватный режим: тема продержится до перезагрузки
    }
  };

  return [theme, toggle];
}

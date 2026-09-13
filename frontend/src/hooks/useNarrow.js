import { useEffect, useState } from 'react';

/**
 * true, когда экран уже breakpoint — для мобильной раскладки сравнения.
 * Значение берётся из matchMedia и перепроверяется после монтирования,
 * чтобы не остаться с шириной, измеренной до первого layout.
 */
export default function useNarrow(breakpoint = 760) {
  const queryString = `(max-width: ${breakpoint - 1}px)`;
  const [narrow, setNarrow] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(queryString).matches
  );

  useEffect(() => {
    const mq = window.matchMedia(queryString);
    const update = () => setNarrow(mq.matches);
    update();

    if (mq.addEventListener) mq.addEventListener('change', update);
    else mq.addListener(update);
    window.addEventListener('resize', update);

    return () => {
      if (mq.removeEventListener) mq.removeEventListener('change', update);
      else mq.removeListener(update);
      window.removeEventListener('resize', update);
    };
  }, [queryString]);

  return narrow;
}

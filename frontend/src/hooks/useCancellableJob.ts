import { useCallback, useEffect, useRef } from 'react';
import { JobRecord, PollJobOptions } from '../api';

/**
 * Manages a cancellation flag that is tripped when the component unmounts,
 * and returns a factory that builds {@link PollJobOptions} for job polling.
 *
 * Usage:
 *   const jobOptions = useCancellableJob();
 *   await parseChatScreenshot(file, jobOptions((job) => setStatus(...)));
 */
export function useCancellableJob(): (onProgress?: (job: JobRecord) => void) => PollJobOptions {
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
    };
  }, []);

  return useCallback(
    (onProgress?: (job: JobRecord) => void): PollJobOptions => ({
      shouldCancel: () => cancelledRef.current,
      onProgress,
    }),
    [],
  );
}

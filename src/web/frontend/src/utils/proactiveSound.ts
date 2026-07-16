/**
 * proactiveSound - synthesise a short "ding" tone via the Web Audio API.
 *
 * Spec (Stage D.2.3):
 *   - Duration ~200ms
 *   - 440Hz sine wave
 *   - Soft attack/release envelope to avoid clicks
 *   - Gracefully degrade when AudioContext is unavailable or the browser
 *     has blocked autoplay (no user gesture yet). Callers can fall back
 *     to a visual cue when ``playProactiveDing()`` returns ``false``.
 *
 * No external audio file is shipped; the tone is generated on the fly.
 */

interface DingOptions {
  /** Frequency in Hz. Default 440 (A4). */
  frequency?: number;
  /** Total tone duration in ms. Default 200. */
  durationMs?: number;
  /** Peak gain (0-1). Default 0.3. */
  peakGain?: number;
}

interface PlayResult {
  ok: boolean;
  reason?: string;
}

let _sharedContext: AudioContext | null = null;

/**
 * Lazily create / reuse a single AudioContext. Creating many AudioContexts
 * is wasteful and some browsers cap the number of simultaneous contexts.
 */
function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  const Ctor: typeof AudioContext | undefined =
    (window as any).AudioContext || (window as any).webkitAudioContext;
  if (!Ctor) return null;
  if (_sharedContext) return _sharedContext;
  try {
    _sharedContext = new Ctor();
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[proactiveSound] AudioContext 构造失败:', err);
    _sharedContext = null;
  }
  return _sharedContext;
}

/**
 * Try to (re)start the shared AudioContext. Modern browsers require a user
 * gesture before audio plays. We attempt a resume() so that the first
 * ``playProactiveDing()`` call after a user click will succeed.
 *
 * Safe to call on every user interaction (no-op when already running).
 */
export function unlockProactiveAudio(): void {
  const ctx = getAudioContext();
  if (!ctx) return;
  if (ctx.state === 'suspended') {
    try {
      ctx.resume().catch(() => {
        /* will retry on next user gesture */
      });
    } catch {
      /* ignore */
    }
  }
}

/**
 * Play the proactive "ding". Returns a structured result so callers can
 * choose to fall back to a visual cue when audio is blocked.
 */
export function playProactiveDing(options: DingOptions = {}): PlayResult {
  const {
    frequency = 440,
    durationMs = 200,
    peakGain = 0.3,
  } = options;

  const ctx = getAudioContext();
  if (!ctx) {
    return { ok: false, reason: 'AudioContext 不可用' };
  }

  // Some browsers start the context in 'suspended' state. Attempt resume()
  // but don't block: if it can't resume right now, the oscillator simply
  // stays silent and we report failure to the caller.
  if (ctx.state === 'suspended') {
    try {
      ctx.resume().catch(() => {
        /* swallow - we will still try and report */
      });
    } catch {
      /* ignore */
    }
  }

  try {
    const durationSec = Math.max(0.05, durationMs / 1000);
    const now = ctx.currentTime;
    const attack = 0.01;
    const release = 0.04;
    const hold = Math.max(0, durationSec - attack - release);

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(frequency, now);

    // Envelope: 0 -> peak -> hold -> 0
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(peakGain, now + attack);
    gain.gain.linearRampToValueAtTime(peakGain, now + attack + hold);
    gain.gain.linearRampToValueAtTime(0, now + attack + hold + release);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + durationSec + 0.01);

    osc.onended = () => {
      try {
        osc.disconnect();
      } catch {
        /* ignore */
      }
      try {
        gain.disconnect();
      } catch {
        /* ignore */
      }
    };

    return { ok: true };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[proactiveSound] 播放失败:', err);
    return {
      ok: false,
      reason: err instanceof Error ? err.message : String(err),
    };
  }
}

export default playProactiveDing;

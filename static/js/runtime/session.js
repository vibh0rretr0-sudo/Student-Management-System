let boot = null;

export function setBoot(data) {
  boot = data;
}

export function getBoot() {
  return boot || { user: {}, threshold: 75, idle_minutes: 30, warn_minutes: 25 };
}

export function getUser() {
  return getBoot().user || {};
}

export function getThreshold() {
  const value = Number(getBoot().threshold);
  return Number.isFinite(value) && value > 0 ? value : 75;
}
